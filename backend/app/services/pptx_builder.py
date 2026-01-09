"""
PPTX Builder Service

Converts Presentation model to actual PPTX file using pptagent_pptx
"""

import io
import logging
from pathlib import Path

from pptagent_pptx import Presentation as PPTXPresentation
from pptagent_pptx.util import Inches

from app.pptagent_core.presentation.models import (
    ContentType,
    ImagePosition,
    LayoutType,
    Presentation,
    SlideContent,
    SlideImage,
)

logger = logging.getLogger(__name__)


class PPTXBuilder:
    """
    Builds PPTX files from Presentation model

    Converts our domain model to actual PowerPoint files using pptagent_pptx
    """

    # Layout index mapping (standard PowerPoint layouts)
    LAYOUT_MAP = {
        LayoutType.TITLE: 0,  # Title Slide
        LayoutType.SECTION_HEADER: 2,  # Section Header
        LayoutType.CONTENT: 1,  # Title and Content
        LayoutType.TWO_COLUMN: 3,  # Two Content
        LayoutType.IMAGE: 6,  # Blank
        LayoutType.IMAGE_TEXT: 8,  # Picture with Caption
        LayoutType.QUOTE: 2,  # Section Header (reuse for quote)
        LayoutType.CLOSING: 0,  # Title Slide (reuse for closing)
        LayoutType.BLANK: 6,  # Blank
    }

    # Default image position by layout type
    LAYOUT_IMAGE_POSITION = {
        LayoutType.TITLE: ImagePosition.CENTER,
        LayoutType.SECTION_HEADER: ImagePosition.BACKGROUND,
        LayoutType.CONTENT: ImagePosition.RIGHT,
        LayoutType.TWO_COLUMN: ImagePosition.CENTER,
        LayoutType.IMAGE: ImagePosition.CENTER,
        LayoutType.IMAGE_TEXT: ImagePosition.LEFT,
        LayoutType.QUOTE: ImagePosition.BACKGROUND,
        LayoutType.CLOSING: ImagePosition.CENTER,
        LayoutType.BLANK: ImagePosition.CENTER,
    }

    # Standard slide dimensions (in inches) - 16:9 widescreen
    SLIDE_WIDTH = 13.333
    SLIDE_HEIGHT = 7.5

    def __init__(self, template_path: Path | None = None):
        """
        Initialize builder

        Args:
            template_path: Optional path to PPTX template file
        """
        self.template_path = template_path

    def build(self, presentation: Presentation) -> bytes:
        """
        Build PPTX file from Presentation model

        Args:
            presentation: Presentation domain model

        Returns:
            PPTX file as bytes

        Raises:
            ValueError: If build fails
        """
        logger.info(f"Building PPTX: {presentation.metadata.title}")

        try:
            # Create presentation from template or default
            if self.template_path and self.template_path.exists():
                pptx = PPTXPresentation(str(self.template_path))
                logger.debug(f"Using template: {self.template_path}")
            else:
                pptx = PPTXPresentation()
                logger.debug("Using default template")

            # Add slides
            for idx, slide_content in enumerate(presentation.slides):
                self._add_slide(pptx, slide_content, idx)

            # Set presentation properties
            pptx.core_properties.title = presentation.metadata.title
            if presentation.metadata.author:
                pptx.core_properties.author = presentation.metadata.author

            # Save to bytes
            buffer = io.BytesIO()
            pptx.save(buffer)
            buffer.seek(0)
            pptx_bytes = buffer.read()

            logger.info(
                f"PPTX built successfully: {len(pptx_bytes)} bytes, "
                f"{len(presentation.slides)} slides"
            )

            return pptx_bytes

        except Exception as e:
            logger.error(f"Failed to build PPTX: {e}", exc_info=True)
            raise ValueError(f"Failed to build PPTX: {e}") from e

    def _add_slide(self, pptx: PPTXPresentation, slide_content: SlideContent, index: int):
        """
        Add a slide to the presentation

        Args:
            pptx: PPTX presentation object
            slide_content: Slide content model
            index: Slide index for logging
        """
        # Get layout index
        layout_idx = self.LAYOUT_MAP.get(slide_content.layout, 1)

        # Ensure layout index is within bounds
        if layout_idx >= len(pptx.slide_layouts):
            layout_idx = 1  # Default to Title and Content

        # Add slide with layout
        layout = pptx.slide_layouts[layout_idx]
        slide = pptx.slides.add_slide(layout)

        # Set title if slide has title placeholder
        if slide.shapes.title:
            slide.shapes.title.text = slide_content.title

        # Find content placeholder and add content
        content_placeholder = self._find_content_placeholder(slide)

        if content_placeholder and slide_content.elements:
            # Build content text from elements
            content_text = self._build_content_text(slide_content)

            # Set content
            if hasattr(content_placeholder, "text_frame"):
                tf = content_placeholder.text_frame
                tf.clear()  # Clear existing content

                # Add paragraphs
                lines = content_text.split("\n")
                for i, line in enumerate(lines):
                    if i == 0:
                        p = tf.paragraphs[0]
                    else:
                        p = tf.add_paragraph()
                    p.text = line.strip()
                    p.level = 0

        # Add images if present
        if slide_content.images:
            for image in slide_content.images:
                self._add_image_to_slide(slide, image, slide_content.layout)

        # Build notes with image attribution
        notes_parts = []
        if slide_content.notes:
            notes_parts.append(slide_content.notes)

        # Add image attributions to notes
        if slide_content.images:
            notes_parts.append("\n--- Image Credits ---")
            for image in slide_content.images:
                attribution = f"Photo by {image.photographer} on Pexels ({image.pexels_url})"
                notes_parts.append(attribution)

        if notes_parts:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = "\n".join(notes_parts)

        logger.debug(f"Added slide {index + 1}: {slide_content.title[:30]}...")

    def _find_content_placeholder(self, slide):
        """Find content placeholder in slide"""
        from pptagent_pptx.enum.shapes import PP_PLACEHOLDER

        for shape in slide.shapes:
            if shape.is_placeholder:
                ph_type = shape.placeholder_format.type
                if ph_type in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT, PP_PLACEHOLDER.SUBTITLE):
                    return shape
        return None

    def _build_content_text(self, slide_content: SlideContent) -> str:
        """
        Build content text from slide elements

        Args:
            slide_content: Slide content model

        Returns:
            Formatted text content
        """
        lines = []

        for element in slide_content.elements:
            content = element.content

            if element.type == ContentType.BULLET_LIST:
                # Format as bullet points
                for item in content.split("\n"):
                    item = item.strip()
                    if item:
                        # Remove existing bullet markers
                        item = item.lstrip("•-*").strip()
                        lines.append(f"• {item}")

            elif element.type == ContentType.NUMBERED_LIST:
                # Format as numbered list
                items = [i.strip() for i in content.split("\n") if i.strip()]
                for i, item in enumerate(items, 1):
                    # Remove existing number markers
                    item = item.lstrip("0123456789.)").strip()
                    lines.append(f"{i}. {item}")

            elif element.type == ContentType.CODE_BLOCK:
                # Format code with monospace indication
                lines.append(content)

            elif element.type == ContentType.TABLE:
                # Simple table representation
                lines.append(content)

            elif element.type == ContentType.QUOTE:
                # Format as quote
                lines.append(f'"{content}"')

            else:
                # TEXT, HEADING, etc.
                lines.append(content)

        return "\n".join(lines)

    def _add_image_to_slide(
        self,
        slide,
        image: SlideImage,
        layout: LayoutType,
    ):
        """
        Add an image to a slide.

        Args:
            slide: PPTX slide object
            image: SlideImage with file path and metadata
            layout: Slide layout type for position determination
        """
        image_path = Path(image.file_path)
        if not image_path.exists():
            logger.warning(f"Image file not found: {image_path}")
            return

        # Determine position
        position = image.position
        if position == ImagePosition.AUTO:
            position = self.LAYOUT_IMAGE_POSITION.get(layout, ImagePosition.RIGHT)

        # Calculate image dimensions and position based on layout
        left, top, width, height = self._calculate_image_bounds(position, layout)

        try:
            slide.shapes.add_picture(
                str(image_path),
                Inches(left),
                Inches(top),
                width=Inches(width),
                height=Inches(height),
            )
            logger.debug(
                f"Added image {image.image_id} at position {position.value} "
                f"({width:.1f}x{height:.1f} inches)"
            )
        except Exception as e:
            logger.error(f"Failed to add image to slide: {e}")

    def _calculate_image_bounds(
        self,
        position: ImagePosition,
        layout: LayoutType,
    ) -> tuple[float, float, float, float]:
        """
        Calculate image bounds (left, top, width, height) in inches.

        Args:
            position: Image position on slide
            layout: Slide layout type

        Returns:
            Tuple of (left, top, width, height) in inches
        """
        # Margins and common dimensions
        margin = 0.5
        title_height = 1.2  # Space for title

        # Available space after margins
        available_width = self.SLIDE_WIDTH - (2 * margin)
        available_height = self.SLIDE_HEIGHT - title_height - margin

        if position == ImagePosition.RIGHT:
            # Right side: 40% of width, full available height
            width = available_width * 0.4
            height = available_height * 0.8
            left = self.SLIDE_WIDTH - margin - width
            top = title_height + (available_height - height) / 2

        elif position == ImagePosition.LEFT:
            # Left side: 40% of width
            width = available_width * 0.4
            height = available_height * 0.8
            left = margin
            top = title_height + (available_height - height) / 2

        elif position == ImagePosition.TOP:
            # Top area: 60% width, 40% height
            width = available_width * 0.6
            height = available_height * 0.4
            left = (self.SLIDE_WIDTH - width) / 2
            top = title_height

        elif position == ImagePosition.BOTTOM:
            # Bottom area: 60% width, 40% height
            width = available_width * 0.6
            height = available_height * 0.4
            left = (self.SLIDE_WIDTH - width) / 2
            top = self.SLIDE_HEIGHT - margin - height

        elif position == ImagePosition.CENTER:
            # Center: 50% of available space
            width = available_width * 0.5
            height = available_height * 0.6
            left = (self.SLIDE_WIDTH - width) / 2
            top = title_height + (available_height - height) / 2

        elif position == ImagePosition.BACKGROUND:
            # Full slide background
            width = self.SLIDE_WIDTH
            height = self.SLIDE_HEIGHT
            left = 0
            top = 0

        else:
            # Default to right
            width = available_width * 0.4
            height = available_height * 0.8
            left = self.SLIDE_WIDTH - margin - width
            top = title_height + (available_height - height) / 2

        return left, top, width, height


# Singleton instance
_builder: PPTXBuilder | None = None


def get_pptx_builder(template_path: Path | None = None) -> PPTXBuilder:
    """
    Get PPTX builder instance

    Args:
        template_path: Optional template path

    Returns:
        PPTXBuilder instance
    """
    global _builder
    if _builder is None or template_path:
        _builder = PPTXBuilder(template_path)
    return _builder
