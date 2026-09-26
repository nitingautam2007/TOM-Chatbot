import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import chat, conversations, health, nlp, safety, screening
from app.core.config import settings
from app.database.connection import engine
from app.services.errors import DatabaseNotConfiguredError

# App loggers (chat/NLP/safety failures) must be visible: uvicorn only
# configures its own loggers, leaving the root logger at WARNING with no
# handler, so logger.info was silently dropped before this.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    if engine is not None:
        await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.version,
    lifespan=lifespan,
)

# Missing/misconfigured database → clear 503, not an opaque 500.
@app.exception_handler(DatabaseNotConfiguredError)
async def database_not_configured_handler(
    request: Request, exc: DatabaseNotConfiguredError
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": exc.detail})


# Configured-but-unreachable database (connection refused, pool exhausted)
# surfaces as a SQLAlchemyError. Map it to the same 503 contract shape so the
# client can tell "database unavailable" from "server bug", and make it
# observable server-side. Handled inside CORS, so the response carries
# Access-Control-Allow-Origin (a raw 500 does not).
@app.exception_handler(SQLAlchemyError)
async def database_unavailable_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.exception("Database unavailable on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503, content={"detail": "Database temporarily unavailable"}
    )


# Cross-origin writes: CORSMiddleware only sets response headers — it never
# rejects a non-preflighted request, so a foreign web page could POST into the
# local shared user's data. Reject any request the browser labels with a
# foreign Origin. Requests without an Origin (curl, TestClient, navigation)
# are unaffected; registered after CORS below so CORS stays outermost.
@app.middleware("http")
async def reject_foreign_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.allowed_origins:
        return JSONResponse(
            status_code=403, content={"detail": "Cross-origin requests are not allowed"}
        )
    return await call_next(request)


# Catch-all: keep the {"detail": ...} JSON contract for unexpected errors and
# log them with a traceback. Lives in middleware (not exception_handler(Exception),
# which runs outside CORS and would emit a header-less plain-text 500).
@app.middleware("http")
async def unexpected_error_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:  # noqa: BLE001 — last line of defence; logged, never leaked
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )


# CORS: allow only the local React dev server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(nlp.router)  # Phase 3A — development/testing only
app.include_router(safety.router)  # Phase 4 — crisis-language screening
app.include_router(screening.router)  # Phase 5 — PHQ-9 screening


@app.get("/", tags=["root"])
async def root() -> dict:
    """Project name, API status and version."""
    return {
        "name": settings.app_name,
        "status": "running",
        "version": settings.version,
    }
