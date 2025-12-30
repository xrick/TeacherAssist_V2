"""
Template Manager Service

Manages PPTX templates for presentation generation
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class TemplateMetadata(BaseModel):
    """Template metadata model"""

    id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Template description")
    category: str = Field(default="general", description="Template category")
    file_path: Path = Field(..., description="Path to PPTX file")
    preview_image: str | None = Field(None, description="Preview image URL")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: list[str] = Field(default_factory=list, description="Template tags")


class TemplateService:
    """
    Template management service

    Handles template discovery, validation, and metadata management
    """

    def __init__(self, templates_path: Path | None = None):
        """
        Initialize Template Service

        Args:
            templates_path: Path to templates directory
        """
        self.templates_path = templates_path or settings.template_storage_path
        self._templates_cache: dict[str, TemplateMetadata] | None = None
        self._last_scan: datetime | None = None

    async def list_templates(
        self, category: str | None = None, refresh: bool = False
    ) -> list[TemplateMetadata]:
        """
        List all available templates

        Args:
            category: Filter by category (optional)
            refresh: Force refresh template cache

        Returns:
            List of template metadata
        """
        # Refresh cache if needed
        if refresh or self._templates_cache is None:
            await self._scan_templates()

        assert self._templates_cache is not None  # _scan_templates initializes cache
        templates = list(self._templates_cache.values())

        # Filter by category if specified
        if category:
            templates = [t for t in templates if t.category == category]

        logger.info(f"Listing {len(templates)} templates")
        return templates

    async def get_template(self, template_id: str) -> TemplateMetadata | None:
        """
        Get specific template by ID

        Args:
            template_id: Template identifier

        Returns:
            Template metadata or None if not found
        """
        if self._templates_cache is None:
            await self._scan_templates()

        assert self._templates_cache is not None  # _scan_templates initializes cache
        template = self._templates_cache.get(template_id)

        if template:
            logger.info(f"Retrieved template: {template_id}")
        else:
            logger.warning(f"Template not found: {template_id}")

        return template

    async def validate_template(self, template_id: str) -> bool:
        """
        Validate template exists and is usable

        Args:
            template_id: Template identifier

        Returns:
            True if template is valid
        """
        template = await self.get_template(template_id)

        if not template:
            return False

        # Check file exists
        if not template.file_path.exists():
            logger.error(f"Template file not found: {template.file_path}")
            return False

        # Check file is readable
        if not template.file_path.is_file():
            logger.error(f"Template path is not a file: {template.file_path}")
            return False

        # Check file extension
        if template.file_path.suffix.lower() != ".pptx":
            logger.error(f"Invalid template file type: {template.file_path.suffix}")
            return False

        logger.info(f"Template validated successfully: {template_id}")
        return True

    async def get_template_path(self, template_id: str) -> Path | None:
        """
        Get file path for template

        Args:
            template_id: Template identifier

        Returns:
            Path to template file or None if not found
        """
        template = await self.get_template(template_id)
        return template.file_path if template else None

    async def _scan_templates(self):
        """
        Scan templates directory and build cache

        This method discovers PPTX files and creates metadata entries
        """
        logger.info(f"Scanning templates in: {self.templates_path}")

        self._templates_cache = {}

        # Ensure templates directory exists
        self.templates_path.mkdir(parents=True, exist_ok=True)

        # Scan for PPTX files
        for pptx_file in self.templates_path.glob("*.pptx"):
            try:
                template_id = pptx_file.stem
                metadata = self._create_metadata(pptx_file)
                self._templates_cache[template_id] = metadata
                logger.debug(f"Discovered template: {template_id}")

            except Exception as e:
                logger.error(f"Failed to process template {pptx_file}: {e}")
                continue

        # Also scan subdirectories
        for subdir in self.templates_path.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                category = subdir.name
                for pptx_file in subdir.glob("*.pptx"):
                    try:
                        template_id = f"{category}/{pptx_file.stem}"
                        metadata = self._create_metadata(pptx_file, category=category)
                        self._templates_cache[template_id] = metadata
                        logger.debug(f"Discovered template: {template_id}")

                    except Exception as e:
                        logger.error(f"Failed to process template {pptx_file}: {e}")
                        continue

        self._last_scan = datetime.utcnow()
        logger.info(f"Template scan complete: {len(self._templates_cache)} templates found")

    def _create_metadata(self, file_path: Path, category: str = "general") -> TemplateMetadata:
        """
        Create metadata for template file

        Args:
            file_path: Path to PPTX file
            category: Template category

        Returns:
            Template metadata
        """
        template_id = file_path.stem

        # Generate display name from file name
        name = template_id.replace("_", " ").replace("-", " ").title()

        # Basic metadata
        metadata = TemplateMetadata(
            id=template_id if category == "general" else f"{category}/{template_id}",
            name=name,
            description=f"{name} presentation template",
            category=category,
            file_path=file_path,
            preview_image=None,
            created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
        )

        # Try to load additional metadata from companion JSON file
        metadata_file = file_path.with_suffix(".json")
        if metadata_file.exists():
            try:
                import json

                with open(metadata_file) as f:
                    extra_data = json.load(f)

                # Update metadata with JSON data
                if "description" in extra_data:
                    metadata.description = extra_data["description"]
                if "tags" in extra_data:
                    metadata.tags = extra_data["tags"]
                if "preview_image" in extra_data:
                    metadata.preview_image = extra_data["preview_image"]

            except Exception as e:
                logger.warning(f"Failed to load metadata from {metadata_file}: {e}")

        return metadata

    async def get_stats(self) -> dict[str, Any]:
        """
        Get template statistics

        Returns:
            Statistics dictionary
        """
        if self._templates_cache is None:
            await self._scan_templates()

        assert self._templates_cache is not None  # _scan_templates initializes cache
        categories: dict[str, int] = {}
        for template in self._templates_cache.values():
            cat = template.category
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_templates": len(self._templates_cache),
            "categories": categories,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
            "templates_path": str(self.templates_path),
        }


# Singleton instance
_template_service: TemplateService | None = None


def get_template_service() -> TemplateService:
    """
    Get template service singleton

    Returns:
        TemplateService instance
    """
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service
