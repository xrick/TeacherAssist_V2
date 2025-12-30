"""
Coder Role

Fifth stage: Generates final presentation structure for PPTX creation
"""

import json
import logging
from typing import Any

from app.pptagent_core.presentation.models import (
    ContentElement,
    ContentType,
    LayoutType,
    Presentation,
    PresentationMetadata,
    SlideContent,
)
from app.pptagent_core.prompts.templates import (
    CODER_SYSTEM,
    render_coder_prompt,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class Coder:
    """
    Generates final presentation structure

    This is the fifth and final stage in the PPTAgent pipeline. It:
    - Creates complete presentation structure
    - Adds formatting directives
    - Prepares for PPTX generation
    - Includes all metadata
    """

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def code(
        self,
        refined_slides: dict[str, Any],
        title: str,
        author: str | None = None,
        template: str | None = None,
    ) -> Presentation:
        """
        Generate final presentation structure

        Args:
            refined_slides: Refined slides from Editor
            title: Presentation title
            author: Author name
            template: Template file name

        Returns:
            Presentation object ready for PPTX generation

        Raises:
            ValueError: If coding fails or returns invalid JSON
            RuntimeError: If LLM generation fails
        """
        logger.info(f"Generating final presentation structure for '{title}'...")

        # Prepare metadata
        metadata = {"title": title}
        if author:
            metadata["author"] = author
        if template:
            metadata["template"] = template

        # Convert to JSON strings for prompt
        slides_json = json.dumps(refined_slides, indent=2)
        metadata_json = json.dumps(metadata, indent=2)

        # Render prompt
        user_prompt = render_coder_prompt(slides_json, metadata_json, author, template)

        # Generate final structure
        try:
            response = await self.llm.generate(
                prompt=user_prompt,
                system_prompt=CODER_SYSTEM,
                temperature=0.2,  # Very low temperature for precise structure
                max_tokens=10000,
            )

            logger.info(
                f"Coding completed: {response.usage.total_tokens} tokens, "
                f"${response.usage.cost_usd:.6f}"
            )

            # Parse JSON response
            final_structure = self._parse_json_response(response.content)

            # Convert to Presentation model
            presentation = self._build_presentation(final_structure)

            logger.info(f"Final presentation generated: {presentation.slide_count()} slides")

            return presentation

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}") from e

        except Exception as e:
            logger.error(f"Coding failed: {e}", exc_info=True)
            raise

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                return json.loads(content[start:end].strip())

        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                return json.loads(content[start:end].strip())

        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])

        raise json.JSONDecodeError("No valid JSON found", content, 0)

    def _build_presentation(self, structure: dict[str, Any]) -> Presentation:
        """
        Build Presentation model from structure dictionary

        Args:
            structure: Final presentation structure

        Returns:
            Presentation model instance
        """
        # Extract metadata
        meta_dict = structure.get("metadata", {})
        metadata = PresentationMetadata(
            title=meta_dict.get("title", "Untitled Presentation"),
            author=meta_dict.get("author"),
            topic=meta_dict.get("topic"),
            audience=meta_dict.get("audience"),
            duration_minutes=meta_dict.get("duration_minutes"),
            template=meta_dict.get("template", "default.pptx"),
            tags=meta_dict.get("tags", []),
        )

        # Build slides
        slides = []
        for slide_dict in structure.get("slides", []):
            # Build content elements
            elements = []
            for elem_dict in slide_dict.get("elements", []):
                # Map string type to ContentType enum
                elem_type_str = elem_dict.get("type", "text")
                try:
                    elem_type = ContentType(elem_type_str)
                except ValueError:
                    logger.warning(f"Invalid content type '{elem_type_str}', defaulting to 'text'")
                    elem_type = ContentType.TEXT

                element = ContentElement(
                    type=elem_type,
                    content=elem_dict.get("content", ""),
                    metadata=elem_dict.get("metadata", {}),
                )
                elements.append(element)

            # Map layout string to LayoutType enum
            layout_str = slide_dict.get("layout", "content")
            try:
                layout = LayoutType(layout_str)
            except ValueError:
                logger.warning(f"Invalid layout type '{layout_str}', defaulting to 'content'")
                layout = LayoutType.CONTENT

            # Create slide
            slide = SlideContent(
                title=slide_dict.get("title", ""),
                elements=elements,
                notes=slide_dict.get("notes"),
                layout=layout,
                metadata=slide_dict.get("metadata", {}),
            )
            slides.append(slide)

        # Create presentation
        presentation = Presentation(metadata=metadata, slides=slides)

        logger.debug(
            f"Built presentation: {presentation.slide_count()} slides, "
            f"template: {metadata.template}"
        )

        return presentation
