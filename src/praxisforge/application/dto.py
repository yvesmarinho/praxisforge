# -*- coding: utf-8 -*-
"""
NOME: dto.py
TITULO: DTOs pydantic de entrada dos casos de uso (fronteira Application/CLI)
DATA: 22/09/2026 09:45
MODIFICADO: 25/09/2026 09:52
VERSÃO: 0.1.0
DEPEND: pydantic
HISTÓRICO:
    - 22/09/2026 09:45: criação (T025) — faz tests/unit/application/test_dto.py passar
    - 23/09/2026 16:54: path em RegisterFolderInput/UpdateFolderInput (T024, feature 005)
    - 25/09/2026 09:52: folders update --description
STATUS: DEV
"""

from pydantic import BaseModel, ConfigDict, Field

_ALIAS_PATTERN = r"^[a-z][a-z0-9_]{1,62}$"


class RegisterFolderInput(BaseModel):
    """
    Entrada validada do caso de uso `register_folder`.

    :param alias: identificador único da pasta.
    :type alias: str
    :param description: descrição não vazia.
    :type description: str
    :param content_type: slug do tipo de conteúdo.
    :type content_type: str
    :param license: identificador SPDX ou `"unknown"`.
    :type license: str
    :param status: status inicial (opcional; padrão decidido pelo caso de uso).
    :type status: str | None
    :param path: caminho da pasta como informado (canonizado pelo caso de uso).
    :type path: str
    """

    model_config = ConfigDict(strict=True)

    alias: str = Field(pattern=_ALIAS_PATTERN)
    description: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    license: str = Field(min_length=1)  # noqa: A003
    status: str | None = None
    path: str = Field(min_length=1)


class UpdateFolderInput(BaseModel):
    """
    Entrada validada do caso de uso `update_folder`.

    :param alias: identificador da pasta a atualizar.
    :type alias: str
    :param status: novo status, se informado.
    :type status: str | None
    :param last_scanned: nova data ISO 8601, se informada.
    :type last_scanned: str | None
    :param license: nova licença, se informada.
    :type license: str | None
    :param path: novo caminho da pasta, se informado (pasta movida — FR-016).
    :type path: str | None
    :param description: nova descrição, se informada (1 a 500 caracteres).
    :type description: str | None
    """

    model_config = ConfigDict(strict=True)

    alias: str = Field(pattern=_ALIAS_PATTERN)
    status: str | None = None
    last_scanned: str | None = None
    license: str | None = None  # noqa: A003
    path: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1, max_length=500)
