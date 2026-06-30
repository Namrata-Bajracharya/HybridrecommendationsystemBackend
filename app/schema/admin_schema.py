from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Brand
class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None


class BrandResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# Supplier
class SupplierCreate(BaseModel):
    name: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    address: Optional[str]


class SupplierResponse(BaseModel):
    id: int
    name: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    address: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# Coupon
class CouponCreate(BaseModel):
    code: str
    is_percentage: bool = True
    amount: float
    description: Optional[str] = None
    active: bool = True


class CouponResponse(BaseModel):
    id: int
    code: str
    is_percentage: bool
    amount: float
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Payment Method
class PaymentMethodCreate(BaseModel):
    name: str
    provider: Optional[str]


class PaymentMethodResponse(BaseModel):
    id: int
    name: str
    provider: Optional[str]
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Shipping
class ShippingZoneCreate(BaseModel):
    name: str
    description: Optional[str]


class ShippingZoneResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CourierCreate(BaseModel):
    name: str
    phone: Optional[str]


class CourierResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Inventory movement
class InventoryMovementCreate(BaseModel):
    product_id: int
    change: int
    reason: Optional[str]


class InventoryMovementResponse(BaseModel):
    id: int
    product_id: int
    change: int
    reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# Purchase order
class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    total_amount: float = 0.0
    status: Optional[str] = "draft"


class PurchaseOrderResponse(BaseModel):
    id: int
    supplier_id: int
    total_amount: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# Notification
class NotificationCreate(BaseModel):
    user_id: Optional[int]
    title: str
    message: str


class NotificationResponse(BaseModel):
    id: int
    user_id: Optional[int]
    title: str
    message: str
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Analytics Schemas
class SalesAnalytics(BaseModel):
    """Sales analytics for admin dashboard"""

    total_revenue: float = Field(..., description="Total revenue from all orders")
    total_orders: int = Field(..., description="Total number of orders")
    pending_orders: int = Field(..., description="Orders with pending status")
    paid_orders: int = Field(..., description="Orders with paid status")
    shipped_orders: int = Field(..., description="Orders with shipped status")
    delivered_orders: int = Field(..., description="Orders with delivered status")
    cancelled_orders: int = Field(..., description="Orders with cancelled status")
    average_order_value: float = Field(..., description="Average order value")
    revenue_last_30_days: float = Field(..., description="Revenue from last 30 days")


class UserAnalytics(BaseModel):
    """User analytics for admin dashboard"""

    total_users: int = Field(..., description="Total number of users")
    total_customers: int = Field(..., description="Number of customer users")
    total_admins: int = Field(..., description="Number of admin users")
    new_users_last_30_days: int = Field(..., description="New users in last 30 days")


class ProductAnalytics(BaseModel):
    """Product analytics for admin dashboard"""

    total_products: int = Field(..., description="Total number of products")
    active_products: int = Field(..., description="Number of active products")
    inactive_products: int = Field(..., description="Number of inactive products")
    out_of_stock_count: int = Field(..., description="Number of out of stock products")
    low_stock_count: int = Field(..., description="Number of low stock products (< 10)")


class ReviewAnalytics(BaseModel):
    """Review analytics for admin dashboard"""

    total_reviews: int = Field(..., description="Total number of reviews")
    pending_reviews: int = Field(..., description="Reviews awaiting approval")
    approved_reviews: int = Field(..., description="Approved reviews")
    average_rating: Optional[float] = Field(
        None, description="Average rating across all reviews"
    )


class DashboardOverview(BaseModel):
    """Complete dashboard overview with all analytics"""

    sales: SalesAnalytics
    users: UserAnalytics
    products: ProductAnalytics
    reviews: ReviewAnalytics


# User Management Schemas
class UserListItem(BaseModel):
    """User item for admin user list"""

    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    created_at: datetime
    total_orders: int = Field(..., description="Total orders by this user")
    total_spent: float = Field(..., description="Total amount spent by this user")

    class Config:
        from_attributes = True


class UserManagementResponse(BaseModel):
    """Paginated user list response"""

    users: List[UserListItem]
    total: int
    page: int
    page_size: int


class UpdateUserRoleRequest(BaseModel):
    """Request to update user role"""

    role: str = Field(..., description="New role: 'customer' or 'admin'")


# Order Management Schemas
class OrderListItem(BaseModel):
    """Order item for admin order list"""

    id: int
    order_number: str
    user_id: int
    user_email: str = Field(..., description="Email of the user who placed the order")
    total_amount: float
    status: str
    payment_status: str
    order_date: datetime
    shipped_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrderManagementResponse(BaseModel):
    """Paginated order list response"""

    orders: List[OrderListItem]
    total: int
    page: int
    page_size: int


class UpdateOrderStatusRequest(BaseModel):
    """Request to update order status"""

    status: str = Field(
        ...,
        description="New status: 'pending', 'paid', 'shipped', 'delivered', 'cancelled'",
    )


class MarkOrderShippedRequest(BaseModel):
    """Request to mark order as shipped"""

    shipped_at: Optional[datetime] = Field(
        None, description="Shipping timestamp, defaults to now"
    )


# Review Moderation Schemas
class ReviewModerationItem(BaseModel):
    """Review item for moderation"""

    id: int
    user_id: int
    user_email: str
    product_id: int
    product_name: str
    rating: int
    comment: Optional[str]
    created_at: datetime
    is_approved: bool

    class Config:
        from_attributes = True


class ReviewModerationResponse(BaseModel):
    """Paginated review list response"""

    reviews: List[ReviewModerationItem]
    total: int
    page: int
    page_size: int


# Inventory Management Schemas
class InventoryAlert(BaseModel):
    """Low stock product alert"""

    id: int
    name: str
    sku: Optional[str]
    stock_quantity: int
    is_active: bool

    class Config:
        from_attributes = True


class BulkInventoryUpdateItem(BaseModel):
    """Single item for bulk inventory update"""

    product_id: int
    stock_quantity: int = Field(
        ..., ge=0, description="New stock quantity (must be >= 0)"
    )


class BulkInventoryUpdateRequest(BaseModel):
    """Request to bulk update inventory"""

    updates: List[BulkInventoryUpdateItem]


class BulkInventoryUpdateResponse(BaseModel):
    """Response for bulk inventory update"""

    updated_count: int
    failed_products: List[int] = Field(
        default_factory=list, description="Product IDs that failed to update"
    )
