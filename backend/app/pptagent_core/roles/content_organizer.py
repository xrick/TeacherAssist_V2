"""
Content Organizer Role

Second stage: Organizes extracted schema into well-structured slide content
"""

import json
import logging
from typing import Any

from app.pptagent_core.prompts.templates import (
    CONTENT_ORGANIZER_SYSTEM,
    render_content_organizer_prompt,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ContentOrganizer:
    """
    Organizes schema into structured slide content

    This is the second stage in the PPTAgent pipeline. It:
    - Distributes content evenly across slides
    - Creates balanced slide structure
    - Determines content elements for each slide
    - Adds speaker notes where appropriate
    """

    def __init__(self, llm_service: LLMService, max_slides: int = 50):
        self.llm = llm_service
        self.max_slides = max_slides

    async def organize(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Organize schema into slide content

        Args:
            schema: Extracted schema from SchemaExtractor

        Returns:
            Dictionary with organized slides

        Raises:
            ValueError: If organization fails or returns invalid JSON
            RuntimeError: If LLM generation fails
        """
        logger.info(
            f"Organizing content from schema ({schema.get('total_slides', 'unknown')} slides)..."
        )

        # Convert schema to JSON string for prompt
        schema_json = json.dumps(schema, indent=2)

        # Render prompt
        user_prompt = render_content_organizer_prompt(schema_json, self.max_slides)

        # Generate organized content
        try:
            response = await self.llm.generate(
                prompt=user_prompt,
                system_prompt=CONTENT_ORGANIZER_SYSTEM,
                temperature=0.4,  # Moderate creativity for organization
                max_tokens=6000,
            )

            logger.info(
                f"Content organization completed: {response.usage.total_tokens} tokens, "
                f"${response.usage.cost_usd:.6f}"
            )

            # Parse JSON response
            organized = self._parse_json_response(response.content)

            # Validate organized content
            self._validate_organized_content(organized)

            slide_count = len(organized.get("slides", []))
            logger.info(f"Content organized successfully: {slide_count} slides")

            return organized

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(
                f"Response content: {response.content if 'response' in locals() else 'N/A'}"
            )
            raise ValueError(f"Invalid JSON response from LLM: {e}") from e

        except Exception as e:
            logger.error(f"Content organization failed: {e}", exc_info=True)
            raise

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks

        Args:
            content: LLM response content

        Returns:
            Parsed JSON dictionary

        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        # Try direct parsing first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                json_str = content[start:end].strip()
                return json.loads(json_str)

        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                json_str = content[start:end].strip()
                return json.loads(json_str)

        # Try to find JSON object
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = content[start:end]
            return json.loads(json_str)

        raise json.JSONDecodeError("No valid JSON found in response", content, 0)

    def _validate_organized_content(self, organized: dict[str, Any]):
        """
        Validate organized content structure

        Args:
            organized: Parsed organized content dictionary

        Raises:
            ValueError: If content is invalid
        """
        if "slides" not in organized:
            raise ValueError("Organized content missing 'slides' field")

        if not isinstance(organized["slides"], list):
            raise ValueError("'slides' must be a list")

        slides = organized["slides"]

        if len(slides) == 0:
            raise ValueError("No slides in organized content")

        if len(slides) > self.max_slides:
            logger.warning(
                f"Slide count ({len(slides)}) exceeds maximum ({self.max_slides}), "
                f"truncating..."
            )
            organized["slides"] = slides[: self.max_slides]

        # Validate each slide
        for idx, slide in enumerate(slides[: self.max_slides]):
            if "title" not in slide:
                raise ValueError(f"Slide {idx} missing 'title'")

            if "elements" not in slide:
                raise ValueError(f"Slide {idx} missing 'elements'")

            if not isinstance(slide["elements"], list):
                raise ValueError(f"Slide {idx} 'elements' must be a list")

            # Validate elements
            for elem_idx, element in enumerate(slide["elements"]):
                if "type" not in element:
                    raise ValueError(f"Slide {idx}, element {elem_idx} missing 'type'")

                if "content" not in element:
                    raise ValueError(f"Slide {idx}, element {elem_idx} missing 'content'")

        logger.debug(f"Content validation passed: {len(slides)} slides")
