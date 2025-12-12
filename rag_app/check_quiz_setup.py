"""
Quick diagnostic script to check quiz generator setup
Run: python check_quiz_setup.py
"""

import sys
import os

def check_import(module_name, import_statement):
    """Check if a module can be imported."""
    try:
        exec(import_statement)
        print(f"✓ {module_name}: OK")
        return True
    except ImportError as e:
        print(f"✗ {module_name}: FAILED - {e}")
        return False
    except Exception as e:
        print(f"⚠ {module_name}: ERROR - {e}")
        return False

def check_file(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"✓ {description}: EXISTS")
        return True
    else:
        print(f"✗ {description}: MISSING")
        return False

print("=" * 70)
print("🔍 QUIZ GENERATOR SETUP DIAGNOSTIC")
print("=" * 70)

# Check Python version
print(f"\n📌 Python Version: {sys.version}")

# Check core dependencies
print("\n📦 Checking Dependencies:")
print("-" * 70)
deps_ok = all([
    check_import("sentence_transformers", "from sentence_transformers import SentenceTransformer"),
    check_import("PyPDF2", "import PyPDF2"),
    check_import("rank_bm25", "from rank_bm25 import BM25Okapi"),
    check_import("sklearn", "from sklearn.metrics.pairwise import cosine_similarity"),
    check_import("groq", "from groq import Groq"),
    check_import("dotenv", "from dotenv import load_dotenv"),
    check_import("numpy", "import numpy as np"),
])

# Check quiz modules
print("\n🧩 Checking Quiz Modules:")
print("-" * 70)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
modules_ok = all([
    check_import("quiz_document_processor", "from backend.quiz_document_processor import QuizDocumentProcessor"),
    check_import("quiz_hybrid_retriever", "from backend.quiz_hybrid_retriever import QuizHybridRetriever"),
    check_import("quiz_semantic_query_expander", "from backend.quiz_semantic_query_expander import QuizSemanticQueryExpander"),
    check_import("quiz_question_generator", "from backend.quiz_question_generator import QuizQuestionGenerator"),
])

# Check files
print("\n📁 Checking Files:")
print("-" * 70)
files_ok = all([
    check_file("backend/quiz_document_processor.py", "Document Processor"),
    check_file("backend/quiz_hybrid_retriever.py", "Hybrid Retriever"),
    check_file("backend/quiz_semantic_query_expander.py", "Query Expander"),
    check_file("backend/quiz_question_generator.py", "Question Generator"),
    check_file("backend/config.py", "Config File"),
    check_file(".env", "Environment File"),
])

# Check directories
print("\n📂 Checking Directories:")
print("-" * 70)
dirs_ok = all([
    check_file("quiz_uploads", "Quiz Uploads Dir"),
    check_file("quiz_outputs", "Quiz Outputs Dir"),
])

# Check environment variables
print("\n🔑 Checking Environment Variables:")
print("-" * 70)
from dotenv import load_dotenv
load_dotenv()

groq_key = os.getenv('GROQ_API_KEY')
quiz_key = os.getenv('QUIZ_GROQ_API_KEY')

if groq_key:
    print(f"✓ GROQ_API_KEY: SET ({groq_key[:20]}...)")
else:
    print("✗ GROQ_API_KEY: NOT SET")

if quiz_key:
    print(f"✓ QUIZ_GROQ_API_KEY: SET ({quiz_key[:20]}...)")
else:
    print("⚠ QUIZ_GROQ_API_KEY: NOT SET (will use GROQ_API_KEY)")

env_ok = bool(groq_key or quiz_key)

# Final verdict
print("\n" + "=" * 70)
if deps_ok and modules_ok and files_ok and env_ok:
    print("✅ ALL CHECKS PASSED - Quiz generator is ready!")
    print("\nNext steps:")
    print("1. Start backend: uvicorn backend.main:app --reload --port 8000")
    print("2. Start frontend: cd ../ai-chat-react && npm start")
    print("3. Open http://localhost:3000 and click Quiz Generator in menu")
else:
    print("❌ SOME CHECKS FAILED - Please fix the issues above")
    print("\nTo fix dependency issues, run:")
    print("pip install --upgrade sentence-transformers==2.7.0 PyPDF2==3.0.1 rank-bm25==0.2.2 python-dotenv==1.0.0")
print("=" * 70)
