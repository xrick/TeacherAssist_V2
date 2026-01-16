"""
Slide Builder Role

Stage 3: Builds the final PPTX file from template and content
Enhanced with Layout Engine for Auto-fit and Smart Image Placement
"""

import io
import logging
from pathlib import Path
from typing import Any

from pptx import Presentation as PptxPresentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.util import Inches

# Import Layout Engine components
from app.pptagent_core.layout_engine.auto_fitter import AutoFitter

logger = logging.getLogger(__name__)


class SlideBuilder:
    """
    建構最終 PPTX 檔案

    Features:
    - Smart Layout Engine (Auto-fit text)
    - Dynamic Image Placement
    - Template Integrity Preservation
    """

    # 略過的 Placeholder 類型
    SKIP_TYPES = {
        PP_PLACEHOLDER.FOOTER,
        PP_PLACEHOLDER.DATE,
        PP_PLACEHOLDER.SLIDE_NUMBER,
    }

    def __init__(self, template_path: Path):
        self.template_path = template_path
        # 初始化時先設為 None，建立時再讀取
        self.slide_width = None
        self.slide_height = None

    def build(
        self,
        content: dict[str, Any],
        master_index: int = 0,
    ) -> bytes:
        logger.info(f"建構 PPTX (Enhanced): {self.template_path.name}")

        prs = PptxPresentation(str(self.template_path))

        # 讀取投影片尺寸，供排版引擎使用
        self.slide_width = prs.slide_width
        self.slide_height = prs.slide_height

        self._clear_slides(prs)

        master = prs.slide_masters[master_index]
        layouts = list(master.slide_layouts)

        for slide_data in content.get("slides", []):
            layout_idx = slide_data.get("layout_index", 1)
            if layout_idx >= len(layouts):
                layout_idx = 1

            layout = layouts[layout_idx]
            slide = prs.slides.add_slide(layout)

            # 1. 填入文字內容 (使用 AutoFitter)
            self._fill_slide_content(slide, slide_data)

            # 2. 加入圖片 (新增功能)
            images = slide_data.get("images", [])
            if images:
                self._place_images(slide, images, slide_data.get("layout", "content"))

            logger.debug(f"Slide {slide_data.get('index', '?')}: {layout.name} built")

        buffer = io.BytesIO()
        prs.save(buffer)
        buffer.seek(0)
        pptx_bytes = buffer.read()

        logger.info(
            f"PPTX 建構完成: {len(content.get('slides', []))} 張投影片, {len(pptx_bytes):,} bytes"
        )

        return pptx_bytes

    def _clear_slides(self, prs: PptxPresentation) -> None:
        for i in range(len(prs.slides) - 1, -1, -1):
            rId = prs.slides._sldIdLst[i].rId
            prs.part.drop_rel(rId)
            del prs.slides._sldIdLst[i]

    def _fill_slide_content(self, slide, slide_data: dict[str, Any]) -> None:
        """填入單張投影片的內容，使用 AutoFitter"""
        content_map = {ph["idx"]: ph for ph in slide_data.get("placeholders", [])}

        for shape in slide.shapes:
            if not shape.is_placeholder:
                continue

            ph_format = shape.placeholder_format
            if ph_format.type in self.SKIP_TYPES:
                continue

            ph_idx = ph_format.idx
            ph_data = content_map.get(ph_idx)

            if not ph_data:
                # 清除未使用的 placeholder 以保持整潔
                if shape.has_text_frame:
                    shape.text_frame.clear()
                continue

            content_value = ph_data.get("content", "")

            if shape.has_text_frame:
                # 將列表內容轉換為字串以便測量
                text_str = ""
                if isinstance(content_value, list):
                    text_str = "\n".join(str(x) for x in content_value)
                else:
                    text_str = str(content_value)

                # 使用 AutoFitter 替代直接賦值
                # 策略：標題允許較大字級 (44pt)，內文較小 (24pt)
                is_title = (
                    ph_format.type == PP_PLACEHOLDER.TITLE
                    or ph_format.type == PP_PLACEHOLDER.CENTER_TITLE
                )
                max_size = 44 if is_title else 24

                # TODO: 可以從 Template 讀取該 Placeholder 原本的字體名稱
                # 目前暫時統一使用 Arial (因為有 fallback 保護)
                AutoFitter.fit_text(
                    shape.text_frame, text_str, font_name="Arial", max_font_size=max_size
                )

    def _place_images(self, slide, images: list, layout_type: str):
        """
        動態配置圖片位置，避免與文字重疊
        """
        if not images:
            return

        # 暫時只處理第一張圖片，避免過度擁擠
        image_data = images[0]
        # 注意：這裡需適配 models.py 定義的結構 (SlideImage -> dict)
        # 如果是 Pydantic model dump 出來的 dict，欄位是 snake_case
        img_path = image_data.get("file_path")

        if not img_path or not Path(img_path).exists():
            logger.warning(f"Image not found: {img_path}")
            return

        # 預設排版參數 (Safe Zone Strategy)
        margin = Inches(0.5)

        # 根據不同的 Layout 決定圖片位置
        # 這裡使用「安全區域」策略，確保圖片在右側或特定區域
        if layout_type == "two_column":
            # 放在右側欄位稍微偏右的位置
            left = self.slide_width * 0.55
            top = Inches(2.0)
            width = self.slide_width * 0.4
            height = self.slide_height * 0.5
        elif layout_type == "image_text":
            # 圖片在左側
            left = margin
            top = Inches(1.5)
            width = self.slide_width * 0.45
            height = self.slide_height * 0.65
        else:
            # 預設 (Content Layout): 放在右下角，避免遮擋主要列表
            width = self.slide_width * 0.35
            height = self.slide_height * 0.4
            left = self.slide_width - width - margin
            top = self.slide_height - height - margin

        try:
            slide.shapes.add_picture(
                str(img_path),
                left,
                top,
                width=width,
                height=height,
            )
        except Exception as e:
            logger.error(f"Failed to add image: {e}")

    def build_to_file(
        self, content: dict[str, Any], output_path: Path, master_index: int = 0
    ) -> Path:
        pptx_bytes = self.build(content, master_index)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pptx_bytes)
        return output_path
