#Pydantic response schemas.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


DocumentStatus = Literal["queued", "extracting", "embedding", "storing", "ready", "failed"]


class UploadedFile(BaseModel):
    name: str
    size: int
    type: str
    document_id: str
    task_id: str
    status: DocumentStatus


class UploadResponse(BaseModel):
    uploaded: list[UploadedFile]
    collection_id: str


class DocumentResponse(BaseModel):
    document_id: str
    collection_id: str
    original_filename: str
    content_type: str
    size: int
    status: DocumentStatus
    task_id: str | None
    chunks_stored: int
    error: str | None
    created_at: datetime
    updated_at: datetime
