"""
API schemas for presentation generation
"""

from typing import Any

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    """Request to generate a presentation"""

    markdown_content: str = Field(..., description="Source markdown content for the presentation")
    title: str | None = Field(
        None, description="Presentation title (auto-extracted if not provided)"
    )
    author: str | None = Field(None, description="Author name")
    template: str | None = Field("default.pptx", description="Template file to use")
    audience: str | None = Field(
        None, description="Target audience (e.g., 'professionals', 'students')"
    )
    tone: str | None = Field(None, description="Desired tone (e.g., 'professional', 'casual')")

    model_config = {
        "json_schema_extra": {
            "example": {
                "markdown_content": "# My Presentation\n\n## Introduction\n\nThis is a sample presentation...",
                "title": "My Awesome Presentation",
                "author": "John Doe",
                "template": "default.pptx",
                "audience": "professionals",
                "tone": "professional",
            }
        }
    }


class GenerationResponse(BaseModel):
    """Response after presentation generation"""

    success: bool
    message: str
    presentation_id: str = Field(..., description="Unique ID for the presentation")
    slide_count: int = Field(..., description="Number of slides generated")
    download_url: str | None = Field(None, description="URL to download the PPTX file")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ProgressUpdate(BaseModel):
    """Progress update during streaming generation"""

    stage: str = Field(..., description="Current generation stage")
    progress: float = Field(..., description="Completion percentage (0-100)")
    message: str = Field(..., description="Status message")
    error: str | None = Field(None, description="Error message if failed")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    version: str
    llm_provider: str
    llm_available: bool


class UsageStatsResponse(BaseModel):
    """LLM usage statistics"""

    provider: str
    model: str
    total_cost_today: float
    request_count_today: int
    daily_budget: float
    budget_remaining: float
    budget_usage_percent: float
    last_reset: str
