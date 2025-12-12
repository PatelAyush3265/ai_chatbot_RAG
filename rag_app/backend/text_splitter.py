import re
import hashlib
from typing import List
import logging

logger = logging.getLogger(__name__)

class Document:
    """Document class for compatibility"""
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata

class RecursiveCharacterTextSplitter:
    """Split text into chunks with overlap"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 75):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", " ", ""]
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split multiple documents into chunks"""
        logger.info(f"Splitting {len(documents)} documents")
        all_chunks = []
        
        for doc in documents:
            chunks = self._split_text(doc.page_content)
            
            for i, chunk in enumerate(chunks):
                # Create unique chunk ID
                chunk_id = hashlib.md5(chunk.encode()).hexdigest()
                
                chunk_doc = Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        "chunk_id": chunk_id,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                )
                all_chunks.append(chunk_doc)
        
        logger.info(f"Created {len(all_chunks)} chunks")
        return all_chunks
    
    def _split_text(self, text: str) -> List[str]:
        """Split text recursively using separators"""
        chunks = []
        
        # Start with the text
        current_chunks = [text]
        
        for separator in self.separators:
            new_chunks = []
            
            for chunk in current_chunks:
                if len(chunk) <= self.chunk_size:
                    new_chunks.append(chunk)
                else:
                    # Split by separator
                    splits = chunk.split(separator) if separator else list(chunk)
                    
                    # Merge small splits
                    merged = []
                    current = ""
                    
                    for split in splits:
                        if len(current) + len(split) + len(separator) <= self.chunk_size:
                            current += split + separator
                        else:
                            if current:
                                merged.append(current.strip())
                            current = split + separator
                    
                    if current:
                        merged.append(current.strip())
                    
                    new_chunks.extend(merged)
            
            current_chunks = new_chunks
        
        # Add overlap
        final_chunks = []
        for i, chunk in enumerate(current_chunks):
            if i > 0 and self.chunk_overlap > 0:
                # Add overlap from previous chunk
                prev_chunk = current_chunks[i-1]
                overlap = prev_chunk[-self.chunk_overlap:]
                chunk = overlap + " " + chunk
            
            final_chunks.append(chunk.strip())
        
        return [c for c in final_chunks if c]