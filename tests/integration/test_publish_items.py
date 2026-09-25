# -*- coding: utf-8 -*-
"""
NOME: test_publish_items.py
TITULO: Testes de falha — caso de uso publish_items (estados de publicação por item)
DATA: 25/09/2026 13:17
MODIFICADO: 25/09/2026 13:17
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.publish_items
HISTÓRICO:
    - 25/09/2026 13:17: criação (T032, feature 009) — sucede test_publish_skills.py
STATUS: DEV
"""

import json
import shutil
from pathlib import Path

import pytest

from praxisforge.application.publish_items import PublishReport, publish_items
from praxisforge.domain.errors import NotPublishableKindError, SkillPublicationError
from praxisforge.domain.library_item import ItemKind
from praxisforge.infrastructure.filesystem_item_publisher import FilesystemItemPublisher
from praxisforge.infrastructure.filesystem_library_repository import FilesystemLibraryRepository
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from praxisforge.infrastructure.source_frontmatter import FrontmatterSourceReader
from tests.library_helpers import criar_projeto, escrever_item


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return criar_projeto(tmp_path / "repo")


@pytest.fixture
def projeto(tmp_path: Path) -> Path:
    destino = tmp_path / "app"
    destino.mkdir()
    return destino


def _publicar(
    root: Path,
    projeto: Path,
    kind: ItemKind | None = None,
    name: str | None = None,
    *,
    mode: str = "copy",
    prune: bool = False,
) -> PublishReport:
    validator = JsonSchemaContractValidator(schemas_dir=root / "schemas")
    return publish_items(
        FilesystemLibraryRepository(root / "library"),
        validator,
        FrontmatterSourceReader(),
        sorted((root / "src" / "data" / "sources").rglob("*.md")),
        FilesystemItemPublisher(root / "library", validator),
        projeto,
        kind=kind,
        name=name,
        mode=mode,
        prune=prune,
    )


def _status(report: PublishReport) -> dict[str, str]:
    return {o.name: o.status for o in report.outcomes}


def test_publica_todos_os_tipos_publicaveis(root: Path, projeto: Path) -> None:
    """--all publica skill, command, agent e rule; hook e reference não (FR-019)."""
    for kind in ("skill", "command", "agent", "hook", "rule", "reference"):
        escrever_item(root, kind, f"{kind}-a")
    report = _publicar(root, projeto)
    assert _status(report) == {
        "skill/skill-a": "publicada",
        "command/command-a": "publicada",
        "agent/agent-a": "publicada",
        "rule/rule-a": "publicada",
    }
    claude = projeto / ".claude"
    assert (claude / "skills" / "skill-a" / "SKILL.md").is_file()
    assert (claude / "commands" / "command-a.md").is_file()
    assert (claude / "agents" / "agent-a.md").is_file()
    assert (claude / "rules" / "rule-a.md").is_file()
    assert not (claude / "hooks").exists()


def test_republicar_sem_mudanca_nao_altera_nada(root: Path, projeto: Path) -> None:
    """Segunda publicação: tudo inalterado (FR-020)."""
    escrever_item(root, "skill", "s")
    escrever_item(root, "command", "c")
    _publicar(root, projeto)
    assert set(_status(_publicar(root, projeto)).values()) == {"inalterada"}


def test_versao_nova_atualiza(root: Path, projeto: Path) -> None:
    """Conteúdo e versão novos → atualizada."""
    escrever_item(root, "agent", "a")
    _publicar(root, projeto)
    escrever_item(root, "agent", "a", version="1.1.0", corpo="Novo.\n")
    assert _status(_publicar(root, projeto)) == {"agent/a": "atualizada"}


def test_mesma_versao_com_conteudo_diferente_recusa(root: Path, projeto: Path) -> None:
    """Conteúdo mudou sem nova versão → recusada."""
    escrever_item(root, "rule", "r")
    _publicar(root, projeto)
    escrever_item(root, "rule", "r", corpo="Outra regra.\n")
    report = _publicar(root, projeto)
    assert _status(report) == {"rule/r": "recusada"}
    assert "incremente a versão" in report.outcomes[0].reason
    assert report.refused


def test_terceiro_intocado(root: Path, projeto: Path) -> None:
    """Item de mesmo nome não publicado por nós fica intacto e a recusa é reportada."""
    escrever_item(root, "command", "c")
    alheio = projeto / ".claude" / "commands" / "c.md"
    alheio.parent.mkdir(parents=True)
    alheio.write_text("meu\n", encoding="utf-8")
    report = _publicar(root, projeto)
    assert _status(report) == {"command/c": "recusada"}
    assert alheio.read_text(encoding="utf-8") == "meu\n"


def test_item_invalido_nao_publica(root: Path, projeto: Path) -> None:
    """Item inválido é recusado e não chega ao projeto."""
    escrever_item(root, "agent", "a", campos={"name": "x"})
    assert _status(_publicar(root, projeto)) == {"agent/a": "recusada"}
    assert not (projeto / ".claude" / "agents" / "a.md").exists()


def test_reescrita_pendente_publica(root: Path, projeto: Path) -> None:
    """rewrite_pending não bloqueia a publicação (FR-024a)."""
    escrever_item(root, "skill", "s", metadata={"rewrite_pending": True})
    assert _status(_publicar(root, projeto)) == {"skill/s": "publicada"}


@pytest.mark.parametrize("kind", [ItemKind.HOOK, ItemKind.REFERENCE])
def test_tipo_nao_publicavel(root: Path, projeto: Path, kind: ItemKind) -> None:
    """Pedir hook ou reference explicitamente → NotPublishableKindError."""
    escrever_item(root, kind.value, "x")
    with pytest.raises(NotPublishableKindError):
        _publicar(root, projeto, kind=kind, name="x")


def test_um_item(root: Path, projeto: Path) -> None:
    """--type + nome publica só aquele item."""
    escrever_item(root, "agent", "a")
    escrever_item(root, "agent", "b")
    assert _status(_publicar(root, projeto, ItemKind.AGENT, "b")) == {"agent/b": "publicada"}


def test_orfaos_so_removidos_com_prune(root: Path, projeto: Path) -> None:
    """Item publicado que saiu do acervo é órfão; só --prune remove (só os nossos)."""
    escrever_item(root, "command", "velho")
    escrever_item(root, "skill", "s")
    _publicar(root, projeto)
    (root / "library" / "commands" / "velho.md").unlink()
    report = _publicar(root, projeto)
    assert report.orphans == ["command/velho"]
    assert (projeto / ".claude" / "commands" / "velho.md").exists()
    report = _publicar(root, projeto, prune=True)
    assert report.removed == ["command/velho"]
    assert not (projeto / ".claude" / "commands" / "velho.md").exists()
    assert not (projeto / ".claude" / "commands" / ".velho.md.praxisforge.json").exists()


def test_symlink_e_troca_de_modo(root: Path, projeto: Path) -> None:
    """Modo symlink publica link; voltar para cópia atualiza sem regra de versão."""
    escrever_item(root, "command", "c")
    assert _status(_publicar(root, projeto, mode="symlink")) == {"command/c": "publicada"}
    assert (projeto / ".claude" / "commands" / "c.md").is_symlink()
    assert _status(_publicar(root, projeto, mode="symlink")) == {"command/c": "inalterada"}
    assert _status(_publicar(root, projeto)) == {"command/c": "atualizada"}
    assert not (projeto / ".claude" / "commands" / "c.md").is_symlink()


def test_references_citadas_vao_dentro_da_skill(root: Path, projeto: Path) -> None:
    """References citadas pela skill são copiadas para <skill>/references/ (FR-021)."""
    escrever_item(root, "reference", "checklist", corpo="Itens.\n")
    escrever_item(root, "skill", "s", metadata={"references": ["checklist"]})
    _publicar(root, projeto)
    copia = projeto / ".claude" / "skills" / "s" / "references" / "checklist.md"
    assert copia.read_text(encoding="utf-8").endswith("Itens.\n")


def test_reference_alterada_republica_a_skill(root: Path, projeto: Path) -> None:
    """Mudar a reference muda o conteúdo publicado da skill (exige nova versão da skill)."""
    escrever_item(root, "reference", "checklist")
    escrever_item(root, "skill", "s", metadata={"references": ["checklist"]})
    _publicar(root, projeto)
    escrever_item(root, "reference", "checklist", corpo="Mudou.\n")
    assert _status(_publicar(root, projeto)) == {"skill/s": "recusada"}


def _publicacao_da_008(root: Path, projeto: Path, nome: str) -> Path:
    """Simula uma skill publicada pela feature 008 (marcador skill-publication-v1)."""
    repo = FilesystemLibraryRepository(root / "library")
    destino = projeto / ".claude" / "skills" / nome
    shutil.copytree(root / "library" / "skills" / nome, destino)
    (destino / ".praxisforge-skill.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "name": nome,
                "version": "1.0.0",
                "content_sha256": repo.content_hash(ItemKind.SKILL, nome),
                "source": f"skills/{nome}",
            }
        ),
        encoding="utf-8",
    )
    return destino


def test_marcador_da_008_so_e_regravado(root: Path, projeto: Path) -> None:
    """Publicação antiga igual: só o marcador muda; depois, nada muda (FR-017, FR-017b)."""
    escrever_item(root, "skill", "s")
    destino = _publicacao_da_008(root, projeto, "s")
    skill_md = (destino / "SKILL.md").read_bytes()
    assert _status(_publicar(root, projeto)) == {"skill/s": "marcador atualizado"}
    marcador = json.loads((destino / ".praxisforge-skill.json").read_text(encoding="utf-8"))
    assert (marcador["kind"], marcador["source"]) == ("skill", "library/skills/s")
    assert (destino / "SKILL.md").read_bytes() == skill_md
    assert _status(_publicar(root, projeto)) == {"skill/s": "inalterada"}


def test_symlink_da_008_quebrado_e_recriado(root: Path, projeto: Path) -> None:
    """Symlink antigo para skills/<nome> (que sumiu) é nosso e é recriado (FR-017b)."""
    escrever_item(root, "skill", "s")
    link = projeto / ".claude" / "skills" / "s"
    link.parent.mkdir(parents=True)
    link.symlink_to(root / "skills" / "s", target_is_directory=True)
    report = _publicar(root, projeto, mode="symlink")
    assert _status(report) == {"skill/s": "atualizada"}
    assert link.resolve() == (root / "library" / "skills" / "s").resolve()


def test_falha_de_gravacao_no_meio_do_lote(
    root: Path, projeto: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falha de I/O num item: os anteriores ficam publicados e a falha é por item (exit 3)."""
    escrever_item(root, "skill", "a")
    escrever_item(root, "skill", "b")
    original = FilesystemItemPublisher.publish_copy

    def falhar_em_b(
        self: FilesystemItemPublisher,
        project: Path,
        kind: ItemKind,
        name: str,
        version: str,
        content_sha256: str,
        references: list[Path],
    ) -> None:
        if name == "b":
            raise SkillPublicationError(f"{kind.value}/{name}", "disco cheio")
        original(self, project, kind, name, version, content_sha256, references)

    monkeypatch.setattr(FilesystemItemPublisher, "publish_copy", falhar_em_b)
    report = _publicar(root, projeto)
    assert _status(report) == {"skill/a": "publicada", "skill/b": "recusada"}
    assert report.environment_failure
    assert (projeto / ".claude" / "skills" / "a" / "SKILL.md").is_file()
    assert not (projeto / ".claude" / "skills" / "b").exists()
