from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated, List
from datetime import datetime

from app.dependencies import get_db, require_admin, get_optional_user
from sqlalchemy.orm import Session
from app.services.admin_service import AdminService
from app.schema.admin_schema import (
    BrandCreate,
    BrandResponse,
    SupplierCreate,
    SupplierResponse,
    CouponCreate,
    CouponResponse,
    PaymentMethodResponse,
    ShippingZoneResponse,
    CourierResponse,
    InventoryMovementCreate,
    InventoryMovementResponse,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    NotificationCreate,
    NotificationResponse,
    RejectionReasonResponse,
)
from app.schema.user_schema import UserPublic

router = APIRouter(tags=["Admin"])


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    return AdminService(db=db)


@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
def create_brand(
    create: BrandCreate,
    admin: Annotated[UserPublic, Depends(require_admin)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    return svc.create_brand(name=create.name, description=create.description)


@router.get("/brands", response_model=List[BrandResponse])
def list_brands(svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.list_brands()


@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(create: SupplierCreate, admin: Annotated[UserPublic, Depends(require_admin)], svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.create_supplier(name=create.name, contact_email=create.contact_email, contact_phone=create.contact_phone, address=create.address)


@router.get("/suppliers", response_model=List[SupplierResponse])
def list_suppliers(svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.list_suppliers()


@router.post("/coupons", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(create: CouponCreate, admin: Annotated[UserPublic, Depends(require_admin)], svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.create_coupon(code=create.code, is_percentage=create.is_percentage, amount=create.amount, description=create.description, active=create.active)


@router.get("/coupons", response_model=List[CouponResponse])
def list_coupons(svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.list_coupons()


@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
def list_payment_methods(svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.list_payment_methods()


@router.get("/shipping-zones", response_model=List[ShippingZoneResponse])
def list_shipping_zones(svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.list_shipping_zones()


@router.get("/couriers", response_model=List[CourierResponse])
def list_couriers(svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.list_couriers()


@router.post("/inventory/movements", response_model=InventoryMovementResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_movement(create: InventoryMovementCreate, admin: Annotated[UserPublic, Depends(require_admin)], svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.record_inventory_movement(product_id=create.product_id, change=create.change, reason=create.reason)


@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_order(create: PurchaseOrderCreate, admin: Annotated[UserPublic, Depends(require_admin)], svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.create_purchase_order(supplier_id=create.supplier_id, total_amount=create.total_amount, status=create.status)


@router.post("/notifications", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(create: NotificationCreate, admin: Annotated[UserPublic, Depends(require_admin)], svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.create_notification(user_id=create.user_id, title=create.title, message=create.message, type=create.type, order_id=create.order_id)


@router.get("/notifications/me", response_model=List[NotificationResponse])
def my_notifications(current_user: Annotated[UserPublic, Depends(get_optional_user)], svc: Annotated[AdminService, Depends(get_admin_service)]):
    if not current_user:
        return []
    return svc.list_notifications_for_user(current_user.id)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: Annotated[UserPublic, Depends(get_optional_user)],
    svc: Annotated[AdminService, Depends(get_admin_service)],
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return svc.mark_notification_read(notification_id)


@router.get("/rejection-reasons", response_model=List[RejectionReasonResponse])
def list_rejection_reasons(svc: Annotated[AdminService, Depends(get_admin_service)]):
    return svc.list_rejection_reasons()


# ═══════════════════════════════════════════════════════════════════
# Second section — dashboard, analytics, user & order management
# ═══════════════════════════════════════════════════════════════════
from fastapi import APIRouter, Depends, Query, status
from typing import Annotated, Optional
from datetime import datetime

from app.dependencies import require_admin, get_db
from app.services.admin_service import AdminService
from app.schema.admin_schema import (
    DashboardOverview,
    SalesAnalytics,
    UserAnalytics,
    ProductAnalytics,
    ReviewAnalytics,
    UserManagementResponse,
    UserDetailResponse,
    UpdateUserRoleRequest,
    OrderManagementResponse,
    UpdateOrderStatusRequest,
    MarkOrderShippedRequest,
    ReviewModerationResponse,
    InventoryAlert,
    InventoryResponse,
    BulkInventoryUpdateRequest,
    BulkInventoryUpdateResponse,
    RestockRequest,
    RestockResponse,
    ProfitReportResponse,
    ProductProfitReportResponse,
    OrderReportResponse,
    AdminWishlistResponse,
)
from app.schema.review_schema import ReviewResponse, ReviewReplyRequest
from app.schema.user_schema import UserPublic
from app.services.review_service import ReviewService
from sqlalchemy.orm import Session


def get_admin_service(db: Annotated[Session, Depends(get_db)]) -> AdminService:
    """Dependency to get admin service"""
    return AdminService(db=db)


# Analytics Endpoints
@router.get(
    "/dashboard",
    response_model=DashboardOverview,
    summary="Get complete dashboard overview",
    description="Get comprehensive analytics including sales, users, products, and reviews",
)
async def get_dashboard(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Get complete admin dashboard overview with all analytics"""
    return admin_service.get_dashboard_overview()


@router.get(
    "/analytics/sales",
    response_model=SalesAnalytics,
    summary="Get sales analytics",
    description="Get detailed sales analytics including revenue and order statistics",
)
async def get_sales_analytics(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Get sales analytics"""
    return admin_service.get_sales_analytics()


@router.get(
    "/analytics/users",
    response_model=UserAnalytics,
    summary="Get user analytics",
    description="Get user analytics including total users and growth metrics",
)
async def get_user_analytics(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Get user analytics"""
    return admin_service.get_user_analytics()


@router.get(
    "/analytics/products",
    response_model=ProductAnalytics,
    summary="Get product analytics",
    description="Get product analytics including inventory status",
)
async def get_product_analytics(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Get product analytics"""
    return admin_service.get_product_analytics()


@router.get(
    "/analytics/reviews",
    response_model=ReviewAnalytics,
    summary="Get review analytics",
    description="Get review analytics including approval status and average rating",
)
async def get_review_analytics(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Get review analytics"""
    return admin_service.get_review_analytics()


# User Management Endpoints
@router.get(
    "/users",
    response_model=UserManagementResponse,
    summary="List all users",
    description="Get paginated list of all users with optional search and role filters",
)
async def list_all_users(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    role: Optional[str] = Query(
        None, description="Filter by role: 'customer' or 'admin'"
    ),
):
    """List all users with pagination and filters"""
    return admin_service.get_all_users(
        page=page, page_size=page_size, search=search, role=role
    )


@router.patch(
    "/users/{user_id}/role",
    response_model=UserPublic,
    summary="Update user role",
    description="Change a user's role between 'customer' and 'admin'",
)
async def update_user_role(
    user_id: int,
    role_update: UpdateUserRoleRequest,
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Update a user's role"""
    user = admin_service.update_user_role(user_id=user_id, new_role=role_update.role)
    return UserPublic.model_validate(user)


@router.get(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="Get user detail",
    description="Get detailed user info with orders, spending, wishlist and stats",
)
async def get_user_detail(
    user_id: int,
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Get detailed information about a specific user/customer"""
    return admin_service.get_user_detail(user_id=user_id)


# Order Management Endpoints
@router.get(
    "/orders",
    response_model=OrderManagementResponse,
    summary="List all orders",
    description="Get paginated list of all orders with optional filters",
)
async def list_all_orders(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(
        None,
        description="Filter by status: 'pending', 'paid', 'shipped', 'delivered', 'cancelled'",
    ),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
):
    """List all orders with pagination and filters"""
    return admin_service.get_all_orders(
        page=page, page_size=page_size, status=status, user_id=user_id
    )


@router.patch(
    "/orders/{order_id}/status",
    summary="Update order status",
    description="Update an order's status",
)
async def update_order_status(
    order_id: int,
    status_update: UpdateOrderStatusRequest,
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Update an order's status"""
    order = admin_service.update_order_status(
        order_id=order_id, new_status=status_update.status
    )
    return {
        "message": "Order status updated successfully",
        "order_id": order.id,
        "new_status": order.status,
    }


@router.patch(
    "/orders/{order_id}/shipping",
    summary="Mark order as shipped",
    description="Mark an order as shipped and set shipping timestamp",
)
async def mark_order_shipped(
    order_id: int,
    shipping_data: MarkOrderShippedRequest,
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Mark an order as shipped"""
    order = admin_service.mark_order_shipped(
        order_id=order_id, shipped_at=shipping_data.shipped_at
    )
    return {
        "message": "Order marked as shipped",
        "order_id": order.id,
        "shipped_at": order.shipped_at,
    }


# Review Moderation Endpoints
@router.get(
    "/reviews/pending",
    response_model=ReviewModerationResponse,
    summary="Get pending reviews",
    description="Get paginated list of reviews awaiting approval",
)
async def get_pending_reviews(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Get pending reviews for moderation"""
    return admin_service.get_pending_reviews(page=page, page_size=page_size)


@router.get(
    "/reviews",
    response_model=ReviewModerationResponse,
    summary="Get all reviews",
    description="Get paginated list of all reviews",
)
async def get_all_reviews(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Get all reviews"""
    return admin_service.get_all_reviews(page=page, page_size=page_size)


@router.post(
    "/reviews/{review_id}/approve",
    summary="Approve review",
    description="Approve a pending review",
)
async def approve_review(
    review_id: int,
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Approve a review"""
    review = admin_service.approve_review(review_id=review_id)
    return {"message": "Review approved successfully", "review_id": review.id}


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reject/delete review",
    description="Reject and delete a review",
)
async def reject_review(
    review_id: int,
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Reject/delete a review"""
    admin_service.reject_review(review_id=review_id)
    return None


def get_review_service(db: Annotated[Session, Depends(get_db)]) -> ReviewService:
    return ReviewService(db=db)


@router.patch(
    "/reviews/{review_id}/reply",
    response_model=ReviewResponse,
    summary="Reply to a review",
    description="Admin replies to a customer review",
)
async def reply_to_review(
    review_id: int,
    payload: ReviewReplyRequest,
    review_service: Annotated[ReviewService, Depends(get_review_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Admin replies to a review"""
    return review_service.reply_to_review(review_id=review_id, user_id=current_admin.id, payload=payload)


# Wishlist Management Endpoint
@router.get("/wishlist", response_model=AdminWishlistResponse)
async def list_all_wishlists(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get paginated list of all wishlist items across users."""
    return admin_service.get_all_wishlists(page=page, page_size=page_size)


# Inventory Management Endpoints
@router.get("/inventory", response_model=InventoryResponse)
async def list_inventory(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by product name or SKU"),
    low_stock: Optional[bool] = Query(None, description="Filter products with stock < 10"),
):
    """Get paginated inventory list with last restock date and summary."""
    return admin_service.get_inventory(page=page, page_size=page_size, search=search, low_stock=low_stock)


@router.get(
    "/inventory/low-stock",
    response_model=list[InventoryAlert],
    summary="Get low stock alerts",
    description="Get products with stock below threshold",
)
async def get_low_stock_alerts(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
    threshold: int = Query(10, ge=1, description="Stock threshold for alerts"),
):
    """Get low stock product alerts"""
    return admin_service.get_low_stock_products(threshold=threshold)


@router.patch(
    "/inventory/bulk-update",
    response_model=BulkInventoryUpdateResponse,
    summary="Bulk update inventory",
    description="Update stock quantities for multiple products",
)
async def bulk_update_inventory(
    update_request: BulkInventoryUpdateRequest,
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Bulk update product inventory"""
    return admin_service.bulk_update_inventory(updates=update_request.updates)


@router.post("/inventory/restock", response_model=RestockResponse)
async def restock_product(
    payload: RestockRequest,
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
):
    """Restock a product — creates a stock batch for FIFO cost tracking"""
    return admin_service.restock_product(
        product_id=payload.product_id,
        variant_id=payload.variant_id,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        supplier_id=payload.supplier_id,
        new_buying_price=payload.new_buying_price,
        new_selling_price=payload.new_selling_price,
    )


@router.get("/reports/profit", response_model=ProfitReportResponse)
async def get_profit_report(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
    period: str = Query("all_time", description="Filter: today, week, month, all_time"),
):
    """Get profit/loss report across delivered orders"""
    return admin_service.get_profit_report(period=period)


@router.get("/reports/product-profit", response_model=ProductProfitReportResponse)
async def get_product_profit_report(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
    period: str = Query("all_time", description="Filter: today, week, month, year, all_time"),
):
    """Get per-product profit report"""
    return admin_service.get_product_profit_report(period=period)


@router.get("/reports/orders", response_model=OrderReportResponse)
async def get_orders_report(
    admin_service: Annotated[AdminService, Depends(get_admin_service)],
    current_admin: Annotated[UserPublic, Depends(require_admin)],
    period: str = Query("all_time", description="Filter: today, week, month, year, all_time"),
):
    """Get orders report listing all orders"""
    return admin_service.get_orders_report(period=period)
