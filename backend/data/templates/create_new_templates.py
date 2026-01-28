"""
Generate strategic_consulting.pptx and visionary_story.pptx templates.

Approach: Use education_basic.pptx as base (12 standard layouts),
modify color theme and replace demo slides with appropriate content.
"""

import copy
import shutil
from pathlib import Path

from lxml import etree
from pptagent_pptx import Presentation
from pptagent_pptx.dml.color import RGBColor
from pptagent_pptx.enum.text import PP_ALIGN
from pptagent_pptx.util import Inches, Pt

TEMPLATES_DIR = Path(__file__).parent
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def set_color_theme(prs, scheme_name, colors):
    """
    Modify the color scheme in the presentation's theme.

    colors dict keys: dk1, lt1, dk2, lt2, accent1..accent6, hlink, folHlink
    Values are hex color strings like 'FF0000'.
    """
    sm_part = prs.slide_masters[0].part
    for rel in sm_part.rels.values():
        if "theme" in rel.reltype:
            theme_part = rel.target_part
            root = etree.fromstring(theme_part.blob)
            cs = root.find(".//a:clrScheme", NS)
            if cs is None:
                raise ValueError("Color scheme not found in theme")

            cs.set("name", scheme_name)

            for color_name, hex_val in colors.items():
                elem = cs.find(f"a:{color_name}", NS)
                if elem is not None:
                    # Remove existing children
                    for child in list(elem):
                        elem.remove(child)
                    # Add srgbClr
                    srgb = etree.SubElement(
                        elem,
                        f"{{{NS['a']}}}srgbClr",
                    )
                    srgb.set("val", hex_val)

            theme_part.blob = etree.tostring(
                root, xml_declaration=True, encoding="UTF-8", standalone=True
            )
            return

    raise ValueError("Theme part not found")


def clear_slides(prs):
    """Remove all existing slides from the presentation."""
    while len(prs.slides) > 0:
        rId = prs.slides._sldIdLst[0].get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        prs.part.drop_rel(rId)
        prs.slides._sldIdLst.remove(prs.slides._sldIdLst[0])


def add_slide(prs, layout_index, title_text=None, body_text=None, subtitle_text=None):
    """Add a slide with optional title, subtitle, and body text."""
    layout = prs.slide_layouts[layout_index]
    slide = prs.slides.add_slide(layout)

    for ph in slide.placeholders:
        ph_type = ph.placeholder_format.type
        if title_text and ph_type in (1, 3):  # TITLE or CENTER_TITLE
            ph.text = title_text
        elif subtitle_text and ph_type == 4:  # SUBTITLE
            ph.text = subtitle_text
        elif body_text and ph_type in (2, 7):  # BODY or OBJECT
            ph.text = body_text

    return slide


def set_slide_text_color(slide, color_hex):
    """Set text color for all text frames in a slide (best effort)."""
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    run.font.color.rgb = RGBColor.from_string(color_hex)


def create_strategic_consulting():
    """
    策略顧問模板 — 深藍、冷灰、白色調
    強調邏輯結構、MECE原則、圖表與數據展示
    """
    print("Creating strategic_consulting.pptx...")

    base_path = TEMPLATES_DIR / "education_basic.pptx"
    output_path = TEMPLATES_DIR / "strategic_consulting.pptx"

    prs = Presentation(str(base_path))

    # Set color theme: 深藍 + 冷灰 + 白色
    set_color_theme(
        prs,
        "Strategic Consulting",
        {
            "dk1": "0F172A",  # 極深藍（主文字）
            "lt1": "FFFFFF",  # 白色（亮底）
            "dk2": "1E3A5F",  # 深藍（標題用）
            "lt2": "F1F5F9",  # 極淺灰（次背景）
            "accent1": "1E3A5F",  # 深藍（主強調）
            "accent2": "475569",  # 冷灰（次強調）
            "accent3": "64748B",  # 中灰
            "accent4": "94A3B8",  # 淺灰
            "accent5": "0EA5E9",  # 亮藍（數據點綴）
            "accent6": "1E293B",  # 暗藍灰
            "hlink": "0284C7",  # 連結藍
            "folHlink": "6B7280",  # 已訪問灰
        },
    )

    # Clear existing slides and add consulting-style demo slides
    clear_slides(prs)

    # Slide 0: Title Slide (layout index 1 = "Title Slide")
    add_slide(
        prs,
        layout_index=1,
        title_text="策略分析報告",
        subtitle_text="年度策略規劃與業務回顧",
    )

    # Slide 1: Section Header (any layout with title)
    add_slide(
        prs,
        layout_index=4,  # Title Only
        title_text="執行摘要",
    )

    # Slide 2: Content slide (Title + Content)
    add_slide(
        prs,
        layout_index=2,  # Title, Content
        title_text="核心發現",
        body_text="關鍵洞察 1：市場分析結果\n關鍵洞察 2：競爭態勢評估\n關鍵洞察 3：策略建議方向\n關鍵洞察 4：執行計畫概要",
    )

    # Slide 3: Two-column (Title + 2 Content)
    add_slide(
        prs,
        layout_index=3,  # Title, 2 Content
        title_text="SWOT 分析",
        body_text="優勢 (S)\n• 品牌知名度\n• 技術領先\n\n劣勢 (W)\n• 市場覆蓋率\n• 成本結構",
    )

    # Slide 4: Closing
    add_slide(
        prs,
        layout_index=5,  # Centered Text
        subtitle_text="謝謝！\n如有任何問題，歡迎討論",
    )

    prs.save(str(output_path))
    print(f"  ✅ Created: {output_path.name} ({output_path.stat().st_size:,} bytes)")


def create_visionary_story():
    """
    願景敘事模板 — 暗色電影感，大氣留白
    TED 風格演講、品牌故事、願景發表
    """
    print("Creating visionary_story.pptx...")

    base_path = TEMPLATES_DIR / "education_basic.pptx"
    output_path = TEMPLATES_DIR / "visionary_story.pptx"

    prs = Presentation(str(base_path))

    # Set color theme: 暗底 + 高對比白字 + 溫暖點綴
    set_color_theme(
        prs,
        "Visionary Story",
        {
            "dk1": "F8FAFC",  # 亮色文字（暗底上用）
            "lt1": "0F172A",  # 暗色背景
            "dk2": "E2E8F0",  # 次亮色
            "lt2": "1E293B",  # 次暗底
            "accent1": "F8FAFC",  # 白色強調
            "accent2": "94A3B8",  # 冷灰
            "accent3": "64748B",  # 中灰
            "accent4": "F59E0B",  # 溫暖金黃（故事性點綴）
            "accent5": "EF4444",  # 情感紅
            "accent6": "334155",  # 深灰
            "hlink": "38BDF8",  # 亮藍連結
            "folHlink": "6B7280",  # 已訪問灰
        },
    )

    # Clear existing slides and add story-style demo slides
    clear_slides(prs)

    # Slide 0: Title (dramatic opening)
    add_slide(
        prs,
        layout_index=1,  # Title Slide
        title_text="改變的起點",
        subtitle_text="一個關於願景與行動的故事",
    )

    # Slide 1: Single statement (TED-style)
    add_slide(
        prs,
        layout_index=5,  # Centered Text
        subtitle_text="每一個偉大的改變，\n都始於一個簡單的信念。",
    )

    # Slide 2: Section
    add_slide(
        prs,
        layout_index=4,  # Title Only
        title_text="挑戰",
    )

    # Slide 3: Content
    add_slide(
        prs,
        layout_index=2,  # Title, Content
        title_text="我們面對的現實",
        body_text="產業正在經歷前所未有的變革\n傳統方法已無法應對新挑戰\n我們需要全新的思維模式",
    )

    # Slide 4: Insight statement
    add_slide(
        prs,
        layout_index=5,  # Centered Text
        subtitle_text="問題不在於「能不能」，\n而在於「敢不敢」。",
    )

    # Slide 5: Closing
    add_slide(
        prs,
        layout_index=1,  # Title Slide
        title_text="謝謝",
        subtitle_text="讓我們一起開始這段旅程",
    )

    prs.save(str(output_path))
    print(f"  ✅ Created: {output_path.name} ({output_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    create_strategic_consulting()
    create_visionary_story()
    print("\n✅ All new templates created!")
