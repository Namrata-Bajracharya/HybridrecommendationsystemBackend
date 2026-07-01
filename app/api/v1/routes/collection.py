from fastapi import APIRouter, Depends
from app.schema.collection_schema import CreateCollection, UpdateCollection, CollectionPublic
from app.schema.user_schema import UserPublic
from app.dependencies import (
    get_collection_service_dep,
    require_admin,
)
from app.services.collection_service import CollectionService
from typing import Annotated, List

router = APIRouter(tags=["Collection"])

collection_dependency = Annotated[CollectionService, Depends(get_collection_service_dep)]
admin_dependency = Annotated[UserPublic, Depends(require_admin)]


@router.post(
    "",
    response_model=CollectionPublic,
    status_code=201,
    summary="Create collection",
    description="Create a new collection (admin only).",
)
async def create_collection(
    create_dto: CreateCollection,
    collection_service: collection_dependency,
    current_admin: admin_dependency,
):
    return collection_service.create_collection(create_dto)


@router.get(
    "",
    response_model=List[CollectionPublic],
    summary="List collections",
    description="Returns all collections.",
)
async def get_all_collections(
    collection_service: collection_dependency,
):
    return collection_service.get_all_collections()


@router.get(
    "/{slug}",
    response_model=CollectionPublic,
    summary="Get collection by slug",
    description="Retrieve a collection by slug.",
)
async def get_collection_by_slug(
    slug: str,
    collection_service: collection_dependency,
):
    return collection_service.get_collection_by_slug(slug)


@router.put(
    "/{id}",
    response_model=CollectionPublic,
    summary="Update collection",
    description="Partially update a collection (admin only).",
)
async def update_collection(
    id: int,
    update_dto: UpdateCollection,
    collection_service: collection_dependency,
    current_admin: admin_dependency,
):
    return collection_service.update_collection(id, update_dto)


@router.delete(
    "/{id}",
    summary="Delete collection",
    description="Delete a collection by id (admin only).",
)
async def delete_collection(
    id: int,
    collection_service: collection_dependency,
    current_admin: admin_dependency,
):
    collection_service.delete_collection(id)
    return {"detail": "collection deleted successfully"}
