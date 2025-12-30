"""
PPT Generation Service

Orchestrates the 5-stage PPTAgent pipeline to generate presentations
"""

import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.pptagent_core.presentation.models import Presentation
from app.pptagent_core.roles.coder import Coder
from app.pptagent_core.roles.content_organizer import ContentOrganizer
from app.pptagent_core.roles.editor import Editor
from app.pptagent_core.roles.layout_selector import LayoutSelector
from app.pptagent_core.roles.schema_extractor import SchemaExtractor
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


class PPTGenerationProgress:
    """Progress tracking for presentation generation"""

    def __init__(self):
        self.stage: str = "initializing"
        self.progress: float = 0.0
        self.message: str = "Starting generation..."
        self.error: str | None = None


class PPTService:
    """
    Main service for PPT generation

    Orchestrates the 5-stage pipeline:
    1. Schema Extraction
    2. Content Organization
    3. Layout Selection
    4. Content Editing
    5. Final Coding
    """

    def __init__(self, llm_service: LLMService | None = None):
        self.llm = llm_service or get_llm_service()

        # Initialize pipeline stages
        self.schema_extractor = SchemaExtractor(self.llm)
        self.content_organizer = ContentOrganizer(
            self.llm, max_slides=settings.max_slides_per_presentation
        )
        self.layout_selector = LayoutSelector(self.llm)
        self.editor = Editor(self.llm)
        self.coder = Coder(self.llm)

    async def generate_presentation(
        self,
        markdown_content: str,
        title: str | None = None,
        author: str | None = None,
        template: str | None = None,
        audience: str | None = None,
        tone: str | None = None,
    ) -> Presentation:
        """
        Generate presentation from markdown content

        Args:
            markdown_content: Source markdown text
            title: Presentation title (auto-extracted if not provided)
            author: Author name
            template: Template file name
            audience: Target audience
            tone: Desired tone

        Returns:
            Presentation object

        Raises:
            ValueError: If generation fails
            RuntimeError: If LLM service fails
        """
        start_time = datetime.now()
        logger.info("Starting presentation generation pipeline...")

        try:
            # Stage 1: Extract schema
            logger.info("[1/5] Extracting schema...")
            schema = await self.schema_extractor.extract(markdown_content)

            # Use extracted title if not provided
            if not title:
                title = schema.get("title", "Untitled Presentation")

            # Stage 2: Organize content
            logger.info("[2/5] Organizing content...")
            organized = await self.content_organizer.organize(schema)

            # Stage 3: Select layouts
            logger.info("[3/5] Selecting layouts...")
            with_layouts = await self.layout_selector.select_layouts(organized)

            # Stage 4: Edit content
            logger.info("[4/5] Editing content...")
            refined = await self.editor.edit(with_layouts, audience, tone)

            # Stage 5: Generate final structure
            logger.info("[5/5] Generating final structure...")
            presentation = await self.coder.code(refined, title, author, template)

            # Log completion
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Presentation generation completed in {duration:.2f}s: "
                f"{presentation.slide_count()} slides"
            )

            return presentation

        except Exception as e:
            logger.error(f"Presentation generation failed: {e}", exc_info=True)
            raise

    async def generate_presentation_stream(
        self,
        markdown_content: str,
        title: str | None = None,
        author: str | None = None,
        template: str | None = None,
        audience: str | None = None,
        tone: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Generate presentation with progress streaming

        Args:
            Same as generate_presentation()

        Yields:
            Progress updates as dictionaries with:
            - stage: Current stage name
            - progress: Completion percentage (0-100)
            - message: Status message
            - result: Final presentation (only in last message)
            - error: Error message if failed

        Example:
            async for update in service.generate_presentation_stream(content):
                print(f"{update['stage']}: {update['progress']}% - {update['message']}")
                if 'result' in update:
                    presentation = update['result']
        """
        start_time = datetime.now()

        try:
            # Stage 1: Extract schema (0-20%)
            yield {
                "stage": "schema_extraction",
                "progress": 0,
                "message": "Analyzing markdown structure...",
            }

            schema = await self.schema_extractor.extract(markdown_content)

            if not title:
                title = schema.get("title", "Untitled Presentation")

            yield {
                "stage": "schema_extraction",
                "progress": 20,
                "message": f"Schema extracted: {schema.get('total_slides', 'unknown')} slides estimated",
            }

            # Stage 2: Organize content (20-40%)
            yield {
                "stage": "content_organization",
                "progress": 20,
                "message": "Organizing content into slides...",
            }

            organized = await self.content_organizer.organize(schema)

            yield {
                "stage": "content_organization",
                "progress": 40,
                "message": f"Content organized: {len(organized.get('slides', []))} slides created",
            }

            # Stage 3: Select layouts (40-60%)
            yield {
                "stage": "layout_selection",
                "progress": 40,
                "message": "Selecting optimal layouts...",
            }

            with_layouts = await self.layout_selector.select_layouts(organized)

            yield {
                "stage": "layout_selection",
                "progress": 60,
                "message": "Layouts selected for all slides",
            }

            # Stage 4: Edit content (60-80%)
            yield {
                "stage": "content_editing",
                "progress": 60,
                "message": "Refining content and adding polish...",
            }

            refined = await self.editor.edit(with_layouts, audience, tone)

            yield {
                "stage": "content_editing",
                "progress": 80,
                "message": "Content refined and polished",
            }

            # Stage 5: Generate final structure (80-100%)
            yield {
                "stage": "final_generation",
                "progress": 80,
                "message": "Generating final presentation structure...",
            }

            presentation = await self.coder.code(refined, title, author, template)

            duration = (datetime.now() - start_time).total_seconds()

            yield {
                "stage": "completed",
                "progress": 100,
                "message": f"Generation completed in {duration:.2f}s",
                "result": presentation,
                "stats": {
                    "slide_count": presentation.slide_count(),
                    "duration_seconds": duration,
                    "title": presentation.metadata.title,
                },
            }

        except Exception as e:
            logger.error(f"Presentation generation failed: {e}", exc_info=True)
            yield {
                "stage": "error",
                "progress": 0,
                "message": f"Generation failed: {str(e)}",
                "error": str(e),
            }
            raise


# Global instance
_ppt_service: PPTService | None = None


def get_ppt_service() -> PPTService:
    """Get or create global PPT service instance"""
    global _ppt_service
    if _ppt_service is None:
        _ppt_service = PPTService()
    return _ppt_service
