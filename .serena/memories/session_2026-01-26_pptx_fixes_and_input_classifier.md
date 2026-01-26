# 工作記錄：PPTX 生成修復 + 輸入分類器整合

**日期**: 2026-01-26
**分支**: main
**狀態**: 全部完成，尚未 commit

---

## 任務一：修復 JSON 解析失敗問題

### 問題描述
使用 Ollama + `gpt-oss:20b` 模型生成 PPTX 時，幾乎每次都在 `content_generator.py:217` 拋出 `json.JSONDecodeError: No valid JSON found`。

### Root Cause
`gpt-oss:20b` 模型對 JSON 結構化輸出的能力不足，LLM 回傳的 `response.content` 不是有效 JSON（可能是空字串、帶有多餘文字、或被截斷的 JSON）。

### 修改檔案
**`backend/app/pptagent_core/roles/content_generator.py`**

1. **強化 System Prompt**（第 61-66 行）
   - 從單行 "Return ONLY valid JSON" 改為 5 條 CRITICAL RULES
   - 明確禁止 markdown code block、多餘文字

2. **`generate()` 方法加入 JSON 重試機制**
   - 首次嘗試：`temperature=0.3`（從原本 0.7 降低）
   - 重試（最多 2 次）：`temperature=0.1` + 強化 JSON 約束 prompt
   - 僅對 `json.JSONDecodeError` 重試

3. **`_parse_json_response()` 強化容錯**
   - 新增 debug logging（記錄前 500 字元）
   - 空值提前檢查
   - 新增 `fix_truncated_json()` — 補全被截斷的 `{}`/`[]`
   - 移除控制字元
   - 失敗時 `logger.error` 記錄完整回應

### 後續建議
若仍頻繁失敗，考慮：
- 換用更強模型（如 `qwen2.5:32b`）
- 使用 Ollama 的 `format: "json"` 參數

---

## 任務二：輸入分類器整合

### 需求
判斷使用者輸入是「短題目」（需要 LLM 生成內容）還是「長文章」（LLM 結構化已有內容），並根據分類結果調整 prompt 策略。

### 新增檔案
**`backend/app/pptagent_core/roles/input_classifier.py`**

- `InputMode` enum: `SEARCH`（短題目）/ `DIRECT`（長文章）
- `ClassificationResult` dataclass: mode, confidence, char_count, paragraph_count, reason
- `classify_user_input(text, length_threshold=150)` 函數
- 多維度評分：字數、段落數、句末標點密度（中英文）
- URL 整行偵測（module 層級 compile regex）
- 空值安全處理

### 修改檔案

**`backend/app/pptagent_core/roles/content_generator.py`**
- import `InputMode` from `input_classifier`
- `generate()` 新增 `input_mode: InputMode = InputMode.DIRECT` 參數
- `_build_prompt()` 新增 `input_mode` 參數，依模式切換：
  - SEARCH: `<user_topic>` + 要求 LLM 自行生成完整內容
  - DIRECT: `<user_input>` + 要求 LLM 結構化已有內容，不添加額外資訊

**`backend/app/services/ppt_service_v2.py`**
- import `classify_user_input`
- `generate()`: Stage 1 和 Stage 2 之間插入 `classify_user_input()`
- `generate_stream()`: 新增 `input_classification` SSE 事件（前端可顯示）
- 兩處 `generator.generate()` 呼叫都傳入 `input_mode=classification.mode`

### 測試驗證結果
| 輸入 | 分類 | 信心度 |
|------|------|--------|
| `"大腦運作原理"` (6字) | SEARCH_MODE | 0.75 |
| 133字段落 (3段, 3句號) | DIRECT_MODE | 0.38 |
| URL | SEARCH_MODE | 1.0 |
| 空字串 | SEARCH_MODE | 0.0 |

### 資料流
```
使用者輸入 → classify_user_input() → ClassificationResult
                                           ↓
              ContentGenerator.generate(input_mode=result.mode)
                                           ↓
              _build_prompt() 依 mode 調整指令 → LLM → JSON → 投影片
```

---

## 完整變更清單

```
新增:
  backend/app/pptagent_core/roles/input_classifier.py

修改:
  backend/app/pptagent_core/roles/content_generator.py
  backend/app/services/ppt_service_v2.py
```

## 尚未處理的已知問題

1. System prompt 中有 `{{USER_TOPIC_HERE}}`、`{{SLIDE_COUNT}}`、`{{RAG_DOCUMENTS_HERE}}` placeholder，但 `_build_prompt()` 並未做 replacement — 它們被當作 literal text 送給 LLM。這是原有問題，本次未修改。
2. 分類器的 `length_threshold=150` 為預設值，可能需要根據實際使用情況調整。
3. 前端尚未處理新的 `input_classification` SSE 事件 — 功能正常但前端不會顯示分類結果。
