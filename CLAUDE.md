# CLAUDE.md - TeacherAssist V2

專案層級的 Claude Code 指引，提供 codebase 上下文與開發規範。

## 專案概述

TeacherAssist V2 是一套 AI 驅動的簡報生成系統，使用者輸入 Markdown 或短題目，系統透過 LLM 生成專業 PPTX 簡報。

- **Backend**: Python 3.12+ / FastAPI / async
- **Frontend**: React + TypeScript / Vite
- **LLM**: Ollama (`gpt-oss:20b`) 或 OpenAI
- **Cache**: Redis
- **Config**: `backend/.env` + Pydantic `Settings`

## 核心架構：PPTX 生成管線

```
Stage 0: InputClassifier     — 判斷短題目 / 長文章（多維度評分）
Stage 1: TemplateAnalyzer    — 分析 PPTX Template 結構
Stage 2: ContentGenerator    — LLM 擴展/生成內容 → JSON 草稿
Stage 3: ContentOrganizerV2  — 組織內容到 Template 結構
Stage 4: ImageEnricher       — 注入 Pexels 圖片（可選）
Stage 5: SlideBuilder        — 建構最終 PPTX bytes
```

### 關鍵檔案對照

| 檔案 | 角色 |
|------|------|
| `backend/app/services/ppt_service_v2.py` | 主 orchestrator，串連所有 Stage |
| `backend/app/pptagent_core/roles/input_classifier.py` | Stage 0: 輸入分類 |
| `backend/app/pptagent_core/roles/template_analyzer.py` | Stage 1: Template 分析 |
| `backend/app/pptagent_core/roles/content_generator.py` | Stage 2: LLM 內容生成 |
| `backend/app/pptagent_core/roles/content_organizer_v2.py` | Stage 3: 內容組織 |
| `backend/app/pptagent_core/roles/image_enricher.py` | Stage 4: 圖片注入 |
| `backend/app/pptagent_core/roles/slide_builder.py` | Stage 5: PPTX 建構 |
| `backend/app/api/routes/generation.py` | API endpoint |
| `backend/app/api/schemas/generation.py` | Request/Response schema |
| `backend/app/services/llm_service.py` | LLM 抽象層（Ollama / OpenAI） |
| `backend/app/core/config.py` | 全域設定（`Settings` class） |

### API 端點

- `POST /api/v1/generate/` — 同步生成
- `POST /api/v1/generate/stream` — SSE 串流（含進度更新）

### SSE 事件順序

```
template_analysis → input_classification → content_generation →
content_organization → image_enrichment → pptx_building →
generating_script → complete
```

## 開發規範

### Python 風格

- Formatter: Black (line-length 88)
- Linter: Ruff
- Type checking: MyPy
- 所有 async I/O 使用 `await`
- logging 使用 `logging.getLogger(__name__)`，不用 `print()`
- Pydantic `BaseModel` 定義 API schema
- `dataclass` 用於內部資料結構

### 目錄規範

- 測試放在 `backend/tests/`
- Template 檔放在 `backend/data/templates/`
- 生成的 PPTX 放在 `backend/data/outputs/`（gitignored）

### LLM 整合注意事項

- `LLMResponse.content` 是 `str` 類型
- Ollama 本地模型 JSON 輸出不穩定，`content_generator.py` 已有：
  - JSON 解析重試機制（最多 3 次嘗試）
  - 截斷 JSON 修復（`fix_truncated_json`）
  - 多層 fallback 解析（直接解析 → code block → `{...}` 提取）
- 改動 LLM prompt 時注意 system prompt 中的 JSON 約束規則

### 啟動方式

```bash
# Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# 必要服務
redis-server
ollama serve
```

## 開發進度日誌

### 2026-01-26：JSON 解析修復 + 輸入分類器整合

**狀態**: 已完成，尚未 commit

#### 修復：ContentGenerator JSON 解析失敗

**問題**: Ollama + `gpt-oss:20b` 幾乎每次在 `content_generator.py` 拋出 `JSONDecodeError`。

**變更** (`backend/app/pptagent_core/roles/content_generator.py`):
- System prompt 從單行改為 5 條 CRITICAL RULES
- `generate()` 加入 JSON 解析層重試（首次 temp=0.3，重試 temp=0.1 + 強化 prompt）
- `_parse_json_response()` 新增 debug logging、空值檢查、截斷 JSON 修復、控制字元清理

#### 新功能：輸入分類器

**需求**: 自動判斷使用者輸入是「短題目」（LLM 需生成內容）還是「長文章」（LLM 結構化已有內容）。

**新增檔案**:
- `backend/app/pptagent_core/roles/input_classifier.py`
  - `InputMode` enum: SEARCH / DIRECT
  - `ClassificationResult` dataclass: mode, confidence, char_count, paragraph_count, reason
  - `classify_user_input()`: 多維度評分（字數、段落數、句末標點密度）

**修改檔案**:
- `backend/app/pptagent_core/roles/content_generator.py`
  - `generate()` 新增 `input_mode: InputMode` 參數
  - `_build_prompt()` 依模式切換 prompt 策略：
    - SEARCH: `<user_topic>` + 要求 LLM 從零生成完整內容
    - DIRECT: `<user_input>` + 要求 LLM 結構化已有內容
- `backend/app/services/ppt_service_v2.py`
  - `generate()` 和 `generate_stream()` 在 Stage 2 前呼叫 `classify_user_input()`
  - SSE 新增 `input_classification` 事件

#### 已知待處理事項

1. System prompt 中 `{{USER_TOPIC_HERE}}` 等 placeholder 未被 `_build_prompt()` 替換（原有問題）
2. 分類器 `length_threshold=150` 可能需實測調整
3. 前端尚未處理 `input_classification` SSE 事件
