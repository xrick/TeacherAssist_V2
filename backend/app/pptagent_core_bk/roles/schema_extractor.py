"""
Schema Extractor Role

First stage: Analyzes markdown and extracts presentation structure schema
"""

import json
import logging
from typing import Any

from app.pptagent_core.prompts.templates import (
    SCHEMA_EXTRACTOR_SYSTEM,
    render_schema_extractor_prompt,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class SchemaExtractor:
    """
    Analyzes markdown content and extracts structured schema

    This is the first stage in the PPTAgent pipeline. It identifies:
    - Presentation title and structure
    - Logical sections and slide boundaries
    - Content types (text, lists, code, tables)
    - Suggested slide count
    """

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def extract(self, markdown_content: str) -> dict[str, Any]:
        """
        Extract presentation schema from markdown

        Args:
            markdown_content: Raw markdown text

        Returns:
            Dictionary with extracted schema

        Raises:
            ValueError: If extraction fails or returns invalid JSON
            RuntimeError: If LLM generation fails
        """
        logger.info(f"Extracting schema from markdown ({len(markdown_content)} chars)...")

        # Render prompt
        user_prompt = render_schema_extractor_prompt(markdown_content)

        # Generate schema
        try:
            response = await self.llm.generate(
                prompt=user_prompt,
                system_prompt=SCHEMA_EXTRACTOR_SYSTEM,
                temperature=0.3,  # Low temperature for structured output
                max_tokens=4000,
            )

            logger.info(
                f"Schema extraction completed: {response.usage.total_tokens} tokens, "
                f"${response.usage.cost_usd:.6f}"
            )

            # Parse JSON response
            schema = self._parse_json_response(response.content)

            # Validate schema structure
            self._validate_schema(schema)

            logger.info(
                f"Schema extracted successfully: {schema.get('total_slides', 'unknown')} slides"
            )

            return schema

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(
                f"Response content: {response.content if 'response' in locals() else 'N/A'}"
            )
            raise ValueError(f"Invalid JSON response from LLM: {e}") from e

        except Exception as e:
            logger.error(f"Schema extraction failed: {e}", exc_info=True)
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
            # Extract content between ```json and ```
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                json_str = content[start:end].strip()
                return json.loads(json_str)

        elif "```" in content:
            # Extract content between ``` and ```
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                json_str = content[start:end].strip()
                return json.loads(json_str)

        # If all else fails, try to find JSON object
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = content[start:end]
            return json.loads(json_str)

        # Give up
        raise json.JSONDecodeError("No valid JSON found in response", content, 0)

    def _validate_schema(self, schema: dict[str, Any]):
        """
        Validate schema structure

        Args:
            schema: Parsed schema dictionary

        Raises:
            ValueError: If schema is invalid
        """
        required_fields = ["title", "sections", "total_slides"]

        for field in required_fields:
            if field not in schema:
                raise ValueError(f"Schema missing required field: {field}")

        if not isinstance(schema["sections"], list):
            raise ValueError("Schema 'sections' must be a list")

        if not isinstance(schema["total_slides"], int):
            raise ValueError("Schema 'total_slides' must be an integer")

        if schema["total_slides"] < 1:
            raise ValueError("Schema must have at least 1 slide")

        # Validate sections
        for idx, section in enumerate(schema["sections"]):
            if "title" not in section:
                raise ValueError(f"Section {idx} missing 'title'")
            if "slides" not in section:
                raise ValueError(f"Section {idx} missing 'slides'")

        logger.debug(f"Schema validation passed: {len(schema['sections'])} sections")
