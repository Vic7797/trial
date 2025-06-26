from typing import BinaryIO, Dict, List, Optional
from uuid import UUID, uuid4
import io

from fastapi import UploadFile, HTTPException
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession
import pypdf
import docx
from tempfile import NamedTemporaryFile

from app.config import settings
from app.crud.documents import document as document_crud
from app.models.documents import Document
from app.schemas.documents import DocumentCreate
from app.ai.vector_db import vector_db
from app.core.logging import logger

class DocumentService:
    """Service for managing document storage and retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._init_minio_client()

    def _init_minio_client(self):
        """Initialize MinIO client."""
        self.minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            region=settings.MINIO_REGION
        )

        if not self.minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
            self.minio_client.make_bucket(settings.MINIO_BUCKET_NAME)

    async def _store_in_vector_db(
        self,
        document_id: UUID,
        organization_id: UUID,
        content: str,
        category_ids: List[UUID]
    ) -> None:
        """Store document in vector database.
        
        Args:
            document_id: UUID of the document
            organization_id: UUID of the organization
            content: Document content as text
            category_ids: List of category UUIDs
        """
        metadata = {
            "document_id": str(document_id),
            "organization_id": str(organization_id),
            "categories": [str(cat_id) for cat_id in category_ids]
        }
        
        await vector_db.add_documents(
            texts=[content],
            metadatas=[metadata],
            ids=[str(document_id)]
        )

    async def create_document(
        self,
        file: UploadFile,
        organization_id: UUID,
        category_ids: List[UUID],
        uploaded_by: UUID
    ) -> Document:
        """Create a new document with file upload and vector storage."""
        # Validate file
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        if file.content_type not in settings.ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=400, detail="Invalid file type")
            
        document_id = uuid4()
        file_path = f"{organization_id}/{document_id}_{file.filename}"
        
        # Upload to MinIO
        await self._upload_to_minio(file, file_path)
        
        # Create document in database
        document_in = DocumentCreate(
            id=document_id,
            organization_id=organization_id,
            title=file.filename,
            file_path=file_path,
            file_size=file.size,
            mime_type=file.content_type,
            uploaded_by=uploaded_by
        )
        document = await document_crud.create(self.db, obj_in=document_in)
        
        # Process document content and store in vector database
        content = await self._extract_text_content(file)
        await self._store_in_vector_db(
            document_id=document_id,
            organization_id=organization_id,
            content=content,
            category_ids=category_ids
        )
        
        return document

    async def _upload_to_minio(self, file: BinaryIO, file_path: str):
        """Upload file to MinIO storage."""
        try:
            self.minio_client.put_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=file_path,
                data=file.file,
                length=file.size,
                content_type=file.content_type
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {str(e)}"
            )

    async def _extract_text_content(self, file: UploadFile) -> str:
        """
        Extract text content from document.
        Supports PDF, TXT, and DOC/DOCX files.
        """
        try:
            content = await file.read()
            
            if file.content_type == "text/plain":
                return content.decode('utf-8')
            
            elif file.content_type == "application/pdf":
                # Create a bytes buffer and read PDF
                with io.BytesIO(content) as pdf_buffer:
                    pdf_reader = pypdf.PdfReader(pdf_buffer)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            
            elif file.content_type in [
                "application/msword",
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ]:
                # Save to temporary file for docx processing
                with NamedTemporaryFile(
                    delete=False,
                    suffix='.docx'
                ) as temp_file:
                    temp_file.write(content)
                    temp_file.flush()
                    
                    # Read document
                    doc = docx.Document(temp_file.name)
                    paragraphs = [p.text for p in doc.paragraphs]
                    text = "\n".join(paragraphs)
                    return text
            
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file type for text extraction"
                )
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error extracting text content: {str(e)}"
            )
        finally:
            await file.seek(0)  



    async def get_document(
        self,
        document_id: UUID,
        organization_id: UUID
    ) -> Optional[Document]:
        """Get document by ID for an organization."""
        return await document_crud.get_by_org(
            self.db,
            id=document_id,
            organization_id=organization_id
        )

    async def delete_document(
        self,
        document_id: UUID,
        organization_id: UUID
    ) -> bool:
        """Delete document and its associated data."""
        document = await self.get_document(document_id, organization_id)
        if not document:
            return False

        # Delete from MinIO
        try:
            self.minio_client.remove_object(
                settings.MINIO_BUCKET_NAME,
                document.file_path
            )
        except Exception:
            pass  # Continue with deletion even if file removal fails

        # Delete from vector database
        try:
            await vector_db.delete([str(document_id)])
        except Exception as e:
            logger.error(f"Error deleting from vector DB: {str(e)}")
            # Continue with deletion even if vector DB removal fails

        # Delete from database
        await document_crud.delete(self.db, id=document_id)
        return True

    async def search_documents(
        self,
        query: str,
        organization_id: UUID,
        category_ids: Optional[List[UUID]] = None,
        user=None,
        limit: int = 10
    ) -> List[dict]:
        """Search documents using vector similarity, enforcing visibility rules."""
        filter_metadata = {
            "organization_id": str(organization_id)
        }
        # If category_ids provided, search within those categories
        category = str(category_ids[0]) if category_ids else None
        results = await vector_db.search(
            query=query,
            category=category,
            n_results=limit,
            filter_metadata=filter_metadata
        )
        # Filter: public or assigned to user (by org/category)
        visible_docs = []
        user_category_ids = set(str(cid) for cid in getattr(user, 'category_ids', []) or [])
        for doc in results:
            is_public = doc.metadata.get('is_public', False)
            doc_cats = set(doc.metadata.get('categories', []))
            if is_public or (user and (user.organization_id == organization_id or user_category_ids.intersection(doc_cats))):
                visible_docs.append({
                    "document_id": UUID(doc.metadata["document_id"]),
                    "similarity": doc.metadata.get("score", 1.0),
                    "content": doc.page_content
                })
        return visible_docs


    async def verify_storage_integrity(self) -> Dict[str, List[Dict[str, str]]]:
        """Verify consistency between database, MinIO, and vector database.

    Returns:
        Dict containing lists of issues found in each storage system.
    """
        issues = {
            "database": [],
            "minio": [],
            "vector_db": [],
            "orphaned_vectors": []
        }
        
        # Get all documents from database
        db_docs = await document_crud.get_multi(self.db)
        db_doc_ids = {str(doc.id) for doc in db_docs}
        
        # Check MinIO storage
        for doc in db_docs:
            try:
                if not self.minio_client.stat_object(
                    settings.MINIO_BUCKET_NAME,
                    doc.file_path
                ):
                    issues["minio"].append({
                        "id": str(doc.id),
                        "issue": "File not found in MinIO",
                        "path": doc.file_path
                    })
            except Exception as e:
                issues["minio"].append({
                    "id": str(doc.id),
                    "issue": f"Error accessing MinIO: {str(e)}",
                    "path": doc.file_path
                })
        
        # Check vector database
        try:
            vector_docs = await vector_db.get_all_documents()
            vector_doc_ids = {doc.metadata.get("document_id") for doc in vector_docs 
                            if doc.metadata and "document_id" in doc.metadata}
            
            # Find documents in vector DB but not in database
            for doc_id in (vector_doc_ids - db_doc_ids):
                issues["orphaned_vectors"].append({
                    "id": doc_id,
                    "issue": "Document exists in vector DB but not in database"
                })
                
            # Check documents in database but not in vector DB
            for doc_id in (db_doc_ids - vector_doc_ids):
                issues["vector_db"].append({
                    "id": doc_id,
                    "issue": "Document missing from vector DB"
                })
                
        except Exception as e:
            issues["vector_db"].append({
                "issue": f"Error accessing vector database: {str(e)}"
            })
        
        return issues
