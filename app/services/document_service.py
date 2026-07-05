import base64
import io
import mimetypes
from pathlib import Path
from fastapi import UploadFile
from uuid import uuid4
from datetime import datetime
from PIL import Image
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
        """Write raw bytes to disk under upload/YYYY/MM and return Document dict.
        Compresses images (JPEG, PNG, WebP) to reduce file size with minimal quality loss.
        """
        now = datetime.utcnow()
        year = str(now.year)
        month = f"{now.month:02d}"
        dest_dir = self.base_dir / year / month
        dest_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(filename).suffix
        stored_name = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}{ext}"
        rel_path = Path(year) / month / stored_name
        abs_path = (dest_dir / stored_name).resolve()

        content, mime_type, ext = self._compress_image(content, mime_type)

        if ext:
            stored_name = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}{ext}"
            rel_path = Path(year) / month / stored_name
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

    def _compress_image(self, content: bytes, mime_type: str | None) -> tuple[bytes, str | None, str | None]:
        """Compress image bytes with minimal quality loss and significant size reduction."""
        if not mime_type or not mime_type.startswith("image/"):
            return content, mime_type, None

        try:
            img = Image.open(io.BytesIO(content))
            buf = io.BytesIO()
            save_ext = None

            if mime_type == "image/jpeg":
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(buf, format="JPEG", quality=85, optimize=True, progressive=True)
                save_ext = ".jpg"
            elif mime_type == "image/png":
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                img.save(buf, format="PNG", optimize=True, compress_level=9)
                save_ext = ".png"
            elif mime_type == "image/webp":
                img.save(buf, format="WEBP", quality=85, method=6)
                save_ext = ".webp"
            else:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(buf, format=img.format or "JPEG", optimize=True)
                save_ext = Path(f".{img.format.lower()}" if img.format else ".jpg").suffix

            compressed = buf.getvalue()
            if len(compressed) < len(content):
                return compressed, mime_type, save_ext
            return content, mime_type, None
        except Exception as e:
            logger.warning(f"Image compression failed for {mime_type}, saving raw: {e}")
            return content, mime_type, None
