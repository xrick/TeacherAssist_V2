#!/usr/bin/env python3
"""Debug: 檢查每個階段的內容"""

import asyncio
import json
from pathlib import Path

from app.pptagent_core.config import TemplateConfigLoader
from app.pptagent_core.roles.content_generator import ContentGenerator
from app.pptagent_core.roles.content_organizer_v2 import ContentOrganizerV2
from app.pptagent_core.roles.input_classifier import classify_user_input
from app.pptagent_core.roles.template_analyzer import TemplateAnalyzer
from app.services.llm_service import get_llm_service
from app.services.ppt_service_v2 import PPTServiceV2


async def main():
    with open("tests/data/ml.md", "r") as f:
        user_input = f.read()
    print(f"輸入: {len(user_input)} 字元\n")

    # 取得 config
    config_loader = TemplateConfigLoader()
    template_config = config_loader.get_template_config("my_basic")
    template_path = Path("data") / template_config.file_path

    # Stage 1: 分析 Template
    print("=== Stage 1: Template 分析 ===")
    analyzer = TemplateAnalyzer(template_path, config=template_config)
    template_structure = analyzer.analyze(slide_count=10, include_title=True, include_closing=True)
    print(
        f"Layout sequence: {[s.get('layout_index') for s in template_structure.get('slides', [])]}"
    )
    print()

    # Stage 2: 生成內容
    print("=== Stage 2: LLM 內容生成 ===")
    llm = get_llm_service()
    generator = ContentGenerator(llm)
    classification = classify_user_input(user_input)
    draft_content = await generator.generate(
        user_input=user_input,
        slide_count=10,
        input_mode=classification.mode,
        prompt_path=template_config.prompt_path,
    )
    print(f"Draft slides: {len(draft_content.get('slides', []))}")
    for i, slide in enumerate(draft_content.get("slides", [])[:3]):
        print(f"  Slide {i + 1}: {slide.get('title', 'No title')[:50]}")
        print(f"    bullets: {slide.get('bullet_points', [])[:2]}")
    print()

    # Stage 3: 組織內容
    print("=== Stage 3: 組織內容 ===")
    organizer = ContentOrganizerV2(llm)
    organized_content = await organizer.organize(
        draft_content=draft_content,
        template_structure=template_structure,
    )
    print(f"Organized slides: {len(organized_content.get('slides', []))}")
    for i, slide in enumerate(organized_content.get("slides", [])):
        placeholders = slide.get("placeholders", [])
        print(f"  Slide {i + 1}: {len(placeholders)} placeholders")
        for ph in placeholders[:2]:
            print(
                f"    - type={ph.get('type')}, idx={ph.get('idx')}, text={str(ph.get('text', ''))[:50]}"
            )


if __name__ == "__main__":
    asyncio.run(main())
