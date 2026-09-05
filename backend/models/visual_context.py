"""
Sanitized visual context metadata.

The backend NEVER accepts raw screenshots. Every image handled here is
assumed to have already passed through the local privacy/redaction layer
before it reaches this service. We only ever store/return metadata and a
storage reference -- never re-expose raw bytes through JSON responses.
"""

from typing import Optional
from pydantic import BaseModel, Field


class SanitizedVisualContext(BaseModel):
    """Metadata describing a stored sanitized screenshot for a session."""

    session_id: str
    filename: Optional[str] = Field(None, description="Original filename, if provided")
    content_type: Optional[str] = Field(None, description="MIME type reported by the upload")
    size_bytes: int = Field(..., description="Size of the stored sanitized image in bytes")
    storage_ref: str = Field(..., description="Internal storage reference/path. Not a public download URL.")
    updated_at: str = Field(..., description="ISO-8601 timestamp of last update")


class VisualContextUploadResponse(BaseModel):
    session_id: str
    status: str
    message: str
    visual_context: SanitizedVisualContext
