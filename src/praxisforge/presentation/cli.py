# -*- coding: utf-8 -*-
"""
NOME: cli.py
TITULO: CLI `praxisforge` — argparse; ponto de composição das dependências
DATA: 22/09/2026 09:45
MODIFICADO: 24/09/2026 10:14
VERSÃO: 0.1.0
DEPEND: praxisforge.application, praxisforge.infrastructure (só aqui, ponto de composição)
HISTÓRICO:
    - 22/09/2026 09:45: criação (T038) — subcomandos folders add|list|show|update
    - 23/09/2026 12:08: versão curada e linha 'conteúdo' (T022, T030, feature 004)
    - 23/09/2026 16:56: caminho no registro (--path, list/show), FolderLocator (T026, feature 005)
    - 24/09/2026 10:14: scan/resolve tratam registro inválido sem traceback (bug)
STATUS: DEV
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from praxisforge.application.bootstrap_folders import bootstrap_folders
from praxisforge.application.dto import RegisterFolderInput, UpdateFolderInput
from praxisforge.application.errors import (
    ContentInspectionError,
    ContractValidationError,
    FolderNotFoundError,
    FolderPathInvalidError,
    FolderPathUnreadableError,
    InvalidRootPathError,
    PraxisForgeError,
    RegistryUnavailableError,
)
from praxisforge.application.migrate_registry import migrate_registry
from praxisforge.application.ports import (
    FolderLocator,
    FolderRegistryRepository,
    GitContentInspector,
    RootFolderProbe,
)
from praxisforge.application.query_folders import list_folders, show_folder
from praxisforge.application.register_folder import register_folder
from praxisforge.application.resolve_folder_path import (
    resolve_all_folder_paths,
    resolve_folder_path,
)
from praxisforge.application.scan_folders import scan_all_folders, scan_folder
from praxisforge.application.update_folder import update_folder
from praxisforge.application.validate_registry import validate_registry
from praxisforge.infrastructure.env_legacy_path_source import EnvLegacyPathSource
from praxisforge.infrastructure.filesystem_folder_locator import FilesystemFolderLocator
from praxisforge.infrastructure.filesystem_folder_probe import FilesystemFolderProbe
from praxisforge.infrastructure.git_cli_inspector import GitCliInspector
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from praxisforge.infrastructure.logging_setup import configure_logging
from praxisforge.infrastructure.source_frontmatter import read_frontmatter
from praxisforge.infrastructure.yaml_folder_registry import YamlFolderRegistryRepository

_EXIT_AMBIENTE_ERRORS = (
    FolderPathInvalidError,
    FolderPathUnreadableError,
    ContentInspectionError,
)

_DEFAULT_REGISTRY = Path("src/data/folders.yaml")
_SCHEMAS_DIR = Path("schemas")

_EXIT_OK = 0
_EXIT_VALIDACAO = 1
_EXIT_USO = 2
_EXIT_AMBIENTE = 3


def _formatar_data(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="praxisforge")
    parser.add_argument("--registry", type=Path, default=_DEFAULT_REGISTRY)
    parser.add_argument("--log-level", default="INFO")
    subparsers = parser.add_subparsers(dest="comando", required=True)

    folders = subparsers.add_parser("folders")
    folders_sub = folders.add_subparsers(dest="subcomando", required=True)

    add_parser = folders_sub.add_parser("add")
    add_parser.add_argument("--alias", required=True)
    add_parser.add_argument("--description", required=True)
    add_parser.add_argument("--content-type", required=True)
    add_parser.add_argument("--license", required=True)
    add_parser.add_argument("--status", default="not_scanned")
    add_parser.add_argument("--path", required=True)

    list_parser = folders_sub.add_parser("list")
    list_parser.add_argument("--status", default=None)

    show_parser = folders_sub.add_parser("show")
    show_parser.add_argument("alias")

    update_parser = folders_sub.add_parser("update")
    update_parser.add_argument("alias")
    update_parser.add_argument("--status", default=None)
    update_parser.add_argument("--last-scanned", default=None)
    update_parser.add_argument("--license", default=None)
    update_parser.add_argument("--path", default=None)

    resolve_parser = folders_sub.add_parser("resolve")
    resolve_group = resolve_parser.add_mutually_exclusive_group(required=True)
    resolve_group.add_argument("alias", nargs="?", default=None)
    resolve_group.add_argument("--all", action="store_true", dest="all_aliases")

    scan_parser = folders_sub.add_parser("scan")
    scan_group = scan_parser.add_mutually_exclusive_group(required=True)
    scan_group.add_argument("alias", nargs="?", default=None)
    scan_group.add_argument("--all", action="store_true", dest="all_aliases")

    bootstrap_parser = folders_sub.add_parser("bootstrap")
    bootstrap_parser.add_argument("root", type=Path)

    folders_sub.add_parser("validate")

    migrate_parser = folders_sub.add_parser("migrate")
    migrate_parser.add_argument("--root", type=Path, default=None)

    sources = subparsers.add_parser("sources")
    sources_sub = sources.add_subparsers(dest="subcomando", required=True)
    sources_validate_parser = sources_sub.add_parser("validate")
    sources_validate_parser.add_argument("paths", nargs="+", type=Path)

    return parser


def _cmd_folders_add(
    args: argparse.Namespace, repository: FolderRegistryRepository, locator: FolderLocator
) -> int:
    try:
        data = RegisterFolderInput(
            alias=args.alias,
            description=args.description,
            content_type=args.content_type,
            license=args.license,
            status=args.status,
            path=args.path,
        )
    except ValidationError as error:
        sys.stderr.write(f"argumentos inválidos: {error}\n")
        return _EXIT_USO
    try:
        result = register_folder(repository, data, locator=locator)
    except _EXIT_AMBIENTE_ERRORS as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_AMBIENTE
    except PraxisForgeError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    if result.outcome == "inalterado":
        sys.stdout.write(f"pasta '{args.alias}' inalterado\n")
    else:
        sys.stdout.write(f"pasta '{args.alias}' registrada\n")
    return _EXIT_OK


def _cmd_folders_list(args: argparse.Namespace, repository: FolderRegistryRepository) -> int:
    try:
        folders = list_folders(repository, status=args.status)
    except PraxisForgeError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    for folder in folders:
        sys.stdout.write(
            f"{folder.alias.value}\t{folder.content_type}\t{folder.license}\t"
            f"{folder.status.label_pt_br()}\t{_formatar_data(folder.last_scanned)}\t"
            f"{folder.path}\n"
        )
    return _EXIT_OK


def _cmd_folders_show(args: argparse.Namespace, repository: FolderRegistryRepository) -> int:
    try:
        folder = show_folder(repository, alias=args.alias)
    except PraxisForgeError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    sys.stdout.write(f"alias: {folder.alias.value}\n")
    sys.stdout.write(f"descrição: {folder.description}\n")
    sys.stdout.write(f"tipo de conteúdo: {folder.content_type}\n")
    sys.stdout.write(f"licença: {folder.license}\n")
    sys.stdout.write(f"status: {folder.status.label_pt_br()}\n")
    sys.stdout.write(f"última varredura: {_formatar_data(folder.last_scanned)}\n")
    sys.stdout.write(f"caminho: {folder.path}\n")
    versao = folder.last_curated_commit[:12] if folder.last_curated_commit else "-"
    sys.stdout.write(f"versão curada: {versao}\n")
    return _EXIT_OK


def _cmd_folders_update(
    args: argparse.Namespace,
    repository: FolderRegistryRepository,
    locator: FolderLocator,
    inspector: GitContentInspector,
) -> int:
    try:
        data = UpdateFolderInput(
            alias=args.alias,
            status=args.status,
            last_scanned=args.last_scanned,
            license=args.license,
            path=args.path,
        )
    except ValidationError as error:
        sys.stderr.write(f"argumentos inválidos: {error}\n")
        return _EXIT_USO
    try:
        result = update_folder(repository, data, locator=locator, inspector=inspector)
    except _EXIT_AMBIENTE_ERRORS as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_AMBIENTE
    except PraxisForgeError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    sys.stdout.write(f"pasta '{args.alias}' atualizada\n")
    if result.head_recorded is not None:
        commit = result.folder.last_curated_commit
        versao = commit[:12] if result.head_recorded and commit else "(pasta não é repositório git)"
        sys.stdout.write(f"versão curada: {versao}\n")
    return _EXIT_OK


def _falha_de_registro(error: PraxisForgeError) -> int:
    """Mensagem amigável para registro ilegível ou fora do contrato; código 1."""
    sys.stderr.write(f"{error}\n")
    if isinstance(error, ContractValidationError):
        sys.stderr.write("registro inválido: rode `praxisforge folders validate` para detalhes\n")
    return _EXIT_VALIDACAO


def _cmd_folders_resolve(
    args: argparse.Namespace, repository: FolderRegistryRepository, locator: FolderLocator
) -> int:
    if args.all_aliases:
        try:
            report = resolve_all_folder_paths(repository, locator)
        except PraxisForgeError as error:
            return _falha_de_registro(error)
        for alias, path in sorted(report.ok.items()):
            sys.stdout.write(f"{alias} → ok ({path})\n")
        for failure in sorted(report.failures, key=lambda f: f.alias):
            sys.stdout.write(f"{failure.alias} → falha ({failure.message})\n")
        sys.stdout.write(f"{len(report.ok)} ok, {len(report.failures)} com falha\n")
        return _EXIT_OK if not report.failures else _EXIT_VALIDACAO
    try:
        path = resolve_folder_path(repository, locator, alias=args.alias)
    except FolderNotFoundError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    except _EXIT_AMBIENTE_ERRORS as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_AMBIENTE
    except PraxisForgeError as error:
        return _falha_de_registro(error)
    sys.stdout.write(f"{path}\n")
    return _EXIT_OK


def _cmd_folders_scan(
    args: argparse.Namespace,
    repository: FolderRegistryRepository,
    locator: FolderLocator,
    inspector: GitContentInspector,
) -> int:
    if args.all_aliases:
        try:
            report = scan_all_folders(repository, locator, inspector=inspector)
        except PraxisForgeError as error:
            return _falha_de_registro(error)
        for resultado in report.ok:
            sys.stdout.write(
                f"{resultado.alias} → varrida ({resultado.status.label_pt_br()}) — "
                f"conteúdo: {resultado.content_check.label_pt_br()}\n"
            )
        for failure in report.failures:
            sys.stdout.write(f"{failure.alias} → falha ({failure.message})\n")
        for grupo in report.duplicates:
            sys.stdout.write(f"duplicidade: {', '.join(grupo.aliases)} apontam pro mesmo caminho\n")
        sys.stdout.write(
            f"{len(report.ok)} ok, {len(report.failures)} com falha, "
            f"{len(report.ignored)} ignoradas\n"
        )
        revertidas = report.reverted
        detalhe = f" ({', '.join(revertidas)})" if revertidas else ""
        sys.stdout.write(f"revertidas: {len(revertidas)}{detalhe}\n")
        return _EXIT_OK if not report.failures else _EXIT_VALIDACAO
    try:
        resultado = scan_folder(repository, locator, args.alias, inspector=inspector)
    except FolderNotFoundError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    except _EXIT_AMBIENTE_ERRORS as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_AMBIENTE
    except PraxisForgeError as error:
        return _falha_de_registro(error)
    sys.stdout.write(
        f"pasta '{resultado.alias}' varrida — status: {resultado.status.label_pt_br()}, "
        f"última varredura: {_formatar_data(resultado.last_scanned)}\n"
    )
    sys.stdout.write(f"conteúdo: {resultado.content_check.label_pt_br()}\n")
    return _EXIT_OK


def _cmd_folders_bootstrap(
    args: argparse.Namespace,
    repository: FolderRegistryRepository,
    probe: RootFolderProbe,
    locator: FolderLocator,
) -> int:
    try:
        report = bootstrap_folders(repository, probe, args.root, locator=locator)
    except InvalidRootPathError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    for alias in report.registered:
        sys.stdout.write(f"{alias} → registrada\n")
    for failure in report.failures:
        sys.stdout.write(f"{failure.alias} → falha ({failure.message})\n")
    sys.stdout.write(
        f"{len(report.registered)} registradas, {len(report.skipped_existing)} já existentes, "
        f"{len(report.skipped_ignored)} ignoradas, {len(report.failures)} com falha\n"
    )
    return _EXIT_OK


def _cmd_folders_migrate(
    args: argparse.Namespace, repository: FolderRegistryRepository, locator: FolderLocator
) -> int:
    try:
        report = migrate_registry(
            repository,
            EnvLegacyPathSource(),
            locator,
            probe=FilesystemFolderProbe(),
            root=args.root,
        )
    except PraxisForgeError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    if report.already_current:
        sys.stdout.write("registro já no formato atual (v2) — nada a migrar\n")
        return _EXIT_OK
    for alias in report.migrated:
        sys.stdout.write(f"{alias} → migrada\n")
    for alias in report.removed_roots:
        sys.stdout.write(f"{alias} → removida (pasta-raiz)\n")
    for falha in report.pending:
        sys.stdout.write(f"{falha.alias} → pendente ({falha.message})\n")
    sys.stdout.write(
        f"{len(report.migrated)} migradas, {len(report.pending)} pendentes, "
        f"{len(report.removed_roots)} removidas (pasta-raiz)\n"
    )
    if not report.written:
        sys.stdout.write("nada gravado — resolva as pendências e execute de novo\n")
        return _EXIT_VALIDACAO
    sys.stdout.write("registro gravado no formato v2\n")
    return _EXIT_OK


def _cmd_folders_validate(
    args: argparse.Namespace,
    repository: FolderRegistryRepository,
    validator: JsonSchemaContractValidator,
) -> int:
    try:
        report = validate_registry(repository, validator)
    except PraxisForgeError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    for failure in report.failures:
        sys.stdout.write(f"{failure.alias}: {failure.message}\n")
    sys.stdout.write(f"{len(report.ok)} ok, {len(report.failures)} com falha\n")
    return _EXIT_OK if not report.failures else _EXIT_VALIDACAO


def _cmd_sources_validate(args: argparse.Namespace, validator: JsonSchemaContractValidator) -> int:
    arquivos: list[Path] = []
    for path in args.paths:
        if path.is_dir():
            arquivos.extend(sorted(path.glob("*.md")))
        else:
            arquivos.append(path)
    ok = 0
    falhas: list[tuple[Path, str]] = []
    for arquivo in arquivos:
        try:
            documento = read_frontmatter(arquivo)
            validator.validate(documento, schema_name="source-schema-v1")
        except (RegistryUnavailableError, ContractValidationError) as error:
            falhas.append((arquivo, str(error)))
        else:
            ok += 1
    for arquivo, motivo in falhas:
        sys.stdout.write(f"{arquivo}: {motivo}\n")
    sys.stdout.write(f"{ok} ok, {len(falhas)} com falha\n")
    return _EXIT_OK if not falhas else _EXIT_VALIDACAO


def main(argv: list[str] | None = None) -> int:
    """
    Ponto de entrada da CLI `praxisforge`.

    :param argv: argumentos de linha de comando (None usa `sys.argv[1:]`).
    :type argv: list[str] | None
    :return: código de saída (0 ok, 1 validação/negócio, 2 uso, 3 ambiente).
    :rtype: int
    """
    configure_logging()
    parser = _build_parser()
    args = parser.parse_args(argv)
    validator = JsonSchemaContractValidator(schemas_dir=_SCHEMAS_DIR)
    repository: FolderRegistryRepository = YamlFolderRegistryRepository(args.registry, validator)
    locator = FilesystemFolderLocator()

    if args.comando == "folders":
        if args.subcomando == "add":
            return _cmd_folders_add(args, repository, locator)
        if args.subcomando == "list":
            return _cmd_folders_list(args, repository)
        if args.subcomando == "show":
            return _cmd_folders_show(args, repository)
        if args.subcomando == "update":
            return _cmd_folders_update(args, repository, locator, GitCliInspector())
        if args.subcomando == "resolve":
            return _cmd_folders_resolve(args, repository, locator)
        if args.subcomando == "scan":
            return _cmd_folders_scan(args, repository, locator, GitCliInspector())
        if args.subcomando == "bootstrap":
            return _cmd_folders_bootstrap(args, repository, FilesystemFolderProbe(), locator)
        if args.subcomando == "validate":
            return _cmd_folders_validate(args, repository, validator)
        if args.subcomando == "migrate":
            return _cmd_folders_migrate(args, repository, locator)

    if args.comando == "sources" and args.subcomando == "validate":
        return _cmd_sources_validate(args, validator)

    sys.stderr.write("comando desconhecido\n")
    return _EXIT_USO


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
