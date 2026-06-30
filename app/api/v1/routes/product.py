from fastapi import APIRouter, Depends, Path, Query, status
from app.schema.common_schema import PaginatedResponse
from app.schema.product_schema import ProductCreate, ProductUpdate, ProductResponse
from app.schema.search_schema import (
    AvailabilityFilter,
    SortByField,
    SortOrder,
    ProductAutocompleteResponse,
)
from app.services.product_service import ProductService
from app.dependencies import get_product_service_dep, require_admin
from app.schema.user_schema import UserPublic
from typing import Annotated, List
from app.core.logger import logger
import enum
from datetime import datetime
from app.dependencies import get_recommendation_service_dep, get_optional_user
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["Product"])
product_dependency = Annotated[ProductService, Depends(get_product_service_dep)]
admin_dependency = Annotated[UserPublic, Depends(require_admin)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProductResponse)
async def create_prodcut(
    create_dto: ProductCreate,
    product_service: product_dependency,
    current_admin: admin_dependency,
) -> ProductResponse:
    product = product_service.create_product(create_dto)
    # for traceabilty purpose
    logger.info(
        f"current user creating the product: {current_admin.id} product: {product.id}"
    )
    return product


@router.get("", response_model=PaginatedResponse[ProductResponse])
async def get_all_products(
    product_service: product_dependency,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 10,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    min_rating: Annotated[float | None, Query(ge=0, le=5)] = None,
    availability: AvailabilityFilter = AvailabilityFilter.ALL,
    sort_by: SortByField = SortByField.ID,
    sort_order: SortOrder = SortOrder.ASC,
) -> PaginatedResponse[ProductResponse]:
    """
    Get all products with advanced filtering and sorting.

    **Filters:**
    - `search`: Search in product name and description (case-insensitive)
    - `category_id`: Filter by category
    - `min_price`, `max_price`: Price range filter
    - `min_rating`: Minimum average rating (0-5)
    - `availability`: Stock availability (all, in_stock, out_of_stock)

    **Sorting:**
    - `sort_by`: Field to sort by (id, name, price, rating, popularity, created_at)
    - `sort_order`: Sort direction (asc, desc)

    **Pagination:**
    - `page`: Page number (1-indexed)
    - `per_page`: Items per page (1-100)
    """
    return product_service.get_all_products(
        page,
        per_page,
        search,
        category_id,
        min_price,
        max_price,
        min_rating,
        availability.value,
        sort_by.value,
        sort_order.value,
    )


@router.get("/autocomplete", response_model=ProductAutocompleteResponse)
async def get_product_autocomplete(
    product_service: product_dependency,
    q: Annotated[str, Query(min_length=2, max_length=100, description="Search query")],
) -> ProductAutocompleteResponse:
    """
    Get product name suggestions for autocomplete.

    **Requirements:**
    - Query must be at least 2 characters
    - Returns maximum 10 suggestions
    - Results are cached for 1 hour

    **Matching:**
    - Prioritizes products that start with the query
    - Falls back to products containing the query
    - Case-insensitive matching
    """
    suggestions = await product_service.get_autocomplete_suggestions(q)
    return ProductAutocompleteResponse(suggestions=suggestions)


@router.get("/category/{slug}", response_model=List[ProductResponse])
async def get_products_by_category_slug(
    slug: Annotated[str, Path(title="The category slug")],
    product_service: product_dependency,
) -> List[ProductResponse]:
    return product_service.get_products_by_category_slug(slug)


@router.get("/id/{id}", response_model=ProductResponse)
async def get_product_by_id(
    id: int, product_service: product_dependency, current_admin: admin_dependency
) -> ProductResponse:
    return await product_service.get_product_by_id(id)


@router.get("/{slug}", response_model=ProductResponse)
async def get_product_by_slug(
    slug: Annotated[str, Path(title="The slug of the item to get")],
    product_service: product_dependency,
) -> ProductResponse:
    return product_service.get_product_by_slug(slug)


@router.put("/{id}", response_model=ProductResponse)
async def update_product(
    id: int,
    update_dto: ProductUpdate,
    product_service: product_dependency,
    current_admin: admin_dependency,
) -> ProductResponse:
    return product_service.update_product(id, update_dto)


@router.delete("/{id}")
async def delete_product(
    id: int, product_service: product_dependency, current_admin: admin_dependency
):
    product_service.delete_product(id)
    return {"detail": "product deleted successfully"}


@router.get("/{slug}/recommendations", response_model="app.schema.recommendation_schema.RecommendationResponse")
async def get_product_recommendations(
    slug: Annotated[str, Path(title="The slug of the item")],
    product_service: product_dependency,
    rec_service: Annotated[RecommendationService, Depends(get_recommendation_service_dep)],
    current_user: Annotated[UserPublic | None, Depends(get_optional_user)],
    top_k: Annotated[int, Query(ge=1, le=50)] = 5,
) -> "app.schema.recommendation_schema.RecommendationResponse":
    """Get product-based and user-aware recommendations for a product detail view."""
    # Load product and derive an item identifier used by recommendation engine
    product = product_service.get_product_by_slug(slug)
    if not product:
        return {
            "user_id": current_user.id if current_user else None,
            "recommendation_type": "product",
            "recommendations": [],
            "total_count": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

    item_id = str(product.id)

    # 1) Similar products based on content + collaborative signals
    similar = rec_service.get_similar_products(product_id=item_id, top_k=top_k)

    # 2) If user present, get personalized recommendations and merge
    merged = []
    seen = set()

    for rec in similar:
        if rec["item_id"] not in seen and rec["item_id"] != item_id:
            seen.add(rec["item_id"])
            merged.append(rec)

    if current_user:
        user_recs = rec_service.get_recommendations_for_user(
            user_id=str(current_user.id), top_k=top_k, exclude_ids=[item_id]
        )
        for rec in user_recs:
            if rec["item_id"] not in seen and rec["item_id"] != item_id:
                seen.add(rec["item_id"])
                merged.append(rec)

    # Trim to top_k
    merged = merged[:top_k]

    return {
        "user_id": str(current_user.id) if current_user else None,
        "product_id": item_id,
        "recommendation_type": "product",
        "recommendations": merged,
        "total_count": len(merged),
        "timestamp": datetime.utcnow().isoformat(),
    }
