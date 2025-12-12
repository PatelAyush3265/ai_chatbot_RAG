import os
import hashlib
from typing import List, Dict
import pdfplumber
import re
import logging

logger = logging.getLogger(__name__)

class Document:
    """LangChain-style Document object"""
    def __init__(self, page_content: str, metadata: Dict):
        self.page_content = page_content
        self.metadata = metadata
    
    def __repr__(self):
        return f"Document(page_content='{self.page_content[:50]}...', metadata={self.metadata})"

def clean_text(text: str) -> str:
    """Remove PDF artifacts and clean text"""
    # Remove (cid:XX) patterns
    text = re.sub(r'\(cid:\d+\)', '', text)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters that cause issues
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return text.strip()

class DocumentLoader:
    """Load and extract text from PDF and TXT files"""
    
    @staticmethod
    def load_pdf(file_path: str) -> List[Document]:
        """Extract text from PDF file"""
        documents = []
        logger.info(f"Loading PDF: {file_path}")
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        # Clean the text
                        cleaned_text = clean_text(text)
                        if cleaned_text:
                            doc = Document(
                                page_content=cleaned_text,
                                metadata={
                                    "source": os.path.basename(file_path),
                                    "page": page_num,
                                    "file_type": "pdf"
                                }
                            )
                            documents.append(doc)
            
            logger.info(f"Extracted {len(documents)} pages from PDF")
            return documents
        
        except Exception as e:
            logger.error(f"Error loading PDF {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def load_txt(file_path: str) -> List[Document]:
        """Extract text from TXT file"""
        logger.info(f"Loading TXT: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if text.strip():
                # Clean the text
                cleaned_text = clean_text(text)
                if cleaned_text:
                    doc = Document(
                        page_content=cleaned_text,
                        metadata={
                            "source": os.path.basename(file_path),
                            "page": 1,
                            "file_type": "txt"
                        }
                    )
                    logger.info(f"Loaded TXT file with {len(cleaned_text)} characters")
                    return [doc]
            
            return []
        
        except Exception as e:
            logger.error(f"Error loading TXT {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def load_documents(file_paths: List[str]) -> List[Document]:
        """Load multiple documents"""
        all_documents = []
        
        for file_path in file_paths:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.pdf':
                docs = DocumentLoader.load_pdf(file_path)
                all_documents.extend(docs)
            elif ext == '.txt':
                docs = DocumentLoader.load_txt(file_path)
                all_documents.extend(docs)
            else:
                logger.warning(f"Unsupported file type: {file_path}")
        
        logger.info(f"Total documents loaded: {len(all_documents)}")
        return all_documents