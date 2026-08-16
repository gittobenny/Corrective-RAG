#Streaming research endpoint used by the frontend

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.agents.research_agent import ConversationTurn, prepare_research, stream_answer
from backend.config import get_settings


router = APIRouter(prefix="/api", tags=["research"])
logger = logging.getLogger(__name__)


class ResearchRequest(BaseModel):
    request: str = Field(min_length=1, max_length=10_000)
    collection_id: str | None = Field(default=None, min_length=1, max_length=128)
    history: list[ConversationTurn] = Field(default_factory=list, max_length=6)


@router.post("/research", response_class=StreamingResponse)
async def research(payload: ResearchRequest) -> StreamingResponse:
    question = payload.request.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Research request cannot be blank")
    collection_id = payload.collection_id or get_settings().default_collection_id

    async def response_stream():
        try:
            preparation = prepare_research(question, collection_id, payload.history)
            async for chunk in stream_answer(preparation):
                yield chunk
        except LookupError as error:
            logger.info("Research evidence unavailable: %s", error)
            yield f"> Unable to complete the research request: {error}\n"
        except Exception:
            logger.exception("Research streaming failed")
            yield (
                "\n\n> Research stopped because a backend dependency "
                "could not complete the response. Check the backend log, API key, "
                "model availability, quota, and outbound network access.\n"
            )

    return StreamingResponse(
        response_stream(),
        media_type="text/markdown; charset=utf-8",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
