#!/usr/bin/env python3
"""
基於 education_minimal.pptx 生成 4 個顏色主題變體

策略：
1. 讀取 education_minimal.pptx 的 theme1.xml
2. 替換顏色方案（dk1, dk2, lt1, lt2, accent1-6）
3. 寫入新的 PPTX 檔案

顏色主題設計：
- industrial_tech: 深藍科技風
- professional_corporate: 商務灰藍
- strategic_consulting: 深綠專業
- visionary_story: 紫橙創意
"""

import re
import shutil
import zipfile
from pathlib import Path

# 顏色主題定義 (RGB hex)
THEMES = {
    "industrial_tech": {
        "name": "Industrial Tech",
        "dk1": "1A1A2E",  # 深海軍藍
        "lt1": "FFFFFF",  # 白
        "dk2": "16213E",  # 深藍
        "lt2": "E8E8E8",  # 淺灰
        "accent1": "0F4C75",  # 鋼藍
        "accent2": "3282B8",  # 科技藍
        "accent3": "00A8CC",  # 青藍
        "accent4": "4ECCA3",  # 科技綠
        "accent5": "232931",  # 炭黑
        "accent6": "393E46",  # 深灰
    },
    "professional_corporate": {
        "name": "Professional Corporate",
        "dk1": "2C3E50",  # 深灰藍
        "lt1": "FFFFFF",  # 白
        "dk2": "34495E",  # 灰藍
        "lt2": "F5F5F5",  # 米白
        "accent1": "3498DB",  # 商務藍
        "accent2": "2980B9",  # 深藍
        "accent3": "1ABC9C",  # 青綠
        "accent4": "16A085",  # 深青綠
        "accent5": "95A5A6",  # 灰
        "accent6": "7F8C8D",  # 深灰
    },
    "strategic_consulting": {
        "name": "Strategic Consulting",
        "dk1": "1B4332",  # 深綠
        "lt1": "FFFFFF",  # 白
        "dk2": "2D6A4F",  # 森林綠
        "lt2": "F0F4F0",  # 淺綠白
        "accent1": "40916C",  # 專業綠
        "accent2": "52B788",  # 亮綠
        "accent3": "74C69D",  # 淺綠
        "accent4": "D4A574",  # 金棕
        "accent5": "264653",  # 深青
        "accent6": "2A9D8F",  # 青綠
    },
    "visionary_story": {
        "name": "Visionary Story",
        "dk1": "2D2D3A",  # 深紫灰
        "lt1": "FFFFFF",  # 白
        "dk2": "3D3D54",  # 紫灰
        "lt2": "F8F8FC",  # 淺紫白
        "accent1": "6C5CE7",  # 紫
        "accent2": "A29BFE",  # 淺紫
        "accent3": "FD79A8",  # 粉紅
        "accent4": "FDCB6E",  # 金黃
        "accent5": "E17055",  # 橙
        "accent6": "00B894",  # 青綠
    },
}


def hex_to_rgb_xml(hex_color: str) -> str:
    """將 hex 轉為 OOXML 格式 (val="RRGGBB")"""
    return hex_color.upper()


def replace_theme_colors(theme_xml: str, colors: dict) -> str:
    """
    替換 theme1.xml 中的顏色定義

    OOXML 顏色結構：
    <a:clrScheme name="...">
      <a:dk1><a:srgbClr val="RRGGBB"/></a:dk1>
      ...
    </a:clrScheme>
    """
    # 定義需要替換的顏色標籤
    color_tags = [
        "dk1",
        "lt1",
        "dk2",
        "lt2",
        "accent1",
        "accent2",
        "accent3",
        "accent4",
        "accent5",
        "accent6",
    ]

    for tag in color_tags:
        if tag not in colors:
            continue

        new_val = hex_to_rgb_xml(colors[tag])

        # 模式 1: <a:dk1><a:srgbClr val="..."/></a:dk1>
        pattern1 = rf'(<a:{tag}>.*?<a:srgbClr[^>]*val=")[^"]*("[^>]*/></a:{tag}>)'
        theme_xml = re.sub(pattern1, rf"\g<1>{new_val}\2", theme_xml, flags=re.DOTALL)

        # 模式 2: <a:dk1><a:sysClr ...><a:srgbClr val="..."/></a:sysClr></a:dk1>
        # 有些主題使用 sysClr 包裝
        pattern2 = rf"(<a:{tag}>.*?<a:sysClr[^>]*>.*?</a:sysClr>)(</a:{tag}>)"

        def replace_sysClr(match):
            # 替換為直接的 srgbClr
            return f'<a:{tag}><a:srgbClr val="{new_val}"/></a:{tag}>'

        theme_xml = re.sub(pattern2, replace_sysClr, theme_xml, flags=re.DOTALL)

    # 更新主題名稱
    if "name" in colors:
        theme_xml = re.sub(
            r'(<a:clrScheme[^>]*name=")[^"]*(")', rf"\g<1>{colors['name']}\2", theme_xml
        )

    return theme_xml


def generate_variant(base_pptx: Path, output_pptx: Path, theme_colors: dict):
    """
    基於 base_pptx 生成顏色變體

    步驟：
    1. 複製 base_pptx 到 output_pptx
    2. 打開 output_pptx 作為 ZIP
    3. 讀取並修改 ppt/theme/theme1.xml
    4. 寫回修改後的內容
    """
    print(f"Generating: {output_pptx.name}")

    # 複製基礎模板
    shutil.copy2(base_pptx, output_pptx)

    # 作為 ZIP 操作
    theme_path = "ppt/theme/theme1.xml"

    # 讀取所有內容
    with zipfile.ZipFile(output_pptx, "r") as zf:
        theme_xml = zf.read(theme_path).decode("utf-8")
        all_files = {}
        for name in zf.namelist():
            all_files[name] = zf.read(name)

    # 修改顏色
    new_theme_xml = replace_theme_colors(theme_xml, theme_colors)
    all_files[theme_path] = new_theme_xml.encode("utf-8")

    # 重新寫入 ZIP
    with zipfile.ZipFile(output_pptx, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in all_files.items():
            zf.writestr(name, content)

    print(f"  -> Created: {output_pptx} ({output_pptx.stat().st_size:,} bytes)")


def main():
    base_dir = Path(__file__).parent
    base_pptx = base_dir / "education_minimal.pptx"

    if not base_pptx.exists():
        print(f"ERROR: Base template not found: {base_pptx}")
        return 1

    print(f"Base template: {base_pptx}")
    print(f"Base size: {base_pptx.stat().st_size:,} bytes")
    print()

    # 生成 4 個變體
    for theme_name, colors in THEMES.items():
        output_pptx = base_dir / f"{theme_name}.pptx"
        generate_variant(base_pptx, output_pptx, colors)

    print()
    print("All variants generated successfully!")

    # 驗證
    print("\nVerification:")
    for theme_name in THEMES:
        pptx_path = base_dir / f"{theme_name}.pptx"
        if pptx_path.exists():
            print(f"  ✓ {theme_name}.pptx ({pptx_path.stat().st_size:,} bytes)")
        else:
            print(f"  ✗ {theme_name}.pptx MISSING")

    return 0


if __name__ == "__main__":
    exit(main())
