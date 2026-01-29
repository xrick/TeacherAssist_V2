#!/usr/bin/env python3
"""Debug: 檢查 LLM 原始回傳"""

import asyncio

from app.pptagent_core.config import TemplateConfigLoader
from app.pptagent_core.roles.content_generator import ContentGenerator, load_prompt_template
from app.pptagent_core.roles.input_classifier import classify_user_input
from app.services.llm_service import get_llm_service


async def main():
    with open("tests/data/ml.md", "r") as f:
        user_input = f.read()

    config_loader = TemplateConfigLoader()
    template_config = config_loader.get_template_config("my_basic")

    llm = get_llm_service()
    generator = ContentGenerator(llm)

    # 載入 prompt
    prompt_template = load_prompt_template(template_config.prompt_path)

    # 建立 prompt
    prompt = generator._build_custom_prompt(prompt_template, user_input, 10, None, "zh-TW")

    print("=== Prompt 傳給 LLM (前 800 字) ===")
    print(prompt[:800])
    print("\n...\n")

    # 呼叫 LLM
    from app.pptagent_core.roles.content_generator import CONTENT_GENERATOR_SYSTEM

    response = await llm.generate(
        prompt=prompt,
        system_prompt=CONTENT_GENERATOR_SYSTEM,
        temperature=0.3,
        max_tokens=8000,
    )

    print("=== LLM 原始回傳 (前 2000 字) ===")
    print(response.content[:2000])
    print("\n...\n")

    # 嘗試解析
    print("=== 解析結果 ===")
    try:
        parsed = generator._parse_json_response(response.content)
        slides = parsed.get("slides", [])
        print(f"解析成功！Slides 數量: {len(slides)}")
        for i, s in enumerate(slides[:3]):
            print(f"  Slide {i + 1}: title={s.get('title', 'N/A')[:40]}")
            print(f"    bullets: {s.get('bullet_points', [])[:2]}")
    except Exception as e:
        print(f"解析失敗: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
