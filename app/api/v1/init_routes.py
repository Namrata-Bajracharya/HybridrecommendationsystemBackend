from fastapi import FastAPI

from app.api.v1.routes import (
    admin,
    cart,
    category,
    collection,
    document,
    # elastic,  # DISABLED: Not required for development
    healthcheck,
    order,
    payment,
    product,
    recommendation,
    review,
    shipping,
    user,
    variant,
    wishlist,
    test,
    test_recommendation,
)


def init_routes(app: FastAPI):
    app.include_router(router=healthcheck.router, prefix="/healthcheck")
    app.include_router(router=user.router, prefix="/users")
    app.include_router(router=category.router, prefix="/category")
    app.include_router(router=product.router, prefix="/product")
    app.include_router(router=document.router, prefix="/document")
    app.include_router(router=cart.router, prefix="/cart")
    app.include_router(router=order.router, prefix="/order")
    app.include_router(router=review.router, prefix="/reviews")
    app.include_router(router=payment.router, prefix="/payments")
    app.include_router(router=admin.router, prefix="/admin")
    app.include_router(router=wishlist.router, prefix="/wishlist")
    app.include_router(router=shipping.router)         # root_path supplies /api/v1
    app.include_router(router=recommendation.router)   # root_path supplies /api/v1; router has its own /recommendations prefix
    # app.include_router(router=elastic.router, prefix="/elastic")  # DISABLED: Not required
    app.include_router(router=collection.router, prefix="/collections")
    app.include_router(router=variant.router)          # root_path supplies /api/v1
    app.include_router(router=test.router, prefix="/test")
    app.include_router(router=test_recommendation.router)
