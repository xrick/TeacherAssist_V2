"""
Markdown document parsing utilities

Parses markdown content into structured format for presentation generation
"""

import re

from pydantic import BaseModel


class MarkdownSection(BaseModel):
    """A section from markdown document"""

    level: int  # Heading level (1-6)
    title: str
    content: str
    line_start: int
    line_end: int


class MarkdownDocument(BaseModel):
    """Parsed markdown document structure"""

    raw_content: str
    sections: list[MarkdownSection]
    metadata: dict = {}

    @property
    def total_lines(self) -> int:
        """Total number of lines in document"""
        return len(self.raw_content.split("\n"))


class MarkdownParser:
    """Parse markdown documents into structured format"""

    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    @staticmethod
    def parse(markdown_content: str) -> MarkdownDocument:
        """
        Parse markdown content into structured document

        Args:
            markdown_content: Raw markdown text

        Returns:
            MarkdownDocument with parsed sections
        """
        lines = markdown_content.split("\n")
        sections: list[MarkdownSection] = []

        # Find all headings
        headings: list[tuple[int, int, str]] = []  # (line_num, level, title)
        for i, line in enumerate(lines):
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                headings.append((i, level, title))

        # Extract sections between headings
        for idx, (line_num, level, title) in enumerate(headings):
            # Determine section end
            if idx + 1 < len(headings):
                end_line = headings[idx + 1][0]
            else:
                end_line = len(lines)

            # Extract section content (excluding heading line)
            content_lines = lines[line_num + 1 : end_line]
            content = "\n".join(content_lines).strip()

            section = MarkdownSection(
                level=level,
                title=title,
                content=content,
                line_start=line_num,
                line_end=end_line,
            )
            sections.append(section)

        # Handle content before first heading
        if headings and headings[0][0] > 0:
            intro_content = "\n".join(lines[: headings[0][0]]).strip()
            if intro_content:
                sections.insert(
                    0,
                    MarkdownSection(
                        level=0,
                        title="Introduction",
                        content=intro_content,
                        line_start=0,
                        line_end=headings[0][0],
                    ),
                )

        return MarkdownDocument(raw_content=markdown_content, sections=sections)

    @staticmethod
    def extract_metadata(markdown_content: str) -> dict:
        """
        Extract YAML frontmatter metadata if present

        Args:
            markdown_content: Raw markdown text

        Returns:
            Dictionary of metadata
        """
        metadata = {}

        # Check for YAML frontmatter
        if markdown_content.startswith("---"):
            parts = markdown_content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                # Simple key-value parsing (not full YAML)
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip().strip("\"'")

        return metadata

    @staticmethod
    def count_words(text: str) -> int:
        """Count words in text"""
        return len(text.split())

    @staticmethod
    def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
        """
        Estimate reading time in minutes

        Args:
            text: Text content
            words_per_minute: Average reading speed

        Returns:
            Estimated minutes
        """
        words = MarkdownParser.count_words(text)
        return max(1, words // words_per_minute)
