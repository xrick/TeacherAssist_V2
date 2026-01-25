"""
Stage 2 Integration Test: ContentGenerator

驗證 ContentGenerator.generate() 輸出符合 Stage 3 (ContentOrganizerV2) 期望的資料結構。
使用真實 LLM 呼叫 (Ollama)。
"""

import pytest

from app.pptagent_core.roles.content_generator import ContentGenerator
from app.services.llm_service import get_llm_service

TEST_INPUT = """
# 機器學習入門

機器學習是 AI 的子領域，讓電腦從資料學習。

## 類型
1. 監督式學習
2. 非監督式學習
3. 強化學習
"""


@pytest.fixture
def generator():
    """取得 ContentGenerator 實例"""
    llm = get_llm_service()
    return ContentGenerator(llm)


class TestStage2ContentGenerator:
    """Stage 2: ContentGenerator 輸出驗證"""

    @pytest.mark.asyncio
    async def test_generate_returns_slides_array(self, generator: ContentGenerator):
        """測試 generate() 回傳 slides 陣列"""
        result = await generator.generate(
            user_input=TEST_INPUT,
            slide_count=5,
            language="zh-TW",
        )

        assert "slides" in result, "缺少 slides 欄位"
        assert isinstance(result["slides"], list), "slides 應為 list"
        assert len(result["slides"]) > 0, "slides 不應為空"

    @pytest.mark.asyncio
    async def test_each_slide_has_required_fields(self, generator: ContentGenerator):
        """測試每個 slide 有必要欄位"""
        result = await generator.generate(
            user_input=TEST_INPUT,
            slide_count=5,
            language="zh-TW",
        )

        required_fields = ["title", "slide_type"]

        for i, slide in enumerate(result["slides"]):
            for field in required_fields:
                assert field in slide, f"Slide {i} 缺少 {field}"

    @pytest.mark.asyncio
    async def test_slides_have_visual_suggestion(self, generator: ContentGenerator):
        """測試 slides 包含 visual_suggestion（供 ImageEnricher 使用）"""
        result = await generator.generate(
            user_input=TEST_INPUT,
            slide_count=5,
            language="zh-TW",
        )

        slides_with_visual = sum(1 for s in result["slides"] if s.get("visual_suggestion"))
        assert slides_with_visual > 0, "應至少有一個 slide 包含 visual_suggestion"

    @pytest.mark.asyncio
    async def test_slide_types_are_valid(self, generator: ContentGenerator):
        """測試 slide_type 為有效值"""
        result = await generator.generate(
            user_input=TEST_INPUT,
            slide_count=5,
            language="zh-TW",
        )

        valid_types = {"title", "content", "section", "closing", "image", "comparison", "timeline"}

        for i, slide in enumerate(result["slides"]):
            slide_type = slide.get("slide_type", "").lower()
            assert any(vt in slide_type for vt in valid_types), (
                f"Slide {i} 有無效的 slide_type: {slide_type}"
            )

    @pytest.mark.asyncio
    async def test_presentation_title_exists(self, generator: ContentGenerator):
        """測試回傳包含簡報標題"""
        result = await generator.generate(
            user_input=TEST_INPUT,
            slide_count=5,
            language="zh-TW",
        )

        assert "presentation_title" in result or result["slides"][0].get("slide_type") == "title", (
            "應有 presentation_title 或 title slide"
        )

    @pytest.mark.asyncio
    async def test_content_reflects_input_topic(self, generator: ContentGenerator):
        """測試生成內容反映輸入主題"""
        result = await generator.generate(
            user_input=TEST_INPUT,
            slide_count=5,
            language="zh-TW",
        )

        all_text = " ".join(str(slide) for slide in result["slides"])
        keywords = ["機器學習", "學習", "AI", "監督", "非監督"]

        found = [kw for kw in keywords if kw in all_text]
        assert len(found) >= 2, f"內容應包含主題關鍵字，找到: {found}"
