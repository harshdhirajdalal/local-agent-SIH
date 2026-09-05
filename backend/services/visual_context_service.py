"""
Handles storage of SANITIZED screenshots only.

This service must never be given, and never exposes, raw/original
screenshot bytes. Everything that reaches this module is assumed to have
already been redacted locally before upload. We deliberately avoid logging
image contents or filenames at anything above debug-free info level.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile

from storage import memory_store
from models.visual_context import SanitizedVisualContext
from services.session_service import require_session

# Temporary local storage for sanitized screenshots. Swap this for
# object storage later without touching API or model code.
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "sanitized_screenshots")
os.makedirs(STORAGE_DIR, exist_ok=True)

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}


def save_sanitized_screenshot(session_id: str, file: UploadFile) -> SanitizedVisualContext:
    require_session(session_id)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported content type '{file.content_type}'. "
                f"Expected one of: {sorted(ALLOWED_CONTENT_TYPES)}. "
                "This endpoint only accepts already-sanitized image files."
            ),
        )

    # One file per session -- each new upload replaces the previous
    # sanitized screenshot for that session.
    extension = os.path.splitext(file.filename or "")[1] or ".png"
    storage_ref = os.path.join(STORAGE_DIR, f"{session_id}{extension}")

    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded sanitized_screenshot file is empty.")

    with open(storage_ref, "wb") as f:
        f.write(contents)

    visual_context = SanitizedVisualContext(
        session_id=session_id,
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(contents),
        storage_ref=storage_ref,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    memory_store.update_visual_context(session_id, visual_context)

    # Intentionally: no logging of file contents or full paths beyond what
    # is needed for local debugging of this prototype.
    return visual_context


def get_visual_context(session_id: str) -> Optional[SanitizedVisualContext]:
    require_session(session_id)
    return memory_store.get_visual_context(session_id)
