from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, List
from app.dependencies import get_current_user, require_admin
from app.schema.user_schema import UserPublic
from app.services.user_service import UserService
from app.dependencies import get_user_service_dep
from app.db.database import check_db_health
from sqlalchemy.orm import Session
from app.dependencies import get_db
from pydantic import BaseModel

router = APIRouter(tags=["Test"])

user_dependency = Annotated[UserService, Depends(get_user_service_dep)]

# In-memory data storage for demonstration (no database needed)
test_items_db = []
test_item_id_counter = 1


class HealthCheckResponse(BaseModel):
    status: str
    message: str
    database: str


class TestUserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_admin: bool


class TestItem(BaseModel):
    id: int
    title: str
    description: str
    price: float
    quantity: int


class TestItemCreate(BaseModel):
    title: str
    description: str
    price: float
    quantity: int


class TestItemUpdate(BaseModel):
    title: str = None
    description: str = None
    price: float = None
    quantity: int = None


@router.get("/health", response_model=HealthCheckResponse)
async def test_health_check(db: Session = Depends(get_db)):
    """
    Simple health check endpoint for testing.
    """
    is_healthy = check_db_health(db)
    return {
        "status": "ok" if is_healthy else "error",
        "message": "Server is running and healthy" if is_healthy else "Database connection failed",
        "database": "Connected" if is_healthy else "Disconnected",
    }


@router.get("/users", response_model=List[UserPublic])
async def test_get_all_users(
    user_service: user_dependency,
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """
    Test endpoint to fetch all users (admin only).
    Returns list of all users in the system.
    """
    return user_service.get_all_users()


# ============ CRUD Operations for Testing (In-Memory) ============

@router.get("/crud/items", response_model=List[TestItem])
async def get_all_items():
    """
    GET - Retrieve all test items from in-memory storage.
    No authentication required for testing.
    """
    return test_items_db


@router.post("/crud/items", response_model=TestItem, status_code=status.HTTP_201_CREATED)
async def create_item(item: TestItemCreate):
    """
    POST - Create a new test item.
    No authentication required for testing.
    """
    global test_item_id_counter
    new_item = TestItem(
        id=test_item_id_counter,
        title=item.title,
        description=item.description,
        price=item.price,
        quantity=item.quantity,
    )
    test_items_db.append(new_item)
    test_item_id_counter += 1
    return new_item


@router.get("/crud/items/{item_id}", response_model=TestItem)
async def get_item(item_id: int):
    """
    GET - Retrieve a specific test item by ID.
    No authentication required for testing.
    """
    for item in test_items_db:
        if item.id == item_id:
            return item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Item with id {item_id} not found",
    )


@router.put("/crud/items/{item_id}", response_model=TestItem)
async def update_item(item_id: int, item_update: TestItemUpdate):
    """
    PUT - Update a specific test item.
    No authentication required for testing.
    """
    for item in test_items_db:
        if item.id == item_id:
            # Update only provided fields
            if item_update.title is not None:
                item.title = item_update.title
            if item_update.description is not None:
                item.description = item_update.description
            if item_update.price is not None:
                item.price = item_update.price
            if item_update.quantity is not None:
                item.quantity = item_update.quantity
            return item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Item with id {item_id} not found",
    )


@router.delete("/crud/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int):
    """
    DELETE - Remove a specific test item.
    No authentication required for testing.
    """
    for i, item in enumerate(test_items_db):
        if item.id == item_id:
            test_items_db.pop(i)
            return
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Item with id {item_id} not found",
    )
