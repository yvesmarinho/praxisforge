# -*- coding: utf-8 -*-
"""
NOME: test_publish_skills.py
TITULO: Testes de falha — caso de uso publish_skills (idempotência, versão, terceiros, órfãs)
DATA: 24/09/2026 16:48
MODIFICADO: 24/09/2026 16:49
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.publish_skills
HISTÓRICO:
    - 24/09/2026 16:48: criação (T029, feature 008)
STATUS: DEV
"""

from collections.abc import Mapping
from pathlib import Path

import pytest

from praxisforge.application.ports import (
    ContractValidator,
    PublishedState,
    SkillDocument,
    SkillPublisher,
    SkillRepository,
    SourceReader,
)
from praxisforge.application.publish_skills import PublishReport, publish_skills
from praxisforge.domain.errors import (
    ForeignSkillDestinationError,
    SkillNotFoundError,
    SkillPublicationError,
)

DEST = Path("/destino")


class _Repo(SkillRepository):
    def __init__(self, versoes: Mapping[str, str], hashes: Mapping[str, str] | None = None) -> None:
        self._versoes = versoes
        self._hashes = hashes or {}

    def list_names(self) -> list[str]:
        return sorted(self._versoes)

    def load(self, name: str) -> SkillDocument:
        if name not in self._versoes:
            raise SkillNotFoundError(name)
        return SkillDocument(
            folder_name=name,
            frontmatter={
                "name": name,
                "description": "d",
                "metadata": {"version": self._versoes[name], "authored": True},
            },
            references=[],
            missing_references=[],
        )

    def content_hash(self, name: str) -> str:
        return self._hashes.get(name, "h" * 64)

    def skill_dir(self, name: str) -> Path:
        return Path("skills") / name


class _Validator(ContractValidator):
    def validate(self, document: Mapping[str, object], schema_name: str) -> None:
        return None


class _Reader(SourceReader):
    def read(self, path: Path) -> dict[str, object]:
        raise AssertionError("sem fontes")


class _Publisher(SkillPublisher):
    def __init__(self, estados: dict[str, PublishedState] | None = None) -> None:
        self.estados = estados or {}
        self.chamadas: list[tuple[str, str]] = []
        self.falhar: set[str] = set()

    def inspect(self, dest_root: Path, name: str) -> PublishedState:
        return self.estados.get(name, PublishedState("absent"))

    def _checar(self, name: str) -> None:
        if name in self.falhar:
            raise SkillPublicationError(name, "sem permissão")

    def publish_copy(self, dest_root: Path, name: str, version: str, content_sha256: str) -> None:
        self._checar(name)
        self.chamadas.append(("copy", name))
        self.estados[name] = PublishedState("copy", version, content_sha256)

    def publish_symlink(self, dest_root: Path, name: str) -> None:
        self._checar(name)
        self.chamadas.append(("symlink", name))
        self.estados[name] = PublishedState("symlink")

    def remove(self, dest_root: Path, name: str) -> None:
        if self.estados.get(name, PublishedState("absent")).kind == "foreign":
            raise ForeignSkillDestinationError(name, str(dest_root / name))
        self._checar(name)
        self.chamadas.append(("remove", name))
        del self.estados[name]

    def list_published(self, dest_root: Path) -> list[str]:
        return sorted(n for n, e in self.estados.items() if e.kind in ("copy", "symlink"))


def _publicar(
    repo: SkillRepository,
    publisher: _Publisher,
    names: list[str] | None = None,
    mode: str = "copy",
    prune: bool = False,
) -> PublishReport:
    return publish_skills(
        repo, _Validator(), _Reader(), [], publisher, DEST, names, mode=mode, prune=prune
    )


def _status(report: PublishReport) -> dict[str, str]:
    return {o.name: o.status for o in report.outcomes}


def test_invalida_recusada_sem_publicar() -> None:
    """Skill inválida é recusada e o publisher não é chamado (FR-012)."""
    publisher = _Publisher()
    report = _publicar(_Repo({"a": "1"}), publisher)
    assert _status(report) == {"a": "recusada"}
    assert publisher.chamadas == []


def test_ausente_publicada() -> None:
    """Destino ausente → publicada."""
    report = _publicar(_Repo({"a": "1.0.0"}), _Publisher())
    assert _status(report) == {"a": "publicada"}


def test_mesmo_hash_inalterada() -> None:
    """Marcador com o mesmo hash → inalterada, sem gravar (SC-003)."""
    publisher = _Publisher({"a": PublishedState("copy", "1.0.0", "h" * 64)})
    report = _publicar(_Repo({"a": "1.0.0"}), publisher)
    assert _status(report) == {"a": "inalterada"} and publisher.chamadas == []


def test_hash_e_versao_diferentes_atualizada() -> None:
    """Conteúdo novo com versão nova → atualizada."""
    publisher = _Publisher({"a": PublishedState("copy", "1.0.0", "x" * 64)})
    report = _publicar(_Repo({"a": "1.1.0"}), publisher)
    assert _status(report) == {"a": "atualizada"}


def test_mesma_versao_conteudo_diferente_recusada_e_lote_segue() -> None:
    """Conteúdo mudou sem incrementar a versão → recusada; as demais seguem (FR-013)."""
    publisher = _Publisher({"a": PublishedState("copy", "1.0.0", "x" * 64)})
    report = _publicar(_Repo({"a": "1.0.0", "b": "1.0.0"}), publisher)
    assert _status(report) == {"a": "recusada", "b": "publicada"}
    falha = next(o for o in report.outcomes if o.name == "a")
    assert falha.error_type == "SkillVersionNotBumpedError" and "versão" in falha.reason
    assert publisher.estados["a"].version == "1.0.0"


def test_terceiro_recusado() -> None:
    """Destino de terceiro → recusada sem alterar (FR-014, SC-004)."""
    publisher = _Publisher({"a": PublishedState("foreign")})
    report = _publicar(_Repo({"a": "1.0.0"}), publisher)
    assert _status(report) == {"a": "recusada"}
    assert report.outcomes[0].error_type == "ForeignSkillDestinationError"
    assert publisher.chamadas == []


def test_symlink_existente_modo_symlink_inalterada() -> None:
    """Link nosso já existente em modo symlink → inalterada."""
    publisher = _Publisher({"a": PublishedState("symlink")})
    report = _publicar(_Repo({"a": "1.0.0"}), publisher, mode="symlink")
    assert _status(report) == {"a": "inalterada"} and publisher.chamadas == []


def test_troca_copia_para_symlink() -> None:
    """Cópia nossa em modo symlink → troca, sem regra de versão."""
    publisher = _Publisher({"a": PublishedState("copy", "1.0.0", "x" * 64)})
    report = _publicar(_Repo({"a": "1.0.0"}), publisher, mode="symlink")
    assert _status(report) == {"a": "atualizada"} and publisher.chamadas == [("symlink", "a")]


def test_troca_symlink_para_copia_mesma_versao() -> None:
    """Link nosso em modo cópia → sempre publica, mesmo com a mesma versão (U1)."""
    publisher = _Publisher({"a": PublishedState("symlink")})
    report = _publicar(_Repo({"a": "1.0.0"}), publisher)
    assert _status(report) == {"a": "atualizada"} and publisher.chamadas == [("copy", "a")]


def test_symlink_ausente_publicada() -> None:
    """Modo symlink com destino ausente → publicada."""
    report = _publicar(_Repo({"a": "1.0.0"}), _Publisher(), mode="symlink")
    assert _status(report) == {"a": "publicada"}


def test_all_lista_orfas_sem_remover() -> None:
    """--all lista órfãs nossas e não as remove (FR-015a)."""
    publisher = _Publisher(
        {"velha": PublishedState("copy", "1.0.0", "x" * 64), "alheia": PublishedState("foreign")}
    )
    report = _publicar(_Repo({"a": "1.0.0"}), publisher)
    assert report.orphans == ["velha"] and report.removed == []
    assert "velha" in publisher.estados


def test_prune_remove_so_orfas_nossas() -> None:
    """--prune remove órfãs nossas; terceiros ficam."""
    publisher = _Publisher(
        {"velha": PublishedState("symlink"), "alheia": PublishedState("foreign")}
    )
    report = _publicar(_Repo({"a": "1.0.0"}), publisher, prune=True)
    assert report.removed == ["velha"]
    assert "velha" not in publisher.estados and "alheia" in publisher.estados


def test_nome_unico_nao_calcula_orfas() -> None:
    """Publicação de uma skill não lista órfãs."""
    publisher = _Publisher({"velha": PublishedState("copy", "1.0.0", "x" * 64)})
    report = _publicar(_Repo({"a": "1.0.0"}), publisher, names=["a"])
    assert report.orphans == []


def test_falha_de_gravacao_agregada_como_ambiente() -> None:
    """SkillPublicationError vira recusa com erro de ambiente; o lote segue."""
    publisher = _Publisher()
    publisher.falhar.add("a")
    report = _publicar(_Repo({"a": "1.0.0", "b": "1.0.0"}), publisher)
    assert _status(report) == {"a": "recusada", "b": "publicada"}
    assert report.environment_failure is True


def test_falha_ao_remover_orfa_e_ambiente() -> None:
    """Falha de I/O ao remover órfã entra no relatório como erro de ambiente."""
    publisher = _Publisher({"velha": PublishedState("copy", "1.0.0", "x" * 64)})
    publisher.falhar.add("velha")
    report = _publicar(_Repo({}), publisher, prune=True)
    assert report.removed == [] and report.environment_failure is True


def test_modo_invalido() -> None:
    """Modo desconhecido é erro de programação da fronteira."""
    with pytest.raises(ValueError, match="modo"):
        _publicar(_Repo({}), _Publisher(), mode="hardlink")
