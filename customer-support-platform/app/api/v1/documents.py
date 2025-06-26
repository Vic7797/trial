from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Query, Path
from app.core.security import get_current_user, require_admin
from app.schemas.documents import (
    DocumentResponse,
    DocumentList,
    DocumentSearch,
    DocumentCategoryUpdate
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/", response_model=DocumentList)
async def list_documents(
    category: Optional[str] = None,
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    current_user=Depends(require_admin)
):
    """List all documents with optional category filter (admin only)"""
    document_service = DocumentService()
    return await document_service.list_documents(
        category=category,
        page=page,
        per_page=per_page
    )


@router.post("/", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    category_ids: list[str] = Query(None),
    is_public: bool = Query(False),
    current_user=Depends(require_admin)
):
    """Upload a new document (admin only)"""
    document_service = DocumentService()
    return await document_service.upload_document(
        file=file,
        category_ids=category_ids,
        is_public=is_public
    )


@router.get("/search", response_model=DocumentSearch)
async def search_documents(
    q: str = Query(..., min_length=3),
    category: Optional[str] = None,
    is_public: Optional[bool] = None,
    file_type: Optional[str] = None,
    uploaded_after: Optional[str] = None,
    uploaded_before: Optional[str] = None,
    sort_by: str = "relevance",
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    current_user=Depends(get_current_user)
):
    """Search documents with various filters"""
    document_service = DocumentService()
    return await document_service.search_documents(
        query=q,
        category=category,
        is_public=is_public,
        file_type=file_type,
        uploaded_after=uploaded_after,
        uploaded_before=uploaded_before,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
        user=current_user
    )


@router.get("/public", response_model=DocumentList)
async def list_public_documents(
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    current_user=Depends(get_current_user)
):
    """List all public documents"""
    document_service = DocumentService()
    return await document_service.list_public_documents(
        page=page,
        per_page=per_page
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str = Path(...),
    current_user=Depends(get_current_user)
):
    """Get document details"""
    document_service = DocumentService()
    return await document_service.get_document(document_id, current_user)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str = Path(...),
    current_user=Depends(require_admin)
):
    """Delete document (admin only)"""
    document_service = DocumentService()
    await document_service.delete_document(document_id)
    return None


@router.put("/{document_id}/categories", response_model=DocumentResponse)
async def update_document_categories(
    category_data: DocumentCategoryUpdate,
    document_id: str = Path(...),
    current_user=Depends(require_admin)
):
    """Update document categories (admin only)"""
    document_service = DocumentService()
    return await document_service.update_categories(document_id, category_data.category_ids)