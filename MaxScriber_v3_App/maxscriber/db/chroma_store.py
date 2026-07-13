import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

try:
    # pyrefly: ignore [missing-import]
    import chromadb
    # pyrefly: ignore [missing-import]
    from chromadb.config import Settings
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("chromadb not found. VectorStoreManager will be disabled.")

class VectorStoreManager:
    """
    Manages local vector storage using ChromaDB for semantic search and 
    audit trails of extracted clinical data.
    """
    
    def __init__(self, persist_directory: str = "maxscriber_chroma_db"):
        self.ml_available = ML_AVAILABLE
        if not self.ml_available:
            logger.error("Attempted to initialize VectorStoreManager without chromadb.")
            return

        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection_name = "clinical_audit_trail"
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        logger.info(f"Initialized ChromaDB vector store at {self.persist_directory}")

    def store_document(self, doc_id: str, text: str, metadata: Dict[str, Any]):
        """
        Stores a document and its metadata in the vector database.
        
        Args:
            doc_id (str): Unique identifier for the document/report.
            text (str): The raw or parsed text of the report.
            metadata (dict): Structured data extracted from the report.
        """
        if not self.ml_available:
            return

        # Ensure metadata values are strings, ints, or floats for ChromaDB
        sanitized_metadata = {k: str(v) for k, v in metadata.items()}

        self.collection.add(
            documents=[text],
            metadatas=[sanitized_metadata],
            ids=[doc_id]
        )
        logger.info(f"Stored document {doc_id} in vector store.")

    def search_similar(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Searches for clinical reports semantically similar to the query.
        
        Args:
            query_text (str): The search query.
            n_results (int): Number of top results to return.
            
        Returns:
            dict: The search results from ChromaDB.
        """
        if not self.ml_available:
            return {"error": "ChromaDB not available."}

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

    def get_audit_trail(self, doc_id: str) -> Dict[str, Any]:
        """
        Retrieves the exact record for a given document ID.
        """
        if not self.ml_available:
            return {"error": "ChromaDB not available."}

        return self.collection.get(ids=[doc_id])
