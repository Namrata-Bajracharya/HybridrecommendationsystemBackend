from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import ProductException
from app.core.logger import logger
from app.crud.category import CategoryCrud
from app.crud.product import ProductCrud
from app.crud.document import DocumentCrud
from app.schema.product_schema import ProductCreate, ProductResponse, ProductUpdate
from app.schema.common_schema import PaginatedResponse


class ProductService:
    def __init__(self, db: Session, redis=None):
        self.db = db
        self.redis_client = redis
        self.crud = ProductCrud(db=db)

    def create_product(self, create_dto: ProductCreate) -> ProductResponse:
        """Create a product and return a validated response model."""
        try:
            if create_dto.image_document_ids:
                doc_crud = DocumentCrud(self.db)
                for doc_id in create_dto.image_document_ids:
                    doc = doc_crud.get_by_id(doc_id)
                    if not doc:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid document id: {doc_id}",
                        )

            result = self.crud.create_product(create_dto)
            return ProductResponse.model_validate(result)
        except ProductException as e:
            if "UNIQUE constraint" in str(e):
                raise HTTPException(status_code=409, detail="Product already exists.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="invalid product data"
            )
        except Exception as e:
            logger.info(f"exception: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="please try again",
            )

    def get_product_by_slug(self, slug: str) -> ProductResponse:
        """Retrieve a product by slug; 404 if not found."""
        product = self.crud.get_product_detail(slug)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )
        return ProductResponse.model_validate(product)

    async def get_product_by_id(self, id: int) -> ProductResponse:
        """Retrieve a product by id with caching (if redis is available)."""
        cache_key = f"product:{id}"

        if self.redis_client:
            try:
                cached_json = await self.redis_client.get_json(cache_key)
                if cached_json:
                    logger.info(f"Cache hit for product: {id}")
                    return ProductResponse.model_validate_json(cached_json)
            except Exception as e:
                logger.warning(f"Cache error: {e}")

        logger.info("Cache miss for product:%s", id)

        product_model = self.crud.get_product_by_id(id)

        if not product_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )

        response_data = ProductResponse.model_validate(product_model)

        if self.redis_client:
            try:
                await self.redis_client.set_json(
                    cache_key, response_data.model_dump_json(), ex=600
                )
            except Exception as e:
                logger.warning(f"Cache set error: {e}")

        return response_data

    def get_all_products(
        self,
        page: Optional[int],
        per_page: Optional[int],
        search: str | None = None,
        category_id: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        min_rating: float | None = None,
        availability: str | None = "all",
        sort_by: str | None = "id",
        sort_order: str | None = "asc",
    ) -> PaginatedResponse[ProductResponse]:
        """List all products with advanced filtering and sorting."""
        try:
            products = self.crud.get_all_products(
                page,
                per_page,
                search,
                category_id,
                min_price,
                max_price,
                min_rating,
                availability,
                sort_by,
                sort_order,
            )
            return products
        except Exception as e:
            logger.info(f"exception: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to fetch products",
            )

    def update_product(self, id: int, update_dto: ProductUpdate) -> ProductResponse:
        """Partially update a product; maps conflicts and not-found to HTTP codes."""
        try:
            if update_dto.image_document_ids is not None:
                doc_crud = DocumentCrud(self.db)
                for doc_id in update_dto.image_document_ids:
                    doc = doc_crud.get_by_id(doc_id)
                    if not doc:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid document id: {doc_id}",
                        )

            updated = self.crud.update_product(id, update_dto)
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
                )
            return ProductResponse.model_validate(updated)
        except ProductException as e:
            if "UNIQUE constraint" in str(e):
                raise HTTPException(status_code=409, detail="Duplicate product data")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid product update data",
            )
        except Exception as e:
            logger.info(f"exception: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="please try again",
            )

    def delete_product(self, id: int) -> None:
        """Delete a product by id; 404 if missing."""
        deleted = self.crud.delete_product(id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )
        return None

    def get_products_by_category_id(self, category_id: int) -> List[ProductResponse]:
        products = self.crud.get_products_by_category_id(category_id)
        return [ProductResponse.model_validate(p) for p in products]

    def get_products_by_category_slug(self, slug: str) -> List[ProductResponse]:
        category = CategoryCrud(self.db).get_category_by_slug(slug)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )
        products = self.crud.get_products_by_category_id(category.id)
        return [ProductResponse.model_validate(p) for p in products]

    async def get_autocomplete_suggestions(self, query: str) -> List[str]:
        if not query or len(query) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query must be at least 2 characters",
            )

        cache_key = f"autocomplete:{query.lower()}"

        cached_suggestions = await self.redis_client.get_json(cache_key)
        if cached_suggestions:
            logger.info(f"Cache hit for autocomplete: {query}")
            import json
            return json.loads(cached_suggestions)

        logger.info(f"Cache miss for autocomplete: {query}")

        suggestions = self.crud.get_product_suggestions(query, limit=10)

        if suggestions:
            import json
            await self.redis_client.set_json(
                cache_key, json.dumps(suggestions), ex=3600
            )

        return suggestions
