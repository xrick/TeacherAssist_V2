"""
Slide Image Service

Handles automatic image assignment for slides and manual image updates.
Coordinates between Pexels API, cache, and PPTX building.
"""

import logging

from app.pptagent_core.presentation.models import (
    ImagePosition,
    LayoutType,
    Presentation,
    SlideContent,
    SlideImage,
)
from app.services.image_cache_service import ImageCacheService, get_image_cache_service
from app.services.pexels_service import ImageOrientation, PexelsService, get_pexels_service

logger = logging.getLogger(__name__)


# Layouts that should have images by default
IMAGE_LAYOUTS = {
    LayoutType.CONTENT,
    LayoutType.IMAGE,
    LayoutType.IMAGE_TEXT,
    LayoutType.TWO_COLUMN,
}

# Layouts that should NOT have images
NO_IMAGE_LAYOUTS = {
    LayoutType.TITLE,
    LayoutType.CLOSING,
    LayoutType.SECTION_HEADER,
}


class SlideImageService:
    """
    Service for managing slide images.

    Handles:
    - Automatic image assignment during presentation generation
    - Manual image replacement
    - Image search and selection
    """

    def __init__(
        self,
        pexels_service: PexelsService | None = None,
        cache_service: ImageCacheService | None = None,
    ):
        """
        Initialize service.

        Args:
            pexels_service: Optional Pexels service instance
            cache_service: Optional cache service instance
        """
        self._pexels_service = pexels_service
        self._cache_service = cache_service

    @property
    def pexels_service(self) -> PexelsService:
        """Get Pexels service (lazy initialization)."""
        if self._pexels_service is None:
            self._pexels_service = get_pexels_service()
        return self._pexels_service

    @property
    def cache_service(self) -> ImageCacheService:
        """Get cache service (lazy initialization)."""
        if self._cache_service is None:
            self._cache_service = get_image_cache_service()
        return self._cache_service

    async def add_images_to_presentation(
        self,
        presentation: Presentation,
        images_per_slide: int = 1,
    ) -> Presentation:
        """
        Add images to all eligible slides in a presentation.

        Args:
            presentation: Presentation to add images to
            images_per_slide: Number of images per slide (1-2)

        Returns:
            Updated presentation with images
        """
        course_title = presentation.metadata.title
        logger.info(f"Adding images to presentation: {course_title}")

        for idx, slide in enumerate(presentation.slides):
            # Skip slides that shouldn't have images
            if slide.layout in NO_IMAGE_LAYOUTS:
                logger.debug(f"Skipping slide {idx + 1} (layout: {slide.layout})")
                continue

            # Skip if slide already has images
            if slide.images:
                logger.debug(f"Slide {idx + 1} already has images")
                continue

            try:
                await self._add_images_to_slide(
                    slide=slide,
                    course_title=course_title,
                    slide_index=idx,
                    count=images_per_slide,
                )
            except Exception as e:
                logger.warning(f"Failed to add images to slide {idx + 1}: {e}")
                # Continue with other slides

        return presentation

    async def _add_images_to_slide(
        self,
        slide: SlideContent,
        course_title: str,
        slide_index: int,
        count: int = 1,
    ):
        """
        Add images to a single slide.

        Args:
            slide: Slide to add images to
            course_title: Course title for keyword generation
            slide_index: Slide index for logging
            count: Number of images to add
        """
        # Generate search keywords using AI
        slide_content = self._extract_slide_text(slide)
        keywords_result = await self.pexels_service.generate_search_keywords(
            course_title=course_title,
            slide_title=slide.title,
            slide_content=slide_content,
        )

        primary_keyword = keywords_result.primary_keyword
        logger.debug(f"Slide {slide_index + 1}: searching for '{primary_keyword}'")

        # Check cache first
        cached_images = await self.cache_service.get_cached_images_by_keyword(primary_keyword)
        if cached_images:
            # Use cached images
            for cached in cached_images[:count]:
                slide_image = SlideImage(
                    image_id=cached.image_id,
                    file_path=cached.file_path,
                    keyword=cached.keyword,
                    photographer=cached.photographer,
                    pexels_url=cached.pexels_url,
                    alt_text=cached.alt_text,
                    position=ImagePosition.AUTO,
                )
                slide.images.append(slide_image)
                logger.debug(f"Using cached image {cached.image_id} for slide {slide_index + 1}")

            if len(slide.images) >= count:
                return

        # Search for new images
        remaining = count - len(slide.images)
        search_result = await self.pexels_service.search_images(
            keyword=primary_keyword,
            per_page=remaining + 2,  # Get a few extra in case of issues
            orientation=self._get_preferred_orientation(slide.layout),
        )

        if not search_result.photos:
            # Try fallback keywords
            for fallback_keyword in keywords_result.keywords[1:]:
                search_result = await self.pexels_service.search_images(
                    keyword=fallback_keyword,
                    per_page=remaining + 2,
                )
                if search_result.photos:
                    primary_keyword = fallback_keyword
                    break

        if not search_result.photos:
            logger.warning(f"No images found for slide {slide_index + 1}")
            return

        # Download and cache images
        for photo in search_result.photos[:remaining]:
            try:
                # Download image
                image_url = photo.src.large  # Use large size for PPTX
                image_data = await self.pexels_service.download_image(image_url)

                # Cache image
                cached_info = await self.cache_service.save_to_cache(
                    keyword=primary_keyword,
                    image=photo,
                    image_data=image_data,
                )

                # Add to slide
                slide_image = SlideImage(
                    image_id=photo.id,
                    file_path=cached_info.file_path,
                    keyword=primary_keyword,
                    photographer=photo.photographer,
                    pexels_url=photo.url,
                    alt_text=photo.alt,
                    position=ImagePosition.AUTO,
                )
                slide.images.append(slide_image)

                logger.info(f"Added image {photo.id} to slide {slide_index + 1}")

            except Exception as e:
                logger.warning(f"Failed to download/cache image {photo.id}: {e}")
                continue

    def _extract_slide_text(self, slide: SlideContent) -> str:
        """Extract text content from slide for keyword generation."""
        parts = []
        for element in slide.elements:
            if element.content:
                parts.append(element.content[:200])  # Limit per element
        return " ".join(parts)[:500]  # Limit total

    def _get_preferred_orientation(self, layout: LayoutType) -> ImageOrientation | None:
        """Get preferred image orientation for layout."""
        if layout in {LayoutType.IMAGE, LayoutType.CONTENT}:
            return ImageOrientation.LANDSCAPE
        elif layout == LayoutType.IMAGE_TEXT:
            return ImageOrientation.PORTRAIT
        return None

    async def replace_slide_image(
        self,
        slide: SlideContent,
        image_index: int,
        new_image_id: int,
        keyword: str,
    ) -> SlideImage:
        """
        Replace an image on a slide.

        Args:
            slide: Slide containing the image
            image_index: Index of image to replace (0-based)
            new_image_id: New Pexels image ID
            keyword: Search keyword for cache organization

        Returns:
            New SlideImage

        Raises:
            ValueError: If image index is invalid
        """
        if image_index < 0 or image_index >= len(slide.images):
            raise ValueError(f"Invalid image index: {image_index}")

        # Check cache first
        cached = await self.cache_service.get_cached_image(keyword, new_image_id)

        if cached:
            # Use cached image
            new_slide_image = SlideImage(
                image_id=cached.image_id,
                file_path=cached.file_path,
                keyword=cached.keyword,
                photographer=cached.photographer,
                pexels_url=cached.pexels_url,
                alt_text=cached.alt_text,
                position=slide.images[image_index].position,  # Preserve position
            )
        else:
            # Fetch and cache new image
            image = await self.pexels_service.get_image_by_id(new_image_id)
            image_data = await self.pexels_service.download_image(image.src.large)
            cached_info = await self.cache_service.save_to_cache(
                keyword=keyword,
                image=image,
                image_data=image_data,
            )

            new_slide_image = SlideImage(
                image_id=image.id,
                file_path=cached_info.file_path,
                keyword=keyword,
                photographer=image.photographer,
                pexels_url=image.url,
                alt_text=image.alt,
                position=slide.images[image_index].position,
            )

        # Replace image
        slide.images[image_index] = new_slide_image
        logger.info(f"Replaced image at index {image_index} with {new_image_id}")

        return new_slide_image

    async def add_image_to_slide(
        self,
        slide: SlideContent,
        image_id: int,
        keyword: str,
        position: ImagePosition = ImagePosition.AUTO,
    ) -> SlideImage:
        """
        Add a new image to a slide.

        Args:
            slide: Slide to add image to
            image_id: Pexels image ID
            keyword: Search keyword for cache organization
            position: Image position on slide

        Returns:
            New SlideImage
        """
        # Check cache first
        cached = await self.cache_service.get_cached_image(keyword, image_id)

        if cached:
            new_slide_image = SlideImage(
                image_id=cached.image_id,
                file_path=cached.file_path,
                keyword=cached.keyword,
                photographer=cached.photographer,
                pexels_url=cached.pexels_url,
                alt_text=cached.alt_text,
                position=position,
            )
        else:
            # Fetch and cache new image
            image = await self.pexels_service.get_image_by_id(image_id)
            image_data = await self.pexels_service.download_image(image.src.large)
            cached_info = await self.cache_service.save_to_cache(
                keyword=keyword,
                image=image,
                image_data=image_data,
            )

            new_slide_image = SlideImage(
                image_id=image.id,
                file_path=cached_info.file_path,
                keyword=keyword,
                photographer=image.photographer,
                pexels_url=image.url,
                alt_text=image.alt,
                position=position,
            )

        slide.images.append(new_slide_image)
        logger.info(f"Added image {image_id} to slide")

        return new_slide_image


# Global instance
_slide_image_service: SlideImageService | None = None


def get_slide_image_service() -> SlideImageService:
    """Get or create global slide image service instance."""
    global _slide_image_service
    if _slide_image_service is None:
        _slide_image_service = SlideImageService()
    return _slide_image_service
