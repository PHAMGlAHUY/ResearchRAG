import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.dependencies import warmup
from api.routers import chat, health
from chat import InvalidQuestion
from core.setup_logging import setup_logging
from llm.generator import LLMError

logger = logging.getLogger('api')

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    try:
        warmup()
    except Exception:
        logger.exception("Warmup failed, server still running")
    yield

app = FastAPI(title="my_rag API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(chat.router)
app.include_router(health.router)

def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": message})

@app.exception_handler(InvalidQuestion)
async def _invalid_question(request: Request, exc: InvalidQuestion):
    return _error(400, str(exc))

@app.exception_handler(ConnectionError)
async def _connection_error(request: Request, exc: ConnectionError):
    return _error(503, str(exc))

@app.exception_handler(TimeoutError)
async def _timeout(request: Request, exc: TimeoutError):
    return _error(504, str(exc))

@app.exception_handler(LLMError)
async def _llm_error(request: Request, exc: LLMError):
    return _error(500, str(exc))

@app.exception_handler(Exception)
async def _unexpected(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return _error(500, "Unexpected error")
