from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.init_routes import init_routes
from app.core.logger import logger
from app.middleware.request_logger import LoggingMiddleware

# DB/user seeding
from app.db.database import SessionLocal
from app.crud.user import UserCrud
from app.schema.user_schema import CreateUserSchema


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Application starting...")

    # Startup tasks go here
    # Seed default admin user if missing
    db = SessionLocal()
    try:
        try:
            user_crud = UserCrud(db=db)
            admin_email = "admin@kallee.com"
            existing = user_crud.get_user_by_email(admin_email)
            if not existing:
                admin_data = CreateUserSchema(
                    email=admin_email,
                    password="admin123",
                    first_name="Admin",
                    last_name="",
                    phone="",
                )
                created = user_crud.create_user(admin_data)
                # ensure role is admin
                created.role = "admin"
                db.commit()
                logger.info("Created default admin user: %s", admin_email)
        except Exception as e:
            logger.exception("Failed to seed admin user: %s", e)
    finally:
        db.close()

    yield

    logger.info("Application shutting down...")

    # Shutdown tasks go here


class RootResponse(BaseModel):
    message: str


app = FastAPI(
    lifespan=lifespan,
    title="KALLEE BACKEND",
    description="RESTful API for managing the product catalog, user authentication, shopping carts, and order processing for the online store.",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "products",
            "description": "Operations related to product catalog management.",
        },
        {
            "name": "users",
            "description": "User authentication and profile management.",
        },
        {
            "name": "carts",
            "description": "Shopping cart operations.",
        },
        {
            "name": "orders",
            "description": "Order processing and history.",
        },
        {
            "name": "reviews",
            "description": "Write and retrieve product reviews.",
        },
        {
            "name": "payment",
            "description": "Payment processing.",
        },
    ],
    root_path="/api/v1",
    servers=[],
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware - Allow frontend requests from development ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite development server
        "http://localhost:3000",  # Alternative frontend port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Middleware
app.add_middleware(LoggingMiddleware)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    errors = {}

    for error in exc.errors():
        field = ".".join(map(str, error["loc"][1:]))
        errors[field] = error["msg"]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Validation failed for one or more fields.",
            "fields": errors,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
):
    logger.exception(exc)

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Database error. Please try again later."
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(exc)

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred."
        },
    )


@app.get("/", tags=["Root"], response_model=RootResponse)
async def read_root():
    return RootResponse(
        message="Welcome to the KALLEE E-Commerce API v1. Check out /docs for the API specification!"
    )


UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/upload/{file_path:path}")
async def serve_upload(file_path: str):
    full_path = (UPLOADS_DIR / file_path).resolve()
    # Ensure the resolved path is within UPLOADS_DIR (security check)
    if not str(full_path).startswith(str(UPLOADS_DIR.resolve())):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    if full_path.exists() and full_path.is_file():
        return FileResponse(str(full_path))
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


# Register all API routes
init_routes(app)

# Optional startup utilities
# seed_product()
# bulk_index_products()
# create_product_index()