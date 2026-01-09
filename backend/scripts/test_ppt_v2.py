#!/usr/bin/env python3
"""
測試 PPTServiceV2 四階段流程
"""

import asyncio
import sys
from pathlib import Path

# 加入 backend 到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ppt_service_v2 import PPTServiceV2

# 模擬使用者在 UI 中輸入的內容
USER_INPUT = """
# 機器學習入門

## 什麼是機器學習
機器學習是人工智慧的一個分支，讓電腦從資料中自動學習規律，不需要明確編寫規則。

## 三大類型
- 監督式學習：有標籤資料
- 非監督式學習：無標籤資料
- 強化學習：透過獎懲學習

## 應用場景
- Netflix 推薦系統
- Google 翻譯
- Tesla 自動駕駛

## 常用工具
Python、TensorFlow、PyTorch
"""


async def test_generate():
    """測試簡報生成"""
    print("=" * 60)
    print("PPTServiceV2 四階段流程測試")
    print("=" * 60)

    # 建立服務
    service = PPTServiceV2()

    # 測試參數
    template = "creative_colorful.pptx"
    slide_count = 8
    output_path = Path("output/test_v2_四階段.pptx")

    print(f"\n📝 使用者輸入: {len(USER_INPUT)} 字元")
    print(f"📄 Template: {template}")
    print(f"📊 目標投影片數: {slide_count}")
    print(f"💾 輸出: {output_path}")
    print()

    # 使用串流生成（顯示進度）
    print("🚀 開始生成...\n")

    async for update in service.generate_stream(
        user_input=USER_INPUT,
        template=template,
        slide_count=slide_count,
        audience="程式設計初學者",
        language="zh-TW",
    ):
        stage = update["stage"]
        progress = update["progress"]
        message = update["message"]

        print(f"  [{progress:3d}%] {stage}: {message}")

        if "result" in update:
            # 儲存結果
            pptx_bytes = update["result"]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(pptx_bytes)

            stats = update.get("stats", {})
            print(f"\n✅ 生成完成!")
            print(f"   投影片數: {stats.get('slide_count')}")
            print(f"   檔案大小: {stats.get('file_size', 0):,} bytes")
            print(f"   耗時: {stats.get('duration_seconds', 0):.2f}s")
            print(f"   儲存: {output_path}")

            # 顯示草稿摘要
            draft = update.get("draft_content", {})
            if draft:
                print(f"\n📋 草稿摘要:")
                print(f"   標題: {draft.get('title', 'N/A')}")
                print(f"   受眾: {draft.get('target_audience', 'N/A')}")
                for i, slide in enumerate(draft.get("slides", [])[:3]):
                    print(f"   Slide {i + 1}: {slide.get('title', '')[:30]}...")
                if len(draft.get("slides", [])) > 3:
                    print(f"   ... 共 {len(draft['slides'])} 張")

        if "error" in update:
            print(f"\n❌ 錯誤: {update['error']}")
            return False

    return True


async def main():
    """主測試流程"""
    try:
        success = await test_generate()

        if success:
            print("\n" + "=" * 60)
            print("✅ 測試通過!")
            print("=" * 60)

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
