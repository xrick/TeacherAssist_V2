# TeacherAssist Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React + TypeScript)                   │
│  ┌───────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐  │
│  │MarkdownEditor │→ │GenerationControl │→ │    ProgressMonitor (SSE)     │  │
│  └───────────────┘  └──────────────────┘  └──────────────────────────────┘  │
│          │                   │                          │                    │
│          ▼                   ▼                          ▼                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         ResultPreview                                  │  │
│  │  (Download PPTX / View Metadata / Delete Presentation)                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP/SSE
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND API (FastAPI)                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         API Routes                                      │ │
│  │  POST /api/v1/generate/        → Synchronous generation                │ │
│  │  POST /api/v1/generate/stream  → SSE streaming generation              │ │
│  │  GET  /api/v1/presentations/{id}/download → Download PPTX              │ │
│  │  GET  /api/v1/presentations/{id}/metadata → Get metadata               │ │
│  │  DELETE /api/v1/presentations/{id}        → Delete presentation        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         PPTService                                      │ │
│  │              (Orchestrates 5-Stage PPTAgent Pipeline)                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│  ┌───────────┐ ┌───────────────────┐ │ ┌───────────────────────────────────┐│
│  │LLMService │ │PresentationStorage│ │ │       PPTXBuilder                 ││
│  │(Ollama/   │ │(File-based PPTX   │◄┼►│(Converts Model → PPTX bytes)      ││
│  │ OpenAI)   │ │ + JSON metadata)  │ │ │                                   ││
│  └───────────┘ └───────────────────┘ │ └───────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```
