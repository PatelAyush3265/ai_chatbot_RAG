from sentence_transformers import SentenceTransformer
from typing import List
import logging

logger = logging.getLogger(__name__)

class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding model directly without Hugging Face login"""
        logger.info(f"Loading embedding model: {model_name}")
        # Directly load public model
        self.model = SentenceTransformer(model_name, device='cpu')  # or 'cuda' if GPU
        logger.info("Embedding model loaded successfully")
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Convert list of texts into embeddings"""
        logger.info(f"Creating embeddings for {len(texts)} texts")
        embeddings = self.model.encode(texts, show_progress_bar=True)
        return embeddings.tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """Convert a single query into embedding"""
        logger.info(f"Creating embedding for query: {query[:50]}...")
        embedding = self.model.encode([query])
        return embedding[0].tolist()
