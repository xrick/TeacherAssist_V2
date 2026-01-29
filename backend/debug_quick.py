#!/usr/bin/env python3
"""快速 debug：檢查 content 結構"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.pptagent_core.roles.content_generator import ContentGenerator
from app.pptagent_core.roles.input_classifier import InputMode, classify_user_input
from app.services.llm_service import get_llm_service


async def main():
    user_input = "深度學習是機器學習的一個分支，使用多層神經網路來學習數據的表示。"

    print("=" * 60)
    print("Debug: 檢查 ContentGenerator 輸出")
    print("=" * 60)

    llm = get_llm_service()
    generator = ContentGenerator(llm)

    content = await generator.generate(
        user_input=user_input,
        slide_count=3,
        input_mode=InputMode.SEARCH,
        prompt_path="prompts/professional_corporate_prompt.md",
    )

    print("\n--- 完整輸出 ---")
    print(json.dumps(content, indent=2, ensure_ascii=False)[:2000])

    print("\n--- placeholders 檢查 ---")
    for i, slide in enumerate(content.get("slides", [])):
        print(f"\nSlide {i + 1}:")
        print(f"  Keys: {slide.keys()}")
        phs = slide.get("placeholders", [])
        print(f"  placeholders count: {len(phs)}")
        for ph in phs:
            print(
                f"    - type={ph.get('type')}, idx={ph.get('idx')}, content={str(ph.get('content', ''))[:50]}"
            )


if __name__ == "__main__":
    asyncio.run(main())
