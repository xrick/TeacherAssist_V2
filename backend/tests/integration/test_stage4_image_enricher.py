"""
Stage 4 Integration Test: ImageEnricher

驗證 ImageEnricher.enrich() 正確加入圖片資訊。
需要 Pexels API key。
"""

import os

import pytest

from app.pptagent_core.roles.image_enricher import ImageEnricher


@pytest.fixture
def pexels_configured():
    """檢查 Pexels API 是否配置"""
    return bool(os.getenv("PEXELS_API_KEY"))


@pytest.fixture
def sample_organized_content():
    """模擬 Stage 3 輸出 - placeholders 為 list of dicts"""
    return {
        "slides": [
            {
                "index": 0,
                "layout_index": 0,
                "layout_name": "Title Slide",
                "placeholders": [
                    {"idx": 0, "type": "CENTER_TITLE", "content": "機器學習入門"},
                    {"idx": 1, "type": "SUBTITLE", "content": "AI 基礎知識"},
                ],
                "visual_suggestion": "artificial intelligence concept",
            },
            {
                "index": 1,
                "layout_index": 1,
                "layout_name": "Content",
                "placeholders": [
                    {"idx": 0, "type": "TITLE", "content": "監督式學習"},
                    {"idx": 1, "type": "BODY", "content": "從標記資料學習"},
                ],
                "visual_suggestion": "data analysis chart",
            },
        ]
    }


@pytest.fixture
def sample_draft_content():
    """模擬 Stage 2 輸出"""
    return {
        "slides": [
            {"title": "機器學習入門", "visual_suggestion": "artificial intelligence"},
            {"title": "監督式學習", "visual_suggestion": "data analysis"},
        ]
    }


class TestStage4ImageEnricher:
    """Stage 4: ImageEnricher 輸出驗證"""

    @pytest.mark.asyncio
    async def test_enrich_adds_images_field(
        self, pexels_configured, sample_organized_content, sample_draft_content
    ):
        """測試 enrich() 加入 images 欄位"""
        if not pexels_configured:
            pytest.skip("Pexels API key 未配置")

        enricher = ImageEnricher()
        result = await enricher.enrich(
            organized_content=sample_organized_content,
            draft_content=sample_draft_content,
        )

        for i, slide in enumerate(result["slides"]):
            assert "images" in slide, f"Slide {i} 缺少 images 欄位"

    @pytest.mark.asyncio
    async def test_enrich_preserves_original_content(
        self, pexels_configured, sample_organized_content, sample_draft_content
    ):
        """測試 enrich() 保留原始內容"""
        if not pexels_configured:
            pytest.skip("Pexels API key 未配置")

        enricher = ImageEnricher()
        result = await enricher.enrich(
            organized_content=sample_organized_content,
            draft_content=sample_draft_content,
        )

        for i, slide in enumerate(result["slides"]):
            assert "placeholders" in slide, f"Slide {i} 遺失 placeholders"
            assert "layout_index" in slide, f"Slide {i} 遺失 layout_index"

    @pytest.mark.asyncio
    async def test_images_have_url(
        self, pexels_configured, sample_organized_content, sample_draft_content
    ):
        """測試 images 包含 URL"""
        if not pexels_configured:
            pytest.skip("Pexels API key 未配置")

        enricher = ImageEnricher()
        result = await enricher.enrich(
            organized_content=sample_organized_content,
            draft_content=sample_draft_content,
        )

        slides_with_image_url = 0
        for slide in result["slides"]:
            images = slide.get("images", [])
            if images and any(img.get("url") for img in images):
                slides_with_image_url += 1

        assert slides_with_image_url > 0, "至少一個 slide 應有圖片 URL"

    @pytest.mark.asyncio
    async def test_enrich_without_api_returns_empty_images(
        self, sample_organized_content, sample_draft_content
    ):
        """測試無 API 時回傳空 images（優雅降級）"""
        original_key = os.environ.pop("PEXELS_API_KEY", None)

        try:
            enricher = ImageEnricher()
            result = await enricher.enrich(
                organized_content=sample_organized_content,
                draft_content=sample_draft_content,
            )

            assert "slides" in result, "應回傳 slides"
            for slide in result["slides"]:
                images = slide.get("images", [])
                assert isinstance(images, list), "images 應為 list"
        finally:
            if original_key:
                os.environ["PEXELS_API_KEY"] = original_key
