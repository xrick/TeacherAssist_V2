"""
Generation API routes
"""

import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.api.schemas.generation import (
    GenerationRequest,
    GenerationResponse,
)
from app.services.ppt_service import PPTService, get_ppt_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/generate", tags=["generation"])


@router.post("/", response_model=GenerationResponse)
async def generate_presentation(
    request: GenerationRequest,
    ppt_service: PPTService = Depends(get_ppt_service),
) -> GenerationResponse:
    """
    Generate a presentation from markdown content

    This endpoint generates a complete presentation synchronously.
    For progress updates, use the `/stream` endpoint instead.

    Args:
        request: Generation request with markdown content and options

    Returns:
        GenerationResponse with presentation details

    Raises:
        HTTPException: If generation fails
    """
    try:
        logger.info(f"Generating presentation: {request.title or 'Untitled'}")

        presentation = await ppt_service.generate_presentation(
            markdown_content=request.markdown_content,
            title=request.title,
            author=request.author,
            template=request.template,
            audience=request.audience,
            tone=request.tone,
        )

        presentation_id = str(uuid.uuid4())

        return GenerationResponse(
            success=True,
            message="Presentation generated successfully",
            presentation_id=presentation_id,
            slide_count=presentation.slide_count(),
            download_url=f"/api/v1/presentations/{presentation_id}/download",
            metadata={
                "title": presentation.metadata.title,
                "author": presentation.metadata.author,
                "template": presentation.metadata.template,
            },
        )

    except ValueError as e:
        logger.error(f"Validation error during generation: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/stream")
async def generate_presentation_stream(
    request: GenerationRequest,
    ppt_service: PPTService = Depends(get_ppt_service),
):
    """
    Generate a presentation with Server-Sent Events (SSE) progress updates

    This endpoint returns an SSE stream with real-time progress updates.
    The final event will contain the completed presentation.

    Args:
        request: Generation request with markdown content and options

    Returns:
        StreamingResponse with SSE events

    Event format:
    ```
    event: progress
    data: {"stage": "schema_extraction", "progress": 20, "message": "..."}

    event: complete
    data: {"presentation_id": "...", "slide_count": 10}

    event: error
    data: {"error": "..."}
    ```
    """

    async def event_generator() -> AsyncGenerator[dict, None]:
        """Generate SSE events for progress updates"""
        try:
            presentation_id = str(uuid.uuid4())

            async for update in ppt_service.generate_presentation_stream(
                markdown_content=request.markdown_content,
                title=request.title,
                author=request.author,
                template=request.template,
                audience=request.audience,
                tone=request.tone,
            ):
                if "error" in update:
                    # Error event
                    yield {
                        "event": "error",
                        "data": {"error": update["error"]},
                    }
                    break

                elif "result" in update:
                    # Completion event
                    presentation = update["result"]
                    yield {
                        "event": "complete",
                        "data": {
                            "presentation_id": presentation_id,
                            "slide_count": presentation.slide_count(),
                            "download_url": f"/api/v1/presentations/{presentation_id}/download",
                            "stats": update.get("stats", {}),
                        },
                    }

                else:
                    # Progress event
                    yield {
                        "event": "progress",
                        "data": {
                            "stage": update["stage"],
                            "progress": update["progress"],
                            "message": update["message"],
                        },
                    }

        except Exception as e:
            logger.error(f"Stream generation failed: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": {"error": str(e)},
            }

    return EventSourceResponse(event_generator())
