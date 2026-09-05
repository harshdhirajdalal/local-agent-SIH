from fastapi import APIRouter, File, HTTPException, UploadFile

from models.page import PageState, PageStateIn
from models.visual_context import SanitizedVisualContext, VisualContextUploadResponse

from services import state_service, visual_context_service

router = APIRouter(prefix="/sessions", tags=["state"])


@router.post("/{session_id}/state", response_model=PageState)
def update_state(session_id: str, payload: PageStateIn):
    """
    Receive sanitized structured UI/page state for a session.

    The payload here is expected to already be sanitized by the local
    privacy layer (e.g. sensitive elements flagged/redacted upstream).
    """
    return state_service.update_state(session_id, payload)


@router.post("/{session_id}/visual-context", response_model=VisualContextUploadResponse)
def upload_visual_context(session_id: str, sanitized_screenshot: UploadFile = File(...)):
    """
    Receive a SANITIZED screenshot for a session.

    IMPORTANT: This endpoint expects ONLY screenshots that have already been
    redacted/sanitized by the local privacy layer on the user's device. The
    backend performs no redaction of its own and must never be sent raw
    screenshots. There is intentionally no generic "/raw-screenshot" or
    "/screenshot" endpoint in this API.

    The file field name is `sanitized_screenshot` on purpose, to keep this
    privacy contract explicit at the API boundary.
    """
    visual_context = visual_context_service.save_sanitized_screenshot(session_id, sanitized_screenshot)
    return VisualContextUploadResponse(
        session_id=session_id,
        status="stored",
        message="Sanitized screenshot stored and associated with session.",
        visual_context=visual_context,
    )


@router.get("/{session_id}/visual-context", response_model=SanitizedVisualContext)
def get_visual_context(session_id: str):
    """Return metadata about the latest sanitized visual context, if any."""
    visual_context = visual_context_service.get_visual_context(session_id)
    if visual_context is None:
        raise HTTPException(status_code=404, detail=f"No sanitized visual context uploaded yet for session '{session_id}'.")
    return visual_context
