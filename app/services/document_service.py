from pathlib import Path
from fastapi import UploadFile
from uuid import uuid4
from datetime import datetime
from app.core.logger import logger
from app.crud.document import DocumentCrud


class DocumentService:
    def __init__(self, db, base_upload_dir: Path | None = None):
        self.db = db
        self.crud = DocumentCrud(db=db)
        # default uploads folder at repo root
        if base_upload_dir:
            self.base_dir = Path(base_upload_dir)
        else:
            self.base_dir = Path(__file__).parent.parent.parent / "uploads"

    async def save_upload(self, upload: UploadFile) -> dict:
        """Save UploadFile to disk under upload/YYYY/MM with timestamped filename.

        Returns dict suitable for Document model creation.
        """
        now = datetime.utcnow()
        year = str(now.year)
        month = f"{now.month:02d}"
        # ensure directories exist
        dest_dir = self.base_dir / year / month
        dest_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(upload.filename).suffix
        stored_name = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}{ext}"
        rel_path = Path("upload") / year / month / stored_name
        abs_path = (dest_dir / stored_name).resolve()

        # write bytes
        with open(abs_path, "wb") as f:
            content = await upload.read()
            f.write(content)

        data = {
            "id": str(uuid4()),
            "original_filename": upload.filename,
            "stored_filename": stored_name,
            "relative_path": str(rel_path).replace('\\\\', '/'),
            "absolute_path": str(abs_path),
            "mime_type": upload.content_type,
            "size": len(content),
        }

        doc = self.crud.create_document(data)
        return doc
