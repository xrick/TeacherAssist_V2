# PPTX Blueprint Architecture V2

## 完整參考專案分析總結

### 1. PPTX-Presentation-Generator (Python)

**核心設計**：
- LLM 用 **Tag-based** 輸出：`[L_TS]`, `[L_CS]`, `[L_IS]`, `[L_THS]`
- 每個 Tag 直接映射到 `pptx.slide_layouts[index]`
- 圖片：`[IMAGE]query[/IMAGE]` tag 觸發 icrawler 搜尋
- 圖片位置：使用 placeholder 的 left/top/width/height

```python
# Tag → Layout 映射
[L_TS]  → slide_layouts[0]  # Title Slide
[L_CS]  → slide_layouts[1]  # Content Slide  
[L_IS]  → slide_layouts[8]  # Image Slide (Pic with caption)
[L_THS] → slide_layouts[2]  # Section Header
```

**優點**：
- Tag 明確，解析簡單
- Layout 映射清晰

**缺點**：
- Tag 格式對 LLM 輸出不夠友好
- 圖片搜尋用 icrawler (爬蟲)，不夠穩定

---

### 2. presentation-ai-main (TypeScript)

**核心設計**：
- LLM 輸出 **XML 格式**：`<SECTION>`, `<H1>`, `<P>`, `<IMG query="...">`
- 使用 Plate.js 作為中間表示層 (Rich Text Editor AST)
- 使用 PptxGenJS (非 python-pptx) 輸出
- 支援複雜視覺元素：Pyramid, Timeline, Cycle, Arrows, etc.

**Slide 結構**：
```typescript
type PlateSlide = {
  id: string;
  content: PlateNode[];          // 內容節點陣列
  rootImage?: {                  // 背景/裝飾圖片
    query: string;
    url?: string;
    layoutType?: "left" | "right" | "vertical" | "background";
  };
  layoutType?: LayoutType;       // 圖片佈局類型
  alignment?: "start" | "center" | "end";
  bgColor?: string;
};
```

**圖片處理**：
- `rootImage` 可指定 layoutType（left/right/vertical/background）
- 圖片位置根據 layoutType 動態計算
- 支援 objectFit (cover/contain/fill)

**優點**：
- 結構化程度高
- 支援豐富的視覺元素
- 圖片位置靈活

**缺點**：
- TypeScript/React 生態，不適合直接移植
- 使用 PptxGenJS 而非 python-pptx

---

### 3. GenSlide-main (Python)

**核心設計**：
- LLM 直接輸出 **JSON 陣列**
- 極簡結構：title_text, text[], img_path[]

**JSON 結構**：
```json
[
  {"id": 1, "title_text": "Title", "subtitle_text": "Subtitle", "is_title_slide": "yes"},
  {"id": 2, "title_text": "Slide 1", "text": ["Bullet 1", "Bullet 2"]},
  {"id": 3, "title_text": "Slide 2", "text": ["Bullet 1"], "img_path": ["path/to/img.jpg"]}
]
```

**優點**：
- 結構簡單，LLM 容易生成
- 直接用 JSON，解析無風險

**缺點**：
- 功能太簡單，只有 title + bullets
- 圖片位置硬編碼
- 沒有 layout type 概念

---

## JSON Blueprint 設計 (整合三者優點)

### 設計原則

1. **Blueprint First**：先生成完整 JSON 藍圖，再按圖施工
2. **Layout 明確**：每頁都有明確的 layout_type
3. **圖片位置可控**：每張圖片都有 position 設定
4. **結構完整**：支援 outline, section header, content, image 等

### Blueprint JSON Schema

```json
{
  "$schema": "PPTX Blueprint v2.0",
  
  "metadata": {
    "title": "簡報主標題",
    "author": "TeacherAssist V2",
    "language": "zh-TW",
    "created_at": "2026-01-29T12:00:00Z",
    "template": "education_minimal.pptx",
    "theme_colors": {
      "primary": "#3B82F6",
      "secondary": "#1F2937",
      "accent": "#60A5FA",
      "background": "#FFFFFF",
      "text": "#1F2937"
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
        "speaker_notes": "歡迎各位，今天我們來探討機器學習..."
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
        ],
        "speaker_notes": "首先讓我們看看今天要討論的主題..."
      },
      
      "text_layout": {
        "title": {
          "placeholder_idx": 0,
          "font_size": 36,
          "position": {"x": 0.5, "y": 0.5, "w": 9.0, "h": 1.0}
        },
        "body": {
          "placeholder_idx": 10,
          "font_size": 24,
          "bullet_style": "numbered",
          "line_spacing": 1.5,
          "position": {"x": 0.5, "y": 1.8, "w": 9.0, "h": 4.5}
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
      
      "text_layout": {
        "title": {
          "placeholder_idx": 0,
          "font_size": 48,
          "alignment": "center"
        }
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
        "speaker_notes": "機器學習是AI的核心技術之一..."
      },
      
      "text_layout": {
        "title": {
          "placeholder_idx": 0,
          "font_size": 32,
          "position": {"x": 0.5, "y": 0.5, "w": 5.5, "h": 1.0}
        },
        "body": {
          "placeholder_idx": 10,
          "font_size": 20,
          "bullet_style": "bullet",
          "position": {"x": 0.5, "y": 1.8, "w": 5.5, "h": 4.5}
        }
      },
      
      "images": [
        {
          "image_id": "img_001",
          "search_query": "artificial intelligence neural network",
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
      "index": 4,
      "slide_type": "content",
      "layout_index": 2,
      "layout_name": "Title and Content",
      
      "content": {
        "title": "監督式學習",
        "bullets": [
          "提供標註好的訓練資料",
          "學習輸入到輸出的映射",
          "常見任務：分類、迴歸"
        ],
        "speaker_notes": "監督式學習是最常見的機器學習類型..."
      },
      
      "text_layout": {
        "title": {
          "placeholder_idx": 0,
          "font_size": 32
        },
        "body": {
          "placeholder_idx": 10,
          "font_size": 24,
          "bullet_style": "bullet"
        }
      },
      
      "images": []
    },
    
    {
      "index": 9,
      "slide_type": "closing",
      "layout_index": 1,
      "layout_name": "Title Slide",
      
      "content": {
        "title": "總結",
        "subtitle": "機器學習正在改變世界",
        "speaker_notes": "感謝各位的聆聽..."
      },
      
      "text_layout": {
        "title": {
          "placeholder_idx": 0,
          "font_size": 44,
          "alignment": "center"
        },
        "subtitle": {
          "placeholder_idx": 1,
          "font_size": 24,
          "alignment": "center"
        }
      },
      
      "images": []
    }
  ]
}
```

---

## Slide Types 定義

| slide_type | 說明 | 必要欄位 | 可選欄位 |
|------------|------|----------|----------|
| `title` | 標題頁 | title, subtitle | speaker_notes |
| `outline` | 大綱頁 | title, bullets | speaker_notes |
| `section` | 章節標題 | title | subtitle |
| `content` | 純文字內容頁 | title, bullets | speaker_notes |
| `content_image` | 文字+圖片頁 | title, bullets, images | speaker_notes |
| `full_image` | 全版圖片頁 | images | title, caption |
| `two_column` | 雙欄佈局 | title, left_content, right_content | images |
| `closing` | 結尾頁 | title | subtitle, speaker_notes |

---

## Image Position 策略

### Position 類型

```json
{
  "position": {
    "layout_type": "right",      // right | left | top | bottom | background | custom
    "x": 6.2,                    // 左邊距 (inches)
    "y": 1.5,                    // 上邊距 (inches)
    "w": 3.5,                    // 寬度 (inches)
    "h": 4.5,                    // 高度 (inches)
    "object_fit": "cover",       // cover | contain | fill
    "z_order": "back"            // back | front (背景圖或前景圖)
  }
}
```

### 預設 Position Templates

```python
IMAGE_POSITION_TEMPLATES = {
    "right": {"x": 6.2, "y": 1.5, "w": 3.5, "h": 4.5},
    "left": {"x": 0.3, "y": 1.5, "w": 3.5, "h": 4.5},
    "top": {"x": 2.5, "y": 0.5, "w": 5.0, "h": 2.5},
    "bottom": {"x": 2.5, "y": 4.0, "w": 5.0, "h": 2.5},
    "background": {"x": 0, "y": 0, "w": 10.0, "h": 5.625},
    "small_right": {"x": 7.0, "y": 3.5, "w": 2.5, "h": 2.0},
}
```

---

## 完整生成流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PPTX Blueprint Pipeline                             │
└─────────────────────────────────────────────────────────────────────────────┘

                              User Input
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 1: Input Classification                                               │
│                                                                             │
│ 判斷輸入類型：                                                               │
│   - SHORT_TOPIC: 短題目 → 需要 LLM 生成完整內容                              │
│   - LONG_ARTICLE: 長文章 → 需要 LLM 結構化/摘要                              │
│                                                                             │
│ 輸出: InputMode                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 2: Template Analysis                                                  │
│                                                                             │
│ 分析 PPTX Template:                                                         │
│   - 掃描所有 slide_layouts                                                   │
│   - 建立 slide_type → layout_index 映射表                                    │
│   - 記錄每個 layout 的 placeholder 位置/尺寸                                 │
│                                                                             │
│ 輸出: TemplateInfo { layouts: [...], type_mapping: {...} }                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 3: Blueprint Generation (LLM)                                         │
│                                                                             │
│ LLM 生成完整 Blueprint JSON:                                                │
│   - 決定 slide 數量和類型序列                                                │
│   - 生成每頁的 title, bullets, speaker_notes                                │
│   - 決定哪些頁需要圖片 (slide_type = content_image)                         │
│   - 生成圖片搜尋關鍵字 (search_query)                                        │
│                                                                             │
│ Prompt 策略:                                                                │
│   - 強制結構: title → outline → sections → content → closing                │
│   - 明確 slide_type 選項                                                    │
│   - 輸出必須是完整的 JSON                                                    │
│                                                                             │
│ 輸出: Blueprint JSON (不含圖片 URL/path)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 4: Blueprint Validation & Enhancement                                 │
│                                                                             │
│ 驗證 Blueprint:                                                             │
│   - 檢查 JSON 結構完整性                                                     │
│   - 確認 slide_type 有效                                                    │
│   - 補全缺失的 text_layout 和 position                                      │
│                                                                             │
│ 增強:                                                                       │
│   - 根據 slide_type 填入預設 layout_index                                   │
│   - 根據 slide_type 填入預設 image position                                 │
│   - 計算 text_layout 的 position (如果未指定)                               │
│                                                                             │
│ 輸出: Validated Blueprint JSON                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 5: Image Acquisition                                                  │
│                                                                             │
│ 對每個 images[].search_query:                                               │
│   1. 檢查快取 (ImageCacheService)                                           │
│   2. 若無快取 → 呼叫 Pexels API 搜尋                                        │
│   3. 下載圖片到本地                                                          │
│   4. 更新 Blueprint: images[].url, images[].file_path                       │
│                                                                             │
│ 輸出: Blueprint JSON (含圖片 URL/path)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage 6: PPTX Construction                                                  │
│                                                                             │
│ 按 Blueprint 建構 PPTX:                                                     │
│                                                                             │
│ for slide in blueprint.slides:                                              │
│   1. 選擇 layout: prs.slide_layouts[slide.layout_index]                     │
│   2. 新增 slide: prs.slides.add_slide(layout)                               │
│   3. 填入文字:                                                               │
│      - 使用 text_layout.position 定位                                       │
│      - 套用 font_size, alignment, bullet_style                              │
│   4. 放置圖片:                                                               │
│      - 使用 images[].position 定位                                          │
│      - 套用 object_fit                                                      │
│                                                                             │
│ 輸出: PPTX bytes                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                             PPTX File
```

---

## Stage 3: Blueprint Generation Prompt

```python
BLUEPRINT_GENERATION_PROMPT = """
你是專業的簡報設計師。請根據使用者輸入，生成一份完整的 PPTX Blueprint JSON。

## 輸入資訊
- 使用者輸入: {user_input}
- 目標投影片數量: {slide_count}
- 語言: {language}

## 必須遵守的簡報結構
1. **第 1 頁**: slide_type = "title" (標題頁)
2. **第 2 頁**: slide_type = "outline" (大綱頁，列出主要主題)
3. **中間頁**: 依內容選擇:
   - "section" - 章節標題 (每個主題開始前)
   - "content" - 純文字內容
   - "content_image" - 文字 + 圖片 (重要概念/視覺化需求)
4. **最後 1 頁**: slide_type = "closing" (總結/感謝)

## slide_type 選項
- title: 標題頁，需要 title + subtitle
- outline: 大綱頁，需要 title + bullets (列出所有主題)
- section: 章節標題，需要 title + subtitle
- content: 純文字，需要 title + bullets
- content_image: 文字+圖片，需要 title + bullets + images
- closing: 結尾頁，需要 title + subtitle

## 圖片規則
- 只有 slide_type = "content_image" 才需要 images
- 每張圖片必須提供 search_query (英文，適合 Pexels 搜尋)
- position.layout_type 可選: "right" (預設), "left", "top", "bottom"

## 輸出格式
請輸出完整的 JSON，結構如下:

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
        "subtitle": "...",
        "speaker_notes": "..."
      },
      "images": []
    },
    ...
  ]
}

只輸出 JSON，不要加任何解釋。
"""
```

---

## Stage 6: PPTX Builder 實現

```python
class BlueprintPPTXBuilder:
    """根據 Blueprint JSON 建構 PPTX"""
    
    # Slide Type → Layout Index 預設映射
    SLIDE_TYPE_LAYOUT_MAP = {
        "title": 1,        # Title Slide
        "outline": 2,      # Title and Content
        "section": 3,      # Section Header
        "content": 2,      # Title and Content
        "content_image": 9, # Title, Content and Picture (如果有)
        "full_image": 12,  # Full Image (如果有)
        "closing": 1,      # Title Slide
    }
    
    # Image Position 預設模板
    IMAGE_POSITION_TEMPLATES = {
        "right": {"x": 6.2, "y": 1.5, "w": 3.5, "h": 4.5},
        "left": {"x": 0.3, "y": 1.5, "w": 3.5, "h": 4.5},
        "top": {"x": 2.5, "y": 0.5, "w": 5.0, "h": 2.5},
        "bottom": {"x": 2.5, "y": 4.0, "w": 5.0, "h": 2.5},
        "background": {"x": 0, "y": 0, "w": 10.0, "h": 5.625},
    }
    
    def __init__(self, template_path: Path):
        self.template_path = template_path
        self.prs = None
    
    def build(self, blueprint: dict) -> bytes:
        """從 Blueprint 建構 PPTX"""
        self.prs = Presentation(str(self.template_path))
        self._clear_slides()
        
        for slide_data in blueprint.get("slides", []):
            self._build_slide(slide_data)
        
        return self._save_to_bytes()
    
    def _build_slide(self, slide_data: dict):
        """建構單張投影片"""
        slide_type = slide_data.get("slide_type", "content")
        layout_index = slide_data.get("layout_index") or self.SLIDE_TYPE_LAYOUT_MAP.get(slide_type, 2)
        
        layout = self.prs.slide_layouts[layout_index]
        slide = self.prs.slides.add_slide(layout)
        
        # 填入文字
        self._fill_text_content(slide, slide_data)
        
        # 放置圖片
        self._place_images(slide, slide_data)
    
    def _fill_text_content(self, slide, slide_data: dict):
        """填入文字內容"""
        content = slide_data.get("content", {})
        text_layout = slide_data.get("text_layout", {})
        
        # Title
        if "title" in content and slide.shapes.title:
            slide.shapes.title.text = content["title"]
        
        # Body/Bullets
        if "bullets" in content:
            for shape in slide.shapes:
                if shape.is_placeholder:
                    ph_type = shape.placeholder_format.type
                    if ph_type in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT):
                        self._fill_bullets(shape, content["bullets"])
                        break
        
        # Subtitle
        if "subtitle" in content:
            for shape in slide.shapes:
                if shape.is_placeholder:
                    ph_type = shape.placeholder_format.type
                    if ph_type == PP_PLACEHOLDER.SUBTITLE:
                        shape.text = content["subtitle"]
                        break
    
    def _fill_bullets(self, shape, bullets: list):
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
    
    def _place_images(self, slide, slide_data: dict):
        """放置圖片"""
        images = slide_data.get("images", [])
        
        for img_data in images:
            file_path = img_data.get("file_path")
            if not file_path or not Path(file_path).exists():
                continue
            
            position = img_data.get("position", {})
            layout_type = position.get("layout_type", "right")
            
            # 取得位置參數
            if layout_type in self.IMAGE_POSITION_TEMPLATES:
                pos = self.IMAGE_POSITION_TEMPLATES[layout_type].copy()
            else:
                pos = position
            
            # 覆蓋自訂值
            x = Inches(position.get("x", pos.get("x", 6.2)))
            y = Inches(position.get("y", pos.get("y", 1.5)))
            w = Inches(position.get("w", pos.get("w", 3.5)))
            h = Inches(position.get("h", pos.get("h", 4.5)))
            
            slide.shapes.add_picture(str(file_path), x, y, w, h)
```

---

## 優勢總結

### vs 當前系統
| 問題 | 當前系統 | Blueprint 架構 |
|------|----------|----------------|
| Layout 選擇 | 固定 2 種 | 由 slide_type 決定 |
| 圖片位置 | 硬編碼或 PICTURE placeholder | 每張圖有獨立 position |
| 結構控制 | LLM 自由發揮 | 強制 title→outline→content→closing |
| 可追蹤性 | 只有最終輸出 | 完整 Blueprint JSON 可審核 |

### Blueprint 優點
1. **可審核**：生成後可以檢視 JSON，確認結構正確再建構
2. **可修改**：可以在建構前手動調整 Blueprint
3. **可重用**：相同 Blueprint 可以套用不同 Template
4. **可測試**：每個 Stage 可以獨立測試

---

## 實作優先順序

### Phase 1: Core Blueprint
1. 定義 Blueprint JSON Schema (Pydantic models)
2. 實作 BlueprintGenerator (LLM 生成)
3. 實作 BlueprintValidator (驗證和補全)

### Phase 2: Image Integration
4. 實作 ImageAcquisitionService (Pexels + 快取)
5. 更新 Blueprint 加入圖片路徑

### Phase 3: PPTX Builder
6. 實作 BlueprintPPTXBuilder
7. 整合測試

### Phase 4: Optimization
8. 改進 LLM Prompt
9. 增加更多 slide_type
10. 支援更複雜的佈局

---

*Generated by /sc:analyze on 2026-01-29*
