# Queued PDF ingestion task.

from pathlib import Path

from backend.celery_app import celery_app
from backend.config import get_settings
from backend.repositories.documents import DocumentRepository
from backend.services.embeddings import embed_texts
from backend.services.pdf_processor import extract_pdf, split_pages
from backend.services.weaviate_store import store_chunks


@celery_app.task(bind=True, name="documents.process_pdf")
def process_pdf(
    self,
    *,
    document_id: str,
    collection_id: str,
    storage_path: str,
    original_filename: str,
) -> dict[str, str | int]:
    settings = get_settings()
    repository = DocumentRepository(settings.metadata_db_path)
    try:
        repository.update(document_id, status="extracting", error=None)
        pages = extract_pdf(Path(storage_path))
        chunks = split_pages(
            pages,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        repository.update(document_id, status="embedding")
        vectors = embed_texts([chunk.page_content for chunk in chunks])

        repository.update(document_id, status="storing")
        count = store_chunks(
            chunks=chunks,
            vectors=vectors,
            document_id=document_id,
            collection_id=collection_id,
            filename=original_filename,
        )
        repository.update(
            document_id,
            status="ready",
            chunks_stored=count,
            error=None,
        )
        return {
            "document_id": document_id,
            "status": "ready",
            "chunks_stored": count,
        }
    except Exception as error:
        repository.update(document_id, status="failed", error=str(error)[:1000])
        raise
