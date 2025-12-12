"""
Quiz Generator RAG Pipeline - Verification Script

This script verifies that the full RAG pipeline is working correctly:
1. Document upload with embedding generation
2. Vector database storage
3. Hybrid retrieval (0.7 × Cosine + 0.3 × BM25)
4. Quiz generation
"""

import os
import sys
import requests
import json
from pathlib import Path

# Configuration
BACKEND_URL = "http://localhost:8000"
TEST_DOCUMENT_PATH = None  # Set this to test with a specific file

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_success(text):
    """Print success message"""
    print(f"✅ {text}")

def print_error(text):
    """Print error message"""
    print(f"❌ {text}")

def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")

def verify_backend():
    """Check if backend is running"""
    print_header("Step 1: Verify Backend")
    
    try:
        response = requests.get(f"{BACKEND_URL}/")
        if response.status_code == 200:
            print_success("Backend is running")
            print_info(f"Response: {response.json()}")
            return True
        else:
            print_error(f"Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Cannot connect to backend: {e}")
        print_info("Make sure to start the backend with: uvicorn backend.main:app --reload")
        return False

def verify_vector_db():
    """Check if vector database exists and is accessible"""
    print_header("Step 2: Verify Vector Database")
    
    db_path = Path(__file__).parent / "chroma_db" / "quiz_collection"
    
    if db_path.exists():
        print_success(f"Vector database directory exists: {db_path}")
        
        # Try to connect to ChromaDB
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(db_path))
            collection = client.get_or_create_collection("quiz_documents")
            count = collection.count()
            print_success(f"ChromaDB connected successfully")
            print_info(f"Current document count: {count}")
            return True
        except Exception as e:
            print_error(f"Cannot connect to ChromaDB: {e}")
            return False
    else:
        print_info(f"Vector database directory will be created on first upload: {db_path}")
        return True

def test_upload(file_path=None):
    """Test document upload and embedding generation"""
    print_header("Step 3: Test Document Upload")
    
    # Use provided file or create a test file
    if file_path and os.path.exists(file_path):
        test_file = file_path
        print_info(f"Using file: {test_file}")
    else:
        # Create a test text file
        test_file = "test_document.txt"
        with open(test_file, "w") as f:
            f.write("""
            Linear Regression
            
            Linear regression is a statistical method used to model the relationship between 
            a dependent variable and one or more independent variables. The goal is to find 
            the best-fitting line through the data points.
            
            The formula for simple linear regression is:
            y = mx + b
            
            Where:
            - y is the dependent variable
            - x is the independent variable
            - m is the slope
            - b is the y-intercept
            
            Linear regression assumes a linear relationship between variables and uses the 
            method of least squares to minimize the sum of squared residuals.
            """)
        print_info(f"Created test file: {test_file}")
    
    try:
        # Upload file
        with open(test_file, "rb") as f:
            files = {"file": (os.path.basename(test_file), f)}
            response = requests.post(f"{BACKEND_URL}/quiz/upload", files=files)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print_success("Document uploaded successfully")
                print_info(f"Session ID: {result['session_id']}")
                print_info(f"Filename: {result['filename']}")
                print_info(f"Chunks created: {result['num_chunks']}")
                print_info(f"Embeddings stored: {result.get('embeddings_stored', False)}")
                return result['session_id']
            else:
                print_error(f"Upload failed: {result}")
                return None
        else:
            print_error(f"Upload failed with status {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Upload error: {e}")
        return None
    finally:
        # Clean up test file if we created it
        if not file_path and os.path.exists("test_document.txt"):
            os.remove("test_document.txt")

def test_retrieval(session_id):
    """Test hybrid retrieval"""
    print_header("Step 4: Test Hybrid Retrieval")
    
    print_info("Testing retrieval by generating a quiz...")
    
    try:
        payload = {
            "session_id": session_id,
            "topic": "linear regression",
            "num_questions": 3,
            "difficulty": "mixed",
            "use_expansion": False
        }
        
        response = requests.post(
            f"{BACKEND_URL}/quiz/generate",
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print_success("Quiz generated successfully")
                print_info(f"Questions generated: {result['num_questions']}")
                print_info(f"Chunks used: {result['num_chunks_used']}")
                print_info(f"Output files: {result.get('json_filename', 'N/A')}")
                
                # Display first question
                if result.get("questions"):
                    print_info("\nSample Question:")
                    q = result["questions"][0]
                    print(f"   Q: {q['question']}")
                    for key in ['A', 'B', 'C', 'D']:
                        print(f"   {key}. {q['options'][key]}")
                    print(f"   Correct: {q['correct_answer']}")
                
                return True
            else:
                print_error(f"Generation failed: {result}")
                return False
        else:
            print_error(f"Generation failed with status {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Retrieval error: {e}")
        return False

def test_hybrid_scoring():
    """Verify hybrid scoring formula"""
    print_header("Step 5: Verify Hybrid Scoring")
    
    print_info("Checking configuration...")
    
    try:
        from backend import config
        
        cosine_weight = getattr(config, 'QUIZ_COSINE_WEIGHT', None)
        bm25_weight = getattr(config, 'QUIZ_BM25_WEIGHT', None)
        
        if cosine_weight is not None and bm25_weight is not None:
            if abs(cosine_weight - 0.7) < 0.001 and abs(bm25_weight - 0.3) < 0.001:
                print_success("Hybrid scoring formula: 0.7 × Cosine + 0.3 × BM25 ✓")
                return True
            else:
                print_error(f"Incorrect weights: Cosine={cosine_weight}, BM25={bm25_weight}")
                return False
        else:
            print_error("Weights not found in config")
            return False
    except Exception as e:
        print_error(f"Config check error: {e}")
        return False

def verify_config():
    """Verify all config settings"""
    print_header("Step 6: Verify Configuration")
    
    try:
        from backend import config
        
        settings = {
            "QUIZ_CHUNK_SIZE": getattr(config, 'QUIZ_CHUNK_SIZE', None),
            "QUIZ_CHUNK_OVERLAP": getattr(config, 'QUIZ_CHUNK_OVERLAP', None),
            "QUIZ_EMBEDDING_MODEL": getattr(config, 'QUIZ_EMBEDDING_MODEL', None),
            "QUIZ_COSINE_WEIGHT": getattr(config, 'QUIZ_COSINE_WEIGHT', None),
            "QUIZ_BM25_WEIGHT": getattr(config, 'QUIZ_BM25_WEIGHT', None),
            "QUIZ_RETRIEVAL_THRESHOLD": getattr(config, 'QUIZ_RETRIEVAL_THRESHOLD', None),
            "QUIZ_LLM_MODEL": getattr(config, 'QUIZ_LLM_MODEL', None),
        }
        
        all_present = True
        for key, value in settings.items():
            if value is not None:
                print_success(f"{key} = {value}")
            else:
                print_error(f"{key} is not set")
                all_present = False
        
        return all_present
    except Exception as e:
        print_error(f"Config verification error: {e}")
        return False

def main():
    """Run all verification tests"""
    print("\n" + "🔍 Quiz Generator RAG Pipeline Verification".center(70))
    print("This script will verify the complete RAG implementation\n")
    
    # Track results
    results = []
    
    # Test 1: Backend
    results.append(("Backend Running", verify_backend()))
    
    if not results[-1][1]:
        print("\n⚠️  Backend is not running. Start it and try again.")
        return
    
    # Test 2: Vector DB
    results.append(("Vector Database", verify_vector_db()))
    
    # Test 3: Config
    results.append(("Configuration", verify_config()))
    
    # Test 4: Hybrid Scoring
    results.append(("Hybrid Scoring", test_hybrid_scoring()))
    
    # Test 5: Upload
    session_id = test_upload(TEST_DOCUMENT_PATH)
    results.append(("Document Upload", session_id is not None))
    
    # Test 6: Retrieval
    if session_id:
        results.append(("Hybrid Retrieval", test_retrieval(session_id)))
    
    # Summary
    print_header("Verification Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<50} {status}")
    
    print(f"\n{'='*70}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*70}\n")
    
    if passed == total:
        print("🎉 All tests passed! The RAG pipeline is working correctly.")
        print("\n📚 Documentation:")
        print("   - QUIZ_RAG_PIPELINE.md - Full pipeline documentation")
        print("   - QUIZ_UPDATE_SUMMARY.md - Implementation summary")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print("\n")

if __name__ == "__main__":
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
