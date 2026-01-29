#!/usr/bin/env python3
"""Debug: 檢查 SlideBuilder 的 placeholder 匹配"""

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

template_path = Path("data/templates/standard_template_01.pptx")
prs = Presentation(template_path)
master = prs.slide_master

print("=" * 60)
print("Debug: 檢查 Template placeholder types")
print("=" * 60)

# 檢查 Layout 2 (TITLE_AND_BODY) 的 placeholder
layout = master.slide_layouts[2]
print(f"\nLayout 2: {layout.name}")

for shape in layout.placeholders:
    ph = shape.placeholder_format
    ph_type_raw = ph.type
    ph_type_str = str(ph_type_raw)
    print(f"  idx={ph.idx}")
    print(f"    type (raw): {ph_type_raw}")
    print(f"    type (str): {ph_type_str}")

    # 模擬 SlideBuilder 的處理
    ph_type_name = ph_type_str.replace("PLACEHOLDER_TYPE.", "").replace(" (13)", "")
    print(f"    type (processed): {ph_type_name}")
