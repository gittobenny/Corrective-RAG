from backend.repositories.documents import DocumentRepository


def test_document_lifecycle(tmp_path):
    repository = DocumentRepository(tmp_path / "documents.sqlite3")
    repository.create(
        document_id="doc-1",
        collection_id="default",
        original_filename="report.pdf",
        storage_path="/tmp/report.pdf",
        content_type="application/pdf",
        size=100,
    )
    repository.update("doc-1", task_id="task-1", status="embedding")
    repository.update("doc-1", status="ready", chunks_stored=4)

    document = repository.get("doc-1")
    assert document is not None
    assert document["status"] == "ready"
    assert document["task_id"] == "task-1"
    assert document["chunks_stored"] == 4
