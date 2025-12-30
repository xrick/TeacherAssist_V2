# Development Guide

Comprehensive guide for developers working on TeacherAssist V2.

## 🚀 Getting Started

### Development Environment Setup

1. **System Requirements**

   - Python 3.12+
   - Node.js 22+
   - Redis 7+
   - Ollama (for local LLM) or OpenAI API key
   - Git

2. **Initial Setup**

   ```bash
   # Clone repository
   git clone <repository-url>
   cd TeacherAssist_V2

   # Backend setup
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"

   # Frontend setup
   cd ../frontend
   npm install

   # Install pre-commit hooks
   cd ..
   backend/venv/bin/pre-commit install
   ```

3. **Environment Configuration**

   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start Required Services**

   ```bash
   # Terminal 1: Redis
   redis-server

   # Terminal 2: Ollama (if using local LLM)
   ollama serve

   # Terminal 3: Backend
   cd backend
   uvicorn app.main:app --reload

   # Terminal 4: Frontend
   cd frontend
   npm run dev
   ```

## 📁 Project Structure

```
TeacherAssist_V2/
├── backend/
│   ├── app/
│   │   ├── pptagent_core/          # Core PPT generation engine
│   │   │   ├── presentation/       # Presentation models
│   │   │   ├── response/           # Response formatters
│   │   │   ├── roles/              # Agent roles (schema, content, layout, editor, coder)
│   │   │   ├── prompts/            # LLM prompt templates
│   │   │   └── document/           # Document processing
│   │   ├── services/               # Business logic
│   │   │   ├── llm_service.py      # LLM abstraction layer
│   │   │   ├── cache_service.py    # Multi-layer caching
│   │   │   └── ppt_service.py      # Main orchestration
│   │   ├── api/
│   │   │   ├── routes/             # API endpoints
│   │   │   └── schemas/            # Pydantic models
│   │   └── core/
│   │       ├── config.py           # Configuration management
│   │       └── dependencies.py     # FastAPI dependencies
│   ├── tests/
│   │   ├── unit/                   # Unit tests
│   │   ├── integration/            # Integration tests
│   │   ├── e2e/                    # End-to-end tests
│   │   └── performance/            # Performance benchmarks
│   ├── data/
│   │   ├── templates/              # PPTX templates
│   │   ├── outputs/                # Generated presentations (gitignored)
│   │   └── cache/                  # Disk cache (gitignored)
│   └── pyproject.toml              # Python dependencies
├── frontend/
│   └── src/
│       ├── components/             # React components
│       ├── hooks/                  # Custom React hooks
│       ├── api/                    # API client layer
│       ├── utils/                  # Utility functions
│       ├── types/                  # TypeScript types
│       └── styles/                 # Global styles
├── infra/
│   ├── docker/                     # Docker configurations
│   ├── k8s/                        # Kubernetes manifests
│   └── scripts/                    # Deployment scripts
├── docs/                           # Documentation
└── .github/
    └── workflows/                  # CI/CD pipelines
```

## 🏗️ Architecture Overview

### Backend Architecture

**Layered Design**:

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │  ← REST endpoints, SSE streaming
├─────────────────────────────────────┤
│      Service Layer (Business)       │  ← PPTService, LLMService, CacheService
├─────────────────────────────────────┤
│    PPTAgent Core (Generation)       │  ← 5-stage pipeline
├─────────────────────────────────────┤
│   Infrastructure (LLM, Cache, DB)   │  ← Ollama/OpenAI, Redis, Files
└─────────────────────────────────────┘
```

**PPTAgent 5-Stage Pipeline**:

1. **Schema Extractor**: Analyze markdown structure and extract metadata
2. **Content Organizer**: Organize content into logical slide units
3. **Layout Selector**: Choose appropriate layouts for each slide
4. **Editor**: Refine content for presentation format
5. **Coder**: Generate final PPTX file

### Frontend Architecture

**Component Hierarchy**:

```
App
├── Layout
│   ├── Header
│   ├── Sidebar
│   └── Main
│       ├── GenerationForm
│       ├── ProgressIndicator (SSE)
│       ├── PreviewPanel
│       └── DownloadButton
└── ErrorBoundary
```

## 🔧 Development Workflow

### Feature Development

1. **Create Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Develop with TDD**

   ```bash
   # Write test first
   # backend/tests/unit/test_new_feature.py

   # Run test (should fail)
   pytest tests/unit/test_new_feature.py -v

   # Implement feature
   # backend/app/...

   # Run test (should pass)
   pytest tests/unit/test_new_feature.py -v
   ```

3. **Run Quality Checks**

   ```bash
   # Backend
   cd backend
   ruff check app/ tests/
   black app/ tests/
   mypy app/
   pytest --cov=app

   # Frontend
   cd frontend
   npm run lint
   npx tsc --noEmit
   npm run build
   ```

4. **Commit Changes**

   Pre-commit hooks will run automatically:

   ```bash
   git add .
   git commit -m "feat: add new feature"
   # Hooks run: black, ruff, mypy, prettier, etc.
   ```

5. **Push and Create PR**

   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub
   ```

### Testing Strategy

**Test Pyramid**:

```
    ┌─────────┐
    │   E2E   │  ← 10%: Critical user flows
    ├─────────┤
    │ Integ.  │  ← 20%: Service integration
    ├─────────┤
    │  Unit   │  ← 70%: Core logic
    └─────────┘
```

**Running Tests**:

```bash
# Unit tests (fast, isolated)
pytest tests/unit/ -v

# Integration tests (with Redis, etc.)
pytest tests/integration/ -v

# E2E tests (full system)
pytest tests/e2e/ -v

# Performance tests
pytest tests/performance/ -v -m baseline

# Coverage report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html
```

### Code Quality Standards

**Python**:

- **Formatting**: Black (line length: 88)
- **Linting**: Ruff (replace flake8, isort, etc.)
- **Type Checking**: MyPy (strict mode)
- **Security**: Bandit
- **Complexity**: Max McCabe complexity: 10

**TypeScript**:

- **Formatting**: Prettier
- **Linting**: ESLint with TypeScript rules
- **Type Safety**: Strict mode enabled

**Quality Gates** (must pass):

- ✅ All tests passing
- ✅ Code coverage >80%
- ✅ No linting errors
- ✅ No type errors
- ✅ No security vulnerabilities

## 🎯 Common Development Tasks

### Adding a New API Endpoint

1. **Define Schema** (`backend/app/api/schemas/`)

   ```python
   from pydantic import BaseModel

   class NewFeatureRequest(BaseModel):
       field1: str
       field2: int

   class NewFeatureResponse(BaseModel):
       result: str
       status: str
   ```

2. **Implement Route** (`backend/app/api/routes/`)

   ```python
   from fastapi import APIRouter, Depends
   from app.api.schemas import NewFeatureRequest, NewFeatureResponse
   from app.core.dependencies import get_service

   router = APIRouter()

   @router.post("/new-feature", response_model=NewFeatureResponse)
   async def new_feature(
       request: NewFeatureRequest,
       service = Depends(get_service)
   ):
       result = await service.process(request)
       return NewFeatureResponse(result=result, status="success")
   ```

3. **Write Tests** (`backend/tests/unit/api/`)

   ```python
   from fastapi.testclient import TestClient

   def test_new_feature(client: TestClient):
       response = client.post("/new-feature", json={
           "field1": "value",
           "field2": 42
       })
       assert response.status_code == 200
       assert response.json()["status"] == "success"
   ```

### Adding a New React Component

1. **Create Component** (`frontend/src/components/`)

   ```typescript
   import React from 'react';

   interface NewComponentProps {
     title: string;
     onAction: () => void;
   }

   export const NewComponent: React.FC<NewComponentProps> = ({ title, onAction }) => {
     return (
       <div className="new-component">
         <h2>{title}</h2>
         <button onClick={onAction}>Action</button>
       </div>
     );
   };
   ```

2. **Add Styles** (if needed)

   ```typescript
   // Use Tailwind CSS classes or styled-components
   ```

3. **Write Tests** (if complex logic)

   ```typescript
   import { render, screen, fireEvent } from '@testing-library/react';
   import { NewComponent } from './NewComponent';

   test('renders and handles action', () => {
     const mockAction = jest.fn();
     render(<NewComponent title="Test" onAction={mockAction} />);

     expect(screen.getByText('Test')).toBeInTheDocument();
     fireEvent.click(screen.getByRole('button'));
     expect(mockAction).toHaveBeenCalled();
   });
   ```

### Modifying PPTAgent Pipeline

**Location**: `backend/app/pptagent_core/roles/`

Each stage is a separate module:

- `schema_extractor.py`: Markdown structure analysis
- `content_organizer.py`: Content segmentation
- `layout_selector.py`: Layout decision logic
- `editor.py`: Content refinement
- `coder.py`: PPTX file generation

**Pattern**:

```python
from app.services.llm_service import LLMService

class NewStage:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def process(self, input_data):
        # Use LLM
        prompt = self._build_prompt(input_data)
        result = await self.llm.generate(prompt)

        # Process result
        return self._parse_result(result)

    def _build_prompt(self, input_data):
        # Construct prompt from template
        pass

    def _parse_result(self, result):
        # Parse LLM output
        pass
```

## 🔍 Debugging

### Backend Debugging

**Enable Debug Mode**:

```bash
# .env
DEBUG=true
```

**Add Breakpoints**:

```python
import pdb; pdb.set_trace()  # Standard debugger
# or
import ipdb; ipdb.set_trace()  # Enhanced debugger
```

**Logging**:

```python
import logging

logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

### Frontend Debugging

**Browser DevTools**:

- Use React DevTools extension
- Use Redux DevTools (if using Redux)

**Console Debugging**:

```typescript
console.log('Debug:', data);
console.table(arrayData);
console.trace('Call stack');
```

## 📊 Performance Optimization

### Backend Performance

**Profiling**:

```bash
# Install profiler
pip install py-spy

# Profile running application
py-spy top --pid <pid>

# Generate flamegraph
py-spy record -o profile.svg -- python app/main.py
```

**Optimization Checklist**:

- ✅ Use async/await for I/O operations
- ✅ Implement caching (L1/L2/L3)
- ✅ Batch LLM requests where possible
- ✅ Use connection pooling for Redis
- ✅ Profile and optimize hot paths

### Frontend Performance

**Tools**:

- Chrome DevTools Performance tab
- Lighthouse audits
- React Profiler

**Optimization Checklist**:

- ✅ Use React.memo for expensive components
- ✅ Implement virtualization for long lists
- ✅ Code splitting with React.lazy
- ✅ Optimize bundle size
- ✅ Use web workers for heavy computation

## 🐛 Troubleshooting

### Common Issues

**Issue**: Redis connection failed

```bash
# Solution: Start Redis
redis-server

# Verify
redis-cli ping
# Should return: PONG
```

**Issue**: Ollama model not found

```bash
# Solution: Pull model
ollama pull gpt-oss:20b

# List models
ollama list
```

**Issue**: Import errors after dependency update

```bash
# Solution: Reinstall dependencies
cd backend
pip install -e ".[dev]"

cd ../frontend
npm install
```

**Issue**: Tests failing with cache errors

```bash
# Solution: Clear test cache
rm -rf backend/data/cache/*
pytest --cache-clear
```

## 📚 Additional Resources

### Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [React Documentation](https://react.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)

### Internal Docs

- [Architecture Analysis](docs/architectural_analysis_report.md)
- [Implementation Workflow](docs/implementation_workflow.md)
- [API Documentation](http://localhost:8000/docs)

### Tools

- **Code Editor**: VSCode with Python, TypeScript, React extensions
- **API Testing**: Postman, HTTPie, or curl
- **Database**: RedisInsight for Redis GUI
- **Monitoring**: Prometheus + Grafana (production)

## 🔐 Security Guidelines

### Secrets Management

- **Never commit secrets** to version control
- Use `.env` for local development
- Use environment variables in production
- Use secrets management service (e.g., HashiCorp Vault) for production

### Input Validation

```python
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    content: str

    @validator('content')
    def validate_content(cls, v):
        if len(v) > 100000:
            raise ValueError('Content too large')
        return v
```

### Security Checklist

- ✅ Validate all user inputs
- ✅ Use parameterized queries (prevent SQL injection)
- ✅ Sanitize LLM outputs
- ✅ Implement rate limiting
- ✅ Use HTTPS in production
- ✅ Keep dependencies updated
- ✅ Run security scans (Bandit, npm audit)

## 🚀 Deployment

### Local Development

```bash
# Use development servers
uvicorn app.main:app --reload
npm run dev
```

### Production Build

```bash
# Backend
cd backend
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run build
# Serve from dist/ directory
```

### Docker Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

---

**Last Updated**: 2025-12-30
**Maintainers**: Development Team
