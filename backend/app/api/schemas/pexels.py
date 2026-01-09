"""
API schemas for Pexels image operations
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ImageSrcResponse(BaseModel):
    """Image source URLs in various sizes"""

    original: str
    large2x: str
    large: str
    medium: str
    small: str
    portrait: str
    landscape: str
    tiny: str


class PexelsImageResponse(BaseModel):
    """Pexels image metadata for API response"""

    id: int
    width: int
    height: int
    url: str = Field(..., description="Pexels page URL")
    photographer: str
    photographer_url: str
    avg_color: str
    src: ImageSrcResponse
    alt: str
    attribution: str = Field(..., description="Attribution text for the image")


class ImageSearchRequest(BaseModel):
    """Request to search for images"""

    keyword: str = Field(..., min_length=1, max_length=200, description="Search keyword")
    per_page: int = Field(default=9, ge=1, le=80, description="Number of results (1-80)")
    page: int = Field(default=1, ge=1, description="Page number")
    orientation: str | None = Field(
        default=None,
        description="Filter by orientation: landscape, portrait, square",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "keyword": "education technology",
                "per_page": 9,
                "page": 1,
                "orientation": "landscape",
            }
        }
    }


class ImageSearchResponse(BaseModel):
    """Response from image search"""

    total_results: int
    page: int
    per_page: int
    photos: list[PexelsImageResponse]
    has_next: bool


class ImageDownloadRequest(BaseModel):
    """Request to download and cache an image"""

    image_id: int = Field(..., description="Pexels image ID")
    keyword: str = Field(
        ..., min_length=1, max_length=200, description="Keyword for cache organization"
    )
    size: str = Field(
        default="large",
        description="Image size: original, large2x, large, medium, small",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "image_id": 123456,
                "keyword": "education",
                "size": "large",
            }
        }
    }


class ImageDownloadResponse(BaseModel):
    """Response after downloading an image"""

    success: bool
    image_id: int
    keyword: str
    file_path: str
    photographer: str
    attribution: str
    cached_at: datetime
    expires_at: datetime


class AIKeywordRequest(BaseModel):
    """Request to generate AI keywords"""

    course_title: str = Field(..., min_length=1, max_length=500, description="Course title")
    slide_title: str = Field(..., min_length=1, max_length=500, description="Slide title")
    slide_content: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional slide content for context",
    )
    max_keywords: int = Field(default=3, ge=1, le=5, description="Maximum keywords to generate")

    model_config = {
        "json_schema_extra": {
            "example": {
                "course_title": "Introduction to Machine Learning",
                "slide_title": "Neural Network Basics",
                "slide_content": "A neural network is a computational model inspired by biological neurons...",
                "max_keywords": 3,
            }
        }
    }


class AIKeywordResponse(BaseModel):
    """Response with AI-generated keywords"""

    keywords: list[str]
    primary_keyword: str
    language: str
    generated_at: datetime


class CacheStatsResponse(BaseModel):
    """Cache statistics response"""

    total_images: int
    total_size_bytes: int
    total_size_mb: float
    keywords_count: int
    oldest_image: datetime | None
    newest_image: datetime | None


class CachedImageResponse(BaseModel):
    """Cached image information"""

    image_id: int
    keyword: str
    file_path: str
    photographer: str
    pexels_url: str
    alt_text: str
    cached_at: datetime
    expires_at: datetime
    file_size_bytes: int


class SlideImageUpdateRequest(BaseModel):
    """Request to update a slide's image"""

    presentation_id: str = Field(..., description="Presentation ID")
    slide_index: int = Field(..., ge=0, description="Slide index (0-based)")
    image_id: int = Field(..., description="Pexels image ID to use")
    keyword: str = Field(..., description="Search keyword for cache lookup")
    position: str = Field(
        default="auto",
        description="Image position: auto, left, right, top, bottom, background",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "presentation_id": "abc-123-def",
                "slide_index": 2,
                "image_id": 123456,
                "keyword": "education",
                "position": "right",
            }
        }
    }


class SlideImageUpdateResponse(BaseModel):
    """Response after updating slide image"""

    success: bool
    message: str
    slide_index: int
    image_id: int
    attribution: str
