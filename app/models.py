# app/models.py


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