# Template Directory

This directory contains PPTX template files used by the PPTAgent for presentation generation.

## Template Structure

Each template should include:
- **Master slides**: Title slide, content slides, section headers
- **Layouts**: Various layout options (title-only, title-content, two-column, etc.)
- **Theme**: Consistent color scheme, fonts, and styling
- **Placeholders**: Properly configured placeholders for dynamic content

## Required Templates

### 1. default.pptx
- General-purpose academic presentation template
- Clean, professional design
- Supports: title slides, bullet points, images, tables

### 2. educational.pptx
- Education-focused template with clear typography
- High contrast for readability
- Supports: learning objectives, activities, assessments

### 3. modern.pptx
- Contemporary design with gradient backgrounds
- Icon support and infographics
- Supports: data visualization, modern layouts

## Template Metadata

Each template should have a corresponding JSON file with:
```json
{
  "name": "Template Name",
  "description": "Template description",
  "layouts": ["title", "content", "two-column", "image", "closing"],
  "color_scheme": "primary color hex",
  "recommended_for": ["education", "business", "technical"]
}
```

## Usage

Templates are loaded by PPTAgent during initialization and selected based on:
1. User preference (if specified)
2. Content type detection
3. Default fallback (default.pptx)

## Adding New Templates

1. Create PPTX file with proper master slides
2. Add metadata JSON file
3. Test with sample content
4. Update this README with template details
