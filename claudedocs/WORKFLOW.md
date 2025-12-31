<!-- claudedocs/WORKFLOW.md -->
<!-- markdownlint-disable MD013 -->
# TeacherAssist V2 - System Workflow Documentation

## Overview

TeacherAssist 是一個 AI 驅動的簡報生成系統，將 Markdown 內容轉換為專業的 PowerPoint 簡報。
系統採用 5 階段 PPTAgent pipeline 進行內容處理，並透過 FastAPI 後端提供 RESTful API 和 SSE 串流服務。

---

## Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React + TypeScript)                   │
│  ┌───────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐  │
│  │MarkdownEditor │→ │GenerationControl │→ │    ProgressMonitor (SSE)     │  │
│  └───────────────┘  └──────────────────┘  └──────────────────────────────┘  │
│          │                   │                          │                    │
│          ▼                   ▼                          ▼                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         ResultPreview                                  │  │
│  │  (Download PPTX / View Metadata / Delete Presentation)                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP/SSE
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND API (FastAPI)                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         API Routes                                      │ │
│  │  POST /api/v1/generate/        → Synchronous generation                │ │
│  │  POST /api/v1/generate/stream  → SSE streaming generation              │ │
│  │  GET  /api/v1/presentations/{id}/download → Download PPTX              │ │
│  │  GET  /api/v1/presentations/{id}/metadata → Get metadata               │ │
│  │  DELETE /api/v1/presentations/{id}        → Delete presentation        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         PPTService                                      │ │
│  │              (Orchestrates 5-Stage PPTAgent Pipeline)                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│  ┌───────────┐ ┌───────────────────┐ │ ┌───────────────────────────────────┐│
│  │LLMService │ │PresentationStorage│ │ │       PPTXBuilder                 ││
│  │(Ollama/   │ │(File-based PPTX   │◄┼►│(Converts Model → PPTX bytes)      ││
│  │ OpenAI)   │ │ + JSON metadata)  │ │ │                                   ││
│  └───────────┘ └───────────────────┘ │ └───────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5-Stage PPTAgent Pipeline

系統核心是 **PPTAgent Pipeline**，包含 5 個處理階段，每個階段由獨立的 Role 類別實現：

```text
┌──────────────┐    ┌──────────────────┐    ┌────────────────┐    ┌────────┐    ┌────────┐
│   Stage 1    │ →  │     Stage 2      │ →  │    Stage 3     │ →  │Stage 4 │ →  │Stage 5 │
│   Schema     │    │    Content       │    │    Layout      │    │ Editor │    │ Coder  │
│  Extractor   │    │   Organizer      │    │   Selector     │    │        │    │        │
└──────────────┘    └──────────────────┘    └────────────────┘    └────────┘    └────────┘
    (0-20%)              (20-40%)               (40-60%)           (60-80%)      (80-100%)
```

### Stage 1: Schema Extractor (0-20%)

**檔案**: [schema_extractor.py](../backend/app/pptagent_core/roles/schema_extractor.py)

**功能**:

- 分析原始 Markdown 內容
- 識別簡報標題和結構
- 確定邏輯區段和投影片邊界
- 識別內容類型（文字、列表、程式碼、表格）
- 估計建議的投影片數量

**輸入**: Raw Markdown 文字
**輸出**: JSON Schema 結構

```json
{
  "title": "簡報標題",
  "sections": [
    {
      "title": "區段標題",
      "slides": []
    }
  ],
  "total_slides": 10
}
```

**LLM 參數**: temperature=0.3 (低溫度確保結構化輸出)

---

### Stage 2: Content Organizer (20-40%)

**檔案**: [content_organizer.py](../backend/app/pptagent_core/roles/content_organizer.py)

**功能**:

- 將內容均勻分配到各投影片
- 建立平衡的投影片結構
- 決定每張投影片的內容元素
- 適當添加演講者備註

**輸入**: Schema 結構
**輸出**: 組織後的投影片內容

```json
{
  "slides": [
    {
      "title": "投影片標題",
      "elements": [
        {"type": "text", "content": "..."},
        {"type": "bullet_list", "content": "項目1\n項目2\n項目3"}
      ],
      "notes": "演講者備註"
    }
  ]
}
```

**LLM 參數**: temperature=0.4, max_tokens=6000

---

### Stage 3: Layout Selector (40-60%)

**檔案**: [layout_selector.py](../backend/app/pptagent_core/roles/layout_selector.py)

**功能**:

- 分析內容類型和密度
- 為每張投影片選擇最佳版面配置
- 確保視覺多樣性和專業性

**可用版面類型**:
| Layout Type      | 用途               |
|------------------|-------------------|
| `title`          | 標題投影片         |
| `content`        | 標準內容           |
| `two_column`     | 雙欄比較           |
| `image`          | 圖片為主           |
| `image_text`     | 圖文並茂           |
| `quote`          | 引言投影片         |
| `section_header` | 區段標題           |
| `closing`        | 結尾投影片         |
| `blank`          | 空白版面           |

**LLM 參數**: temperature=0.3

---

### Stage 4: Editor (60-80%)

**檔案**: [editor.py](../backend/app/pptagent_core/roles/editor.py)

**功能**:

- 精煉標題使其簡潔有力
- 優化要點清晰度
- 確保平行結構
- 修正文法和標點
- 添加有幫助的演講者備註
- 根據目標受眾和語調調整內容

**可選參數**:

- `audience`: 目標受眾 (e.g., "professionals", "students")
- `tone`: 期望語調 (e.g., "professional", "casual")

**LLM 參數**: temperature=0.5, max_tokens=8000

---

### Stage 5: Coder (80-100%)

**檔案**: [coder.py](../backend/app/pptagent_core/roles/coder.py)

**功能**:

- 建立完整的簡報結構
- 添加格式指令
- 準備 PPTX 生成資料
- 包含所有元資料
- 將 JSON 結構轉換為 Pydantic Model

**輸出**: `Presentation` 物件 (Pydantic Model)

**LLM 參數**: temperature=0.2, max_tokens=10000 (極低溫度確保精確結構)

---

## Data Models

### Presentation Model

**檔案**: [models.py](../backend/app/pptagent_core/presentation/models.py)

```text
Presentation
├── metadata: PresentationMetadata
│   ├── title: str
│   ├── author: str | None
│   ├── topic: str | None
│   ├── audience: str | None
│   ├── duration_minutes: int | None
│   ├── template: str = "default.pptx"
│   └── tags: list[str]
│
└── slides: list[SlideContent]
    ├── title: str
    ├── elements: list[ContentElement]
    │   ├── type: ContentType (text|bullet_list|numbered_list|code_block|table|image|quote|heading)
    │   ├── content: str
    │   └── metadata: dict
    ├── notes: str | None
    ├── layout: LayoutType
    └── metadata: dict
```

---

## API Endpoints

### Generation Endpoints

#### POST `/api/v1/generate/`

同步生成簡報，等待完成後返回結果。

**Request Body**:

```json
{
  "markdown_content": "# 簡報標題\n\n## 第一章\n...",
  "title": "可選標題",
  "author": "作者",
  "template": "模板名稱",
  "audience": "目標受眾",
  "tone": "語調風格"
}
```

**Response**:

```json
{
  "success": true,
  "message": "Presentation generated successfully",
  "presentation_id": "uuid-string",
  "slide_count": 10,
  "download_url": "/api/v1/presentations/{id}/download",
  "metadata": {
    "title": "簡報標題",
    "author": "作者",
    "template": "default.pptx"
  }
}
```

---

#### POST `/api/v1/generate/stream`

使用 Server-Sent Events (SSE) 串流生成進度。

**SSE Events**:

```text
event: progress
data: {"stage": "schema_extraction", "progress": 20, "message": "..."}

event: complete
data: {"presentation_id": "...", "slide_count": 10, "download_url": "..."}

event: error
data: {"error": "錯誤訊息"}
```

---

### Presentation Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/presentations/{id}/download` | GET | 下載 PPTX 檔案 |
| `/api/v1/presentations/{id}/metadata` | GET | 取得簡報元資料 |
| `/api/v1/presentations/{id}` | DELETE | 刪除簡報 |

---

## Service Layer

### LLMService

**檔案**: [llm_service.py](../backend/app/services/llm_service.py)

提供統一的 LLM 介面，支援多個 Provider：

| Provider | 用途 | 成本 |
|----------|------|------|
| **Ollama** | 本地部署 | 免費 |
| **OpenAI** | 雲端 API | 按量計費 |

**功能**:

- 重試邏輯 (exponential backoff)
- 成本追蹤
- 每日預算控制
- 自動 Provider 切換

---

### PPTXBuilder

**檔案**: [pptx_builder.py](../backend/app/services/pptx_builder.py)

將 `Presentation` Model 轉換為實際 PPTX 檔案：

```text
Presentation Model
       │
       ▼
  PPTXBuilder.build()
       │
       ├── 載入模板 (可選)
       ├── 逐一添加投影片
       │     ├── 設定版面配置
       │     ├── 填入標題
       │     ├── 填入內容元素
       │     └── 添加演講者備註
       ├── 設定簡報屬性
       └── 輸出 bytes
       │
       ▼
   PPTX bytes
```

---

### PresentationStorage

**檔案**: [presentation_storage.py](../backend/app/services/presentation_storage.py)

管理生成的簡報檔案：

```text
data/outputs/
├── {presentation_id}.pptx    # PPTX 檔案
└── {presentation_id}.json    # 元資料
```

**功能**:

- 儲存簡報檔案和元資料
- 元資料快取
- 自動清理過期檔案 (預設 7 天)

---

## Complete Request Flow

```text
┌─────────┐                                                              ┌─────────┐
│ Browser │                                                              │ Storage │
└────┬────┘                                                              └────┬────┘
     │ 1. POST /api/v1/generate/stream                                        │
     │    {markdown_content: "..."}                                           │
     ▼                                                                        │
┌─────────┐                                                                   │
│ FastAPI │                                                                   │
└────┬────┘                                                                   │
     │ 2. Create SSE EventSourceResponse                                      │
     │                                                                        │
     ▼                                                                        │
┌────────────┐                                                                │
│ PPTService │                                                                │
└────┬───────┘                                                                │
     │ 3. Stage 1: SchemaExtractor.extract()                                  │
     │    → SSE: {stage: "schema_extraction", progress: 0}                    │
     │    → LLM Call (Ollama/OpenAI)                                          │
     │    → SSE: {stage: "schema_extraction", progress: 20}                   │
     │                                                                        │
     │ 4. Stage 2: ContentOrganizer.organize()                                │
     │    → SSE: {stage: "content_organization", progress: 20}                │
     │    → LLM Call                                                          │
     │    → SSE: {stage: "content_organization", progress: 40}                │
     │                                                                        │
     │ 5. Stage 3: LayoutSelector.select_layouts()                            │
     │    → SSE: {stage: "layout_selection", progress: 40}                    │
     │    → LLM Call                                                          │
     │    → SSE: {stage: "layout_selection", progress: 60}                    │
     │                                                                        │
     │ 6. Stage 4: Editor.edit()                                              │
     │    → SSE: {stage: "content_editing", progress: 60}                     │
     │    → LLM Call                                                          │
     │    → SSE: {stage: "content_editing", progress: 80}                     │
     │                                                                        │
     │ 7. Stage 5: Coder.code()                                               │
     │    → SSE: {stage: "final_generation", progress: 80}                    │
     │    → LLM Call                                                          │
     │    → Returns Presentation Model                                        │
     │                                                                        │
     ▼                                                                        │
┌─────────────┐                                                               │
│ PPTXBuilder │                                                               │
└────┬────────┘                                                               │
     │ 8. PPTXBuilder.build(presentation)                                     │
     │    → Convert Model to PPTX bytes                                       │
     │                                                                        │
     ▼                                                                        │
┌───────────────────┐                                                         │
│PresentationStorage│─────────────────────────────────────────────────────────┤
└────┬──────────────┘                                                         │
     │ 9. storage.save_presentation(id, presentation, pptx_bytes)             │
     │    → Save {id}.pptx                                                    │
     │    → Save {id}.json                                                    │
     │                                                                        │
     ▼                                                                        │
┌─────────┐                                                                   │
│ FastAPI │                                                                   │
└────┬────┘                                                                   │
     │ 10. SSE: {event: "complete", presentation_id, download_url}            │
     │                                                                        │
     ▼                                                                        │
┌─────────┐                                                                   │
│ Browser │                                                                   │
└────┬────┘                                                                   │
     │ 11. GET /api/v1/presentations/{id}/download                            │
     │                                                                        │
     ▼                                                                        │
┌─────────────────────────────────────────────────────────────────────────────┤
│ FileResponse (PPTX file)                                         ◄──────────┘
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration

**檔案**: [config.py](../backend/app/core/config.py)

| 設定項 | 預設值 | 說明 |
|--------|--------|------|
| `llm_provider` | `ollama` | LLM Provider (ollama/openai) |
| `ollama_base_url` | `http://localhost:11434` | Ollama API URL |
| `ollama_model` | `gpt-oss:20b` | Ollama 模型名稱 |
| `max_slides_per_presentation` | `50` | 最大投影片數量 |
| `max_concurrent_generations` | `3` | 最大並行生成數 |
| `generation_timeout_seconds` | `600` | 生成超時時間 |
| `daily_cost_budget_usd` | `10.0` | 每日成本預算 |

---

## Frontend Components

| Component | 功能 |
|-----------|------|
| [GeneratorPage.tsx](../frontend/src/components/GeneratorPage.tsx) | 主頁面容器 |
| [MarkdownEditor.tsx](../frontend/src/components/input/MarkdownEditor.tsx) | Markdown 編輯器 |
| [GenerationControl.tsx](../frontend/src/components/generation/GenerationControl.tsx) | 生成控制面板 |
| [ProgressMonitor.tsx](../frontend/src/components/generation/ProgressMonitor.tsx) | SSE 進度監控 |
| [ResultPreview.tsx](../frontend/src/components/preview/ResultPreview.tsx) | 結果預覽與下載 |
| [TemplateGallery.tsx](../frontend/src/components/template/TemplateGallery.tsx) | 模板選擇 |

---

## Error Handling

系統在每個階段都有錯誤處理機制：

1. **LLM 錯誤**: 重試 3 次 (exponential backoff)
2. **JSON 解析錯誤**: 嘗試多種解析策略 (直接、code block、尋找 `{}`)
3. **驗證錯誤**: 檢查必要欄位並提供具體錯誤訊息
4. **SSE 錯誤**: 發送 `error` event 並終止串流
5. **檔案操作錯誤**: 記錄日誌並返回 HTTP 錯誤

---

## Performance Considerations

- **Token 優化**: 每個 Stage 使用適當的 `max_tokens` 限制
- **溫度控制**: 結構化輸出使用低溫度 (0.2-0.4)
- **串流生成**: SSE 提供即時進度回饋
- **快取**: 元資料快取減少磁碟 I/O
- **清理機制**: 自動清理過期檔案

---

Generated: 2025-12-31 | TeacherAssist V2 Workflow Documentation
