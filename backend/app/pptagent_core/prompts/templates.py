"""
Prompt templates for PPTAgent roles

Jinja2-based templates for each stage of the generation pipeline
"""

from jinja2 import Template

# System prompts for each role

SCHEMA_EXTRACTOR_SYSTEM = """You are an expert presentation structure analyzer.
Your task is to analyze markdown content and extract a structured schema for creating slides.

Focus on:
- Identifying logical slide boundaries
- Determining appropriate slide titles
- Categorizing content types (text, lists, code, tables, images)
- Estimating content density per slide
- Suggesting appropriate layouts

Output must be valid JSON only."""

CONTENT_ORGANIZER_SYSTEM = """You are an expert content organizer for presentations.
Your task is to organize extracted content into well-structured slides.

Focus on:
- One main idea per slide
- Balanced content distribution
- Logical flow and transitions
- Appropriate use of bullet points vs. paragraphs
- Code snippet placement and formatting

Output must be valid JSON only."""

LAYOUT_SELECTOR_SYSTEM = """You are an expert presentation layout designer.
Your task is to select the most appropriate layout for each slide based on its content.

Available layouts:
- title: Title slide with main heading and subtitle
- content: Standard content slide with title and body
- two_column: Two-column layout for comparisons
- image: Full image slide with caption
- image_text: Image with accompanying text
- quote: Centered quote or key message
- section_header: Section divider slide
- closing: Closing slide with summary or call-to-action

Focus on:
- Content type and density
- Visual hierarchy
- Engagement and variety
- Professional appearance

Output must be valid JSON only."""

EDITOR_SYSTEM = """You are an expert presentation content editor.
Your task is to refine and polish slide content for maximum impact.

Focus on:
- Concise, impactful language
- Clear and professional tone
- Proper grammar and punctuation
- Consistent formatting
- Audience-appropriate vocabulary
- Action-oriented messaging

Output must be valid JSON only."""

CODER_SYSTEM = """You are an expert in generating presentation code structures.
Your task is to generate the final presentation structure that can be converted to PPTX.

Focus on:
- Accurate content placement
- Proper formatting directives
- Image placeholders and paths
- Table structures
- Metadata preservation

Output must be valid JSON only."""


# User prompt templates

SCHEMA_EXTRACTOR_PROMPT = Template(
    """
Analyze the following markdown document and extract a presentation schema.

Document:
```markdown
{{ markdown_content }}
```

Extract:
1. Main title and optional subtitle
2. Logical sections and subsections
3. Content elements (headings, paragraphs, lists, code blocks, tables)
4. Suggested slide boundaries
5. Estimated slide count

Return a JSON object with this structure:
{
  "title": "main presentation title",
  "subtitle": "optional subtitle",
  "sections": [
    {
      "title": "section title",
      "slide_count": estimated_slides,
      "slides": [
        {
          "title": "slide title",
          "content_elements": ["type: heading/text/list/code/table"],
          "estimated_words": word_count
        }
      ]
    }
  ],
  "total_slides": number,
  "metadata": {
    "topic": "inferred topic",
    "audience": "inferred audience level"
  }
}
"""
)

CONTENT_ORGANIZER_PROMPT = Template(
    """
Organize the extracted schema into well-structured slide content.

Schema:
{{ schema_json }}

Guidelines:
- Maximum {{ max_slides }} slides
- Each slide should have 1 main idea
- Use bullet points for lists (3-5 points per slide)
- Keep text concise (max ~50 words per slide body)
- Place code blocks on dedicated slides
- Distribute content evenly

Return JSON with this structure:
{
  "slides": [
    {
      "title": "slide title",
      "layout_hint": "suggested layout type",
      "elements": [
        {
          "type": "text|bullet_list|code_block|table|image",
          "content": "element content",
          "metadata": {"language": "python"} // for code blocks
        }
      ],
      "notes": "optional speaker notes"
    }
  ]
}
"""
)

LAYOUT_SELECTOR_PROMPT = Template(
    """
Select the most appropriate layout for each slide based on its content.

Slides:
{{ slides_json }}

Available layouts:
- title: For opening slide
- content: Standard text/bullet point slide
- two_column: For comparisons or parallel content
- image: Slides with primary image focus
- image_text: Image with supporting text
- quote: Important quotes or key messages
- section_header: Section dividers
- closing: Summary or closing slide

Return JSON with updated slides including "layout" field:
{
  "slides": [
    {
      "title": "slide title",
      "layout": "selected_layout_type",
      "elements": [...],
      "layout_rationale": "why this layout was chosen"
    }
  ]
}
"""
)

EDITOR_PROMPT = Template(
    """
Refine and polish the content for each slide.

Slides:
{{ slides_json }}

Audience: {{ audience or "general professional" }}
Tone: {{ tone or "professional and engaging" }}

Guidelines:
- Make titles concise and impactful (max 8 words)
- Refine bullet points for clarity
- Ensure parallel structure in lists
- Fix grammar and punctuation
- Maintain consistent voice
- Add speaker notes where helpful

Return JSON with refined content:
{
  "slides": [
    {
      "title": "refined title",
      "layout": "layout_type",
      "elements": [...],  // refined content
      "notes": "enhanced speaker notes"
    }
  ]
}
"""
)

CODER_PROMPT = Template(
    """
Generate the final presentation structure for PPTX generation.

Refined slides:
{{ slides_json }}

Metadata:
{{ metadata_json }}

IMPORTANT: All "content" fields MUST be strings, not arrays.
For bullet_list or numbered_list types, format as a single string with newlines:
- Use "\\n" to separate bullet points
- Example: "Point 1\\nPoint 2\\nPoint 3"

Return complete presentation JSON:
{
  "metadata": {
    "title": "presentation title",
    "author": "{{ author or 'TeacherAssist' }}",
    "template": "{{ template or 'default.pptx' }}"
  },
  "slides": [
    {
      "title": "slide title",
      "layout": "layout_type",
      "elements": [
        {
          "type": "text|bullet_list|numbered_list|code_block|table|image",
          "content": "formatted content as STRING (use \\n for multiple lines)",
          "style": {"font_size": 18, "color": "#000000"},
          "metadata": {}
        }
      ],
      "notes": "speaker notes",
      "background": "optional background color/image"
    }
  ]
}
"""
)


def render_schema_extractor_prompt(markdown_content: str) -> str:
    """Render schema extractor prompt"""
    return SCHEMA_EXTRACTOR_PROMPT.render(markdown_content=markdown_content)


def render_content_organizer_prompt(schema_json: str, max_slides: int = 50) -> str:
    """Render content organizer prompt"""
    return CONTENT_ORGANIZER_PROMPT.render(schema_json=schema_json, max_slides=max_slides)


def render_layout_selector_prompt(slides_json: str) -> str:
    """Render layout selector prompt"""
    return LAYOUT_SELECTOR_PROMPT.render(slides_json=slides_json)


def render_editor_prompt(
    slides_json: str, audience: str | None = None, tone: str | None = None
) -> str:
    """Render editor prompt"""
    return EDITOR_PROMPT.render(slides_json=slides_json, audience=audience, tone=tone)


def render_coder_prompt(
    slides_json: str, metadata_json: str, author: str | None = None, template: str | None = None
) -> str:
    """Render coder prompt"""
    return CODER_PROMPT.render(
        slides_json=slides_json,
        metadata_json=metadata_json,
        author=author,
        template=template,
    )
