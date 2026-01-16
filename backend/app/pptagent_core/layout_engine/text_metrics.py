import logging
import os
import platform
from functools import lru_cache
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class TextMetrics:
    """
    負責 PPTX 排版計算的文字測量工具 (基於 Pillow)。
    處理 EMU (PPTX 單位) 與 Pixels (螢幕單位) 之間的轉換。
    支援 Windows, macOS, Linux 本機環境的字體自動偵測。
    """

    # Constants
    DPI = 96
    EMU_PER_INCH = 914400
    PIXELS_PER_INCH = 96
    EMU_PER_PIXEL = EMU_PER_INCH / PIXELS_PER_INCH

    @staticmethod
    def emu_to_pixels(emu: int) -> float:
        return emu / TextMetrics.EMU_PER_PIXEL

    @staticmethod
    def pixels_to_emu(pixels: float) -> int:
        return int(pixels * TextMetrics.EMU_PER_PIXEL)

    @staticmethod
    def pt_to_pixels(pt: float) -> float:
        # 1 pt = 1/72 inch, 1 px = 1/96 inch
        return pt * (96 / 72)

    @staticmethod
    def _get_system_font_path(font_name: str) -> Optional[str]:
        """
        根據作業系統尋找字體檔案路徑。
        """
        system = platform.system().lower()
        font_filename = f"{font_name}.ttf"

        # 常見的中英文字體對應
        lower_name = font_name.lower()
        if "heiti" in lower_name or "jhenghei" in lower_name or "microsoft yahei" in lower_name:
            if system == "windows":
                font_filename = "msjh.ttc"  # Microsoft JhengHei
            elif system == "darwin":
                font_filename = "STHeiti Medium.ttc"
            else:
                font_filename = "NotoSansCJK-Regular.ttc"
        elif "arial" in lower_name:
            font_filename = "arial.ttf"

        # 搜尋路徑
        search_paths = []
        if system == "windows":
            search_paths = [os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")]
        elif system == "darwin":
            search_paths = [
                "/Library/Fonts",
                "/System/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"),
            ]
        else:  # Linux/Unix
            search_paths = [
                "/usr/share/fonts",
                "/usr/share/fonts/truetype",
                "/usr/share/fonts/truetype/dejavu",
                "/usr/share/fonts/truetype/noto",
                os.path.expanduser("~/.local/share/fonts"),
            ]

        # 1. 直接搜尋檔案
        for path in search_paths:
            full_path = os.path.join(path, font_filename)
            if os.path.exists(full_path):
                return full_path

            # 2. 遞迴搜尋 (針對 Linux 結構)
            for root, _, files in os.walk(path):
                if font_filename in files:
                    return os.path.join(root, font_filename)

        return None

    @classmethod
    @lru_cache(maxsize=32)
    def _get_font(cls, font_name: str, font_size_pt: float):
        """
        載入字體，若找不到則使用 fallback 機制。
        """
        size_px = int(cls.pt_to_pixels(font_size_pt))

        # 1. 嘗試尋找指定字體
        font_path = cls._get_system_font_path(font_name)

        # 2. 若找不到，嘗試使用 Arial 作為通用替代
        if not font_path:
            font_path = cls._get_system_font_path("Arial")

        try:
            if font_path:
                return ImageFont.truetype(font_path, size_px)
            else:
                logger.warning(
                    f"Font {font_name} not found and fallback failed. Using default bitmap font."
                )
                return ImageFont.load_default()
        except OSError:
            logger.warning("Failed to load TrueType font. Using default.")
            return ImageFont.load_default()

    @classmethod
    def measure_text(
        cls, text: str, font_name: str, font_size_pt: float, max_width_emu: int = None
    ) -> Tuple[int, int]:
        """
        測量文字區塊的尺寸。

        Args:
            text: 要測量的文字
            font_name: 字體名稱
            font_size_pt: 字體大小 (pt)
            max_width_emu: 最大允許寬度 (用於計算換行)

        Returns:
            (width_emu, height_emu)
        """
        if not text:
            return 0, 0

        font = cls._get_font(font_name, font_size_pt)
        dummy_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_img)

        if max_width_emu:
            max_width_px = cls.emu_to_pixels(max_width_emu)

            # 模擬文字換行 (Word Wrapping)
            lines = []
            paragraphs = text.split("\n")

            for paragraph in paragraphs:
                if not paragraph:
                    lines.append("")
                    continue

                words = paragraph.split()
                if not words:
                    lines.append(paragraph)
                    continue

                current_line = []
                for word in words:
                    # 測試加入下一個字後的寬度
                    test_line = " ".join(current_line + [word])
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    w = bbox[2] - bbox[0]

                    if w > max_width_px and current_line:
                        # 若超過寬度，將目前的行推入 lines，並開啟新的一行
                        lines.append(" ".join(current_line))
                        current_line = [word]
                    else:
                        current_line.append(word)
                if current_line:
                    lines.append(" ".join(current_line))

            # 計算總高度
            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            line_spacing = line_height * 0.2  # 1.2倍行高，接近 PPT 預設

            total_h_px = len(lines) * (line_height + line_spacing)

            # 計算最大寬度
            max_w_px = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                if w > max_w_px:
                    max_w_px = w

            return cls.pixels_to_emu(max_w_px), cls.pixels_to_emu(total_h_px)

        else:
            # 單行測量
            bbox = draw.textbbox((0, 0), text, font=font)
            width_px = bbox[2] - bbox[0]
            height_px = bbox[3] - bbox[1]
            return cls.pixels_to_emu(width_px), cls.pixels_to_emu(height_px)
