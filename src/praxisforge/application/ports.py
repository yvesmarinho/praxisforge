# -*- coding: utf-8 -*-
"""
NOME: ports.py
TITULO: Portas (abstrações) da Application — Dependency Inversion para integrações reais
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 16:50
VERSÃO: 0.1.0
DEPEND: praxisforge.domain
HISTÓRICO:
    - 22/09/2026 09:45: criação (T023)
    - 22/09/2026 18:05: +RootFolderProbe (T016, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:07: +porta GitContentInspector (T015, feature 004)
    - 23/09/2026 16:50: PathResolver → FolderLocator + LegacyPathSource (T015, feature 005)
STATUS: DEV
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
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
