"""
Editor Role

Fourth stage: Refines and polishes slide content
"""

import json
import logging
from typing import Any

from app.pptagent_core.prompts.templates import (
    EDITOR_SYSTEM,
    render_editor_prompt,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class Editor:
    """
    Refines and polishes slide content

    This is the fourth stage in the PPTAgent pipeline. It:
    - Makes titles concise and impactful
    - Refines bullet points for clarity
    - Ensures parallel structure
    - Fixes grammar and punctuation
    - Adds helpful speaker notes
    """

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def edit(
        self,
        slides_with_layouts: dict[str, Any],
        audience: str | None = None,
        tone: str | None = None,
    ) -> dict[str, Any]:
        """
        Edit and refine slide content

        Args:
            slides_with_layouts: Slides with layout selections
            audience: Target audience (e.g., "professionals", "students")
            tone: Desired tone (e.g., "professional", "casual")

        Returns:
            Dictionary with refined slide content

        Raises:
            ValueError: If editing fails or returns invalid JSON
            RuntimeError: If LLM generation fails
        """
        logger.info(
            f"Editing {len(slides_with_layouts.get('slides', []))} slides "
            f"(audience: {audience or 'general'}, tone: {tone or 'professional'})..."
        )

        # Convert slides to JSON string for prompt
        slides_json = json.dumps(slides_with_layouts, indent=2)

        # Render prompt
        user_prompt = render_editor_prompt(slides_json, audience, tone)

        # Generate refined content
        try:
            response = await self.llm.generate(
                prompt=user_prompt,
                system_prompt=EDITOR_SYSTEM,
                temperature=0.5,  # Moderate creativity for refinement
                max_tokens=8000,
            )

            logger.info(
                f"Editing completed: {response.usage.total_tokens} tokens, "
                f"${response.usage.cost_usd:.6f}"
            )

            # Parse JSON response
            refined = self._parse_json_response(response.content)

            # Validate refined content
            self._validate_refined_content(refined)

            logger.info("Content refined successfully")

            return refined

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}") from e

        except Exception as e:
            logger.error(f"Editing failed: {e}", exc_info=True)
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

    def _validate_refined_content(self, refined: dict[str, Any]):
        """Validate refined content"""
        if "slides" not in refined:
            raise ValueError("Refined content missing 'slides' field")

        for idx, slide in enumerate(refined["slides"]):
            if "title" not in slide:
                raise ValueError(f"Slide {idx} missing 'title'")

            if "layout" not in slide:
                raise ValueError(f"Slide {idx} missing 'layout'")

            if "elements" not in slide:
                raise ValueError(f"Slide {idx} missing 'elements'")

            # Check title length (should be concise)
            title = slide["title"]
            word_count = len(title.split())
            if word_count > 12:
                logger.warning(f"Slide {idx} title is long ({word_count} words): '{title}'")

        logger.debug("Refined content validation passed")
