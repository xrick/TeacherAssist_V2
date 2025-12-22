# app/api/routes.py
# app/routes.py

# app/api/routes.py

from fastapi import APIRouter, BackgroundTasks, WebSocket
from app.models import (
    GenerateRequest, GenerateResponse, 
    ProgressEvent, TemplateInfo
)

router = APIRouter(prefix="/api/v2")

@router.get("/templates")
async def list_templates() -> list[TemplateInfo]:
    """List available PPTX templates"""
    pass

@router.post("/presentations/generate")
async def generate_presentation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
) -> GenerateResponse:
    """
    Start async presentation generation.
    Returns task_id for progress tracking.
    """
    pass

@router.get("/presentations/{task_id}/status")
async def get_status(task_id: str) -> ProgressEvent:
    """Get current generation status"""
    pass

@router.get("/presentations/{task_id}/download")
async def download(task_id: str):
    """Download generated PPTX"""
    pass

@router.websocket("/ws/progress/{task_id}")
async def progress_websocket(websocket: WebSocket, task_id: str):
    """Real-time progress streaming"""
    pass