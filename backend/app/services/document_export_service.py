"""
Document Export Service

Exports teaching scripts to PDF and Word formats.
"""

import logging
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from fpdf import FPDF

from app.core.config import settings
from app.services.script_service import PresentationScript, SlideScript

logger = logging.getLogger(__name__)


class ScriptPDF(FPDF):
    """Custom PDF class for script export."""

    def __init__(self, title: str):
        super().__init__()
        self.title = title
        self._setup_fonts()

    def _setup_fonts(self):
        """Setup fonts for Chinese support."""
        # Use built-in fonts that support basic characters
        # For full Chinese support, would need to add Chinese font files
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """PDF header."""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, self.title[:50], align="L")
        self.ln(5)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        """PDF footer."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


class DocumentExportService:
    """
    Service for exporting scripts to PDF and Word formats.

    Features:
    - PDF export with proper formatting
    - Word (.docx) export with styles
    - Chinese text support
    - Section formatting for different script elements
    """

    def __init__(self, output_path: Path | None = None):
        """
        Initialize export service.

        Args:
            output_path: Base path for output files
        """
        self.output_path = output_path or settings.output_storage_path

    async def export_to_pdf(
        self,
        script: PresentationScript,
        presentation_id: str,
    ) -> Path:
        """
        Export script to PDF format.

        Args:
            script: PresentationScript to export
            presentation_id: Presentation ID for file naming

        Returns:
            Path to generated PDF file
        """
        logger.info(f"Exporting script to PDF: {script.title}")

        # Create output directory
        output_dir = self.output_path / presentation_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "script.pdf"

        # Create PDF
        pdf = ScriptPDF(script.title)
        pdf.alias_nb_pages()
        pdf.add_page()

        # Title page
        pdf.set_font("Helvetica", "B", 24)
        pdf.cell(0, 20, "", ln=True)  # Spacer
        pdf.multi_cell(0, 15, script.title, align="C")

        pdf.set_font("Helvetica", "", 14)
        pdf.cell(0, 10, "", ln=True)
        pdf.cell(0, 10, f"Total Duration: {script.total_minutes:.0f} minutes", align="C", ln=True)
        pdf.cell(0, 10, f"Slides: {len(script.scripts)}", align="C", ln=True)

        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 20, "", ln=True)
        pdf.cell(
            0,
            10,
            f"Generated: {script.generated_at.strftime('%Y-%m-%d %H:%M')}",
            align="C",
            ln=True,
        )

        # Content pages
        for slide_script in script.scripts:
            self._add_slide_to_pdf(pdf, slide_script)

        # Save PDF
        pdf.output(str(output_file))

        logger.info(f"PDF exported: {output_file}")
        return output_file

    def _add_slide_to_pdf(self, pdf: ScriptPDF, slide: SlideScript):
        """Add a slide script to PDF."""
        pdf.add_page()

        # Slide header
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(0, 102, 204)
        header = f"Slide {slide.slide_index + 1}: {slide.slide_title}"
        pdf.multi_cell(0, 10, header[:80])

        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, f"Estimated Time: {slide.estimated_minutes:.1f} minutes", ln=True)
        pdf.ln(5)

        # Lecture content
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, "Lecture Content:", ln=True)

        pdf.set_font("Helvetica", "", 11)
        # Handle long text by splitting into chunks
        content = slide.lecture_content or "(No content)"
        self._add_multiline_text(pdf, content)
        pdf.ln(5)

        # Teaching tips
        if slide.teaching_tips:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 128, 0)
            pdf.cell(0, 8, "Teaching Tips:", ln=True)

            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(0, 0, 0)
            for tip in slide.teaching_tips:
                pdf.cell(5)  # Indent
                pdf.multi_cell(0, 6, f"* {tip}")
            pdf.ln(3)

        # Interactive Q&A
        if slide.interaction_qa:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(204, 102, 0)
            pdf.cell(0, 8, "Interactive Q&A:", ln=True)

            pdf.set_text_color(0, 0, 0)
            for qa in slide.interaction_qa:
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(5)
                pdf.multi_cell(0, 6, f"Q: {qa.question}")

                if qa.expected_answers:
                    pdf.set_font("Helvetica", "I", 10)
                    pdf.cell(10)
                    pdf.multi_cell(0, 6, f"Expected: {', '.join(qa.expected_answers)}")
            pdf.ln(3)

        # Transition
        if slide.transition:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(128, 0, 128)
            pdf.cell(0, 8, "Transition:", ln=True)

            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, slide.transition)

    def _add_multiline_text(self, pdf: FPDF, text: str, max_chars: int = 2000):
        """Add multiline text handling encoding issues."""
        # Truncate very long text
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        # Replace problematic characters
        text = text.encode("latin-1", errors="replace").decode("latin-1")

        pdf.multi_cell(0, 6, text)

    async def export_to_docx(
        self,
        script: PresentationScript,
        presentation_id: str,
    ) -> Path:
        """
        Export script to Word (.docx) format.

        Args:
            script: PresentationScript to export
            presentation_id: Presentation ID for file naming

        Returns:
            Path to generated DOCX file
        """
        logger.info(f"Exporting script to DOCX: {script.title}")

        # Create output directory
        output_dir = self.output_path / presentation_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "script.docx"

        # Create document
        doc = Document()

        # Setup styles
        self._setup_docx_styles(doc)

        # Title
        title_para = doc.add_heading(script.title, level=0)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Metadata
        meta_para = doc.add_paragraph()
        meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        meta_run = meta_para.add_run(
            f"Total Duration: {script.total_minutes:.0f} minutes | "
            f"Slides: {len(script.scripts)}"
        )
        meta_run.font.size = Pt(12)
        meta_run.font.color.rgb = RGBColor(100, 100, 100)

        doc.add_paragraph()  # Spacer

        # Table of contents hint
        toc_para = doc.add_paragraph()
        toc_para.add_run("Contents:").bold = True
        for slide in script.scripts:
            doc.add_paragraph(
                f"Slide {slide.slide_index + 1}: {slide.slide_title} "
                f"({slide.estimated_minutes:.1f} min)",
                style="List Bullet",
            )

        doc.add_page_break()

        # Add each slide
        for slide_script in script.scripts:
            self._add_slide_to_docx(doc, slide_script)
            doc.add_page_break()

        # Save document
        doc.save(str(output_file))

        logger.info(f"DOCX exported: {output_file}")
        return output_file

    def _setup_docx_styles(self, doc: Document):
        """Setup custom styles for the document."""
        styles = doc.styles

        # Ensure Heading styles exist with proper formatting
        try:
            h1_style = styles["Heading 1"]
            h1_style.font.size = Pt(18)
            h1_style.font.color.rgb = RGBColor(0, 102, 204)
        except KeyError:
            pass

        try:
            h2_style = styles["Heading 2"]
            h2_style.font.size = Pt(14)
            h2_style.font.color.rgb = RGBColor(0, 128, 0)
        except KeyError:
            pass

    def _add_slide_to_docx(self, doc: Document, slide: SlideScript):
        """Add a slide script to Word document."""

        # Slide header
        header = f"Slide {slide.slide_index + 1}: {slide.slide_title}"
        heading = doc.add_heading(header, level=1)

        # Time estimate
        time_para = doc.add_paragraph()
        time_run = time_para.add_run(f"⏱️ Estimated Time: {slide.estimated_minutes:.1f} minutes")
        time_run.font.italic = True
        time_run.font.color.rgb = RGBColor(100, 100, 100)

        doc.add_paragraph()  # Spacer

        # Lecture content
        doc.add_heading("📖 Lecture Content", level=2)
        content_para = doc.add_paragraph(slide.lecture_content or "(No content)")
        content_para.paragraph_format.line_spacing = 1.5

        # Teaching tips
        if slide.teaching_tips:
            doc.add_heading("💡 Teaching Tips", level=2)
            for tip in slide.teaching_tips:
                doc.add_paragraph(tip, style="List Bullet")

        # Interactive Q&A
        if slide.interaction_qa:
            doc.add_heading("❓ Interactive Q&A", level=2)
            for qa in slide.interaction_qa:
                q_para = doc.add_paragraph()
                q_run = q_para.add_run(f"Q: {qa.question}")
                q_run.bold = True

                if qa.expected_answers:
                    a_para = doc.add_paragraph()
                    a_para.paragraph_format.left_indent = Inches(0.5)
                    a_run = a_para.add_run(f"Expected Answers: {', '.join(qa.expected_answers)}")
                    a_run.italic = True

        # Transition
        if slide.transition:
            doc.add_heading("🔗 Transition", level=2)
            trans_para = doc.add_paragraph(slide.transition)
            trans_para.paragraph_format.left_indent = Inches(0.25)
            for run in trans_para.runs:
                run.italic = True


# Global instance
_export_service: DocumentExportService | None = None


def get_export_service() -> DocumentExportService:
    """Get or create global export service instance."""
    global _export_service
    if _export_service is None:
        _export_service = DocumentExportService()
    return _export_service
