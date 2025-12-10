"""
Hybrid Retrieval System
Combines Cosine Similarity (semantic) and BM25 (keyword-based) scoring.
Final Score = 0.7 × CosineSimilarity + 0.3 × BM25
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple
import re


class HybridRetriever:
    """Hybrid retrieval combining semantic similarity and BM25 keyword matching."""
    
    def __init__(self, 
                 model_name: str = 'all-MiniLM-L6-v2',
                 cosine_weight: float = 0.7,
                 bm25_weight: float = 0.3,
                 threshold: float = 0.45):
        """
        Initialize hybrid retriever.
        
        Args:
            model_name: Sentence transformer model name
            cosine_weight: Weight for cosine similarity (default 0.7)
            bm25_weight: Weight for BM25 score (default 0.3)
            threshold: Minimum score threshold for retrieval (default 0.45)
        """
        self.model = SentenceTransformer(model_name)
        self.cosine_weight = cosine_weight
        self.bm25_weight = bm25_weight
        self.threshold = threshold
        
        # Storage for chunks and embeddings
        self.chunks = []
        self.chunk_embeddings = None
        self.bm25 = None
        self.tokenized_chunks = []
    
    def index_chunks(self, chunks: List[Dict[str, any]]):
        """
        Index chunks for retrieval by creating embeddings and BM25 index.
        
        Args:
            chunks: List of text chunks with metadata
        """
        self.chunks = chunks
        texts = [chunk['text'] for chunk in chunks]
        
        print(f"Creating embeddings for {len(texts)} chunks...")
        # Create embeddings for semantic similarity
        self.chunk_embeddings = self.model.encode(texts, show_progress_bar=True)
        
        print("Creating BM25 index...")
        # Tokenize chunks for BM25
        self.tokenized_chunks = [self._tokenize(text) for text in texts]
        self.bm25 = BM25Okapi(self.tokenized_chunks)
        
        print("Indexing complete!")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens (words)
        """
        # Convert to lowercase and split by non-alphanumeric characters
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """
        Normalize scores to [0, 1] range.
        
        Args:
            scores: Array of scores
            
        Returns:
            Normalized scores
        """
        if len(scores) == 0:
            return scores
        
        min_score = np.min(scores)
        max_score = np.max(scores)
        
        # Avoid division by zero
        if max_score - min_score < 1e-10:
            return np.ones_like(scores)
        
        normalized = (scores - min_score) / (max_score - min_score)
        return normalized
    
    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, any]]:
        """
        Retrieve relevant chunks using hybrid scoring.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of retrieved chunks with scores
        """
        if not self.chunks or self.chunk_embeddings is None or self.bm25 is None:
            raise ValueError("No chunks indexed. Call index_chunks() first.")
        
        # 1. Compute cosine similarity scores
        query_embedding = self.model.encode([query])[0]
        cosine_scores = cosine_similarity(
            [query_embedding], 
            self.chunk_embeddings
        )[0]
        
        # 2. Compute BM25 scores
        query_tokens = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(query_tokens)
        
        # 3. Normalize BM25 scores to [0, 1]
        bm25_scores_normalized = self._normalize_scores(bm25_scores)
        
        # 4. Compute hybrid scores
        hybrid_scores = (
            self.cosine_weight * cosine_scores + 
            self.bm25_weight * bm25_scores_normalized
        )
        
        # 5. Create results with all scores
        results = []
        for idx, chunk in enumerate(self.chunks):
            if hybrid_scores[idx] >= self.threshold:
                results.append({
                    'chunk': chunk,
                    'hybrid_score': float(hybrid_scores[idx]),
                    'cosine_score': float(cosine_scores[idx]),
                    'bm25_score': float(bm25_scores_normalized[idx]),
                    'text': chunk['text']
                })
        
        # 6. Sort by hybrid score (descending)
        results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        # 7. Return top K results
        return results[:top_k]
    
    def get_retrieval_stats(self, query: str, results: List[Dict[str, any]]) -> Dict:
        """
        Get statistics about the retrieval results.
        
        Args:
            query: Original query
            results: Retrieved results
            
        Returns:
            Statistics dictionary
        """
        if not results:
            return {
                'query': query,
                'total_retrieved': 0,
                'avg_hybrid_score': 0.0,
                'avg_cosine_score': 0.0,
                'avg_bm25_score': 0.0
            }
        
        return {
            'query': query,
            'total_retrieved': len(results),
            'avg_hybrid_score': np.mean([r['hybrid_score'] for r in results]),
            'avg_cosine_score': np.mean([r['cosine_score'] for r in results]),
            'avg_bm25_score': np.mean([r['bm25_score'] for r in results]),
            'top_score': results[0]['hybrid_score'] if results else 0.0
        }


if __name__ == "__main__":
    # Example usage
    sample_chunks = [
        {
            'id': 0,
            'text': 'Linear regression is a statistical method used to model the relationship between variables.',
            'start_pos': 0,
            'end_pos': 100,
            'length': 100
        },
        {
            'id': 1,
            'text': 'Multiple linear regression extends simple linear regression by using more than one predictor variable.',
            'start_pos': 100,
            'end_pos': 200,
            'length': 100
        },
        {
            'id': 2,
            'text': 'Polynomial regression fits non-linear data by using polynomial transformation.',
            'start_pos': 200,
            'end_pos': 300,
            'length': 100
        }
    ]
    
    retriever = HybridRetriever()
    retriever.index_chunks(sample_chunks)
    
    query = "linear regression"
    results = retriever.retrieve(query, top_k=3)
    
    print(f"\nQuery: {query}")
    print(f"Retrieved {len(results)} chunks:\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. Chunk {result['chunk']['id']}")
        print(f"   Hybrid Score: {result['hybrid_score']:.3f}")
        print(f"   Cosine Score: {result['cosine_score']:.3f}")
        print(f"   BM25 Score: {result['bm25_score']:.3f}")
        print(f"   Text: {result['text'][:80]}...\n")
