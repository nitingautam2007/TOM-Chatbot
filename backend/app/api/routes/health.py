from fastapi import APIRouter

from app.core.config import settings
from app.schemas.chat import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe for the API."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.version,
    )
