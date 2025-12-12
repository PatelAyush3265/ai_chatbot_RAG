import os

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable must be set")

# Quiz Generator API Key (separate key for quiz feature)
QUIZ_GROQ_API_KEY = os.getenv("QUIZ_GROQ_API_KEY")
if not QUIZ_GROQ_API_KEY:
    raise ValueError("QUIZ_GROQ_API_KEY environment variable must be set")

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
CHROMA_DB_DIR = os.path.join(BASE_DIR, "chroma_db")
SENTIMENT_MODEL_DIR = os.path.join(BASE_DIR, "sentiment_model")
QUIZ_UPLOAD_DIR = os.path.join(BASE_DIR, "quiz_uploads")
QUIZ_OUTPUT_DIR = os.path.join(BASE_DIR, "quiz_outputs")

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DB_DIR, exist_ok=True)
os.makedirs(QUIZ_UPLOAD_DIR, exist_ok=True)
os.makedirs(QUIZ_OUTPUT_DIR, exist_ok=True)

# Model Settings
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.3-70b-versatile"

# Quiz Generator Model Settings
QUIZ_LLM_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # Specific model for quiz generation
QUIZ_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# RAG Settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 3
TOP_K_RESULTS = 3  # Added this line

# Quiz Generator Settings
QUIZ_CHUNK_SIZE = 1000
QUIZ_CHUNK_OVERLAP = 280
QUIZ_COSINE_WEIGHT = 0.7
QUIZ_BM25_WEIGHT = 0.3
QUIZ_RETRIEVAL_THRESHOLD = 0.3