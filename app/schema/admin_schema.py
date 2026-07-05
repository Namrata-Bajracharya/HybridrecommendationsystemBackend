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


# Rejection Reason
class RejectionReasonResponse(BaseModel):
    id: int
    reason: str

    model_config = {"from_attributes": True}


# Notification
class NotificationCreate(BaseModel):
    user_id: Optional[int]
    title: str
    message: str
    type: Optional[str] = None
    order_id: Optional[int] = None


class NotificationResponse(BaseModel):
    id: int
    user_id: Optional[int]
    title: str
    message: str
    type: Optional[str] = None
    order_id: Optional[int] = None
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


# Restock
class RestockRequest(BaseModel):
    product_id: int
    variant_id: Optional[int] = Field(None, description="Variant ID if restocking a variant")
    quantity: int = Field(..., gt=0, description="Quantity being added")
    unit_cost: float = Field(..., gt=0, description="Cost per unit for this batch")
    supplier_id: Optional[int] = Field(None, description="Supplier for this purchase order")
    new_buying_price: Optional[float] = Field(None, ge=0, description="New buying price for the product")
    new_selling_price: Optional[float] = Field(None, ge=0, description="New selling price for the product")


class RestockResponse(BaseModel):
    product_id: int
    name: str
    previous_stock: int
    new_stock: int
    batch_unit_cost: float
    batch_quantity: int


# Profit / Loss Report
class ProfitReportItem(BaseModel):
    product_id: int
    product_name: str
    units_sold: int
    revenue: float
    cost: float
    profit: float
    margin: Optional[float] = None


class ProfitReportResponse(BaseModel):
    total_revenue: float
    total_cost: float
    total_profit: float
    overall_margin: Optional[float] = None
    period: str = "all_time"
    items: List[ProfitReportItem]


class ProductProfitItem(BaseModel):
    product_id: int
    product_name: str
    sku: Optional[str] = None
    stock_quantity: int = 0
    total_revenue: float = 0
    total_cost: float = 0
    total_profit: float = 0
    total_units_sold: int = 0
    last_purchase_cost: Optional[float] = None
    last_restock_date: Optional[datetime] = None


class ProductProfitReportResponse(BaseModel):
    period: str = "all_time"
    items: List[ProductProfitItem]


class OrderReportItem(BaseModel):
    id: int
    order_number: str
    contact_name: Optional[str] = None
    total_amount: float
    order_date: datetime
    delivered_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    status: str


class OrderReportResponse(BaseModel):
    period: str = "all_time"
    items: List[OrderReportItem]


# Inventory List
class InventoryItem(BaseModel):
    product_id: int
    name: str
    sku: Optional[str] = None
    stock_quantity: int = 0
    buying_price: Optional[float] = None
    selling_price: Optional[float] = None
    is_active: bool = True
    last_restock_at: Optional[datetime] = None
    days_since_restock: Optional[int] = None

    class Config:
        from_attributes = True


class InventorySummary(BaseModel):
    total_products: int = 0
    in_stock: int = 0
    low_stock: int = 0
    out_of_stock: int = 0


class InventoryResponse(BaseModel):
    items: List[InventoryItem]
    total: int
    page: int
    page_size: int
    summary: InventorySummary


# User Detail
class UserOrderItemSummary(BaseModel):
    id: int
    order_number: str
    total_amount: float
    status: str
    order_date: datetime
    payment_mode: str = "cod"
    item_count: int = 0

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "customer"
    created_at: datetime
    total_orders: int = 0
    total_spent: float = 0
    today_orders: int = 0
    today_spend: float = 0
    pending_orders: int = 0
    wishlist_count: int = 0
    products_count: int = 0
    orders_by_status: dict[str, int] = Field(default_factory=dict)
    recent_orders: List[UserOrderItemSummary] = Field(default_factory=list)
    wishlist_product_ids: List[int] = Field(default_factory=list)

    class Config:
        from_attributes = True


# Admin Wishlist
class AdminWishlistItem(BaseModel):
    id: int
    user_id: int
    user_email: str
    user_name: Optional[str] = None
    product_id: int
    product_name: str
    product_price: float = 0
    product_image: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminWishlistResponse(BaseModel):
    items: List[AdminWishlistItem]
    total: int
    page: int
    page_size: int
