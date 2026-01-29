#!/usr/bin/env python3
"""
v0.3 整合測試：驗證移除 Stage 3 後的管線
- 輸入：brain.txt
- 輸出：8 頁，其中 4 頁有圖片
- Prompt: academic_research_and_deep_analysis_mode.md
"""

import asyncio
import sys
from pathlib import Path

# 添加 backend 到 path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.llm_service import get_llm_service
from app.services.ppt_service_v2 import PPTServiceV2


async def main():
    # 讀取測試資料
    test_data_path = Path(__file__).parent / "tests" / "data" / "brain.txt"
    if not test_data_path.exists():
        print(f"錯誤：找不到測試資料 {test_data_path}")
        return

    user_input = test_data_path.read_text(encoding="utf-8")
    print(f"讀取測試資料: {len(user_input)} 字元")
    print(f"前 200 字元:\n{user_input[:200]}...\n")

    # 建立服務
    llm = get_llm_service()
    service = PPTServiceV2(llm)

    print("=" * 60)
    print("開始 v0.3 整合測試")
    print("- 目標：8 頁")
    print("- 圖片：啟用，最多 4 張")
    print("- Template: education_basic")
    print("- Prompt: academic_research_and_deep_analysis_mode.md")
    print("=" * 60)

    # 使用串流模式以追蹤進度
    output_path = Path(__file__).parent / "data" / "outputs" / "test_v03_brain.pptx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async for event in service.generate_stream(
            user_input=user_input,
            template="education_basic",
            slide_count=8,
            add_images=True,
            images_per_slide=1,
            max_images=4,  # v0.3: 限制最多 4 張圖片
        ):
            stage = event.get("stage", "unknown")
            progress = event.get("progress", 0)
            message = event.get("message", "")

            print(f"[{progress:3d}%] {stage}: {message}")

            if "result" in event:
                pptx_bytes = event["result"]
                output_path.write_bytes(pptx_bytes)

                stats = event.get("stats", {})
                print("\n" + "=" * 60)
                print("測試完成！")
                print(f"- 輸出檔案: {output_path}")
                print(f"- 檔案大小: {stats.get('file_size', 0) / 1024:.1f} KB")
                print(f"- 投影片數: {stats.get('slide_count', 0)}")
                print(f"- 圖片數量: {stats.get('image_count', 0)}")
                print(f"- 執行時間: {stats.get('duration_seconds', 0):.2f}s")
                print("=" * 60)

            if stage == "error":
                print(f"\n錯誤: {event.get('error')}")

    except Exception as e:
        print(f"\n測試失敗: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
