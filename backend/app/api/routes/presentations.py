"""
Presentation Download API routes
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.services.presentation_storage import PresentationStorage, get_presentation_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/presentations", tags=["presentations"])


@router.get("/{presentation_id}/download")
async def download_presentation(
    presentation_id: str,
    storage: PresentationStorage = Depends(get_presentation_storage),
):
    """
    Download generated presentation

    Args:
        presentation_id: Unique presentation identifier
        storage: Presentation storage dependency

    Returns:
        FileResponse with PPTX file

    Raises:
        HTTPException: If presentation not found
    """
    try:
        # Get presentation file path
        file_path = await storage.get_presentation_path(presentation_id)

        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Presentation not found: {presentation_id}"
            )

        # Get metadata for filename
        metadata = await storage.get_presentation_metadata(presentation_id)
        filename = (
            f"{metadata['title']}.pptx"
            if metadata and metadata.get("title")
            else f"{presentation_id}.pptx"
        )

        # Clean filename (remove invalid characters, but preserve "." for extension)
        filename = "".join(c if c.isalnum() or c in (" ", "_", "-", ".") else "_" for c in filename)

        logger.info(f"Downloading presentation: {presentation_id}")

        return FileResponse(
            path=str(file_path),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=filename,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download presentation {presentation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to download presentation: {str(e)}")


@router.get("/{presentation_id}/metadata")
async def get_presentation_metadata(
    presentation_id: str,
    storage: PresentationStorage = Depends(get_presentation_storage),
):
    """
    Get presentation metadata

    Args:
        presentation_id: Unique presentation identifier
        storage: Presentation storage dependency

    Returns:
        Metadata dictionary

    Raises:
        HTTPException: If presentation not found
    """
    try:
        metadata = await storage.get_presentation_metadata(presentation_id)

        if not metadata:
            raise HTTPException(
                status_code=404, detail=f"Presentation not found: {presentation_id}"
            )

        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metadata for {presentation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get metadata: {str(e)}")


@router.delete("/{presentation_id}")
async def delete_presentation(
    presentation_id: str,
    storage: PresentationStorage = Depends(get_presentation_storage),
):
    """
    Delete presentation

    Args:
        presentation_id: Unique presentation identifier
        storage: Presentation storage dependency

    Returns:
        Success message

    Raises:
        HTTPException: If presentation not found or deletion failed
    """
    try:
        deleted = await storage.delete_presentation(presentation_id)

        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"Presentation not found: {presentation_id}"
            )

        logger.info(f"Presentation deleted: {presentation_id}")

        return {"success": True, "message": f"Presentation {presentation_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete presentation {presentation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete presentation: {str(e)}")
