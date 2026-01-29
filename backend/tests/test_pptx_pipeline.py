#!/usr/bin/env python3
"""
PPTX Pipeline 整合測試

測試完整的 PPTX 生成流程：
1. 讀取測試輸入 (ml.md)
2. 使用 education_minimal.pptx 模板
3. 執行完整管線
4. 驗證輸出檔案存在
"""

import asyncio
import sys
from pathlib import Path

# 加入 backend 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.ppt_service_v2 import PPTServiceV2


async def run_pipeline_test():
    """執行完整管線測試"""
    print("=" * 60)
    print("PPTX Pipeline Integration Test")
    print("=" * 60)

    # 設定已作為 module-level 變數匯入
    test_data_dir = Path(__file__).parent / "data"
    input_file = test_data_dir / "ml.md"
    output_dir = backend_dir / "data" / "outputs"
    template_dir = backend_dir / "data" / "templates"

    # 確保輸出目錄存在
    output_dir.mkdir(parents=True, exist_ok=True)

    # 讀取測試輸入
    print(f"\n1. Reading input: {input_file}")
    if not input_file.exists():
        print(f"   ERROR: Input file not found!")
        return 1

    user_input = input_file.read_text(encoding="utf-8")
    print(f"   Input length: {len(user_input)} chars")

    # 選擇模板
    template_name = "education_minimal"
    template_path = template_dir / f"{template_name}.pptx"
    print(f"\n2. Using template: {template_path}")
    if not template_path.exists():
        print(f"   ERROR: Template not found!")
        return 1
    print(f"   Template size: {template_path.stat().st_size:,} bytes")

    # 初始化服務
    print(f"\n3. Initializing services...")
    llm_service = LLMService()
    ppt_service = PPTServiceV2(llm_service=llm_service, templates_path=template_dir)

    # 執行生成
    print(f"\n4. Running pipeline...")
    output_file = output_dir / "test_ml_output.pptx"

    try:
        # 使用非串流方式
        result = await ppt_service.generate(
            user_input=user_input,
            template=template_name,
            add_images=False,  # 先不含圖片加速測試
        )

        # 儲存結果 (generate 返回 bytes)
        if result:
            output_file.write_bytes(result)
            print(f"\n5. Output saved: {output_file}")
            print(f"   Output size: {output_file.stat().st_size:,} bytes")

            # 驗證
            print(f"\n6. Verification:")
            if output_file.exists() and output_file.stat().st_size > 0:
                print(f"   ✓ Output file exists")
                print(f"   ✓ File size > 0")

                # 驗證是否為有效 ZIP (PPTX)
                import zipfile

                try:
                    with zipfile.ZipFile(output_file, "r") as zf:
                        file_count = len(zf.namelist())
                        print(f"   ✓ Valid PPTX (ZIP with {file_count} files)")

                        # 檢查是否有 slide
                        slides = [
                            f
                            for f in zf.namelist()
                            if f.startswith("ppt/slides/slide") and f.endswith(".xml")
                        ]
                        print(f"   ✓ Contains {len(slides)} slides")

                except zipfile.BadZipFile:
                    print(f"   ✗ Invalid PPTX format")
                    return 1

                print(f"\n{'=' * 60}")
                print("TEST PASSED!")
                print(f"{'=' * 60}")
                return 0
            else:
                print(f"   ✗ Output file missing or empty")
                return 1
        else:
            print(f"\n   ERROR: No result from pipeline")
            return 1

    except Exception as e:
        print(f"\n   ERROR: Pipeline failed with exception:")
        print(f"   {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return 1


async def main():
    """主函式"""
    return await run_pipeline_test()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
