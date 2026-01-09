"""
API schemas for teaching script operations
"""

from datetime import datetime

from pydantic import BaseModel, Field


class InteractionQAResponse(BaseModel):
    """Interactive Q&A item"""

    question: str
    expected_answers: list[str]


class SlideScriptResponse(BaseModel):
    """Script for a single slide"""

    slide_index: int
    slide_title: str
    estimated_minutes: float

    lecture_content: str
    teaching_tips: list[str]
    interaction_qa: list[InteractionQAResponse]
    transition: str


class PresentationScriptResponse(BaseModel):
    """Complete script response"""

    presentation_id: str
    title: str
    total_minutes: float
    scripts: list[SlideScriptResponse]
    generated_at: datetime
    last_edited_at: datetime


class SlideScriptUpdateRequest(BaseModel):
    """Request to update a single slide's script"""

    lecture_content: str | None = Field(None, description="Updated lecture content")
    teaching_tips: list[str] | None = Field(None, description="Updated teaching tips")
    interaction_qa: list[InteractionQAResponse] | None = Field(None, description="Updated Q&A")
    transition: str | None = Field(None, description="Updated transition")
    estimated_minutes: float | None = Field(None, ge=0.5, le=30, description="Updated time")

    model_config = {
        "json_schema_extra": {
            "example": {
                "lecture_content": "各位同學，今天我們要來討論...",
                "teaching_tips": ["使用白板輔助說明", "觀察學生反應"],
                "estimated_minutes": 5.0,
            }
        }
    }


class PresentationScriptUpdateRequest(BaseModel):
    """Request to update entire presentation script"""

    scripts: list[SlideScriptUpdateRequest] = Field(
        ..., description="Updated scripts for each slide"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "scripts": [
                    {"lecture_content": "開場內容...", "estimated_minutes": 2.0},
                    {"lecture_content": "第二張內容...", "estimated_minutes": 5.0},
                ]
            }
        }
    }


class TimeAllocationRequest(BaseModel):
    """Request to adjust time allocation"""

    target_total_minutes: float | None = Field(
        None, ge=5, le=180, description="Target total duration in minutes"
    )
    slide_times: list[float] | None = Field(
        None, description="Individual slide times (must match slide count)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_total_minutes": 50.0,
            }
        }
    }


class TimeAllocationResponse(BaseModel):
    """Response after time allocation adjustment"""

    success: bool
    total_minutes: float
    slide_times: list[float]
    message: str


class RegenerateScriptRequest(BaseModel):
    """Request to regenerate script"""

    style: str = Field(
        default="conversational",
        description="Script style: conversational, formal, casual",
    )
    target_total_minutes: float | None = Field(
        None, ge=5, le=180, description="Optional target duration"
    )
    slide_indices: list[int] | None = Field(
        None, description="Specific slides to regenerate (None = all)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "style": "conversational",
                "target_total_minutes": 45.0,
            }
        }
    }


class ScriptExportResponse(BaseModel):
    """Response for script export"""

    success: bool
    format: str
    download_url: str
    file_size: int | None = None
