from contextlib import asynccontextmanager

from fastapi import FastAPI

from .init_db import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="ML Service", version="0.1.0", lifespan=lifespan)


@app.get("/")
async def index() -> dict[str, str]:
    return {"message": "ML service is running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
