from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .exceptions import (
    AuthenticationError,
    BrokerError,
    ConflictError,
    InsufficientBalanceError,
    InvalidDataError,
    NotFoundError,
    ServiceError,
)
from .init_db import initialize_database


def create_app(initialize: bool = True) -> FastAPI:
    web_directory = Path(__file__).parent / "web"

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if initialize:
            initialize_database()
        yield

    application = FastAPI(
        title="ML Service",
        version="0.2.0",
        lifespan=lifespan,
    )
    application.include_router(router)
    application.mount(
        "/static", StaticFiles(directory=web_directory / "static"), name="static"
    )
    application.add_exception_handler(ServiceError, service_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(web_directory / "index.html")

    @application.get("/auth", include_in_schema=False)
    async def auth_page() -> FileResponse:
        return FileResponse(web_directory / "auth.html")

    @application.get("/dashboard", include_in_schema=False)
    async def dashboard_page() -> FileResponse:
        return FileResponse(web_directory / "dashboard.html")

    @application.get("/history", include_in_schema=False)
    async def history_page() -> FileResponse:
        return FileResponse(web_directory / "history.html")

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    return application


async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
    status_code = 400
    headers = None
    if isinstance(exc, AuthenticationError):
        status_code = 401
        headers = {"WWW-Authenticate": "Bearer"}
    elif isinstance(exc, NotFoundError):
        status_code = 404
    elif isinstance(exc, ConflictError):
        status_code = 409
    elif isinstance(exc, InsufficientBalanceError):
        status_code = 409
    elif isinstance(exc, BrokerError):
        status_code = 503
    elif isinstance(exc, InvalidDataError):
        status_code = 400

    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": str(exc), "details": None}},
        headers=headers,
    )


async def validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": "Ошибка валидации данных",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


app = create_app()
