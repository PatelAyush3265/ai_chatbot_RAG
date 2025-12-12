import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def timer(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logger.info(f"{func.__name__} took {end - start:.2f} seconds")
        return result
    return wrapper

def format_retrieved_chunks(results: dict) -> str:
    """Format retrieved chunks into a single context string"""
    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    
    context_parts = []
    for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
        source = meta.get('source', 'Unknown')
        page = meta.get('page', 'N/A')
        context_parts.append(f"[Source: {source}, Page: {page}]\n{doc}\n")
    
    return "\n---\n".join(context_parts)