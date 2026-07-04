import math
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.crud.user import UserCrud

SHIPPING_RATES = [
    (0, 1, 50),
    (2, 5, 80),
    (6, 10, 200),
    (11, 20, 500),
]

CROSS_ZONE_SHIPPING = 800
BEYOND_20KM_SHIPPING = 500
TAX_PERCENTAGE = 15.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_admin_shop(db: Session) -> Optional[User]:
    return db.query(User).filter(User.role == "admin").first()


def get_settings(db: Session) -> dict:
    admin = get_admin_shop(db)
    shop_name = admin.shop_name if admin and admin.shop_name else "Kallee Nepal"
    shop_lat = admin.shop_latitude if admin and admin.shop_latitude else 27.7172
    shop_lng = admin.shop_longitude if admin and admin.shop_longitude else 85.3240
    shop_district = admin.shop_district if admin and admin.shop_district else "Kathmandu"
    shop_zone = admin.shop_zone if admin and admin.shop_zone else "Bagmati"
    return {
        "tax_percentage": TAX_PERCENTAGE,
        "shop_name": shop_name,
        "shop_latitude": shop_lat,
        "shop_longitude": shop_lng,
        "shop_district": shop_district,
        "shop_zone": shop_zone,
        "shipping_rates": [
            {"min_km": mn, "max_km": mx, "cost": ct}
            for mn, mx, ct in SHIPPING_RATES
        ],
        "beyond_20km_shipping": BEYOND_20KM_SHIPPING,
        "cross_zone_shipping": CROSS_ZONE_SHIPPING,
    }


def calculate_shipping(
    db: Session,
    customer_lat: float,
    customer_lng: float,
    customer_district: Optional[str] = None,
    customer_zone: Optional[str] = None,
) -> dict:
    admin = get_admin_shop(db)
    if not admin or not admin.shop_latitude or not admin.shop_longitude:
        return {"cost": 0, "method": "flat"}

    shop_district = admin.shop_district
    shop_zone = admin.shop_zone

    if (
        customer_district
        and customer_zone
        and shop_district
        and shop_zone
        and (customer_district.lower() != shop_district.lower() or customer_zone.lower() != shop_zone.lower())
    ):
        return {"cost": CROSS_ZONE_SHIPPING, "method": "cross_zone"}

    # If lat/lng are 0/0 or missing, fall back to a same-zone flat rate
    if not customer_lat or not customer_lng:
        return {"cost": 80, "method": "flat", "distance_km": 0}

    distance = haversine_km(customer_lat, customer_lng, admin.shop_latitude, admin.shop_longitude)

    for mn, mx, cost in SHIPPING_RATES:
        if mn <= distance <= mx:
            return {"cost": cost, "method": "distance", "distance_km": round(distance, 2)}

    return {
        "cost": BEYOND_20KM_SHIPPING,
        "method": "distance",
        "distance_km": round(distance, 2),
    }
