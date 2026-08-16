from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest

from backend.config import get_settings
from backend.main import app
import backend.rest.sources as sources


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_upload_queues_pdf(monkeypatch, tmp_path):
    settings = replace(
        get_settings(),
        upload_root=tmp_path / "uploads",
        metadata_db_path=tmp_path / "documents.sqlite3",
    )
    monkeypatch.setattr(sources, "get_settings", lambda: settings)
    monkeypatch.setattr(
        sources,
        "process_pdf",
        SimpleNamespace(delay=lambda **kwargs: SimpleNamespace(id="task-123")),
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/sources",
            files={
                "files": ("report.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")
            },
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["collection_id"] == "default"
    assert payload["uploaded"][0]["name"] == "report.pdf"
    assert payload["uploaded"][0]["task_id"] == "task-123"
    assert payload["uploaded"][0]["status"] == "queued"


@pytest.mark.anyio
async def test_upload_rejects_non_pdf(monkeypatch, tmp_path):
    settings = replace(
        get_settings(),
        upload_root=tmp_path / "uploads",
        metadata_db_path=tmp_path / "documents.sqlite3",
    )
    monkeypatch.setattr(sources, "get_settings", lambda: settings)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/sources",
            files={"files": ("notes.txt", b"not a pdf", "text/plain")},
        )

    assert response.status_code == 415
