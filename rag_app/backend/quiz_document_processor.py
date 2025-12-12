"""
PDF Text Extraction and Chunking Module for Quiz Generator
Handles PDF text extraction and splits text into overlapping chunks for RAG system.
Converts documents into embeddings and stores them in vector database.
"""

import PyPDF2
from typing import List, Dict
import re
import os
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class QuizDocumentProcessor:
    """Process PDF documents and split them into chunks for quiz generation."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize document processor.
        
        Args:
            chunk_size: Number of characters per chunk
            chunk_overlap: Number of overlapping characters between chunks
            embedding_model: Model name for generating embeddings
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        logger.info("Embedding model loaded successfully")
    
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
    
    def extract_text_from_txt(self, txt_path: str) -> str:
        """
        Extract text from a TXT file.
        
        Args:
            txt_path: Path to the TXT file
            
        Returns:
            Extracted text as a single string
        """
        try:
            with open(txt_path, 'r', encoding='utf-8') as file:
                text = file.read()
            return self._clean_text(text)
        except Exception as e:
            raise Exception(f"Error extracting text from TXT: {str(e)}")
    
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
                    'chunk_id': chunk_id,
                    'text': chunk_text,
                    'start_char': start,
                    'end_char': end
                })
                chunk_id += 1
            
            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            
            # Ensure we make progress
            if start <= chunks[-1]['start_char'] if chunks else False:
                start = end
        
        return chunks
    
    def _find_sentence_boundary(self, text: str) -> int:
        """
        Find the last sentence boundary in text.
        
        Args:
            text: Text to search
            
        Returns:
            Position of sentence boundary, or -1 if not found
        """
        # Look for sentence endings
        for delimiter in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
            pos = text.rfind(delimiter)
            if pos != -1:
                return pos
        
        return -1
    
    def process_pdf(self, pdf_path: str) -> List[Dict[str, any]]:
        """
        Complete pipeline: extract text and create chunks.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of text chunks
        """
        print(f"Processing PDF: {pdf_path}")
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            raise ValueError("No text could be extracted from the PDF. Please check the file content.")
        print(f"Extracted {len(text)} characters")
        chunks = self.create_chunks(text)
        print(f"Created {len(chunks)} chunks")
        return chunks
    
    def process_file(self, file_path: str) -> List[Dict[str, any]]:
        """
        Process any supported file type.
        
        Args:
            file_path: Path to file
            
        Returns:
            List of text chunks
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return self.process_pdf(file_path)
        elif ext in ['.txt', '.md']:
            text = self.extract_text_from_txt(file_path)
            if not text:
                raise ValueError("No text could be extracted from the file. Please check the file content.")
            print(f"Extracted {len(text)} characters")
            chunks = self.create_chunks(text)
            print(f"Created {len(chunks)} chunks")
            return chunks
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def create_embeddings(self, chunks: List[Dict[str, any]]) -> List[List[float]]:
        """
        Generate embeddings for text chunks.
        Performs full RAG preprocessing:
        - Text extraction (already done)
        - Chunking (already done)
        - Tokenization (handled by embedding model)
        - Embedding generation
        
        Args:
            chunks: List of text chunks with metadata
            
        Returns:
            List of embeddings (one per chunk)
        """
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings - the model handles tokenization internally
        # All word meanings and sentence semantics are preserved
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        logger.info(f"✓ Generated {len(embeddings)} embeddings")
        return embeddings.tolist()
