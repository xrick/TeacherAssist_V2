#!/usr/bin/env python3
"""Debug: 追蹤內容流"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.pptagent_core.roles.content_generator import ContentGenerator
from app.pptagent_core.roles.input_classifier import classify_user_input
from app.services.llm_service import get_llm_service


async def main():
    # 讀取測試資料
    test_data_path = Path(__file__).parent / "tests" / "data" / "DL.txt"
    user_input = test_data_path.read_text(encoding="utf-8")[:500]  # 只取前 500 字元加速測試

    print("=" * 60)
    print("Debug: 追蹤 ContentGenerator 輸出")
    print("=" * 60)

    llm = get_llm_service()
    generator = ContentGenerator(llm)

    classification = classify_user_input(user_input)
    print(f"輸入模式: {classification.mode.value}")

    content = await generator.generate(
        user_input=user_input,
        slide_count=3,  # 只生成 3 張測試
        input_mode=classification.mode,
        prompt_path="prompts/professional_corporate_prompt.md",
    )

    print("\n--- LLM 輸出結構 ---")
    print(f"Keys: {content.keys()}")

    if "slides" in content:
        print(f"Slides 數量: {len(content['slides'])}")
        for i, slide in enumerate(content["slides"][:2]):  # 只顯示前 2 張
            print(f"\n--- Slide {i + 1} ---")
            print(json.dumps(slide, indent=2, ensure_ascii=False)[:500])


if __name__ == "__main__":
    asyncio.run(main())
