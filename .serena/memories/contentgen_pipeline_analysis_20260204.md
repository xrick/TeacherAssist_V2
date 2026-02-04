# TeacherAssist V2 - ContentGenerator 內容生成管線深度分析

**分析日期**: 2026-02-04  
**版本**: v0.3（已簡化，移除 ContentOrganizerV2）

---

## 一、完整生成流程（5 階段）

```
Stage 0: InputClassifier
  → 判斷輸入為「短題目」(SEARCH) 或「長文章」(DIRECT)
  → 輸出: InputMode enum

Stage 1: TemplateAnalyzer
  → 分析 PPTX 模板結構、取得 Layout 列表
  → 輸出: 可用的投影片版面配置

Stage 2: ContentGenerator ⭐ 核心
  → LLM 生成結構化內容（placeholders 格式）
  → 輸出: JSON {title, target_audience, slides[]}

Stage 3: ImageEnricher
  → 為投影片注入 Pexels 圖片
  → 輸出: enriched_content with images[]

Stage 4: SlideBuilder
  → 構建最終 PPTX bytes
  → 使用 AutoFitter 智慧排版
  → 輸出: .pptx binary
```

---

## 二、ContentGenerator 深度分析

### 2.1 主要功能
```python
class ContentGenerator:
  async def generate(
    user_input: str,
    slide_count: int | None = None,
    audience: str | None = None,
    language: str = "zh-TW",
    input_mode: InputMode = InputMode.DIRECT,
    max_json_retries: int = 2,
    prompt_path: str | None = None
  ) -> dict[str, Any]
```

### 2.2 核心邏輯流程

1. **載入 Prompt**（v0.2 新增動態載入）
   - 如果提供 `prompt_path`，載入自訂 prompt 模板
   - 否則使用預設 prompt（根據 `input_mode` 調整）

2. **建立 User Prompt**
   - SEARCH 模式：`<user_topic>{用戶輸入}</user_topic>` + 要求 LLM 從零生成內容
   - DIRECT 模式：`<user_input>{用戶輸入}</user_input>` + 要求 LLM 結構化已有內容

3. **LLM 呼叫（含重試機制）**
   - 首次：`temperature=0.3`，使用原始 prompt
   - 重試：`temperature=0.1`，加入更強的 JSON 約束提示
   - 最多重試 `max_json_retries` 次（預設 2）

4. **JSON 解析（多層 fallback）**
   - 嘗試直接 `json.loads()`
   - 清理 JSON：移除 trailing commas、控制字元
   - 修復被截斷的 JSON：計算未關閉括號，自動補齊
   - 從 code block 提取（```json ... ```）
   - 找第一個 `{` 到最後一個 `}` 之間的內容

5. **結構驗證（v0.3）**
   - 檢查 `slides` 陣列存在
   - 檢查每個 slide 有 `placeholders` 陣列
   - **向後相容**：如果 slide 有舊格式（title, bullet_points），自動轉換為 placeholders

### 2.3 System Prompt 結構

```
<system-instruction>
  You are an experienced Presentation Specialist (PPTX Expert)
</system-instruction>

<Input_Data>
  {{USER_TOPIC_HERE}}
  {{SLIDE_COUNT}}
  {{RAG_DOCUMENTS_HERE}}
</Input_Data>

<Task>
  1. Synthesize & Ground (使用 Retrieved_Context)
  2. Structure (Plan exact {{SLIDE_COUNT}} slides)
  3. Draft Slides (EXACT format)
</Task>

<Constraints>
  - Exact slide count
  - Source truth (no hallucination)
  - Professional tone
  - JSON safety (proper escaping)
</Constraints>

<OutputFormat>
  JSON with: title, target_audience, slides[]
  Each slide: slide_number, layout_index, layout, placeholders[], visual_suggestion, speaker_notes
  Placeholders: idx, type ("TITLE", "BODY", "SUBTITLE"), content
</OutputFormat>
```

### 2.4 已知限制與問題

**問題 1: Placeholder 變數未被替換**
- System prompt 中有 `{{USER_TOPIC_HERE}}`, `{{SLIDE_COUNT}}`, `{{RAG_DOCUMENTS_HERE}}`
- 但 `_build_prompt()` 未實作替換邏輯
- 目前 LLM 收到的是包含 `{{...}}` 的原始字符串
- **狀態**: 已知問題，未修復

**問題 2: Ollama JSON 輸出不穩定**
- 原因：Ollama 模型 (gpt-oss:20b) 的 JSON 生成能力有限
- 表現：~60-70% 成功率，需多次重試
- 修復：已在 v0.2 實裝多層 JSON 修復機制

**問題 3: AutoFitter 字體測量不準**
- AutoFitter 使用 TextMetrics.measure_text()
- 只測量單一段落，未考慮 bullet list 格式
- 結果：有時文字與容器尺寸不匹配

**問題 4: 圖片配置策略有限**
- `_place_images()` 目前只處理第一張圖片（hardcoded）
- 多張圖片無法智慧配置
- Layout 匹配邏輯簡單（按 layout type 分類）

---

## 三、LLMService（LLM 服務層）

### 3.1 架構
```python
class LLMService:
  provider: BaseLLMProvider  # OllamaProvider 或 OpenAIProvider
  total_cost_today: float
  request_count: int
  
  async def generate(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    max_retries: int = 3,
    retry_delay: float = 1.0
  ) -> LLMResponse
```

### 3.2 關鍵特性

1. **Provider 抽象層**
   - OllamaProvider：本地模型，URL + model name
   - OpenAIProvider：API 調用，需 API key

2. **重試邏輯**
   - 指數退避：`delay = retry_delay * (2**attempt)`
   - 預設 3 次重試，每次間隔倍增

3. **成本追蹤**
   - 按日統計 (`total_cost_today`)
   - 檢查日預算 (`daily_cost_budget_usd`)
   - 每次呼叫記錄 token 數和成本

4. **使用統計**
   ```python
   async def get_usage_stats() -> dict:
     return {
       "provider": str,
       "model": str,
       "total_cost_today": float,
       "request_count_today": int,
       "daily_budget": float,
       "budget_remaining": float,
       "budget_usage_percent": float
     }
   ```

---

## 四、ImageEnricher（圖片注入）

### 4.1 流程
```
enrich(organized_content, draft_content) 
  → _build_visual_suggestions_map() [從 draft_content 提取視覺建議]
  → 逐張投影片處理：
    ├─ 判斷 layout type（跳過某些 layout）
    ├─ 檢查是否已達 max_images 限制
    ├─ _get_images_for_slide()
    │   ├─ _generate_keywords() [從 LLM 生成搜尋關鍵字]
    │   ├─ cache.get_cached_images_by_keyword() [檢查快取]
    │   └─ _search_and_cache_images()
    │       ├─ pexels.search_images()
    │       ├─ pexels.download_image()
    │       └─ cache.save_to_cache()
    └─ enriched_slide.images = images[]
```

### 4.2 v0.3 改進：max_images 限制
- 新增 `max_images: int | None` 參數
- 逐張投影片檢查：若已達上限，後續投影片跳過圖片注入
- 解決原先「每張投影片都有圖片」的問題

### 4.3 關鍵字生成策略
```python
async def _generate_keywords(
  visual_suggestion: str,
  slide_title: str,
  presentation_title: str
) -> tuple[str, list[str]]
```
- 優先使用 `visual_suggestion`（由 ContentGenerator 提供）
- 呼叫 PexelsService.generate_search_keywords() 優化關鍵字
- Fallback：使用 `slide_title` 或 `presentation_title`

### 4.4 快取機制
- CachedImageInfo: (image_id, file_path, keyword, photographer, pexels_url, alt_text)
- 快取鍵：keyword（同一關鍵字的圖片複用）
- 避免重複下載，加速生成

---

## 五、SlideBuilder（投影片構建）

### 5.1 核心方法
```python
def build(content: dict[str, Any], master_index: int = 0) -> bytes
```

流程：
1. 讀取 PPTX 模板
2. 清除現有投影片
3. 迴圈生成投影片：
   - 智慧選擇 layout_index（opening, closing, body pool 輪替）
   - _fill_slide_content() [填入文字]
   - _place_images() [加入圖片]
4. 返回 PPTX bytes

### 5.2 v0.3 改進：Layout 選擇邏輯
```python
if layout_idx is None:
  if i == 0 or slide_layout == "title":
    layout_idx = structure_rules.opening  # 第一頁
  elif i == total_slides - 1 or slide_layout == "closing":
    layout_idx = structure_rules.closing  # 最後一頁
  elif slide_layout == "section":
    layout_idx = 1  # SECTION_HEADER
  else:
    layout_idx = body_pool[body_pool_idx % len(body_pool)]  # 輪替
    body_pool_idx += 1
```
- 从 config 的 `structure_rules` 讀取 opening, closing, body_pool
- body_pool 輪替：[2, 3] → [2, 3, 2, 3, ...]

### 5.3 文字填入：_fill_slide_content()
```python
def _fill_slide_content(self, slide, slide_data: dict[str, Any])
```

**改進（v0.3）**:
- 建立 `type_map` 和 `idx_map` 對照表
- 優先使用 type 匹配（如 "TITLE", "BODY"）
- regex 移除 type 名稱中的 " (數字)" 後綴
- 特殊處理：OBJECT → CONTENT / BODY
- 備用：使用 idx 匹配

**使用 AutoFitter**:
```python
AutoFitter.fit_text(
  shape.text_frame, 
  text_str, 
  font_name="Arial", 
  max_font_size=28 if is_title else 24
)
```
- 標題：28pt
- 內容：24pt
- 自動縮小至適應容器

### 5.4 圖片配置：_place_images()
```python
def _place_images(self, slide, images: list, layout_type: str, layout_index: int = -1)
```

**v0.2 改進**:
- 優先查找 PICTURE placeholder（idx 可從 config 取得）
- 其次嘗試 PICTURE type
- 若無 placeholder，使用手動位置策略

**手動位置策略**:
- `two_column`: 放在右側 (55% + width 40%)
- `image_text`: 放在左側 (45% width)
- `full_image`: 全版
- 預設：右下角，避免遮擋列表

**已知限制**:
- 只處理第一張圖片（`images[0]`）
- 多張圖片無法配置

---

## 六、AutoFitter（智慧排版）

### 6.1 演算法：二分搜尋法
```python
@classmethod
def fit_text(cls, text_frame, text: str, font_name: str = "Arial", max_font_size: int = 24):
  # 取得容器尺寸（扣除邊距）
  available_width = shape.width - margin_left - margin_right
  available_height = shape.height - margin_top - margin_bottom
  
  # 二分搜尋最佳字級
  low = MIN_FONT_SIZE (8pt)
  high = max_font_size
  
  while low <= high:
    mid = (low + high) / 2
    w, h = TextMetrics.measure_text(text, font_name, mid, max_width_emu=available_width)
    
    if h <= available_height:
      optimal_size = mid
      low = mid + 0.5  # 嘗試更大
    else:
      high = mid - 0.5  # 縮小
```

### 6.2 限制
- 只測量單一段落高度
- 未考慮 bullet list 的行距、段落間距
- 邊距使用預設值（91440 EMU），未讀取實際 placeholder 邊距
- 結果：有時測量不準確

---

## 七、設定系統（sys_template_config.json）

### 7.1 結構
```json
{
  "version": "0.3",
  "default_template": "my_basic",
  "templates": {
    "template_name": {
      "file_path": "templates/xxx.pptx",
      "prompt_path": "prompts/xxx.md",
      "total_layouts": 11,
      "structure_rules": {
        "opening": 0,       # 標題頁 layout idx
        "agenda": 1,        # 議程頁
        "closing": 10,      # 結束頁
        "body_pool": [2, 3] # 內容頁輪替池
      },
      "placeholders": {
        "standard": { "title": 0, "body": 1 },
        "exceptions": {}
      }
    }
  }
}
```

### 7.2 當前模板（5 個）
- `my_basic`: 標準模板
- `education_basic`: 教育風格
- `industrial_tech`: 工業技術
- `professional_corporate`: 企業專業
- `strategic_consulting`: 策略顧問
- `visionary_story`: 願景故事

**注意**: 所有模板都使用 **同一個 PPTX 檔案** (`standard_template_01.pptx`)，只是 prompt 不同

---

## 八、Prompt 檔案系統（v0.2）

### 8.1 位置
`backend/data/prompts/` 下：
- `professional_corporate_prompt.md`
- `academic_research_and_deep_analysis_mode.md`
- `industrial_tech_prompt.md`
- `strategic_consulting_prompt.md`
- `visionary_story_prompt.md`

### 8.2 格式（範例：professional_corporate_prompt.md）
```markdown
# Role
你是一位麥肯錫風格商業顧問

# Task
將【原始資料】轉化為簡報

# Rules for Expansion & Allocation
...

# Input Data
原始資料："""{USER_DATA}"""

# Output Format (CRITICAL)
必須輸出 JSON，結構如下：
{
  "title": "簡報標題",
  "target_audience": "目標受眾",
  "slides": [...]
}
```

### 8.3 替換變數
- `{USER_DATA}` 或 `{USER_INPUT}`: 使用者輸入
- `{SLIDE_COUNT}`: 投影片數量
- `{AUDIENCE}`: 目標受眾
- `{LANGUAGE}`: 輸出語言

---

## 九、架構改進建議

### 高優先級（影響功能）

1. **修復 System Prompt 變數替換**
   - 當前：System prompt 中 `{{...}}` 未被替換
   - 修復：在 `_build_prompt()` 中替換這些變數
   - 影響：LLM 能更好地理解約束條件

2. **完整的多圖片配置**
   - 當前：只處理第一張圖片
   - 修復：支援多張圖片的網格配置
   - 參考：Pexels API 返回多張結果，但未使用

3. **AutoFitter 精準度改進**
   - 當前：邊距使用預設值
   - 修復：讀取實際 placeholder 邊距
   - 當前：只測量單段落
   - 修復：支援 bullet list 的多行測量

### 中優先級（體驗優化）

4. **Prompt 動態優化**
   - 根據輸入長度調整 prompt
   - SEARCH 模式加入「產業上下文」
   - DIRECT 模式加入「邏輯分析提示」

5. **快取策略優化**
   - 當前：只按 keyword 快取
   - 改進：按 (keyword, orientation) 快取
   - 改進：過期策略、LRU 淘汰

6. **SSE 事件豐富**
   - 當前：input_classification 事件未被前端處理
   - 改進：為 image_enrichment 階段加入進度百分比

### 低優先級（代碼質量）

7. **型別註解完整化**
   - 一些內部函式缺少型別提示
   - 改進：補齊所有型別註解（mypy strict）

8. **單元測試覆蓋**
   - JSON 解析 fallback 邏輯複雜，缺少測試
   - 改進：為 `_parse_json_response()` 寫單元測試

---

## 十、性能特徵

| 階段 | 典型耗時 | Token 數 | 成本 |
|------|---------|---------|------|
| InputClassifier | <0.1s | 0 | 0 |
| TemplateAnalyzer | <0.5s | 0 | 0 |
| ContentGenerator | 30-60s | 2000-4000 | $0.01-0.02 |
| ImageEnricher | 10-30s | LLM 調用 | $0.001-0.01 |
| SlideBuilder | 1-5s | 0 | 0 |
| **總計** | 45-100s | 2000-4500 | $0.02-0.03 |

**瓶頸**: ContentGenerator LLM 呼叫（佔 60% 耗時）

---

## 十一、測試用例

### 快樂路徑
```python
# 短題目 (SEARCH 模式)
input_data = "深度學習"
result = await content_gen.generate(
  user_input=input_data,
  slide_count=10,
  input_mode=InputMode.SEARCH
)
# 預期：LLM 擴展內容，生成 10 張詳細投影片

# 長文章 (DIRECT 模式)
input_data = "詳細的白皮書，3000 字..."
result = await content_gen.generate(
  user_input=input_data,
  slide_count=8,
  input_mode=InputMode.DIRECT
)
# 預期：LLM 結構化內容，生成 8 張概括投影片
```

### 邊界情況
- 超長輸入 (>10K 字元) → token 溢出
- 空 visual_suggestion → ImageEnricher fallback 到 slide_title
- JSON 截斷 → 多層 fallback 機制補救
- max_images 限制 → 均勻分配圖片至前 N 張投影片

