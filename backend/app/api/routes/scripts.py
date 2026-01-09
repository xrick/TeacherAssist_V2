"""
Teaching Script API routes

Provides endpoints for script generation, editing, and export.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.schemas.scripts import (
    InteractionQAResponse,
    PresentationScriptResponse,
    PresentationScriptUpdateRequest,
    RegenerateScriptRequest,
    SlideScriptResponse,
    SlideScriptUpdateRequest,
    TimeAllocationRequest,
    TimeAllocationResponse,
)
from app.services.presentation_storage import PresentationStorage, get_presentation_storage
from app.services.script_service import (
    InteractionQA,
    PresentationScript,
    ScriptService,
    ScriptStyle,
    get_script_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scripts", tags=["scripts"])

# In-memory script storage (in production, use database)
_script_storage: dict[str, PresentationScript] = {}


def _script_to_response(script: PresentationScript) -> PresentationScriptResponse:
    """Convert PresentationScript to API response."""
    return PresentationScriptResponse(
        presentation_id=script.presentation_id,
        title=script.title,
        total_minutes=script.total_minutes,
        scripts=[
            SlideScriptResponse(
                slide_index=s.slide_index,
                slide_title=s.slide_title,
                estimated_minutes=s.estimated_minutes,
                lecture_content=s.lecture_content,
                teaching_tips=s.teaching_tips,
                interaction_qa=[
                    InteractionQAResponse(
                        question=qa.question,
                        expected_answers=qa.expected_answers,
                    )
                    for qa in s.interaction_qa
                ],
                transition=s.transition,
            )
            for s in script.scripts
        ],
        generated_at=script.generated_at,
        last_edited_at=script.last_edited_at,
    )


@router.get("/{presentation_id}", response_model=PresentationScriptResponse)
async def get_script(
    presentation_id: str,
    storage: PresentationStorage = Depends(get_presentation_storage),
) -> PresentationScriptResponse:
    """
    Get teaching script for a presentation.

    Args:
        presentation_id: Presentation ID

    Returns:
        PresentationScriptResponse with all slide scripts
    """
    # Check if script exists
    if presentation_id not in _script_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Script not found for presentation: {presentation_id}",
        )

    script = _script_storage[presentation_id]
    return _script_to_response(script)


@router.put("/{presentation_id}", response_model=PresentationScriptResponse)
async def update_script(
    presentation_id: str,
    request: PresentationScriptUpdateRequest,
) -> PresentationScriptResponse:
    """
    Update entire presentation script.

    Args:
        presentation_id: Presentation ID
        request: Updated script data

    Returns:
        Updated PresentationScriptResponse
    """
    if presentation_id not in _script_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Script not found for presentation: {presentation_id}",
        )

    script = _script_storage[presentation_id]

    # Validate slide count
    if len(request.scripts) != len(script.scripts):
        raise HTTPException(
            status_code=400,
            detail=f"Script count mismatch: expected {len(script.scripts)}, got {len(request.scripts)}",
        )

    # Update each slide script
    from datetime import datetime

    for idx, update in enumerate(request.scripts):
        slide_script = script.scripts[idx]

        if update.lecture_content is not None:
            slide_script.lecture_content = update.lecture_content
        if update.teaching_tips is not None:
            slide_script.teaching_tips = update.teaching_tips
        if update.interaction_qa is not None:
            slide_script.interaction_qa = [
                InteractionQA(
                    question=qa.question,
                    expected_answers=qa.expected_answers,
                )
                for qa in update.interaction_qa
            ]
        if update.transition is not None:
            slide_script.transition = update.transition
        if update.estimated_minutes is not None:
            slide_script.estimated_minutes = update.estimated_minutes

    script.last_edited_at = datetime.utcnow()
    script.update_total_time()

    return _script_to_response(script)


@router.put("/{presentation_id}/slide/{slide_index}", response_model=SlideScriptResponse)
async def update_slide_script(
    presentation_id: str,
    slide_index: int,
    request: SlideScriptUpdateRequest,
) -> SlideScriptResponse:
    """
    Update a single slide's script.

    Args:
        presentation_id: Presentation ID
        slide_index: Slide index (0-based)
        request: Updated slide script data

    Returns:
        Updated SlideScriptResponse
    """
    if presentation_id not in _script_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Script not found for presentation: {presentation_id}",
        )

    script = _script_storage[presentation_id]

    if slide_index < 0 or slide_index >= len(script.scripts):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid slide index: {slide_index}",
        )

    slide_script = script.scripts[slide_index]

    # Apply updates
    from datetime import datetime

    if request.lecture_content is not None:
        slide_script.lecture_content = request.lecture_content
    if request.teaching_tips is not None:
        slide_script.teaching_tips = request.teaching_tips
    if request.interaction_qa is not None:
        slide_script.interaction_qa = [
            InteractionQA(
                question=qa.question,
                expected_answers=qa.expected_answers,
            )
            for qa in request.interaction_qa
        ]
    if request.transition is not None:
        slide_script.transition = request.transition
    if request.estimated_minutes is not None:
        slide_script.estimated_minutes = request.estimated_minutes

    script.last_edited_at = datetime.utcnow()
    script.update_total_time()

    return SlideScriptResponse(
        slide_index=slide_script.slide_index,
        slide_title=slide_script.slide_title,
        estimated_minutes=slide_script.estimated_minutes,
        lecture_content=slide_script.lecture_content,
        teaching_tips=slide_script.teaching_tips,
        interaction_qa=[
            InteractionQAResponse(
                question=qa.question,
                expected_answers=qa.expected_answers,
            )
            for qa in slide_script.interaction_qa
        ],
        transition=slide_script.transition,
    )


@router.post("/{presentation_id}/regenerate", response_model=PresentationScriptResponse)
async def regenerate_script(
    presentation_id: str,
    request: RegenerateScriptRequest,
    storage: PresentationStorage = Depends(get_presentation_storage),
    script_service: ScriptService = Depends(get_script_service),
) -> PresentationScriptResponse:
    """
    Regenerate teaching script.

    Args:
        presentation_id: Presentation ID
        request: Regeneration options

    Returns:
        Regenerated PresentationScriptResponse
    """
    try:
        # Get presentation
        presentation = await storage.get_presentation(presentation_id)
        if presentation is None:
            raise HTTPException(
                status_code=404,
                detail=f"Presentation not found: {presentation_id}",
            )

        # Parse style
        try:
            style = ScriptStyle(request.style.lower())
        except ValueError:
            style = ScriptStyle.CONVERSATIONAL

        # Regenerate specific slides or all
        if request.slide_indices:
            # Regenerate specific slides
            if presentation_id not in _script_storage:
                raise HTTPException(
                    status_code=404,
                    detail="No existing script to update. Regenerate all first.",
                )

            script = _script_storage[presentation_id]

            for idx in request.slide_indices:
                if 0 <= idx < len(script.scripts):
                    new_slide_script = await script_service.regenerate_slide_script(
                        presentation=presentation,
                        slide_index=idx,
                        style=style,
                    )
                    script.scripts[idx] = new_slide_script

            from datetime import datetime

            script.last_edited_at = datetime.utcnow()
            script.update_total_time()

        else:
            # Regenerate all
            script = await script_service.generate_presentation_script(
                presentation=presentation,
                presentation_id=presentation_id,
                style=style,
                target_total_minutes=request.target_total_minutes,
            )
            _script_storage[presentation_id] = script

        return _script_to_response(script)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Script regeneration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")


@router.put("/{presentation_id}/time-allocation", response_model=TimeAllocationResponse)
async def adjust_time_allocation(
    presentation_id: str,
    request: TimeAllocationRequest,
) -> TimeAllocationResponse:
    """
    Adjust time allocation for slides.

    Args:
        presentation_id: Presentation ID
        request: Time allocation settings

    Returns:
        TimeAllocationResponse with updated times
    """
    if presentation_id not in _script_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Script not found for presentation: {presentation_id}",
        )

    script = _script_storage[presentation_id]

    from datetime import datetime

    if request.slide_times:
        # Set individual slide times
        if len(request.slide_times) != len(script.scripts):
            raise HTTPException(
                status_code=400,
                detail=f"Slide time count mismatch: expected {len(script.scripts)}, got {len(request.slide_times)}",
            )

        for idx, time in enumerate(request.slide_times):
            script.scripts[idx].estimated_minutes = max(0.5, min(30, time))

    elif request.target_total_minutes:
        # Proportionally adjust all slides
        if script.total_minutes > 0:
            ratio = request.target_total_minutes / script.total_minutes
            for slide_script in script.scripts:
                slide_script.estimated_minutes = round(slide_script.estimated_minutes * ratio, 1)

    script.last_edited_at = datetime.utcnow()
    script.update_total_time()

    return TimeAllocationResponse(
        success=True,
        total_minutes=script.total_minutes,
        slide_times=[s.estimated_minutes for s in script.scripts],
        message=f"Time allocation updated. Total: {script.total_minutes:.1f} minutes",
    )


@router.get("/{presentation_id}/export/pdf")
async def export_script_pdf(
    presentation_id: str,
) -> FileResponse:
    """
    Export script as PDF.

    Args:
        presentation_id: Presentation ID

    Returns:
        PDF file download
    """
    if presentation_id not in _script_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Script not found for presentation: {presentation_id}",
        )

    # Import export service (will be created in Phase 3)
    try:
        from app.services.document_export_service import get_export_service

        export_service = get_export_service()
        script = _script_storage[presentation_id]

        file_path = await export_service.export_to_pdf(script, presentation_id)

        return FileResponse(
            path=str(file_path),
            filename=f"{script.title}_script.pdf",
            media_type="application/pdf",
        )
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="PDF export not yet implemented",
        )
    except Exception as e:
        logger.error(f"PDF export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/{presentation_id}/export/docx")
async def export_script_docx(
    presentation_id: str,
) -> FileResponse:
    """
    Export script as Word document.

    Args:
        presentation_id: Presentation ID

    Returns:
        DOCX file download
    """
    if presentation_id not in _script_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Script not found for presentation: {presentation_id}",
        )

    # Import export service (will be created in Phase 3)
    try:
        from app.services.document_export_service import get_export_service

        export_service = get_export_service()
        script = _script_storage[presentation_id]

        file_path = await export_service.export_to_docx(script, presentation_id)

        return FileResponse(
            path=str(file_path),
            filename=f"{script.title}_script.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="DOCX export not yet implemented",
        )
    except Exception as e:
        logger.error(f"DOCX export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# Helper function to store script (called from generation flow)
def store_script(presentation_id: str, script: PresentationScript):
    """Store script in memory storage."""
    _script_storage[presentation_id] = script


def get_stored_script(presentation_id: str) -> PresentationScript | None:
    """Get script from memory storage."""
    return _script_storage.get(presentation_id)
