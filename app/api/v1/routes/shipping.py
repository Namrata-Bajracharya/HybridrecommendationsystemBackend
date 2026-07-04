from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Annotated, Generator
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services import shipping_service

router = APIRouter(tags=["Shipping"])


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ShippingCalculateRequest(BaseModel):
    latitude: float
    longitude: float
    district: Optional[str] = None
    zone: Optional[str] = None


class ShippingCalculateResponse(BaseModel):
    cost: int
    method: str
    distance_km: Optional[float] = None


@router.get(
    "/settings",
    summary="Get store settings (tax, shop location, shipping rates)",
)
async def get_settings(
    db: Annotated[Session, Depends(get_db)],
):
    return shipping_service.get_settings(db)


@router.post(
    "/shipping/calculate",
    response_model=ShippingCalculateResponse,
    summary="Calculate shipping cost based on customer location",
)
async def calculate_shipping(
    req: ShippingCalculateRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return shipping_service.calculate_shipping(
        db,
        customer_lat=req.latitude,
        customer_lng=req.longitude,
        customer_district=req.district,
        customer_zone=req.zone,
    )
