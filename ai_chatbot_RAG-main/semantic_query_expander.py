"""
Semantic Query Expansion (SQE)
Uses LLM to generate related topics from user query to improve retrieval coverage.
"""

from groq import Groq
from typing import List, Dict, Set
import os
from dotenv import load_dotenv


class SemanticQueryExpander:
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
            print(f"Error expanding query: {str(e)}")
            # Fall back to original query only
            return [query]
    
    def retrieve_with_expansion(self, 
                                query: str, 
                                retriever,
                                num_expansions: int = 5,
                                top_k_per_query: int = 5) -> List[Dict[str, any]]:
        """
        Retrieve chunks using expanded queries.
        
        Args:
            query: Original query
            retriever: HybridRetriever instance
            num_expansions: Number of query expansions to generate
            top_k_per_query: Number of results to retrieve per expanded query
            
        Returns:
            Merged and deduplicated list of retrieved chunks
        """
        # Expand the query
        print(f"\nExpanding query: '{query}'")
        expanded_queries = self.expand_query(query, num_expansions)
        
        print(f"\nGenerated {len(expanded_queries)} queries:")
        for i, eq in enumerate(expanded_queries, 1):
            print(f"  {i}. {eq}")
        
        # Retrieve for each expanded query
        all_results = {}  # Use dict to deduplicate by chunk ID
        
        print(f"\nRetrieving chunks for each query...")
        for i, expanded_query in enumerate(expanded_queries, 1):
            print(f"\n[{i}/{len(expanded_queries)}] Retrieving for: '{expanded_query}'")
            
            results = retriever.retrieve(expanded_query, top_k=top_k_per_query)
            
            print(f"  Found {len(results)} chunks")
            
            # Add to results dict (deduplicate by chunk ID)
            for result in results:
                chunk_id = result['chunk']['id']
                
                # Keep the result with highest score
                if chunk_id not in all_results or \
                   result['hybrid_score'] > all_results[chunk_id]['hybrid_score']:
                    # Add source query information
                    result['source_query'] = expanded_query
                    all_results[chunk_id] = result
        
        # Convert back to list and sort by score
        merged_results = list(all_results.values())
        merged_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        print(f"\n{'='*60}")
        print(f"Total unique chunks retrieved: {len(merged_results)}")
        print(f"{'='*60}")
        
        return merged_results
    
    def get_expansion_stats(self, query: str, results: List[Dict[str, any]]) -> Dict:
        """
        Get statistics about query expansion results.
        
        Args:
            query: Original query
            results: Retrieved results with source_query field
            
        Returns:
            Statistics dictionary
        """
        if not results:
            return {
                'original_query': query,
                'total_chunks': 0,
                'queries_used': 0
            }
        
        # Count chunks per source query
        query_counts = {}
        for result in results:
            source = result.get('source_query', 'unknown')
            query_counts[source] = query_counts.get(source, 0) + 1
        
        return {
            'original_query': query,
            'total_chunks': len(results),
            'queries_used': len(query_counts),
            'chunks_per_query': query_counts,
            'avg_score': sum(r['hybrid_score'] for r in results) / len(results)
        }


if __name__ == "__main__":
    # Example usage (requires HybridRetriever and chunks)
    print("Semantic Query Expansion Example")
    print("="*60)
    
    # This is just to show the expansion functionality
    # In practice, you'd use it with a HybridRetriever
    
    try:
        expander = SemanticQueryExpander()
        
        query = "linear regression"
        expanded = expander.expand_query(query, num_expansions=6)
        
        print(f"\nOriginal query: {query}")
        print(f"\nExpanded queries ({len(expanded)}):")
        for i, eq in enumerate(expanded, 1):
            print(f"  {i}. {eq}")
    
    except Exception as e:
        print(f"\nNote: {str(e)}")
        print("\nTo use this module, you need to:")
        print("1. Set GROQ_API_KEY in your .env file")
        print("2. Get a free API key from: https://console.groq.com")
        print("3. Install required packages: pip install -r requirements.txt")
