from fastapi import APIRouter, Depends, UploadFile, File
from app.dependencies import get_document_service_dep, require_admin
from app.services.document_service import DocumentService
from app.schema.document_schema import DocumentPublic
from app.schema.user_schema import UserPublic

router = APIRouter(tags=["Document"])


@router.post("", response_model=DocumentPublic, summary="Upload a file")
async def upload_file(
    upload: UploadFile = File(...),
    doc_service: DocumentService = Depends(get_document_service_dep),
    current_admin: UserPublic = Depends(require_admin),
):
    doc = await doc_service.save_upload(upload)
    return doc
