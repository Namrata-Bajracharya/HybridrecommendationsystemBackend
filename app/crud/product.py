from pathlib import Path
from pydantic import HttpUrl
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ProductException
from app.core.logger import logger
from app.models.category import Category
from app.models.document import Document
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant
from app.schema.admin_schema import BulkInventoryUpdateItem, BulkInventoryUpdateResponse
from app.schema.common_schema import PaginatedResponse, PaginationLinks, PaginationMeta
from app.schema.product_schema import ProductCreate, ProductResponse, ProductUpdate
from app.utils.generate_slug import generate_sku, generate_slug
from app.services.document_service import DocumentService
from typing import List, Literal

allowed_sort_order = Literal["asc", "desc"]
allowed_sort_by = Literal["id", "price", "name", "created_at", "rating", "popularity"]


class ProductCrud:
    def __init__(self, db: Session):
        self.db = db

    def create_product(self, create_dto: ProductCreate) -> Product:
        """Create a new product with generated slug and sku."""
        try:
            create_data = create_dto.model_dump(exclude={"image_document_ids", "image_data_urls"})
            image_document_ids = create_dto.image_document_ids or []
            image_data_urls = create_dto.image_data_urls or []

            product_name = create_data.get("name")
            if not product_name:
                raise ValueError("Product name is required for slug generation.")

            gen_slug = generate_slug(self.db, product_name, context="product")
            gen_sku = generate_sku(product_name)

            product = Product(**create_data, slug=gen_slug, sku=gen_sku)
            self.db.add(product)
            self.db.flush()

            doc_service = DocumentService(self.db)
            for i, data_url in enumerate(image_data_urls):
                doc = doc_service.save_base64(data_url)
                self.db.add(ProductImage(
                    product_id=product.id,
                    document_id=doc.id,
                    sort_order=i,
                ))

            for i, doc_id in enumerate(image_document_ids):
                self.db.add(ProductImage(
                    product_id=product.id,
                    document_id=doc_id,
                    sort_order=len(image_data_urls) + i,
                ))

            self.db.commit()
            self.db.refresh(product)
            return product
        except IntegrityError as e:
            self.db.rollback()
            logger.info(f"exception: {e}")
            raise ProductException(str(e)) from e

    def _load_images(self, product: Product) -> Product:
        """Eagerly load images on a product instance."""
        if not product.images:
            stmt = select(Product).where(Product.id == product.id).options(joinedload(Product.images))
            loaded = self.db.scalar(stmt)
            if loaded:
                product.images = loaded.images
        return product

    def get_product_detail(self, slug: str) -> Product:
        """Retrieve a product by slug; returns None if not found."""
        stmt = select(Product).where(Product.slug == slug).options(joinedload(Product.images), joinedload(Product.variants))
        product = self.db.scalar(stmt)
        return product

    def get_product_by_id(self, id: int) -> Product | None:
        """Retrieve a product by id; returns None if not found."""
        stmt = select(Product).where(Product.id == id).options(joinedload(Product.images), joinedload(Product.variants))
        result = self.db.scalar(stmt)
        return result

    def get_all_products(
        self,
        page: int = 1,
        per_page: int = 10,
        search: str | None = None,
        category_id: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        min_rating: float | None = None,
        availability: str | None = "all",
        sort_by: allowed_sort_by | None = "id",
        sort_order: allowed_sort_order = "asc",
    ) -> PaginatedResponse[ProductResponse]:
        """
        List all products with advanced filtering and sorting.
        """
        logger.info(f"page: {page} - per_page: {per_page}")
        logger.info(
            f"filters - price: [{min_price}, {max_price}], rating: {min_rating}, availability: {availability}"
        )

        page = max(page, 1)
        per_page = max(min(per_page, 100), 1)

        base_conditions = [Product.is_active == True]

        if search:
            search_pattern = f"%{search}%"
            base_conditions.append(
                Product.name.ilike(search_pattern)
                | Product.description.ilike(search_pattern)
            )

        if category_id:
            base_conditions.append(Product.category_id == category_id)

        if min_price is not None:
            base_conditions.append(Product.price >= min_price)
        if max_price is not None:
            base_conditions.append(Product.price <= max_price)

        if min_rating is not None:
            base_conditions.append(Product.average_rating >= min_rating)

        if availability == "in_stock":
            base_conditions.append(Product.in_stock == True)
        elif availability == "out_of_stock":
            base_conditions.append(Product.in_stock == False)

        from app.models.order_item import OrderItem

        allowed_sorting_fields = {
            "id": Product.id,
            "name": Product.name,
            "price": Product.price,
            "created_at": Product.created_at,
            "rating": Product.average_rating,
            "popularity": (
                select(func.count(OrderItem.id))
                .where(OrderItem.product_id == Product.id)
                .correlate_except(OrderItem)
                .scalar_subquery()
            ),
        }

        sort_field = allowed_sorting_fields.get(sort_by, Product.id)
        order = sort_field.desc() if sort_order == "desc" else sort_field.asc()

        count_stmt = select(func.count(Product.id)).where(*base_conditions)
        total_items = self.db.scalar(count_stmt)

        stmt = select(Product).where(*base_conditions).options(joinedload(Product.images), joinedload(Product.variants)).order_by(order)

        offset = (page - 1) * per_page
        items = self.db.scalars(stmt.offset(offset).limit(per_page)).unique().all()

        total_pages = (total_items + per_page - 1) // per_page
        from_item = offset + 1 if items else None
        to_item = offset + len(items) if items else None

        meta = PaginationMeta(
            current_page=page,
            per_page=per_page,
            total_pages=total_pages,
            total_items=total_items,
            from_item=from_item,
            to_item=to_item,
        )

        base = "/products"
        query_params = []
        if search:
            query_params.append(f"search={search}")
        if category_id:
            query_params.append(f"category_id={category_id}")
        if min_price is not None:
            query_params.append(f"min_price={min_price}")
        if max_price is not None:
            query_params.append(f"max_price={max_price}")
        if min_rating is not None:
            query_params.append(f"min_rating={min_rating}")
        if availability != "all":
            query_params.append(f"availability={availability}")
        if sort_by != "id":
            query_params.append(f"sort_by={sort_by}")
        if sort_order != "asc":
            query_params.append(f"sort_order={sort_order}")

        query_string = "&".join(query_params)
        base_with_params = f"{base}?{query_string}&" if query_params else f"{base}?"

        links = PaginationLinks(
            self=f"{base_with_params}page={page}&per_page={per_page}",
            first=f"{base_with_params}page=1&per_page={per_page}",
            last=f"{base_with_params}page={total_pages}&per_page={per_page}",
            prev=(
                f"{base_with_params}page={page - 1}&per_page={per_page}"
                if page > 1
                else None
            ),
            next=(
                f"{base_with_params}page={page + 1}&per_page={per_page}"
                if page < total_pages
                else None
            ),
        )

        return PaginatedResponse(
            data=items,
            meta=meta,
            links=links,
        )

    def get_products_by_category_id(self, category_id: int) -> list[Product]:
        stmt = (
            select(Product)
            .where(Product.category_id == category_id)
            .options(joinedload(Product.images), joinedload(Product.variants))
            .order_by(Product.id)
        )
        return self.db.scalars(stmt).unique().all()

    def get_products_by_category_slug(self, slug: str) -> list[Product]:
        stmt = (
            select(Product)
            .join(Category, Product.category_id == Category.id)
            .where(Category.slug == slug)
            .options(joinedload(Product.images), joinedload(Product.variants))
            .order_by(Product.id)
        )
        return self.db.scalars(stmt).unique().all()

    def update_product(self, id: int, update_dto: ProductUpdate) -> Product | None:
        """Partially update product; auto-generate slug when name changes."""
        try:
            update_data = update_dto.model_dump(exclude_unset=True, exclude={"image_document_ids", "image_data_urls"})
            image_document_ids = getattr(update_dto, "image_document_ids", None)
            image_data_urls = getattr(update_dto, "image_data_urls", None)
            has_image_changes = image_document_ids is not None or image_data_urls is not None

            if not update_data and not has_image_changes:
                return self.get_product_by_id(id)

            if "name" in update_data and "slug" not in update_data:
                update_data["slug"] = generate_slug(self.db, update_data["name"])

            if update_data:
                stmt = (
                    update(Product)
                    .where(Product.id == id)
                    .values(**update_data)
                    .returning(Product)
                )
                updated = self.db.execute(stmt).scalar_one_or_none()
            else:
                updated = self.get_product_by_id(id)

            if updated and has_image_changes:
                from app.models.document import Document
                old_docs = [
                    pi.document_id
                    for pi in self.db.execute(
                        select(ProductImage.document_id).where(ProductImage.product_id == id)
                    ).scalars()
                ]
                removed_ids = set(old_docs) - set(image_document_ids or [])
                for did in removed_ids:
                    doc = self.db.get(Document, did)
                    if doc:
                        fpath = Path(doc.absolute_path)
                        if fpath.exists() and fpath.is_file():
                            fpath.unlink()
                        self.db.delete(doc)

                doc_service = DocumentService(self.db)
                self.db.execute(delete(ProductImage).where(ProductImage.product_id == id))
                sort = 0
                for data_url in (image_data_urls or []):
                    doc = doc_service.save_base64(data_url)
                    self.db.add(ProductImage(
                        product_id=id,
                        document_id=doc.id,
                        sort_order=sort,
                    ))
                    sort += 1
                for doc_id in (image_document_ids or []):
                    self.db.add(ProductImage(
                        product_id=id,
                        document_id=doc_id,
                        sort_order=sort,
                    ))
                    sort += 1

            self.db.commit()
            return updated
        except IntegrityError as e:
            self.db.rollback()
            raise ProductException(str(e)) from e

    def delete_product(self, id: int) -> bool:
        """Delete product by id. Cleans up associated document records and files."""
        from app.models.document import Document

        product = self.db.get(Product, id)
        if not product:
            return False

        doc_ids = set()

        for pi in product.images:
            if pi.document_id:
                doc_ids.add(pi.document_id)

        for v in product.variants:
            if v.image_document_id:
                doc_ids.add(v.image_document_id)

        self.db.delete(product)
        self.db.flush()

        if doc_ids:
            docs = self.db.scalars(select(Document).where(Document.id.in_(doc_ids))).all()
            for doc in docs:
                fpath = Path(doc.absolute_path)
                if fpath.exists() and fpath.is_file():
                    fpath.unlink()
                self.db.delete(doc)

        self.db.commit()
        return True

    def get_product_suggestions(self, query: str, limit: int = 10) -> list[str]:
        """
        Get product name suggestions for autocomplete.
        """
        if not query or len(query) < 2:
            return []

        search_pattern = f"{query}%"
        contains_pattern = f"%{query}%"

        stmt_prefix = (
            select(Product.name)
            .where(Product.is_active == True)
            .where(Product.name.ilike(search_pattern))
            .distinct()
            .limit(limit)
        )

        prefix_matches = self.db.scalars(stmt_prefix).all()

        if len(prefix_matches) >= limit:
            return list(prefix_matches)[:limit]

        remaining = limit - len(prefix_matches)
        stmt_contains = (
            select(Product.name)
            .where(Product.is_active == True)
            .where(Product.name.ilike(contains_pattern))
            .where(~Product.name.ilike(search_pattern))
            .distinct()
            .limit(remaining)
        )

        contains_matches = self.db.scalars(stmt_contains).all()

        return list(prefix_matches) + list(contains_matches)

    def deduct_stock(self, product_id: int, item_quantity: int):
        stmt = (
            update(Product)
            .where(Product.id == product_id)
            .values(stock_quantity=Product.stock_quantity - item_quantity)
            .returning(Product.id)
        )
        self.db.execute(stmt).scalar_one_or_none()

    def get_total_products(self):
        total_products = self.db.query(func.count(Product.id)).scalar() or 0
        return total_products

    def total_active_products(self):
        active_products = (
            self.db.query(func.count(Product.id))
            .filter(Product.is_active == True)
            .scalar()
            or 0
        )
        return active_products

    def total_inactive_products(self):
        inactive_products = (
            self.db.query(func.count(Product.id))
            .filter(Product.is_active == False)
            .scalar()
            or 0
        )
        return inactive_products

    def out_of_stock_count(self):
        out_stock_count = (
            self.db.query(func.count(Product.id))
            .filter(Product.stock_quantity == 0)
            .scalar()
            or 0
        )
        return out_stock_count

    def low_stock_count(self):
        low_stock_count = (
            self.db.query(func.count(Product.id))
            .filter(and_(Product.stock_quantity > 0, Product.stock_quantity < 10))
            .scalar()
            or 0
        )
        return low_stock_count

    def get_slow_stock_products(self, threshold: int):
        products = (
            self.db.query(Product)
            .filter(
                and_(Product.stock_quantity > 0, Product.stock_quantity < threshold)
            )
            .order_by(Product.stock_quantity.asc())
            .all()
        )
        return products

    def bulk_update_inventory(self, updates: List[BulkInventoryUpdateItem]):
        """Bulk update product inventory"""
        updated_count = 0
        failed_products = []

        for update in updates:
            product = (
                self.db.query(Product).filter(Product.id == update.product_id).first()
            )
            if not product:
                failed_products.append(update.product_id)
                continue

            product.stock_quantity = update.stock_quantity
            updated_count += 1

        self.db.commit()

        return updated_count, failed_products
