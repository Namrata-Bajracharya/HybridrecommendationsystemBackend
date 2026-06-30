"""
Pydantic schemas for recommendation endpoints
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class RecommendationItem(BaseModel):
    """Single recommendation result"""
    item_id: str = Field(..., description="Recommended product ID")
    rank: int = Field(..., description="Ranking position (1 = highest)")
    score: float = Field(..., ge=0.0, le=1.0, description="Recommendation confidence score [0-1]")
    reason: str = Field(default="Personalized for you", description="Why this item is recommended")

    class Config:
        json_schema_extra = {
            "example": {
                "item_id": "amazon::B07XVD1RR7",
                "rank": 1,
                "score": 0.92,
                "reason": "Based on your purchase history"
            }
        }


class RecommendationResponse(BaseModel):
    """Response containing list of recommendations"""
    user_id: Optional[str] = Field(None, description="User ID (if applicable)")
    product_id: Optional[str] = Field(None, description="Product ID (if applicable)")
    recommendation_type: str = Field(..., description="Type of recommendation (user, product, cart, review, similar_users)")
    recommendations: List[RecommendationItem] = Field(..., description="List of recommended items")
    total_count: int = Field(..., description="Total number of recommendations")
    timestamp: Optional[str] = Field(None, description="Timestamp of recommendation generation")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "recommendation_type": "user",
                "recommendations": [
                    {
                        "item_id": "amazon::B07XVD1RR7",
                        "rank": 1,
                        "score": 0.92,
                        "reason": "Based on your purchase history"
                    },
                    {
                        "item_id": "hm::123456",
                        "rank": 2,
                        "score": 0.87,
                        "reason": "Similar to items you liked"
                    }
                ],
                "total_count": 2,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class SimilarProductResponse(BaseModel):
    """Response for similar products endpoint"""
    product_id: str = Field(..., description="Base product ID")
    similar_products: List[RecommendationItem] = Field(..., description="List of similar products")
    total_count: int = Field(..., description="Total number of similar products found")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "amazon::B07XVD1RR7",
                "similar_products": [
                    {
                        "item_id": "amazon::B08YVD1RR8",
                        "rank": 1,
                        "score": 0.89,
                        "reason": "Similar product"
                    }
                ],
                "total_count": 1
            }
        }


class CartRecommendationRequest(BaseModel):
    """Request for cart-based recommendations"""
    user_id: str = Field(..., description="User ID")
    cart_items: List[str] = Field(..., description="List of item IDs in cart", min_items=1)
    top_k: int = Field(default=5, ge=1, le=20, description="Number of recommendations to return")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "cart_items": ["amazon::B07XVD1RR7", "hm::123456"],
                "top_k": 5
            }
        }


class ReviewBasedRecommendationRequest(BaseModel):
    """Request for review/rating based recommendations"""
    user_id: str = Field(..., description="User ID")
    product_id: str = Field(..., description="Product ID being reviewed")
    rating: int = Field(..., ge=1, le=5, description="User's rating (1-5 stars)")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of recommendations to return")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "product_id": "amazon::B07XVD1RR7",
                "rating": 5,
                "top_k": 5
            }
        }


class UserSimilarityRecommendationResponse(BaseModel):
    """Response for user similarity based recommendations"""
    user_id: str = Field(..., description="Target user ID")
    recommendations: List[RecommendationItem] = Field(..., description="Recommended items from similar users")
    total_count: int = Field(..., description="Total recommendations")
    similar_users_count: int = Field(..., description="Number of similar users analyzed")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "recommendations": [
                    {
                        "item_id": "amazon::B07XVD1RR7",
                        "rank": 1,
                        "score": 0.85,
                        "reason": "Based on users with similar taste"
                    }
                ],
                "total_count": 1,
                "similar_users_count": 3
            }
        }
