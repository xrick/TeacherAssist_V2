"""
Pexels API routes

Provides endpoints for image search, download, and cache management.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.pexels import (
    AIKeywordRequest,
    AIKeywordResponse,
    CachedImageResponse,
    CacheStatsResponse,
    ImageDownloadRequest,
    ImageDownloadResponse,
    ImageSearchResponse,
    PexelsImageResponse,
)
from app.services.image_cache_service import ImageCacheService, get_image_cache_service
from app.services.pexels_service import (
    ImageOrientation,
    PexelsService,
    get_pexels_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pexels", tags=["pexels"])


def _image_to_response(image, pexels_service: PexelsService) -> PexelsImageResponse:
    """Convert PexelsImage to API response with attribution."""
    return PexelsImageResponse(
        id=image.id,
        width=image.width,
        height=image.height,
        url=image.url,
        photographer=image.photographer,
        photographer_url=image.photographer_url,
        avg_color=image.avg_color,
        src=image.src,
        alt=image.alt,
        attribution=pexels_service.get_attribution_text(image),
    )


@router.get("/search", response_model=ImageSearchResponse)
async def search_images(
    keyword: str = Query(..., min_length=1, max_length=200, description="Search keyword"),
    per_page: int = Query(default=9, ge=1, le=80, description="Results per page"),
    page: int = Query(default=1, ge=1, description="Page number"),
    orientation: str | None = Query(
        default=None,
        description="Filter: landscape, portrait, square",
    ),
    pexels_service: PexelsService = Depends(get_pexels_service),
) -> ImageSearchResponse:
    """
    Search for images on Pexels.

    Returns thumbnail URLs for preview display.
    Use the download endpoint to cache selected images.

    Args:
        keyword: Search keyword or phrase
        per_page: Number of results (default: 9 for 3x3 grid)
        page: Page number for pagination
        orientation: Optional orientation filter

    Returns:
        ImageSearchResponse with matching images
    """
    try:
        # Convert orientation string to enum if provided
        orientation_enum = None
        if orientation:
            try:
                orientation_enum = ImageOrientation(orientation.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid orientation: {orientation}. Use: landscape, portrait, square",
                )

        result = await pexels_service.search_images(
            keyword=keyword,
            per_page=per_page,
            page=page,
            orientation=orientation_enum,
        )

        photos = [_image_to_response(photo, pexels_service) for photo in result.photos]

        return ImageSearchResponse(
            total_results=result.total_results,
            page=result.page,
            per_page=result.per_page,
            photos=photos,
            has_next=result.next_page is not None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/download", response_model=ImageDownloadResponse)
async def download_image(
    request: ImageDownloadRequest,
    pexels_service: PexelsService = Depends(get_pexels_service),
    cache_service: ImageCacheService = Depends(get_image_cache_service),
) -> ImageDownloadResponse:
    """
    Download and cache an image from Pexels.

    Checks cache first; downloads only if not cached or expired.

    Args:
        request: Download request with image ID and keyword

    Returns:
        ImageDownloadResponse with cached file path
    """
    try:
        # Check cache first
        cached = await cache_service.get_cached_image(request.keyword, request.image_id)
        if cached:
            logger.info(f"Cache hit for image {request.image_id}")
            return ImageDownloadResponse(
                success=True,
                image_id=cached.image_id,
                keyword=cached.keyword,
                file_path=cached.file_path,
                photographer=cached.photographer,
                attribution=f"Photo by {cached.photographer} on Pexels ({cached.pexels_url})",
                cached_at=cached.cached_at,
                expires_at=cached.expires_at,
            )

        # Fetch image metadata
        image = await pexels_service.get_image_by_id(request.image_id)

        # Get URL for requested size
        size_map = {
            "original": image.src.original,
            "large2x": image.src.large2x,
            "large": image.src.large,
            "medium": image.src.medium,
            "small": image.src.small,
        }
        image_url = size_map.get(request.size, image.src.large)

        # Download image
        image_data = await pexels_service.download_image(image_url)

        # Save to cache
        cached_info = await cache_service.save_to_cache(
            keyword=request.keyword,
            image=image,
            image_data=image_data,
        )

        return ImageDownloadResponse(
            success=True,
            image_id=cached_info.image_id,
            keyword=cached_info.keyword,
            file_path=cached_info.file_path,
            photographer=cached_info.photographer,
            attribution=f"Photo by {cached_info.photographer} on Pexels ({cached_info.pexels_url})",
            cached_at=cached_info.cached_at,
            expires_at=cached_info.expires_at,
        )

    except Exception as e:
        logger.error(f"Image download failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/ai-keywords", response_model=AIKeywordResponse)
async def generate_ai_keywords(
    request: AIKeywordRequest,
    pexels_service: PexelsService = Depends(get_pexels_service),
) -> AIKeywordResponse:
    """
    Generate AI-powered search keywords from course content.

    Uses LLM to generate relevant image search keywords based on
    course title, slide title, and optional content.

    Args:
        request: AI keyword request with course/slide information

    Returns:
        AIKeywordResponse with generated keywords
    """
    try:
        result = await pexels_service.generate_search_keywords(
            course_title=request.course_title,
            slide_title=request.slide_title,
            slide_content=request.slide_content,
            max_keywords=request.max_keywords,
        )

        return AIKeywordResponse(
            keywords=result.keywords,
            primary_keyword=result.primary_keyword,
            language=result.language,
            generated_at=result.generated_at,
        )

    except Exception as e:
        logger.error(f"AI keyword generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Keyword generation failed: {str(e)}")


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    cache_service: ImageCacheService = Depends(get_image_cache_service),
) -> CacheStatsResponse:
    """
    Get cache statistics.

    Returns information about cached images, total size, etc.
    """
    try:
        stats = await cache_service.get_cache_stats()
        return CacheStatsResponse(**stats.model_dump())

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/cache/keyword/{keyword}", response_model=list[CachedImageResponse])
async def get_cached_images_by_keyword(
    keyword: str,
    cache_service: ImageCacheService = Depends(get_image_cache_service),
) -> list[CachedImageResponse]:
    """
    Get all cached images for a keyword.

    Args:
        keyword: Search keyword

    Returns:
        List of cached images for the keyword
    """
    try:
        images = await cache_service.get_cached_images_by_keyword(keyword)
        return [
            CachedImageResponse(
                image_id=img.image_id,
                keyword=img.keyword,
                file_path=img.file_path,
                photographer=img.photographer,
                pexels_url=img.pexels_url,
                alt_text=img.alt_text,
                cached_at=img.cached_at,
                expires_at=img.expires_at,
                file_size_bytes=img.file_size_bytes,
            )
            for img in images
        ]

    except Exception as e:
        logger.error(f"Failed to get cached images: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cached images: {str(e)}")


@router.post("/cache/cleanup")
async def cleanup_cache(
    cache_service: ImageCacheService = Depends(get_image_cache_service),
) -> dict:
    """
    Clean up expired cache entries.

    Returns:
        Number of entries removed
    """
    try:
        removed = await cache_service.cleanup_expired()
        return {"success": True, "removed_count": removed}

    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.delete("/cache/clear")
async def clear_cache(
    cache_service: ImageCacheService = Depends(get_image_cache_service),
) -> dict:
    """
    Clear all cached images.

    WARNING: This removes all cached images permanently.

    Returns:
        Number of entries removed
    """
    try:
        removed = await cache_service.clear_cache()
        return {"success": True, "removed_count": removed}

    except Exception as e:
        logger.error(f"Cache clear failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")
