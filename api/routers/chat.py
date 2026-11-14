from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.rate_limit import rate_limit
from api.schemas import ChatRequest, ChatResponse
from api.services import chat_service

router = APIRouter(prefix="/api", tags=["chat"], dependencies=[Depends(rate_limit)])


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest) -> ChatResponse:
    return chat_service.ask(req.question)


@router.post("/chat/stream")
def chat_stream_endpoint(req: ChatRequest) -> StreamingResponse:
    events = chat_service.start_stream(req.question)
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )