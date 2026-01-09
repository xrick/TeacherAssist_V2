"""
Layout Selector Role

Third stage: Selects appropriate layouts for each slide
"""

import json
import logging
from typing import Any

from app.pptagent_core.prompts.templates import (
    LAYOUT_SELECTOR_SYSTEM,
    render_layout_selector_prompt,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class LayoutSelector:
    """
    Selects appropriate layouts for slides

    This is the third stage in the PPTAgent pipeline. It:
    - Analyzes content type and density
    - Selects optimal layout for each slide
    - Ensures visual variety and professionalism
    """

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def select_layouts(self, organized_content: dict[str, Any]) -> dict[str, Any]:
        """
        Select layouts for organized slides

        Args:
            organized_content: Organized content from ContentOrganizer

        Returns:
            Dictionary with slides including layout selections

        Raises:
            ValueError: If selection fails or returns invalid JSON
            RuntimeError: If LLM generation fails
        """
        logger.info(f"Selecting layouts for {len(organized_content.get('slides', []))} slides...")

        # Convert organized content to JSON string for prompt
        slides_json = json.dumps(organized_content, indent=2)

        # Render prompt
        user_prompt = render_layout_selector_prompt(slides_json)

        # Generate layout selections
        try:
            response = await self.llm.generate(
                prompt=user_prompt,
                system_prompt=LAYOUT_SELECTOR_SYSTEM,
                temperature=0.3,  # Low temperature for consistent layout choices
                max_tokens=6000,
            )

            logger.info(
                f"Layout selection completed: {response.usage.total_tokens} tokens, "
                f"${response.usage.cost_usd:.6f}"
            )

            # Parse JSON response
            with_layouts = self._parse_json_response(response.content)

            # Validate layout selections
            self._validate_layouts(with_layouts)

            logger.info("Layouts selected successfully for all slides")

            return with_layouts

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}") from e

        except Exception as e:
            logger.error(f"Layout selection failed: {e}", exc_info=True)
            raise

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Extract from code block
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

        # Find JSON object
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])

        raise json.JSONDecodeError("No valid JSON found", content, 0)

    def _validate_layouts(self, with_layouts: dict[str, Any]):
        """Validate layout selections"""
        if "slides" not in with_layouts:
            raise ValueError("Response missing 'slides' field")

        valid_layouts = {
            "title",
            "content",
            "two_column",
            "image",
            "image_text",
            "quote",
            "section_header",
            "closing",
            "blank",
        }

        for idx, slide in enumerate(with_layouts["slides"]):
            if "layout" not in slide:
                raise ValueError(f"Slide {idx} missing 'layout' field")

            layout = slide["layout"]
            if layout not in valid_layouts:
                logger.warning(
                    f"Slide {idx} has invalid layout '{layout}', defaulting to 'content'"
                )
                slide["layout"] = "content"

        logger.debug("Layout validation passed")
