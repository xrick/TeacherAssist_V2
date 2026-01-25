# 五階段 PPTX 生成架構確認與前端更新

**日期**: 2026-01-25  
**類型**: 架構分析與實作  
**狀態**: 完成

---

## 1. 架構確認結果

### 1.1 目前架構：五階段（含圖片整合）

經過分析 `ppt_service_v2.py`，確認目前專案使用**五階段架構**：

```
五階段流程（含圖片）：
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Stage 1         │    │ Stage 2         │    │ Stage 3         │
│ TemplateAnalyzer│ →  │ ContentGenerator│ →  │ContentOrganizerV2│
│   (0-10%)       │    │   (10-45%)      │    │   (45-65%)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
┌─────────────────┐    ┌─────────────────┐           ↓
│ Stage 5         │ ←  │ Stage 4         │ ←─────────┘
│ SlideBuilder    │    │ ImageEnricher   │  
│   (85-100%)     │    │   (65-85%)      │
└─────────────────┘    └─────────────────┘
```

### 1.2 各階段功能說明

| Stage | Role | 功能 | 輸出 |
|-------|------|------|------|
| **1** | `TemplateAnalyzer` | 分析 PPTX Template 結構 | `template_structure` (slides, placeholders) |
| **2** | `ContentGenerator` | LLM 擴展使用者輸入 | `draft_content` (含 visual_suggestion) |
| **3** | `ContentOrganizerV2` | 組織內容到 Template 結構 | `organized_content` (layout_index, placeholders) |
| **4** | `ImageEnricher` | 圖片搜尋與注入 (Pexels API) | `enriched_content` (含 images 欄位) |
| **5** | `SlideBuilder` | 建構最終 PPTX | PPTX bytes |

---

## 2. Layout Engine 分析

### 2.1 Layout Engine 使用位置

**只在 Stage 5 (SlideBuilder) 中使用**：

```python
# backend/app/pptagent_core/roles/slide_builder.py

from app.pptagent_core.layout_engine.auto_fitter import AutoFitter

class SlideBuilder:
    def _fill_slide_content(self, slide, slide_data):
        # 使用 AutoFitter 進行智慧字體縮放
        AutoFitter.fit_text(
            shape.text_frame, 
            text_str, 
            font_name="Arial", 
            max_font_size=max_size  # 標題 44pt, 內文 24pt
        )
```

### 2.2 Layout Engine 元件

| 元件 | 檔案 | 功能 |
|------|------|------|
| `TextMetrics` | `layout_engine/text_metrics.py` | 文字測量（EMU/像素轉換、跨平台字體） |
| `AutoFitter` | `layout_engine/auto_fitter.py` | 智慧字體縮放（二分搜尋法） |

### 2.3 各階段與 Layout Engine 關係

| 階段 | Role | 使用 Layout Engine | 使用 SlideBuilder |
|------|------|-------------------|------------------|
| Stage 1 | TemplateAnalyzer | ❌ | ❌ |
| Stage 2 | ContentGenerator | ❌ | ❌ |
| Stage 3 | ContentOrganizerV2 | ❌ | ❌ |
| Stage 4 | ImageEnricher | ❌ | ❌ |
| **Stage 5** | **SlideBuilder** | **✅ AutoFitter** | **✅ 本身** |

---

## 3. 前後端不一致問題

### 3.1 問題描述

更新前，前端 `ProgressMonitor.tsx` 只有 4 階段，缺少 `image_enrichment`：

**前端（更新前）**：
```typescript
const mainStages = [
  { key: "template_analysis", progressStart: 0 },
  { key: "content_generation", progressStart: 10 },
  { key: "content_organization", progressStart: 50 },
  { key: "pptx_building", progressStart: 80 },  // 缺少 image_enrichment
];
```

**後端（實際）**：
```
template_analysis (0-10%)
content_generation (10-45%)
content_organization (45-65%)
image_enrichment (65-85%)  ← 前端沒有對應！
pptx_building (85-100%)
```

### 3.2 影響

當後端發送 `image_enrichment` 進度事件時，前端：
- 無法正確顯示階段名稱
- 進度指示器無法對應到正確的圓點

---

## 4. 實作修復

### 4.1 修改檔案

**檔案**: `frontend/src/components/generation/ProgressMonitor.tsx`

### 4.2 修改內容

#### 4.2.1 更新階段定義

```typescript
// 修改前：4 階段
const stageNames: Record<string, string> = {
  template_analysis: "🔍 分析模板",
  content_generation: "✨ 生成內容",
  content_organization: "📋 組織結構",
  pptx_building: "🏗️ 建構簡報",
  adding_images: "🖼️ 自動配圖",  // 錯誤的名稱
  // ...
};

// 修改後：5 階段
const stageNames: Record<string, string> = {
  template_analysis: "🔍 分析模板",
  content_generation: "✨ 生成內容",
  content_organization: "📋 組織結構",
  image_enrichment: "🖼️ 配置圖片",  // 正確對應後端
  pptx_building: "🏗️ 建構簡報",
  generating_script: "📝 生成教學稿",
  completed: "✅ 完成",
};
```

#### 4.2.2 更新進度指示器

```typescript
// 修改前：4 階段
const mainStages = [
  { key: "template_analysis", name: "分析模板", progressStart: 0 },
  { key: "content_generation", name: "生成內容", progressStart: 10 },
  { key: "content_organization", name: "組織結構", progressStart: 50 },
  { key: "pptx_building", name: "建構簡報", progressStart: 80 },
];

// 修改後：5 階段
const mainStages = [
  { key: "template_analysis", name: "分析模板", progressStart: 0 },
  { key: "content_generation", name: "生成內容", progressStart: 10 },
  { key: "content_organization", name: "組織結構", progressStart: 45 },
  { key: "image_enrichment", name: "配置圖片", progressStart: 65 },
  { key: "pptx_building", name: "建構簡報", progressStart: 85 },
];
```

#### 4.2.3 更新 Grid 佈局

```tsx
// 修改前
<div className="mt-6 grid grid-cols-4 gap-2">

// 修改後
<div className="mt-6 grid grid-cols-5 gap-2">
```

#### 4.2.4 移除重複的後處理提示

```tsx
// 修改前：有 adding_images 判斷
{(currentStage === "adding_images" || currentStage === "generating_script") && (
  // ...
)}

// 修改後：只保留 generating_script（image_enrichment 已在主流程）
{currentStage === "generating_script" && (
  // ...
)}
```

---

## 5. 驗證結果

### 5.1 前後端 Stage 名稱對照

| 後端 Stage | 前端 mainStages | 狀態 |
|------------|----------------|------|
| `template_analysis` | `template_analysis` | ✅ 一致 |
| `content_generation` | `content_generation` | ✅ 一致 |
| `content_organization` | `content_organization` | ✅ 一致 |
| `image_enrichment` | `image_enrichment` | ✅ 一致 |
| `pptx_building` | `pptx_building` | ✅ 一致 |
| `completed` | (在 stageNames) | ✅ 有對應 |
| `generating_script` | (後處理) | ✅ 有對應 |

### 5.2 進度百分比對應

| Stage | 後端進度 | 前端 progressStart |
|-------|---------|-------------------|
| template_analysis | 0-10% | 0 |
| content_generation | 10-45% | 10 |
| content_organization | 45-65% | 45 |
| image_enrichment | 65-85% | 65 |
| pptx_building | 85-100% | 85 |

---

## 6. 規劃文件位置

| 文件 | 路徑 |
|------|------|
| 圖片整合計畫 | `claudedocs/dev_diary/image_integration_plan_2026-01-25_14.md` |
| 架構確認日誌 | `claudedocs/dev_diary/architecture_review_2026-01-25_14.md` |
| 本文件 | `claudedocs/dev_diary/five_stage_architecture_2026-01-25.md` |

---

## 7. 架構圖：完整五階段流程

```
使用者輸入 (Markdown/Text)
         │
         ↓
┌─────────────────────────────────────────────────────────┐
│ Stage 1: TemplateAnalyzer (0-10%)                       │
│ - 讀取 PPTX Template                                    │
│ - 提取 Slide Layouts 和 Placeholders                   │
│ - 輸出: template_structure                              │
└─────────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────┐
│ Stage 2: ContentGenerator (10-45%)                      │
│ - LLM 擴展使用者輸入                                    │
│ - 生成結構化投影片草稿                                  │
│ - 產生 visual_suggestion（供圖片搜尋）                  │
│ - 輸出: draft_content                                   │
└─────────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────┐
│ Stage 3: ContentOrganizerV2 (45-65%)                    │
│ - 整合 draft_content 和 template_structure              │
│ - 對應內容到 Placeholders                               │
│ - 選擇最佳 Layout                                       │
│ - 輸出: organized_content                               │
└─────────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────┐
│ Stage 4: ImageEnricher (65-85%) [可選]                  │
│ - 讀取 visual_suggestion                                │
│ - AI 生成搜尋關鍵字                                     │
│ - Pexels API 圖片搜尋                                   │
│ - 下載並快取圖片                                        │
│ - 輸出: enriched_content (含 images 欄位)               │
└─────────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────┐
│ Stage 5: SlideBuilder (85-100%)                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Layout Engine (AutoFitter)                          │ │
│ │ - 智慧字體縮放                                      │ │
│ │ - 文字測量與適配                                    │ │
│ │ - 避免文字溢出                                      │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ _place_images()                                     │ │
│ │ - 動態圖片放置                                      │ │
│ │ - 安全區域策略                                      │ │
│ │ - 避免遮擋文字                                      │ │
│ └─────────────────────────────────────────────────────┘ │
│ - 輸出: PPTX bytes                                      │
└─────────────────────────────────────────────────────────┘
         │
         ↓
     PPTX 檔案
```

---

## 8. 總結

1. **架構確認**: 目前是五階段流程，包含 ImageEnricher
2. **Layout Engine**: 只在 Stage 5 (SlideBuilder) 中使用 AutoFitter
3. **前端更新**: 已將 ProgressMonitor.tsx 從 4 階段更新為 5 階段
4. **一致性**: 前後端 Stage 名稱和進度百分比現已完全對應
