"""
Health check and monitoring routes
"""

import logging

from fastapi import APIRouter, Depends

from app.api.schemas.generation import HealthResponse, UsageStatsResponse
from app.core.config import settings
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint

    Returns system status and LLM provider information
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        llm_provider=settings.llm_provider,
        llm_available=True,  # TODO: Add actual LLM health check
    )


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    llm_service: LLMService = Depends(get_llm_service),
) -> UsageStatsResponse:
    """
    Get LLM usage statistics

    Returns current usage and budget information
    """
    stats = await llm_service.get_usage_stats()

    return UsageStatsResponse(
        provider=stats["provider"],
        model=stats["model"],
        total_cost_today=stats["total_cost_today"],
        request_count_today=stats["request_count_today"],
        daily_budget=stats["daily_budget"],
        budget_remaining=stats["budget_remaining"],
        budget_usage_percent=stats["budget_usage_percent"],
        last_reset=stats["last_reset"],
    )
