# PPTX 生成系統 - Blueprint 架構設計文件

**版本**: v0.1  
**日期**: 2026-01-29 13:43  
**狀態**: 設計完成，待實作  

---

## 1. 執行摘要

### 1.1 問題陳述

當前 TeacherAssist V2 的 PPTX 生成管線存在以下問題：

| 問題 | 嚴重度 | 根因 |
|------|--------|------|
| Layout 單一化 | Critical | 所有內容頁只用 Layout 2/3，忽略 LLM 輸出的 `slide_type` |
| 結構缺失 | Critical | 缺少 Outline、Section Header 的智能選擇機制 |
| 圖片完全缺失 | High | `add_images=False` 被傳入，`visual_suggestion` 資料流斷裂 |
| 排版混亂 | High | 文字位置由 placeholder 決定，無法精確控制 |

### 1.2 解決方案

採用 **Blueprint-First** 架構：

```
核心理念：先產生完整的 JSON 藍圖，再按圖施工

User Input → [LLM] → Blueprint JSON → [Builder] → PPTX
                         ↑
                    可審核/可修改
```

---

## 2. 參考專案分析

### 2.1 PPTX-Presentation-Generator (Python)

**GitHub**: 參考專案 1

**核心設計**:
```python
# Tag-based Layout 選擇
[L_TS]  → slide_layouts[0]  # Title Slide
[L_CS]  → slide_layouts[1]  # Content Slide  
[L_IS]  → slide_layouts[8]  # Image Slide
[L_THS] → slide_layouts[2]  # Section Header

# 圖片處理
[IMAGE]neural network diagram[/IMAGE] → icrawler 搜尋 → 下載 → 放置
```

**圖片位置策略**:
```python
slide.shapes.add_picture(
    img_path, 
    slide.placeholders[1].left,   # 使用 placeholder 的位置
    slide.placeholders[1].top,
    slide.placeholders[1].width,
    slide.placeholders[1].height
)
```

**優點**:
- Tag 明確，Layout 映射清晰
- 圖片位置使用 placeholder，符合模板設計

**缺點**:
- Tag 格式對 LLM 輸出不夠友好
- icrawler 爬蟲不夠穩定

---

### 2.2 presentation-ai-main (TypeScript/React)

**GitHub**: 參考專案 2

**核心設計**:
```typescript
// LLM 輸出 XML 格式
<SECTION layout="right">
  <H1>標題</H1>
  <P>內容</P>
  <IMG query="search keywords" />
</SECTION>

// Slide 結構 (Plate.js AST)
type PlateSlide = {
  id: string;
  content: PlateNode[];
  rootImage?: {
    query: string;
    url?: string;
    layoutType?: "left" | "right" | "vertical" | "background";
  };
  layoutType?: LayoutType;
  alignment?: "start" | "center" | "end";
};
```

**圖片位置策略**:
```typescript
// 根據 layoutType 動態計算
switch (layoutType) {
  case "left":
    imageOptions = { x: 0, w: SLIDE_WIDTH * 0.45 };
    break;
  case "right":
    imageOptions = { x: SLIDE_WIDTH * 0.55, w: SLIDE_WIDTH * 0.45 };
    break;
  case "vertical":
    imageOptions = { y: 0, h: SLIDE_HEIGHT * 0.4 };
    break;
  case "background":
    imageOptions = { x: 0, y: 0, w: SLIDE_WIDTH, h: SLIDE_HEIGHT };
    break;
}
```

**優點**:
- 結構化程度高
- 圖片位置靈活可控
- 支援豐富視覺元素 (Pyramid, Timeline, Cycle)

**缺點**:
- TypeScript/React 生態，不適合直接移植
- 使用 PptxGenJS 而非 python-pptx

---

### 2.3 GenSlide-main (Python)

**GitHub**: 參考專案 3

**核心設計**:
```python
# LLM 直接輸出 JSON 陣列
PROMPT = """
Return the response as an array of json objects.
The first item must be a json object for the title slide:
{"id": 1, "title_text": "Title", "subtitle_text": "Subtitle", "is_title_slide": "yes"}

Slides format:
{"id": 2, "title_text": "Slide Title", "text": ["Bullet 1", "Bullet 2"]}
"""

# 極簡 Slide 建構
def add_slide(self, slide_data):
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    shapes.title.text = slide_data["title_text"]
    
    for bullet in slide_data["text"]:
        p = tf.add_paragraph()
        p.text = bullet
    
    if "img_path" in slide_data:
        for img_path in slide_data["img_path"]:
            slide.shapes.add_picture(img_path, Inches(6), Inches(2), height=Inches(4))
```

**優點**:
- 結構最簡單，LLM 容易生成正確 JSON
- 直接用 JSON，解析風險低

**缺點**:
- 功能太簡單，只有 title + bullets
- 圖片位置硬編碼 `Inches(6), Inches(2)`
- 沒有 slide_type/layout 概念

---

### 2.4 三專案比較總表

| 特性 | PPTX-Generator | presentation-ai | GenSlide |
|------|----------------|-----------------|----------|
| **語言** | Python | TypeScript | Python |
| **LLM 輸出格式** | Tag-based | XML | JSON |
| **Layout 控制** | Tag→Index 映射 | layoutType 屬性 | 無 |
| **圖片搜尋** | icrawler 爬蟲 | 無 (需外部) | 無 |
| **圖片位置** | Placeholder 位置 | 動態計算 | 硬編碼 |
| **結構化程度** | 中 | 高 | 低 |
| **LLM 友好度** | 低 | 中 | 高 |

---

## 3. Blueprint 架構設計

### 3.1 設計原則

1. **Blueprint First**: 先產生完整 JSON 藍圖，再按圖施工
2. **Layout 明確**: 每頁都有明確的 `slide_type` 和 `layout_index`
3. **圖片位置可控**: 每張圖片都有獨立的 `position` 設定
4. **結構強制**: 強制簡報結構 (title → outline → sections → closing)
5. **可審核**: Blueprint 可以在建構前檢視和修改

### 3.2 Slide Types 定義

| slide_type | 說明 | 必要欄位 | 預設 Layout |
|------------|------|----------|-------------|
| `title` | 標題頁 | title, subtitle | Layout 1 |
| `outline` | 大綱頁 | title, bullets | Layout 2 |
| `section` | 章節標題 | title | Layout 3 |
| `content` | 純文字內容 | title, bullets | Layout 2 |
| `content_image` | 文字+圖片 | title, bullets, images | Layout 9 |
| `full_image` | 全版圖片 | images | Layout 12 |
| `two_column` | 雙欄佈局 | title, left, right | Layout 4 |
| `closing` | 結尾頁 | title, subtitle | Layout 1 |

### 3.3 Blueprint JSON Schema

```json
{
  "$schema": "PPTX Blueprint v1.0",
  
  "metadata": {
    "title": "簡報主標題",
    "author": "TeacherAssist V2",
    "language": "zh-TW",
    "created_at": "2026-01-29T13:43:00Z",
    "template": "education_minimal.pptx",
    "theme_colors": {
      "primary": "#3B82F6",
      "secondary": "#1F2937",
      "accent": "#60A5FA"
    }
  },
  
  "structure": {
    "total_slides": 10,
    "has_outline": true,
    "section_count": 2,
    "image_slides_count": 3
  },
  
  "slides": [
    {
      "index": 0,
      "slide_type": "title",
      "layout_index": 1,
      "layout_name": "Title Slide",
      
      "content": {
        "title": "機器學習概述",
        "subtitle": "讓電腦從經驗中學習的技術",
        "speaker_notes": "歡迎各位..."
      },
      
      "text_layout": {
        "title": {
          "placeholder_idx": 0,
          "font_size": 44,
          "font_bold": true,
          "alignment": "center",
          "position": {"x": 0.5, "y": 2.5, "w": 9.0, "h": 1.5}
        },
        "subtitle": {
          "placeholder_idx": 1,
          "font_size": 24,
          "alignment": "center",
          "position": {"x": 0.5, "y": 4.2, "w": 9.0, "h": 1.0}
        }
      },
      
      "images": []
    },
    
    {
      "index": 1,
      "slide_type": "outline",
      "layout_index": 2,
      "layout_name": "Title and Content",
      
      "content": {
        "title": "今日大綱",
        "bullets": [
          "什麼是機器學習",
          "三大核心類別",
          "運作流程",
          "為什麼這麼紅"
        ]
      },
      
      "text_layout": {
        "title": {"placeholder_idx": 0, "font_size": 36},
        "body": {
          "placeholder_idx": 10,
          "font_size": 24,
          "bullet_style": "numbered",
          "line_spacing": 1.5
        }
      },
      
      "images": []
    },
    
    {
      "index": 2,
      "slide_type": "section",
      "layout_index": 3,
      "layout_name": "Section Header",
      
      "content": {
        "title": "Part 1",
        "subtitle": "基礎概念"
      },
      
      "images": []
    },
    
    {
      "index": 3,
      "slide_type": "content_image",
      "layout_index": 9,
      "layout_name": "Title, Content and Image",
      
      "content": {
        "title": "什麼是機器學習？",
        "bullets": [
          "人工智慧（AI）的子領域",
          "讓電腦從經驗中學習",
          "無需顯式程式設計"
        ],
        "speaker_notes": "機器學習是 AI 的核心技術之一..."
      },
      
      "text_layout": {
        "title": {"placeholder_idx": 0, "font_size": 32},
        "body": {"placeholder_idx": 10, "font_size": 20}
      },
      
      "images": [
        {
          "image_id": "img_001",
          "search_query": "artificial intelligence neural network brain",
          "alt_text": "神經網路示意圖",
          "source": "pexels",
          "url": null,
          "file_path": null,
          "position": {
            "layout_type": "right",
            "x": 6.2,
            "y": 1.5,
            "w": 3.5,
            "h": 4.5,
            "object_fit": "cover"
          }
        }
      ]
    },
    
    {
      "index": 9,
      "slide_type": "closing",
      "layout_index": 1,
      
      "content": {
        "title": "總結",
        "subtitle": "機器學習正在改變世界"
      },
      
      "images": []
    }
  ]
}
```

### 3.4 Image Position Templates

```python
IMAGE_POSITION_TEMPLATES = {
    # 圖片在右側 (最常用)
    "right": {
        "x": 6.2,    # 左邊距 (inches)
        "y": 1.5,    # 上邊距 (inches)
        "w": 3.5,    # 寬度 (inches)
        "h": 4.5     # 高度 (inches)
    },
    
    # 圖片在左側
    "left": {
        "x": 0.3,
        "y": 1.5,
        "w": 3.5,
        "h": 4.5
    },
    
    # 圖片在上方
    "top": {
        "x": 2.5,
        "y": 0.5,
        "w": 5.0,
        "h": 2.5
    },
    
    # 圖片在下方
    "bottom": {
        "x": 2.5,
        "y": 4.0,
        "w": 5.0,
        "h": 2.5
    },
    
    # 全版背景圖
    "background": {
        "x": 0,
        "y": 0,
        "w": 10.0,      # 16:9 slide width
        "h": 5.625      # 16:9 slide height
    },
    
    # 小圖在右下角
    "small_right": {
        "x": 7.0,
        "y": 3.5,
        "w": 2.5,
        "h": 2.0
    }
}
```

---

## 4. 完整生成流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PPTX Blueprint Pipeline                             │
└─────────────────────────────────────────────────────────────────────────────┘

                              User Input
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 1: Input Classification                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 功能: 判斷輸入類型                                                           │
│                                                                             │
│ 輸入: user_input (str)                                                      │
│ 輸出: InputMode (SHORT_TOPIC | LONG_ARTICLE)                                │
│                                                                             │
│ 判斷邏輯:                                                                   │
│   - 字數 < 150 → SHORT_TOPIC (需要 LLM 生成內容)                            │
│   - 字數 >= 150 + 段落 >= 3 → LONG_ARTICLE (需要 LLM 結構化)                │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 2: Template Analysis                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 功能: 分析 PPTX Template 結構                                               │
│                                                                             │
│ 輸入: template_path (Path)                                                  │
│ 輸出: TemplateInfo                                                          │
│   {                                                                         │
│     layouts: [                                                              │
│       {index: 0, name: "Blank", placeholders: [...]},                       │
│       {index: 1, name: "Title Slide", placeholders: [...]},                 │
│       ...                                                                   │
│     ],                                                                      │
│     slide_type_mapping: {                                                   │
│       "title": 1,                                                           │
│       "outline": 2,                                                         │
│       "section": 3,                                                         │
│       "content": 2,                                                         │
│       "content_image": 9,                                                   │
│       "closing": 1                                                          │
│     }                                                                       │
│   }                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 3: Blueprint Generation (LLM)                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 功能: LLM 生成完整 Blueprint JSON                                           │
│                                                                             │
│ 輸入:                                                                       │
│   - user_input                                                              │
│   - input_mode                                                              │
│   - slide_count                                                             │
│   - template_info                                                           │
│                                                                             │
│ Prompt 策略:                                                                │
│   - 強制結構: title → outline → sections → content → closing                │
│   - 明確 slide_type 選項                                                    │
│   - 對 content_image 類型，要求提供 search_query                            │
│                                                                             │
│ 輸出: Blueprint JSON (不含圖片 URL/path)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 4: Blueprint Validation & Enhancement                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 功能: 驗證並補全 Blueprint                                                  │
│                                                                             │
│ 驗證項目:                                                                   │
│   - JSON 結構完整性                                                          │
│   - slide_type 有效性                                                       │
│   - 必要欄位存在 (title, bullets 等)                                        │
│                                                                             │
│ 補全項目:                                                                   │
│   - 根據 slide_type 填入預設 layout_index                                   │
│   - 根據 slide_type 填入預設 text_layout                                    │
│   - 對 images 填入預設 position (基於 layout_type)                          │
│                                                                             │
│ 輸出: Validated Blueprint JSON                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 5: Image Acquisition                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 功能: 取得圖片並更新 Blueprint                                              │
│                                                                             │
│ 對每個 images[].search_query:                                               │
│   1. 檢查快取 (ImageCacheService)                                           │
│   2. 若無快取 → 呼叫 Pexels API 搜尋                                        │
│   3. 下載圖片到本地 (data/image_cache/)                                     │
│   4. 更新 Blueprint:                                                        │
│      - images[].url = pexels_url                                            │
│      - images[].file_path = local_path                                      │
│                                                                             │
│ 輸出: Blueprint JSON (含圖片 URL/path)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 6: PPTX Construction                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 功能: 按 Blueprint 建構 PPTX                                                │
│                                                                             │
│ for slide in blueprint.slides:                                              │
│   1. 選擇 layout:                                                           │
│      layout = prs.slide_layouts[slide.layout_index]                         │
│                                                                             │
│   2. 新增 slide:                                                            │
│      slide = prs.slides.add_slide(layout)                                   │
│                                                                             │
│   3. 填入文字:                                                               │
│      - 找到對應的 placeholder (by idx or type)                              │
│      - 設定 font_size, alignment                                            │
│      - 填入 title, bullets, subtitle                                        │
│                                                                             │
│   4. 放置圖片:                                                               │
│      for img in slide.images:                                               │
│        pos = img.position                                                   │
│        slide.shapes.add_picture(                                            │
│          img.file_path,                                                     │
│          Inches(pos.x), Inches(pos.y),                                      │
│          Inches(pos.w), Inches(pos.h)                                       │
│        )                                                                    │
│                                                                             │
│ 輸出: PPTX bytes                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                             PPTX File
```

---

## 5. LLM Prompt 設計

### 5.1 Blueprint Generation Prompt

```python
BLUEPRINT_GENERATION_SYSTEM = """
你是專業的簡報設計師。請根據使用者輸入，生成一份完整的 PPTX Blueprint JSON。

## 簡報結構規則 (必須遵守)

1. **第 1 頁**: slide_type = "title"
   - 必須有 title 和 subtitle

2. **第 2 頁**: slide_type = "outline"
   - 必須列出所有主要主題 (作為 bullets)

3. **中間頁**: 根據內容選擇
   - "section": 章節標題，用於主題轉換
   - "content": 純文字內容頁
   - "content_image": 文字 + 圖片，用於重要概念或需要視覺化的內容

4. **最後 1 頁**: slide_type = "closing"
   - 總結或感謝頁

## slide_type 選項

| type | 用途 | 必要欄位 |
|------|------|----------|
| title | 標題頁 | title, subtitle |
| outline | 大綱頁 | title, bullets |
| section | 章節標題 | title, subtitle |
| content | 純文字 | title, bullets |
| content_image | 文字+圖 | title, bullets, images |
| closing | 結尾頁 | title, subtitle |

## 圖片規則

- 只有 slide_type = "content_image" 才需要 images
- 每張圖片必須提供 search_query (英文，適合 Pexels 搜尋)
- position.layout_type 可選: "right" (預設), "left", "top", "bottom"

## 內容規則

- bullets: 每個要點不超過 15 個中文字
- 每頁最多 5 個 bullets
- speaker_notes: 講者備註，可選

## 輸出格式

只輸出 JSON，不要加任何解釋。結構如下:

{
  "metadata": {
    "title": "簡報標題",
    "language": "zh-TW"
  },
  "slides": [
    {
      "index": 0,
      "slide_type": "title",
      "content": {
        "title": "...",
        "subtitle": "..."
      },
      "images": []
    },
    {
      "index": 1,
      "slide_type": "outline",
      "content": {
        "title": "今日大綱",
        "bullets": ["主題1", "主題2", ...]
      },
      "images": []
    },
    {
      "index": 2,
      "slide_type": "content_image",
      "content": {
        "title": "...",
        "bullets": ["...", "..."]
      },
      "images": [
        {
          "search_query": "english keywords for pexels",
          "position": {"layout_type": "right"}
        }
      ]
    },
    ...
  ]
}
"""

BLUEPRINT_GENERATION_USER = """
## 輸入資訊
- 使用者輸入: {user_input}
- 目標投影片數量: {slide_count}
- 語言: {language}

請生成完整的 Blueprint JSON。
"""
```

---

## 6. 核心模組設計

### 6.1 資料模型 (Pydantic)

```python
# backend/app/pptagent_core/models/blueprint.py

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SlideType(str, Enum):
    TITLE = "title"
    OUTLINE = "outline"
    SECTION = "section"
    CONTENT = "content"
    CONTENT_IMAGE = "content_image"
    FULL_IMAGE = "full_image"
    TWO_COLUMN = "two_column"
    CLOSING = "closing"


class ImageLayoutType(str, Enum):
    RIGHT = "right"
    LEFT = "left"
    TOP = "top"
    BOTTOM = "bottom"
    BACKGROUND = "background"
    CUSTOM = "custom"


class ImagePosition(BaseModel):
    layout_type: ImageLayoutType = ImageLayoutType.RIGHT
    x: float = 6.2
    y: float = 1.5
    w: float = 3.5
    h: float = 4.5
    object_fit: str = "cover"


class SlideImage(BaseModel):
    image_id: Optional[str] = None
    search_query: str
    alt_text: Optional[str] = None
    source: str = "pexels"
    url: Optional[str] = None
    file_path: Optional[str] = None
    position: ImagePosition = Field(default_factory=ImagePosition)


class TextLayoutItem(BaseModel):
    placeholder_idx: Optional[int] = None
    font_size: int = 24
    font_bold: bool = False
    alignment: str = "left"
    bullet_style: Optional[str] = None
    line_spacing: float = 1.2


class SlideContent(BaseModel):
    title: str
    subtitle: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)
    speaker_notes: Optional[str] = None
    left_content: Optional[list[str]] = None
    right_content: Optional[list[str]] = None


class SlideBlueprint(BaseModel):
    index: int
    slide_type: SlideType
    layout_index: Optional[int] = None
    layout_name: Optional[str] = None
    content: SlideContent
    text_layout: dict[str, TextLayoutItem] = Field(default_factory=dict)
    images: list[SlideImage] = Field(default_factory=list)


class BlueprintMetadata(BaseModel):
    title: str
    author: str = "TeacherAssist V2"
    language: str = "zh-TW"
    created_at: Optional[str] = None
    template: str = "education_minimal.pptx"


class BlueprintStructure(BaseModel):
    total_slides: int
    has_outline: bool = True
    section_count: int = 0
    image_slides_count: int = 0


class PresentationBlueprint(BaseModel):
    """完整的簡報藍圖"""
    metadata: BlueprintMetadata
    structure: BlueprintStructure
    slides: list[SlideBlueprint]
```

### 6.2 Blueprint Generator

```python
# backend/app/pptagent_core/roles/blueprint_generator.py

class BlueprintGenerator:
    """Stage 3: 使用 LLM 生成 Blueprint JSON"""
    
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
    
    async def generate(
        self,
        user_input: str,
        slide_count: int = 10,
        language: str = "zh-TW",
        input_mode: InputMode = InputMode.DIRECT,
    ) -> PresentationBlueprint:
        """生成完整的 Blueprint"""
        
        # 建立 prompt
        prompt = BLUEPRINT_GENERATION_USER.format(
            user_input=user_input,
            slide_count=slide_count,
            language=language,
        )
        
        # 呼叫 LLM
        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=BLUEPRINT_GENERATION_SYSTEM,
            temperature=0.3,
            max_tokens=8000,
        )
        
        # 解析 JSON
        blueprint_dict = self._parse_json(response.content)
        
        # 轉換為 Pydantic model
        blueprint = PresentationBlueprint(**blueprint_dict)
        
        return blueprint
```

### 6.3 Blueprint Validator

```python
# backend/app/pptagent_core/roles/blueprint_validator.py

class BlueprintValidator:
    """Stage 4: 驗證並補全 Blueprint"""
    
    # slide_type → layout_index 映射
    DEFAULT_LAYOUT_MAP = {
        SlideType.TITLE: 1,
        SlideType.OUTLINE: 2,
        SlideType.SECTION: 3,
        SlideType.CONTENT: 2,
        SlideType.CONTENT_IMAGE: 9,
        SlideType.FULL_IMAGE: 12,
        SlideType.CLOSING: 1,
    }
    
    def validate_and_enhance(
        self,
        blueprint: PresentationBlueprint,
        template_info: TemplateInfo,
    ) -> PresentationBlueprint:
        """驗證並補全 Blueprint"""
        
        for slide in blueprint.slides:
            # 補全 layout_index
            if slide.layout_index is None:
                slide.layout_index = self.DEFAULT_LAYOUT_MAP.get(
                    slide.slide_type, 2
                )
            
            # 補全 image position
            for image in slide.images:
                if image.position.layout_type and not image.position.x:
                    template = IMAGE_POSITION_TEMPLATES.get(
                        image.position.layout_type.value
                    )
                    if template:
                        image.position = ImagePosition(**template)
        
        # 更新 structure
        blueprint.structure.total_slides = len(blueprint.slides)
        blueprint.structure.image_slides_count = sum(
            1 for s in blueprint.slides if s.images
        )
        
        return blueprint
```

### 6.4 Blueprint PPTX Builder

```python
# backend/app/pptagent_core/roles/blueprint_builder.py

class BlueprintPPTXBuilder:
    """Stage 6: 根據 Blueprint 建構 PPTX"""
    
    def __init__(self, template_path: Path):
        self.template_path = template_path
    
    def build(self, blueprint: PresentationBlueprint) -> bytes:
        """從 Blueprint 建構 PPTX"""
        
        prs = Presentation(str(self.template_path))
        self._clear_slides(prs)
        
        for slide_bp in blueprint.slides:
            self._build_slide(prs, slide_bp)
        
        return self._save_to_bytes(prs)
    
    def _build_slide(self, prs, slide_bp: SlideBlueprint):
        """建構單張投影片"""
        
        # 選擇 layout
        layout = prs.slide_layouts[slide_bp.layout_index]
        slide = prs.slides.add_slide(layout)
        
        # 填入文字
        self._fill_content(slide, slide_bp)
        
        # 放置圖片
        self._place_images(slide, slide_bp)
    
    def _fill_content(self, slide, slide_bp: SlideBlueprint):
        """填入文字內容"""
        content = slide_bp.content
        
        # Title
        if slide.shapes.title and content.title:
            slide.shapes.title.text = content.title
        
        # Subtitle
        if content.subtitle:
            for shape in slide.shapes:
                if shape.is_placeholder:
                    if shape.placeholder_format.type == PP_PLACEHOLDER.SUBTITLE:
                        shape.text = content.subtitle
                        break
        
        # Bullets
        if content.bullets:
            for shape in slide.shapes:
                if shape.is_placeholder:
                    ph_type = shape.placeholder_format.type
                    if ph_type in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT):
                        self._fill_bullets(shape, content.bullets)
                        break
    
    def _fill_bullets(self, shape, bullets: list[str]):
        """填入 bullet points"""
        tf = shape.text_frame
        tf.clear()
        
        for i, bullet in enumerate(bullets):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.text = bullet
            p.level = 0
    
    def _place_images(self, slide, slide_bp: SlideBlueprint):
        """放置圖片"""
        for img in slide_bp.images:
            if not img.file_path or not Path(img.file_path).exists():
                continue
            
            pos = img.position
            slide.shapes.add_picture(
                str(img.file_path),
                Inches(pos.x),
                Inches(pos.y),
                Inches(pos.w),
                Inches(pos.h),
            )
```

---

## 7. 實作計畫

### Phase 1: Core Blueprint (Week 1)

| 任務 | 優先級 | 預估工作量 |
|------|--------|------------|
| 定義 Blueprint Pydantic models | P0 | 2h |
| 實作 BlueprintGenerator | P0 | 4h |
| 實作 BlueprintValidator | P0 | 2h |
| 單元測試 | P0 | 2h |

### Phase 2: Image Integration (Week 1-2)

| 任務 | 優先級 | 預估工作量 |
|------|--------|------------|
| 重構 ImageAcquisitionService | P0 | 3h |
| 整合到 Blueprint 流程 | P0 | 2h |
| 測試 Pexels API 連通性 | P1 | 1h |

### Phase 3: PPTX Builder (Week 2)

| 任務 | 優先級 | 預估工作量 |
|------|--------|------------|
| 實作 BlueprintPPTXBuilder | P0 | 4h |
| 整合測試 (完整流程) | P0 | 3h |
| 效能優化 | P1 | 2h |

### Phase 4: Refinement (Week 2-3)

| 任務 | 優先級 | 預估工作量 |
|------|--------|------------|
| 改進 LLM Prompt | P1 | 2h |
| 增加更多 slide_type | P2 | 2h |
| 文件更新 | P1 | 1h |

---

## 8. 驗收標準

### 8.1 功能驗收

```
輸入: "機器學習概述"
預期輸出: 10 張投影片的 PPTX

檢查項目:
✅ Slide 1: Title Slide (Layout 1) - 有 title + subtitle
✅ Slide 2: Outline (Layout 2) - 有大綱 bullet list
✅ Slide 3: Section Header (Layout 3)
✅ Slide 4-7: Content 或 Content+Image
✅ Slide 8: Section Header (Layout 3)
✅ Slide 9: Content (Layout 2)
✅ Slide 10: Closing (Layout 1)

圖片檢查:
✅ content_image slides 有圖片
✅ 圖片位置符合 position 設定
✅ 圖片來源為 Pexels
```

### 8.2 Blueprint JSON 驗收

```json
// Blueprint 必須包含:
{
  "metadata": { "title": "...", "language": "zh-TW" },
  "structure": { "total_slides": 10, "has_outline": true },
  "slides": [
    // 第 1 頁必須是 title
    { "index": 0, "slide_type": "title", ... },
    // 第 2 頁必須是 outline
    { "index": 1, "slide_type": "outline", ... },
    // 最後 1 頁必須是 closing
    { "index": 9, "slide_type": "closing", ... }
  ]
}
```

---

## 9. 附錄

### A. education_minimal.pptx Layout 對照表

| Layout Index | Layout Name | Placeholders | 建議用途 |
|--------------|-------------|--------------|----------|
| 0 | Blank Slide | [] | 純圖片頁 |
| 1 | Title Slide | [TITLE, SUBTITLE] | title, closing |
| 2 | Title, Content | [TITLE, OBJECT] | outline, content |
| 3 | Section Header | [TITLE, SUBTITLE] | section |
| 4 | Two Content | [TITLE, OBJECT, OBJECT] | two_column |
| 9 | Title, Content, Picture | [TITLE, OBJECT, PICTURE] | content_image |
| 12 | Full Image | [PICTURE] | full_image |

### B. 相關檔案路徑

```
backend/
├── app/
│   ├── pptagent_core/
│   │   ├── models/
│   │   │   └── blueprint.py          # Blueprint Pydantic models
│   │   └── roles/
│   │       ├── blueprint_generator.py # Stage 3
│   │       ├── blueprint_validator.py # Stage 4
│   │       └── blueprint_builder.py   # Stage 6
│   └── services/
│       └── ppt_service_v3.py          # 新版主服務
├── data/
│   └── templates/
│       └── education_minimal.pptx
└── tests/
    └── test_blueprint_pipeline.py
```

---

**文件結束**

*Generated by Claude Code /sc:analyze + /sc:document on 2026-01-29*
