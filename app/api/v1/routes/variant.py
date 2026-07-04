from typing import Annotated, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_admin
from app.schema.user_schema import UserPublic
from app.schema.variant_schema import VariantCreate, VariantUpdate, VariantBulkCreate, VariantPublic
from app.crud.variant import VariantCrud

router = APIRouter(tags=["Variants"])
admin_dependency = Annotated[UserPublic, Depends(require_admin)]


def get_crud(db: Session = Depends(get_db)) -> VariantCrud:
    return VariantCrud(db)


@router.get("/products/{product_id}/variants", response_model=List[VariantPublic])
def list_variants(product_id: int, db: Session = Depends(get_db)):
    return VariantCrud(db).get_by_product(product_id)


@router.post("/products/{product_id}/variants", response_model=List[VariantPublic], status_code=status.HTTP_201_CREATED)
def create_variants(
    product_id: int,
    body: VariantBulkCreate,
    db: Session = Depends(get_db),
    _: admin_dependency = None,
):
    return VariantCrud(db).bulk_create(product_id, body.variants)


@router.put("/variants/{variant_id}", response_model=VariantPublic)
def update_variant(
    variant_id: int,
    body: VariantUpdate,
    db: Session = Depends(get_db),
    _: admin_dependency = None,
):
    updated = VariantCrud(db).update(variant_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Variant not found")
    return updated


@router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(
    variant_id: int,
    db: Session = Depends(get_db),
    _: admin_dependency = None,
):
    deleted = VariantCrud(db).delete(variant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Variant not found")
