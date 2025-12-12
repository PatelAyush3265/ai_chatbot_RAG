"""
Semantic Query Expansion (SQE) for Quiz Generator
Uses LLM to generate related topics from user query to improve retrieval coverage.
"""

from groq import Groq
from typing import List, Dict, Set
import os
from dotenv import load_dotenv


class QuizSemanticQueryExpander:
    """Expand queries using LLM to generate related topics."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize semantic query expander.
        
        Args:
            api_key: Groq API key (if None, reads from environment)
        """
        load_dotenv()
        
        if api_key is None:
            api_key = os.getenv('GROQ_API_KEY')
        
        if not api_key:
            raise ValueError(
                "Groq API key not found. Set GROQ_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = Groq(api_key=api_key)
    
    def expand_query(self, query: str, num_expansions: int = 5) -> List[str]:
        """
        Generate related topics/queries from the main query.
        
        Args:
            query: Original user query
            num_expansions: Number of related topics to generate
            
        Returns:
            List of expanded queries (including original)
        """
        prompt = f"""Given the topic: "{query}"

Generate {num_expansions} closely related topics, subtopics, or alternative phrasings that would be relevant when searching a technical document.

Focus on:
- Direct subtopics and extensions (e.g., "linear regression" → "multiple linear regression")
- Key terminology and concepts related to the topic
- Common variations and specific techniques
- Mathematical or theoretical foundations
- Practical applications

Return ONLY the related topics, one per line, without numbering or explanations.
Do NOT include the original query.

Example:
Query: "linear regression"
Output:
multiple linear regression
predictor variables
ordinary least squares
cost function
polynomial regression
regression assumptions
"""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are an expert at generating related technical topics for document retrieval."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            # Parse the response
            expanded_queries = response.choices[0].message.content.strip().split('\n')
            
            # Clean up the queries
            expanded_queries = [q.strip() for q in expanded_queries if q.strip()]
            
            # Remove any numbering or bullet points
            expanded_queries = [
                q.lstrip('0123456789.-•*) ').strip() 
                for q in expanded_queries
            ]
            
            # Filter out empty strings and duplicates
            expanded_queries = list(dict.fromkeys([q for q in expanded_queries if q]))
            
            # Add original query at the beginning
            all_queries = [query] + expanded_queries[:num_expansions]
            
            return all_queries
        
        except Exception as e:
            print(f"Warning: Query expansion failed: {e}")
            return [query]
    
    def retrieve_with_expansion(self, 
                               query: str,
                               retriever,
                               num_expansions: int = 5,
                               chunks_per_query: int = 5,
                               session_id: str = "default") -> List[Dict[str, any]]:
        """
        Retrieve chunks using query expansion.
        
        Args:
            query: Original query
            retriever: HybridRetriever instance
            num_expansions: Number of query expansions
            chunks_per_query: Chunks to retrieve per expanded query
            session_id: Session identifier for retrieval
            
        Returns:
            Deduplicated list of retrieved chunks
        """
        print(f"\nExpanding query: '{query}'")
        
        # Expand query
        expanded_queries = self.expand_query(query, num_expansions)
        
        print(f"Generated {len(expanded_queries)} queries:")
        for i, q in enumerate(expanded_queries, 1):
            print(f"  {i}. {q}")
        
        # Retrieve for each query
        all_chunks = {}
        
        for exp_query in expanded_queries:
            chunks = retriever.retrieve(exp_query, top_k=chunks_per_query, session_id=session_id)
            
            for chunk in chunks:
                chunk_id = chunk.get('chunk_id')
                
                if chunk_id not in all_chunks:
                    all_chunks[chunk_id] = chunk
                else:
                    # Keep chunk with higher score
                    if chunk['score'] > all_chunks[chunk_id]['score']:
                        all_chunks[chunk_id] = chunk
        
        # Convert to list and sort by score
        result_chunks = sorted(
            all_chunks.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        print(f"\nRetrieved {len(result_chunks)} unique chunks")
        
        return result_chunks
