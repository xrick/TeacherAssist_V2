"""
Image Cache Service

Manages local caching of Pexels images with TTL-based expiration.
Supports keyword-based organization and cross-course image sharing.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel

from app.core.config import settings
from app.services.pexels_service import PexelsImage

logger = logging.getLogger(__name__)


class CachedImageInfo(BaseModel):
    """Metadata for a cached image"""

    image_id: int
    keyword: str
    file_path: str
    original_url: str
    photographer: str
    photographer_url: str
    pexels_url: str
    alt_text: str
    cached_at: datetime
    expires_at: datetime
    file_size_bytes: int


class CacheStats(BaseModel):
    """Cache statistics"""

    total_images: int
    total_size_bytes: int
    total_size_mb: float
    keywords_count: int
    oldest_image: datetime | None
    newest_image: datetime | None


class ImageCacheService:
    """
    Local image cache service with TTL-based expiration.

    Features:
    - Keyword-based directory organization
    - Automatic expiration cleanup
    - Cross-course image sharing
    - Cache statistics and management
    """

    INDEX_FILENAME = "cache_index.json"

    def __init__(self, cache_path: Path | None = None, ttl_days: int | None = None):
        """
        Initialize cache service.

        Args:
            cache_path: Root path for cache directory
            ttl_days: Cache TTL in days
        """
        self.cache_path = cache_path or settings.pexels_cache_path
        self.ttl_days = ttl_days or settings.pexels_cache_ttl_days

        # Ensure cache directory exists
        self.cache_path.mkdir(parents=True, exist_ok=True)

        # Load or create index
        self._index: dict[str, CachedImageInfo] = {}
        self._load_index()

    def _get_index_path(self) -> Path:
        """Get path to cache index file."""
        return self.cache_path / self.INDEX_FILENAME

    def _load_index(self):
        """Load cache index from disk."""
        index_path = self._get_index_path()
        if index_path.exists():
            try:
                with open(index_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self._index = {key: CachedImageInfo(**value) for key, value in data.items()}
                logger.debug(f"Loaded cache index: {len(self._index)} entries")
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to load cache index, starting fresh: {e}")
                self._index = {}
        else:
            self._index = {}

    def _save_index(self):
        """Save cache index to disk."""
        index_path = self._get_index_path()
        try:
            with open(index_path, "w", encoding="utf-8") as f:
                data = {key: value.model_dump(mode="json") for key, value in self._index.items()}
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Saved cache index: {len(self._index)} entries")
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")

    def _normalize_keyword(self, keyword: str) -> str:
        """
        Normalize keyword for use as directory name.

        Args:
            keyword: Raw keyword

        Returns:
            Normalized keyword safe for filesystem
        """
        # Lowercase and replace spaces/special chars with underscores
        normalized = keyword.lower().strip()
        normalized = re.sub(r"[^\w\s-]", "", normalized)
        normalized = re.sub(r"[\s-]+", "_", normalized)
        return normalized[:50]  # Limit length

    def _get_cache_key(self, keyword: str, image_id: int) -> str:
        """Generate unique cache key for an image."""
        normalized = self._normalize_keyword(keyword)
        return f"{normalized}_{image_id}"

    def _get_keyword_dir(self, keyword: str) -> Path:
        """Get directory path for a keyword."""
        normalized = self._normalize_keyword(keyword)
        return self.cache_path / normalized

    def _get_image_path(self, keyword: str, image_id: int, extension: str = "jpg") -> Path:
        """Get file path for an image."""
        keyword_dir = self._get_keyword_dir(keyword)
        return keyword_dir / f"{image_id}.{extension}"

    async def get_cached_image(self, keyword: str, image_id: int) -> CachedImageInfo | None:
        """
        Get cached image info if available and not expired.

        Args:
            keyword: Search keyword
            image_id: Pexels image ID

        Returns:
            CachedImageInfo if found and valid, None otherwise
        """
        cache_key = self._get_cache_key(keyword, image_id)
        info = self._index.get(cache_key)

        if info is None:
            return None

        # Check if expired
        if datetime.utcnow() > info.expires_at:
            logger.debug(f"Cache expired for {cache_key}")
            await self.remove_cached_image(keyword, image_id)
            return None

        # Verify file exists
        file_path = Path(info.file_path)
        if not file_path.exists():
            logger.warning(f"Cache file missing: {file_path}")
            del self._index[cache_key]
            self._save_index()
            return None

        return info

    async def get_cached_images_by_keyword(self, keyword: str) -> list[CachedImageInfo]:
        """
        Get all cached images for a keyword.

        Args:
            keyword: Search keyword

        Returns:
            List of cached images for the keyword
        """
        normalized = self._normalize_keyword(keyword)
        results = []

        for key, info in self._index.items():
            if key.startswith(f"{normalized}_"):
                # Check expiration
                if datetime.utcnow() <= info.expires_at:
                    # Verify file exists
                    if Path(info.file_path).exists():
                        results.append(info)

        return results

    async def save_to_cache(
        self,
        keyword: str,
        image: PexelsImage,
        image_data: bytes,
    ) -> CachedImageInfo:
        """
        Save image to cache.

        Args:
            keyword: Search keyword for organization
            image: Pexels image metadata
            image_data: Image file data

        Returns:
            CachedImageInfo for the saved image
        """
        # Determine file extension from URL
        extension = "jpg"
        if ".png" in image.src.large.lower():
            extension = "png"
        elif ".webp" in image.src.large.lower():
            extension = "webp"

        # Create keyword directory
        keyword_dir = self._get_keyword_dir(keyword)
        keyword_dir.mkdir(parents=True, exist_ok=True)

        # Save image file
        file_path = self._get_image_path(keyword, image.id, extension)
        with open(file_path, "wb") as f:
            f.write(image_data)

        # Create cache info
        now = datetime.utcnow()
        cache_info = CachedImageInfo(
            image_id=image.id,
            keyword=keyword,
            file_path=str(file_path),
            original_url=image.src.original,
            photographer=image.photographer,
            photographer_url=image.photographer_url,
            pexels_url=image.url,
            alt_text=image.alt,
            cached_at=now,
            expires_at=now + timedelta(days=self.ttl_days),
            file_size_bytes=len(image_data),
        )

        # Update index
        cache_key = self._get_cache_key(keyword, image.id)
        self._index[cache_key] = cache_info
        self._save_index()

        logger.info(
            f"Cached image: {cache_key} ({len(image_data)} bytes, "
            f"expires: {cache_info.expires_at})"
        )

        return cache_info

    async def remove_cached_image(self, keyword: str, image_id: int) -> bool:
        """
        Remove image from cache.

        Args:
            keyword: Search keyword
            image_id: Pexels image ID

        Returns:
            True if removed, False if not found
        """
        cache_key = self._get_cache_key(keyword, image_id)
        info = self._index.get(cache_key)

        if info is None:
            return False

        # Remove file
        try:
            file_path = Path(info.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to remove cache file: {e}")

        # Remove from index
        del self._index[cache_key]
        self._save_index()

        logger.debug(f"Removed from cache: {cache_key}")
        return True

    async def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.

        Returns:
            Number of entries removed
        """
        now = datetime.utcnow()
        expired_keys = [key for key, info in self._index.items() if now > info.expires_at]

        removed = 0
        for key in expired_keys:
            info = self._index[key]
            try:
                file_path = Path(info.file_path)
                if file_path.exists():
                    file_path.unlink()
                removed += 1
            except Exception as e:
                logger.warning(f"Failed to remove expired file {key}: {e}")

            del self._index[key]

        if removed > 0:
            self._save_index()
            # Clean up empty directories
            self._cleanup_empty_dirs()
            logger.info(f"Cleaned up {removed} expired cache entries")

        return removed

    def _cleanup_empty_dirs(self):
        """Remove empty keyword directories."""
        for item in self.cache_path.iterdir():
            if item.is_dir() and not any(item.iterdir()):
                try:
                    item.rmdir()
                    logger.debug(f"Removed empty cache directory: {item}")
                except Exception as e:
                    logger.warning(f"Failed to remove empty dir {item}: {e}")

    async def get_cache_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            CacheStats with current cache info
        """
        total_size = 0
        keywords = set()
        oldest: datetime | None = None
        newest: datetime | None = None

        for info in self._index.values():
            total_size += info.file_size_bytes
            keywords.add(info.keyword)

            if oldest is None or info.cached_at < oldest:
                oldest = info.cached_at
            if newest is None or info.cached_at > newest:
                newest = info.cached_at

        return CacheStats(
            total_images=len(self._index),
            total_size_bytes=total_size,
            total_size_mb=round(total_size / (1024 * 1024), 2),
            keywords_count=len(keywords),
            oldest_image=oldest,
            newest_image=newest,
        )

    async def clear_cache(self) -> int:
        """
        Clear all cached images.

        Returns:
            Number of entries removed
        """
        count = len(self._index)

        # Remove all files
        for info in self._index.values():
            try:
                file_path = Path(info.file_path)
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove cache file: {e}")

        # Clear index
        self._index = {}
        self._save_index()

        # Clean up directories
        self._cleanup_empty_dirs()

        logger.info(f"Cache cleared: {count} entries removed")
        return count


# Global instance
_image_cache_service: ImageCacheService | None = None


def get_image_cache_service() -> ImageCacheService:
    """Get or create global image cache service instance."""
    global _image_cache_service
    if _image_cache_service is None:
        _image_cache_service = ImageCacheService()
    return _image_cache_service
