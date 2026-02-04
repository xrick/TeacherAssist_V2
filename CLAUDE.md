# CLAUDE.md - TeacherAssist V2

專案層級的 Claude Code 指引，提供 codebase 上下文與開發規範。

## 專案概述

TeacherAssist V2 是一套 AI 驅動的簡報生成系統，使用者輸入 Markdown 或短題目，系統透過 LLM 生成專業 PPTX 簡報。

- **Backend**: Python 3.12+ / FastAPI / async
- **Frontend**: React + TypeScript / Vite
- **LLM**: Ollama (`gpt-oss:20b`) 或 OpenAI
- **Cache**: Redis
- **Config**: `backend/.env` + Pydantic `Settings`

## 核心架構：PPTX 生成管線 (v0.3)

```
Stage 0: InputClassifier     — 判斷短題目 / 長文章（多維度評分）
Stage 1: TemplateAnalyzer    — 分析 PPTX Template 結構
Stage 2: ContentGenerator    — LLM 生成內容 → placeholders 格式
Stage 3: ImageEnricher       — 注入 Pexels 圖片（可選，max_images 限制）
Stage 4: SlideBuilder        — 建構最終 PPTX bytes
```

> **v0.3 變更**: 移除原 Stage 3 (ContentOrganizerV2)，ContentGenerator 直接輸出 `placeholders` 格式

### 關鍵檔案對照

| 檔案 | 角色 |
|------|------|
| `backend/app/services/ppt_service_v2.py` | 主 orchestrator，串連所有 Stage |
| `backend/app/pptagent_core/roles/input_classifier.py` | Stage 0: 輸入分類 |
| `backend/app/pptagent_core/roles/template_analyzer.py` | Stage 1: Template 分析 |
| `backend/app/pptagent_core/roles/content_generator.py` | Stage 2: LLM 內容生成（輸出 placeholders 格式） |
| `backend/app/pptagent_core/roles/image_enricher.py` | Stage 3: 圖片注入 |
| `backend/app/pptagent_core/roles/slide_builder.py` | Stage 4: PPTX 建構 |
| `backend/app/api/routes/generation.py` | API endpoint |
| `backend/app/api/schemas/generation.py` | Request/Response schema |
| `backend/app/services/llm_service.py` | LLM 抽象層（Ollama / OpenAI） |
| `backend/app/core/config.py` | 全域設定（`Settings` class） |
| `backend/data/sys_template_config.json` | 模板設定（v0.3） |

### API 端點

- `POST /api/v1/generate/` — 同步生成
- `POST /api/v1/generate/stream` — SSE 串流（含進度更新）

### SSE 事件順序

```
template_analysis → input_classification → content_generation →
image_enrichment → pptx_building → complete
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

#### 決定：採用路線 A 的變體 — 以 `education_basic.pptx` 為 base，修改其 XML 結構

**討論結論**:
- 路線 A 原方案（以 `professional_corporate` 為 base）被否決：版面太花俏、留白不足，不適合做 base template
- 路線 B（全面修復所有模板 + 程式碼）工作量過大
- **最終方案**：以 `education_basic.pptx` 為 base，透過 Python 腳本修改其 slide layout XML，補齊缺少的結構元素

**education_basic.pptx 需要修改的項目**:

| 修改項目 | 技術手段 |
|---------|---------|
| 為每個 placeholder 賦予唯一 idx | 修改 slideLayout XML 中 `<p:ph>` 的 `idx` 屬性 |
| 將 TITLE 移到頂部 | 修改 `<a:off>` (位置) 和 `<a:ext>` (尺寸) |
| 調整 OBJECT 內容區到 TITLE 下方 | 同上，調整 y 座標和高度 |
| 新增含 PICTURE placeholder 的 layout | 複製現有 layout XML，加入 `<p:ph type="pic" idx="N"/>` |
| 增加留白 margin | 調整各 placeholder 的 left/top/width/height |

**XML 層面確認**:
- `xml_idx=None` 即 PPTX 規範中省略 idx 屬性 = 預設值 0（合法但造成程式端衝突）
- TITLE: `xml_type=title`，SUBTITLE: `xml_type=subTitle`，OBJECT: `xml_type=None`（即 body/content）
- 修改方式：用 `pptagent_pptx` + `lxml` 操作 XML blob，與先前改 color theme 同一技術路線

**程式碼端配合修改**:
- `_fill_slide_content()` 改用 placeholder type + 位置匹配，而非只靠 idx
- `_place_images()` 優先使用 PICTURE placeholder

**狀態**: 已被 v0.3 架構簡化取代

### 2026-01-29：v0.3 架構簡化 — 移除 Stage 3 (ContentOrganizerV2)

**狀態**: 已完成並通過整合測試

#### 決策

移除 Stage 3 (ContentOrganizerV2)，讓 ContentGenerator 直接輸出 `placeholders` 格式。

**優點**:
- 減少管線複雜度（6 階段 → 5 階段）
- ContentGenerator 直接輸出最終格式，無需中間轉換

#### 主要變更

**1. ContentGenerator (`content_generator.py`)**
- System prompt 更新為輸出 `placeholders` 格式
- 新增向後相容：`_validate_content()` 可從舊格式自動轉換

**2. PPTServiceV2 (`ppt_service_v2.py`)**
- 移除 `ContentOrganizerV2` import 和呼叫
- 新增 `max_images` 參數傳遞

**3. SlideBuilder (`slide_builder.py`)**
- 修復 layout 選擇：使用 `body_pool` 配置輪替內容頁
- 修復 placeholder type 匹配：使用 regex 移除 ` (數字)` 後綴

**4. ImageEnricher (`image_enricher.py`)**
- 新增 `max_images` 參數限制總圖片數量

**5. Prompt 檔案**
- 5 個 prompt 檔案已更新為輸出 `placeholders` 格式

**6. 設定檔 (`sys_template_config.json`)**
- 版本號更新為 `"version": "0.3"`
- 新增 `my_basic` 模板

#### 修復的 Bug

| Bug | 原因 | 修復 |
|-----|------|------|
| 所有投影片使用 SECTION_HEADER | `layout_index` 預設為 1 | 使用 `body_pool` 輪替 |
| 每張投影片都有圖片 | 無總數限制 | 新增 `max_images` 參數 |
| 內容無法填入（只有標題） | Type 匹配失敗 (`TITLE (1)` vs `TITLE`) | Regex 移除數字後綴 |

#### 整合測試結果

| 測試 | 資料 | Template | 投影片 | 圖片 | 時間 | 結果 |
|------|------|----------|--------|------|------|------|
| 1 | DL.txt | my_basic | 10 | 4 | ~150s | 通過 |
| 2 | brain.txt | education_basic | 8 | 4 | 107s | 通過 |

#### 詳細文件

完整變更記錄見：`claudedocs/dev_diary/v03_architecture_simplification_20260129.md`

### 2026-02-04：v0.4 改善計畫 — 三大研究課題與架構規劃

**狀態**: 研究完成，計畫已產出，待核准後進入實作

#### 背景

針對 v0.3 管線的三大弱點進行深度研究，產出 v0.4 整合改善計畫。

#### 研究課題一：網路搜尋 + LLM Prompt 整合

**目標**: 使用者輸入短題目時，系統先搜尋網路取得相關資料，再結合 prompt 生成有據可查的內容。

**研究結果**:
- **搜尋 API 選型**: Tavily Search（主要，AI-optimized + 內建摘要）、DuckDuckGo（備用/開發測試）
- **架構設計**: 新增 Stage 0.5 `WebSearcher`，僅 SEARCH 模式觸發
- **注入機制**: 搜尋結果格式化為 `<reference_materials>` XML，注入 `{{RAG_DOCUMENTS_HERE}}` placeholder（system prompt 中已預留但從未啟用）
- **Token 預算**: 搜尋結果限 1,250 tokens，最多 5 筆來源
- **Strategy Pattern**: `SearchProvider` ABC → `TavilyProvider` / `DuckDuckGoProvider` 可插拔

**新增檔案規劃**:
- `backend/app/services/search_service.py` — 搜尋抽象層
- `backend/app/pptagent_core/roles/web_searcher.py` — Stage 0.5 角色

**修改檔案規劃**:
- `backend/app/pptagent_core/roles/content_generator.py` — `_build_prompt()` 注入 search_context
- `backend/app/services/ppt_service_v2.py` — 管線新增 Stage 0.5
- `backend/app/core/config.py` — `Settings` 新增搜尋相關設定

#### 研究課題二：精準美觀文字排版

**目標**: 解決 AutoFitter 的致命排版問題，實現 CJK 字體支援與 bullet list 保留。

**發現的現有問題**:

| 問題 | 嚴重度 | 位置 |
|------|--------|------|
| `font.name="Arial"` 硬編碼，無 CJK 支援 | 高 | `auto_fitter.py` |
| `p.text = text` 單段落填充，bullet list 消失 | 致命 | `auto_fitter.py` |
| 無 `<a:ea>` 東亞字體 XML 設定 | 高 | `auto_fitter.py` |
| `measure_text()` 以空格分詞，中文斷行異常 | 高 | `text_metrics.py` |
| `"\n".join(...)` 合併所有內容為單段落 | 致命 | `slide_builder.py` |

**解決方案設計**:
- **`FontConfig`** dataclass: latin + east_asian + complex_script 三層字體配置
- **`EnhancedAutoFitter`**: 多段落填充（每個 bullet point 獨立段落）、XML 操作設定 `<a:ea>` 東亞字體、CJK-aware binary search 字體大小
- **`CJKTextMetrics`**: 逐字斷行（CJK 字元可在任意位置斷行）、字元寬度估算（全形 vs 半形）
- **Bullet list XML**: `<a:buChar>` + `marL` + `indent`（hanging indent）
- **行距**: 1.35x（CJK 建議 1.3~1.5）
- **段落間距**: 6pt after（可配置）

**新增檔案規劃**:
- `backend/app/pptagent_core/layout_engine/font_config.py`

**重寫檔案規劃**:
- `backend/app/pptagent_core/layout_engine/auto_fitter.py` — `EnhancedAutoFitter`
- `backend/app/pptagent_core/layout_engine/text_metrics.py` — `CJKTextMetrics`

**修改檔案規劃**:
- `backend/app/pptagent_core/roles/slide_builder.py` — `_fill_slide_content()` 改用多段落填充

#### 研究課題三：PEXELS API 精準圖片搜尋

**目標**: 解決圖片搜尋效能瓶頸 + 提升圖片相關性。

**發現的現有問題**:

| 問題 | 嚴重度 | 影響 |
|------|--------|------|
| 逐張投影片呼叫 LLM 生成關鍵字 | 致命（效能） | Ollama 下 ~60s/slide |
| 關鍵字品質不穩（抽象標題 → 不相關圖片） | 高 | 圖片匹配度低 |
| 無方向匹配（landscape/portrait） | 中 | 圖片比例與版面不符 |
| 無去重機制 | 中 | 不同投影片可能配到相同圖片 |
| Cache 鍵值不含 orientation | 低 | 同關鍵字不同方向共用 cache |

**解決方案設計**:
- **Stage 2.5 `BatchKeywordGenerator`**: 單次 LLM 呼叫生成所有投影片的英文關鍵字（N 次 → 1 次，效能提升 90%+）
- **方向匹配**: `ORIENTATION_MAP` 依 layout 類型自動選擇 landscape/portrait
- **圖片去重**: `used_image_ids: set[int]` 全域追蹤，搜尋時排除已使用的圖片
- **Cache 修正**: `f"pexels:{keyword}:{orientation}:{per_page}"`
- **色彩匹配**（可選進階）: 從 template 色彩主題提取 Pexels `color` 參數

**新增檔案規劃**:
- `backend/app/pptagent_core/roles/batch_keyword_gen.py`

**修改檔案規劃**:
- `backend/app/pptagent_core/roles/image_enricher.py` — 使用預生成關鍵字 + 去重
- `backend/app/services/pexels_service.py` — Cache 鍵值修正
- `backend/app/services/ppt_service_v2.py` — 管線新增 Stage 2.5

#### v0.4 預期管線

```
Stage 0  : InputClassifier     — 輸入分類
Stage 0.5: WebSearcher [NEW]   — 網路搜尋增強（僅 SEARCH 模式）
Stage 1  : TemplateAnalyzer    — 模板分析
Stage 2  : ContentGenerator    — LLM 內容生成（注入搜尋結果）
Stage 2.5: BatchKeywordGen [NEW] — 批次圖片關鍵字生成
Stage 3  : ImageEnricher       — 圖片注入（使用預生成關鍵字 + 去重）
Stage 4  : SlideBuilder        — PPTX 建構（EnhancedAutoFitter）
```

#### 實作優先序

1. **Phase 1 — 排版基礎修復**（最高優先）: FontConfig + CJKTextMetrics + EnhancedAutoFitter + SlideBuilder 修改
2. **Phase 2 — 圖片搜尋優化**（高優先）: BatchKeywordGenerator + 方向匹配 + 去重 + Cache 修正
3. **Phase 3 — 網路搜尋整合**（中優先）: SearchService + WebSearcher + ContentGenerator 注入 + Settings 更新
4. **Phase 4 — 整合驗證**: 端對端測試 + 效能基準 + PPTX 視覺品質檢查

#### 風險評估

| 風險 | 機率 | 影響 | 緩解策略 |
|------|------|------|---------|
| Tavily API 不穩定 | 低 | 高 | Strategy Pattern + DuckDuckGo fallback |
| CJK 字體跨 OS 不可用 | 中 | 中 | fallback chain + `_get_system_font_path()` |
| 批次關鍵字 JSON 解析失敗 | 中 | 中 | 復用 7 層 JSON fallback |
| XML 操作破壞 PPTX | 低 | 高 | 單元測試 + PPTX 開啟驗證 |

#### 產出文件

- 系統 Workflow + Dataflow 文件：`claudedocs/workflow_dataflow_20260204.md`
- v0.4 整合改善計畫：螢幕輸出（含完整設計規格、程式碼範例、管線全景圖）
