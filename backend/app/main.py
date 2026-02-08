import logging
import os
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.chat.router import router as chat_router
from app.config import settings
from app.ingestion.router import router as ingestion_router

# Set LangSmith env vars before any imports that might use them
os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
os.environ["LANGSMITH_TRACING"] = settings.langsmith_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="RAG Masterclass API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)
app.include_router(ingestion_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
