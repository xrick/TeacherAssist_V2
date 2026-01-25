# 開發日誌：四階段流程與 Layout Engine 狀態確認

**日期**: 2026-01-25 14:00  
**類型**: 架構確認  
**狀態**: 確認完成

---

## 確認結果：四階段流程與 Layout Engine 狀態

專案**已經從五階段改為四階段**，同時 **Layout Engine 已經實作完成**。

---

## 新四階段流程（V2）

| 階段 | Role | 功能 | 狀態 |
|------|------|------|------|
| **Stage 1** | `TemplateAnalyzer` | 分析 PPTX Template 結構、提取 Placeholder | ✅ 已實作 |
| **Stage 2** | `ContentGenerator` | LLM 擴展使用者輸入為結構化草稿 | ✅ 已實作 |
| **Stage 3** | `ContentOrganizerV2` | 將草稿內容組織到 Template 結構 | ✅ 已實作 |
| **Stage 4** | `SlideBuilder` | 建構最終 PPTX（整合 Layout Engine） | ✅ 已實作 |

**服務檔案**: `ppt_service_v2.py` ✅ 已實作完整的四階段流程

---

## Layout Engine 狀態

| 元件 | 檔案 | 功能 | 狀態 |
|------|------|------|------|
| `TextMetrics` | `text_metrics.py` | 文字測量（支援 EMU/像素轉換、跨平台字體偵測） | ✅ 已實作 |
| `AutoFitter` | `auto_fitter.py` | 智慧字體縮放（二分搜尋法尋找最佳字級） | ✅ 已實作 |

**Layout Engine 特色**：
- 使用 Pillow 進行精確文字測量
- 支援 Windows/macOS/Linux 字體自動偵測
- 二分搜尋法優化字體大小計算（效能優化）
- 已整合到 `SlideBuilder._fill_slide_content()` 中

---

## 新舊架構對比

```
舊五階段（ppt_service.py）：
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ SchemaExtractor │ →  │ ContentOrganizer│ →  │ LayoutSelector  │
│     (0-20%)     │    │    (20-40%)     │    │    (40-60%)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ↓
┌─────────────────┐    ┌─────────────────┐
│     Editor      │ →  │      Coder      │
│    (60-80%)     │    │   (80-100%)     │
└─────────────────┘    └─────────────────┘

新四階段（ppt_service_v2.py）：
┌───────────────────┐    ┌───────────────────┐
│ TemplateAnalyzer  │    │ ContentGenerator  │
│     (0-10%)       │    │    (10-50%)       │
└───────────────────┘    └───────────────────┘
         ↓                        ↓
         └────────┬───────────────┘
                  ↓
        ┌───────────────────┐
        │ ContentOrganizerV2│
        │    (50-80%)       │
        └───────────────────┘
                  ↓
        ┌───────────────────┐
        │   SlideBuilder    │  ← 整合 Layout Engine
        │   (80-100%)       │
        └───────────────────┘
```

---

## 需注意事項

1. **API 路由尚未切換到 V2**
   - `generation.py` 目前仍使用 `ppt_service.py`（舊五階段）
   - 需要更新為使用 `ppt_service_v2.py`

2. **兩套流程並存**
   - 舊流程保留在 `roles/__init__.py` 中（向後相容）
   - 新流程可透過 `get_ppt_service_v2()` 使用

3. **Layout Engine 尚有 TODO**
   - `slide_builder.py:118` 註解提到可從 Template 讀取原本字體名稱

---

## 相關檔案位置

```
backend/app/
├── services/
│   ├── ppt_service.py      # 舊五階段（仍在使用）
│   └── ppt_service_v2.py   # 新四階段 ✅
├── pptagent_core/
│   ├── roles/
│   │   ├── template_analyzer.py    # Stage 1 ✅
│   │   ├── content_generator.py    # Stage 2 ✅
│   │   ├── content_organizer_v2.py # Stage 3 ✅
│   │   └── slide_builder.py        # Stage 4 ✅
│   └── layout_engine/
│       ├── __init__.py
│       ├── text_metrics.py   # ✅ 已實作
│       └── auto_fitter.py    # ✅ 已實作
```

---

## 下一步建議

1. 將 API 路由切換到新的四階段流程
2. 完成 Layout Engine 的 TODO（從 Template 讀取字體名稱）
3. 進行整合測試確認新流程運作正常
