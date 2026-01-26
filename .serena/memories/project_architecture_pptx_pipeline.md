# TeacherAssist_V2 — PPTX 生成管線架構

## 核心流程（5+1 階段）

```
Stage 0: InputClassifier     — 判斷短題目 / 長文章（新增 2026-01-26）
Stage 1: TemplateAnalyzer    — 分析 PPTX Template 結構
Stage 2: ContentGenerator    — LLM 擴展/生成內容 → JSON 草稿
Stage 3: ContentOrganizerV2  — 組織內容到 Template 結構
Stage 4: ImageEnricher       — 注入圖片（可選）
Stage 5: SlideBuilder        — 建構最終 PPTX bytes
```

## 關鍵檔案

| 檔案 | 角色 |
|------|------|
| `backend/app/services/ppt_service_v2.py` | 主要 orchestrator，串連所有 Stage |
| `backend/app/pptagent_core/roles/input_classifier.py` | Stage 0: 輸入分類 |
| `backend/app/pptagent_core/roles/template_analyzer.py` | Stage 1: Template 分析 |
| `backend/app/pptagent_core/roles/content_generator.py` | Stage 2: LLM 內容生成 |
| `backend/app/pptagent_core/roles/content_organizer_v2.py` | Stage 3: 內容組織 |
| `backend/app/pptagent_core/roles/image_enricher.py` | Stage 4: 圖片注入 |
| `backend/app/pptagent_core/roles/slide_builder.py` | Stage 5: PPTX 建構 |
| `backend/app/api/routes/generation.py` | API endpoint（POST /api/v1/generate/） |
| `backend/app/api/schemas/generation.py` | Request/Response schema |
| `backend/app/services/llm_service.py` | LLM 抽象層（Ollama / OpenAI） |

## LLM 設定

- Provider: OllamaProvider 或 OpenAIProvider（由 config 決定）
- 目前使用: Ollama + gpt-oss:20b
- LLMResponse.content 為 str 類型
- 重試邏輯在 LLMService.generate()（網路層）和 ContentGenerator.generate()（JSON 解析層）

## API 端點

- `POST /api/v1/generate/` — 同步生成
- `POST /api/v1/generate/stream` — SSE 串流（含進度更新）
- GenerationRequest 主要欄位: markdown_content, template, slide_count, audience, language, add_images

## SSE 事件順序

```
template_analysis → input_classification → content_generation → content_organization → image_enrichment → pptx_building → generating_script → complete
```
