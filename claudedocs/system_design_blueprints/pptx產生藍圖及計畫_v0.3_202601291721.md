# PPTX 生成系統藍圖 v0.3

> 最後更新: 2026-01-29 17:21
> 狀態: 實作中（Stage 3 移除完成，待測試驗證）

---

## 1. 架構概覽

### 1.1 四階段管線（v0.3 簡化版）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PPTX Generation Pipeline v0.3                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   使用者輸入 (Markdown/Text)                                              │
│        │                                                                 │
│        ▼                                                                 │
│   ┌──────────────────┐                                                   │
│   │ InputClassifier  │ ← Stage 0: 判斷 SEARCH/DIRECT 模式                │
│   │ (規則式，無 LLM) │   - 字數、段落數、句末標點密度評分                  │
│   └────────┬─────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌──────────────────┐     ┌──────────────────┐                         │
│   │ TemplateAnalyzer │ ←── │ PPTX Template    │                         │
│   │   (Stage 1)      │     │ + Config JSON    │                         │
│   └────────┬─────────┘     └──────────────────┘                         │
│            │ template_structure                                          │
│            ▼                                                             │
│   ┌──────────────────┐     ┌──────────────────┐                         │
│   │ ContentGenerator │ ←── │ Dynamic Prompt   │                         │
│   │   (Stage 2)      │     │ (per template)   │                         │
│   │   [LLM 呼叫]     │                                                   │
│   └────────┬─────────┘                                                   │
│            │ content (placeholders 格式)  ← v0.3: 直接輸出最終格式       │
│            ▼                                                             │
│   ┌──────────────────┐     ┌──────────────────┐                         │
│   │ ImageEnricher    │ ←── │ Pexels API       │                         │
│   │   (Stage 3)      │     │                  │                         │
│   │   [可選]         │                                                   │
│   └────────┬─────────┘                                                   │
│            │ enriched_content                                            │
│            ▼                                                             │
│   ┌──────────────────┐                                                   │
│   │ SlideBuilder     │                                                   │
│   │   (Stage 4)      │                                                   │
│   └────────┬─────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│      PPTX Bytes                                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 v0.3 vs v0.2 比較

| 項目 | v0.2 | v0.3 |
|------|------|------|
| Stage 數量 | 5 (含 ContentOrganizerV2) | 4 (移除 Stage 3) |
| LLM 呼叫次數 | 2 次 | 1 次 |
| ContentGenerator 輸出 | `title` + `bullet_points` 格式 | `placeholders` 陣列格式 |
| 格式轉換 | ContentOrganizerV2 負責 | 不需要（直接輸出） |
| 預估執行時間 | ~3-5 分鐘 | ~2-3 分鐘 |

---

## 2. 資料流與格式定義

### 2.1 Stage 0: InputClassifier

**輸入**: 使用者原始文字
**輸出**: `ClassificationResult`

```python
class InputMode(Enum):
    SEARCH = "SEARCH_MODE"   # 短題目，需 LLM 從零生成
    DIRECT = "DIRECT_MODE"   # 長文章，需 LLM 結構化

@dataclass
class ClassificationResult:
    mode: InputMode
    confidence: float        # 0.0 ~ 1.0
    char_count: int
    paragraph_count: int
    reason: str
```

**分類邏輯**:
- 字數 < 150 且段落 < 3 → SEARCH
- 字數 >= 150 或段落 >= 3 → DIRECT
- 句末標點密度影響信心度

### 2.2 Stage 1: TemplateAnalyzer

**輸入**: PPTX 檔案路徑 + TemplateConfig
**輸出**: `template_structure`

```python
template_structure = {
    "slide_count": 10,
    "layouts": [
        {
            "index": 0,           # layout_index in PPTX
            "name": "Title Slide",
            "placeholders": [
                {"idx": 0, "type": "TITLE", "position": {...}, "size": {...}},
                {"idx": 1, "type": "SUBTITLE", "position": {...}, "size": {...}},
            ]
        },
        # ... more layouts
    ],
    "structure_rules": {
        "opening": 0,      # layout_index for title slide
        "agenda": 1,       # layout_index for agenda (optional)
        "closing": 10,     # layout_index for closing slide
        "body_pool": [2, 3]  # layout_index 輪替池
    }
}
```

### 2.3 Stage 2: ContentGenerator (v0.3 新格式)

**輸入**: 
- `user_input`: 使用者文字
- `slide_count`: 目標頁數
- `input_mode`: SEARCH / DIRECT
- `prompt_path`: 動態 prompt 檔案路徑

**輸出**: `content` (placeholders 格式)

```json
{
  "title": "簡報標題",
  "target_audience": "目標受眾",
  "slides": [
    {
      "slide_number": 1,
      "layout_index": 0,
      "layout": "title",
      "placeholders": [
        {"idx": 0, "type": "TITLE", "content": "機器學習入門"},
        {"idx": 1, "type": "SUBTITLE", "content": "從理論到實踐"}
      ],
      "visual_suggestion": "科技感背景圖. Keywords: AI, technology",
      "speaker_notes": "歡迎各位..."
    },
    {
      "slide_number": 2,
      "layout_index": 2,
      "layout": "content",
      "placeholders": [
        {"idx": 0, "type": "TITLE", "content": "什麼是機器學習？"},
        {"idx": 1, "type": "BODY", "content": "• 定義與概念\n• 監督式學習\n• 非監督式學習"}
      ],
      "visual_suggestion": "機器學習流程圖. Keywords: ML, diagram",
      "speaker_notes": "機器學習是..."
    }
  ]
}
```

**System Prompt 關鍵規則**:
1. 每個 slide 必須有 `placeholders` 陣列
2. TITLE 使用 `idx=0`，BODY/SUBTITLE 使用 `idx=1`
3. Body 內容使用 `• ` 前綴和 `\n` 分隔
4. `layout_index`: 0=title, 2=content, 3=two-column, 10=closing
5. `layout`: "title", "content", "two_column", "section", "closing"

### 2.4 Stage 3: ImageEnricher

**輸入**: `content` (placeholders 格式)
**輸出**: `enriched_content` (加入 images 陣列)

```json
{
  "slides": [
    {
      "slide_number": 2,
      "placeholders": [...],
      "images": [
        {
          "file_path": "/tmp/pexels_12345.jpg",
          "alt_text": "Machine learning concept",
          "source": "pexels",
          "width": 800,
          "height": 600
        }
      ]
    }
  ]
}
```

**圖片選擇邏輯**:
- 從 `visual_suggestion` 提取 Keywords
- 呼叫 Pexels API 搜尋
- 下載到臨時目錄
- 每張投影片最多 1-3 張圖片

### 2.5 Stage 4: SlideBuilder

**輸入**: `enriched_content` + PPTX Template
**輸出**: PPTX bytes

**Placeholder 匹配邏輯**:
1. 建立 `type_map` 和 `idx_map` 從 content
2. 遍歷 PPTX slide 中的 shapes
3. 優先按 `type` 匹配（支援不同模板）
4. 其次按 `idx` 匹配
5. 使用 AutoFitter 自動調整字體大小

**圖片放置邏輯**:
1. 優先使用 PICTURE placeholder (idx=10)
2. 若無，使用預設位置（右下角）

---

## 3. 設定檔結構

### 3.1 sys_template_config.json (v0.3)

```json
{
  "version": "0.3",
  "default_template": "my_basic",
  "templates": {
    "my_basic": {
      "file_path": "templates/standard_template_01.pptx",
      "prompt_path": "prompts/professional_corporate_prompt.md",
      "total_layouts": 11,
      "structure_rules": {
        "opening": 0,
        "agenda": 1,
        "closing": 10,
        "body_pool": [2, 3]
      },
      "placeholders": {
        "standard": { "title": 0, "body": 1 },
        "exceptions": {}
      }
    }
  }
}
```

### 3.2 Template 設定說明

| 欄位 | 說明 |
|------|------|
| `file_path` | PPTX 模板相對路徑（相對於 `backend/data/`） |
| `prompt_path` | LLM prompt 檔案路徑 |
| `total_layouts` | 模板中的 layout 總數 |
| `structure_rules.opening` | 開場頁 layout_index |
| `structure_rules.agenda` | 議程頁 layout_index |
| `structure_rules.closing` | 結尾頁 layout_index |
| `structure_rules.body_pool` | 內容頁 layout_index 輪替池 |
| `placeholders.standard` | 標準 placeholder idx 映射 |
| `placeholders.exceptions` | 特定 layout 的例外映射 |

---

## 4. 關鍵檔案對照

| 檔案 | 角色 | 行數（約） |
|------|------|-----------|
| `backend/app/services/ppt_service_v2.py` | 主 orchestrator | ~350 |
| `backend/app/pptagent_core/roles/input_classifier.py` | Stage 0 | ~80 |
| `backend/app/pptagent_core/roles/template_analyzer.py` | Stage 1 | ~200 |
| `backend/app/pptagent_core/roles/content_generator.py` | Stage 2 | ~450 |
| `backend/app/pptagent_core/roles/image_enricher.py` | Stage 3 | ~150 |
| `backend/app/pptagent_core/roles/slide_builder.py` | Stage 4 | ~250 |
| `backend/app/pptagent_core/config.py` | Config Loader | ~100 |
| `backend/data/sys_template_config.json` | Template 設定 | ~95 |

---

## 5. API 端點

### 5.1 同步生成

```
POST /api/v1/generate/
Content-Type: application/json

{
  "user_input": "機器學習入門教學",
  "template": "my_basic",
  "slide_count": 10,
  "add_images": true,
  "images_per_slide": 1
}

Response: application/vnd.openxmlformats-officedocument.presentationml.presentation
```

### 5.2 串流生成 (SSE)

```
POST /api/v1/generate/stream
Content-Type: application/json

{
  "user_input": "機器學習入門教學",
  "template": "my_basic",
  "slide_count": 10,
  "add_images": true
}

Response: text/event-stream

event: progress
data: {"stage": "template_analysis", "progress": 0, "message": "分析 Template..."}

event: progress
data: {"stage": "content_generation", "progress": 12, "message": "LLM 正在生成..."}

event: progress
data: {"stage": "image_enrichment", "progress": 50, "message": "注入圖片..."}

event: progress
data: {"stage": "pptx_building", "progress": 80, "message": "建構 PPTX..."}

event: complete
data: {"stage": "completed", "progress": 100, "result": "<base64 bytes>", "stats": {...}}
```

### 5.3 SSE 事件順序 (v0.3)

```
template_analysis (0-10%)
    ↓
input_classification (10%)
    ↓
content_generation (12-50%)
    ↓
image_enrichment (50-80%) [可選]
    ↓
pptx_building (80-100%)
    ↓
completed (100%)
```

---

## 6. 錯誤處理與容錯

### 6.1 JSON 解析容錯 (ContentGenerator)

```
解析層級：
1. 直接 json.loads()
2. 清理 trailing commas
3. 移除控制字元
4. 修復缺少括號
5. 從 ```json``` code block 提取
6. 找 {...} 物件提取

重試策略：
- 第 1 次: temperature=0.3
- 重試: temperature=0.1 + 強化 JSON 約束 prompt
- 最多 3 次嘗試
```

### 6.2 向後相容 (_validate_content)

```python
# 若 LLM 回傳舊格式，自動轉換
if "placeholders" not in slide:
    placeholders = []
    if "title" in slide:
        placeholders.append({"idx": 0, "type": "TITLE", "content": slide["title"]})
    if "bullet_points" in slide:
        body_text = "\n".join(f"• {b}" for b in slide["bullet_points"])
        placeholders.append({"idx": 1, "type": "BODY", "content": body_text})
    slide["placeholders"] = placeholders
```

---

## 7. 已知限制與待改善

### 7.1 目前限制

| 項目 | 限制 | 影響 |
|------|------|------|
| 圖片數量 | 每頁最多 1 張（_place_images 限制） | 圖片豐富度受限 |
| 字體支援 | AutoFitter 硬編碼 Arial | 中文字體可能不佳 |
| Bullet 格式 | 單一段落填入 | 失去原生 bullet list 格式 |
| LLM 依賴 | Ollama 本地模型 JSON 不穩定 | 需要重試機制 |

### 7.2 v0.4 規劃

1. **多圖片支援**: 修改 `_place_images()` 支援多張圖片
2. **字體優化**: 支援自訂字體和中文字體 fallback
3. **Bullet 格式**: 使用原生 paragraph 結構而非單一文字框
4. **快取機制**: 圖片和 LLM 回應快取

---

## 8. 測試驗證

### 8.1 測試腳本

```bash
# v0.3 整合測試
cd backend && python test_v03_integration.py

# 預期輸出
- 輸入: tests/data/ml.md
- 輸出: data/outputs/test_v03_ml.pptx
- 目標: 10 頁，4 頁有圖片
```

### 8.2 驗證項目

- [ ] PPTX 成功生成
- [ ] 投影片數量正確 (10 頁)
- [ ] 標題位置正確 (頂部)
- [ ] 內容填入正確 (非空白)
- [ ] 圖片正確放置 (4 頁)
- [ ] 執行時間合理 (<3 分鐘)

---

## 9. 變更日誌

### v0.3 (2026-01-29)
- **移除 Stage 3 (ContentOrganizerV2)**: 減少一次 LLM 呼叫
- **ContentGenerator 新格式**: 直接輸出 `placeholders` 陣列
- **向後相容**: `_validate_content()` 自動轉換舊格式
- **進度百分比調整**: 移除 content_organization 階段

### v0.2 (2026-01-28)
- 整合 TemplateConfigLoader
- 支援 structure_rules 和 body_pool 輪替
- 支援 PICTURE placeholder (idx=10)
- 動態 prompt 載入

### v0.1 (2026-01-26)
- 初始五階段架構
- JSON 解析修復
- 輸入分類器整合

---

*文件產生時間: 2026-01-29 17:21*
*架構版本: v0.3*
*狀態: 實作完成，待測試驗證*
