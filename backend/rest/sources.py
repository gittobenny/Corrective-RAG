#PDF upload and document-status endpoints

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from backend.config import get_settings
from backend.models.schemas import DocumentResponse, UploadedFile, UploadResponse
from backend.repositories.documents import DocumentRepository
from backend.tasks.document_tasks import process_pdf


router = APIRouter(prefix="/api", tags=["sources"])


def _save_pdf(file: UploadFile, destination: Path, maximum: int) -> int:
    size = 0
    first_chunk = True
    try:
        with destination.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                if first_chunk:
                    first_chunk = False
                    if not chunk.startswith(b"%PDF-"):
                        raise HTTPException(
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail=f"{file.filename or 'File'} is not a valid PDF",
                        )
                size += len(chunk)
                if size > maximum:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"{file.filename or 'File'} exceeds the upload limit",
                    )
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()
    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty files are not supported")
    return size


@router.post(
    "/sources",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_sources(files: list[UploadFile] = File(...)) -> UploadResponse:
    settings = get_settings()
    repository = DocumentRepository(settings.metadata_db_path)
    collection_id = settings.default_collection_id
    directory = settings.upload_root / collection_id
    directory.mkdir(parents=True, exist_ok=True)
    uploaded: list[UploadedFile] = []

    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF is required")

    for file in files:
        filename = file.filename or "document.pdf"
        if Path(filename).suffix.lower() != ".pdf":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"{filename} is not a PDF",
            )

        document_id = str(uuid4())
        destination = directory / f"{document_id}.pdf"
        size = _save_pdf(file, destination, settings.max_upload_bytes)
        content_type = file.content_type or "application/pdf"
        repository.create(
            document_id=document_id,
            collection_id=collection_id,
            original_filename=filename,
            storage_path=str(destination),
            content_type=content_type,
            size=size,
        )
        try:
            task = process_pdf.delay(
                document_id=document_id,
                collection_id=collection_id,
                storage_path=str(destination),
                original_filename=filename,
            )
        except Exception as error:
            repository.update(document_id, status="failed", error="Queue unavailable")
            raise HTTPException(status_code=503, detail="Document queue is unavailable") from error

        repository.update(document_id, task_id=task.id)
        uploaded.append(
            UploadedFile(
                name=filename,
                size=size,
                type=content_type,
                document_id=document_id,
                task_id=task.id,
                status="queued",
            )
        )

    return UploadResponse(uploaded=uploaded, collection_id=collection_id)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str) -> DocumentResponse:
    settings = get_settings()
    record = DocumentRepository(settings.metadata_db_path).get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(record)
