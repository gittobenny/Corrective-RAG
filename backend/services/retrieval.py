# retriever on pdf chunks

from langchain_core.documents import Document

from backend.config import get_settings
from backend.repositories.documents import DocumentRepository
from backend.services.embeddings import embed_texts
from backend.services.weaviate_store import search_chunks


def retrieve_pdf_evidence(question: str, collection_id: str) -> list[Document]:
    settings = get_settings()
    repository = DocumentRepository(settings.metadata_db_path)
    ready_ids = repository.ready_document_ids(collection_id)
    if not ready_ids:
        return []
    query_vector = embed_texts([question])[0]
    documents = search_chunks(
        vector=query_vector,
        collection_id=collection_id,
        ready_document_ids=ready_ids,
        limit=settings.retrieval_limit,
    )
    records: dict[str, dict] = {}
    for document in documents:
        document_id = str(document.metadata.get("document_id", ""))
        if not document_id:
            continue
        if document_id not in records:
            records[document_id] = repository.get(document_id) or {}
        record = records[document_id]
        document.metadata.update(
            {
                "document_status": record.get("status"),
                "document_size": record.get("size"),
                "chunks_stored": record.get("chunks_stored"),
                "document_error": record.get("error"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
            }
        )
    return documents
