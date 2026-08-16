# API reference and processing workflows

This document describes the complete PDF-ingestion and research workflows, the available HTTP endpoints, and application error behavior.

## End-to-end processing

### Document ingestion

1. The frontend sends PDFs as repeated multipart fields named `files` to `POST /api/sources`.
2. FastAPI verifies the `.pdf` extension, `%PDF-` signature, and configured size limit.
3. The original file is stored at `uploads/{collection_id}/{document_id}.pdf`.
4. SQLite creates one document record with status `queued`.
5. FastAPI publishes a Celery task to Redis and immediately returns HTTP `202`.
6. The frontend polls `GET /api/documents/{document_id}` every two seconds.
7. Celery extracts page text with PyMuPDF and changes the status to `extracting`.
8. The text is recursively split into overlapping chunks.
9. Sentence Transformer vectors are created while the status is `embedding`.
10. Chunks and self-provided vectors are inserted into Weaviate while the status is `storing`.
11. SQLite is updated to `ready` with the stored chunk count, or `failed` with an error.
12. The frontend enables research after processing completes.

```text
queued → extracting → embedding → storing → ready
                                          └→ failed
```

### Adaptive research

1. Recent page-lifetime conversation history is used to clarify follow-up questions.
2. The contextual question is embedded with the same model used for document chunks.
3. Weaviate retrieves relevant chunks belonging to documents marked `ready` in SQLite.
4. Groq grades whether the local evidence is sufficient.
5. If evidence is insufficient and Tavily is configured, external search results are added.
6. Groq generates a grounded answer and streams Markdown chunks to the browser.
7. The backend appends numbered PDF citations, web links, and deduplicated document metadata.

Conversation history resolves references such as “What are its limitations?”, but previous model answers remain context rather than trusted evidence.

## Base URLs

Local FastAPI development:

```text
http://localhost:8787
```

Docker/Nginx deployment:

```text
http://SERVER_HOST:5173
```

Nginx proxies `/api/*` and `/health` to the internal FastAPI service.

## Health

```http
GET /health
```

Example response:

```json
{"status":"ok"}
```

## Upload PDFs

```http
POST /api/sources
Content-Type: multipart/form-data
```

The multipart field name is `files`. Multiple fields may be included in one request.

```bash
curl -X POST http://localhost:8787/api/sources \
  -F 'files=@/absolute/path/report.pdf'
```

Example HTTP `202` response:

```json
{
  "collection_id": "default",
  "uploaded": [
    {
      "name": "report.pdf",
      "size": 12345,
      "type": "application/pdf",
      "document_id": "7f90c78f-...",
      "task_id": "94a53e31-...",
      "status": "queued"
    }
  ]
}
```

## Document status

```http
GET /api/documents/{document_id}
```

```bash
curl http://localhost:8787/api/documents/DOCUMENT_ID
```

Research should begin only after `status` becomes `ready` and `chunks_stored` is greater than zero.

## Stream research

```http
POST /api/research
Content-Type: application/json
```

Example request:

```json
{
  "request": "Explain the Duration Score formula with citations",
  "history": [
    {"role": "user", "content": "What scoring formulas are defined?"},
    {"role": "assistant", "content": "The document defines several scores..."}
  ]
}
```

`history` is optional and limited to six messages. The frontend keeps this history in memory, does not display it, and clears it when the page is refreshed.

Test streaming without client-side buffering:

```bash
curl -N -X POST http://localhost:8787/api/research \
  -H 'Content-Type: application/json' \
  -d '{"request":"Summarize the uploaded report with citations"}'
```

The response media type is `text/markdown`. PDF sources use filename/page citations, and external sources use linked titles and URLs.

## Error handling

| Condition | Behavior |
|---|---|
| Unsupported extension | HTTP `415` |
| Invalid PDF signature | HTTP `415` |
| File exceeds configured limit | HTTP `413` |
| Empty upload | HTTP `400` |
| Queue unavailable | Document marked `failed`; HTTP `503` |
| Document ID not found | HTTP `404` |
| Extraction, embedding, or Weaviate failure | Error stored in SQLite; document marked `failed` |
| Image-only or scanned PDF | Document marked `failed` with an OCR-required message |
| Research dependency failure after streaming begins | Error logged and a readable Markdown error returned in the stream |

Invalid or partially written upload files are removed when validation fails.

## Testing

The current suite covers:

- SQLite document lifecycle.
- PDF extraction and chunking.
- Frontend-compatible streaming.
- Missing-evidence reporting.
- Adaptive web fallback routing.
- Temporary session-history propagation.
- One-based PDF citations.
- Upload queue dispatch.
- Unsupported-file rejection.