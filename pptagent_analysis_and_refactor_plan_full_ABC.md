# PPTAgent + DeepPresenter Analysis & TeacherAssist Refactoring Plan

## Executive Summary

This document provides a comprehensive analysis of PPTAgent v2 and DeepPresenter's architecture, along with a detailed refactoring plan to replace TeacherAssist's deprecated Presenton engine.

**Key Discovery**: PPTAgent is wrapped by **DeepPresenter**, a higher-level agentic orchestration system that uses MCP (Model Context Protocol) for tool management and supports multiple generation modes:
- **Template-based** (PPTAgent) - Uses reference PPTX templates
- **Freeform** (Design Agent) - Generates HTML/CSS slides with visual inspection loop

---

## Part 0: DeepPresenter Orchestration Layer

### 0.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DeepPresenter System                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Agent Orchestration                          │   │
│  │                                                                     │   │
│  │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │   │
│  │   │   Research   │   │    Design    │   │   PPTAgent   │           │   │
│  │   │    Agent     │   │    Agent     │   │    Agent     │           │   │
│  │   │              │   │              │   │              │           │   │
│  │   │ Deep content │   │  HTML/CSS    │   │  Template-   │           │   │
│  │   │ research &   │   │  freeform    │   │  based PPTX  │           │   │
│  │   │ manuscript   │   │  slides      │   │  generation  │           │   │
│  │   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘           │   │
│  │          │                  │                  │                    │   │
│  │          └──────────────────┼──────────────────┘                    │   │
│  │                             │                                       │   │
│  │                             ▼                                       │   │
│  │                    ┌──────────────────┐                             │   │
│  │                    │    AgentEnv      │                             │   │
│  │                    │  (MCP Manager)   │                             │   │
│  │                    └────────┬─────────┘                             │   │
│  └─────────────────────────────│───────────────────────────────────────┘   │
│                                │                                           │
│  ┌─────────────────────────────│───────────────────────────────────────┐   │
│  │                    MCP Tool Servers                                 │   │
│  │                             │                                       │   │
│  │   ┌─────────────────────────┼─────────────────────────────────┐     │   │
│  │   │                         ▼                                 │     │   │
│  │   │  ┌────────────┐  ┌────────────┐  ┌────────────┐          │     │   │
│  │   │  │ desktop_   │  │  pptagent  │  │deeppresenter│          │     │   │
│  │   │  │ commander  │  │   server   │  │   tools    │          │     │   │
│  │   │  │            │  │            │  │            │          │     │   │
│  │   │  │• execute_  │  │• generate_ │  │• search_web│          │     │   │
│  │   │  │  command   │  │  slide     │  │• fetch_url │          │     │   │
│  │   │  │• read_file │  │• set_slide_│  │• image_gen │          │     │   │
│  │   │  │• write_file│  │  template  │  │• research  │          │     │   │
│  │   │  └────────────┘  └────────────┘  └────────────┘          │     │   │
│  │   └───────────────────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         LLM Providers                               │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │   │
│  │   │  OpenAI    │  │  Anthropic │  │   Gemini   │  │   Ollama   │   │   │
│  │   └────────────┘  └────────────┘  └────────────┘  └────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 0.2 Agent Base Class (`agents/agent.py`)

```python
# Context budget management messages
HALF_NOTICE_MESSAGE = ChatMessage(
    role=Role.USER,
    content="NOTICE: You have used about half of your working budget. Now focused on the core task and skipping unnecessary steps or explorations.",
)
URGENT_NOTICE_MESSAGE = ChatMessage(
    role=Role.USER,
    content="URGENT: Working budget nearly exhausted. You must finish the core task and call `finalize` now, or your work will fail. Skip extras like inspection and validation.",
)

class Agent:
    def __init__(
        self,
        config: DeepPresenterConfig,
        agent_env: AgentEnv,
        workspace: Path,
        config_file: str | None = None,
        language: Literal["zh", "en"] = "zh",
    ):
        self.name = self.__class__.__name__
        self.cost = Cost()
        self.context_length = 0
        self.context_warning = 0  # Tracks warning state (0, 1, 2)
        
        # Load YAML role config
        config_file = config_file or PACKAGE_DIR / "roles" / f"{self.name}.yaml"
        role_config = RoleConfig(**yaml.safe_load(open(config_file)))
        
        self.llm: LLM = config[role_config.use_model]
        self.prompt: Template = Template(role_config.instruction, undefined=StrictUndefined)
        
        # Disable inspect_slide for non-multimodal models
        if not self.llm.is_multimodal:
            if "inspect_slide" not in role_config.exclude_tools:
                role_config.exclude_tools.append("inspect_slide")
        
        # Build tool list from server configs
        self.tools = []
        if role_config.include_tool_servers == "all":
            role_config.include_tool_servers = list(agent_env._server_tools)
        
        for server in role_config.include_tool_servers:
            if server not in role_config.exclude_tool_servers:
                for tool in agent_env._server_tools[server]:
                    if tool not in role_config.exclude_tools:
                        self.tools.append(agent_env._tools_dict[tool])
        
        # Add explicitly included tools
        for tool_name in role_config.include_tools:
            self.tools.append(agent_env._tools_dict[tool_name])

    async def action(self, **chat_kwargs) -> ChatMessage:
        """Tool calling interface with context budget management"""
        if len(self.chat_history) == 1:
            # First call - render instruction template
            self.chat_history.append(ChatMessage(
                role=Role.USER,
                content=self.prompt.render(**chat_kwargs),
            ))
        
        # Context budget enforcement
        if self.context_length > CONTEXT_LENGTH_LIMIT:
            raise RuntimeError(f"{self.name} exceeded context budget: {self.context_length}")
        elif self.context_warning == 0 and self.context_length > CONTEXT_LENGTH_LIMIT * 0.5:
            self.context_warning = 1
            self.chat_history.append(HALF_NOTICE_MESSAGE)
        elif self.context_warning == 1 and self.context_length > CONTEXT_LENGTH_LIMIT * 0.8:
            self.context_warning = 2
            self.chat_history.append(URGENT_NOTICE_MESSAGE)
        
        response = await self.llm.run(messages=self.chat_history, tools=self.tools)
        if response.usage:
            self.cost += response.usage
            self.context_length = response.usage.total_tokens
        
        agent_message = response.choices[0].message
        self.chat_history.append(ChatMessage(
            role=agent_message.role,
            content=agent_message.content,
            tool_calls=agent_message.tool_calls,
        ))
        return self.chat_history[-1]

    async def execute(self, tool_calls: list[ToolCall], limit_len: bool = False) -> str | list[ChatMessage]:
        """Execute tool calls via MCP, handle finalize specially"""
        coros = []
        observations = []
        finish_id = None
        outcome = None
        
        for t in tool_calls:
            arguments = json.loads(t.function.arguments) if t.function.arguments else None
            if t.function.name == "finalize":
                arguments["agent_name"] = self.name  # Inject agent name for validation
                finish_id = t.id
                outcome = arguments["outcome"]
            coros.append(self.agent_env.tool_execute(t, limit_len))
        
        observations = await asyncio.gather(*coros)
        self.chat_history.extend(observations)
        
        # Check if finalize succeeded
        if finish_id:
            for obs in observations:
                if obs.tool_call_id == finish_id and obs.text == outcome:
                    return obs.text  # Return outcome path, ending the loop
        
        return observations

    @abstractmethod
    async def loop(self, req: InputRequest) -> AsyncGenerator[str | ChatMessage, None]:
        """Main agent loop - yields messages until finalize returns outcome"""
        pass
```

### 0.3 Concrete Agent Implementations

**PPTAgent Agent** (`agents/pptagent.py`):
```python
class PPTAgent(Agent):
    async def loop(self, req: InputRequest, markdown_file: str):
        while True:
            agent_message = await self.action(
                markdown_file=markdown_file, 
                prompt=req.pptagent_prompt
            )
            yield agent_message
            outcome = await self.execute(agent_message.tool_calls)
            if isinstance(outcome, list):
                for item in outcome:
                    yield item
            else:
                yield outcome
                break  # finalize returned outcome path
```

**Research Agent** (`agents/research.py`):
```python
class Research(Agent):
    async def loop(self, req: InputRequest):
        while True:
            agent_message = await self.action(
                prompt=req.deepresearch_prompt,
                attachments=req.attachments,
            )
            yield agent_message
            # limit_len=True truncates long web/document content
            outcome = await self.execute(agent_message.tool_calls, limit_len=True)
            if isinstance(outcome, list):
                for item in outcome:
                    yield item
            else:
                yield outcome
                break
```

**Design Agent** (`agents/design.py`):
```python
class Design(Agent):
    async def loop(self, req: InputRequest, markdown_file: str):
        while True:
            agent_message = await self.action(
                markdown_file=markdown_file, 
                prompt=req.webagent_prompt
            )
            yield agent_message
            outcome = await self.execute(agent_message.tool_calls)
            if isinstance(outcome, list):
                for item in outcome:
                    yield item
            else:
                break
        yield outcome
```

### 0.4 Agent Role Configurations

**Research Agent** (`Research.yaml`):
```yaml
system:
  zh: |
    你是一位专业的幻灯片内容专家，能够利用多种工具进行深度信息检索...
    <任务说明>
    1. 系统而全面地开展信息研究，构建具有故事张力的幻灯片框架
    2. 以信息价值与内容逻辑为导向组织视觉素材
    3. 撰写 Markdown 格式文稿（使用`---`分页）
    4. 借助`inspect_manuscript`逐页审查
    5. 调用`finalize`返回文稿路径
    </任务说明>
use_model: research_agent
include_tool_servers: all
exclude_tool_servers: [pptagent]
exclude_tools: [inspect_slide, markdown_table_to_image]
```

**Design Agent** (`Design.yaml`):
```yaml
system:
  zh: |
    你是一位专业的幻灯片视觉设计专家，擅长使用 HTML/CSS 进行固定版式设计
    <任务说明>
    1. 制定"幻灯片母版"式的设计方案，保存至 design_plan.md
    2. 逐页生成HTML文件，保存到 slides/slide_{页码:02d}.html
    3. 生成后必须调用 `inspect_slide` 获取视觉反馈，进行像素级审查
    4. 调用 `finalize` 返回幻灯片文件夹
    </任务说明>
    <风格说明>
    1. 平面设计原则：禁止网页交互行为
    2. 强制固定尺寸：body/html 锁定为 1280x720px, overflow: hidden
    3. 视觉反馈闭环：必须依据 inspect_slide 结果动态调整 CSS
    </风格说明>
use_model: design_agent
include_tool_servers: [desktop_commander]
include_tools: [inspect_slide, thinking, finalize]
```

**PPTAgent Agent** (`PPTAgent.yaml`):
```yaml
system:
  zh: |
    你是一位专业的幻灯片制作专家，根据Markdown内容调用工具生成幻灯片
    <任务说明>
    1. 理解每页的 Markdown 内容（`---` 分隔）
    2. 交互式调用工具生成忠实还原的幻灯片
    3. 使用`finalize`工具返回生成的幻灯片
    </任务说明>
use_model: agent
include_tool_servers: all
exclude_tools: [todo_create, todo_update, todo_list, get_markdown_overview]
```

### 0.5 MCP Tool Server (`tools/server.py`)

```python
from fastmcp import FastMCP
mcp = FastMCP(name="DeepPresenter Tools")  # appcore.py

# server.py - Dynamic tool loading based on API keys
if __name__ == "__main__":
    import any2markdown   # convert_to_markdown
    import fetch          # fetch_url
    import research       # search_papers, get_paper_authors, get_scholar_details
    import richfile       # download_file, inspect_slide, inspect_manuscript
    import task           # thinking, finalize, todo_*
    import tool_agents    # image_generation, image_caption, document_analyze

    if os.getenv("TAVILY_API_KEY"):
        import tavily_search    # search_web, search_images
    elif os.getenv("FIRECRAWL_API_KEY"):
        import firecrawl_search # search_web, search_images
    
    mcp.run(show_banner=False)
```

### 0.6 Key MCP Tool Implementations

| Tool | Module | Purpose |
|------|--------|---------|
| `search_web` | tavily/firecrawl | Web search with time filtering (month/year) |
| `search_images` | tavily/firecrawl | Image search with descriptions |
| `fetch_url` | fetch.py | Web page → markdown via Playwright + trafilatura |
| `search_papers` | research.py | arXiv paper search with field prefixes (ti:, au:, abs:) |
| `get_paper_authors` | research.py | Semantic Scholar author lookup |
| `get_scholar_details` | research.py | Scholar profile with papers, citations |
| `convert_to_markdown` | any2markdown.py | PDF/docx → markdown (uses markitdown, MinerU) |
| `download_file` | richfile.py | Download files with retry logic |
| `inspect_slide` | richfile.py | HTML → image for visual feedback loop |
| `inspect_manuscript` | richfile.py | Validate markdown structure, check images |
| `markdown_table_to_image` | richfile.py | Table → image for PPTX embedding |
| `image_generation` | tool_agents.py | Text-to-image via configurable API |
| `image_caption` | tool_agents.py | Image → type + description |
| `document_analyze` | tool_agents.py | Long document → structured summary |
| `thinking` | task.py | Explicit reasoning step (no-op, just logs) |
| `finalize` | task.py | Terminate loop with agent-specific validation |
| `todo_create/update/list` | task.py | Task management via CSV file |

**Key Tool Implementations:**

```python
# task.py - finalize with agent-specific validation
@mcp.tool(exclude_args=["agent_name"])
def finalize(outcome: str, agent_name: str | None = None) -> str:
    path = Path(outcome)
    if not path.exists():
        return f"Outcome file {outcome} does not exist"
    
    if agent_name == "Research":
        if not (path.is_file() and path.suffix == ".md"):
            return "Outcome file should be a markdown file"
        # Validate all image paths exist, convert to absolute paths
        # Check no external image links
        
    elif agent_name == "PPTAgent":
        if not (path.is_file() and path.suffix == ".pptx"):
            return "Outcome file should be a pptx file"
        if len(Presentation(str(path)).slides) <= 0:
            return "PPTX file should contain at least one slide"
            
    elif agent_name == "Design":
        if not (path.is_dir() and path.stem.startswith("slide")):
            return "Outcome directory should start with 'slide'"
        html_files = list(path.glob("*.html"))
        if not all(f.stem.startswith("slide_") for f in html_files):
            return "All HTML files should start with 'slide_'"
    
    return outcome  # Success - return path to end agent loop

# richfile.py - inspect_slide for visual feedback
@mcp.tool()
async def inspect_slide(
    html_file: str, 
    aspect_ratio: Literal["widescreen", "normal", "A1"] = "widescreen"
) -> ImageContent | str:
    """Read the HTML file as an image for visual inspection."""
    async with PlaywrightConverter() as converter:
        await converter.page.goto(f"file://{html_file}", wait_until="domcontentloaded")
        slide_image_folder = await converter.convert_to_pdf([html_file], ...)
    
    with open(slide_image_folder / "slide_01.jpg", "rb") as f:
        return ImageContent(
            type="image",
            data=f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}",
            mimeType="image/jpeg",
        )

# fetch.py - Web fetching with Playwright
@mcp.tool()
async def fetch_url(url: str, body_only: bool = True) -> str:
    """Fetch web page content as markdown."""
    async with PlaywrightConverter() as converter:
        await converter.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        html = await converter.page.content()
    
    markdown = markdownify.markdownify(html, heading_style=markdownify.ATX)
    if body_only:
        return extract(html, output_format="markdown", with_metadata=True, ...)
    return markdown

# any2markdown.py - Document conversion
@mcp.tool()
async def convert_to_markdown(file_path: str, output_folder: str) -> dict | str:
    """Convert PDF/docx to markdown with images extracted."""
    if file_path.lower().endswith(".pdf") and MINERU_API_KEY:
        # Use MinerU VLM for high-quality PDF parsing
        await parse_pdf(file_path, output_folder, MINERU_API_KEY, model_version="vlm")
    else:
        # Use markitdown for other formats
        result = MarkItDown().convert_local(file_path, keep_data_uris=True)
        markdown = parse_base64_images(result.text_content, output_folder / "images")
    
    return {"success": True, "markdown_file": str(markdown_file), "images": ...}
```

### 0.7 AgentEnv - MCP Connection Manager (`agents/env.py`)

> **Note**: The original AgentEnv uses Docker for workspace isolation. For TeacherAssist, this is **not required** - workspaces can be simple directories.

```python
class AgentEnv:
    def __init__(
        self,
        workspace: Path,
        hci_enable: bool = False,
        config_file: str = GLOBAL_CONFIG.mcp_config_file,
    ):
        self.workspace = Path(workspace).absolute()
        self.config: list[MCPServer] = [MCPServer(**s) for s in json.load(open(config_file))]
        
        # Pass workspace-specific variables to MCP client
        self.client = MCPClient(
            WORKSPACE=str(self.workspace),
            WORKSPACE_ID=self.workspace.stem,
        )
        self.cutoff_len = TOOL_CUTOFF_LEN
        
        # Tool registry
        self._tools_dict: dict[str, dict] = {}        # tool_name → OpenAI tool spec
        self._server_tools = defaultdict(list)         # server_name → [tool_names]
        self._tool_to_server = {}                      # tool_name → server_name
        self.tool_history: list[tuple[ToolCall, ChatMessage]] = []

    async def tool_execute(self, tool_call: ToolCall, limit_len: bool = False) -> ChatMessage:
        """Execute a tool call and return observation message"""
        try:
            server_id = self._tool_to_server[tool_call.function.name]
            arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else None
            result = await self.client.tool_execute(server_id, tool_call.function.name, arguments)
        except KeyError:
            result = CallToolResult(content=[TextContent(text=f"Tool not found", type="text")], isError=True)
        except TimeoutError:
            result = CallToolResult(content=[TextContent(text=f"Execution timed out", type="text")], isError=True)
        
        # Process result content blocks
        content = []
        for block in result.content:
            if block.type == "text":
                text = block.text
                # Truncate overlong content and save to file
                if limit_len and len(text) > self.cutoff_len:
                    local_file = self.workspace / f"{tool_call.function.name}_{uuid.uuid4().hex[:8]}.txt"
                    local_file.write_text(text)
                    text = text[:self.cutoff_len] + f"\n[Content truncated, full content at: {local_file}]"
                content.append({"type": "text", "text": text})
            elif block.type == "image":
                content.append({"type": "image_url", "image_url": {"url": block.data}})
        
        return ChatMessage(role=Role.TOOL, content=content, tool_call_id=tool_call.id, is_error=result.isError)

    async def __aenter__(self):
        """Connect to all MCP servers and build tool registry"""
        # NOTE: Original code has Docker container cleanup here - NOT NEEDED for TeacherAssist
        # Simply create workspace directory
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Connect to all servers in parallel
        connect_tasks = []
        for server in self.config:
            connect_tasks.append(self.client.connect_server(server.name, server))
        await asyncio.gather(*connect_tasks)
        
        # Build tool registry from connected servers
        for server in self.config:
            tools_dict = await self.client.list_tools(server.name)
            for tool_name, tool_info in tools_dict.items():
                if (server.keep_tools is None or tool_name in server.keep_tools) \
                   and tool_name not in server.exclude_tools:
                    self._tools_dict[tool_name] = {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": tool_info.description,
                            "parameters": tool_info.inputSchema,
                        },
                    }
                    self._server_tools[server.name].append(tool_name)
                    self._tool_to_server[tool_name] = server.name
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up MCP connections and save tool history"""
        await self.client.cleanup()
        # Save tool call history to JSONL
        history_dir = self.workspace / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        with open(history_dir / "tool_history.jsonl", "a") as f:
            for tool_call, msg in self.tool_history:
                f.write(json.dumps([tool_call.model_dump(), msg.text]) + "\n")
```

### 0.8 Workflow Patterns

**Mode 1: Research → PPTAgent (Full Pipeline)**
```
User Topic/Request
        ↓
┌───────────────────┐
│  Research Agent   │ ← Uses: search_web, fetch_url, search_papers,
│                   │   download_file, image_generation, document_analyze
│  Output: manuscript.md with images
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  PPTAgent Agent   │ ← Uses: PPTAgent MCP tools (generate_slide, etc.)
│                   │
│  Output: presentation.pptx
└───────────────────┘
```

**Mode 2: Research → Design (HTML Slides)**
```
User Topic/Request
        ↓
┌───────────────────┐
│  Research Agent   │ ← Deep content research
│                   │
│  Output: manuscript.md
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  Design Agent     │ ← Uses: desktop_commander (file ops),
│                   │   inspect_slide (visual feedback loop)
│  Output: slides/*.html
└───────────────────┘
```

**Mode 3: Direct PPTAgent (Manuscript Provided)**
```
User-provided manuscript.md
        ↓
┌───────────────────┐
│  PPTAgent Agent   │ ← Template-based generation
│                   │
│  Output: presentation.pptx
└───────────────────┘
```

**Key Insight for TeacherAssist**: For MVP, Mode 3 is simplest - user provides content, PPTAgent generates slides. Mode 1 can be added later for "topic → slides" workflow.

### 0.9 DeepPresenter Dependencies

**Core Dependencies** (from tools):
```txt
# MCP Framework
fastmcp                    # FastMCP server framework

# Web & Content
playwright                 # Browser automation for fetch_url, inspect_slide
httpx                      # Async HTTP client
markdownify                # HTML → Markdown
trafilatura                # Content extraction
markitdown                 # Document → Markdown (docx, etc.)
fake-useragent             # User agent rotation

# Search APIs (one of)
tavily                     # Tavily search API
firecrawl                  # Firecrawl search API

# Academic Research
arxiv                      # arXiv API
semanticscholar            # Semantic Scholar API

# Image Processing
pillow                     # Image handling

# Document Processing
python-pptx                # PPTX validation in finalize
mistune                    # Markdown → HTML for tables

# Utilities
filelock                   # CSV file locking for todos
```

**LLM Configuration** (from config):
```python
class DeepPresenterConfig:
    # Different models for different purposes
    agent: LLM              # General agent tasks (PPTAgent)
    design_agent: LLM       # Design agent (needs vision)
    research_agent: LLM     # Research agent (long context)
    vision_model: LLM       # Image captioning
    t2i_model: T2IModel     # Text-to-image generation
    long_context_model: LLM # Document analysis
```

---

## Part 1: PPTAgent Architecture Deep Dive

### 1.1 Core Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PPTAgent Text-to-PPTX Pipeline                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │  Source   │───▶│   Document   │───▶│    Slide     │             │
│  │ Document  │    │   Parser     │    │  Inducter    │             │
│  └───────────┘    └──────────────┘    └──────┬───────┘             │
│       │                                      │                      │
│       │                                      ▼                      │
│       │                              ┌──────────────┐               │
│       │                              │   Layout     │               │
│       │                              │  Induction   │               │
│       │                              │  (Schema)    │               │
│       │                              └──────┬───────┘               │
│       │                                      │                      │
│       ▼                                      ▼                      │
│  ┌───────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │  PPTGen   │◀───│   Outline    │◀───│   Content    │             │
│  │  Engine   │    │  Generator   │    │  Organizer   │             │
│  └─────┬─────┘    └──────────────┘    └──────────────┘             │
│        │                                                            │
│        ├─────────────────────────────────────────────┐              │
│        ▼                                             ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   Layout     │───▶│    Editor    │───▶│    Coder     │          │
│  │  Selector    │    │    Agent     │    │    Agent     │          │
│  └──────────────┘    └──────────────┘    └──────┬───────┘          │
│                                                  │                  │
│                                                  ▼                  │
│                                          ┌──────────────┐          │
│                                          │  Presentation │          │
│                                          │    Builder    │          │
│                                          │ (pptagent_pptx)│          │
│                                          └──────┬───────┘          │
│                                                  │                  │
│                                                  ▼                  │
│                                          ┌──────────────┐          │
│                                          │  Output PPTX │          │
│                                          └──────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Modules Analysis

#### 1.2.1 LLM Layer (`llms.py`)

**Classes:**
- `LLM`: Synchronous OpenAI-compatible wrapper
- `AsyncLLM`: Async version with batch support
- `ThinkMode`: Enum for reasoning modes (think/not_think)

**Key Features:**
```python
@dataclass
class AsyncLLM(LLM):
    use_batch: bool = False
    
    async def __call__(
        self,
        content: str,
        images: str | list[str] | None = None,
        system_message: str | None = None,
        history: list | None = None,
        return_json: bool = False,
        response_format: BaseModel | None = None,  # Pydantic structured output
        **client_kwargs,
    ) -> str | dict | tuple
```

**Integration Points:**
- Uses standard OpenAI API format
- Supports vision models (base64 image encoding)
- Compatible with Ollama, OpenAI, and other OpenAI-compatible APIs

#### 1.2.2 Agent System (`agent.py`)

**Agent Configuration (YAML-based):**
```yaml
# roles/*.yaml structure
use_model: language  # or "vision"
system_prompt: "..."
template: "{{ jinja2_template }}"
jinja_args: [arg1, arg2]
return_json: true
run_args:
  temperature: 0.7
```

**Agent Roles:**
- `schema_extractor`: Extracts content schema from slides
- `content_organizer`: Organizes content into key points
- `layout_selector`: Selects appropriate layout for content
- `editor`: Generates slide content matching schema
- `coder`: Generates API calls to edit slides

**Retry Mechanism:**
```python
async def retry(
    self,
    feedback: str,
    traceback: str,
    turn_id: int,
    error_idx: int,
    response_format: BaseModel | None = None,
)
```

#### 1.2.3 Slide Induction (`induct.py`)

**Two-Phase Induction:**

1. **Category Split** - Clusters slides by function:
   - opening, table_of_contents, section_outline, ending (functional)
   - content slides (text/image variants)

2. **Layout Split** - Groups similar content slides:
   - Uses image embeddings (ViT-base-patch16-224)
   - Cosine similarity clustering
   - Extracts content schema per layout

**Output Structure:**
```python
layout_induction = {
    "opening": {
        "template_id": 1,
        "slides": [1],
        "content_schema": {...}
    },
    "Content:text": {
        "template_id": 3,
        "slides": [3, 5, 7],
        "content_schema": {...}
    },
    "functional_keys": ["opening", "ending"],
    "language": {"lid": "en"}
}
```

#### 1.2.4 Presentation Generation (`pptgen.py`)

**PPTGen Workflow:**
```python
async def generate_pres(
    self,
    source_doc: Document,
    num_slides: int | None = None,
    outline: list[OutlineItem] | None = None,
    dst_language: Language | None = None,
):
    # 1. Generate outline
    self.outline = await self.generate_outline(num_slides, source_doc)
    
    # 2. Generate slides concurrently
    async with asyncio.TaskGroup() as tg:
        for slide_idx, item in enumerate(self.outline):
            tg.create_task(self.generate_slide(slide_idx, item))
    
    # 3. Build presentation
    return self.build_presentation()
```

**Slide Generation Pipeline:**
```python
async def generate_slide(self, slide_idx, outline_item):
    # 1. Select layout
    layout, header, content = await self._select_layout(slide_idx, outline_item)
    
    # 2. Generate content (Editor Agent)
    editor_output = await self.staffs["editor"](
        schema=layout.content_schema,
        slide_content=content,
        response_format=EditorOutput.response_model(elements)
    )
    
    # 3. Generate edit commands
    command_list = self._generate_commands(editor_output, layout)
    
    # 4. Execute edits (Coder Agent)
    edit_actions = await self.staffs["coder"](
        api_docs=CodeExecutor.get_apis_docs(API_TYPES.Agent.value),
        command_list=command_list
    )
    
    # 5. Apply edits with retry
    code_executor.execute_actions(edit_actions, edit_slide)
```

#### 1.2.5 Slide Editing API (`apis.py`)

**Available APIs:**
```python
def del_paragraph(slide, div_id: int, paragraph_id: int)
def replace_paragraph(slide, div_id: int, paragraph_id: int, text: str)
def clone_paragraph(slide, div_id: int, paragraph_id: int)
def del_image(slide, figure_id: int)
def replace_image(slide, doc, img_id: int, image_path: str)
```

**CodeExecutor:** Executes LLM-generated code safely with history tracking

#### 1.2.6 Presentation Layer (`presentation/`)

**Hierarchy:**
```
Presentation
├── slides: list[SlidePage]
│   ├── shapes: list[ShapeElement]
│   │   ├── TextBox
│   │   ├── Picture
│   │   ├── FreeShape
│   │   └── GroupShape
│   └── backgrounds: list[Background]
├── layout_mapping: dict[str, Layout]
└── prs: pptagent_pptx.Presentation
```

**Key Classes:**
- `SlidePage`: Internal slide representation with HTML export
- `ShapeElement`: Base class for all shapes with closure system
- `Closure`: Deferred operations applied during PPTX build

### 1.3 Dependencies

**Core Dependencies:**
```toml
dependencies = [
    "pptagent>=0.2.16",           # Core library (includes pptagent_pptx)
    "openai>=1.108.2",            # LLM API
    "pydantic>=2.11.9",           # Structured outputs
    "jinja2>=3.1.6",              # Prompt templates
    "pillow",                      # Image processing
]

# For image embedding (optional):
transformers, torch, huggingface_hub

# For PDF parsing (optional):
mineru API (MINERU_API env var)
```

---

## Part 2: TeacherAssist Refactoring Architecture

### 2.1 Current Architecture (To Be Replaced)

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Current TeacherAssist Stack                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │ Frontend  │───▶│   Backend    │───▶│  Presenton   │             │
│  │ (Static)  │    │  (FastAPI)   │    │  (Docker)    │             │
│  │ :8080     │    │   :5050      │    │   :8001      │             │
│  └───────────┘    └──────────────┘    └──────────────┘             │
│                          │                   │                      │
│                          ▼                   ▼                      │
│                   ┌──────────────┐    ┌──────────────┐             │
│                   │   Ollama     │    │  ChromaDB    │             │
│                   │   :11434     │    │  (internal)  │             │
│                   └──────────────┘    └──────────────┘             │
│                                                                     │
│  Issues:                                                            │
│  ❌ Presenton = black box, hard to debug                           │
│  ❌ Limited customization                                           │
│  ❌ No progress streaming                                           │
│  ❌ Platform compatibility issues (ARM64)                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Refactoring Options

Based on the DeepPresenter architecture, we have **three integration options**:

#### Option A: Minimal - PPTAgent Core Only (Recommended for MVP)
- Transplant only `pptagent/` core modules
- Direct LLM calls without MCP overhead
- Fastest implementation, simplest debugging

#### Option B: Standard - PPTAgent + DeepPresenter Tools
- Include DeepPresenter's tool modules (search, image gen, etc.)
- Use FastMCP for tool management
- More features, moderate complexity

#### Option C: Full - Complete DeepPresenter Stack
- Full agent orchestration (Research → Design/PPTAgent)
- Multi-stage workflow with deep research
- Maximum features, highest complexity

**Recommendation**: Start with **Option A** for MVP, evolve to **Option B** as needed.

### 2.3 New Architecture (Option A - MVP)

```
┌─────────────────────────────────────────────────────────────────────┐
│           Refactored TeacherAssist with PPTAgent Core               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │              Modern Frontend (React + Tailwind)                │ │
│  │                                                               │ │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │ │
│  │  │  Input  │  │ Template │  │  Live    │  │   Download    │  │ │
│  │  │  Panel  │  │ Gallery  │  │ Preview  │  │   Actions     │  │ │
│  │  │         │  │          │  │          │  │               │  │ │
│  │  │• Topic  │  │• Browse  │  │• Slide   │  │• PPTX         │  │ │
│  │  │• Content│  │• Filter  │  │  Cards   │  │• Regenerate   │  │ │
│  │  │• Upload │  │• Preview │  │• Progress│  │• Edit         │  │ │
│  │  └────┬────┘  └────┬─────┘  └────▲─────┘  └───────────────┘  │ │
│  │       │            │             │ SSE                        │ │
│  └───────│────────────│─────────────│────────────────────────────┘ │
│          │            │             │                              │
│          ▼            ▼             │                              │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    Backend (FastAPI)                          │ │
│  │                                                               │ │
│  │  ┌──────────────────────────────────────────────────────────┐│ │
│  │  │                PPTAgent Service Layer                     ││ │
│  │  │                                                          ││ │
│  │  │  ┌────────────────────────────────────────────────────┐  ││ │
│  │  │  │           Presentation Engine                       │  ││ │
│  │  │  │                                                    │  ││ │
│  │  │  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │  ││ │
│  │  │  │  │ Template │  │ Outline  │  │  Slide Generator │ │  ││ │
│  │  │  │  │ Inductor │─▶│Generator │─▶│  (Parallel)      │ │  ││ │
│  │  │  │  └──────────┘  └──────────┘  └──────────────────┘ │  ││ │
│  │  │  │                                                    │  ││ │
│  │  │  │  ┌──────────────────────────────────────────────┐ │  ││ │
│  │  │  │  │          PPTAgent Core (Transplanted)        │ │  ││ │
│  │  │  │  │                                              │ │  ││ │
│  │  │  │  │  agent.py │ apis.py │ pptgen.py │ induct.py │ │  ││ │
│  │  │  │  │  presentation/ │ response/ │ roles/         │ │  ││ │
│  │  │  │  └──────────────────────────────────────────────┘ │  ││ │
│  │  │  └────────────────────────────────────────────────────┘  ││ │
│  │  └──────────────────────────────────────────────────────────┘│ │
│  │                                                               │ │
│  │  ┌────────────┐    ┌────────────┐    ┌────────────────────┐  │ │
│  │  │   LLM      │    │  Template  │    │    Output          │  │ │
│  │  │  Adapter   │    │  Storage   │    │   Storage          │  │ │
│  │  └──────┬─────┘    └────────────┘    └────────────────────┘  │ │
│  └─────────│─────────────────────────────────────────────────────┘ │
│            │                                                        │
│            ▼                                                        │
│  ┌──────────────┐    ┌──────────────┐                              │
│  │    Ollama    │ OR │  OpenAI API  │                              │
│  │   :11434     │    │   (cloud)    │                              │
│  └──────────────┘    └──────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘

Frontend Stack:
• React 18 + TypeScript
• Tailwind CSS + shadcn/ui
• Framer Motion (animations)
• SSE for real-time progress
• Responsive (mobile-first)
```

### 2.4 New Architecture (Option B - With Tools)

```
┌─────────────────────────────────────────────────────────────────────┐
│         Refactored TeacherAssist with DeepPresenter Tools           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                       Frontend (Modern SPA)                    │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                      │
│  ┌───────────────────────────▼───────────────────────────────────┐ │
│  │                    Backend (FastAPI)                          │ │
│  │                                                               │ │
│  │  ┌──────────────────────────────────────────────────────────┐│ │
│  │  │                   Agent Orchestration                     ││ │
│  │  │                                                          ││ │
│  │  │   ┌────────────────┐       ┌────────────────┐            ││ │
│  │  │   │ Simple Mode    │       │ Research Mode  │            ││ │
│  │  │   │                │       │                │            ││ │
│  │  │   │ Text → PPTAgent│       │ Topic → Search │            ││ │
│  │  │   │     → PPTX     │       │   → Research   │            ││ │
│  │  │   │                │       │   → PPTAgent   │            ││ │
│  │  │   └────────┬───────┘       └────────┬───────┘            ││ │
│  │  │            │                        │                    ││ │
│  │  │            └────────────┬───────────┘                    ││ │
│  │  │                         ▼                                ││ │
│  │  │            ┌────────────────────────┐                    ││ │
│  │  │            │     AgentEnv (MCP)     │                    ││ │
│  │  │            └────────────┬───────────┘                    ││ │
│  │  └─────────────────────────│────────────────────────────────┘│ │
│  │                            │                                  │ │
│  │  ┌─────────────────────────▼────────────────────────────────┐│ │
│  │  │                    MCP Tool Servers                      ││ │
│  │  │                                                          ││ │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ ││ │
│  │  │  │ pptagent │  │  search  │  │  fetch   │  │  image   │ ││ │
│  │  │  │          │  │          │  │          │  │  tools   │ ││ │
│  │  │  │generate_ │  │search_web│  │fetch_url │  │image_gen │ ││ │
│  │  │  │slide     │  │search_   │  │convert_  │  │image_    │ ││ │
│  │  │  │          │  │images    │  │to_md     │  │caption   │ ││ │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ ││ │
│  │  └──────────────────────────────────────────────────────────┘│ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.5 Backend Module Structure (Option A - MVP)

```
backend/
├── app/
│   ├── main.py                    # FastAPI app entry
│   ├── config.py                  # Settings management
│   ├── models.py                  # Pydantic request/response models
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py              # API endpoints
│   │   ├── websocket.py           # Progress streaming
│   │   └── dependencies.py        # DI container
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── presentation_service.py   # High-level orchestration
│   │   ├── template_service.py       # Template management
│   │   └── llm_service.py            # LLM provider abstraction
│   │
│   ├── pptagent_core/              # TRANSPLANTED FROM PPTAGENT
│   │   ├── __init__.py
│   │   ├── agent.py                # Agent system
│   │   ├── apis.py                 # Slide editing APIs
│   │   ├── induct.py               # Layout induction
│   │   ├── llms.py                 # LLM wrappers
│   │   ├── pptgen.py               # Generation engine
│   │   ├── utils.py                # Utilities
│   │   │
│   │   ├── presentation/           # PPTX abstraction layer
│   │   │   ├── __init__.py
│   │   │   ├── layout.py
│   │   │   ├── presentation.py
│   │   │   └── shapes.py
│   │   │
│   │   ├── response/               # Response parsing
│   │   │   ├── __init__.py
│   │   │   ├── induct.py
│   │   │   ├── outline.py
│   │   │   └── pptgen.py
│   │   │
│   │   ├── roles/                  # Agent YAML configs
│   │   │   ├── coder.yaml
│   │   │   ├── content_organizer.yaml
│   │   │   ├── editor.yaml
│   │   │   ├── layout_selector.yaml
│   │   │   └── schema_extractor.yaml
│   │   │
│   │   └── prompts/                # Prompt templates
│   │       ├── ask_category.txt
│   │       ├── caption.txt
│   │       ├── category_split.txt
│   │       └── lengthy_rewrite.txt
│   │
│   └── utils/
│       ├── __init__.py
│       └── file_utils.py
│
├── templates/                      # PPTX templates
│   ├── default/
│   ├── academic/
│   └── business/
│
├── output/                         # Generated files
└── requirements.txt
```

### 2.6 Backend Module Structure (Option B - With Tools)

```
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   │
│   ├── api/
│   │   └── ...
│   │
│   ├── services/
│   │   ├── presentation_service.py
│   │   ├── template_service.py
│   │   ├── llm_service.py
│   │   └── agent_orchestrator.py    # NEW: Agent loop management
│   │
│   ├── pptagent_core/               # From PPTAgent
│   │   └── ...
│   │
│   ├── agents/                       # TRANSPLANTED FROM DEEPPRESENTER
│   │   ├── __init__.py
│   │   ├── agent.py                  # Base Agent class
│   │   ├── env.py                    # AgentEnv (MCP manager)
│   │   ├── pptagent.py               # PPTAgent agent
│   │   ├── research.py               # Research agent (optional)
│   │   └── design.py                 # Design agent (optional)
│   │
│   ├── tools/                        # TRANSPLANTED FROM DEEPPRESENTER
│   │   ├── __init__.py
│   │   ├── appcore.py                # FastMCP instance
│   │   ├── server.py                 # MCP server entry
│   │   ├── fetch.py                  # Web fetching
│   │   ├── research.py               # Academic search
│   │   ├── richfile.py               # File handling
│   │   ├── task.py                   # Thinking, finalize
│   │   ├── tool_agents.py            # Image gen, caption
│   │   └── tavily_search.py          # Web search
│   │
│   ├── roles/                        # Agent configs (YAML)
│   │   ├── PPTAgent.yaml
│   │   ├── Research.yaml
│   │   └── Design.yaml
│   │
│   └── utils/
│       └── ...
│
├── templates/
├── output/
└── requirements.txt
```

### 2.7 API Design

#### 2.7.1 REST Endpoints

```python
# app/api/routes.py

from fastapi import APIRouter, BackgroundTasks, WebSocket
from app.models import (
    GenerateRequest, GenerateResponse, 
    ProgressEvent, TemplateInfo
)

router = APIRouter(prefix="/api/v2")

@router.get("/templates")
async def list_templates() -> list[TemplateInfo]:
    """List available PPTX templates"""
    pass

@router.post("/presentations/generate")
async def generate_presentation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
) -> GenerateResponse:
    """
    Start async presentation generation.
    Returns task_id for progress tracking.
    """
    pass

@router.get("/presentations/{task_id}/status")
async def get_status(task_id: str) -> ProgressEvent:
    """Get current generation status"""
    pass

@router.get("/presentations/{task_id}/download")
async def download(task_id: str):
    """Download generated PPTX"""
    pass

@router.websocket("/ws/progress/{task_id}")
async def progress_websocket(websocket: WebSocket, task_id: str):
    """Real-time progress streaming"""
    pass
```

#### 2.7.2 Request/Response Models

```python
# app/models.py

from pydantic import BaseModel
from enum import Enum

class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class GenerateRequest(BaseModel):
    topic: str
    content: str                      # Main content/outline
    template_id: str = "default"
    num_slides: int | None = None     # Auto if None
    language: str = "en"
    
    # LLM configuration
    llm_provider: LLMProvider = LLMProvider.OLLAMA
    model_name: str = "gpt-oss:20b"
    
    # Optional customization
    include_images: bool = True
    generate_transcript: bool = False

class GenerateResponse(BaseModel):
    task_id: str
    status: str = "queued"
    estimated_time: int  # seconds

class ProgressEvent(BaseModel):
    task_id: str
    stage: str           # outline, content, slide_N, building, complete
    progress: float      # 0.0 - 1.0
    message: str
    current_slide: int | None = None
    total_slides: int | None = None

class GenerationResult(BaseModel):
    task_id: str
    status: str
    pptx_url: str | None = None
    transcript_url: str | None = None
    error: str | None = None
    slides_generated: int = 0
    generation_time: float  # seconds
```

### 2.8 Service Layer Implementation

```python
# app/services/presentation_service.py

import asyncio
from typing import AsyncGenerator
from app.pptagent_core.pptgen import PPTGen
from app.pptagent_core.induct import SlideInducter
from app.pptagent_core.llms import AsyncLLM
from app.pptagent_core.presentation import Presentation

class PresentationService:
    def __init__(
        self,
        template_dir: str,
        output_dir: str,
        llm_service: "LLMService"
    ):
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.llm_service = llm_service
        self._tasks: dict[str, asyncio.Task] = {}
        self._progress: dict[str, ProgressEvent] = {}

    async def generate(
        self,
        request: GenerateRequest
    ) -> AsyncGenerator[ProgressEvent, None]:
        """Generate presentation with progress streaming"""
        
        task_id = str(uuid.uuid4())
        
        # 1. Setup LLM
        yield ProgressEvent(
            task_id=task_id,
            stage="init",
            progress=0.0,
            message="Initializing LLM connection..."
        )
        
        llm = await self.llm_service.get_async_llm(
            provider=request.llm_provider,
            model=request.model_name
        )
        
        # 2. Load template
        yield ProgressEvent(
            task_id=task_id,
            stage="template",
            progress=0.05,
            message="Loading presentation template..."
        )
        
        template_path = self._get_template_path(request.template_id)
        config = Config(self.output_dir)
        presentation = Presentation.from_file(template_path, config)
        
        # 3. Induct template layouts
        yield ProgressEvent(
            task_id=task_id,
            stage="induction",
            progress=0.1,
            message="Analyzing template layouts..."
        )
        
        inducter = SlideInducter(
            prs=presentation,
            ppt_image_folder=config.IMAGE_DIR,
            template_image_folder=config.TEMPLATE_IMAGE_DIR,
            config=config,
            language_model=llm,
            vision_model=llm,  # Use same for now
            image_models=None,  # Skip embedding for speed
            use_assert=False
        )
        layout_induction = await inducter.layout_induct()
        
        # 4. Setup PPTGen
        yield ProgressEvent(
            task_id=task_id,
            stage="setup",
            progress=0.15,
            message="Preparing generation engine..."
        )
        
        pptgen = PPTGen(
            language_model=llm,
            vision_model=llm,
            retry_times=3,
            record_cost=False
        )
        pptgen.set_reference(layout_induction, presentation)
        
        # 5. Generate outline
        yield ProgressEvent(
            task_id=task_id,
            stage="outline",
            progress=0.2,
            message="Generating presentation outline..."
        )
        
        source_doc = Document.from_text(request.content)
        outline = await pptgen.generate_outline(
            num_slides=request.num_slides,
            doc=source_doc
        )
        
        total_slides = len(outline)
        
        # 6. Generate slides
        for i, item in enumerate(outline):
            progress = 0.2 + (0.7 * (i / total_slides))
            
            yield ProgressEvent(
                task_id=task_id,
                stage=f"slide_{i+1}",
                progress=progress,
                message=f"Generating slide {i+1}/{total_slides}: {item.purpose}",
                current_slide=i+1,
                total_slides=total_slides
            )
            
            slide, _ = await pptgen.generate_slide(i, item, asyncio.Semaphore(1))
            pptgen.slides.append(slide)
        
        # 7. Build final PPTX
        yield ProgressEvent(
            task_id=task_id,
            stage="building",
            progress=0.9,
            message="Building final presentation..."
        )
        
        output_path = os.path.join(
            self.output_dir,
            f"{task_id}.pptx"
        )
        pptgen.build_presentation().save(output_path)
        
        # 8. Complete
        yield ProgressEvent(
            task_id=task_id,
            stage="complete",
            progress=1.0,
            message="Presentation ready!",
            total_slides=total_slides
        )
```

### 2.9 LLM Service Abstraction

```python
# app/services/llm_service.py

from app.pptagent_core.llms import AsyncLLM

class LLMService:
    """Unified LLM provider abstraction"""
    
    PROVIDER_CONFIGS = {
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama"
        },
        "openai": {
            "base_url": None,  # Use default
            "api_key": None    # From OPENAI_API_KEY env
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com/v1",
            "api_key": None    # From ANTHROPIC_API_KEY env
        }
    }
    
    async def get_async_llm(
        self,
        provider: str,
        model: str
    ) -> AsyncLLM:
        config = self.PROVIDER_CONFIGS[provider]
        
        return AsyncLLM(
            model=model,
            base_url=config["base_url"],
            api_key=config["api_key"] or os.getenv(f"{provider.upper()}_API_KEY"),
            timeout=360
        )
```

### 2.10 Frontend Architecture & UI Design

#### 2.10.1 Design Principles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UI Design Principles                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. PROGRESSIVE DISCLOSURE                                                  │
│     • Show simple form first, advanced options on demand                    │
│     • Don't overwhelm users with all options upfront                        │
│                                                                             │
│  2. REAL-TIME FEEDBACK                                                      │
│     • Generation progress visible at all times                              │
│     • Live preview of slides as they're generated                           │
│     • Clear status indicators (loading, success, error)                     │
│                                                                             │
│  3. MINIMAL FRICTION                                                        │
│     • One-click generation for common use cases                             │
│     • Smart defaults that work for 80% of users                             │
│     • Drag-and-drop for file uploads                                        │
│                                                                             │
│  4. VISUAL HIERARCHY                                                        │
│     • Primary action (Generate) always prominent                            │
│     • Secondary actions clearly subordinate                                 │
│     • Consistent spacing and typography                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.10.2 Recommended Tech Stack

| Option | Stack | Pros | Cons |
|--------|-------|------|------|
| **A (Recommended)** | React + Tailwind + shadcn/ui | Modern, accessible, fast dev | Requires build step |
| B | Vue 3 + Vuetify | Batteries included | Heavier bundle |
| C | HTMX + Alpine.js | No build, simple | Less ecosystem |
| D | Svelte + Skeleton UI | Smallest bundle | Smaller community |

**Recommended**: React 18 + Tailwind CSS + shadcn/ui
- Modern component library with excellent accessibility
- Consistent design language
- Easy customization via CSS variables
- Great TypeScript support

#### 2.10.3 UI Layout Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TeacherAssist.AI                                    [Templates] [Settings] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │       INPUT PANEL (Left)        │  │      PREVIEW PANEL (Right)      │  │
│  │                                 │  │                                 │  │
│  │  ┌─────────────────────────┐   │  │  ┌─────────────────────────┐   │  │
│  │  │  📝 Topic / Title       │   │  │  │                         │   │  │
│  │  │  [Enter presentation...]│   │  │  │    Slide Preview        │   │  │
│  │  └─────────────────────────┘   │  │  │                         │   │  │
│  │                                 │  │  │   (Live updates as      │   │  │
│  │  ┌─────────────────────────┐   │  │  │    slides generate)     │   │  │
│  │  │  📄 Content             │   │  │  │                         │   │  │
│  │  │                         │   │  │  │    ┌─────────────┐      │   │  │
│  │  │  [Paste or type your    │   │  │  │    │  Slide 1    │      │   │  │
│  │  │   content here...]      │   │  │  │    │  ✓ Done     │      │   │  │
│  │  │                         │   │  │  │    └─────────────┘      │   │  │
│  │  │  ─── OR ───             │   │  │  │    ┌─────────────┐      │   │  │
│  │  │                         │   │  │  │    │  Slide 2    │      │   │  │
│  │  │  📎 Drop file here      │   │  │  │    │  ⏳ Working │      │   │  │
│  │  │  (PDF, DOCX, MD)        │   │  │  │    └─────────────┘      │   │  │
│  │  └─────────────────────────┘   │  │  │    ┌─────────────┐      │   │  │
│  │                                 │  │  │    │  Slide 3    │      │   │  │
│  │  ┌─────────────────────────┐   │  │  │    │  ○ Pending  │      │   │  │
│  │  │  🎨 Template            │   │  │  │    └─────────────┘      │   │  │
│  │  │  [Modern Business  ▼]   │   │  │  │                         │   │  │
│  │  └─────────────────────────┘   │  │  └─────────────────────────┘   │  │
│  │                                 │  │                                 │  │
│  │  ▶ Advanced Options            │  │  ┌─────────────────────────┐   │  │
│  │  ┌─────────────────────────┐   │  │  │     Progress Bar        │   │  │
│  │  │ Slides: [Auto ▼]        │   │  │  │  ████████░░░░  67%     │   │  │
│  │  │ Language: [English ▼]   │   │  │  │  "Generating slide 2..." │   │  │
│  │  │ Model: [Default ▼]      │   │  │  └─────────────────────────┘   │  │
│  │  └─────────────────────────┘   │  │                                 │  │
│  │                                 │  │  [📥 Download PPTX]            │  │
│  │  ┌─────────────────────────┐   │  │  [🔄 Regenerate] [✏️ Edit]     │  │
│  │  │  ✨ Generate Slides     │   │  │                                 │  │
│  │  └─────────────────────────┘   │  └─────────────────────────────────┘  │
│  └─────────────────────────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.10.4 Key UI Components

```typescript
// Component hierarchy
<App>
  <Header />
  <MainLayout>
    <InputPanel>
      <TopicInput />
      <ContentEditor>
        <TextArea />
        <FileDropZone />
      </ContentEditor>
      <TemplateSelector />
      <AdvancedOptions collapsed={true}>
        <SlideCountSelector />
        <LanguageSelector />
        <ModelSelector />
      </AdvancedOptions>
      <GenerateButton />
    </InputPanel>
    
    <PreviewPanel>
      <SlideCarousel>
        <SlideCard status="complete|generating|pending" />
      </SlideCarousel>
      <ProgressBar />
      <ActionButtons>
        <DownloadButton />
        <RegenerateButton />
        <EditButton />
      </ActionButtons>
    </PreviewPanel>
  </MainLayout>
</App>
```

#### 2.10.5 Progress & Status States

```typescript
// Generation states with UI feedback
type GenerationState = 
  | { status: 'idle' }
  | { status: 'validating', message: string }
  | { status: 'initializing', message: string, progress: 0 }
  | { status: 'analyzing_template', message: string, progress: 5 }
  | { status: 'generating_outline', message: string, progress: 15 }
  | { status: 'generating_slide', slideNumber: number, totalSlides: number, progress: number }
  | { status: 'building', message: string, progress: 90 }
  | { status: 'complete', downloadUrl: string, progress: 100 }
  | { status: 'error', error: string, retryable: boolean }

// Visual feedback for each state
const statusConfig = {
  idle: { icon: '✨', color: 'blue', text: 'Ready to generate' },
  validating: { icon: '🔍', color: 'yellow', text: 'Validating input...' },
  initializing: { icon: '⚙️', color: 'blue', text: 'Starting up...' },
  analyzing_template: { icon: '🎨', color: 'purple', text: 'Analyzing template...' },
  generating_outline: { icon: '📝', color: 'blue', text: 'Creating outline...' },
  generating_slide: { icon: '🖼️', color: 'blue', text: 'Generating slide {n}/{total}' },
  building: { icon: '🔧', color: 'blue', text: 'Building presentation...' },
  complete: { icon: '✅', color: 'green', text: 'Done!' },
  error: { icon: '❌', color: 'red', text: 'Error occurred' },
}
```

#### 2.10.6 SSE Progress Integration

```typescript
// Frontend SSE connection
function useGenerationProgress(taskId: string) {
  const [state, setState] = useState<GenerationState>({ status: 'idle' });
  const [slides, setSlides] = useState<SlidePreview[]>([]);

  useEffect(() => {
    if (!taskId) return;
    
    const eventSource = new EventSource(`/api/v2/presentations/${taskId}/progress`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setState(data);
      
      // Update slide preview when a slide completes
      if (data.status === 'generating_slide' && data.slidePreview) {
        setSlides(prev => [...prev, data.slidePreview]);
      }
    };
    
    eventSource.onerror = () => {
      setState({ status: 'error', error: 'Connection lost', retryable: true });
      eventSource.close();
    };
    
    return () => eventSource.close();
  }, [taskId]);

  return { state, slides };
}
```

#### 2.10.7 Template Gallery UI

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Choose a Template                                              [Upload ▲]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Filter: [All ▼]  [Business]  [Academic]  [Creative]  [Minimal]            │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │   │
│  │ │  Preview │ │  │ │  Preview │ │  │ │  Preview │ │  │ │  Preview │ │   │
│  │ │  Image   │ │  │ │  Image   │ │  │ │  Image   │ │  │ │  Image   │ │   │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │   │
│  │              │  │              │  │              │  │              │   │
│  │ Modern Biz   │  │ Academic     │  │ Creative    │  │ Minimal      │   │
│  │ ⭐ Popular   │  │ 📚 Formal    │  │ 🎨 Colorful │  │ ⚪ Clean     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│       ✓ Selected                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.10.8 Mobile Responsive Design

```css
/* Responsive breakpoints */
@media (max-width: 768px) {
  .main-layout {
    flex-direction: column;  /* Stack panels vertically */
  }
  
  .preview-panel {
    position: fixed;
    bottom: 0;
    height: 40vh;  /* Bottom sheet style */
    border-radius: 16px 16px 0 0;
  }
  
  .slide-carousel {
    flex-direction: row;  /* Horizontal scroll */
    overflow-x: auto;
  }
}
```

#### 2.10.9 Accessibility Requirements

- **Keyboard Navigation**: All actions accessible via keyboard
- **Screen Reader**: ARIA labels on all interactive elements
- **Color Contrast**: WCAG 2.1 AA compliance
- **Focus Indicators**: Clear visual focus states
- **Progress Announcements**: Live regions for status updates

```tsx
// Example accessible progress component
<div 
  role="progressbar" 
  aria-valuenow={progress} 
  aria-valuemin={0} 
  aria-valuemax={100}
  aria-label={`Generation progress: ${progress}%`}
>
  <div className="progress-fill" style={{ width: `${progress}%` }} />
</div>
<div aria-live="polite" className="sr-only">
  {statusMessage}
</div>
```

#### 2.10.10 Animation & Micro-interactions

```typescript
// Subtle animations for polish
const animations = {
  // Slide card appears when generated
  slideAppear: {
    initial: { opacity: 0, y: 20, scale: 0.95 },
    animate: { opacity: 1, y: 0, scale: 1 },
    transition: { duration: 0.3, ease: 'easeOut' }
  },
  
  // Progress bar pulse while generating
  progressPulse: {
    animate: { opacity: [1, 0.7, 1] },
    transition: { duration: 1.5, repeat: Infinity }
  },
  
  // Success checkmark
  checkmarkDraw: {
    pathLength: { from: 0, to: 1 },
    transition: { duration: 0.4, delay: 0.2 }
  },
  
  // Button hover
  buttonHover: {
    scale: 1.02,
    transition: { duration: 0.15 }
  }
}
```

### 2.11 Frontend Implementation Roadmap

#### Phase 1: Core Setup (Week 3, Days 1-2)

```bash
# Initialize React project with Vite
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install

# Core dependencies
npm install @tanstack/react-query axios
npm install tailwindcss postcss autoprefixer
npm install framer-motion  # Animations
npm install lucide-react   # Icons

# shadcn/ui setup
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card progress input textarea select tabs
```

#### Phase 2: Component Implementation (Week 3, Days 3-5)

```
frontend/src/
├── components/
│   ├── ui/                    # shadcn/ui components
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── MainLayout.tsx
│   │   └── Footer.tsx
│   ├── input/
│   │   ├── TopicInput.tsx
│   │   ├── ContentEditor.tsx
│   │   ├── FileDropZone.tsx
│   │   └── TemplateSelector.tsx
│   ├── preview/
│   │   ├── SlideCarousel.tsx
│   │   ├── SlideCard.tsx
│   │   └── ProgressBar.tsx
│   └── common/
│       ├── LoadingSpinner.tsx
│       └── ErrorBoundary.tsx
├── hooks/
│   ├── useGeneration.ts       # Generation state & SSE
│   ├── useTemplates.ts        # Template fetching
│   └── useLocalStorage.ts     # Persist user preferences
├── api/
│   └── client.ts              # API client with axios
├── types/
│   └── index.ts               # TypeScript types
└── App.tsx
```

#### Phase 3: Key Components Implementation

```tsx
// hooks/useGeneration.ts - Core generation hook
export function useGeneration() {
  const [state, setState] = useState<GenerationState>({ status: 'idle' });
  const [slides, setSlides] = useState<SlidePreview[]>([]);
  const [taskId, setTaskId] = useState<string | null>(null);

  const generate = async (request: GenerateRequest) => {
    setState({ status: 'validating', message: 'Validating input...' });
    
    try {
      // Start generation
      const { data } = await api.post('/api/v2/presentations/generate', request);
      setTaskId(data.task_id);
      
      // Connect to SSE for progress
      const eventSource = new EventSource(
        `/api/v2/presentations/${data.task_id}/progress`
      );
      
      eventSource.onmessage = (event) => {
        const progress = JSON.parse(event.data);
        setState(progress);
        
        if (progress.slidePreview) {
          setSlides(prev => [...prev, progress.slidePreview]);
        }
        
        if (progress.status === 'complete' || progress.status === 'error') {
          eventSource.close();
        }
      };
      
    } catch (error) {
      setState({ status: 'error', error: error.message, retryable: true });
    }
  };

  const reset = () => {
    setState({ status: 'idle' });
    setSlides([]);
    setTaskId(null);
  };

  return { state, slides, taskId, generate, reset };
}

// components/input/ContentEditor.tsx - Smart content input
export function ContentEditor({ value, onChange }: ContentEditorProps) {
  const [mode, setMode] = useState<'text' | 'file'>('text');
  const [dragActive, setDragActive] = useState(false);

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      setMode('file');
      // Handle file upload...
    }
  };

  return (
    <div className="space-y-4">
      <Tabs value={mode} onValueChange={setMode}>
        <TabsList>
          <TabsTrigger value="text">📝 Type Content</TabsTrigger>
          <TabsTrigger value="file">📎 Upload File</TabsTrigger>
        </TabsList>
      </Tabs>

      {mode === 'text' ? (
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter your presentation content here...

You can use markdown formatting:
- **Bold** for emphasis
- Bullet points for lists
- ## Headings for sections"
          className="min-h-[200px] font-mono text-sm"
        />
      ) : (
        <div
          className={cn(
            "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
            dragActive ? "border-primary bg-primary/5" : "border-muted"
          )}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
        >
          <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
          <p className="mt-2 text-sm text-muted-foreground">
            Drop PDF, DOCX, or Markdown file here
          </p>
          <Button variant="outline" className="mt-4">
            Or click to browse
          </Button>
        </div>
      )}
    </div>
  );
}

// components/preview/ProgressBar.tsx - Animated progress
export function GenerationProgressBar({ state }: { state: GenerationState }) {
  const config = statusConfig[state.status];
  
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="flex items-center gap-2">
          <span>{config.icon}</span>
          <span>{state.message || config.text}</span>
        </span>
        {state.progress !== undefined && (
          <span className="font-mono">{Math.round(state.progress)}%</span>
        )}
      </div>
      
      <div className="relative h-2 bg-secondary rounded-full overflow-hidden">
        <motion.div
          className={cn("absolute h-full rounded-full", `bg-${config.color}-500`)}
          initial={{ width: 0 }}
          animate={{ width: `${state.progress || 0}%` }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        />
        
        {state.status === 'generating_slide' && (
          <motion.div
            className="absolute h-full w-20 bg-gradient-to-r from-transparent via-white/20 to-transparent"
            animate={{ x: ['-100%', '500%'] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
          />
        )}
      </div>
      
      {state.slideNumber && state.totalSlides && (
        <p className="text-xs text-muted-foreground text-right">
          Slide {state.slideNumber} of {state.totalSlides}
        </p>
      )}
    </div>
  );
}

// components/preview/SlideCarousel.tsx - Live slide preview
export function SlideCarousel({ slides, activeIndex }: SlideCarouselProps) {
  return (
    <div className="relative">
      <div className="flex gap-4 overflow-x-auto pb-4 snap-x">
        {slides.map((slide, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="snap-center"
          >
            <SlideCard 
              slide={slide} 
              index={i + 1}
              isActive={i === activeIndex}
            />
          </motion.div>
        ))}
        
        {/* Generating placeholder */}
        {slides.length > 0 && (
          <div className="flex-shrink-0 w-48 h-32 border-2 border-dashed rounded-lg flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>
    </div>
  );
}
```

#### Phase 4: Polish & Testing (Week 4)

1. **Error States**
   - Network error recovery
   - Retry mechanisms
   - Graceful degradation

2. **Loading States**
   - Skeleton loaders for initial load
   - Optimistic UI updates

3. **Responsive Testing**
   - Mobile viewport testing
   - Touch interactions

4. **Performance**
   - Code splitting with React.lazy
   - Image optimization for previews
   - SSE reconnection logic

---

## Part 3: Implementation Roadmap

### Option A: Minimal MVP (3-4 weeks)

#### Phase 1: Core Transplant (Week 1)

1. **Extract PPTAgent Core**
   ```bash
   # Files to copy from pptagent/
   pptagent/
   ├── agent.py
   ├── apis.py
   ├── induct.py
   ├── llms.py
   ├── pptgen.py
   ├── utils.py
   ├── presentation/
   ├── response/
   ├── roles/
   └── prompts/
   ```
   - Copy to `backend/app/pptagent_core/`
   - Update imports to relative paths
   - Remove unused dependencies (gradio, deeppresenter)

2. **Setup Dependencies**
   ```txt
   # requirements.txt additions
   pptagent-pptx>=0.2.0     # Forked python-pptx
   openai>=1.0.0
   pydantic>=2.0.0
   jinja2>=3.0.0
   pillow>=9.0.0
   aiohttp>=3.8.0
   pyyaml>=6.0.0
   ```

3. **Create LLM Adapter**
   - Implement `LLMService` with Ollama support
   - Test connection to local Ollama

#### Phase 2: Service Layer (Week 2)

1. **Implement PresentationService**
   - Async generation with progress tracking
   - Template management
   - Error handling with retries

2. **Setup API Routes**
   - REST endpoints for generation
   - SSE for progress streaming

3. **Template Preparation**
   - Convert existing templates to pptagent format
   - Test template induction

#### Phase 3: Frontend Modernization (Week 3)

1. **Project Setup**
   - Initialize React + Vite + TypeScript
   - Configure Tailwind CSS + shadcn/ui
   - Setup project structure (components, hooks, api)

2. **Core Components**
   - TopicInput with validation
   - ContentEditor (text + file drop)
   - TemplateSelector with gallery view
   - AdvancedOptions (collapsible)
   - GenerateButton with loading state

3. **Progress & Preview**
   - SSE connection hook (useGeneration)
   - Animated ProgressBar
   - SlideCarousel with live updates
   - SlideCard with status indicators
   - DownloadButton with format options

4. **Polish**
   - Responsive layout (mobile-first)
   - Keyboard navigation
   - Loading skeletons
   - Error boundaries
   - Micro-animations (Framer Motion)

#### Phase 4: Testing & Deployment (Week 4)

1. **Integration Tests**
   - End-to-end generation tests
   - LLM provider switching

2. **Deployment Updates**
   - Remove Presenton service
   - Update startup scripts (start_system.sh, stop_system.sh)
   - Native ARM64 support

3. **Documentation**
   - API documentation
   - User guide

---

### Option B: With Tools (5-6 weeks)

Includes Option A plus:

#### Additional Phase: Tool Integration (Week 4-5)

1. **FastMCP Setup**
   ```bash
   # Additional files from deeppresenter/tools/
   tools/
   ├── appcore.py
   ├── server.py
   ├── fetch.py
   ├── richfile.py
   ├── task.py
   └── tool_agents.py
   ```

2. **Search Integration**
   - Tavily or Firecrawl for web search
   - Image search capability

3. **Agent Orchestration**
   - AgentEnv for MCP management
   - Simple/Research mode toggle

#### Additional Phase: Enhanced Features (Week 5-6)

1. **Research Mode**
   - Topic → Deep search → Content → PPTX

2. **Image Generation**
   - OpenAI DALL-E or local SD integration

3. **Document Analysis**
   - PDF/docx → markdown → PPTX pipeline

---

## Part 4: Comparison & Risk Analysis

### 4.1 Presenton vs PPTAgent/DeepPresenter

| Aspect | Presenton | PPTAgent Core | DeepPresenter Full |
|--------|-----------|---------------|-------------------|
| Architecture | Black-box Docker | Python library | Agent + MCP framework |
| Customization | Limited | Full control | Maximum flexibility |
| Templates | Fixed | Extensible | Extensible + HTML mode |
| Progress | None | Can add streaming | Built-in yields |
| LLM Support | Ollama only | OpenAI-compatible | Multi-model configs |
| Debugging | Hard (container) | Easy (native) | Moderate (MCP) |
| ARM64 | Emulation | Native | Native |
| Dependencies | Heavy (~2GB) | Lightweight | Moderate |
| Research | None | None | Deep research agent |
| Visual Feedback | None | None | inspect_slide loop |
| Document Input | Limited | Markdown | PDF/docx/markdown |

### 4.2 Implementation Options Comparison

| Option | Effort | Features | Risk | Best For |
|--------|--------|----------|------|----------|
| A: PPTAgent Core Only | 3-4 weeks | Template-based PPTX | Low | MVP |
| B: + DeepPresenter Tools | 5-6 weeks | + Web search, images | Medium | Enhanced |
| C: Full Stack | 8+ weeks | + Research, Design agents | High | Full product |

### 4.3 Risk Mitigation

1. **pptagent_pptx dependency**
   - Use PyPI package (`pptagent-pptx>=0.2.0`) initially
   - Vendor if customization needed
   - Fallback: Standard python-pptx with code adaptation

2. **Image embeddings in SlideInducter**
   - Skip ViT embeddings for MVP (use simpler layout matching)
   - Add later if template matching quality is poor
   - Requires: `transformers`, GPU for best performance

3. **Model compatibility**
   - Test prompts with target models (gpt-oss:20b, llama3, qwen2.5)
   - Role YAML configs may need prompt adjustments for smaller models
   - Context budget limits (`CONTEXT_LENGTH_LIMIT`) may need tuning
   - Consider: OpenAI-compatible API normalization via LLMService

4. **MCP complexity (Option B/C)**
   - Start without MCP for MVP
   - Add FastMCP incrementally for specific tools
   - Original DeepPresenter uses Docker for sandbox - **not needed for TeacherAssist**
   - Simple file-based workspaces are sufficient

5. **Visual feedback loop (Design agent)**
   - Requires Playwright for HTML → image conversion
   - Skip for MVP, use PPTAgent instead
   - Add if HTML slide output is needed later

6. **Search API dependencies**
   - Tavily or Firecrawl require API keys
   - Can be optional features behind feature flags
   - Fallback: DuckDuckGo or SearXNG self-hosted

### 4.4 Recommended Migration Path

```
Week 1-2: Option A MVP
├── Transplant pptagent/ core
├── Create LLMService for Ollama
├── Basic REST API + SSE progress streaming
└── Test with single template

Week 3-4: Stabilization
├── Multiple template support
├── Frontend progress UI
├── Error handling & retries
└── Remove Presenton dependency from codebase

Week 5-6: Option B Enhancement (if needed)
├── Add FastMCP infrastructure
├── Integrate web search (Tavily/Firecrawl)
├── Add image search/download
└── Document conversion support (markitdown)

Future: Option C Features
├── Research agent for deep content
├── Design agent for HTML slides
├── Multi-model orchestration
└── Full MCP tool ecosystem
```

---

## Conclusion

This refactoring replaces the opaque Presenton container with PPTAgent/DeepPresenter's well-documented, extensible architecture. The key benefits are:

1. **Modern UI/UX**: React + Tailwind + shadcn/ui for a polished, responsive interface
2. **Real-time Feedback**: Live progress streaming via SSE with slide previews
3. **Full Control**: Every generation step is visible and customizable
4. **Multi-LLM Support**: Easy switching between Ollama, OpenAI, Anthropic
5. **Native Performance**: No emulation overhead on ARM64
6. **Maintainability**: Standard Python + React code, easy to debug and extend
7. **Extensibility**: Optional research, design, and tool capabilities via DeepPresenter

**User Experience Improvements**:
- Progressive disclosure (simple → advanced)
- Drag-and-drop file upload
- Template gallery with previews
- Live slide generation preview
- Mobile-responsive design
- Accessible (keyboard nav, screen reader)

**Recommended approach**: Start with Option A (3-4 weeks) for MVP, then incrementally add Option B features based on user needs.

---

## Appendix: Key File Mappings

### PPTAgent Core (Option A)
```
pptagent/
├── agent.py         → backend/app/pptagent_core/agent.py
├── apis.py          → backend/app/pptagent_core/apis.py
├── induct.py        → backend/app/pptagent_core/induct.py
├── llms.py          → backend/app/pptagent_core/llms.py
├── pptgen.py        → backend/app/pptagent_core/pptgen.py
├── utils.py         → backend/app/pptagent_core/utils.py
├── presentation/    → backend/app/pptagent_core/presentation/
├── response/        → backend/app/pptagent_core/response/
├── roles/           → backend/app/pptagent_core/roles/
└── prompts/         → backend/app/pptagent_core/prompts/
```

### DeepPresenter Tools (Option B)
```
deeppresenter/
├── agents/
│   ├── agent.py     → backend/app/agents/agent.py
│   ├── env.py       → backend/app/agents/env.py
│   └── pptagent.py  → backend/app/agents/pptagent.py
├── tools/
│   ├── appcore.py   → backend/app/tools/appcore.py
│   ├── server.py    → backend/app/tools/server.py
│   ├── fetch.py     → backend/app/tools/fetch.py
│   ├── richfile.py  → backend/app/tools/richfile.py
│   ├── task.py      → backend/app/tools/task.py
│   └── tavily_search.py → backend/app/tools/tavily_search.py
└── roles/
    └── PPTAgent.yaml → backend/app/roles/PPTAgent.yaml
```
