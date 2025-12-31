<!-- claudedocs/FEATURE_SCRIPT_GENERATION.md -->
<!-- markdownlint-disable MD013 -->
# Feature: 講稿生成功能 (Script Generation)

> **狀態**: 需求規格 (Brainstorming Output)
> **日期**: 2025-12-31

---

## 需求摘要

為 TeacherAssist 加入**講稿自動生成**功能，在生成簡報的同時產生完整的演講逐字稿，並支援多格式匯出。

### 核心需求

| 項目 | 決策 |
|------|------|
| 內容形式 | 逐字稿 (完整演講內容，可直接照讀) |
| 輸出方式 | 獨立文件匯出 |
| 額外資訊 | 時間提示 + 互動提示 + 轉場提示 |
| UI 整合 | 整合在現有生成流程 |
| 匯出格式 | 多格式支援 (Markdown / Word / PDF) |
| 語調風格 | 跟隨簡報的 audience/tone 設定 |
| 時長估算 | 系統自動估算並分配到各投影片 |

---

## 功能規格

### 1. 講稿內容結構

每張投影片對應的講稿區塊應包含：

```markdown
## [投影片標題]

⏱️ 建議時長：2 分鐘

---

[逐字稿內容]

這張投影片我們要探討的是 [主題]。首先讓我們看看...

💡 **互動提示**：此處可以詢問聽眾是否有相關經驗

---

🔄 **轉場**：接下來，讓我們看看下一個重點...

---
```

### 2. 講稿元素定義

| 元素 | 符號 | 說明 |
|------|------|------|
| 時間提示 | ⏱️ | 該段落建議演講時長 |
| 互動提示 | 💡 | 建議與聽眾互動的時機和方式 |
| 轉場提示 | 🔄 | 投影片切換時的銜接語 |
| 強調標記 | **粗體** | 需要強調的關鍵詞 |
| 停頓標記 | `[pause]` | 建議停頓的位置 |

### 3. 時間估算邏輯

```text
總演講時長 = Σ(每張投影片時長)

每張投影片時長估算：
- 標題投影片：30 秒
- 內容投影片：1.5-3 分鐘 (依內容量)
- 區段標題：20 秒
- 結尾投影片：1 分鐘

估算公式：
時長(秒) = 基礎時長 + (字數 × 0.1) + (互動次數 × 30)
```

---

## 系統架構設計

### Pipeline 擴展

在現有 5-Stage Pipeline 後新增 Stage 6：

```text
┌──────────────┐    ┌───────────────┐    ┌────────────────┐
│   Stage 5    │ →  │   Stage 6     │ →  │    Output      │
│    Coder     │    │ScriptGenerator│    │   Builder      │
└──────────────┘    └───────────────┘    └────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Script Document     │
              │  (.md / .docx / .pdf)│
              └──────────────────────┘
```

### 新增 Role: ScriptGenerator

**檔案**: `backend/app/pptagent_core/roles/script_generator.py`

```python
class ScriptGenerator:
    """
    生成演講逐字稿

    這是 PPTAgent Pipeline 的第六階段。它：
    - 根據簡報內容生成完整逐字稿
    - 添加時間估算和分配
    - 插入互動和轉場提示
    - 依據 audience/tone 調整語調
    """

    async def generate(
        self,
        presentation: Presentation,
        total_duration_minutes: int | None = None,  # 可選：指定總時長
        audience: str | None = None,
        tone: str | None = None,
    ) -> Script:
        """生成講稿"""
        pass
```

### 新增 Data Models

**檔案**: `backend/app/pptagent_core/presentation/models.py`

```python
class ScriptSegment(BaseModel):
    """單張投影片的講稿"""
    slide_index: int
    slide_title: str
    content: str                    # 逐字稿內容
    duration_seconds: int           # 建議時長
    interaction_hints: list[str]    # 互動提示
    transition_text: str | None     # 轉場語

class Script(BaseModel):
    """完整講稿"""
    metadata: ScriptMetadata
    segments: list[ScriptSegment]
    total_duration_seconds: int

    def to_markdown(self) -> str:
        """匯出為 Markdown 格式"""
        pass

    def to_docx(self) -> bytes:
        """匯出為 Word 格式"""
        pass

    def to_pdf(self) -> bytes:
        """匯出為 PDF 格式"""
        pass

class ScriptMetadata(BaseModel):
    """講稿元資料"""
    presentation_title: str
    author: str | None
    audience: str | None
    tone: str | None
    total_duration_minutes: int
    generated_at: datetime
```

### 新增 Service: ScriptBuilder

**檔案**: `backend/app/services/script_builder.py`

```python
class ScriptBuilder:
    """
    講稿文件建構器

    將 Script model 轉換為各種格式的文件
    """

    def build_markdown(self, script: Script) -> str:
        """生成 Markdown 格式講稿"""
        pass

    def build_docx(self, script: Script) -> bytes:
        """生成 Word 格式講稿"""
        pass

    def build_pdf(self, script: Script) -> bytes:
        """生成 PDF 格式講稿"""
        pass
```

---

## API 設計

### 修改現有 Generation Response

```python
class GenerationResponse(BaseModel):
    success: bool
    message: str
    presentation_id: str
    slide_count: int
    download_url: str
    metadata: dict
    # 新增
    script_available: bool = True
    script_download_urls: dict[str, str] = {}  # {"md": "...", "docx": "...", "pdf": "..."}
    estimated_duration_minutes: int
```

### 新增 Script Endpoints

```text
GET /api/v1/presentations/{id}/script
    Query params: format=md|docx|pdf (default: md)
    Response: FileResponse

GET /api/v1/presentations/{id}/script/preview
    Response: JSON with script content preview
```

---

## UI 設計

### 1. 生成控制面板擴展

在現有 `GenerationControl.tsx` 中新增講稿選項：

```text
┌─────────────────────────────────────────────────────────────┐
│  生成選項                                                    │
├─────────────────────────────────────────────────────────────┤
│  ☑️ 生成講稿                                                 │
│     └─ 預計時長：[  15  ] 分鐘  (留空自動估算)               │
├─────────────────────────────────────────────────────────────┤
│  受眾：[  教育工作者  ▼]                                     │
│  語調：[  專業且親切  ▼]                                     │
└─────────────────────────────────────────────────────────────┘
```

### 2. 結果預覽擴展

在 `ResultPreview.tsx` 中新增講稿預覽和下載：

```text
┌─────────────────────────────────────────────────────────────┐
│  生成結果                                               ✅   │
├─────────────────────────────────────────────────────────────┤
│  📊 簡報：10 張投影片                                        │
│     [下載 PPTX]                                             │
├─────────────────────────────────────────────────────────────┤
│  📝 講稿：預計 15 分鐘                                       │
│     [下載 Markdown] [下載 Word] [下載 PDF]                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  講稿預覽                                     [展開] │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  ## 課程介紹                                         │   │
│  │  ⏱️ 建議時長：2 分鐘                                 │   │
│  │                                                      │   │
│  │  各位老師、同學大家好，今天我們要一起探討的是...     │   │
│  │  ...                                                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3. 講稿預覽模態框

新增元件 `ScriptPreview.tsx`：

```text
┌─────────────────────────────────────────────────────────────┐
│  📝 講稿預覽                                          [✕]   │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────────────┬────────────────────────────┐   │
│  │ 投影片列表              │ 講稿內容                    │   │
│  │                        │                            │   │
│  │ 1. 課程介紹 (2min) ◀   │ ## 課程介紹                │   │
│  │ 2. 學習目標 (1.5min)   │ ⏱️ 建議時長：2 分鐘        │   │
│  │ 3. 主題一 (3min)       │                            │   │
│  │ 4. 主題二 (3min)       │ 各位老師、同學大家好，     │   │
│  │ 5. 實作練習 (2min)     │ 今天我們要一起探討的是     │   │
│  │ 6. 總結 (1.5min)       │ **人工智慧在教育領域的     │   │
│  │                        │ 應用**。[pause]            │   │
│  │                        │                            │   │
│  │                        │ 💡 此處可詢問聽眾對 AI     │   │
│  │                        │    的認識程度               │   │
│  │                        │                            │   │
│  │                        │ 🔄 接下來，讓我們看看      │   │
│  │                        │    今天的學習目標...        │   │
│  └────────────────────────┴────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  總時長：15 分鐘              [複製全文] [下載 ▼]           │
└─────────────────────────────────────────────────────────────┘
```

### 4. 新增前端元件

| 元件 | 路徑 | 功能 |
|------|------|------|
| `ScriptOptions.tsx` | `components/generation/` | 講稿生成選項控制 |
| `ScriptPreview.tsx` | `components/preview/` | 講稿預覽模態框 |
| `ScriptDownload.tsx` | `components/preview/` | 講稿下載按鈕組 |

---

## SSE 進度更新

擴展 SSE 事件以包含講稿生成進度：

```javascript
// 現有進度事件
event: progress
data: {"stage": "script_generation", "progress": 90, "message": "生成講稿中..."}

// 完成事件擴展
event: complete
data: {
  "presentation_id": "...",
  "slide_count": 10,
  "download_url": "...",
  "script": {
    "available": true,
    "duration_minutes": 15,
    "download_urls": {
      "md": "/api/v1/presentations/.../script?format=md",
      "docx": "/api/v1/presentations/.../script?format=docx",
      "pdf": "/api/v1/presentations/.../script?format=pdf"
    }
  }
}
```

---

## 實作優先順序

### Phase 1: 核心功能 (MVP)

1. 新增 `ScriptGenerator` role
2. 新增 `Script` 和 `ScriptSegment` models
3. 整合到 PPTService pipeline
4. Markdown 格式匯出
5. 基本 API endpoints

### Phase 2: UI 整合

1. `ScriptOptions.tsx` 生成選項
2. `ResultPreview.tsx` 擴展
3. `ScriptPreview.tsx` 預覽模態框
4. 下載功能整合

### Phase 3: 進階功能

1. Word (.docx) 格式支援
2. PDF 格式支援
3. 講稿編輯功能 (可選)
4. 演練模式 (可選)

---

## 技術考量

### 依賴套件

```toml
# pyproject.toml 新增
dependencies = [
    # ... existing ...
    "python-docx>=0.8.11",      # Word 文件生成
    "weasyprint>=60.0",          # PDF 生成 (或使用 reportlab)
]
```

### LLM Prompt 設計要點

1. **明確指示生成逐字稿**而非要點
2. **包含語調指引**：根據 audience/tone 調整用詞
3. **結構化輸出**：使用 JSON 格式確保可解析
4. **時間意識**：提示 LLM 考慮演講節奏

### 效能考量

- 講稿生成增加約 1 次 LLM 呼叫
- 預計增加 10-15 秒生成時間
- 考慮實作快取機制避免重複生成

---

## 驗收標準

- [ ] 可生成完整逐字稿內容
- [ ] 包含時間、互動、轉場三種提示
- [ ] 支援 Markdown/Word/PDF 三種格式匯出
- [ ] UI 整合在現有生成流程中
- [ ] SSE 顯示講稿生成進度
- [ ] 講稿預覽功能正常運作

---

Generated from /sc:brainstorm session | TeacherAssist V2
