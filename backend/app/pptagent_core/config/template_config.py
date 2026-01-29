"""
Template Config Loader

讀取 sys_template_config.json v0.2 格式，提供：
- structure_rules: opening, agenda, closing, body_pool
- placeholders: 每個 layout 的 placeholder idx 映射
- prompt_path: 動態 prompt 載入路徑
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StructureRules:
    """Layout 結構規則"""

    opening: int = 0  # 開場頁 layout index
    agenda: int = 2  # 議程頁 layout index
    closing: int = 0  # 結尾頁 layout index
    body_pool: list[int] = field(default_factory=lambda: [2])  # 內容頁輪替池


@dataclass
class PlaceholderMapping:
    """Placeholder idx 映射"""

    title: int = 0
    body: int = 1
    picture: int | None = None


@dataclass
class TemplateConfig:
    """單一 Template 的完整配置"""

    name: str
    file_path: str
    prompt_path: str
    total_layouts: int
    structure_rules: StructureRules
    placeholders_standard: PlaceholderMapping
    placeholders_exceptions: dict[int, PlaceholderMapping] = field(default_factory=dict)

    def get_placeholder_mapping(self, layout_index: int) -> PlaceholderMapping:
        """取得特定 layout 的 placeholder 映射"""
        if layout_index in self.placeholders_exceptions:
            return self.placeholders_exceptions[layout_index]
        return self.placeholders_standard

    def get_body_layout(self, slide_index: int) -> int:
        """根據 slide index 從 body_pool 輪替選擇 layout"""
        pool = self.structure_rules.body_pool
        if not pool:
            return 2  # fallback
        return pool[slide_index % len(pool)]


class TemplateConfigLoader:
    """
    Template Config 載入器

    支援 sys_template_config.json v0.2 格式：
    {
      "version": "0.2",
      "default_template": "education_basic",
      "templates": {
        "education_basic": { ... }
      }
    }
    """

    _instance: "TemplateConfigLoader | None" = None
    _config_cache: dict[str, Any] | None = None

    def __new__(cls, config_path: Path | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Path | None = None):
        if self._initialized:
            return

        if config_path is None:
            # 預設路徑
            config_path = (
                Path(__file__).parent.parent.parent.parent / "data" / "sys_template_config.json"
            )

        self.config_path = config_path
        self._load_config()
        self._initialized = True

    def _load_config(self) -> None:
        """載入並解析 config 檔案"""
        if not self.config_path.exists():
            logger.warning(f"Config 不存在: {self.config_path}, 使用預設值")
            self._config_cache = self._default_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config_cache = json.load(f)
            logger.info(f"載入 Template Config v{self._config_cache.get('version', '?')}")
        except Exception as e:
            logger.error(f"Config 載入失敗: {e}")
            self._config_cache = self._default_config()

    def _default_config(self) -> dict[str, Any]:
        """預設配置（v0.2 格式）"""
        return {
            "version": "0.2",
            "default_template": "education_basic",
            "templates": {
                "education_basic": {
                    "file_path": "templates/education_basic.pptx",
                    "prompt_path": "prompts/default.md",
                    "total_layouts": 12,
                    "structure_rules": {"opening": 0, "agenda": 2, "closing": 0, "body_pool": [2]},
                    "placeholders": {"standard": {"title": 0, "body": 1}, "exceptions": {}},
                }
            },
        }

    @property
    def version(self) -> str:
        return self._config_cache.get("version", "0.1")

    @property
    def default_template_name(self) -> str:
        return self._config_cache.get("default_template", "education_basic")

    def get_template_names(self) -> list[str]:
        """取得所有可用的 template 名稱"""
        return list(self._config_cache.get("templates", {}).keys())

    def get_template_config(self, template_name: str | None = None) -> TemplateConfig:
        """
        取得指定 template 的配置

        Args:
            template_name: Template 名稱，None 則使用 default

        Returns:
            TemplateConfig 物件
        """
        if template_name is None:
            template_name = self.default_template_name

        templates = self._config_cache.get("templates", {})

        if template_name not in templates:
            logger.warning(f"Template '{template_name}' 不存在，使用 default")
            template_name = self.default_template_name
            if template_name not in templates:
                # 使用第一個可用的
                template_name = next(iter(templates.keys()))

        raw = templates[template_name]

        # 解析 structure_rules
        sr_raw = raw.get("structure_rules", {})
        structure_rules = StructureRules(
            opening=sr_raw.get("opening", 0),
            agenda=sr_raw.get("agenda", 2),
            closing=sr_raw.get("closing", 0),
            body_pool=sr_raw.get("body_pool", [2]),
        )

        # 解析 placeholders
        ph_raw = raw.get("placeholders", {})
        std_raw = ph_raw.get("standard", {})
        placeholders_standard = PlaceholderMapping(
            title=std_raw.get("title", 0),
            body=std_raw.get("body", 1),
            picture=std_raw.get("picture"),
        )

        # 解析 exceptions
        exc_raw = ph_raw.get("exceptions", {})
        placeholders_exceptions = {}
        for layout_idx_str, exc_ph in exc_raw.items():
            layout_idx = int(layout_idx_str)
            placeholders_exceptions[layout_idx] = PlaceholderMapping(
                title=exc_ph.get("title", 0),
                body=exc_ph.get("body", 1),
                picture=exc_ph.get("picture"),
            )

        return TemplateConfig(
            name=template_name,
            file_path=raw.get("file_path", f"templates/{template_name}.pptx"),
            prompt_path=raw.get("prompt_path", "prompts/default.md"),
            total_layouts=raw.get("total_layouts", 12),
            structure_rules=structure_rules,
            placeholders_standard=placeholders_standard,
            placeholders_exceptions=placeholders_exceptions,
        )

    def reload(self) -> None:
        """重新載入 config（用於熱更新）"""
        self._load_config()


# 全域函式
def get_template_config(template_name: str | None = None) -> TemplateConfig:
    """取得 Template 配置的便捷函式"""
    loader = TemplateConfigLoader()
    return loader.get_template_config(template_name)
