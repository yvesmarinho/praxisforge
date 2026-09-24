# -*- coding: utf-8 -*-
"""
NOME: ports.py
TITULO: Portas (abstrações) da Application — Dependency Inversion para integrações reais
DATA: 22/09/2026 09:45
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: praxisforge.domain
HISTÓRICO:
    - 22/09/2026 09:45: criação (T023)
    - 22/09/2026 18:05: +RootFolderProbe (T016, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:07: +porta GitContentInspector (T015, feature 004)
    - 23/09/2026 16:50: PathResolver → FolderLocator + LegacyPathSource (T015, feature 005)
    - 24/09/2026 10:55: +porta SourceReader (T018, feature 006)
    - 24/09/2026 14:35: +porta RegistryFileMover (T029, feature 007)
    - 24/09/2026 16:54: +SkillDocument e porta SkillRepository (T017, feature 008)
    - 24/09/2026 16:54: +porta CatalogWriter (T025, feature 008)
    - 24/09/2026 16:50: +PublishedState e porta SkillPublisher (T034, feature 008)
STATUS: DEV
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from praxisforge.domain.folder_registry import FolderRegistry


class FolderRegistryRepository(ABC):
    """Porta para persistência do agregado FolderRegistry."""

    @abstractmethod
    def load(self) -> FolderRegistry:
        """
        Carrega e valida o registro completo.

        :return: agregado reconstruído a partir do arquivo persistido.
        :rtype: FolderRegistry
        :raises RegistryFileNotFoundError: arquivo ausente.
        :raises RegistryUnavailableError: arquivo ilegível/corrompido.
        """

    @abstractmethod
    def load_raw(self) -> Mapping[str, object]:
        """
        Carrega o documento bruto (sem reconstruir entidades), para validação por item.

        :return: dict com `schema_version` e `folders`.
        :rtype: Mapping[str, object]
        """

    @abstractmethod
    def save(self, registry: FolderRegistry) -> None:
        """
        Grava o registro de forma atômica e determinística.

        :param registry: agregado a persistir.
        :type registry: FolderRegistry
        """

    @abstractmethod
    def exists(self) -> bool:
        """
        Indica se o arquivo do registro existe.

        :return: True se o arquivo existe.
        :rtype: bool
        """


class FolderLocator(ABC):
    """Porta para localizar pastas no filesystem pelo caminho do registro (feature 005)."""

    @abstractmethod
    def canonicalize(self, alias: str, raw: str) -> Path:
        """
        Converte um caminho informado pelo curador na forma absoluta canônica.

        Expande "~", resolve relativo a partir da pasta atual, elimina "." / ".." e
        resolve links simbólicos; confirma que é uma pasta legível.

        :param alias: alias da pasta (só para mensagens de erro).
        :type alias: str
        :param raw: caminho como informado.
        :type raw: str
        :return: caminho absoluto canônico.
        :rtype: Path
        :raises FolderPathInvalidError: inexistente ou não é diretório.
        :raises FolderPathUnreadableError: sem permissão de listar/entrar.
        """

    @abstractmethod
    def check(self, alias: str, path: Path) -> Path:
        """
        Confirma que a pasta registrada continua acessível no caminho gravado.

        :param alias: alias da pasta.
        :type alias: str
        :param path: caminho gravado no registro.
        :type path: Path
        :return: o próprio caminho, quando acessível.
        :rtype: Path
        :raises FolderPathInvalidError: pasta movida/apagada ou não é diretório.
        :raises FolderPathUnreadableError: sem permissão de listar/entrar.
        """


class LegacyPathSource(ABC):
    """Porta para ler caminhos do formato antigo (variáveis por alias) — só na migração."""

    @abstractmethod
    def lookup(self, alias: str) -> str | None:
        """
        Devolve o caminho configurado no formato antigo para o alias, se houver.

        :param alias: alias da pasta.
        :type alias: str
        :return: caminho bruto, ou None se não configurado.
        :rtype: str | None
        """


class ContractValidator(ABC):
    """Porta para validação de documentos contra contratos JSON Schema versionados."""

    @abstractmethod
    def validate(self, document: Mapping[str, object], schema_name: str) -> None:
        """
        Valida um documento contra o schema nomeado.

        :param document: documento a validar (dict já carregado).
        :type document: Mapping[str, object]
        :param schema_name: nome do schema em `schemas/` (sem extensão).
        :type schema_name: str
        :raises ContractValidationError: violações encontradas (todas de uma vez).
        """


class RootFolderProbe(ABC):
    """Porta para inspecionar uma pasta-raiz arbitrária (feature 003 — bootstrap)."""

    @abstractmethod
    def list_subfolders(self, root: Path) -> list[Path]:
        """
        Lista as subpastas de primeiro nível de uma pasta-raiz.

        :param root: caminho da pasta-raiz.
        :type root: Path
        :return: subpastas de primeiro nível, ordenadas alfabeticamente pelo nome.
        :rtype: list[Path]
        :raises InvalidRootPathError: `root` inexistente, não é diretório, ou sem permissão.
        """

    @abstractmethod
    def read_description(self, path: Path) -> str | None:
        """
        Extrai uma descrição a partir do README de uma pasta, se existir.

        :param path: caminho da pasta.
        :type path: Path
        :return: primeiro parágrafo útil do README, truncado em 500 caracteres, ou `None`.
        :rtype: str | None
        """

    @abstractmethod
    def detect_license(self, path: Path) -> str | None:
        """
        Tenta identificar a licença a partir do LICENSE de uma pasta.

        :param path: caminho da pasta.
        :type path: Path
        :return: identificador da licença reconhecida, ou `None` se ausente/não reconhecida/ambígua.
        :rtype: str | None
        """


class GitContentInspector(ABC):
    """Porta para inspecionar o conteúdo versionado (git) de uma pasta (feature 004)."""

    @abstractmethod
    def head_commit(self, path: Path) -> str | None:
        """
        Obtém o hash do commit HEAD do repositório que contém a pasta.

        :param path: caminho real da pasta (raiz ou subpasta de um repositório).
        :type path: Path
        :return: hash do HEAD, ou `None` se a pasta não está num repositório git ou ele
            não tem commits.
        :rtype: str | None
        :raises ContentInspectionError: git indisponível, tempo esgotado ou saída inesperada.
        """

    @abstractmethod
    def changed_since(self, path: Path, commit: str) -> bool:
        """
        Indica se arquivos versionados dentro da pasta mudaram entre `commit` e o HEAD.

        :param path: caminho real da pasta (raiz ou subpasta de um repositório).
        :type path: Path
        :param commit: hash gravado na última curadoria.
        :type commit: str
        :return: True se a pasta mudou ou se `commit` não existe mais no repositório.
        :rtype: bool
        :raises ContentInspectionError: hash malformado, git indisponível, tempo esgotado
            ou saída inesperada.
        """


class SourceReader(ABC):
    """Porta para ler o frontmatter de um registro de fonte (feature 006)."""

    @abstractmethod
    def read(self, path: Path) -> dict[str, object]:
        """
        Lê o frontmatter de um registro de fonte.

        :param path: caminho do arquivo `.md`.
        :type path: Path
        :return: documento do frontmatter (datas como `str` ISO 8601).
        :rtype: dict[str, object]
        :raises RegistryUnavailableError: arquivo ilegível, sem frontmatter ou corrompido.
        """


class RegistryFileMover(ABC):
    """Porta para mover o arquivo do registro entre locais (feature 007)."""

    @abstractmethod
    def move(self, source: Path, target: Path) -> None:
        """
        Move o arquivo preservando o conteúdo; em falha, a origem permanece intacta.

        :param source: arquivo de origem.
        :type source: Path
        :param target: destino (a pasta é criada se preciso).
        :type target: Path
        :raises RegistryRelocationError: falha de I/O; nenhum arquivo parcial no destino.
        """


@dataclass(frozen=True)
class SkillDocument:
    """
    Conteúdo bruto de uma skill lido do repositório (feature 008).

    :param folder_name: nome da pasta em `skills/`.
    :param frontmatter: frontmatter do SKILL.md.
    :param references: alvos locais citados no corpo, em ordem.
    :param missing_references: referências dentro da pasta que não existem.
    """

    folder_name: str
    frontmatter: dict[str, object]
    references: list[str]
    missing_references: list[str]


class SkillRepository(ABC):
    """Porta de leitura das skills versionadas em `skills/` (feature 008)."""

    @abstractmethod
    def list_names(self) -> list[str]:
        """
        Lista as skills (pastas que não começam por `_` ou `.`), em ordem alfabética.

        :return: nomes das pastas de skill.
        :rtype: list[str]
        """

    @abstractmethod
    def load(self, name: str) -> SkillDocument:
        """
        Lê o SKILL.md da skill.

        :param name: nome da pasta.
        :type name: str
        :return: frontmatter e referências.
        :rtype: SkillDocument
        :raises SkillNotFoundError: pasta inexistente.
        :raises InvalidSkillError: SKILL.md ausente, ilegível ou com frontmatter inválido.
        """

    @abstractmethod
    def content_hash(self, name: str) -> str:
        """
        SHA-256 do conteúdo da skill (caminho relativo + bytes), sem marcador nem `__pycache__`.

        :param name: nome da pasta.
        :type name: str
        :return: 64 caracteres hexadecimais minúsculos.
        :rtype: str
        """

    @abstractmethod
    def skill_dir(self, name: str) -> Path:
        """
        Pasta da skill no repositório.

        :param name: nome da pasta.
        :type name: str
        :return: caminho `skills/<nome>`.
        :rtype: Path
        """


class CatalogWriter(ABC):
    """Porta de gravação do catálogo de skills (feature 008)."""

    @abstractmethod
    def write(self, content: str) -> None:
        """
        Grava o catálogo de forma atômica.

        :param content: Markdown completo do catálogo.
        :type content: str
        :raises CatalogWriteError: falha de I/O; o catálogo anterior permanece.
        """


@dataclass(frozen=True)
class PublishedState:
    """
    Estado de uma skill no destino de publicação (feature 008).

    :param kind: `absent`, `copy` (cópia com marcador nosso), `symlink` (link para o repositório)
        ou `foreign` (qualquer outra coisa — não publicada pelo praxisforge).
    :param version: versão registrada no marcador (só `copy`).
    :param content_sha256: hash registrado no marcador (só `copy`).
    """

    kind: str
    version: str | None = None
    content_sha256: str | None = None


class SkillPublisher(ABC):
    """Porta de publicação das skills em `.claude/skills/` (feature 008)."""

    @abstractmethod
    def inspect(self, dest_root: Path, name: str) -> PublishedState:
        """
        Classifica o destino `<dest_root>/<name>`.

        :param dest_root: pasta `.claude/skills` de destino.
        :type dest_root: Path
        :param name: nome da skill.
        :type name: str
        :return: estado do destino.
        :rtype: PublishedState
        """

    @abstractmethod
    def publish_copy(self, dest_root: Path, name: str, version: str, content_sha256: str) -> None:
        """
        Copia a skill com o marcador, de forma atômica (substitui destino nosso).

        :raises SkillPublicationError: falha de I/O; o destino anterior permanece.
        """

    @abstractmethod
    def publish_symlink(self, dest_root: Path, name: str) -> None:
        """
        Cria (ou troca) o link simbólico para a pasta da skill no repositório.

        :raises SkillPublicationError: falha de I/O; o destino anterior permanece.
        """

    @abstractmethod
    def remove(self, dest_root: Path, name: str) -> None:
        """
        Remove um destino publicado pelo praxisforge.

        :raises ForeignSkillDestinationError: destino não é nosso (nada é removido).
        :raises SkillPublicationError: falha de I/O.
        """

    @abstractmethod
    def list_published(self, dest_root: Path) -> list[str]:
        """
        Lista, em ordem alfabética, os destinos publicados pelo praxisforge.

        :param dest_root: pasta `.claude/skills` de destino.
        :type dest_root: Path
        :return: nomes das skills nossas no destino.
        :rtype: list[str]
        """
