"""
Template API Schemas
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TemplateResponse(BaseModel):
    """Template information response"""

    id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    preview_image: str | None = Field(None, description="Preview image URL")
    tags: list[str] = Field(default_factory=list, description="Template tags")
    created_at: datetime = Field(..., description="Creation timestamp")


class TemplateListResponse(BaseModel):
    """List of templates response"""

    templates: list[TemplateResponse] = Field(..., description="Available templates")
    total: int = Field(..., description="Total number of templates")
    categories: list[str] = Field(..., description="Available categories")


class TemplateStatsResponse(BaseModel):
    """Template statistics response"""

    total_templates: int = Field(..., description="Total number of templates")
    categories: dict = Field(..., description="Templates per category")
    last_scan: str | None = Field(None, description="Last scan timestamp")
    templates_path: str = Field(..., description="Templates directory path")
