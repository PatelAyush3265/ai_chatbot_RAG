import os
import logging
from typing import List
from backend.document_loader import DocumentLoader
from backend.text_splitter import RecursiveCharacterTextSplitter
from backend.embeddings import EmbeddingModel
from backend.vector_store import ChromaVectorStore
from backend.llm import GroqLLM
from backend.utils import timer, format_retrieved_chunks
from backend import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGPipeline:
    """Complete RAG pipeline"""

    def __init__(self):
        """Initialize all components"""
        logger.info("Initializing RAG Pipeline")

        self.embedding_model = EmbeddingModel(config.EMBEDDING_MODEL)
        self.vector_store = ChromaVectorStore(
            persist_directory=config.CHROMA_DB_DIR,
            embedding_function=self.embedding_model
        )
        self.llm = GroqLLM(
            api_key=config.GROQ_API_KEY,
            model=config.LLM_MODEL
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP
        )

        logger.info("RAG Pipeline initialized successfully")

    @timer
    def process_documents(self, file_paths: List[str]) -> dict:
        """Process and index documents"""
        logger.info(f"Processing {len(file_paths)} files")
        documents = DocumentLoader.load_documents(file_paths)

        if not documents:
            return {"status": "error", "message": "No documents loaded"}

        chunks = self.text_splitter.split_documents(documents)
        texts = [chunk.page_content for chunk in chunks]
        embeddings = self.embedding_model.embed_texts(texts)
        self.vector_store.add_documents(chunks, embeddings)
        stats = self.vector_store.get_stats()

        return {
            "status": "success",
            "files_processed": len(file_paths),
            "chunks_created": len(chunks),
            "total_documents": stats["total_documents"]
        }

    @timer
    def query(self, user_query: str) -> dict:
        """Answer user query using RAG"""
        try:
            logger.info(f"Processing query: {user_query}")
            query_embedding = self.embedding_model.embed_texts([user_query])[0]
            results = self.vector_store.query(query_embedding, top_k=config.TOP_K_RESULTS)

            if not results["documents"] or len(results["documents"][0]) == 0:
                return {
                    "status": "error",
                    "answer": "No relevant documents found. Please upload documents first."
                }

            context = "\n\n".join(results["documents"][0])
            prompt = f"""You are a helpful AI assistant. Use the following context to answer the user's question in detail.

Context:
{context}

Question: {user_query}

Instructions:
- Provide a comprehensive and detailed answer
- Use specific information from the context
- If the context doesn't contain enough information, say so
- Organize your answer with proper structure
- Aim for at least 3-5 sentences or more if needed

Answer:"""

            answer = self.llm.generate_response(prompt, context, user_query)

            sources = []
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                sources.append({
                    "text": doc[:300] + "..." if len(doc) > 300 else doc,
                    "source": meta.get("source", "Unknown"),
                    "page": meta.get("page", "N/A")
                })

            return {
                "status": "success",
                "answer": answer,
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "status": "error",
                "answer": f"Error: {str(e)}"
            }

    def add_document(self, file_path: str):
        """Process and index a single document file"""
        result = self.process_documents([file_path])
        if result.get("status") == "success":
            return [None] * result.get("chunks_created", 0)
        else:
            return []

    def add_text(self, name: str, text: str):
        """Process and index a text string as a document"""
        temp_path = os.path.join(config.UPLOAD_DIR if hasattr(config, "UPLOAD_DIR") else "uploads", f"{name}.txt")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(text)
        result = self.process_documents([temp_path])
        if result.get("status") == "success":
            return [None] * result.get("chunks_created", 0)
        else:
            return []

    def get_sources(self):
        """Get list of all document sources"""
        return self.vector_store.get_sources()

    def delete_source(self, source_name: str):
        """Delete a source document from the vector store"""
        return self.vector_store.delete_source(source_name)

    def clear_database(self):
        """Clear the vector database"""
        self.vector_store.clear_database()
        return {"status": "success", "message": "Database cleared"}

    def get_stats(self):
        """Get database statistics"""
        return self.vector_store.get_stats()