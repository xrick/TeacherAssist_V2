#!/usr/bin/env python3
"""Create sample PPTX templates for testing"""

import json
from pathlib import Path

from pptagent_pptx import Presentation


def create_template_with_metadata(filename: str, name: str, description: str, tags: list):
    """Create a PPTX template with JSON metadata"""
    # Create presentation
    prs = Presentation()
    output_path = Path(filename)
    prs.save(output_path)
    print(f"✅ Created: {output_path.name}")

    # Create metadata
    metadata = {"description": description, "tags": tags, "preview_image": None}

    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"✅ Created: {json_path.name}")


if __name__ == "__main__":
    templates_dir = Path("data/templates")
    templates_dir.mkdir(parents=True, exist_ok=True)

    # Create sample templates
    create_template_with_metadata(
        templates_dir / "modern_clean.pptx",
        "現代簡約",
        "適合商業簡報的現代簡約風格模板，簡潔大方的設計",
        ["商業", "簡約", "現代"],
    )

    create_template_with_metadata(
        templates_dir / "education_basic.pptx",
        "教育基礎",
        "適合教學使用的基礎教育模板，清晰易讀",
        ["教育", "教學", "基礎"],
    )

    create_template_with_metadata(
        templates_dir / "creative_colorful.pptx",
        "創意繽紛",
        "充滿活力的創意設計，適合創意提案和展示",
        ["創意", "活潑", "多彩"],
    )

    print("\n✅ All templates created successfully!")
