import json
import socketio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.init_routes import init_routes
from app.core.logger import logger
from app.middleware.request_logger import LoggingMiddleware
from app.websocket_manager import manager
from app.utils.security import decode_access_token, TokenError
from app.models.user import User
from fastapi import WebSocket, WebSocketDisconnect, Query
from app.socketio_server import sio

# DB/user seeding
from app.db.database import SessionLocal
from app.crud.user import UserCrud
from app.schema.user_schema import CreateUserSchema


def add_missing_columns(db):
    """Add columns that may not exist on existing SQLite tables."""
    migs = [
        ("addresses", "district", "VARCHAR(100)"),
        ("addresses", "zone", "VARCHAR(100)"),
        ("users", "shop_name", "VARCHAR(200)"),
        ("users", "shop_latitude", "FLOAT"),
        ("users", "shop_longitude", "FLOAT"),
        ("users", "shop_district", "VARCHAR(100)"),
        ("users", "shop_zone", "VARCHAR(100)"),
        ("orders", "contact_name", "VARCHAR(200)"),
        ("orders", "contact_phone", "VARCHAR(50)"),
        ("orders", "contact_email", "VARCHAR(255)"),
        ("orders", "payment_mode", "VARCHAR(50)"),
        ("orders", "shipping_cost", "NUMERIC(10,2)"),
        ("orders", "tax", "NUMERIC(10,2)"),
        ("orders", "discount", "NUMERIC(10,2)"),
        ("orders", "cancel_reason", "VARCHAR(500)"),
        ("orders", "cancelled_by", "VARCHAR(50)"),
        ("orders", "refund_reason", "VARCHAR(500)"),
    ]
    for table, col, coltype in migs:
        try:
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"))
            db.commit()
            logger.info("Added column %s.%s", table, col)
        except Exception:
            db.rollback()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Application starting...")

    db = SessionLocal()
    try:
        add_missing_columns(db)

        # Seed default admin user if missing
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
                created.role = "admin"
                created.is_verified = True
                created.shop_name = "Kallee Nepal"
                created.shop_latitude = 27.7172
                created.shop_longitude = 85.3240
                created.shop_district = "Kathmandu"
                created.shop_zone = "Bagmati"
                db.commit()
                logger.info("Created default admin user: %s", admin_email)
            else:
                # Update existing admin with shop info if not set
                existing.shop_name = existing.shop_name or "Kallee Nepal"
                existing.shop_latitude = existing.shop_latitude or 27.7172
                existing.shop_longitude = existing.shop_longitude or 85.3240
                existing.shop_district = existing.shop_district or "Kathmandu"
                existing.shop_zone = existing.shop_zone or "Bagmati"
                db.commit()
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


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(""),
):
    user_id = None
    is_admin = False
    if token:
        try:
            payload = decode_access_token(token)
            sub = payload.get("sub")
            if sub:
                user_id = int(sub)
                db = SessionLocal()
                try:
                    user = db.get(User, user_id)
                    if user:
                        is_admin = user.role == "admin"
                finally:
                    db.close()
        except (TokenError, ValueError, Exception):
            pass

    await manager.connect(websocket, user_id=user_id, is_admin=is_admin)
    try:
        while True:
            data = await websocket.receive_text()
            if data:
                try:
                    msg = json.loads(data)
                    msg_type = msg.get("type", "")
                    if msg_type == "ping":
                        await manager.send_json(websocket, {"type": "pong"})
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Optional startup utilities
# seed_product()
# bulk_index_products()
# create_product_index()