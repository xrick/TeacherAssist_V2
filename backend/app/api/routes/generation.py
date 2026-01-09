"""
Generation API routes
"""

import json
import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.api.routes.scripts import store_script
from app.api.schemas.generation import (
    GenerationRequest,
    GenerationResponse,
)
from app.core.config import settings
from app.services.ppt_service import PPTService, get_ppt_service
from app.services.pptx_builder import PPTXBuilder
from app.services.presentation_storage import PresentationStorage, get_presentation_storage
from app.services.script_service import ScriptService, get_script_service
from app.services.slide_image_service import SlideImageService, get_slide_image_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/generate", tags=["generation"])


@router.post("/", response_model=GenerationResponse)
async def generate_presentation(
    request: GenerationRequest,
    ppt_service: PPTService = Depends(get_ppt_service),
    storage: PresentationStorage = Depends(get_presentation_storage),
    slide_image_service: SlideImageService = Depends(get_slide_image_service),
    script_service: ScriptService = Depends(get_script_service),
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

        # Generate presentation model
        presentation = await ppt_service.generate_presentation(
            markdown_content=request.markdown_content,
            title=request.title,
            author=request.author,
            template=request.template,
            audience=request.audience,
            tone=request.tone,
            slide_count=request.slide_count,
        )

        # Add images to slides (auto-配圖)
        try:
            logger.info("Adding images to presentation slides...")
            presentation = await slide_image_service.add_images_to_presentation(
                presentation=presentation,
                images_per_slide=1,
            )
            logger.info("Images added successfully")
        except Exception as img_error:
            logger.warning(f"Failed to add images, continuing without: {img_error}")

        # Build PPTX file
        template_path = None
        if request.template:
            template_path = settings.template_storage_path / f"{request.template}.pptx"
            if not template_path.exists():
                template_path = None
                logger.warning(f"Template not found: {request.template}, using default")

        builder = PPTXBuilder(template_path)
        pptx_bytes = builder.build(presentation)

        # Save to storage
        presentation_id = str(uuid.uuid4())
        await storage.save_presentation(presentation_id, presentation, pptx_bytes)

        logger.info(f"Presentation saved: {presentation_id}")

        # Generate teaching script
        try:
            logger.info("Generating teaching script...")
            script = await script_service.generate_presentation_script(
                presentation=presentation,
                presentation_id=presentation_id,
            )
            store_script(presentation_id, script)
            logger.info(f"Script generated: {script.total_minutes:.1f} minutes")
        except Exception as script_error:
            logger.warning(f"Failed to generate script, continuing without: {script_error}")

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
    storage: PresentationStorage = Depends(get_presentation_storage),
    slide_image_service: SlideImageService = Depends(get_slide_image_service),
    script_service: ScriptService = Depends(get_script_service),
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
    # Capture storage in closure
    presentation_storage = storage

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
                slide_count=request.slide_count,
            ):
                if "error" in update:
                    # Error event
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": update["error"]}),
                    }
                    break

                elif "result" in update:
                    # Completion event - build and save PPTX
                    presentation = update["result"]

                    try:
                        # Add images to slides (auto-配圖)
                        yield {
                            "event": "progress",
                            "data": json.dumps(
                                {
                                    "stage": "adding_images",
                                    "progress": 85,
                                    "message": "Adding images to slides...",
                                }
                            ),
                        }

                        try:
                            presentation = await slide_image_service.add_images_to_presentation(
                                presentation=presentation,
                                images_per_slide=1,
                            )
                        except Exception as img_error:
                            logger.warning(f"Failed to add images: {img_error}")

                        # Build PPTX file
                        template_path = None
                        if request.template:
                            template_path = (
                                settings.template_storage_path / f"{request.template}.pptx"
                            )
                            if not template_path.exists():
                                template_path = None

                        builder = PPTXBuilder(template_path)
                        pptx_bytes = builder.build(presentation)

                        # Save to storage
                        await presentation_storage.save_presentation(
                            presentation_id, presentation, pptx_bytes
                        )

                        logger.info(f"Presentation saved: {presentation_id}")

                        # Generate teaching script
                        yield {
                            "event": "progress",
                            "data": json.dumps(
                                {
                                    "stage": "generating_script",
                                    "progress": 92,
                                    "message": "Generating teaching script...",
                                }
                            ),
                        }

                        script_generated = False
                        try:
                            script = await script_service.generate_presentation_script(
                                presentation=presentation,
                                presentation_id=presentation_id,
                            )
                            store_script(presentation_id, script)
                            script_generated = True
                            logger.info(f"Script generated: {script.total_minutes:.1f} min")
                        except Exception as script_error:
                            logger.warning(f"Failed to generate script: {script_error}")

                        yield {
                            "event": "complete",
                            "data": json.dumps(
                                {
                                    "presentation_id": presentation_id,
                                    "slide_count": presentation.slide_count(),
                                    "download_url": f"/api/v1/presentations/{presentation_id}/download",
                                    "script_generated": script_generated,
                                    "stats": update.get("stats", {}),
                                }
                            ),
                        }

                    except Exception as build_error:
                        logger.error(f"Failed to build/save PPTX: {build_error}", exc_info=True)
                        yield {
                            "event": "error",
                            "data": json.dumps(
                                {"error": f"Failed to save presentation: {build_error}"}
                            ),
                        }

                else:
                    # Progress event
                    yield {
                        "event": "progress",
                        "data": json.dumps(
                            {
                                "stage": update["stage"],
                                "progress": update["progress"],
                                "message": update["message"],
                            }
                        ),
                    }

        except Exception as e:
            logger.error(f"Stream generation failed: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())
