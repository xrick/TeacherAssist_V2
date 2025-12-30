"""
Presentation domain models

Core data structures for presentation generation pipeline
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LayoutType(str, Enum):
    """Slide layout types"""

    TITLE = "title"
    CONTENT = "content"
    TWO_COLUMN = "two_column"
    IMAGE = "image"
    IMAGE_TEXT = "image_text"
    QUOTE = "quote"
    SECTION_HEADER = "section_header"
    CLOSING = "closing"
    BLANK = "blank"


class ContentType(str, Enum):
    """Content element types"""

    TEXT = "text"
    BULLET_LIST = "bullet_list"
    NUMBERED_LIST = "numbered_list"
    CODE_BLOCK = "code_block"
    TABLE = "table"
    IMAGE = "image"
    QUOTE = "quote"
    HEADING = "heading"


class ContentElement(BaseModel):
    """A single content element"""

    type: ContentType
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SlideContent(BaseModel):
    """Content for a single slide"""

    title: str
    elements: list[ContentElement] = Field(default_factory=list)
    notes: str | None = None
    layout: LayoutType = LayoutType.CONTENT
    metadata: dict[str, Any] = Field(default_factory=dict)


class PresentationMetadata(BaseModel):
    """Metadata for entire presentation"""

    title: str
    author: str | None = None
    topic: str | None = None
    audience: str | None = None
    duration_minutes: int | None = None
    template: str = "default.pptx"
    tags: list[str] = Field(default_factory=list)


class Presentation(BaseModel):
    """Complete presentation structure"""

    metadata: PresentationMetadata
    slides: list[SlideContent] = Field(default_factory=list)

    def slide_count(self) -> int:
        """Get total number of slides"""
        return len(self.slides)

    def add_slide(self, slide: SlideContent):
        """Add a slide to presentation"""
        self.slides.append(slide)

    def get_slide(self, index: int) -> SlideContent | None:
        """Get slide by index"""
        if 0 <= index < len(self.slides):
            return self.slides[index]
        return None
