from fastapi import APIRouter

from api.dependencies import check_ollama, check_qdrant
from api.schemas import HealthResponse, ServiceStatus

router = APIRouter(prefix="/api", tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    q_ok, q_msg = check_qdrant()
    o_ok, o_msg = check_ollama()

    return HealthResponse(
        status="ok" if (q_ok and o_ok) else "degraded",
        qdrant=ServiceStatus(ok=q_ok, detail=q_msg),
        ollama=ServiceStatus(ok=o_ok, detail=o_msg)
    )
