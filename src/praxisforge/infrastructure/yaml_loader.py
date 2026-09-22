# -*- coding: utf-8 -*-
"""
NOME: yaml_loader.py
TITULO: SafeLoader compartilhado sem resolvedor implícito de timestamp
DATA: 22/09/2026 10:35
MODIFICADO: 22/09/2026 10:07
VERSÃO: 0.1.0
DEPEND: pyyaml
HISTÓRICO:
    - 22/09/2026 10:35: extraído de yaml_folder_registry.py para ser compartilhado
      também por source_frontmatter.py (research.md D16)
STATUS: DEV
"""

import yaml


class NoTimestampSafeLoader(yaml.SafeLoader):
    """SafeLoader sem o resolvedor implícito de timestamp (datas ficam como str)."""


NoTimestampSafeLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
