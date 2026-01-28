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

### 2026-01-28：Template 整併 (7→5) + PPTX 管線排版分析

**狀態**: Template 整併已完成；排版問題分析完成，待決定改善路線

#### 完成：Template 整併 (7→5)

**背景**: 原有 7 個模板，確認保留 5 個：`education_basic`、`industrial_tech`、`professional_corporate`、`strategic_consulting`、`visionary_story`。

**執行內容**:

1. **清理舊檔案**：刪除 4 張舊 preview PNG（`nature_artistic`、`modern_clean`、`pastoral_style`、`creative_colorful`），對應 JSON 已在之前刪除
2. **修正檔名**：`visionary_story.json.json` → `visionary_story.json`（雙副檔名問題）
3. **重寫 preview 生成器**：`backend/data/templates/create_preview_images.py`
   - 5 個函式分別產生各模板的 400×225 wireframe 風格 PNG
4. **程式碼生成新 PPTX**：`backend/data/templates/create_new_templates.py`
   - 以 `education_basic.pptx` 為 base，透過 XML blob 修改 color theme
   - 產出 `strategic_consulting.pptx` (155KB) 和 `visionary_story.pptx` (156KB)
5. **驗證**：5 個模板皆有完整的 JSON + PPTX + Preview PNG

**新增/修改檔案**:
- `backend/data/templates/create_preview_images.py` — 重寫
- `backend/data/templates/create_new_templates.py` — 新增
- `backend/data/templates/strategic_consulting.pptx` — 新增
- `backend/data/templates/visionary_story.pptx` — 新增
- `backend/data/templates/visionary_story.json` — 改名
- `backend/data/templates/previews/*.png` — 5 張重新生成

#### 完成：PPTX 排版管線深度分析

針對使用者需求「容易做文字排版，圖片能放置到正確位置」，對整條管線進行分析。

**分析範圍**:
- `SlideBuilder.build()` / `_fill_slide_content()` / `_place_images()`
- `TemplateAnalyzer.get_available_layouts()` / `suggest_layout_sequence()` / `create_slide_structure()`
- `ContentOrganizerV2._determine_layout_type()`
- `AutoFitter.fit_text()` / `TextMetrics.measure_text()`
- 5 個 PPTX 模板的所有 slide layout placeholder 位置與尺寸

**發現的嚴重問題**:

| # | 問題 | 嚴重度 | 影響範圍 |
|---|------|--------|----------|
| 1 | education_basic 系 (含 strategic_consulting、visionary_story) 所有 placeholder idx=0，`content_map` dict 鍵值衝突，標題與內文無法同時填入 | **致命** | 3/5 模板 |
| 2 | education_basic 系 TITLE 在底部 (y=5.25")，OBJECT 在頂部 (y=0.00")，版面倒置 | 高 | 3/5 模板 |
| 3 | 僅 `professional_corporate` Layout 15 有 PICTURE placeholder，其餘 4 模板完全沒有 | 高 | 4/5 模板 |
| 4 | `_place_images()` 只處理第一張圖片，位置硬編碼不參考 layout | 中 | 全部 |
| 5 | `AutoFitter` 硬編碼 Arial 字體、單一段落填入，失去 bullet list 格式 | 中 | 全部 |

**模板品質評估**:

| 模板 | 尺寸 | Layout 數 | idx 唯一 | PICTURE ph | TITLE 位置 | 排版可行性 |
|------|------|-----------|----------|------------|-----------|-----------|
| professional_corporate | 10.0"×5.6" | 24 | **是** | **有** | 頂部 (0.80") | **高** |
| industrial_tech | 10.0"×5.6" | 12 | 否 | 無 | 頂部 (0.22") | 中 |
| education_basic | 13.3"×7.5" | 12 | 否 | 無 | 底部 (5.25") | 低 |
| strategic_consulting | 13.3"×7.5" | 12 | 否 | 無 | 底部 (5.25") | 低 |
| visionary_story | 13.3"×7.5" | 12 | 否 | 無 | 底部 (5.25") | 低 |

#### 待決定：改善路線

**路線 A — 以 `professional_corporate` 為唯一 base，其他模板只改顏色主題**
- 優點：立即可用，程式碼改動最小
- 缺點：所有模板共用 10.0"×5.6" 尺寸

**路線 B — 修復所有模板 + 修復程式碼**
- 重建 education_basic 系 PPTX 使其有正確 idx 值
- 修改 `_fill_slide_content()` 支援位置匹配
- 修改 `_place_images()` 使用 PICTURE placeholder
- 修改 `AutoFitter` 支援多段落 / bullet list

**影響的程式碼路徑**:
- `backend/app/pptagent_core/roles/slide_builder.py` — `_fill_slide_content()`, `_place_images()`
- `backend/app/pptagent_core/layout_engine/auto_fitter.py` — `AutoFitter.fit_text()`
- `backend/app/pptagent_core/roles/template_analyzer.py` — `get_available_layouts()` (需記錄 position/size)
- `backend/data/templates/*.pptx` — 可能需重建
