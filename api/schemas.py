from pydantic import BaseModel

class ChatRequest(BaseModel):
    question: str

class Source(BaseModel):
    index: int
    section: str
    score: float
    text: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    latency_ms: int

class ServiceStatus(BaseModel):
    ok: bool
    detail: str = ""

class HealthResponse(BaseModel):
    status: str
    qdrant: ServiceStatus
    ollama: ServiceStatus