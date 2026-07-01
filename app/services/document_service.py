import base64
import mimetypes
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
        content = await upload.read()
        return self._save_bytes(
            content=content,
            filename=upload.filename,
            mime_type=upload.content_type,
        )

    def save_base64(self, data_url: str) -> dict:
        """Save a base64 data URL to disk and return Document-compatible dict.

        Expects format: "data:image/png;base64,iVBOR..."
        """
        try:
            mime_type = None
            if ";" in data_url and data_url.startswith("data:"):
                header, _, b64 = data_url.partition(",")
                mime_type = header.replace("data:", "").replace(";base64", "")
            else:
                b64 = data_url

            content = base64.b64decode(b64)

            if not mime_type:
                mime_type = "application/octet-stream"

            ext = mimetypes.guess_extension(mime_type) or ".bin"
            filename = f"image_{uuid4().hex}{ext}"
            return self._save_bytes(content=content, filename=filename, mime_type=mime_type)
        except Exception as e:
            logger.error(f"Failed to save base64 image: {e}")
            raise

    def delete_document(self, doc_id: str) -> bool:
        doc = self.crud.get_by_id(doc_id)
        if not doc:
            return False
        file_path = Path(doc.absolute_path)
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
        return self.crud.delete(doc_id)

    def _save_bytes(self, content: bytes, filename: str, mime_type: str | None) -> dict:
        """Write raw bytes to disk under upload/YYYY/MM and return Document dict."""
        now = datetime.utcnow()
        year = str(now.year)
        month = f"{now.month:02d}"
        dest_dir = self.base_dir / year / month
        dest_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(filename).suffix
        stored_name = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}{ext}"
        rel_path = Path("upload") / year / month / stored_name
        abs_path = (dest_dir / stored_name).resolve()

        with open(abs_path, "wb") as f:
            f.write(content)

        data = {
            "id": str(uuid4()),
            "original_filename": filename,
            "stored_filename": stored_name,
            "relative_path": str(rel_path).replace('\\\\', '/'),
            "absolute_path": str(abs_path),
            "mime_type": mime_type,
            "size": len(content),
        }

        doc = self.crud.create_document(data)
        return doc
