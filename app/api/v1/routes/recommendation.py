"""
Recommendation API Routes
Hybrid recommendation engine combining collaborative + content-based filtering
"""
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Path, Query, status
from datetime import datetime

from app.services.recommendation_service import RecommendationService
from app.schema.recommendation_schema import (
    RecommendationResponse,
    RecommendationItem,
    SimilarProductResponse,
    CartRecommendationRequest,
    ReviewBasedRecommendationRequest,
    UserSimilarityRecommendationResponse,
)
from app.dependencies import get_db
from app.core.logger import logger
from sqlalchemy.orm import Session

router = APIRouter(tags=["Recommendations"], prefix="/recommendations")

# recommendation_dependency will be defined after get_recommendation_service


def get_recommendation_service(db: Session = Depends(get_db)) -> RecommendationService:
    """Dependency to get recommendation service instance"""
    return RecommendationService(db=db)


# Create an Annotated dependency usable in route signatures
recommendation_dependency = Annotated[RecommendationService, Depends(get_recommendation_service)]


@router.get(
    "/for-user/{user_id}",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Personalized Recommendations",
    description="Generate personalized recommendations for a user based on their purchase history, browsing behavior, and user similarity",
)
async def get_recommendations_for_user(
    user_id: Annotated[str, Path(..., description="User ID")],
    top_k: Annotated[int, Query(ge=1, le=50, description="Number of recommendations")] = 10,
    exclude_ids: Annotated[Optional[str], Query(description="Comma-separated product IDs to exclude")] = None,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """
    Generate personalized recommendations for a user.
    
    Uses:
    - User's purchase history
    - Item popularity and ratings
    - Content similarity
    - User behavior patterns
    
    Query Parameters:
    - user_id: Target user ID
    - top_k: Number of recommendations (1-50, default 10)
    - exclude_ids: Comma-separated product IDs to exclude from recommendations
    
    Returns:
    - List of recommended products with scores and reasons
    """
    try:
        service = get_recommendation_service(db)
        
        exclude_list = []
        if exclude_ids:
            exclude_list = [id.strip() for id in exclude_ids.split(",")]
        
        recommendations = service.get_recommendations_for_user(
            user_id=user_id,
            top_k=top_k,
            exclude_ids=exclude_list,
        )
        
        logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
        
        return RecommendationResponse(
            user_id=user_id,
            recommendation_type="user",
            recommendations=recommendations,
            total_count=len(recommendations),
            timestamp=datetime.utcnow().isoformat(),
        )
    
    except Exception as e:
        logger.error(f"Error generating recommendations for user {user_id}: {e}")
        return RecommendationResponse(
            user_id=user_id,
            recommendation_type="user",
            recommendations=[],
            total_count=0,
            timestamp=datetime.utcnow().isoformat(),
        )


@router.get(
    "/similar-products/{product_id}",
    response_model=SimilarProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Similar Products",
    description="Find products similar to a given product using content-based and collaborative filtering",
)
async def get_similar_products(
    product_id: Annotated[str, Path(..., description="Base product ID")],
    top_k: Annotated[int, Query(ge=1, le=20, description="Number of similar products")] = 5,
    db: Session = Depends(get_db),
) -> SimilarProductResponse:
    """
    Get products similar to the specified product.
    
    Similarity is determined by:
    - Product content features (category, attributes, descriptions)
    - Collaborative signal (users who bought X also bought Y)
    
    Query Parameters:
    - product_id: Target product ID
    - top_k: Number of similar products (1-20, default 5)
    
    Returns:
    - List of similar products with similarity scores
    """
    try:
        service = get_recommendation_service(db)
        
        similar_items = service.get_similar_products(
            product_id=product_id,
            top_k=top_k,
        )
        
        logger.info(f"Found {len(similar_items)} similar products for {product_id}")
        
        return SimilarProductResponse(
            product_id=product_id,
            similar_products=similar_items,
            total_count=len(similar_items),
        )
    
    except Exception as e:
        logger.error(f"Error finding similar products for {product_id}: {e}")
        return SimilarProductResponse(
            product_id=product_id,
            similar_products=[],
            total_count=0,
        )


@router.post(
    "/cart-items",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Cart-Based Recommendations",
    description="Generate recommendations based on items currently in user's shopping cart",
)
async def get_cart_recommendations(
    request: CartRecommendationRequest,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """
    Generate recommendations based on items in the user's cart.
    
    Analyzes each cart item and recommends complementary products
    that other users frequently purchased together.
    
    Request Body:
    - user_id: User ID
    - cart_items: List of product IDs in cart
    - top_k: Number of recommendations (1-20, default 5)
    
    Returns:
    - List of recommended complementary products
    """
    try:
        service = get_recommendation_service(db)
        
        recommendations = service.get_cart_recommendations(
            user_id=request.user_id,
            cart_items=request.cart_items,
            top_k=request.top_k,
        )
        
        logger.info(
            f"Generated {len(recommendations)} cart recommendations for user {request.user_id} "
            f"with {len(request.cart_items)} cart items"
        )
        
        return RecommendationResponse(
            user_id=request.user_id,
            recommendation_type="cart",
            recommendations=recommendations,
            total_count=len(recommendations),
            timestamp=datetime.utcnow().isoformat(),
        )
    
    except Exception as e:
        logger.error(f"Error generating cart recommendations: {e}")
        return RecommendationResponse(
            user_id=request.user_id,
            recommendation_type="cart",
            recommendations=[],
            total_count=0,
            timestamp=datetime.utcnow().isoformat(),
        )


@router.post(
    "/review-based",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Review-Based Recommendations",
    description="Generate recommendations based on user's product review/rating",
)
async def get_review_based_recommendations(
    request: ReviewBasedRecommendationRequest,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """
    Generate recommendations based on a product review/rating.
    
    Logic:
    - High rating (4-5★): Recommend similar products user might like
    - Low rating (1-2★): Recommend alternative products user might prefer
    
    Request Body:
    - user_id: User ID
    - product_id: Product being reviewed
    - rating: User's rating (1-5 stars)
    - top_k: Number of recommendations (1-20, default 5)
    
    Returns:
    - List of recommended products based on rating behavior
    """
    try:
        service = get_recommendation_service(db)
        
        recommendations = service.get_review_based_recommendations(
            user_id=request.user_id,
            product_id=request.product_id,
            rating=request.rating,
            top_k=request.top_k,
        )
        
        logger.info(
            f"Generated {len(recommendations)} review-based recommendations for user {request.user_id} "
            f"who rated product {request.product_id} as {request.rating}★"
        )
        
        reason_prefix = "Similar products" if request.rating >= 4 else "Alternative products"
        
        return RecommendationResponse(
            user_id=request.user_id,
            product_id=request.product_id,
            recommendation_type="review",
            recommendations=recommendations,
            total_count=len(recommendations),
            timestamp=datetime.utcnow().isoformat(),
        )
    
    except Exception as e:
        logger.error(f"Error generating review-based recommendations: {e}")
        return RecommendationResponse(
            user_id=request.user_id,
            product_id=request.product_id,
            recommendation_type="review",
            recommendations=[],
            total_count=0,
            timestamp=datetime.utcnow().isoformat(),
        )


@router.get(
    "/similar-users/{user_id}",
    response_model=UserSimilarityRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Similar User Recommendations",
    description="Find users with similar buying patterns and recommend their purchases",
)
async def get_similar_user_recommendations(
    user_id: Annotated[str, Path(..., description="Target user ID")],
    top_k: Annotated[int, Query(ge=1, le=50, description="Number of recommendations")] = 10,
    db: Session = Depends(get_db),
) -> UserSimilarityRecommendationResponse:
    """
    Generate recommendations based on similar users' purchase behavior.
    
    This implements hybrid collaborative filtering:
    1. Finds users with similar purchase history (Jaccard similarity)
    2. Identifies items those users purchased that target user hasn't
    3. Recommends top items with highest combined similarity scores
    
    Query Parameters:
    - user_id: Target user ID
    - top_k: Number of recommendations (1-50, default 10)
    
    Returns:
    - List of recommended products from similar users
    - Number of similar users analyzed
    """
    try:
        service = get_recommendation_service(db)
        
        recommendations = service.get_similar_user_recommendations(
            user_id=user_id,
            top_k=top_k,
        )
        
        similar_users_count = min(5, len(recommendations))  # Estimate from results
        
        logger.info(
            f"Generated {len(recommendations)} recommendations for user {user_id} "
            f"based on {similar_users_count} similar users"
        )
        
        return UserSimilarityRecommendationResponse(
            user_id=user_id,
            recommendations=recommendations,
            total_count=len(recommendations),
            similar_users_count=similar_users_count,
        )
    
    except Exception as e:
        logger.error(f"Error generating similar user recommendations for {user_id}: {e}")
        return UserSimilarityRecommendationResponse(
            user_id=user_id,
            recommendations=[],
            total_count=0,
            similar_users_count=0,
        )


@router.post("/clear-cache", status_code=status.HTTP_200_OK)
async def clear_recommendation_cache(
    db: Session = Depends(get_db),
):
    """
    Clear all cached recommendations.
    
    Useful when:
    - Data has been updated significantly
    - Need to force fresh recommendation generation
    - Clearing memory for performance
    
    Returns:
    - Success status
    """
    try:
        service = get_recommendation_service(db)
        service.clear_cache()
        
        logger.info("Recommendation caches cleared")
        
        return {
            "status": "success",
            "message": "Recommendation caches cleared successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error clearing recommendation cache: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
