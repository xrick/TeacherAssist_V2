"""
Presentation Storage Service

Manages storage and retrieval of generated presentations
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.pptagent_core.presentation.models import Presentation

logger = logging.getLogger(__name__)


class PresentationStorage:
    """
    Presentation storage service

    Handles saving and retrieving generated presentations
    """

    def __init__(self, storage_path: Path | None = None):
        """
        Initialize storage service

        Args:
            storage_path: Path to storage directory
        """
        self.storage_path = storage_path or settings.output_storage_path
        self._metadata_cache: dict[str, dict] = {}

        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def save_presentation(
        self, presentation_id: str, presentation: Presentation, pptx_data: bytes
    ) -> str:
        """
        Save generated presentation

        Args:
            presentation_id: Unique presentation identifier
            presentation: Presentation metadata
            pptx_data: PPTX file data

        Returns:
            Presentation ID
        """
        try:
            # Create file path
            file_path = self.storage_path / f"{presentation_id}.pptx"

            # Save PPTX file
            file_path.write_bytes(pptx_data)

            # Save metadata
            metadata = {
                "id": presentation_id,
                "title": presentation.metadata.title,
                "author": presentation.metadata.author,
                "template": presentation.metadata.template,
                "slide_count": presentation.slide_count(),
                "created_at": datetime.utcnow().isoformat(),
                "file_path": str(file_path),
                "file_size": len(pptx_data),
            }

            self._metadata_cache[presentation_id] = metadata

            # Also save metadata to JSON
            metadata_path = self.storage_path / f"{presentation_id}.json"
            import json

            metadata_path.write_text(json.dumps(metadata, indent=2))

            logger.info(f"Presentation saved: {presentation_id} ({len(pptx_data)} bytes)")

            return presentation_id

        except Exception as e:
            logger.error(f"Failed to save presentation {presentation_id}: {e}", exc_info=True)
            raise

    async def get_presentation_path(self, presentation_id: str) -> Path | None:
        """
        Get file path for presentation

        Args:
            presentation_id: Presentation identifier

        Returns:
            Path to PPTX file or None if not found
        """
        file_path = self.storage_path / f"{presentation_id}.pptx"

        if file_path.exists():
            return file_path

        logger.warning(f"Presentation file not found: {presentation_id}")
        return None

    async def get_presentation_metadata(self, presentation_id: str) -> dict | None:
        """
        Get presentation metadata

        Args:
            presentation_id: Presentation identifier

        Returns:
            Metadata dictionary or None if not found
        """
        # Check cache first
        if presentation_id in self._metadata_cache:
            return self._metadata_cache[presentation_id]

        # Try to load from JSON file
        metadata_path = self.storage_path / f"{presentation_id}.json"
        if metadata_path.exists():
            try:
                import json

                metadata: dict[Any, Any] = json.loads(metadata_path.read_text())
                self._metadata_cache[presentation_id] = metadata
                return metadata
            except Exception as e:
                logger.error(f"Failed to load metadata for {presentation_id}: {e}")

        return None

    async def delete_presentation(self, presentation_id: str) -> bool:
        """
        Delete presentation and its metadata

        Args:
            presentation_id: Presentation identifier

        Returns:
            True if deleted successfully
        """
        try:
            file_path = self.storage_path / f"{presentation_id}.pptx"
            metadata_path = self.storage_path / f"{presentation_id}.json"

            deleted = False

            if file_path.exists():
                file_path.unlink()
                deleted = True

            if metadata_path.exists():
                metadata_path.unlink()

            if presentation_id in self._metadata_cache:
                del self._metadata_cache[presentation_id]

            if deleted:
                logger.info(f"Presentation deleted: {presentation_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete presentation {presentation_id}: {e}", exc_info=True)
            return False

    async def cleanup_old_presentations(self, max_age_days: int = 7) -> int:
        """
        Clean up presentations older than specified days

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of presentations deleted
        """
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
        deleted_count = 0

        try:
            for pptx_file in self.storage_path.glob("*.pptx"):
                # Check file modification time
                mtime = datetime.fromtimestamp(pptx_file.stat().st_mtime)

                if mtime < cutoff_time:
                    presentation_id = pptx_file.stem
                    if await self.delete_presentation(presentation_id):
                        deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old presentations")

        except Exception as e:
            logger.error(f"Failed to cleanup presentations: {e}", exc_info=True)

        return deleted_count


# Singleton instance
_storage: PresentationStorage | None = None


def get_presentation_storage() -> PresentationStorage:
    """
    Get presentation storage singleton

    Returns:
        PresentationStorage instance
    """
    global _storage
    if _storage is None:
        _storage = PresentationStorage()
    return _storage
