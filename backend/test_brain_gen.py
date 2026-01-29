#!/usr/bin/env python3
"""測試腳本：使用 my_basic 模板生成 PPTX"""

import asyncio
import os

from app.services.ppt_service_v2 import PPTServiceV2


async def main():
    with open("tests/data/brain.txt", "r") as f:
        user_input = f.read()
    print(f"輸入: {len(user_input)} 字元")

    service = PPTServiceV2()
    pptx_bytes = await service.generate(
        user_input=user_input,
        template="my_basic",
        slide_count=8,
        add_images=False,
    )

    os.makedirs("data/outputs", exist_ok=True)
    with open("data/outputs/test_brain_basic.pptx", "wb") as f:
        f.write(pptx_bytes)
    print(f"成功: data/outputs/test_brain_basic.pptx ({len(pptx_bytes)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
