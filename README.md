# TeacherAssist V2

**AI-Powered Presentation Generation System**

TeacherAssist V2 is a modern, high-performance system for generating professional PowerPoint presentations from Markdown content using advanced LLM technology.

## 🎯 Features

- **📝 Markdown to PPT**: Convert Markdown documents to professional presentations automatically
- **🤖 AI-Powered**: Intelligent content analysis and layout selection using LLMs
- **⚡ High Performance**: Async architecture with multi-layer caching (L1/L2/L3)
- **🎨 Multiple Templates**: Support for various presentation styles and themes
- **🔄 Streaming**: Real-time progress updates via Server-Sent Events (SSE)
- **🌐 Multi-Provider LLM**: Support for both local (Ollama) and cloud (OpenAI) providers
- **📊 Cost Control**: Token usage tracking and daily budget management
- **🔒 Production Ready**: Comprehensive testing, monitoring, and error handling

## 🏗️ Architecture

```
┌─────────────────┐
│  React Frontend │  ← User Interface
└────────┬────────┘
         │
    ┌────▼──────────────┐
    │  FastAPI Backend  │  ← API Layer
    └────┬──────────────┘
         │
    ┌────▼──────────────┐
    │   PPTAgent Core   │  ← Generation Engine
    ├───────────────────┤
    │  • Schema Extract │
    │  • Content Org    │
    │  • Layout Select  │
    │  • Editor         │
    │  • Coder          │
    └────┬──────────────┘
         │
    ┌────▼──────────────┐
    │   LLM Service     │  ← Ollama/OpenAI
    └───────────────────┘
         │
    ┌────▼──────────────┐
    │  Redis Cache      │  ← Performance Layer
    └───────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.12+
- **Node.js**: 22+
- **Redis**: 7+ (for caching)
- **Ollama**: Latest (for local LLM) or OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TeacherAssist_V2
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start Redis**
   ```bash
   redis-server
   ```

5. **Start Ollama** (if using local LLM)
   ```bash
   ollama serve
   # Pull required model
   ollama pull gpt-oss:20b
   ```

6. **Frontend Setup**
   ```bash
   cd ../frontend
   npm install
   ```

7. **Run Development Servers**

   **Backend**:
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

   **Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

8. **Access Application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## 📖 Documentation

- **[Architecture Analysis](docs/architectural_analysis_report.md)**: Comprehensive architecture evaluation
- **[Implementation Workflow](docs/implementation_workflow.md)**: Detailed implementation plan
- **[Development Guide](DEVELOPMENT.md)**: Developer setup and guidelines
- **[API Documentation](http://localhost:8000/docs)**: Interactive API reference (when running)

## 🛠️ Development

### Project Structure

```
TeacherAssist_V2/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── pptagent_core/  # Core generation engine
│   │   ├── services/       # Business logic services
│   │   ├── api/            # API routes and schemas
│   │   └── core/           # Configuration and utilities
│   ├── tests/              # Test suites
│   └── data/               # Templates and test data
├── frontend/               # React frontend
│   └── src/
│       ├── components/     # React components
│       ├── hooks/          # Custom hooks
│       └── api/            # API client
├── infra/                  # Infrastructure configs
├── docs/                   # Documentation
└── .github/                # CI/CD workflows
```

### Running Tests

**Backend**:
```bash
cd backend

# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest --cov=app --cov-report=html
```

**Frontend**:
```bash
cd frontend

# Lint
npm run lint

# Type check
npx tsc --noEmit

# Build
npm run build
```

### Code Quality

**Pre-commit Hooks** (auto-installed):
- Black (Python formatting)
- Ruff (Python linting)
- MyPy (Type checking)
- Prettier (JavaScript/TypeScript formatting)
- Security checks (Bandit)

**Manual Run**:
```bash
pre-commit run --all-files
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# LLM Provider
LLM_PROVIDER=ollama          # or "openai"
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gpt-oss:20b

# OpenAI (if using)
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4-turbo-preview

# Limits
MAX_SLIDES_PER_PRESENTATION=50
MAX_CONCURRENT_GENERATIONS=3
GENERATION_TIMEOUT_SECONDS=600

# Cache
REDIS_HOST=localhost
REDIS_PORT=6379

# Cost Control
DAILY_COST_BUDGET_USD=10.0
COST_PER_1K_TOKENS=0.002
```

## 📊 Performance Targets

Based on [baseline metrics](backend/data/baseline_metrics.json):

| Metric | Target | Description |
|--------|--------|-------------|
| **P50 Latency** | 5s | Median generation time |
| **P95 Latency** | 12s | 95th percentile |
| **Throughput** | 12/min | Presentations per minute |
| **Cache Hit Rate** | 85% | L1 cache efficiency |
| **Availability** | 99.5% | System uptime |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Guidelines

- Follow existing code style (enforced by pre-commit hooks)
- Write tests for new features
- Update documentation as needed
- Ensure CI/CD passes before requesting review

## 📝 License

[Specify your license]

## 🙏 Acknowledgments

- **PPTAgent**: Original presentation generation framework
- **FastAPI**: Modern Python web framework
- **React**: UI library
- **Ollama**: Local LLM runtime

## 📧 Support

For issues and questions:
- **Issues**: [GitHub Issues](https://github.com/your-org/TeacherAssist_V2/issues)
- **Documentation**: See [docs/](docs/) directory
- **API Help**: Check [API Documentation](http://localhost:8000/docs)

---

**Version**: 2.0.0
**Status**: Phase 0 Complete - Development Ready
**Last Updated**: 2025-12-30
