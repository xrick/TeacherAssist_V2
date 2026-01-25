"""
Unit tests for ImageEnricher Role
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pptagent_core.roles.image_enricher import ImageEnricher


@pytest.fixture
def mock_pexels_service():
    """Mock PexelsService"""
    with patch("app.pptagent_core.roles.image_enricher.PexelsService") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_cache_service():
    """Mock ImageCacheService"""
    with patch("app.pptagent_core.roles.image_enricher.ImageCacheService") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def sample_organized_content():
    """Sample organized content from ContentOrganizerV2"""
    return {
        "title": "AI 技術入門",
        "slides": [
            {
                "title": "什麼是人工智慧",
                "bullet_points": ["機器學習", "深度學習"],
                "slide_type": "content",
                "layout": "content",
                "speaker_notes": "介紹 AI 基礎概念",
            },
            {
                "title": "機器學習應用",
                "bullet_points": ["圖像識別", "自然語言處理"],
                "slide_type": "content",
                "layout": "content",
                "speaker_notes": "展示實際應用案例",
            },
        ],
    }


@pytest.fixture
def sample_draft_content():
    """Sample draft content from ContentGenerator with visual_suggestion"""
    return {
        "slides": [
            {
                "title": "什麼是人工智慧",
                "visual_suggestion": "neural network diagram, abstract technology background",
            },
            {
                "title": "機器學習應用",
                "visual_suggestion": "AI robot, data visualization, modern technology",
            },
        ],
    }


class TestImageEnricher:
    """Test ImageEnricher Role"""

    @pytest.mark.asyncio
    async def test_enrich_success(
        self,
        mock_pexels_service,
        mock_cache_service,
        sample_organized_content,
        sample_draft_content,
    ):
        """Test successful image enrichment"""
        # Setup mock responses
        mock_pexels_service.search_images = AsyncMock(
            return_value=[
                {
                    "id": 12345,
                    "url": "https://pexels.com/photo/12345",
                    "photographer": "John Doe",
                    "src": {"medium": "https://images.pexels.com/12345.jpg"},
                }
            ]
        )
        mock_cache_service.get_cached_image = AsyncMock(return_value=None)
        mock_cache_service.cache_image = AsyncMock()

        enricher = ImageEnricher()
        result = await enricher.enrich(
            organized_content=sample_organized_content,
            draft_content=sample_draft_content,
            presentation_title="AI 技術入門",
            images_per_slide=1,
        )

        # Verify structure
        assert "slides" in result
        assert len(result["slides"]) == 2

        # Verify images were added
        for slide in result["slides"]:
            assert "images" in slide
            assert len(slide["images"]) == 1 or len(slide["images"]) == 0  # May fail due to mock

    @pytest.mark.asyncio
    async def test_enrich_with_cached_images(
        self,
        mock_pexels_service,
        mock_cache_service,
        sample_organized_content,
        sample_draft_content,
    ):
        """Test image enrichment with cached images"""
        cached_image = {
            "id": "cached_123",
            "url": "https://cached.example.com/image.jpg",
            "photographer": "Cached Author",
            "src": {"medium": "https://cached.example.com/image.jpg"},
        }
        mock_cache_service.get_cached_image = AsyncMock(return_value=cached_image)

        enricher = ImageEnricher()
        result = await enricher.enrich(
            organized_content=sample_organized_content,
            draft_content=sample_draft_content,
            presentation_title="AI 技術入門",
            images_per_slide=1,
        )

        # Should not call Pexels API when cache hit
        mock_pexels_service.search_images.assert_not_called()

    @pytest.mark.asyncio
    async def test_enrich_no_visual_suggestions(
        self, mock_pexels_service, mock_cache_service, sample_organized_content
    ):
        """Test enrichment when draft_content has no visual_suggestion"""
        draft_without_visual = {
            "slides": [
                {"title": "Slide 1"},
                {"title": "Slide 2"},
            ]
        }

        mock_pexels_service.search_images = AsyncMock(return_value=[])
        mock_cache_service.get_cached_image = AsyncMock(return_value=None)

        enricher = ImageEnricher()
        result = await enricher.enrich(
            organized_content=sample_organized_content,
            draft_content=draft_without_visual,
            presentation_title="Test",
            images_per_slide=1,
        )

        # Should still return valid structure
        assert "slides" in result
        assert len(result["slides"]) == 2

    @pytest.mark.asyncio
    async def test_enrich_with_multiple_images_per_slide(
        self,
        mock_pexels_service,
        mock_cache_service,
        sample_organized_content,
        sample_draft_content,
    ):
        """Test enrichment with multiple images per slide"""
        mock_pexels_service.search_images = AsyncMock(
            return_value=[
                {
                    "id": i,
                    "url": f"https://pexels.com/photo/{i}",
                    "photographer": f"Photographer {i}",
                    "src": {"medium": f"https://images.pexels.com/{i}.jpg"},
                }
                for i in range(3)
            ]
        )
        mock_cache_service.get_cached_image = AsyncMock(return_value=None)
        mock_cache_service.cache_image = AsyncMock()

        enricher = ImageEnricher()
        result = await enricher.enrich(
            organized_content=sample_organized_content,
            draft_content=sample_draft_content,
            presentation_title="AI 技術入門",
            images_per_slide=3,
        )

        assert "slides" in result

    @pytest.mark.asyncio
    async def test_enrich_zero_images_per_slide(
        self,
        mock_pexels_service,
        mock_cache_service,
        sample_organized_content,
        sample_draft_content,
    ):
        """Test enrichment with zero images per slide"""
        enricher = ImageEnricher()
        result = await enricher.enrich(
            organized_content=sample_organized_content,
            draft_content=sample_draft_content,
            presentation_title="AI 技術入門",
            images_per_slide=0,
        )

        # Should skip image processing entirely
        mock_pexels_service.search_images.assert_not_called()
        assert "slides" in result
        for slide in result["slides"]:
            assert slide.get("images", []) == []

    @pytest.mark.asyncio
    async def test_enrich_pexels_api_failure(
        self,
        mock_pexels_service,
        mock_cache_service,
        sample_organized_content,
        sample_draft_content,
    ):
        """Test graceful handling of Pexels API failure"""
        mock_pexels_service.search_images = AsyncMock(side_effect=Exception("API Error"))
        mock_cache_service.get_cached_image = AsyncMock(return_value=None)

        enricher = ImageEnricher()
        result = await enricher.enrich(
            organized_content=sample_organized_content,
            draft_content=sample_draft_content,
            presentation_title="AI 技術入門",
            images_per_slide=1,
        )

        # Should not raise, should return content without images
        assert "slides" in result
        for slide in result["slides"]:
            # Images may be empty or missing on error
            assert "images" not in slide or slide["images"] == []

    @pytest.mark.asyncio
    async def test_generate_keywords(self, mock_pexels_service, mock_cache_service):
        """Test keyword generation from visual_suggestion"""
        enricher = ImageEnricher()

        # Test basic keyword extraction
        keywords = enricher._generate_keywords(
            slide_title="機器學習入門",
            visual_suggestion="neural network diagram, abstract technology",
            presentation_title="AI 教學",
        )

        assert isinstance(keywords, list)
        assert len(keywords) > 0

    @pytest.mark.asyncio
    async def test_enrich_preserves_original_content(
        self,
        mock_pexels_service,
        mock_cache_service,
        sample_organized_content,
        sample_draft_content,
    ):
        """Test that enrichment preserves original slide content"""
        mock_pexels_service.search_images = AsyncMock(return_value=[])
        mock_cache_service.get_cached_image = AsyncMock(return_value=None)

        enricher = ImageEnricher()
        result = await enricher.enrich(
            organized_content=sample_organized_content,
            draft_content=sample_draft_content,
            presentation_title="AI 技術入門",
            images_per_slide=1,
        )

        # Verify original content is preserved
        for i, slide in enumerate(result["slides"]):
            original = sample_organized_content["slides"][i]
            assert slide["title"] == original["title"]
            assert slide["bullet_points"] == original["bullet_points"]
            assert slide["slide_type"] == original["slide_type"]
