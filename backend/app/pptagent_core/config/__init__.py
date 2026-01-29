"""Config module for pptagent_core"""

from .template_config import (
    PlaceholderMapping,
    StructureRules,
    TemplateConfig,
    TemplateConfigLoader,
    get_template_config,
)

__all__ = [
    "TemplateConfig",
    "TemplateConfigLoader",
    "StructureRules",
    "PlaceholderMapping",
    "get_template_config",
]
