#!/usr/bin/env python3
"""Debug: 檢查 ContentOrganizerV2 的 LLM 回傳"""

import asyncio
import json
from pathlib import Path

from app.pptagent_core.config import TemplateConfigLoader
from app.pptagent_core.roles.content_generator import ContentGenerator
from app.pptagent_core.roles.content_organizer_v2 import ContentOrganizerV2
from app.pptagent_core.roles.input_classifier import classify_user_input
from app.pptagent_core.roles.template_analyzer import TemplateAnalyzer
from app.services.llm_service import get_llm_service


async def main():
    with open("tests/data/ml.md", "r") as f:
        user_input = f.read()

    config_loader = TemplateConfigLoader()
    template_config = config_loader.get_template_config("my_basic")
    template_path = Path("data") / template_config.file_path

    # Stage 1
    analyzer = TemplateAnalyzer(template_path, config=template_config)
    template_structure = analyzer.analyze(slide_count=10, include_title=True, include_closing=True)

    # Stage 2
    llm = get_llm_service()
    generator = ContentGenerator(llm)
    classification = classify_user_input(user_input)
    draft_content = await generator.generate(
        user_input=user_input,
        slide_count=10,
        input_mode=classification.mode,
        prompt_path=template_config.prompt_path,
    )

    # Stage 3 - 手動呼叫看 LLM 回傳
    organizer = ContentOrganizerV2(llm)
    user_prompt = organizer._build_prompt(draft_content, template_structure)

    print("=== User Prompt (前 500 字) ===")
    print(user_prompt[:500])
    print("\n...")

    from app.pptagent_core.roles.content_organizer_v2 import CONTENT_ORGANIZER_SYSTEM

    response = await llm.generate(
        prompt=user_prompt,
        system_prompt=CONTENT_ORGANIZER_SYSTEM,
        temperature=0.3,
        max_tokens=6000,
    )

    print("\n=== LLM 回傳 (前 1500 字) ===")
    print(response.content[:1500])

    # 嘗試解析
    print("\n=== 解析結果 ===")
    try:
        organized = organizer._parse_json_response(response.content)
        slides = organized.get("slides", [])
        print(f"Slides 數量: {len(slides)}")
        if slides:
            print(f"第一張 slide keys: {slides[0].keys()}")
            print(f"第一張 slide: {json.dumps(slides[0], ensure_ascii=False, indent=2)[:500]}")
    except Exception as e:
        print(f"解析失敗: {e}")


if __name__ == "__main__":
    asyncio.run(main())
