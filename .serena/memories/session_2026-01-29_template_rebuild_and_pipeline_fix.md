# 工作記錄：Template 重建 + PPTX 管線修復

**日期**: 2026-01-29
**分支**: main
**狀態**: 全部完成，已測試通過

---

## 任務概述

從 `education_basic.pptx` 重建 base template，修復 placeholder 結構問題，生成 5 個 color theme 變體，並修改 `slide_builder.py` 程式碼以支援新結構。

---

## 一、Template 結構分析與修復

### 原始問題（CLAUDE.md 2026-01-28 記錄）

| 問題 | 嚴重度 | 實際驗證結果 |
|------|--------|-------------|
| idx 全為 None/0 | 致命 | ❌ 不存在 — 實測 idx 已唯一 |
| TITLE 在底部 | 高 | ❌ 不存在 — TITLE 已在頂部 (y≈0.52") |
| 無 PICTURE placeholder | 高 | ⚠️ 部分正確 — Layout 8, 11 有 PICTURE |

### 修復後 Template 結構

**檔案**: `education_minimal.pptx`
**尺寸**: 13.33" × 7.5" (16:9)
**Layout 數**: 13 個（保留全部 + 新增 1 個）

| Layout # | 名稱 | Placeholders | 用途 |
|----------|------|--------------|------|
| 0 | Title Slide | (0, TITLE), (1, SUBTITLE) | 首頁 |
| 1 | Title and Content | (0, TITLE), (10, OBJECT) | 標題+內文 |
| 2 | Section Header | (0, TITLE), (1, SUBTITLE) | 章節分隔 |
| 6 | Blank | 無 | 空白頁 |
| 8 | Picture with Caption | (0, TITLE), (1, PICTURE), (2, BODY) | 圖文並列 |
| 12 | Full Image | (1, PICTURE) | 全版圖片 |

---

## 二、Color Theme 變體生成

**技術**: 複製 base PPTX，替換 `ppt/theme/theme1.xml`

| 檔案 | 風格 | 主要配色 |
|------|------|---------|
| `education_minimal.pptx` | Base | 原始教育風格 |
| `industrial_tech.pptx` | 工業科技 | 深藍 #1A1A2E, 科技藍 #0F4C75 |
| `professional_corporate.pptx` | 專業商務 | 深藍黑 #1B2838, 金色 #D4AF37 |
| `strategic_consulting.pptx` | 策略諮詢 | 深藍黑 #0D1B2A, 海軍藍 #1B4965 |
| `visionary_story.pptx` | 願景故事 | 深灰 #2D3436, 珊瑚紅 #E17055 |

---

## 三、程式碼修改

### 3.1 `_fill_slide_content()` 改進

**檔案**: `backend/app/pptagent_core/roles/slide_builder.py`

**修改內容**:
- 建立 `type_map` 和 `idx_map` 雙重映射
- 優先使用 placeholder type 匹配（TITLE, SUBTITLE, BODY）
- OBJECT type 自動對應到 CONTENT/BODY
- 備用 idx 匹配確保向後相容

```python
# 優先使用 type 匹配，其次使用 idx 匹配
ph_data = type_map.get(ph_type_name) or type_map.get(ph_type_name.upper())

# 特殊處理：OBJECT 類型可能對應 CONTENT 或 BODY
if not ph_data and ph_type_name == "OBJECT":
    ph_data = type_map.get("CONTENT") or type_map.get("BODY")

# 備用：使用 idx 匹配
if not ph_data:
    ph_data = idx_map.get(ph_idx)
```

### 3.2 `_place_images()` 改進

**修改內容**:
- 優先搜尋 `PP_PLACEHOLDER.PICTURE` 類型的 shape
- 使用 `insert_picture()` 自動填入 placeholder
- 備用策略：依 layout_type 手動放置
- 新增 `full_image` layout 支援

```python
if picture_placeholder:
    picture_placeholder.insert_picture(str(img_path))
    return
```

---

## 四、整合測試

**測試檔案**: `backend/tests/test_pptx_pipeline.py`
**輸入資料**: `backend/tests/data/ml.md` (機器學習簡介)
**輸出**: `backend/tests/output/test_output.pptx`

### 測試結果

| 項目 | 結果 |
|------|------|
| 模板載入 | ✅ 正常 |
| 投影片生成 | ✅ 4 張成功 |
| Placeholder 填充 | ✅ 正確 |
| Bullet List | ✅ 正確 |
| 輸出驗證 | ✅ 8,689 bytes |

---

## 五、產出檔案清單

```
backend/data/templates/
├── education_minimal.pptx      # 修復後的 base template
├── education_basic_fixed.pptx  # 中間產物（idx 修復）
├── industrial_tech.pptx        # 工業科技風格
├── professional_corporate.pptx # 專業商務風格
├── strategic_consulting.pptx   # 策略諮詢風格
├── visionary_story.pptx        # 願景故事風格
├── create_minimal_template.py  # idx 修復腳本
├── create_minimal_6_layouts.py # Layout + Full Image 腳本
└── generate_theme_variants.py  # 配色變體生成腳本

backend/app/pptagent_core/roles/
└── slide_builder.py            # 已修改

backend/tests/
├── data/ml.md                  # 測試輸入
├── test_pptx_pipeline.py       # 整合測試腳本
└── output/test_output.pptx     # 測試輸出
```

---

## 六、後續建議

1. **清理暫存檔案**: 可刪除 `education_basic_fixed.pptx`（中間產物）
2. **更新 ppt_service_v2.py**: 確認使用 `education_minimal.pptx` 或其變體作為預設模板
3. **更新 template JSON**: 如有對應的 JSON 描述檔，需同步更新 layout 對照表
4. **考慮精簡 Layout**: 目前保留 13 個 layout，若想精簡為 6 個需重建 slideMaster XML
