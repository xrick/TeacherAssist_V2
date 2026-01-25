"""
Stage 3 Integration Test: ContentOrganizerV2

驗證 ContentOrganizerV2.organize() 正確整合 Stage 1 和 Stage 2 的輸出。
"""

from pathlib import Path

import pytest

from app.pptagent_core.roles.content_generator import ContentGenerator
from app.pptagent_core.roles.content_organizer_v2 import ContentOrganizerV2
from app.pptagent_core.roles.template_analyzer import TemplateAnalyzer
from app.services.llm_service import get_llm_service

TEST_INPUT = """
# 機器學習入門
機器學習讓電腦從資料學習。
"""


@pytest.fixture
def llm_service():
    return get_llm_service()


@pytest.fixture
def template_structure():
    """取得 Stage 1 輸出"""
    template_path = Path(__file__).parent.parent.parent / "data" / "templates" / "modern_clean.pptx"
    if not template_path.exists():
        pytest.skip(f"Template 不存在: {template_path}")
    analyzer = TemplateAnalyzer(template_path)
    return analyzer.analyze(slide_count=5, include_title=True, include_closing=True)


@pytest.fixture
async def draft_content(llm_service):
    """取得 Stage 2 輸出"""
    generator = ContentGenerator(llm_service)
    return await generator.generate(
        user_input=TEST_INPUT,
        slide_count=5,
        language="zh-TW",
    )


class TestStage3ContentOrganizer:
    """Stage 3: ContentOrganizerV2 輸出驗證"""

    @pytest.mark.asyncio
    async def test_organize_returns_slides_array(
        self, llm_service, template_structure, draft_content
    ):
        """測試 organize() 回傳 slides 陣列"""
        organizer = ContentOrganizerV2(llm_service)
        result = await organizer.organize(
            draft_content=draft_content,
            template_structure=template_structure,
        )

        assert "slides" in result, "缺少 slides 欄位"
        assert isinstance(result["slides"], list), "slides 應為 list"
        assert len(result["slides"]) > 0, "slides 不應為空"

    @pytest.mark.asyncio
    async def test_each_slide_has_layout_info(self, llm_service, template_structure, draft_content):
        """測試每個 slide 有 layout 資訊"""
        organizer = ContentOrganizerV2(llm_service)
        result = await organizer.organize(
            draft_content=draft_content,
            template_structure=template_structure,
        )

        for i, slide in enumerate(result["slides"]):
            assert "layout_index" in slide, f"Slide {i} 缺少 layout_index"
            assert "layout_name" in slide, f"Slide {i} 缺少 layout_name"

    @pytest.mark.asyncio
    async def test_each_slide_has_placeholders(
        self, llm_service, template_structure, draft_content
    ):
        """測試每個 slide 有 placeholders"""
        organizer = ContentOrganizerV2(llm_service)
        result = await organizer.organize(
            draft_content=draft_content,
            template_structure=template_structure,
        )

        for i, slide in enumerate(result["slides"]):
            assert "placeholders" in slide, f"Slide {i} 缺少 placeholders"

    @pytest.mark.asyncio
    async def test_placeholders_have_content(self, llm_service, template_structure, draft_content):
        """測試 placeholders 有內容"""
        organizer = ContentOrganizerV2(llm_service)
        result = await organizer.organize(
            draft_content=draft_content,
            template_structure=template_structure,
        )

        slides_with_content = 0
        for slide in result["slides"]:
            placeholders = slide.get("placeholders", {})
            if isinstance(placeholders, dict):
                has_content = any(v for v in placeholders.values() if v)
            else:
                has_content = len(placeholders) > 0
            if has_content:
                slides_with_content += 1

        assert slides_with_content > 0, "至少一個 slide 應有 placeholder 內容"

    @pytest.mark.asyncio
    async def test_layout_index_is_valid(self, llm_service, template_structure, draft_content):
        """測試 layout_index 在有效範圍內"""
        organizer = ContentOrganizerV2(llm_service)
        result = await organizer.organize(
            draft_content=draft_content,
            template_structure=template_structure,
        )

        max_layout = len(template_structure.get("slides", [])) - 1
        if max_layout < 0:
            max_layout = 10

        for i, slide in enumerate(result["slides"]):
            layout_idx = slide.get("layout_index", 0)
            assert 0 <= layout_idx <= max_layout, (
                f"Slide {i} layout_index {layout_idx} 超出範圍 [0, {max_layout}]"
            )
