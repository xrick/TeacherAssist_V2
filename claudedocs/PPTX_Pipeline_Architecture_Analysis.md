# PPTX Generation Pipeline - Architecture Analysis

## Executive Summary

本文件分析當前 TeacherAssist V2 的 PPTX 生成管線問題，並對照參考專案 `PPTX-Presentation-Generator` 的實現，提出改進架構設計。

---

## 1. 當前系統問題診斷

### 1.1 觀察到的輸出問題

**測試輸出**: `data/outputs/test_ml_output.pptx`

| 問題 | 嚴重度 | 描述 |
|------|--------|------|
| Layout 單一化 | **Critical** | 所有 10 張 slide 只用了 Layout 2 (Title) 和 Layout 3 (Content)，沒有使用 Outline、Section Header、Full Image 等 |
| 結構缺失 | **Critical** | 缺少標準簡報結構：Title → Outline → Content Sections → Summary |
| 圖片完全缺失 | **High** | 雖然 `.env` 有設定 `PEXELS_API_KEY`，但 `add_images=False` 被傳入，且 ImageEnricher 未被觸發 |
| Bullet 格式異常 | **Medium** | 第 8 張 slide 標題出現 `**為什麼現在這麼紅？**` markdown 語法未被處理 |

### 1.2 問題根因分析

```
問題鏈路追蹤：

[User Input] → ContentGenerator
                    │
                    ▼ 生成 slide_type: "title|content|section|closing"
                    │ 但只有 4 種類型，缺少 "outline" 類型
                    │
[Template] → TemplateAnalyzer  
                    │
                    ▼ suggest_layout_sequence() 
                    │ 只找 "TITLE+SUBTITLE" 和 "TITLE+CONTENT" 兩種 layout
                    │ 不支援 Outline、Section Header、Image Layout
                    │
              ContentOrganizerV2
                    │
                    ▼ _determine_layout_type()
                    │ 只映射到 5 種類型：title, content, two_column, image_text, closing
                    │ 沒有 outline、section_header 的智能選擇
                    │
              ImageEnricher
                    │
                    ▼ SKIP_IMAGE_LAYOUTS = {"title", "closing", "section_header"}
                    │ 但測試時 add_images=False，完全跳過
                    │
              SlideBuilder
                    │
                    ▼ _fill_slide_content() 使用 type-based matching
                    │ _place_images() 有 PICTURE placeholder 支援但未觸發
```

---

## 2. 參考專案分析：PPTX-Presentation-Generator

### 2.1 核心設計差異

| 特性 | 參考專案 | 當前系統 |
|------|----------|----------|
| **Slide Type 控制** | LLM 用 Tags 明確指定：`[L_TS]`, `[L_CS]`, `[L_IS]`, `[L_THS]` | LLM 輸出 `slide_type` 欄位，但後續處理忽略 |
| **Layout 選擇** | Tag → Layout Index 直接映射 | `suggest_layout_sequence()` 只用兩種 layout |
| **圖片處理** | `[IMAGE]...[/IMAGE]` tag 觸發 icrawler 下載 | ImageEnricher 需 visual_suggestion，但常被跳過 |
| **結構化輸出** | `[SLIDEBREAK]` 分割，Tag-based 解析 | JSON 輸出，需 LLM 正確生成 |

### 2.2 參考專案的 Layout 映射

```python
# 參考專案的 Slide Type → Layout Index 映射
Tag         → Layout → 函式
[L_TS]      → 0      → create_title_slide(title, subtitle)
[L_CS]      → 1      → create_title_and_content_slide(title, content)
[L_IS]      → 8      → create_title_and_content_and_image_slide(title, content, image_query)
[L_THS]     → 2      → create_section_header_slide(title)
```

### 2.3 參考專案的圖片處理流程

```
[IMAGE]tag_content[/IMAGE]
         │
         ▼
 ICrawlerCrawler.get_image(query, save_dir)
         │
         ▼
 GoogleImageCrawler.crawl(keyword=query, max_num=1)
         │
         ▼
 slide.shapes.add_picture(img_path, 
                          slide.placeholders[1].left,
                          slide.placeholders[1].top,
                          slide.placeholders[1].width,
                          slide.placeholders[1].height)
```

關鍵點：**圖片位置使用 placeholder 的位置和尺寸**，而非硬編碼。

---

## 3. 當前系統完整流程圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PPTServiceV2.generate() 主流程                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    │                               │                               │
    ▼                               ▼                               ▼
┌─────────┐                  ┌─────────────┐                 ┌─────────────┐
│ Stage 1 │                  │  Stage 1.5  │                 │  Stage 2    │
│Template │                  │InputClassify│                 │ Content     │
│Analyzer │                  │             │                 │ Generator   │
└────┬────┘                  └──────┬──────┘                 └──────┬──────┘
     │                              │                               │
     │ template_structure           │ InputMode                     │ draft_content
     │ {slides: [{                  │ (SEARCH/DIRECT)               │ {title, slides: [{
     │   layout_index,              │                               │   slide_number,
     │   layout_name,               │                               │   slide_type,  ← 未被使用!
     │   placeholders: [...]        │                               │   title,
     │ }]}                          │                               │   bullet_points,
     │                              │                               │   visual_suggestion ←未被使用!
     │                              │                               │ }]}
     └──────────────────────────────┼───────────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │    Stage 3      │
                          │ContentOrganizer │
                          │      V2         │
                          └────────┬────────┘
                                   │
                                   │ organized_content
                                   │ {slides: [{
                                   │   layout_index,     ← 從 template_structure 複製
                                   │   layout: "content" ← _determine_layout_type() 計算
                                   │   placeholders: [{
                                   │     type, content   ← LLM 填入
                                   │   }]
                                   │ }]}
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
          ┌─────────────────┐           ┌─────────────────┐
          │    Stage 4      │           │  (SKIPPED)      │
          │ ImageEnricher   │           │ add_images=False│
          │                 │           └─────────────────┘
          └────────┬────────┘
                   │
                   │ enriched_content
                   │ {slides: [{
                   │   ...,
                   │   images: [{file_path, ...}]
                   │ }]}
                   │
                   ▼
          ┌─────────────────┐
          │    Stage 5      │
          │  SlideBuilder   │
          └────────┬────────┘
                   │
                   ▼
              PPTX Bytes
```

### 3.1 問題點標註

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 問題 1: ContentGenerator 的 slide_type 欄位被忽略                        │
├──────────────────────────────────────────────────────────────────────────┤
│ ContentGenerator 輸出:                                                   │
│   slide_type: "title|content|section|closing"                           │
│                                                                          │
│ 但 ContentOrganizerV2 沒有使用這個欄位來選擇 layout！                    │
│ 它只用 template_structure 的 layout_index（由 TemplateAnalyzer 決定）    │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ 問題 2: TemplateAnalyzer.suggest_layout_sequence() 太簡單                │
├──────────────────────────────────────────────────────────────────────────┤
│ 當前邏輯:                                                                │
│   1. 找 "TITLE+SUBTITLE" layout → 用於開頭和結尾                        │
│   2. 找 "TITLE+CONTENT" layout → 用於所有中間頁                         │
│   3. 沒有考慮 Outline、Section Header、Image Layout                      │
│                                                                          │
│ 結果: 所有內容頁都用同一個 layout                                        │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ 問題 3: visual_suggestion 未傳遞到 ImageEnricher                         │
├──────────────────────────────────────────────────────────────────────────┤
│ ContentGenerator 生成 visual_suggestion:                                 │
│   "一個展示電腦與人類在一起學習的圖像。關鍵詞：AI, ML"                  │
│                                                                          │
│ 但這個欄位在 ContentOrganizerV2 中被存到 slide 的外層，                 │
│ 而 ImageEnricher 需要從 draft_content 重新取得                          │
│ → 資料流斷裂，容易遺失                                                   │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ 問題 4: 測試呼叫時 add_images=False                                      │
├──────────────────────────────────────────────────────────────────────────┤
│ 測試腳本:                                                                │
│   result = await ppt.generate(                                           │
│       user_input=user_input,                                             │
│       template='education_minimal',                                      │
│       add_images=False,  # ← 這裡關閉了圖片                              │
│   )                                                                      │
│                                                                          │
│ 即使 PEXELS_API_KEY 存在，圖片功能也被關閉                              │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 標準簡報結構（應該要有的）

```
理想的 10 張簡報結構：

Slide 1:  Title Slide          (Layout: Title + Subtitle)
          "機器學習概述"
          "讓電腦從經驗中學習的技術"

Slide 2:  Outline              (Layout: Title + Bullet List)
          "今日大綱"
          • 什麼是機器學習
          • 三大類別
          • 運作流程
          • 為什麼這麼紅

Slide 3:  Section Header       (Layout: Section Header)
          "Part 1: 基礎概念"

Slide 4:  Content + Image      (Layout: Title + Content + Image)
          "什麼是機器學習？"
          • AI 的子領域
          • 從經驗中學習
          [Image: 電腦學習示意圖]

Slide 5:  Content              (Layout: Title + Content)
          "監督式學習"
          • 提供標註好的資料
          • 分類、迴歸

Slide 6:  Content              (Layout: Title + Content)  
          "非監督式學習"
          • 沒有標籤
          • 分群、降維

Slide 7:  Content + Image      (Layout: Title + Content + Image)
          "強化學習"
          • 獲得最大累積獎勵
          [Image: AlphaGo]

Slide 8:  Section Header       (Layout: Section Header)
          "Part 2: 為什麼這麼紅？"

Slide 9:  Content              (Layout: Title + Content)
          "機器學習爆發的原因"
          • 大數據
          • 運算能力
          • 演算法突破

Slide 10: Closing              (Layout: Title + Subtitle)
          "總結"
          "機器學習正在改變世界"
```

---

## 5. 改進架構設計

### 5.1 核心改進：Slide Type 驅動的 Layout 選擇

```
改進後的資料流：

User Input
    │
    ▼
ContentGenerator (改進 Prompt)
    │
    │ 輸出增強：
    │ {
    │   slides: [{
    │     slide_type: "title|outline|section|content|content_image|closing",
    │     ...
    │   }]
    │ }
    │
    ▼
TemplateAnalyzer (改進)
    │
    │ 新增：get_layout_for_type(slide_type) → layout_index
    │ 映射：
    │   "title"         → Layout 1 (Title Slide)
    │   "outline"       → Layout 2 (Title + Content)
    │   "section"       → Layout 3 (Section Header) 
    │   "content"       → Layout 2 (Title + Content)
    │   "content_image" → Layout 9 (Title + Content + Image)
    │   "closing"       → Layout 1 (Title Slide)
    │
    ▼
ContentOrganizerV2 (改進)
    │
    │ 使用 slide_type 來選擇 layout_index
    │ 而非固定序列
    │
    ▼
ImageEnricher (改進)
    │
    │ 只為 slide_type="content_image" 的 slide 加入圖片
    │ 使用 visual_suggestion 生成搜尋關鍵字
    │
    ▼
SlideBuilder (維持)
    │
    ▼
PPTX Bytes
```

### 5.2 ContentGenerator Prompt 改進

```
新增的 Slide Types (6 種):

1. title         - 標題頁 (Title + Subtitle)
2. outline       - 大綱頁 (Title + Bullet List of topics)
3. section       - 章節標題 (Section Header only)
4. content       - 內容頁 (Title + Bullet Points)
5. content_image - 含圖內容頁 (Title + Bullet Points + Image)
6. closing       - 結尾頁 (Title + Subtitle/Summary)

Prompt 範例:
"""
...
You MUST follow this presentation structure:
- Slide 1: type="title" - Presentation title and subtitle
- Slide 2: type="outline" - List of main topics to be covered
- Slides 3-N: type="section", "content", or "content_image"
  - Use "section" for topic transitions
  - Use "content_image" for slides that benefit from visual aid
  - Use "content" for text-heavy information
- Last Slide: type="closing" - Summary or thank you

For content_image slides, provide detailed visual_suggestion with searchable keywords.
"""
```

### 5.3 TemplateAnalyzer 改進

```python
# 新增方法：slide_type → layout_index 映射
class TemplateAnalyzer:
    
    # 定義 slide_type 到 layout 特徵的映射
    SLIDE_TYPE_LAYOUT_FEATURES = {
        "title": {"required": ["TITLE", "SUBTITLE"], "preferred_name": "title"},
        "outline": {"required": ["TITLE", "CONTENT"], "preferred_name": "content"},
        "section": {"required": ["TITLE"], "max_placeholders": 2, "preferred_name": "section"},
        "content": {"required": ["TITLE", "CONTENT"], "preferred_name": "content"},
        "content_image": {"required": ["TITLE", "CONTENT", "PICTURE"], "preferred_name": "picture"},
        "closing": {"required": ["TITLE"], "preferred_name": "title"},
    }
    
    def get_layout_for_type(self, slide_type: str) -> int:
        """根據 slide_type 找到最適合的 layout index"""
        features = self.SLIDE_TYPE_LAYOUT_FEATURES.get(slide_type, {})
        required = features.get("required", ["TITLE"])
        preferred_name = features.get("preferred_name", "")
        
        layouts = self.get_available_layouts()
        
        # 優先匹配 name
        for layout in layouts:
            if preferred_name.lower() in layout["name"].lower():
                ph_types = {ph["type"] for ph in layout["placeholders"]}
                if all(r in ph_types for r in required):
                    return layout["index"]
        
        # 次優先：匹配 placeholder 類型
        for layout in layouts:
            ph_types = {ph["type"] for ph in layout["placeholders"]}
            if all(r in ph_types for r in required):
                return layout["index"]
        
        # Fallback
        return 1  # 預設 content layout
```

### 5.4 ContentOrganizerV2 改進

```python
# 改進：使用 slide_type 來選擇 layout
class ContentOrganizerV2:
    
    async def organize(self, draft_content, template_structure):
        # ...
        
        # 改進：根據 draft 的 slide_type 決定 layout
        for i, draft_slide in enumerate(draft_slides):
            slide_type = draft_slide.get("slide_type", "content")
            
            # 使用 TemplateAnalyzer 的新方法取得適合的 layout
            layout_index = self.analyzer.get_layout_for_type(slide_type)
            
            organized_slide = {
                "index": i,
                "layout_index": layout_index,
                "layout": slide_type,  # 保留 type 供 ImageEnricher 使用
                "placeholders": self._map_content_to_placeholders(
                    draft_slide, 
                    template_structure["layouts"][layout_index]
                ),
                "visual_suggestion": draft_slide.get("visual_suggestion", ""),
            }
```

### 5.5 ImageEnricher 改進

```python
# 改進：只為 content_image 類型加入圖片
class ImageEnricher:
    
    # 改進：明確定義哪些 slide_type 需要圖片
    IMAGE_SLIDE_TYPES = {"content_image"}
    
    async def enrich(self, organized_content, draft_content, ...):
        for slide in slides:
            slide_type = slide.get("layout", "content")
            
            # 只為 content_image 類型加入圖片
            if slide_type not in self.IMAGE_SLIDE_TYPES:
                enriched_slide["images"] = []
                continue
            
            # 使用 visual_suggestion（已在 organized_content 中）
            visual_suggestion = slide.get("visual_suggestion", "")
            
            # 搜尋並加入圖片
            images = await self._get_images_for_slide(visual_suggestion, ...)
```

---

## 6. 改進後的完整流程圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    改進後的 PPTServiceV2.generate() 流程                    │
└─────────────────────────────────────────────────────────────────────────────┘

User Input: "機器學習概述"
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 1: InputClassifier                                                    │
│ 判斷：短題目 → SEARCH_MODE                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 2: ContentGenerator (改進後的 Prompt)                                 │
│                                                                             │
│ 輸出：                                                                      │
│ {                                                                           │
│   "title": "機器學習概述",                                                  │
│   "slides": [                                                               │
│     {"slide_type": "title", "title": "機器學習概述", ...},                  │
│     {"slide_type": "outline", "title": "今日大綱", "bullet_points": [...]}, │
│     {"slide_type": "section", "title": "Part 1: 基礎概念"},                 │
│     {"slide_type": "content_image", "title": "什麼是ML", "visual_suggestion": "..."}, │
│     {"slide_type": "content", "title": "監督式學習", ...},                  │
│     {"slide_type": "content", "title": "非監督式學習", ...},                │
│     {"slide_type": "content_image", "title": "強化學習", "visual_suggestion": "..."}, │
│     {"slide_type": "section", "title": "Part 2: 為什麼這麼紅"},             │
│     {"slide_type": "content", "title": "爆發原因", ...},                    │
│     {"slide_type": "closing", "title": "總結", ...}                         │
│   ]                                                                         │
│ }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 3: TemplateAnalyzer (改進後)                                          │
│                                                                             │
│ 映射 slide_type → layout_index:                                             │
│   "title"         → Layout 1 (Title Slide)                                  │
│   "outline"       → Layout 2 (Title + Content)                              │
│   "section"       → Layout 3 (Section Header)                               │
│   "content"       → Layout 2 (Title + Content)                              │
│   "content_image" → Layout 9 (Title + Content + Picture)                    │
│   "closing"       → Layout 1 (Title Slide)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 4: ContentOrganizerV2 (改進後)                                        │
│                                                                             │
│ 輸出：每張 slide 帶有正確的 layout_index 和 visual_suggestion               │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 5: ImageEnricher (改進後)                                             │
│                                                                             │
│ 只為 slide_type="content_image" 的 slide 搜尋並下載圖片                    │
│ 使用 Pexels API + visual_suggestion 關鍵字                                  │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 6: SlideBuilder                                                       │
│                                                                             │
│ 根據 layout_index 選擇正確的 slide layout                                   │
│ 填入 placeholder 內容                                                       │
│ 放置圖片到 PICTURE placeholder 位置                                         │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
PPTX Output: 結構正確、有圖片的專業簡報
```

---

## 7. 實作優先順序

### Phase 1: 修復 Slide Type 流程 (Critical)

1. **ContentGenerator Prompt 改進**
   - 新增 6 種 slide_type
   - 強制結構：title → outline → sections → closing
   - 明確指示哪些 slide 需要 visual_suggestion

2. **TemplateAnalyzer 改進**
   - 新增 `get_layout_for_type(slide_type)` 方法
   - 建立 slide_type → layout 映射表

3. **ContentOrganizerV2 改進**
   - 使用 draft 的 slide_type 決定 layout_index
   - 保留 visual_suggestion 到 organized_content

### Phase 2: 修復圖片流程 (High)

4. **ImageEnricher 改進**
   - 只為 `content_image` 類型加入圖片
   - 直接使用 organized_content 中的 visual_suggestion

5. **測試腳本修復**
   - 預設 `add_images=True`
   - 確認 Pexels API 連通性

### Phase 3: 優化 (Medium)

6. **Layout 多樣性**
   - 分析 education_minimal.pptx 的所有 13 個 layout
   - 建立完整的 slide_type → layout 映射

7. **圖片位置優化**
   - 使用 PICTURE placeholder 的實際位置
   - 支援多圖片佈局

---

## 8. 測試驗收標準

```
輸入: "機器學習概述"
預期輸出: 10 張投影片

✅ Slide 1: Title Slide (Layout 1)
✅ Slide 2: Outline (Layout 2) - 包含大綱 bullet list
✅ Slide 3: Section Header (Layout 3)
✅ Slide 4: Content + Image (Layout 9) - 有圖片
✅ Slide 5-7: Content (Layout 2)
✅ Slide 8: Section Header (Layout 3)
✅ Slide 9: Content (Layout 2)
✅ Slide 10: Closing (Layout 1)

圖片驗收:
✅ content_image slides 有 Pexels 圖片
✅ 圖片位置在 PICTURE placeholder 位置
✅ 圖片尺寸符合 placeholder 尺寸
```

---

*Generated by /sc:design on 2026-01-29*
