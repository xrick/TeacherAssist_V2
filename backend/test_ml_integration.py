#!/usr/bin/env python3
"""整合測試：使用 ml.md 生成 10 頁 PPTX，含 4 頁圖片"""

import asyncio
import os

from app.services.ppt_service_v2 import PPTServiceV2


async def main():
    with open("tests/data/ml.md", "r") as f:
        user_input = f.read()
    print(f"輸入: {len(user_input)} 字元")

    service = PPTServiceV2()
    pptx_bytes = await service.generate(
        user_input=user_input,
        template="my_basic",
        slide_count=10,
        add_images=True,
        images_per_slide=1,
    )

    os.makedirs("data/outputs", exist_ok=True)
    output_path = "data/outputs/test_ml_integration.pptx"
    with open(output_path, "wb") as f:
        f.write(pptx_bytes)
    print(f"成功: {output_path} ({len(pptx_bytes)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
