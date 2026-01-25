"""
Generation API routes

使用新的 5 階段流程（含圖片）：
1. template_analysis - 分析 Template 結構
2. content_generation - LLM 擴展使用者輸入
3. content_organization - 組織內容到 Template 結構
4. image_enrichment - 注入圖片（可選）
5. pptx_building - 建構最終 PPTX
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
from app.pptagent_core.presentation.models import (
    ContentElement,
    ContentType,
    LayoutType,
    Presentation,
    PresentationMetadata,
    SlideContent,
)
from app.services.ppt_service_v2 import PPTServiceV2, get_ppt_service_v2
from app.services.presentation_storage import PresentationStorage, get_presentation_storage
from app.services.script_service import ScriptService, get_script_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/generate", tags=["generation"])


def _convert_to_presentation(
    organized_content: dict,
    title: str | None,
    author: str | None,
    template: str | None,
) -> Presentation:
    """
    將 PPTServiceV2 的輸出轉換為 Presentation model

    Args:
        organized_content: PPTServiceV2 的 draft_content
        title: 簡報標題
        author: 作者
        template: 模板名稱

    Returns:
        Presentation model
    """
    # 建立 metadata
    metadata = PresentationMetadata(
        title=title or organized_content.get("title", "Untitled"),
        author=author,
        template=template or "default.pptx",
    )

    # 建立 slides
    slides = []
    for slide_data in organized_content.get("slides", []):
        # 建立 elements
        elements = []

        # 從 bullet_points 建立元素
        bullet_points = slide_data.get("bullet_points", [])
        if bullet_points:
            content = "\n".join(bullet_points) if isinstance(bullet_points, list) else bullet_points
            elements.append(
                ContentElement(
                    type=ContentType.BULLET_LIST,
                    content=content,
                )
            )

        # 判斷 layout
        slide_type = slide_data.get("slide_type", "content")
        layout_map = {
            "title": LayoutType.TITLE,
            "content": LayoutType.CONTENT,
            "section": LayoutType.SECTION_HEADER,
            "closing": LayoutType.CLOSING,
        }
        layout = layout_map.get(slide_type, LayoutType.CONTENT)

        slide = SlideContent(
            title=slide_data.get("title", ""),
            elements=elements,
            notes=slide_data.get("speaker_notes"),
            layout=layout,
            metadata={
                "visual_suggestion": slide_data.get("visual_suggestion", ""),
            },
        )
        slides.append(slide)

    return Presentation(metadata=metadata, slides=slides)


@router.post("/", response_model=GenerationResponse)
async def generate_presentation(
    request: GenerationRequest,
    ppt_service: PPTServiceV2 = Depends(get_ppt_service_v2),
    storage: PresentationStorage = Depends(get_presentation_storage),
    script_service: ScriptService = Depends(get_script_service),
) -> GenerationResponse:
    """
    Generate a presentation from markdown content

    使用新的 4 階段流程生成簡報。

    Args:
        request: Generation request with markdown content and options

    Returns:
        GenerationResponse with presentation details

    Raises:
        HTTPException: If generation fails
    """
    try:
        logger.info(f"Generating presentation: {request.title or 'Untitled'}")

        # 使用 PPTServiceV2 生成 (5 階段流程，含圖片)
        # 先執行完整流程取得 draft_content 用於建立 Presentation model
        draft_content = None
        pptx_bytes = None
        image_count = 0

        async for update in ppt_service.generate_stream(
            user_input=request.markdown_content,
            template=request.template,
            slide_count=request.slide_count or 10,
            audience=request.audience,
            language=request.language,
            add_images=request.add_images,
            images_per_slide=request.images_per_slide,
        ):
            if "error" in update:
                raise ValueError(update["error"])
            if "result" in update:
                pptx_bytes = update["result"]
                draft_content = update.get("draft_content", {})
                # 統計圖片數量（從 enriched_content）
                enriched = update.get("enriched_content", draft_content)
                for slide in enriched.get("slides", []):
                    image_count += len(slide.get("images", []))

        if pptx_bytes is None:
            raise ValueError("Generation failed: no result")

        # 轉換為 Presentation model (用於 script 生成)
        presentation = _convert_to_presentation(
            draft_content or {},
            request.title,
            request.author,
            request.template,
        )
        # 圖片已由 ImageEnricher 在 PPTServiceV2 內部處理

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
            image_count=image_count,
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
    ppt_service: PPTServiceV2 = Depends(get_ppt_service_v2),
    storage: PresentationStorage = Depends(get_presentation_storage),
    script_service: ScriptService = Depends(get_script_service),
):
    """
    Generate a presentation with Server-Sent Events (SSE) progress updates

    使用新的 5 階段流程（含圖片）：
    1. template_analysis (0-10%)
    2. content_generation (10-40%)
    3. content_organization (40-60%)
    4. image_enrichment (60-80%) - 可選
    5. pptx_building (80-100%)

    Args:
        request: Generation request with markdown content and options

    Returns:
        StreamingResponse with SSE events

    Event format:
    ```
    event: progress
    data: {"stage": "template_analysis", "progress": 10, "message": "..."}

    event: complete
    data: {"presentation_id": "...", "slide_count": 10}

    event: error
    data: {"error": "..."}
    ```
    """
    presentation_storage = storage

    async def event_generator() -> AsyncGenerator[dict, None]:
        """Generate SSE events for progress updates"""
        try:
            presentation_id = str(uuid.uuid4())
            pptx_bytes = None
            draft_content = None
            image_count = 0

            async for update in ppt_service.generate_stream(
                user_input=request.markdown_content,
                template=request.template,
                slide_count=request.slide_count or 10,
                audience=request.audience,
                language=request.language,
                add_images=request.add_images,
                images_per_slide=request.images_per_slide,
            ):
                if "error" in update:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": update["error"]}),
                    }
                    break

                elif "result" in update:
                    pptx_bytes = update["result"]
                    draft_content = update.get("draft_content", {})
                    stats = update.get("stats", {})
                    # 統計圖片數量（從 enriched_content）
                    enriched = update.get("enriched_content", draft_content)
                    for slide in enriched.get("slides", []):
                        image_count += len(slide.get("images", []))

                    try:
                        # 轉換為 Presentation model
                        presentation = _convert_to_presentation(
                            draft_content,
                            request.title,
                            request.author,
                            request.template,
                        )
                        # 圖片已由 ImageEnricher 在 PPTServiceV2 內部處理

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
                                    "image_count": image_count,
                                    "download_url": f"/api/v1/presentations/{presentation_id}/download",
                                    "script_generated": script_generated,
                                    "stats": stats,
                                }
                            ),
                        }

                    except Exception as build_error:
                        logger.error(f"Failed to save presentation: {build_error}", exc_info=True)
                        yield {
                            "event": "error",
                            "data": json.dumps(
                                {"error": f"Failed to save presentation: {build_error}"}
                            ),
                        }

                else:
                    # Progress event - 直接轉發 PPTServiceV2 的進度
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
