from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.product_variant import ProductVariant
from app.models.product import Product
from app.models.document import Document
from app.schema.variant_schema import VariantCreate, VariantUpdate
from app.services.document_service import DocumentService


class VariantCrud:
    def __init__(self, db: Session):
        self.db = db

    def _resolve_price(self, product_id: int, price: float | None) -> float:
        if price is not None:
            return price
        product = self.db.get(Product, product_id)
        return float(product.price) if product else 0.0

    def create(self, product_id: int, dto: VariantCreate) -> ProductVariant:
        attrs = [a.model_dump() for a in dto.attributes] if dto.attributes else None
        image_document_id = dto.image_document_id
        if dto.image_data_url:
            doc_service = DocumentService(self.db)
            doc = doc_service.save_base64(dto.image_data_url)
            image_document_id = doc.id
        variant = ProductVariant(
            product_id=product_id,
            name=dto.name,
            attributes=attrs,
            price=self._resolve_price(product_id, dto.price),
            buying_price=dto.buying_price,
            selling_price=dto.selling_price,
            stock_quantity=dto.stock_quantity,
            sku=dto.sku,
            image_document_id=image_document_id,
            sort_order=dto.sort_order,
        )
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def bulk_create(self, product_id: int, variants: List[VariantCreate]) -> List[ProductVariant]:
        created = []
        for dto in variants:
            v = self.create(product_id, dto)
            created.append(v)
        return created

    def get_by_product(self, product_id: int) -> List[ProductVariant]:
        stmt = select(ProductVariant).where(ProductVariant.product_id == product_id).order_by(ProductVariant.sort_order)
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, variant_id: int) -> Optional[ProductVariant]:
        return self.db.get(ProductVariant, variant_id)

    def update(self, variant_id: int, dto: VariantUpdate) -> Optional[ProductVariant]:
        variant = self.db.get(ProductVariant, variant_id)
        if not variant:
            return None
        update_data = dto.model_dump(exclude_unset=True)
        if "attributes" in update_data and update_data["attributes"] is not None:
            update_data["attributes"] = [a.model_dump() for a in update_data["attributes"]]
        if "price" in update_data:
            update_data["price"] = self._resolve_price(variant.product_id, update_data["price"])
        for key, val in update_data.items():
            setattr(variant, key, val)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def delete(self, variant_id: int) -> bool:
        variant = self.db.get(ProductVariant, variant_id)
        if not variant:
            return False
        if variant.image_document_id:
            doc = self.db.get(Document, variant.image_document_id)
            if doc:
                fpath = Path(doc.absolute_path)
                if fpath.exists() and fpath.is_file():
                    fpath.unlink()
                self.db.delete(doc)
        self.db.delete(variant)
        self.db.commit()
        return True

    def delete_by_product(self, product_id: int):
        stmt = select(ProductVariant).where(ProductVariant.product_id == product_id)
        variants = self.db.scalars(stmt).all()
        for v in variants:
            if v.image_document_id:
                doc = self.db.get(Document, v.image_document_id)
                if doc:
                    fpath = Path(doc.absolute_path)
                    if fpath.exists() and fpath.is_file():
                        fpath.unlink()
                    self.db.delete(doc)
            self.db.delete(v)
        self.db.commit()
