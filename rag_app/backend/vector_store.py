import chromadb
from chromadb.config import Settings
from typing import List, Dict
import logging
import uuid

logger = logging.getLogger(__name__)

class ChromaVectorStore:
    """Manage ChromaDB vector store"""
    
    def __init__(self, persist_directory: str, embedding_function):
        """Initialize ChromaDB"""
        logger.info(f"Initializing ChromaDB at {persist_directory}")
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.embedding_function = embedding_function
        self.collection_name = "rag_documents"
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "RAG document embeddings"}
        )
        
        logger.info(f"Collection '{self.collection_name}' ready")
    
    def add_documents(self, documents: List, embeddings: List[List[float]]):
        """Add documents with embeddings to ChromaDB"""
        logger.info(f"Adding {len(documents)} documents to ChromaDB")
        
        # Generate unique IDs using UUID to avoid duplicates
        ids = [str(uuid.uuid4()) for _ in documents]
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        try:
            self.collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Successfully added {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise
    
    def query(self, query_embedding: List[float], top_k: int = 5) -> Dict:
        """Query ChromaDB with embedding"""
        logger.info(f"Querying ChromaDB for top {top_k} results")
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        logger.info(f"Retrieved {len(results['documents'][0])} results")
        return results
    
    def clear_database(self):
        """Clear all documents from database"""
        logger.info("Clearing ChromaDB")
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "RAG document embeddings"}
        )
        logger.info("Database cleared")
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        count = self.collection.count()
        
        # Get list of uploaded files
        try:
            all_data = self.collection.get()
            uploaded_files = []
            if all_data and 'metadatas' in all_data:
                sources = set()
                for metadata in all_data['metadatas']:
                    if metadata and 'source' in metadata:
                        source = metadata['source']
                        # Extract filename from path
                        if '/' in source or '\\' in source:
                            source = source.replace('\\', '/').split('/')[-1]
                        sources.add(source)
                uploaded_files = list(sources)
        except Exception as e:
            logger.error(f"Error getting uploaded files: {e}")
            uploaded_files = []
        
        return {
            "total_documents": count,
            "uploaded_files": uploaded_files
        }
    
    def get_sources(self) -> list:
        """Get list of all document sources"""
        try:
            logger.info("Fetching sources from ChromaDB")
            all_data = self.collection.get()
            
            if not all_data or 'metadatas' not in all_data:
                return []
            
            sources = []
            seen = set()
            
            for i, metadata in enumerate(all_data['metadatas']):
                if metadata and 'source' in metadata:
                    source_path = metadata['source']
                    # Extract filename from path
                    if '/' in source_path or '\\' in source_path:
                        source_name = source_path.replace('\\', '/').split('/')[-1]
                    else:
                        source_name = source_path
                    
                    # Avoid duplicates
                    if source_name not in seen:
                        seen.add(source_name)
                        sources.append({
                            "name": source_name,
                            "source": source_path,
                            "page": metadata.get('page', 'N/A')
                        })
            
            logger.info(f"Found {len(sources)} unique sources")
            return sources
            
        except Exception as e:
            logger.error(f"Error fetching sources: {e}")
            return []
    
    def delete_source(self, source_name: str) -> int:
        """Delete all documents from a specific source"""
        try:
            logger.info(f"Deleting source: {source_name}")
            all_data = self.collection.get()
            
            if not all_data or 'metadatas' not in all_data:
                return 0
            
            ids_to_delete = []
            for i, metadata in enumerate(all_data['metadatas']):
                if metadata and 'source' in metadata:
                    source_path = metadata['source']
                    # Extract filename from path
                    if '/' in source_path or '\\' in source_path:
                        current_source = source_path.replace('\\', '/').split('/')[-1]
                    else:
                        current_source = source_path
                    
                    if current_source == source_name or source_path == source_name:
                        ids_to_delete.append(all_data['ids'][i])
            
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} documents from source {source_name}")
            
            return len(ids_to_delete)
            
        except Exception as e:
            logger.error(f"Error deleting source: {e}")
            return 0