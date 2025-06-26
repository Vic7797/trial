"""
Vector database client implementation using ChromaDB with RAG pipeline.
"""

import os
import uuid
from typing import List, Dict, Any, Optional, Callable

import chromadb
from chromadb.config import Settings
from langchain_core.documents import Document
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.document_compressors import FlashrankRerank
from langchain_community.vectorstores import Chroma
import litellm

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorDBClient:
    """Client for interacting with ChromaDB vector database with RAG pipeline."""

    def __init__(self, collection_name: str = "support_docs"):
        """Initialize the vector database client.
        
        Args:
            collection_name: Name of the collection to use
        """
        self.collection_name = collection_name
        self.client = self._get_chroma_client()
        self.embedding_function = self._get_embedding_function()
        self.collection = self._get_or_create_collection()

    def _get_chroma_client(self) -> chromadb.HttpClient:
        """Create and return a ChromaDB client."""
        return chromadb.HttpClient(
            host=settings.CHROMA_DB_HOST or "localhost",
            port=settings.CHROMA_DB_PORT or 8000,
            ssl=settings.CHROMA_DB_SSL or False
        )

    def _get_embedding_function(self) -> Callable[[List[str]], List[List[float]]]:
        """Get the embedding function using LiteLLM."""

        def embed_function(texts: List[str]) -> List[List[float]]:
            try:
                response = litellm.embedding(
                    model=settings.EMBEDDING_MODEL,
                    input=texts,
                    api_key=settings.OPENAI_API_KEY
                )
                return [item['embedding'] for item in response.data]
            except Exception as e:
                logger.error(f"Error getting embeddings: {str(e)}")
                raise

        return embed_function

    def _get_or_create_collection(self):
        """Get or create a collection in ChromaDB."""
        try:
            return self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
        except ValueError:
            return self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )

    def _setup_retriever(self, category: Optional[str] = None) -> ContextualCompressionRetriever:
        """Set up the retriever with optional category filtering and Flashrank reranking.
        
        Args:
            category: Filter documents by this category before reranking
        """
        filter_dict = {"categories": {"$in": [category]}} if category else None

        db = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embedding_function
        )

        base_retriever = db.as_retriever(
            search_kwargs={
                "k": settings.TOP_K_RESULTS * 2,
                "filter": filter_dict
            }
        )

        compressor = FlashrankRerank(
            model=settings.RERANKER_MODEL,
            top_n=settings.TOP_K_RESULTS
        )

        return ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=base_retriever
        )

    def add_documents(
        self,
        documents: List[Document],
        metadata: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents to the vector database.
        
        Args:
            documents: List of Document objects to add
            metadata: List of metadata dictionaries (must include 'categories' key)
            ids: Optional list of document IDs
        """
        if metadata is None:
            metadata = [{} for _ in documents]

        if len(metadata) != len(documents):
            raise ValueError("Metadata list length must match documents list length")

        texts = [doc.page_content for doc in documents]
        metadatas = []

        for i, doc in enumerate(documents):
            doc_meta = doc.metadata.copy()
            doc_meta.update(metadata[i])
            if 'categories' not in doc_meta:
                logger.warning(f"Document at index {i} has no 'categories' in metadata")
            metadatas.append(doc_meta)

        try:
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids or [str(uuid.uuid4()) for _ in documents]
            )
            logger.info(f"Added {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        n_results: int = settings.TOP_K_RESULTS,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Search for documents matching the query.
        
        Args:
            query: Search query
            category: Optional category filter
            n_results: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of matching documents
        """
        retriever = self._setup_retriever(category)
        results = retriever.get_relevant_documents(
            query,
            filter_metadata=filter_metadata
        )
        return results[:n_results]

    def delete_collection(self) -> None:
        """Delete the current collection."""
        self.client.delete_collection(self.collection_name)

    def reset(self) -> None:
        """Reset the database (delete and recreate collection)."""
        self.delete_collection()
        self.collection = self._get_or_create_collection()

    async def get_all_documents(self) -> List[Document]:
        """Retrieve all documents from the vector database.
        
        Returns:
            List of Document objects with their metadata
        """
        try:
            results = self.collection.get(include=["documents", "metadatas"])
            documents = []
            
            for i in range(len(results["ids"])):
                doc = Document(
                    page_content=results["documents"][i],
                    metadata=results["metadatas"][i] or {}
                )
                documents.append(doc)
                
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            raise


# Singleton instance
vector_db = VectorDBClient()