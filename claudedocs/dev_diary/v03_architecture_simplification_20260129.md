# v0.3 架構簡化：移除 Stage 3 (ContentOrganizerV2)

**日期**: 2026-01-29  
**狀態**: 已完成並通過整合測試

## 背景

原有 5 階段管線：
```
Stage 0: InputClassifier → Stage 1: TemplateAnalyzer → Stage 2: ContentGenerator 
→ Stage 3: ContentOrganizerV2 → Stage 4: ImageEnricher → Stage 5: SlideBuilder
```

Stage 3 (ContentOrganizerV2) 的主要工作是將 ContentGenerator 輸出的 `title + bullet_points` 格式轉換為 `placeholders` 格式。這個轉換邏輯簡單，可以直接讓 ContentGenerator 輸出最終格式。

## 決策

採用 **方案 B**：修改 ContentGenerator 直接輸出 `placeholders` 格式，移除 Stage 3。

### 優點
- 減少 LLM 呼叫次數（從 2 次減為 1 次）
- 簡化管線，減少中間轉換
- 降低延遲和成本

## 實作變更

### 1. ContentGenerator (`content_generator.py`)

**System Prompt 更新**：
```json
{
  "slides": [
    {
      "placeholders": [
        {"idx": 0, "type": "TITLE", "content": "投影片標題"},
        {"idx": 1, "type": "BODY", "content": "• 要點一\n• 要點二\n• 要點三"}
      ]
    }
  ]
}
```

**向後相容**：`_validate_content()` 可自動從舊格式轉換：
```python
if "placeholders" not in slide:
    placeholders = []
    if "title" in slide:
        placeholders.append({"idx": 0, "type": "TITLE", "content": slide["title"]})
    if "bullet_points" in slide:
        body_text = "\n".join(f"• {b}" for b in slide["bullet_points"])
        placeholders.append({"idx": 1, "type": "BODY", "content": body_text})
    slide["placeholders"] = placeholders
```

### 2. PPTServiceV2 (`ppt_service_v2.py`)

- 移除 `ContentOrganizerV2` import 和呼叫
- 新增 `max_images` 參數傳遞給 `ImageEnricher`
- 管線簡化為 4 階段

### 3. SlideBuilder (`slide_builder.py`)

**Layout 選擇修復**：
```python
# 從 config 取得 structure_rules
structure_rules = self.config.structure_rules if self.config else None
body_pool = structure_rules.body_pool if structure_rules else [2]

# 依投影片位置選擇 layout
if i == 0 or slide_layout == "title":
    layout_idx = structure_rules.opening  # 標題頁
elif i == total_slides - 1 or slide_layout == "closing":
    layout_idx = structure_rules.closing  # 結尾頁
else:
    layout_idx = body_pool[body_pool_idx % len(body_pool)]  # 內容頁輪替
```

**Placeholder Type 匹配修復**：
```python
import re
# Template 的 placeholder type 是 "TITLE (1)", "BODY (2)" 格式
# LLM 輸出的是 "TITLE", "BODY" 格式
# 需要移除 " (數字)" 後綴才能匹配
ph_type_raw = str(ph_format.type)
ph_type_name = re.sub(r"\s*\(\d+\)$", "", ph_type_raw)
```

### 4. ImageEnricher (`image_enricher.py`)

新增 `max_images` 參數：
```python
async def enrich(
    self,
    organized_content: dict[str, Any],
    draft_content: dict[str, Any],
    presentation_title: str,
    images_per_slide: int = 1,
    max_images: int | None = None,  # 新增：限制總圖片數量
) -> dict[str, Any]:
```

### 5. Prompt 檔案更新

以下 5 個 prompt 檔案已更新為輸出 `placeholders` 格式：
- `professional_corporate_prompt.md`
- `academic_research_and_deep_analysis_mode.md`
- `industrial_tech_prompt.md`
- `strategic_consulting_prompt.md`
- `visionary_story_prompt.md`

### 6. 設定檔更新 (`sys_template_config.json`)

- 版本號更新為 `"version": "0.3"`
- 新增 `my_basic` 模板
- 所有模板統一使用 `standard_template_01.pptx`

## 整合測試結果

### 測試 1: DL.txt + my_basic template
- 投影片數: 10 張
- 圖片數量: 4 張 (max_images=4)
- 執行時間: ~150s
- 結果: 通過

### 測試 2: brain.txt + education_basic template
- 投影片數: 8 張
- 圖片數量: 4 張 (max_images=4)
- 執行時間: 107.47s
- 檔案大小: 210.6 KB
- 結果: 通過

## 修復的 Bug

1. **所有投影片使用 SECTION_HEADER layout**
   - 原因: `SlideBuilder.build()` 預設 `layout_index=1`
   - 修復: 使用 `body_pool` 配置輪替內容頁 layout

2. **每張投影片都有圖片**
   - 原因: `ImageEnricher` 沒有總數限制
   - 修復: 新增 `max_images` 參數

3. **內容無法填入（只有標題）**
   - 原因: Template placeholder type 是 `TITLE (1)`，LLM 輸出是 `TITLE`
   - 修復: 使用 regex 移除 ` (數字)` 後綴

## v0.3 架構總覽

```
Stage 0: InputClassifier     — 判斷短題目 / 長文章
Stage 1: TemplateAnalyzer    — 分析 PPTX Template 結構
Stage 2: ContentGenerator    — LLM 生成內容 → placeholders 格式
Stage 3: ImageEnricher       — 注入 Pexels 圖片（可選，max_images 限制）
Stage 4: SlideBuilder        — 建構最終 PPTX bytes
```

## 檔案變更清單

| 檔案 | 變更類型 | 說明 |
|------|----------|------|
| `backend/app/pptagent_core/roles/content_generator.py` | 修改 | 新 prompt 格式、向後相容 |
| `backend/app/services/ppt_service_v2.py` | 修改 | 移除 Stage 3、新增 max_images |
| `backend/app/pptagent_core/roles/slide_builder.py` | 修改 | layout 選擇、type 匹配修復 |
| `backend/app/pptagent_core/roles/image_enricher.py` | 修改 | 新增 max_images 參數 |
| `backend/data/prompts/*.md` | 修改 | 5 個 prompt 更新為 placeholders 格式 |
| `backend/data/sys_template_config.json` | 修改 | 版本 0.3、新增 my_basic |
| `backend/test_v03_integration.py` | 修改 | 整合測試腳本 |
