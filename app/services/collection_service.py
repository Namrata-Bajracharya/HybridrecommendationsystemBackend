from sqlalchemy.orm import Session
from app.core.exceptions import CollectionCreationError, CollectionUpdateError
from app.crud.collection import CollectionCrud
from app.schema.collection_schema import CreateCollection, UpdateCollection, CollectionPublic
from fastapi import HTTPException, status
from app.core.logger import logger


class CollectionService:
    def __init__(self, db: Session):
        self.db = db
        self.crud = CollectionCrud(db=db)

    def create_collection(self, create_dto: CreateCollection) -> CollectionPublic:
        try:
            result = self.crud.create_collection(create_dto)
            return CollectionPublic.model_validate(result)
        except CollectionCreationError as e:
            logger.warning(f"error: {e}")
            if "UNIQUE constraint" in str(e):
                raise HTTPException(status_code=409, detail="Collection already exists.")
            raise HTTPException(status_code=400, detail="Invalid collection data.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error.")

    def get_collection_by_id(self, id: int) -> CollectionPublic:
        collection = self.crud.get_collection_by_id(id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
            )
        return CollectionPublic.model_validate(collection)

    def get_all_collections(self) -> list[CollectionPublic]:
        try:
            collections = self.crud.get_all_collections()
            return [CollectionPublic.model_validate(c) for c in collections]
        except Exception as e:
            logger.error(f"Error fetching collections: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch collections.",
            )

    def get_collection_by_slug(self, slug: str) -> CollectionPublic:
        collection = self.crud.get_collection_by_slug(slug)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
            )
        return CollectionPublic.model_validate(collection)

    def update_collection(self, id: int, update_dto: UpdateCollection) -> CollectionPublic:
        try:
            updated = self.crud.update_collection(id, update_dto)
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
                )
            return CollectionPublic.model_validate(updated)
        except CollectionUpdateError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="please try again.",
            )

    def delete_collection(self, id: int) -> None:
        is_deleted = self.crud.delete_collection(id)
        if not is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
            )
        return None
