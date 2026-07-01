from sqlalchemy.orm import Session
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from app.core.exceptions import CollectionCreationError, CollectionUpdateError
from app.models.collection import Collection
from app.schema.collection_schema import CreateCollection, UpdateCollection
from app.utils.generate_slug import generate_slug


class CollectionCrud:
    def __init__(self, db: Session):
        self.db = db

    def create_collection(self, create_dto: CreateCollection) -> Collection:
        try:
            data = create_dto.model_dump()
            slug = generate_slug(self.db, data["name"], "collection")
            data["slug"] = slug
            collection = Collection(**data)
            self.db.add(collection)
            self.db.commit()
            self.db.refresh(collection)
            return collection
        except IntegrityError as e:
            self.db.rollback()
            raise CollectionCreationError(str(e)) from e

    def get_collection_by_id(self, id: int) -> Collection | None:
        stmt = select(Collection).where(Collection.id == id)
        return self.db.scalar(stmt)

    def get_collection_by_slug(self, slug: str) -> Collection | None:
        stmt = select(Collection).where(Collection.slug == slug)
        return self.db.scalar(stmt)

    def update_collection(self, id: int, update_dto: UpdateCollection) -> Collection:
        try:
            update_data = update_dto.model_dump(exclude_unset=True)
            if not update_data:
                return self.get_collection_by_id(id)
            stmt = (
                update(Collection)
                .where(Collection.id == id)
                .values(**update_data)
                .returning(Collection)
            )
            updated = self.db.execute(stmt).scalar_one_or_none()
            self.db.commit()
            return updated
        except ValueError as e:
            raise CollectionUpdateError(str(e)) from e

    def delete_collection(self, id: int) -> bool:
        stmt = delete(Collection).where(Collection.id == id)
        result = self.db.execute(stmt)
        if result.rowcount == 0:
            return False
        self.db.commit()
        return True

    def get_all_collections(self) -> list[Collection]:
        stmt = select(Collection).order_by(Collection.id)
        return list(self.db.scalars(stmt).all())
