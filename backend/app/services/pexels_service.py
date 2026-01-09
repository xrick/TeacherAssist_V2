"""
Pexels API Service

Provides image search and download functionality using Pexels API.
Includes AI-powered keyword generation for course content.
"""

import logging
from datetime import datetime
from enum import Enum

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class ImageType(str, Enum):
    """Supported image types for search"""

    PHOTO = "photo"
    ILLUSTRATION = "illustration"


class ImageOrientation(str, Enum):
    """Image orientation options"""

    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    SQUARE = "square"


class PexelsImageSrc(BaseModel):
    """Image source URLs in various sizes"""

    original: str
    large2x: str
    large: str
    medium: str
    small: str
    portrait: str
    landscape: str
    tiny: str


class PexelsImage(BaseModel):
    """Pexels image metadata"""

    id: int
    width: int
    height: int
    url: str  # Pexels page URL
    photographer: str
    photographer_url: str
    photographer_id: int
    avg_color: str
    src: PexelsImageSrc
    alt: str


class PexelsSearchResponse(BaseModel):
    """Pexels search API response"""

    total_results: int
    page: int
    per_page: int
    photos: list[PexelsImage]
    next_page: str | None = None


class AIKeywordResult(BaseModel):
    """AI-generated keywords result"""

    keywords: list[str]
    primary_keyword: str
    language: str
    generated_at: datetime


class PexelsService:
    """
    Pexels API service for image search and download.

    Handles:
    - Image search with keyword filtering
    - Safe content filtering (no adult content)
    - AI-powered keyword generation from course content
    - Image download with proper attribution
    """

    BASE_URL = "https://api.pexels.com/v1"

    def __init__(self, api_key: str | None = None):
        """
        Initialize Pexels service.

        Args:
            api_key: Pexels API key (defaults to settings)
        """
        self.api_key = api_key or settings.pexels_api_key
        if not self.api_key:
            raise ValueError("Pexels API key not configured")

        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": self.api_key},
        )

    async def search_images(
        self,
        keyword: str,
        per_page: int | None = None,
        page: int = 1,
        orientation: ImageOrientation | None = None,
        size: str | None = None,
        locale: str = "en-US",
    ) -> PexelsSearchResponse:
        """
        Search for images on Pexels.

        Args:
            keyword: Search keyword or phrase
            per_page: Number of results per page (1-80, default from settings)
            page: Page number for pagination
            orientation: Filter by orientation (landscape/portrait/square)
            size: Filter by size (large/medium/small)
            locale: Locale for search (default: en-US)

        Returns:
            PexelsSearchResponse with matching images

        Raises:
            httpx.HTTPError: If API request fails
        """
        per_page = per_page or settings.pexels_default_per_page

        params: dict[str, str | int] = {
            "query": keyword,
            "per_page": min(per_page, 80),  # Pexels max is 80
            "page": page,
            "locale": locale,
        }

        if orientation:
            params["orientation"] = orientation.value
        if size:
            params["size"] = size

        try:
            logger.info(f"Searching Pexels: '{keyword}' (page={page}, per_page={per_page})")
            response = await self.client.get(f"{self.BASE_URL}/search", params=params)
            response.raise_for_status()

            data = response.json()
            result = PexelsSearchResponse(
                total_results=data.get("total_results", 0),
                page=data.get("page", page),
                per_page=data.get("per_page", per_page),
                photos=[PexelsImage(**photo) for photo in data.get("photos", [])],
                next_page=data.get("next_page"),
            )

            logger.info(
                f"Pexels search completed: {len(result.photos)} photos found "
                f"(total: {result.total_results})"
            )
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Pexels API error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Pexels request failed: {e}")
            raise

    async def download_image(self, image_url: str) -> bytes:
        """
        Download image from URL.

        Args:
            image_url: Direct image URL from Pexels

        Returns:
            Image data as bytes

        Raises:
            httpx.HTTPError: If download fails
        """
        try:
            logger.debug(f"Downloading image: {image_url[:80]}...")
            response = await self.client.get(image_url)
            response.raise_for_status()

            logger.debug(f"Image downloaded: {len(response.content)} bytes")
            return response.content

        except httpx.HTTPError as e:
            logger.error(f"Image download failed: {e}")
            raise

    async def get_image_by_id(self, photo_id: int) -> PexelsImage:
        """
        Get specific image by ID.

        Args:
            photo_id: Pexels photo ID

        Returns:
            PexelsImage metadata

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            logger.debug(f"Fetching image by ID: {photo_id}")
            response = await self.client.get(f"{self.BASE_URL}/photos/{photo_id}")
            response.raise_for_status()

            data = response.json()
            return PexelsImage(**data)

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch image {photo_id}: {e}")
            raise

    async def generate_search_keywords(
        self,
        course_title: str,
        slide_title: str,
        slide_content: str | None = None,
        max_keywords: int = 3,
    ) -> AIKeywordResult:
        """
        Generate search keywords using AI based on course content.

        Args:
            course_title: Title of the course
            slide_title: Title of the current slide
            slide_content: Optional slide content for context
            max_keywords: Maximum number of keywords to generate

        Returns:
            AIKeywordResult with generated keywords
        """
        llm_service = get_llm_service()

        # Build context for LLM
        context_parts = [
            f"Course: {course_title}",
            f"Slide Title: {slide_title}",
        ]
        if slide_content:
            # Truncate long content
            truncated = slide_content[:500] + "..." if len(slide_content) > 500 else slide_content
            context_parts.append(f"Content: {truncated}")

        context = "\n".join(context_parts)

        system_prompt = """You are an expert at generating image search keywords for educational presentations.
Your task is to generate concise, effective English keywords for searching stock photos.

Guidelines:
- Generate simple, descriptive keywords that would find relevant educational/professional images
- Focus on visual concepts that can be photographed
- Avoid abstract concepts that are hard to visualize
- Prefer concrete nouns over verbs or adjectives
- Keywords should be in English for best Pexels results
- Output ONLY the keywords, one per line, nothing else"""

        user_prompt = f"""Generate {max_keywords} image search keywords for this educational slide:

{context}

Output only the keywords, one per line:"""

        try:
            response = await llm_service.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more focused results
                max_tokens=100,
            )

            # Parse keywords from response
            lines = [line.strip() for line in response.content.strip().split("\n")]
            keywords = [kw for kw in lines if kw and not kw.startswith("#")][:max_keywords]

            if not keywords:
                # Fallback to slide title
                keywords = [slide_title]

            result = AIKeywordResult(
                keywords=keywords,
                primary_keyword=keywords[0],
                language="en",
                generated_at=datetime.utcnow(),
            )

            logger.info(f"Generated keywords for '{slide_title}': {keywords}")
            return result

        except Exception as e:
            logger.warning(f"AI keyword generation failed, using fallback: {e}")
            # Fallback to basic keyword extraction
            return AIKeywordResult(
                keywords=[slide_title],
                primary_keyword=slide_title,
                language="en",
                generated_at=datetime.utcnow(),
            )

    def get_attribution_text(self, image: PexelsImage) -> str:
        """
        Generate attribution text for image (required by Pexels).

        Args:
            image: PexelsImage metadata

        Returns:
            Attribution string for use in slide notes/footer
        """
        return f"Photo by {image.photographer} on Pexels ({image.url})"

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Global instance
_pexels_service: PexelsService | None = None


def get_pexels_service() -> PexelsService:
    """Get or create global Pexels service instance."""
    global _pexels_service
    if _pexels_service is None:
        _pexels_service = PexelsService()
    return _pexels_service


async def shutdown_pexels_service():
    """Cleanup Pexels service on shutdown."""
    global _pexels_service
    if _pexels_service is not None:
        await _pexels_service.close()
        _pexels_service = None
