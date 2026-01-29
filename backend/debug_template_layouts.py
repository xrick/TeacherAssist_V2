#!/usr/bin/env python3
"""Debug: 檢查 Template 的所有 Layout"""

from pathlib import Path

from pptx import Presentation

template_path = Path("data/templates/standard_template_01.pptx")
prs = Presentation(template_path)
master = prs.slide_master

print(f"Template: {template_path}")
print(f"Layout 數量: {len(master.slide_layouts)}")
print("=" * 60)

for i, layout in enumerate(master.slide_layouts):
    print(f"\nLayout {i}: {layout.name}")
    for shape in layout.placeholders:
        ph = shape.placeholder_format
        ph_type = str(ph.type).replace("PLACEHOLDER_TYPE.", "")
        print(f"  idx={ph.idx}, type={ph_type}")
