# -*- coding: utf-8 -*-
"""
NOME: test_filesystem_item_publisher.py
TITULO: Testes de integração — FilesystemItemPublisher (destinos, marcadores, links)
DATA: 25/09/2026 13:17
MODIFICADO: 25/09/2026 13:17
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.filesystem_item_publisher
HISTÓRICO:
    - 25/09/2026 13:17: criação (T033, feature 009) — sucede test_filesystem_skill_publisher.py
STATUS: DEV
"""

import json
from pathlib import Path

import pytest

from praxisforge.domain.errors import ForeignSkillDestinationError, SkillPublicationError
from praxisforge.domain.library_item import ItemKind
from praxisforge.infrastructure.filesystem_item_publisher import FilesystemItemPublisher
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from tests.library_helpers import criar_projeto, escrever_item

SHA = "a" * 64


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return criar_projeto(tmp_path / "repo")


@pytest.fixture
def projeto(tmp_path: Path) -> Path:
    destino = tmp_path / "app"
    destino.mkdir()
    return destino


def _pub(root: Path) -> FilesystemItemPublisher:
    return FilesystemItemPublisher(
        root / "library", JsonSchemaContractValidator(schemas_dir=root / "schemas")
    )


@pytest.mark.parametrize(
    ("kind", "arquivo"),
    [(ItemKind.COMMAND, "commands"), (ItemKind.AGENT, "agents"), (ItemKind.RULE, "rules")],
)
def test_copia_de_arquivo_unico_com_marcador_irmao(
    root: Path, projeto: Path, kind: ItemKind, arquivo: str
) -> None:
    """Arquivo único: .md no destino e marcador oculto .<nome>.md.praxisforge.json ao lado."""
    escrever_item(root, kind.value, "x")
    pub = _pub(root)
    pub.publish_copy(projeto, kind, "x", "1.0.0", SHA, [])
    destino = projeto / ".claude" / arquivo
    assert (destino / "x.md").is_file()
    marcador = json.loads((destino / ".x.md.praxisforge.json").read_text(encoding="utf-8"))
    assert marcador == {
        "schema_version": "1",
        "kind": kind.value,
        "name": "x",
        "version": "1.0.0",
        "content_sha256": SHA,
        "source": f"library/{arquivo}/x",
    }
    estado = pub.inspect(projeto, kind, "x")
    assert (estado.kind, estado.version, estado.legacy_marker) == ("copy", "1.0.0", False)


def test_skill_com_references(root: Path, projeto: Path) -> None:
    """Skill copiada com marcador na pasta e references em references/."""
    escrever_item(root, "skill", "s", arquivos={"apoio.md": "a"})
    ref = escrever_item(root, "reference", "checklist")
    _pub(root).publish_copy(projeto, ItemKind.SKILL, "s", "1.0.0", SHA, [ref])
    destino = projeto / ".claude" / "skills" / "s"
    assert (destino / "apoio.md").is_file()
    assert (destino / "references" / "checklist.md").is_file()
    assert json.loads((destino / ".praxisforge-skill.json").read_text("utf-8"))["kind"] == "skill"


def test_inspect_ausente_e_terceiro(root: Path, projeto: Path) -> None:
    """Sem destino → absent; arquivo sem marcador ou marcador inválido → foreign."""
    pub = _pub(root)
    assert pub.inspect(projeto, ItemKind.RULE, "r").kind == "absent"
    destino = projeto / ".claude" / "rules"
    destino.mkdir(parents=True)
    (destino / "r.md").write_text("meu\n", encoding="utf-8")
    assert pub.inspect(projeto, ItemKind.RULE, "r").kind == "foreign"
    (destino / ".r.md.praxisforge.json").write_text("{ruim", encoding="utf-8")
    assert pub.inspect(projeto, ItemKind.RULE, "r").kind == "foreign"


def test_marcador_legado_reconhecido(root: Path, projeto: Path) -> None:
    """Marcador skill-publication-v1 (feature 008) → copy com legacy_marker."""
    destino = projeto / ".claude" / "skills" / "s"
    destino.mkdir(parents=True)
    (destino / ".praxisforge-skill.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "name": "s",
                "version": "1.0.0",
                "content_sha256": SHA,
                "source": "skills/s",
            }
        ),
        encoding="utf-8",
    )
    estado = _pub(root).inspect(projeto, ItemKind.SKILL, "s")
    assert (estado.kind, estado.legacy_marker, estado.content_sha256) == ("copy", True, SHA)


def test_rewrite_marker_nao_toca_conteudo(root: Path, projeto: Path) -> None:
    """rewrite_marker só troca o marcador."""
    escrever_item(root, "command", "c")
    pub = _pub(root)
    pub.publish_copy(projeto, ItemKind.COMMAND, "c", "1.0.0", SHA, [])
    antes = (projeto / ".claude" / "commands" / "c.md").read_bytes()
    pub.rewrite_marker(projeto, ItemKind.COMMAND, "c", "1.0.0", "b" * 64)
    assert (projeto / ".claude" / "commands" / "c.md").read_bytes() == antes
    assert pub.inspect(projeto, ItemKind.COMMAND, "c").content_sha256 == "b" * 64


def test_symlink_de_arquivo_unico(root: Path, projeto: Path) -> None:
    """Symlink de command aponta para o .md do acervo e é reconhecido como nosso."""
    escrever_item(root, "command", "c")
    pub = _pub(root)
    pub.publish_symlink(projeto, ItemKind.COMMAND, "c")
    link = projeto / ".claude" / "commands" / "c.md"
    assert link.is_symlink()
    assert link.resolve() == (root / "library" / "commands" / "c.md").resolve()
    assert pub.inspect(projeto, ItemKind.COMMAND, "c").kind == "symlink"


def test_symlink_para_fora_e_terceiro(root: Path, projeto: Path, tmp_path: Path) -> None:
    """Link que não aponta para o acervo é de terceiro."""
    outro = tmp_path / "outro.md"
    outro.write_text("x", encoding="utf-8")
    link = projeto / ".claude" / "agents" / "a.md"
    link.parent.mkdir(parents=True)
    link.symlink_to(outro)
    assert _pub(root).inspect(projeto, ItemKind.AGENT, "a").kind == "foreign"


def test_symlink_legado_quebrado(root: Path, projeto: Path) -> None:
    """Link antigo para <repo>/skills/<nome> que sumiu → broken_symlink (nosso)."""
    link = projeto / ".claude" / "skills" / "s"
    link.parent.mkdir(parents=True)
    link.symlink_to(root / "skills" / "s", target_is_directory=True)
    assert _pub(root).inspect(projeto, ItemKind.SKILL, "s").kind == "broken_symlink"


def test_list_published_e_remove(root: Path, projeto: Path) -> None:
    """Lista só os nossos; remove apaga arquivo e marcador; terceiro não é removido."""
    escrever_item(root, "rule", "nossa")
    pub = _pub(root)
    pub.publish_copy(projeto, ItemKind.RULE, "nossa", "1.0.0", SHA, [])
    destino = projeto / ".claude" / "rules"
    (destino / "alheia.md").write_text("x", encoding="utf-8")
    assert pub.list_published(projeto, ItemKind.RULE) == ["nossa"]
    with pytest.raises(ForeignSkillDestinationError):
        pub.remove(projeto, ItemKind.RULE, "alheia")
    pub.remove(projeto, ItemKind.RULE, "nossa")
    assert sorted(p.name for p in destino.iterdir()) == ["alheia.md"]


def test_falha_de_io_vira_skill_publication_error(root: Path, projeto: Path) -> None:
    """Destino sem permissão de escrita → SkillPublicationError, nada parcial."""
    escrever_item(root, "agent", "a")
    destino = projeto / ".claude" / "agents"
    destino.mkdir(parents=True)
    destino.chmod(0o555)
    try:
        with pytest.raises(SkillPublicationError):
            _pub(root).publish_copy(projeto, ItemKind.AGENT, "a", "1.0.0", SHA, [])
    finally:
        destino.chmod(0o755)
    assert list(destino.iterdir()) == []
