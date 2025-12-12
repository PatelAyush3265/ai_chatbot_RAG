"""
PDF Text Extraction and Chunking Module
Handles PDF text extraction and splits text into overlapping chunks for RAG system.
"""

import PyPDF2
from typing import List, Dict
import re


class DocumentProcessor:
    """Process PDF documents and split them into chunks."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        """
        Initialize document processor.
        
        Args:
            chunk_size: Number of characters per chunk
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text as a single string
        """
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Clean up the text
            text = self._clean_text(text)
            return text
        
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing extra whitespace and formatting issues.
        
        Args:
            text: Raw text from PDF
            
        Returns:
            Cleaned text
        """
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove multiple newlines
        text = re.sub(r'\n+', '\n', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text
    
    def create_chunks(self, text: str) -> List[Dict[str, any]]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Full text to chunk
            
        Returns:
            List of chunks with metadata
        """
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size
            
            # If not at the end, try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings (. ! ?) within a window
                window_start = max(start, end - 100)
                window_end = min(len(text), end + 100)
                sentence_end = self._find_sentence_boundary(
                    text[window_start:window_end]
                )
                if sentence_end != -1:
                    end = window_start + sentence_end + 1
            
            # Extract chunk
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    'id': chunk_id,
                    'text': chunk_text,
                    'start_pos': start,
                    'end_pos': end,
                    'length': len(chunk_text)
                })
                chunk_id += 1
            
            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            
            # Prevent infinite loop
            if start >= len(text) - self.chunk_overlap:
                break
        
        return chunks
    
    def _find_sentence_boundary(self, text: str) -> int:
        """
        Find the nearest sentence boundary in text.
        
        Args:
            text: Text to search
            
        Returns:
            Position of sentence boundary or -1 if not found
        """
        # Look for sentence endings
        for delimiter in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
            pos = text.rfind(delimiter)
            if pos != -1:
                return pos + len(delimiter) - 1
        
        return -1
    
    def process_pdf(self, pdf_path: str) -> List[Dict[str, any]]:
        """
        Complete pipeline: extract text from PDF and create chunks.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of text chunks with metadata
        """
        print(f"Extracting text from PDF: {pdf_path}")
        text = self.extract_text_from_pdf(pdf_path)
        print(f"Extracted {len(text)} characters")
        
        print(f"Creating chunks (size={self.chunk_size}, overlap={self.chunk_overlap})")
        chunks = self.create_chunks(text)
        print(f"Created {len(chunks)} chunks")
        
        return chunks


if __name__ == "__main__":
    # Example usage
    processor = DocumentProcessor(chunk_size=500, chunk_overlap=100)
    
    # Example with sample text
    sample_text = """
    Linear regression is a statistical method used to model the relationship between variables.
    Multiple linear regression extends simple linear regression by using more than one predictor variable.
    Polynomial regression fits non-linear data by using polynomial transformation.
    """
    
    chunks = processor.create_chunks(sample_text)
    for chunk in chunks:
        print(f"\nChunk {chunk['id']}:")
        print(f"Text: {chunk['text'][:100]}...")
        print(f"Length: {chunk['length']}")
