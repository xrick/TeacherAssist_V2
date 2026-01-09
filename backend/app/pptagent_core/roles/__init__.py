"""
PPTAgent Roles

四階段流程 (V2)：
1. TemplateAnalyzer - 分析 Template 結構
2. ContentGenerator - LLM 擴展使用者輸入
3. ContentOrganizerV2 - 組織內容到 Template 結構
4. SlideBuilder - 建構最終 PPTX

舊五階段流程（保留向後相容）：
1. SchemaExtractor
2. ContentOrganizer
3. LayoutSelector
4. Editor
5. Coder
"""

# 新四階段流程
from app.pptagent_core.roles.coder import Coder
from app.pptagent_core.roles.content_generator import ContentGenerator
from app.pptagent_core.roles.content_organizer import ContentOrganizer
from app.pptagent_core.roles.content_organizer_v2 import ContentOrganizerV2
from app.pptagent_core.roles.editor import Editor
from app.pptagent_core.roles.layout_selector import LayoutSelector

# 舊流程（向後相容）
from app.pptagent_core.roles.schema_extractor import SchemaExtractor
from app.pptagent_core.roles.slide_builder import SlideBuilder
from app.pptagent_core.roles.template_analyzer import TemplateAnalyzer

__all__ = [
    # 新四階段流程
    "TemplateAnalyzer",
    "ContentGenerator",
    "ContentOrganizerV2",
    "SlideBuilder",
    # 舊流程
    "SchemaExtractor",
    "ContentOrganizer",
    "LayoutSelector",
    "Editor",
    "Coder",
]
