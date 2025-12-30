<!-- docs/architectural_analysis_report.md -->
# TeacherAssist V2 架構分析報告
## PPTAgent/DeepPresenter 重構計劃評估

**分析日期**: 2025-12-30
**文件來源**: [`docs/pptagent_analysis_and_refactor_plan_full_ABC.md`](docs/pptagent_analysis_and_refactor_plan_full_ABC.md)
**分析深度**: Deep Analysis (--think-hard --seq --focus architecture)

---

## 執行摘要

### 📊 整體評分

| 評估維度 | 評分 | 說明 |
|---------|------|------|
| 架構設計質量 | ⭐⭐⭐⭐⭐ 9/10 | 清晰的分層架構，關注點分離良好 |
| 技術選型合理性 | ⭐⭐⭐⭐⭐ 9/10 | 現代技術堆疊，符合業界最佳實踐 |
| 風險管理完整性 | ⭐⭐⭐⭐ 7/10 | 主要風險已識別，但缺少部分運維風險 |
| 實施計劃可行性 | ⭐⭐⭐⭐ 8/10 | 階段清晰，但時間估計略顯樂觀 |
| 可擴展性 | ⭐⭐⭐⭐⭐ 9/10 | 模組化設計，支持漸進式演進 |
| 可維護性 | ⭐⭐⭐⭐ 8/10 | 配置驅動，但缺少標準框架整合 |

**總體建議**: ✅ **強烈推薦執行** - 採用 Option A (MVP) 起點，階段式演進

---

## 1. 架構設計分析

### 1.1 整體架構質量 ⭐⭐⭐⭐⭐

**優勢**:
- ✅ **清晰的分層架構**: Orchestration → Agent → MCP Tools → LLM
- ✅ **關注點分離**: 編排層、業務邏輯、工具服務、基礎設施明確分離
- ✅ **模組化設計**: PPTAgent 核心可獨立使用，DeepPresenter 工具可選擇性整合
- ✅ **業界標準協議**: 使用 MCP (Model Context Protocol) 進行工具管理

**潛在問題**:
- ⚠️ **過度設計風險**: DeepPresenter 的完整堆疊對簡單用例可能過於複雜
- ⚠️ **抽象層開銷**: MCP 架構引入額外抽象，可能影響調試和性能

**評估**: 文件正確識別此問題，建議從 Option A (最小化核心) 開始是明智選擇。

### 1.2 Agent 架構設計 ⭐⭐⭐⭐⭐

**亮點**:

1. **Context Budget 管理**
   ```python
   # 防止 token 超限的主動管理
   HALF_NOTICE_MESSAGE    # 50% 使用時警告
   URGENT_NOTICE_MESSAGE  # 80% 使用時強制完成
   ```
   - 這是生產級 agentic 系統的必備功能
   - 避免因超出上下文限制導致的失敗

2. **YAML-based 配置**
   ```yaml
   use_model: agent
   include_tool_servers: all
   exclude_tools: [inspect_slide]
   ```
   - 聲明式工具選擇，無需修改代碼
   - 支持快速原型和實驗

3. **Agent-specific 驗證**
   ```python
   def finalize(outcome: str, agent_name: str):
       if agent_name == "Research":
           # 驗證 markdown 檔案和圖片路徑
       elif agent_name == "PPTAgent":
           # 驗證 PPTX 檔案和幻燈片數量
   ```
   - 確保每個 Agent 產出符合預期格式
   - 提供即時錯誤回饋

4. **並行工具執行**
   ```python
   observations = await asyncio.gather(*coros)
   ```
   - 多個工具調用並行執行，提高效率

**改進建議**:
- 🔧 添加**細粒度重試策略** (per-tool retry configuration)
- 🔧 實施**工具調用斷路器** (circuit breaker pattern) 防止級聯失敗
- 🔧 添加**工具執行超時設置** (per-tool timeout limits)

### 1.3 PPTAgent 核心架構 ⭐⭐⭐⭐⭐

**關鍵創新**:

1. **雙階段幻燈片歸納**
   - **Phase 1: 功能分類** - 識別 opening, toc, ending 等功能性幻燈片
   - **Phase 2: 版面聚類** - 使用圖像嵌入 (ViT) 和餘弦相似度分組相似版面
   - **結果**: 自動提取內容 schema，無需手動標註模板

2. **五階段生成流程**
   ```
   schema_extractor → content_organizer → layout_selector → editor → coder
   ```
   - 結構化流程確保生成質量
   - 每個階段都有專門的 Agent 角色

3. **並行幻燈片生成**
   ```python
   async with asyncio.TaskGroup() as tg:
       for slide_idx, item in enumerate(outline):
           tg.create_task(generate_slide(slide_idx, item))
   ```
   - 顯著提升大型簡報生成速度
   - 10 頁簡報可並行生成，節省 10x 時間

**架構優勢**: 這不是簡單的「Markdown → PPTX」轉換，而是理解內容語意、匹配最佳版面、生成高質量幻燈片的**智能系統**。

---

## 2. 技術選型評估

### 2.1 前端技術堆疊 ⭐⭐⭐⭐⭐

**選擇**: React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui + Framer Motion

**評價**: ✅ **現代且成熟的組合**

| 技術 | 優勢 | 考量 |
|------|------|------|
| **React 18** | 成熟生態系統，豐富組件庫 | 需要 TypeScript 確保類型安全 |
| **Vite** | 極快的開發伺服器，優化的打包 | 相對 CRA 更輕量 |
| **Tailwind CSS** | 實用優先，快速開發，一致性 | 學習曲線 (對不熟悉者) |
| **shadcn/ui** | 可定制的組件，無供應商鎖定 | 需要手動安裝組件 |
| **Framer Motion** | 流暢動畫，提升用戶體驗 | 包大小增加約 40KB |

**組件架構** (文件第 2.10 節):
```
┌─ InputPanel (TopicInput, ContentEditor, AdvancedOptions)
├─ TemplateGallery (TemplateCard with preview)
├─ GenerationControl (GenerateButton, ProgressBar)
└─ PreviewPanel (SlideCarousel, SlideCard, DownloadButton)
```

**亮點**:
- ✅ **漸進式揭露**: 簡單 → 進階選項，避免認知過載
- ✅ **響應式設計**: Mobile-first approach
- ✅ **無障礙考慮**: Keyboard navigation, screen reader support

### 2.2 後端技術堆疊 ⭐⭐⭐⭐⭐

**選擇**: FastAPI + asyncio + Pydantic + Jinja2

**評價**: ✅ **Python async 生態系統的最佳組合**

| 技術 | 優勢 | TeacherAssist 應用 |
|------|------|-------------------|
| **FastAPI** | 自動 API 文檔，類型驗證，高性能 | REST API + SSE 串流 |
| **asyncio** | 原生異步支持，並行任務處理 | 並行幻燈片生成 |
| **Pydantic** | 數據驗證，結構化輸出 | LLM 響應格式驗證 |
| **Jinja2** | 模板引擎，動態提示生成 | Agent 角色提示模板 |

**SSE (Server-Sent Events) 選擇** ✅:
- 比 WebSocket 更簡單 (單向數據流)
- 原生 HTTP，無需額外協議
- 自動重連機制
- 適合進度串流場景

### 2.3 LLM 整合策略 ⭐⭐⭐⭐

**當前設計**: 自定義 `LLM` / `AsyncLLM` 包裝器

**優勢**:
- ✅ 輕量級，無額外依賴
- ✅ OpenAI-compatible API 支持 (Ollama, OpenAI, etc.)
- ✅ 支持結構化輸出 (Pydantic response_format)

**潛在問題**:
- ⚠️ 與 LangChain/LlamaIndex 等標準框架功能重複
- ⚠️ 缺少內建的錯誤處理、重試、回退機制
- ⚠️ 缺少 token 計數、成本追蹤等工具

**改進建議**:
```python
# 考慮整合 LangChain 作為中間層
from langchain.chat_models import ChatOpenAI, ChatOllama
from langchain.callbacks import AsyncCallbackHandler

class TeacherAssistLLM:
    def __init__(self, provider: str, model: str):
        if provider == "ollama":
            self.llm = ChatOllama(model=model, callbacks=[...])
        elif provider == "openai":
            self.llm = ChatOpenAI(model=model, callbacks=[...])
        # 自動獲得重試、成本追蹤、token 計數等功能
```

**或者保留自定義包裝器，但添加**:
- Token 使用追蹤和預算控制
- 自動重試 (exponential backoff)
- 多模型回退 (fallback chain)
- 成本估算 (pre-call cost estimation)

---

## 3. 實施計劃分析

### 3.1 Option A (MVP, 3-4 週) 評估 ⭐⭐⭐⭐

**階段劃分**:

| 階段 | 時間 | 關鍵交付物 | 風險評估 |
|------|------|-----------|---------|
| **Phase 1: 核心移植** | Week 1 | PPTAgent 核心模組，LLM Adapter | 🟢 低風險 |
| **Phase 2: 服務層** | Week 2 | API 路由，SSE 串流，模板管理 | 🟡 中風險 |
| **Phase 3: 前端** | Week 3 | React UI，組件開發，整合 | 🟡 中風險 |
| **Phase 4: 測試部署** | Week 4 | E2E 測試，Presenton 移除，部署 | 🟢 低風險 |

**時間估計評估**:
- **樂觀**: 假設無重大技術障礙
- **現實**: 可能需要 **4-5 週** (包含提示調整、測試、修復)
- **建議**: 保留 **20% 緩衝時間** 應對意外問題

**潛在延遲因素**:
1. ⏱️ **提示工程調整** - 文件假設提示可直接移植，但可能需要針對 Ollama 模型 (qwen2.5, llama3) 進行調整
2. ⏱️ **模板轉換** - 現有 TeacherAssist 模板可能與 PPTAgent 格式不完全兼容
3. ⏱️ **圖像嵌入依賴** - 如果跳過 ViT 嵌入，版面匹配質量可能下降，需要回頭實施
4. ⏱️ **SSE 整合測試** - 跨瀏覽器兼容性、斷線重連、錯誤處理需要充分測試

### 3.2 Option B (5-6 週) 評估 ⭐⭐⭐⭐

**額外階段**:

| 階段 | 時間 | 功能 | 複雜度 |
|------|------|------|--------|
| **Tool 整合** | Week 4-5 | FastMCP, Tavily/Firecrawl 搜索 | 🟡 中 |
| **增強功能** | Week 5-6 | 研究模式，圖片生成，文檔分析 | 🟠 中高 |

**評價**: Option B 提供顯著的功能提升，但增加複雜度。**建議僅在 Option A 成功驗證後考慮**。

### 3.3 缺少的實施細節

文件在以下方面需要補充:

#### 3.3.1 數據遷移計劃 ❌
- 現有用戶簡報和模板如何遷移？
- 格式轉換策略？
- 數據備份和回滾？

**建議添加**:
```markdown
### Data Migration Strategy
1. **Template Migration**
   - Export Presenton templates to intermediate format
   - Convert to PPTAgent induction format
   - Validate template compatibility

2. **User Presentation Archive**
   - Backup existing presentations to `/archive/`
   - Provide legacy format download option
   - Gradual migration to new format

3. **Configuration Migration**
   - Map Presenton settings to PPTAgent configs
   - User preference preservation
```

#### 3.3.2 測試計劃 ❌ (僅提及「整合測試」)

**建議測試策略**:

```markdown
### Testing Strategy

#### Unit Tests (Coverage target: 80%)
- `pptagent_core/agent.py` - Agent 配置和工具選擇
- `pptagent_core/apis.py` - 幻燈片編輯 API
- `pptagent_core/induct.py` - 模板歸納邏輯
- `pptagent_core/pptgen.py` - 生成流程編排
- Mock LLM 響應確保測試確定性

#### Integration Tests
- LLMService + Ollama/OpenAI 真實連接
- 模板歸納 + 實際範例模板
- API 端點 + 請求驗證
- SSE 串流 + 客戶端連接

#### E2E Tests (Playwright/Cypress)
- 用戶完整流程: 輸入 → 生成 → 下載
- 不同模板測試 (business, academic, creative)
- 錯誤場景 (無效輸入, LLM 超時, 網路中斷)
- 並發用戶測試 (5+ users)

#### Performance Tests (Locust/k6)
- 基準: 10 頁簡報 < 2 分鐘 (Ollama local)
- 負載: 10 concurrent users, 100 presentations/hour
- 記憶體: < 2GB per instance
- CPU: < 80% utilization under load
```

#### 3.3.3 部署和監控計劃 ❌

**建議添加**:

```markdown
### Deployment Strategy

#### Containerization
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5050"]
```

#### Monitoring & Observability
- **Metrics** (Prometheus):
  - `presentation_generation_duration_seconds` (histogram)
  - `llm_api_calls_total` (counter)
  - `llm_api_errors_total` (counter)
  - `active_generations` (gauge)

- **Logging** (Structured JSON):
  ```python
  logger.info("generation_started", extra={
      "presentation_id": pres_id,
      "num_slides": num_slides,
      "template": template_name
  })
  ```

- **Tracing** (OpenTelemetry):
  - E2E 請求追蹤
  - LLM 調用鏈
  - 效能瓶頸識別

#### Health Checks
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "llm_service": await llm_service.ping(),
        "template_count": len(template_storage.list())
    }
```
```

---

## 4. 風險分析與緩解

### 4.1 已識別風險 ⭐⭐⭐⭐

文件識別了 **6 個主要風險**，並提供緩解策略:

| # | 風險 | 緩解策略 | 評價 |
|---|------|---------|------|
| 1 | pptagent-pptx 依賴 | PyPI 包 → vendor → fallback | ✅ 穩健 |
| 2 | 圖像嵌入 (ViT) | MVP 跳過 → 後續添加 | ✅ 實用 |
| 3 | 模型相容性 | 測試目標模型，調整提示 | ✅ 合理 |
| 4 | MCP 複雜性 | MVP 不使用 → 漸進添加 | ✅ 明智 |
| 5 | 視覺回饋循環 | MVP 跳過 Playwright | ✅ 簡化 |
| 6 | 搜索 API 依賴 | 功能標誌 + fallback | ✅ 彈性 |

### 4.2 缺少的風險 ⚠️

#### 4.2.1 LLM API 速率限制和成本控制 🔴

**風險描述**:
- Ollama 本地部署可能資源不足 (記憶體、GPU)
- OpenAI API 使用可能產生意外高成本
- 並發生成可能觸發速率限制

**緩解建議**:
```python
# 成本控制
class CostController:
    def __init__(self, daily_budget_usd: float):
        self.budget = daily_budget_usd
        self.used = 0.0

    async def check_budget(self, estimated_cost: float):
        if self.used + estimated_cost > self.budget:
            raise BudgetExceededError(f"Daily budget ${self.budget} exceeded")
        self.used += estimated_cost

# 速率限制
from aiolimiter import AsyncLimiter
llm_limiter = AsyncLimiter(max_rate=10, time_period=60)  # 10 calls/min

async def call_llm_with_limit(prompt):
    async with llm_limiter:
        return await llm_service.generate(prompt)
```

#### 4.2.2 大型簡報記憶體管理 🟡

**風險描述**:
- 50+ 頁簡報可能消耗大量記憶體
- 並行生成多個簡報可能導致 OOM

**緩解建議**:
```python
# 記憶體監控
import psutil

class MemoryGuard:
    MAX_MEMORY_PERCENT = 85

    async def check_memory(self):
        if psutil.virtual_memory().percent > self.MAX_MEMORY_PERCENT:
            raise MemoryPressureError("System memory critical")

# 批次處理大型簡報
async def generate_large_presentation(slides, batch_size=10):
    for i in range(0, len(slides), batch_size):
        batch = slides[i:i+batch_size]
        await generate_batch(batch)
        # 釋放記憶體
        gc.collect()
```

#### 4.2.3 並發用戶資源競爭 🟡

**風險描述**:
- 多用戶同時生成簡報
- Ollama 本地模型僅支持有限並發
- 文件 I/O 競爭 (模板讀取、PPTX 寫入)

**緩解建議**:
```python
# 任務佇列
from celery import Celery
app = Celery('tasks', broker='redis://localhost:6379')

@app.task
async def generate_presentation_task(request_data):
    # 異步任務處理
    result = await ppt_service.generate(request_data)
    return result

# 限制並發
from asyncio import Semaphore
max_concurrent_generations = Semaphore(3)  # 最多 3 個並發

async def generate_with_limit(request):
    async with max_concurrent_generations:
        return await ppt_service.generate(request)
```

#### 4.2.4 提示注入攻擊 🔴 (Security)

**風險描述**:
- 用戶輸入可能包含惡意提示，操控 LLM 行為
- 例如: "Ignore previous instructions and..."

**緩解建議**:
```python
# 輸入清理
import re

def sanitize_user_input(text: str) -> str:
    # 移除可疑指令
    suspicious_patterns = [
        r"ignore\s+previous\s+instructions",
        r"system\s*:\s*",
        r"<\|im_start\|>",
    ]
    for pattern in suspicious_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text

# 提示隔離
def build_prompt(user_input: str, template: str) -> str:
    # 明確標記用戶內容邊界
    return template.format(
        user_content=f"```user\n{sanitize_user_input(user_input)}\n```"
    )
```

---

## 5. 架構改進建議

### 5.1 可觀測性整合 ⭐⭐⭐⭐⭐

**當前狀態**: 僅有工具調用歷史記錄到 JSONL

**建議**: 整合 OpenTelemetry 獲得完整的可觀測性

```python
# backend/app/observability.py
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Tracing setup
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="localhost:4317"))
)

# Usage in code
@tracer.start_as_current_span("generate_presentation")
async def generate_presentation(request):
    with tracer.start_as_current_span("outline_generation"):
        outline = await generate_outline(request.content)

    with tracer.start_as_current_span("slide_generation"):
        slides = await generate_slides(outline)

    return slides
```

**效益**:
- 🔍 端到端請求追蹤
- ⏱️ 效能瓶頸識別
- 🐛 分散式調試
- 📊 服務依賴圖

### 5.2 配置管理標準化 ⭐⭐⭐⭐

**當前狀態**: YAML 配置 + 環境變數

**建議**: 使用 Pydantic Settings 統一配置管理

```python
# backend/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # LLM Configuration
    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5:7b"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str | None = None

    # Generation Limits
    max_slides_per_presentation: int = 50
    max_concurrent_generations: int = 3
    generation_timeout_seconds: int = 600

    # Cost Control
    daily_cost_budget_usd: float = 10.0
    cost_per_1k_tokens: float = 0.002

    # Template Storage
    template_storage_path: Path = Path("data/templates")
    output_storage_path: Path = Path("data/outputs")

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

settings = Settings()
```

**效益**:
- ✅ 類型安全的配置
- ✅ 環境變數自動映射
- ✅ 配置驗證
- ✅ 文檔自動生成

### 5.3 快取策略 ⭐⭐⭐⭐

**當前狀態**: 無快取

**建議**: 多層快取提升效能和成本效益

```python
# backend/app/cache.py
from functools import lru_cache
import redis
import hashlib
import pickle

class LLMCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _make_key(self, prompt: str, model: str) -> str:
        content = f"{model}:{prompt}"
        return f"llm:cache:{hashlib.sha256(content.encode()).hexdigest()}"

    async def get(self, prompt: str, model: str) -> str | None:
        key = self._make_key(prompt, model)
        cached = await self.redis.get(key)
        if cached:
            return pickle.loads(cached)
        return None

    async def set(self, prompt: str, model: str, response: str, ttl: int = 3600):
        key = self._make_key(prompt, model)
        await self.redis.setex(key, ttl, pickle.dumps(response))

# Usage
llm_cache = LLMCache(redis.Redis(host='localhost'))

async def call_llm_with_cache(prompt: str, model: str):
    # Check cache first
    cached_response = await llm_cache.get(prompt, model)
    if cached_response:
        logger.info("Cache hit", extra={"prompt_hash": prompt[:50]})
        return cached_response

    # Call LLM
    response = await llm_service.generate(prompt, model)

    # Cache result
    await llm_cache.set(prompt, model, response)
    return response
```

**快取策略**:
- **L1 (In-memory)**: 常用提示快取 (LRU, 100 條)
- **L2 (Redis)**: LLM 響應快取 (TTL 1 小時)
- **L3 (Disk)**: 模板歸納結果快取 (永久)

**效益**:
- 💰 減少 LLM API 成本 (30-50%)
- ⚡ 提升響應速度 (10x 對常見請求)
- 🌍 減少碳足跡

### 5.4 錯誤處理和重試機制 ⭐⭐⭐⭐⭐

**當前狀態**: Agent 類有基本重試，但不夠細緻

**建議**: 實施全面的錯誤處理和重試策略

```python
# backend/app/retry.py
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import httpx
import openai

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, openai.APIError))
)
async def call_llm_with_retry(prompt: str):
    try:
        return await llm_service.generate(prompt)
    except openai.RateLimitError as e:
        # 速率限制 - 使用指數退避
        logger.warning(f"Rate limit hit: {e}")
        raise
    except openai.APIConnectionError as e:
        # 網路錯誤 - 可重試
        logger.error(f"API connection error: {e}")
        raise
    except openai.AuthenticationError as e:
        # 認證錯誤 - 不可重試
        logger.critical(f"Authentication failed: {e}")
        raise FatalError("LLM authentication failed") from e

# 錯誤恢復
class GenerationError(Exception):
    """生成過程錯誤"""
    pass

async def generate_with_recovery(request):
    try:
        return await ppt_service.generate(request)
    except GenerationError as e:
        logger.error(f"Generation failed: {e}")
        # 嘗試降級策略
        return await ppt_service.generate_simple(request)
    except Exception as e:
        logger.exception("Unexpected error")
        # 通知監控系統
        await alert_system.notify(f"Critical error: {e}")
        raise
```

---

## 6. 效能分析與優化

### 6.1 效能瓶頸識別 ⚠️

**文件缺少**: 效能基準和 SLA 目標

**預估瓶頸**:

1. **LLM API 延遲** (最大瓶頸)
   - 每個幻燈片需要 3-5 次 LLM 調用
   - 10 頁簡報 = 30-50 次調用
   - 每次調用 2-5 秒 (Ollama local) or 1-3 秒 (OpenAI API)
   - **總時間**: 60-250 秒 (無快取、無並行)

2. **圖像處理**
   - ViT 嵌入計算 (如果啟用): ~500ms per image
   - 模板歸納: 一次性成本，可快取

3. **PPTX 構建**
   - python-pptx 同步 I/O: ~2-5 秒 for 10-page presentation

**優化策略**:

```python
# 1. 並行化 (已實施)
async with asyncio.TaskGroup() as tg:
    for slide in slides:
        tg.create_task(generate_slide(slide))

# 2. 批次處理 (AsyncLLM 已支持)
llm = AsyncLLM(use_batch=True)
responses = await llm.batch_generate([prompt1, prompt2, ...])

# 3. 快取 (建議添加)
@cached(ttl=3600)
async def select_layout(content_schema):
    return await llm.generate(...)

# 4. 預熱 (提前載入模型)
async def startup_event():
    # 預熱 Ollama 模型
    await llm_service.generate("Hello", max_tokens=1)
    logger.info("LLM warmed up")
```

### 6.2 建議效能目標 📊

| 指標 | 目標 | 測量方式 |
|------|------|---------|
| **10 頁簡報生成時間** | < 2 分鐘 (Ollama) | P95 latency |
| **API 響應時間** | < 500ms (啟動) | P99 latency |
| **並發用戶支持** | 5+ users | Load testing |
| **記憶體使用** | < 2GB per instance | RSS monitoring |
| **CPU 使用率** | < 80% under load | System metrics |

---

## 7. 安全性評估

### 7.1 識別的安全考量 ⚠️

**文件缺少**: 安全性分析和威脅模型

**潛在威脅**:

1. **提示注入攻擊** 🔴
   - 用戶輸入操控 LLM 行為
   - 緩解: 輸入清理 + 提示隔離 (見 4.2.4)

2. **路徑遍歷攻擊** 🟡
   - 惡意模板路徑: `../../etc/passwd`
   - 緩解:
     ```python
     from pathlib import Path

     def safe_path(base: Path, user_input: str) -> Path:
         full_path = (base / user_input).resolve()
         if not full_path.is_relative_to(base):
             raise ValueError("Path traversal detected")
         return full_path
     ```

3. **拒絕服務 (DoS)** 🟡
   - 大量並發請求耗盡資源
   - 緩解: 速率限制 + 資源配額
     ```python
     from slowapi import Limiter
     from slowapi.util import get_remote_address

     limiter = Limiter(key_func=get_remote_address)

     @app.post("/api/presentations/generate")
     @limiter.limit("5/minute")
     async def generate_presentation(request: Request):
         ...
     ```

4. **憑證洩漏** 🔴
   - API keys 硬編碼或記錄到日誌
   - 緩解: 使用環境變數 + 秘密管理
     ```python
     # ❌ BAD
     OPENAI_API_KEY = "sk-..."

     # ✅ GOOD
     from pydantic_settings import BaseSettings

     class Settings(BaseSettings):
         openai_api_key: str
         model_config = SettingsConfigDict(env_file=".env")
     ```

5. **未經驗證的文件上傳** 🟡
   - 惡意文件 (病毒、超大文件)
   - 緩解:
     ```python
     MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
     ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}

     async def validate_upload(file: UploadFile):
         # 檢查大小
         content = await file.read()
         if len(content) > MAX_FILE_SIZE:
             raise ValueError("File too large")

         # 檢查副檔名
         ext = Path(file.filename).suffix.lower()
         if ext not in ALLOWED_EXTENSIONS:
             raise ValueError("Invalid file type")

         # 病毒掃描 (可選)
         # await virus_scanner.scan(content)
     ```

### 7.2 建議安全措施 ✅

```python
# backend/app/security.py
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key

# 使用
@app.post("/api/presentations/generate")
async def generate_presentation(
    request: GenerationRequest,
    _: str = Depends(verify_api_key)
):
    ...
```

---

## 8. 最終建議與行動計劃

### 8.1 總體評價 ⭐⭐⭐⭐⭐ 9/10

這份重構計劃是**高質量的技術分析文件**，展示了:
- ✅ 深入的源系統理解 (PPTAgent + DeepPresenter)
- ✅ 清晰的架構設計和選項分析
- ✅ 務實的風險識別和緩解策略
- ✅ 現代技術堆疊選擇
- ✅ 階段式實施路線圖

**強烈建議執行此重構計劃**。

### 8.2 實施建議 🎯

#### Phase 0: 準備階段 (Week 0) 📋

**添加此階段到實施計劃**:

```markdown
### Phase 0: Preparation (Week 0)

1. **Environment Setup**
   - 安裝 Python 3.11+, Node.js 18+
   - 設置 Ollama 並下載模型 (qwen2.5:7b, llama3:8b)
   - 配置開發環境 (VS Code, extensions)

2. **Dependency Analysis**
   - 審計 pptagent 依賴 (特別是 pptagent-pptx)
   - 測試 pptagent-pptx 與目標模板兼容性
   - 確認 python-pptx fallback 可行性

3. **Test Data Preparation**
   - 準備 5+ 測試模板 (不同風格、語言)
   - 準備 10+ 測試內容 (不同長度、格式)
   - 建立質量評估標準 (人工評審 checklist)

4. **Baseline Measurement**
   - 測量 Presenton 當前效能
   - 記錄生成質量範例
   - 建立比較基準

5. **Team Alignment**
   - 技術設計評審
   - 角色和責任分配
   - 溝通計劃 (daily standups, weekly demos)
```

#### Phase 1-4: 按文件建議執行 ✅

保持文件中的 4 階段結構，但添加:

1. **每個階段結束時的 Demo**
   - Week 1: 核心模組 demo (CLI 測試)
   - Week 2: API demo (Postman/curl 測試)
   - Week 3: UI demo (內部用戶試用)
   - Week 4: 完整系統 demo (stakeholder 展示)

2. **質量門檻**
   - 單元測試覆蓋率 ≥ 80%
   - E2E 測試通過率 100%
   - 效能達標 (10 頁 < 2 分鐘)
   - 無 P0/P1 bug

3. **回滾準備**
   - Week 2 結束: Presenton 保持運行
   - Week 3-4: 並行運行新舊系統
   - Week 5: 觀察期 (可快速回滾)
   - Week 6: Presenton 下線

### 8.3 優先改進清單 📝

**立即實施** (Week 1-2):
1. ✅ 添加 Phase 0 準備階段
2. ✅ 設計詳細測試計劃
3. ✅ 實施配置管理 (Pydantic Settings)
4. ✅ 添加基本錯誤處理和重試

**短期添加** (Week 3-4):
5. ✅ 實施 LLM 響應快取 (Redis)
6. ✅ 添加速率限制和成本控制
7. ✅ 設置基本監控 (health checks, metrics)
8. ✅ 實施輸入驗證和清理

**中期優化** (Week 5-6):
9. ✅ 整合 OpenTelemetry 追蹤
10. ✅ 實施記憶體監控和限制
11. ✅ 添加並發控制機制
12. ✅ 優化提示工程 (針對目標模型)

**長期考慮** (Post-MVP):
13. 🔄 評估 LangChain 整合
14. 🔄 實施多租戶支持
15. 🔄 添加幻燈片編輯功能
16. 🔄 PWA 支持 (離線使用)

### 8.4 成功標準 🎯

**技術標準**:
- ✅ 核心功能等同或優於 Presenton
- ✅ 效能: 10 頁簡報 < 2 分鐘 (P95)
- ✅ 穩定性: 99% 生成成功率
- ✅ 質量: 90% 用戶滿意度 (survey)

**業務標準**:
- ✅ 原生 ARM64 支持 (無 Presenton 依賴)
- ✅ 實時進度回饋 (SSE)
- ✅ 多 LLM 提供者支持
- ✅ 可維護和可擴展的代碼庫

**用戶體驗標準**:
- ✅ 現代、響應式 UI
- ✅ < 5 步驟完成簡報生成
- ✅ 移動設備可用
- ✅ 無障礙支持 (WCAG 2.1 AA)

---

## 9. 結論

### 9.1 文件優勢總結 🌟

1. **深度技術分析** - 全面理解 PPTAgent 和 DeepPresenter 內部運作
2. **清晰架構設計** - 三個選項 (A/B/C) 平衡風險和功能
3. **務實實施路徑** - 階段式推進，降低風險
4. **現代技術堆疊** - React + FastAPI + Tailwind 符合業界標準
5. **風險意識** - 識別主要技術風險並提供緩解策略

### 9.2 關鍵差距 ⚠️

需要補充的領域:
1. **測試策略** - 詳細的單元/整合/E2E 測試計劃
2. **效能基準** - 明確的 SLA 和效能目標
3. **安全分析** - 威脅模型和安全措施
4. **監控計劃** - 可觀測性和維運準備
5. **數據遷移** - 現有數據如何遷移到新系統
6. **回滾策略** - 失敗時的恢復計劃

### 9.3 最終建議 ✅

**執行此重構計劃**，但需要:

1. **補充缺失的計劃** (測試、監控、安全)
2. **添加 Phase 0 準備階段**
3. **保留 20% 時間緩衝** (4-5 週而非 3-4 週)
4. **實施質量門檻** (每階段 demo + 測試通過)
5. **維護並行運行期** (新舊系統同時運行 2-3 週)

**預期成果**:
- ✅ 現代化、可維護的簡報生成系統
- ✅ 優越的用戶體驗 (實時回饋、響應式 UI)
- ✅ 技術債務清理 (移除 Presenton 黑盒)
- ✅ 原生 ARM64 支持和更好的效能
- ✅ 未來擴展能力 (Option B/C 功能)

---

## 附錄 A: 快速參考

### 技術堆疊總覽

```
┌─────────────────────────────────────────────────┐
│                  Frontend                       │
│  React 18 + TypeScript + Vite                   │
│  Tailwind CSS + shadcn/ui + Framer Motion       │
└──────────────────┬──────────────────────────────┘
                   │ REST API + SSE
┌──────────────────▼──────────────────────────────┐
│                  Backend                        │
│  FastAPI + asyncio + Pydantic                   │
│                                                 │
│  ┌────────────────────────────────────────────┐ │
│  │      PPTAgent Core (Transplanted)          │ │
│  │  agent.py │ apis.py │ pptgen.py │induct.py│ │
│  └────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│              LLM Providers                      │
│  Ollama (local) OR OpenAI/Anthropic (cloud)     │
└─────────────────────────────────────────────────┘
```

### 關鍵檔案映射 (Option A)

```
pptagent/agent.py      → backend/app/pptagent_core/agent.py
pptagent/apis.py       → backend/app/pptagent_core/apis.py
pptagent/induct.py     → backend/app/pptagent_core/induct.py
pptagent/llms.py       → backend/app/pptagent_core/llms.py
pptagent/pptgen.py     → backend/app/pptagent_core/pptgen.py
pptagent/roles/*.yaml  → backend/app/pptagent_core/roles/
```

### 時間線快速查看

```
Week 0:  準備階段 (新增)
Week 1:  核心移植 + LLM Adapter
Week 2:  服務層 + API + SSE
Week 3:  React UI + 組件開發
Week 4:  測試 + 部署 + Presenton 移除
Week 5+: 觀察期 + Option B 評估
```

---

**文件版本**: v1.0
**生成時間**: 2025-12-30
**分析工具**: Claude Sonnet 4.5 + Sequential Thinking MCP
**下一步**: 團隊評審 → 技術設計評審 → Phase 0 執行
