# -*- coding: utf-8 -*-
"""
NOME: cli.py
TITULO: CLI `praxisforge` — argparse; ponto de composição das dependências
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 10:10
VERSÃO: 0.1.0
DEPEND: praxisforge.application, praxisforge.infrastructure (só aqui, ponto de composição)
HISTÓRICO:
    - 22/09/2026 09:45: criação (T038) — subcomandos folders add|list|show|update
STATUS: DEV
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from praxisforge.application.dto import RegisterFolderInput, UpdateFolderInput
from praxisforge.application.errors import (
    ContractValidationError,
    FolderNotFoundError,
    FolderPathInvalidError,
    FolderPathNotConfiguredError,
    FolderPathUnreadableError,
    PraxisForgeError,
    RegistryUnavailableError,
)
from praxisforge.application.ports import FolderRegistryRepository, PathResolver
from praxisforge.application.query_folders import list_folders, show_folder
from praxisforge.application.register_folder import register_folder
from praxisforge.application.resolve_folder_path import (
    resolve_all_folder_paths,
    resolve_folder_path,
)
from praxisforge.application.update_folder import update_folder
from praxisforge.application.validate_registry import validate_registry
from praxisforge.infrastructure.env_path_resolver import EnvPathResolver
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from praxisforge.infrastructure.logging_setup import configure_logging
from praxisforge.infrastructure.source_frontmatter import read_frontmatter
from praxisforge.infrastructure.yaml_folder_registry import YamlFolderRegistryRepository

_EXIT_AMBIENTE_ERRORS = (
    FolderPathNotConfiguredError,
    FolderPathInvalidError,
    FolderPathUnreadableError,
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

    list_parser = folders_sub.add_parser("list")
    list_parser.add_argument("--status", default=None)

    show_parser = folders_sub.add_parser("show")
    show_parser.add_argument("alias")

    update_parser = folders_sub.add_parser("update")
    update_parser.add_argument("alias")
    update_parser.add_argument("--status", default=None)
    update_parser.add_argument("--last-scanned", default=None)
    update_parser.add_argument("--license", default=None)

    resolve_parser = folders_sub.add_parser("resolve")
    resolve_group = resolve_parser.add_mutually_exclusive_group(required=True)
    resolve_group.add_argument("alias", nargs="?", default=None)
    resolve_group.add_argument("--all", action="store_true", dest="all_aliases")

    folders_sub.add_parser("validate")

    sources = subparsers.add_parser("sources")
    sources_sub = sources.add_subparsers(dest="subcomando", required=True)
    sources_validate_parser = sources_sub.add_parser("validate")
    sources_validate_parser.add_argument("paths", nargs="+", type=Path)

    return parser


def _cmd_folders_add(args: argparse.Namespace, repository: FolderRegistryRepository) -> int:
    try:
        data = RegisterFolderInput(
            alias=args.alias,
            description=args.description,
            content_type=args.content_type,
            license=args.license,
            status=args.status,
        )
    except ValidationError as error:
        sys.stderr.write(f"argumentos inválidos: {error}\n")
        return _EXIT_USO
    try:
        result = register_folder(repository, data)
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
            f"{folder.status.label_pt_br()}\t{_formatar_data(folder.last_scanned)}\n"
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
    return _EXIT_OK


def _cmd_folders_update(args: argparse.Namespace, repository: FolderRegistryRepository) -> int:
    try:
        data = UpdateFolderInput(
            alias=args.alias,
            status=args.status,
            last_scanned=args.last_scanned,
            license=args.license,
        )
    except ValidationError as error:
        sys.stderr.write(f"argumentos inválidos: {error}\n")
        return _EXIT_USO
    try:
        update_folder(repository, data)
    except PraxisForgeError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    sys.stdout.write(f"pasta '{args.alias}' atualizada\n")
    return _EXIT_OK


def _cmd_folders_resolve(
    args: argparse.Namespace, repository: FolderRegistryRepository, resolver: PathResolver
) -> int:
    if args.all_aliases:
        report = resolve_all_folder_paths(repository, resolver)
        for alias, path in sorted(report.ok.items()):
            sys.stdout.write(f"{alias} → ok ({path})\n")
        for failure in sorted(report.failures, key=lambda f: f.alias):
            sys.stdout.write(f"{failure.alias} → falha ({failure.message})\n")
        sys.stdout.write(f"{len(report.ok)} ok, {len(report.failures)} com falha\n")
        return _EXIT_OK if not report.failures else _EXIT_VALIDACAO
    try:
        path = resolve_folder_path(repository, resolver, alias=args.alias)
    except FolderNotFoundError as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_VALIDACAO
    except _EXIT_AMBIENTE_ERRORS as error:
        sys.stderr.write(f"{error}\n")
        return _EXIT_AMBIENTE
    sys.stdout.write(f"{path}\n")
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

    if args.comando == "folders":
        if args.subcomando == "add":
            return _cmd_folders_add(args, repository)
        if args.subcomando == "list":
            return _cmd_folders_list(args, repository)
        if args.subcomando == "show":
            return _cmd_folders_show(args, repository)
        if args.subcomando == "update":
            return _cmd_folders_update(args, repository)
        if args.subcomando == "resolve":
            return _cmd_folders_resolve(args, repository, EnvPathResolver())
        if args.subcomando == "validate":
            return _cmd_folders_validate(args, repository, validator)

    if args.comando == "sources" and args.subcomando == "validate":
        return _cmd_sources_validate(args, validator)

    sys.stderr.write("comando desconhecido\n")
    return _EXIT_USO


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
