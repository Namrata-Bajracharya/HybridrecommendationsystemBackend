from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import HTTPException, status
from app.models.brand import Brand
from app.models.supplier import Supplier
from app.models.coupon import Coupon
from app.models.payment import PaymentMethod
from app.models.shipping import ShippingZone, Courier
from app.models.inventory import InventoryMovement
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_item import PurchaseOrderItem
from app.models.stock_batch import StockBatch
from app.models.notification import Notification
from app.models.rejection_reason import RejectionReason
from app.models.user import User
from app.models.order import Order
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.review import Review
from app.models.wishlist import Wishlist
from app.crud.order import OrderCrud
from app.crud.user import UserCrud
from app.crud.product import ProductCrud
from app.crud.review import ReviewCrud
from app.schema.admin_schema import (
    SalesAnalytics,
    UserAnalytics,
    ProductAnalytics,
    ReviewAnalytics,
    DashboardOverview,
    UserListItem,
    UserManagementResponse,
    UserDetailResponse,
    UserOrderItemSummary,
    OrderListItem,
    OrderManagementResponse,
    ReviewModerationItem,
    ReviewModerationResponse,
    InventoryAlert,
    InventoryItem,
    InventoryResponse,
    InventorySummary,
    BulkInventoryUpdateItem,
    BulkInventoryUpdateResponse,
    RestockResponse,
    ProfitReportItem,
    ProfitReportResponse,
    ProductProfitItem,
    ProductProfitReportResponse,
    OrderReportItem,
    OrderReportResponse,
    AdminWishlistItem,
    AdminWishlistResponse,
)


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.order_crud = OrderCrud(db=db)
        self.user_crud = UserCrud(db=db)
        self.product_crud = ProductCrud(db=db)
        self.review_crud = ReviewCrud(db=db)

    # Brands
    def create_brand(self, name: str, description: Optional[str] = None) -> Brand:
        b = Brand(name=name, description=description)
        self.db.add(b)
        self.db.commit()
        self.db.refresh(b)
        return b

    def list_brands(self) -> List[Brand]:
        return self.db.query(Brand).all()

    def get_brand(self, id: int) -> Optional[Brand]:
        return self.db.get(Brand, id)

    # Suppliers
    def create_supplier(self, name: str, contact_email: Optional[str] = None, contact_phone: Optional[str] = None, address: Optional[str] = None) -> Supplier:
        s = Supplier(name=name, contact_email=contact_email, contact_phone=contact_phone, address=address)
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s

    def list_suppliers(self) -> List[Supplier]:
        return self.db.query(Supplier).all()

    # Coupons
    def create_coupon(self, code: str, is_percentage: bool, amount: float, description: Optional[str] = None, active: bool = True) -> Coupon:
        c = Coupon(code=code, is_percentage=is_percentage, amount=amount, description=description, active=active)
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return c

    def list_coupons(self) -> List[Coupon]:
        return self.db.query(Coupon).all()

    # Payment methods
    def list_payment_methods(self) -> List[PaymentMethod]:
        return self.db.query(PaymentMethod).all()

    # Shipping
    def list_shipping_zones(self) -> List[ShippingZone]:
        return self.db.query(ShippingZone).all()

    def list_couriers(self) -> List[Courier]:
        return self.db.query(Courier).all()

    # Inventory
    def record_inventory_movement(self, product_id: int, change: int, reason: Optional[str] = None) -> InventoryMovement:
        m = InventoryMovement(product_id=product_id, change=change, reason=reason)
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return m

    # Purchase Orders
    def create_purchase_order(self, supplier_id: int, total_amount: float = 0.0, status: str = "draft") -> PurchaseOrder:
        p = PurchaseOrder(supplier_id=supplier_id, total_amount=total_amount, status=status)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    # Notifications
    def create_notification(self, user_id: Optional[int], title: str, message: str, type: Optional[str] = None, order_id: Optional[int] = None) -> Notification:
        n = Notification(user_id=user_id, title=title, message=message, type=type, order_id=order_id)
        self.db.add(n)
        self.db.commit()
        self.db.refresh(n)
        return n

    def list_notifications_for_user(self, user_id: int) -> List[Notification]:
        user = self.db.get(User, user_id)
        if user and user.role == "admin":
            return self.db.query(Notification).filter(
                (Notification.user_id == user_id) | (Notification.user_id.is_(None))
            ).all()
        return self.db.query(Notification).filter(Notification.user_id == user_id).all()

    def mark_notification_read(self, notification_id: int) -> Notification:
        n = self.db.get(Notification, notification_id)
        if not n:
            raise HTTPException(status_code=404, detail="Notification not found")
        n.read = True
        self.db.commit()
        self.db.refresh(n)
        return n

    def list_rejection_reasons(self) -> List:
        return self.db.query(RejectionReason).all()

    # Analytics Methods
    def get_sales_analytics(self) -> SalesAnalytics:
        """Calculate sales analytics including revenue and order statistics"""
        # Total orders and revenue
        total_orders = self.order_crud.get_total_orders()
        total_revenue = self.order_crud.get_total_revenue()

        # Orders by status
        pending_orders = self.order_crud.get_pending_orders()
        paid_orders = self.order_crud.get_paid_orders()
        shipped_orders = self.order_crud.get_shipped_orders_count()
        delivered_orders = self.order_crud.get_delivered_orders_count()
        cancelled_orders = self.order_crud.get_cancelled_orders_count()

        # Average order value
        average_order_value = (
            round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0
        )

        # Revenue last 30 days
        revenue_last_30_days = self.order_crud.revenue_last_thirty_days()

        return SalesAnalytics(
            total_revenue=float(total_revenue),
            total_orders=total_orders,
            pending_orders=pending_orders,
            paid_orders=paid_orders,
            shipped_orders=shipped_orders,
            delivered_orders=delivered_orders,
            cancelled_orders=cancelled_orders,
            average_order_value=average_order_value,
            revenue_last_30_days=float(revenue_last_30_days),
        )

    def get_user_analytics(self) -> UserAnalytics:
        """Calculate user analytics including total users and growth"""
        total_users = self.user_crud.get_total_users()
        total_customers = self.user_crud.get_total_customers()
        total_admins = self.user_crud.get_total_admins()
        # New users in last 30 days
        new_users_last_30_days = self.user_crud.get_new_user_in_last_thirty_days()

        return UserAnalytics(
            total_users=total_users,
            total_customers=total_customers,
            total_admins=total_admins,
            new_users_last_30_days=new_users_last_30_days,
        )

    def get_product_analytics(self) -> ProductAnalytics:
        """Calculate product analytics including inventory status"""
        total_products = self.product_crud.get_total_products()
        active_products = self.product_crud.total_active_products()
        inactive_products = self.product_crud.total_inactive_products()
        out_of_stock_count = self.product_crud.out_of_stock_count()
        low_stock_count = self.product_crud.low_stock_count()

        return ProductAnalytics(
            total_products=total_products,
            active_products=active_products,
            inactive_products=inactive_products,
            out_of_stock_count=out_of_stock_count,
            low_stock_count=low_stock_count,
        )

    def get_review_analytics(self) -> ReviewAnalytics:
        """Calculate review analytics including approval status"""
        total_reviews = self.review_crud.total_reviews()
        pending_reviews = self.review_crud.pending_reviews()
        approved_reviews = self.review_crud.approved_reviews()
        average_rating = self.review_crud.average_rating()

        return ReviewAnalytics(
            total_reviews=total_reviews,
            pending_reviews=pending_reviews,
            approved_reviews=approved_reviews,
            average_rating=round(float(average_rating), 2) if average_rating else None,
        )

    def get_dashboard_overview(self) -> DashboardOverview:
        """Get complete dashboard overview with all analytics"""
        return DashboardOverview(
            sales=self.get_sales_analytics(),
            users=self.get_user_analytics(),
            products=self.get_product_analytics(),
            reviews=self.get_review_analytics(),
        )

    # User Management Methods
    def get_all_users(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
    ) -> UserManagementResponse:
        """Get paginated list of all users with optional filters"""
        # query = self.db.query(User)

        # # Apply filters
        # if search:
        #     search_filter = or_(
        #         User.email.ilike(f"%{search}%"),
        #         User.first_name.ilike(f"%{search}%"),
        #         User.last_name.ilike(f"%{search}%"),
        #     )
        #     query = query.filter(search_filter)

        # if role:
        #     query = query.filter(User.role == role)

        # # Get total count
        # total = query.count()

        # # Apply pagination
        # offset = (page - 1) * page_size
        # users = query.offset(offset).limit(page_size).all()
        total, users = self.user_crud.get_all_users(page, page_size, search, role)

        # Build user list with additional stats
        user_items = []
        for user in users:
            # Calculate total orders and spent
            total_orders = self.order_crud.total_order_by_user(user.id)
            total_spent = self.order_crud.total_spent_by_user(user.id)

            user_items.append(
                UserListItem(
                    id=user.id,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    role=user.role,
                    created_at=user.created_at,
                    total_orders=total_orders,
                    total_spent=float(total_spent),
                )
            )

        return UserManagementResponse(
            users=user_items, total=total, page=page, page_size=page_size
        )

    def update_user_role(self, user_id: int, new_role: str) -> User:
        """Update a user's role"""
        if new_role not in ["customer", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be 'customer' or 'admin'",
            )

        user = self.user_crud.update_user_role(user_id, new_role)
        return user

    # Order Management Methods
    def get_all_orders(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> OrderManagementResponse:
        """Get paginated list of all orders with optional filters"""
        total, orders = self.order_crud.get_all_orders(page, page_size, status)
        order_items = []
        for order in orders:
            order_items.append(
                OrderListItem(
                    id=order.id,
                    order_number=order.order_number,
                    user_id=order.user_id,
                    user_email=order.user.email,
                    total_amount=float(order.total_amount),
                    status=order.status,
                    payment_status=order.payment_status,
                    order_date=order.order_date,
                    shipped_at=order.shipped_at,
                )
            )

        return OrderManagementResponse(
            orders=order_items, total=total, page=page, page_size=page_size
        )

    def update_order_status(self, order_id: int, new_status: str) -> Order:
        """Update an order's status"""
        valid_statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            )

        return self.order_crud.update_order_status(order_id, new_status)

    def mark_order_shipped(
        self, order_id: int, shipped_at: Optional[datetime] = None
    ) -> Order:
        """Mark an order as shipped"""
        return self.order_crud.mark_order_shipped(order_id, shipped_at)

    # Review Moderation Methods
    def get_pending_reviews(
        self, page: int = 1, page_size: int = 20
    ) -> ReviewModerationResponse:
        """Get paginated list of pending reviews"""
        total, reviews = self.review_crud.get_pending_reviews(page, page_size)

        review_items = []
        for review in reviews:
            review_items.append(
                ReviewModerationItem(
                    id=review.id,
                    user_id=review.user_id,
                    user_email=review.user.email,
                    product_id=review.product_id,
                    product_name=review.product.name,
                    rating=review.rating,
                    comment=review.comment,
                    created_at=review.created_at,
                    is_approved=review.is_approved,
                )
            )

        return ReviewModerationResponse(
            reviews=review_items, total=total, page=page, page_size=page_size
        )

    def get_all_reviews(
        self, page: int = 1, page_size: int = 20
    ) -> ReviewModerationResponse:
        """Get paginated list of all reviews"""
        total, reviews = self.review_crud.get_all_reviews(page, page_size)

        review_items = []
        for review in reviews:
            review_items.append(
                ReviewModerationItem(
                    id=review.id,
                    user_id=review.user_id,
                    user_email=review.user.email,
                    product_id=review.product_id,
                    product_name=review.product.name,
                    rating=review.rating,
                    comment=review.comment,
                    created_at=review.created_at,
                    is_approved=review.is_approved,
                )
            )

        return ReviewModerationResponse(
            reviews=review_items, total=total, page=page, page_size=page_size
        )

    def approve_review(self, review_id: int) -> Review:
        """Approve a review"""
        return self.review_crud.approve_review(review_id)

    def reject_review(self, review_id: int) -> None:
        """Reject/delete a review"""
        return self.review_crud.reject_review(review_id)

    # Inventory Management Methods
    def get_low_stock_products(self, threshold: int = 10) -> List[InventoryAlert]:
        """Get products with low stock"""
        products = self.product_crud.get_slow_stock_products(threshold)

        return [
            InventoryAlert(
                id=p.id,
                name=p.name,
                sku=p.sku,
                stock_quantity=p.stock_quantity,
                is_active=p.is_active,
            )
            for p in products
        ]

    def bulk_update_inventory(
        self, updates: List[BulkInventoryUpdateItem]
    ) -> BulkInventoryUpdateResponse:
        """Bulk update product inventory"""
        updated_count, failed_products = self.product_crud.bulk_update_inventory(
            updates
        )

        return BulkInventoryUpdateResponse(
            updated_count=updated_count, failed_products=failed_products
        )

    # Wishlist Management
    def get_all_wishlists(
        self, page: int = 1, page_size: int = 20
    ) -> AdminWishlistResponse:
        """Get paginated list of all wishlist items across users"""
        from app.models.wishlist import Wishlist
        from app.models.user import User
        from app.models.product import Product
        from app.models.product_image import ProductImage

        query = (
            self.db.query(Wishlist)
            .join(User, Wishlist.user_id == User.id)
            .join(Product, Wishlist.product_id == Product.id)
            .order_by(Wishlist.created_at.desc())
        )
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        result = []
        for w in items:
            img = (
                self.db.query(ProductImage)
                .filter(ProductImage.product_id == w.product_id)
                .order_by(ProductImage.sort_order)
                .first()
            )
            result.append(
                AdminWishlistItem(
                    id=w.id,
                    user_id=w.user_id,
                    user_email=w.user.email,
                    user_name=f"{w.user.first_name or ''} {w.user.last_name or ''}".strip() or None,
                    product_id=w.product_id,
                    product_name=w.product.name,
                    product_price=float(w.product.selling_price or 0),
                    product_image=img.document.relative_path if img and img.document else None,
                    created_at=w.created_at,
                )
            )

        return AdminWishlistResponse(items=result, total=total, page=page, page_size=page_size)

    # Restock with FIFO stock batches
    def restock_product(self, product_id: int, quantity: int, unit_cost: float, variant_id: Optional[int] = None, supplier_id: Optional[int] = None, new_buying_price: Optional[float] = None, new_selling_price: Optional[float] = None) -> RestockResponse:
        product = self.db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        if variant_id:
            variant = self.db.get(ProductVariant, variant_id)
            if not variant or variant.product_id != product_id:
                raise HTTPException(status_code=404, detail="Variant not found for this product")

        prev_stock = product.stock_quantity or 0

        if new_buying_price is not None:
            product.buying_price = new_buying_price
        if new_selling_price is not None:
            product.selling_price = new_selling_price

        # Create purchase order item if supplier specified
        po_item = None
        if supplier_id:
            po = PurchaseOrder(supplier_id=supplier_id, total_amount=quantity * unit_cost, status="received")
            self.db.add(po)
            self.db.flush()
            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity,
                unit_cost=unit_cost,
            )
            self.db.add(po_item)
            self.db.flush()

        # Create stock batch
        from app.services.fifo_service import FifoAllocationService
        fifo = FifoAllocationService(self.db)
        batch = fifo.add_batch(
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            unit_cost=unit_cost,
            purchase_order_item_id=po_item.id if po_item else None,
        )

        # Update product stock
        product.stock_quantity = prev_stock + quantity
        if variant_id:
            variant.stock_quantity = (variant.stock_quantity or 0) + quantity

        self.db.commit()
        self.db.refresh(product)

        return RestockResponse(
            product_id=product.id,
            name=product.name,
            previous_stock=prev_stock,
            new_stock=product.stock_quantity,
            batch_unit_cost=unit_cost,
            batch_quantity=quantity,
        )

    # Profit / Loss Report
    def get_profit_report(self, period: str = "all_time") -> ProfitReportResponse:
        from app.models.order_item import OrderItem
        from app.models.order import Order
        from app.models.product import Product
        from datetime import datetime, timedelta

        now = datetime.now()
        if period == "today":
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            since = now - timedelta(days=7)
        elif period == "month":
            since = now - timedelta(days=30)
        else:
            since = None

        query = (
            self.db.query(OrderItem)
            .join(Order)
            .filter(Order.status.in_(["delivered", "Delivered"]))
        )
        if since:
            query = query.filter(Order.delivered_at >= since)

        order_items = query.all()

        product_map: dict[int, dict] = {}
        total_revenue = 0.0
        total_cost = 0.0

        for oi in order_items:
            pid = oi.product_id
            rev = float(oi.unit_price) * oi.quantity
            cost = (float(oi.unit_cost) if oi.unit_cost else 0) * oi.quantity
            total_revenue += rev
            total_cost += cost

            if pid not in product_map:
                product = self.db.get(Product, pid)
                product_map[pid] = {
                    "product_id": pid,
                    "product_name": product.name if product else f"Product #{pid}",
                    "units_sold": 0,
                    "revenue": 0.0,
                    "cost": 0.0,
                }
            product_map[pid]["units_sold"] += oi.quantity
            product_map[pid]["revenue"] += rev
            product_map[pid]["cost"] += cost

        items = []
        for pid, data in product_map.items():
            profit = data["revenue"] - data["cost"]
            margin = round((profit / data["revenue"]) * 100, 2) if data["revenue"] > 0 else None
            items.append(ProfitReportItem(
                product_id=data["product_id"],
                product_name=data["product_name"],
                units_sold=data["units_sold"],
                revenue=round(data["revenue"], 2),
                cost=round(data["cost"], 2),
                profit=round(profit, 2),
                margin=margin,
            ))

        items.sort(key=lambda x: x.profit, reverse=True)
        total_profit = total_revenue - total_cost
        overall_margin = round((total_profit / total_revenue) * 100, 2) if total_revenue > 0 else None

        return ProfitReportResponse(
            total_revenue=round(total_revenue, 2),
            total_cost=round(total_cost, 2),
            total_profit=round(total_profit, 2),
            overall_margin=overall_margin,
            period=period,
            items=items,
        )

    # Product Profit Report
    def get_product_profit_report(self, period: str = "all_time") -> ProductProfitReportResponse:
        from app.models.order_item import OrderItem
        from app.models.order import Order
        from app.models.product import Product
        from app.models.stock_batch import StockBatch
        from datetime import datetime, timedelta

        now = datetime.now()
        if period == "today":
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            since = now - timedelta(days=7)
        elif period == "month":
            since = now - timedelta(days=30)
        elif period == "year":
            since = now - timedelta(days=365)
        else:
            since = None

        query = (
            self.db.query(OrderItem)
            .join(Order)
            .filter(Order.status.in_(["delivered", "Delivered"]))
        )
        if since:
            query = query.filter(Order.delivered_at >= since)

        order_items = query.all()

        product_map: dict[int, dict] = {}
        for oi in order_items:
            pid = oi.product_id
            if pid not in product_map:
                product = self.db.get(Product, pid)
                latest_batch = (
                    self.db.query(StockBatch)
                    .filter(StockBatch.product_id == pid)
                    .order_by(StockBatch.created_at.desc())
                    .first()
                )
                product_map[pid] = {
                    "product_id": pid,
                    "product_name": product.name if product else f"Product #{pid}",
                    "sku": product.sku if product else None,
                    "stock_quantity": product.stock_quantity if product else 0,
                    "total_revenue": 0.0,
                    "total_cost": 0.0,
                    "total_profit": 0.0,
                    "total_units_sold": 0,
                    "last_purchase_cost": latest_batch.unit_cost if latest_batch else None,
                    "last_restock_date": latest_batch.created_at if latest_batch else None,
                }

            rev = float(oi.unit_price) * oi.quantity
            cost = (float(oi.unit_cost) if oi.unit_cost else 0) * oi.quantity
            product_map[pid]["total_revenue"] += rev
            product_map[pid]["total_cost"] += cost
            product_map[pid]["total_units_sold"] += oi.quantity

        items = []
        for pid, data in product_map.items():
            profit = data["total_revenue"] - data["total_cost"]
            items.append(ProductProfitItem(
                product_id=data["product_id"],
                product_name=data["product_name"],
                sku=data["sku"],
                stock_quantity=data["stock_quantity"],
                total_revenue=round(data["total_revenue"], 2),
                total_cost=round(data["total_cost"], 2),
                total_profit=round(profit, 2),
                total_units_sold=data["total_units_sold"],
                last_purchase_cost=data["last_purchase_cost"],
                last_restock_date=data["last_restock_date"],
            ))

        items.sort(key=lambda x: x.total_profit, reverse=True)

        return ProductProfitReportResponse(period=period, items=items)

    # Inventory List
    def get_inventory(self, page: int = 1, page_size: int = 20, search: Optional[str] = None, low_stock: Optional[bool] = None) -> InventoryResponse:
        latest_batch_subq = (
            select(StockBatch.product_id, func.max(StockBatch.created_at).label("last_restock_at"))
            .group_by(StockBatch.product_id)
            .subquery()
        )

        base_query = self.db.query(Product).outerjoin(
            latest_batch_subq, Product.id == latest_batch_subq.c.product_id
        ).add_columns(latest_batch_subq.c.last_restock_at)

        if search:
            base_query = base_query.filter(
                or_(Product.name.ilike(f"%{search}%"), Product.sku.ilike(f"%{search}%"))
            )

        if low_stock:
            base_query = base_query.filter(Product.stock_quantity < 10)

        total = base_query.count()
        rows = base_query.order_by(Product.stock_quantity.asc()).offset((page - 1) * page_size).limit(page_size).all()

        now = datetime.utcnow()
        items = []
        for row in rows:
            p = row.Product if hasattr(row, "Product") else row[0]
            last_restock = row.last_restock_at if hasattr(row, "last_restock_at") else (row[1] if len(row) > 1 else None)
            days = (now - last_restock).days if last_restock else None
            items.append(InventoryItem(
                product_id=p.id, name=p.name, sku=p.sku,
                stock_quantity=p.stock_quantity or 0,
                buying_price=float(p.buying_price) if p.buying_price else None,
                selling_price=float(p.selling_price or p.price) if (p.selling_price or p.price) else None,
                is_active=p.is_active,
                last_restock_at=last_restock,
                days_since_restock=days,
            ))

        all_products = self.db.query(Product).all()
        in_stock = sum(1 for p in all_products if (p.stock_quantity or 0) >= 10)
        low_stock_count = sum(1 for p in all_products if 0 < (p.stock_quantity or 0) < 10)
        out_of_stock_count = sum(1 for p in all_products if (p.stock_quantity or 0) == 0)

        return InventoryResponse(
            items=items, total=total, page=page, page_size=page_size,
            summary=InventorySummary(
                total_products=len(all_products),
                in_stock=in_stock, low_stock=low_stock_count, out_of_stock=out_of_stock_count,
            ),
        )

    # User / Customer Detail
    def get_user_detail(self, user_id: int) -> UserDetailResponse:
        user = self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        from datetime import datetime, timedelta
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        all_orders = self.db.query(Order).filter(Order.user_id == user_id).order_by(Order.order_date.desc()).all()
        total_orders = len(all_orders)
        total_spent = sum(float(o.total_amount) for o in all_orders)
        today_orders = sum(1 for o in all_orders if o.order_date >= today_start)
        today_spend = sum(float(o.total_amount) for o in all_orders if o.order_date >= today_start)
        pending_orders = sum(1 for o in all_orders if o.status in ("pending", "accepted", "packed", "on_delivery"))

        wishlist_count = self.db.query(func.count(Wishlist.id)).filter(Wishlist.user_id == user_id).scalar() or 0

        product_ids = set()
        for o in all_orders:
            for oi in o.order_items:
                product_ids.add(oi.product_id)
        products_count = len(product_ids)

        orders_by_status: dict[str, int] = {}
        for o in all_orders:
            s = o.status or "unknown"
            orders_by_status[s] = orders_by_status.get(s, 0) + 1

        recent = []
        for o in all_orders[:10]:
            recent.append(UserOrderItemSummary(
                id=o.id, order_number=o.order_number,
                total_amount=float(o.total_amount), status=o.status,
                order_date=o.order_date, payment_mode=o.payment_mode or "cod",
                item_count=len(o.order_items),
            ))

        wishlist_product_ids = [w.product_id for w in self.db.query(Wishlist).filter(Wishlist.user_id == user_id).all()]

        return UserDetailResponse(
            id=user.id, email=user.email,
            first_name=user.first_name, last_name=user.last_name,
            phone=user.phone, role=user.role, created_at=user.created_at,
            total_orders=total_orders, total_spent=total_spent,
            today_orders=today_orders, today_spend=today_spend,
            pending_orders=pending_orders,
            wishlist_count=wishlist_count, products_count=products_count,
            orders_by_status=orders_by_status, recent_orders=recent,
            wishlist_product_ids=wishlist_product_ids,
        )

    # Orders Report
    def get_orders_report(self, period: str = "all_time") -> OrderReportResponse:
        from datetime import datetime, timedelta
        now = datetime.now()
        if period == "today":
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            since = now - timedelta(days=7)
        elif period == "month":
            since = now - timedelta(days=30)
        elif period == "year":
            since = now - timedelta(days=365)
        else:
            since = None

        query = self.db.query(Order).order_by(Order.order_date.desc())
        if since:
            query = query.filter(Order.order_date >= since)

        orders = query.all()

        items = []
        for o in orders:
            contact_name = o.contact_name
            if not contact_name and o.user:
                contact_name = f"{o.user.first_name or ''} {o.user.last_name or ''}".strip() or o.user.email
            items.append(OrderReportItem(
                id=o.id,
                order_number=o.order_number,
                contact_name=contact_name,
                total_amount=float(o.total_amount),
                order_date=o.order_date,
                delivered_at=o.delivered_at,
                rejected_at=o.rejected_at,
                status=o.status,
            ))

        return OrderReportResponse(period=period, items=items)
