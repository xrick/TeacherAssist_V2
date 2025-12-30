"""
Template API routes
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.schemas.templates import (
    TemplateListResponse,
    TemplateResponse,
    TemplateStatsResponse,
)
from app.services.template_service import TemplateService, get_template_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    category: str | None = Query(None, description="Filter by category"),
    refresh: bool = Query(False, description="Force refresh template cache"),
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateListResponse:
    """
    List all available templates

    Args:
        category: Optional category filter
        refresh: Force cache refresh
        template_service: Template service dependency

    Returns:
        TemplateListResponse with list of templates
    """
    try:
        templates = await template_service.list_templates(category=category, refresh=refresh)

        # Convert to response models
        template_responses = [
            TemplateResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                category=t.category,
                preview_image=t.preview_image,
                tags=t.tags,
                created_at=t.created_at,
            )
            for t in templates
        ]

        # Get unique categories
        categories = list(set(t.category for t in templates))

        return TemplateListResponse(
            templates=template_responses,
            total=len(template_responses),
            categories=sorted(categories),
        )

    except Exception as e:
        logger.error(f"Failed to list templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    """
    Get specific template information

    Args:
        template_id: Template identifier
        template_service: Template service dependency

    Returns:
        TemplateResponse with template details

    Raises:
        HTTPException: If template not found
    """
    try:
        template = await template_service.get_template(template_id)

        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

        return TemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            category=template.category,
            preview_image=template.preview_image,
            tags=template.tags,
            created_at=template.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


@router.get("/stats", response_model=TemplateStatsResponse)
async def get_template_stats(
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateStatsResponse:
    """
    Get template statistics

    Args:
        template_service: Template service dependency

    Returns:
        TemplateStatsResponse with statistics
    """
    try:
        stats = await template_service.get_stats()
        return TemplateStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get template stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/{template_id}/download")
async def download_template(
    template_id: str,
    template_service: TemplateService = Depends(get_template_service),
):
    """
    Download template file

    Args:
        template_id: Template identifier
        template_service: Template service dependency

    Returns:
        FileResponse with PPTX file

    Raises:
        HTTPException: If template not found or invalid
    """
    try:
        # Validate template
        is_valid = await template_service.validate_template(template_id)
        if not is_valid:
            raise HTTPException(
                status_code=404, detail=f"Template not found or invalid: {template_id}"
            )

        # Get template path
        template_path = await template_service.get_template_path(template_id)

        if not template_path or not template_path.exists():
            raise HTTPException(status_code=404, detail=f"Template file not found: {template_id}")

        # Return file
        return FileResponse(
            path=str(template_path),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=f"{template_id}.pptx",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download template {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to download template: {str(e)}")
