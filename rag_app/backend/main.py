from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import shutil
import logging
from pathlib import Path
from backend.speech_to_text import SpeechToText
from backend.sentiment_analyzer import SentimentAnalyzer
from backend import config
from backend.rag_pipeline import RAGPipeline
from backend.quiz_document_processor import QuizDocumentProcessor
from backend.quiz_hybrid_retriever import QuizHybridRetriever
from backend.quiz_semantic_query_expander import QuizSemanticQueryExpander
from backend.quiz_question_generator import QuizQuestionGenerator
from backend.ocr_utils import OCRProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Application API", version="1.0.0")

# ✅ FIX: Add port 3001 to allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",   # ✅ ADD THIS
        "http://127.0.0.1:3001"    # ✅ ADD THIS
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

stt = SpeechToText(api_key=config.GROQ_API_KEY)

try:
    sentiment = SentimentAnalyzer(model_path=config.SENTIMENT_MODEL_DIR)
    logger.info("✅ Custom sentiment model loaded")
except Exception as e:
    logger.warning(f"⚠️ Using default sentiment model: {e}")
    sentiment = SentimentAnalyzer()

# Initialize OCR processor
try:
    ocr_processor = OCRProcessor()
    logger.info("✅ OCR processor initialized")
except Exception as e:
    logger.warning(f"⚠️ OCR processor initialization failed: {e}")
    ocr_processor = None

rag = RAGPipeline()

UPLOAD_DIR = config.UPLOAD_DIR if hasattr(config, "UPLOAD_DIR") else "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Quiz Generator Instances
QUIZ_UPLOAD_DIR = config.QUIZ_UPLOAD_DIR if hasattr(config, "QUIZ_UPLOAD_DIR") else "quiz_uploads"
QUIZ_OUTPUT_DIR = config.QUIZ_OUTPUT_DIR if hasattr(config, "QUIZ_OUTPUT_DIR") else "quiz_outputs"
QUIZ_DB_DIR = os.path.join(config.CHROMA_DB_DIR if hasattr(config, "CHROMA_DB_DIR") else "chroma_db", "quiz_collection")
os.makedirs(QUIZ_UPLOAD_DIR, exist_ok=True)
os.makedirs(QUIZ_OUTPUT_DIR, exist_ok=True)
os.makedirs(QUIZ_DB_DIR, exist_ok=True)

# Initialize quiz components with vector database support
quiz_processor = QuizDocumentProcessor(
    chunk_size=config.QUIZ_CHUNK_SIZE if hasattr(config, "QUIZ_CHUNK_SIZE") else 500,
    chunk_overlap=config.QUIZ_CHUNK_OVERLAP if hasattr(config, "QUIZ_CHUNK_OVERLAP") else 100,
    embedding_model=config.QUIZ_EMBEDDING_MODEL if hasattr(config, "QUIZ_EMBEDDING_MODEL") else "all-MiniLM-L6-v2"
)
quiz_retriever = QuizHybridRetriever(
    model_name=config.QUIZ_EMBEDDING_MODEL if hasattr(config, "QUIZ_EMBEDDING_MODEL") else "all-MiniLM-L6-v2",
    cosine_weight=config.QUIZ_COSINE_WEIGHT if hasattr(config, "QUIZ_COSINE_WEIGHT") else 0.7,
    bm25_weight=config.QUIZ_BM25_WEIGHT if hasattr(config, "QUIZ_BM25_WEIGHT") else 0.3,
    threshold=config.QUIZ_RETRIEVAL_THRESHOLD if hasattr(config, "QUIZ_RETRIEVAL_THRESHOLD") else 0.45,
    persist_directory=QUIZ_DB_DIR
)

# Store quiz session data (in production, use Redis or a database)
quiz_sessions = {}

@app.get("/")
async def root():
    return {
        "status": "running",
        "message": "RAG API is active",
        "version": "1.0.0"
    }

@app.post("/query")
async def query(request: Request):
    try:
        data = await request.json()
        query_text = data.get("query", "")
        if not query_text:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Query is required"}
            )
        logger.info(f"📝 Query: {query_text}")
        result = rag.query(query_text)
        return JSONResponse(content={
            "status": result.get("status", "error"),
            "answer": result.get("answer", ""),
            "sources": result.get("sources", [])
        })
    except Exception as e:
        logger.error(f"❌ Query error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload and process files (PDFs, images, or text files).
    Images and scanned PDFs are processed using OCR.
    """
    try:
        uploaded_files = []
        total_chunks = 0
        
        for file in files:
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            
            # Save uploaded file
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
            
            logger.info(f"📁 Processing: {file.filename}")
            
            # Detect file type
            file_ext = Path(file.filename).suffix.lower()
            
            # Supported image formats for OCR
            image_formats = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']
            
            # Check if OCR should be used
            use_ocr = file_ext in image_formats or file_ext == '.pdf'
            
            # Process based on file type
            if use_ocr and ocr_processor is not None:
                try:
                    # Extract text using OCR
                    logger.info(f"🔍 Running OCR on {file.filename}")
                    extracted_text = ocr_processor.extract_text(file_path, preprocess=True)
                    
                    if extracted_text and extracted_text.strip():
                        # Create a temporary text file with extracted content
                        temp_text_file = file_path.replace(file_ext, '_ocr.txt')
                        with open(temp_text_file, 'w', encoding='utf-8') as f:
                            f.write(extracted_text)
                        
                        # Add the extracted text to RAG pipeline
                        chunks = rag.add_text(file.filename, extracted_text)
                        total_chunks += len(chunks)
                        uploaded_files.append(file.filename)
                        
                        logger.info(f"✅ OCR completed: {len(chunks)} chunks from {file.filename}")
                    else:
                        logger.warning(f"⚠️ No text extracted from {file.filename}")
                        
                except Exception as ocr_error:
                    logger.warning(f"⚠️ OCR failed for {file.filename}: {ocr_error}")
                    logger.info(f"↩️ Attempting standard processing for {file.filename}")
                    
                    # Fallback to standard processing if OCR fails
                    if file_ext == '.pdf':
                        chunks = rag.add_document(file_path)
                        total_chunks += len(chunks)
                        uploaded_files.append(file.filename)
                    else:
                        logger.error(f"❌ Cannot process {file.filename} without OCR")
            else:
                # Standard processing for text files and PDFs (without OCR)
                chunks = rag.add_document(file_path)
                total_chunks += len(chunks)
                uploaded_files.append(file.filename)
        
        return JSONResponse(content={
            "status": "success",
            "processed_files": len(uploaded_files),
            "total_chunks": total_chunks
        })
        
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.post("/upload-text")
async def upload_text(request: Request):
    try:
        data = await request.json()
        text_name = data.get("name", "")
        text_content = data.get("text", "")
        if not text_name or not text_content:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Name and text required"}
            )
        logger.info(f"📝 Processing text: {text_name}")
        chunks = rag.add_text(text_name, text_content)
        return JSONResponse(content={
            "status": "success",
            "total_chunks": len(chunks)
        })
    except Exception as e:
        logger.error(f"❌ Upload text error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.post("/analyze-sentiment")
async def analyze_sentiment(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "")
        if not text:
            return JSONResponse(content={
                "success": False,
                "error": "Text is required"
            })
        logger.info(f"😊 Analyzing sentiment for text: {text[:50]}...")
        result = sentiment.analyze_sentiment(text)
        if not result.get("success", True):
            return JSONResponse(content=result)
        return JSONResponse(content={
            "success": True,
            "sentiment": result["sentiment"],
            "confidence": result["confidence"]
        })
    except Exception as e:
        logger.error(f"❌ Sentiment error: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        })

@app.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    try:
        temp_path = os.path.join(UPLOAD_DIR, f"temp_{audio.filename}")
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        logger.info(f"🎤 Transcribing audio")
        result = stt.transcribe(temp_path)
        os.remove(temp_path)
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "text": result["text"]
            })
        else:
            return JSONResponse(content={
                "success": False,
                "error": result.get("error", "Transcription failed")
            })
    except Exception as e:
        logger.error(f"❌ Speech-to-text error: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        })

@app.get("/sources")
async def get_sources():
    try:
        sources = rag.get_sources()
        return JSONResponse(content={"sources": sources})
    except Exception as e:
        logger.error(f"❌ Get sources error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/delete-source")
async def delete_source(request: Request):
    try:
        data = await request.json()
        source_name = data.get("source", "")
        if not source_name:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Source name required"}
            )
        deleted_count = rag.delete_source(source_name)
        return JSONResponse(content={
            "status": "success",
            "deleted_count": deleted_count
        })
    except Exception as e:
        logger.error(f"❌ Delete source error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.post("/clear")
async def clear_database():
    try:
        rag.clear_database()
        return JSONResponse(content={
            "status": "success",
            "message": "Database cleared"
        })
    except Exception as e:
        logger.error(f"❌ Clear database error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.get("/stats")
async def get_stats():
    try:
        stats = rag.get_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"❌ Get stats error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ============= QUIZ GENERATOR ENDPOINTS =============

@app.post("/quiz/upload")
async def quiz_upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document for quiz generation.
    Supports: PDFs (text or scanned), Images (PNG, JPG, etc.), Text files (TXT, MD)
    
    Full RAG Pipeline:
    1. Text Extraction (with OCR for images and scanned PDFs)
    2. Chunking
    3. Tokenization (in embedding model)
    4. Embedding Generation
    5. Store in Vector Database
    """
    try:
        # Validate file type - now includes images for OCR
        allowed_extensions = ['.pdf', '.txt', '.md', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"}
            )
        
        # Save uploaded file
        session_id = f"quiz_{os.urandom(8).hex()}"
        file_path = os.path.join(QUIZ_UPLOAD_DIR, f"{session_id}_{file.filename}")
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"📄 Quiz file uploaded: {file.filename}")
        
        # Detect if OCR is needed for images or PDFs
        image_formats = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']
        use_ocr = file_ext in image_formats or file_ext == '.pdf'
        
        # Step 1-2: Process document (text extraction + chunking)
        logger.info("Step 1-2: Text extraction and chunking...")
        
        # Try OCR extraction for images and PDFs if OCR processor is available
        if use_ocr and ocr_processor is not None:
            try:
                logger.info(f"🔍 Running OCR on {file.filename}")
                
                # Extract text using OCR
                extracted_text = ocr_processor.extract_text(file_path, preprocess=True)
                
                if extracted_text and extracted_text.strip():
                    # Create temporary text file with OCR-extracted content
                    temp_text_file = file_path.replace(file_ext, '_ocr.txt')
                    with open(temp_text_file, 'w', encoding='utf-8') as f:
                        f.write(extracted_text)
                    
                    # Process the OCR text file
                    chunks = quiz_processor.process_file(temp_text_file)
                    logger.info(f"✅ OCR completed: {len(chunks)} chunks extracted from {file.filename}")
                else:
                    logger.warning(f"⚠️ No text extracted from {file.filename} via OCR")
                    # Fallback to standard processing for PDFs
                    if file_ext == '.pdf':
                        chunks = quiz_processor.process_file(file_path)
                    else:
                        return JSONResponse(
                            status_code=400,
                            content={"error": "No text could be extracted from the image. Please try a clearer image."}
                        )
                        
            except Exception as ocr_error:
                logger.warning(f"⚠️ OCR failed for {file.filename}: {ocr_error}")
                
                # Fallback to standard processing for PDFs only
                if file_ext == '.pdf':
                    logger.info(f"↩️ Attempting standard PDF text extraction for {file.filename}")
                    chunks = quiz_processor.process_file(file_path)
                else:
                    return JSONResponse(
                        status_code=500,
                        content={"error": f"OCR processing failed: {str(ocr_error)}. Image files require OCR."}
                    )
        else:
            # Standard processing for text files (TXT, MD) or if OCR not available
            chunks = quiz_processor.process_file(file_path)
        
        # Step 3-4: Generate embeddings (tokenization + embedding generation)
        logger.info("Step 3-4: Tokenization and embedding generation...")
        embeddings = quiz_processor.create_embeddings(chunks)
        
        # Step 5: Store in vector database
        logger.info("Step 5: Storing embeddings in vector database...")
        quiz_retriever.index_chunks(chunks, embeddings, session_id=session_id)
        
        # Store session data
        quiz_sessions[session_id] = {
            'filename': file.filename,
            'file_path': file_path,
            'num_chunks': len(chunks),
            'chunks': chunks,
            'embeddings_stored': True
        }
        
        logger.info(f"✓ RAG Pipeline Complete: {len(chunks)} chunks processed and stored in vector DB")
        
        return JSONResponse(content={
            'success': True,
            'session_id': session_id,
            'filename': file.filename,
            'num_chunks': len(chunks),
            'embeddings_stored': True,
            'message': f'Successfully processed {len(chunks)} chunks from {file.filename} and stored in vector database'
        })
    
    except Exception as e:
        logger.error(f"❌ Quiz upload error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/quiz/generate")
async def quiz_generate(request: Request):
    """Generate quiz questions based on uploaded document."""
    try:
        data = await request.json()
        
        # Get parameters
        session_id = data.get('session_id', '')
        topic = data.get('topic', '').strip()
        num_questions = int(data.get('num_questions', 5))
        difficulty = data.get('difficulty', 'mixed')
        use_expansion = data.get('use_expansion', True)
        num_expansions = int(data.get('num_expansions', 5))
        
        if not session_id or session_id not in quiz_sessions:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid session. Please upload a document first."}
            )
        
        if not topic:
            return JSONResponse(
                status_code=400,
                content={"error": "Topic is required"}
            )
        
        logger.info(f"🎯 Generating quiz: topic='{topic}', questions={num_questions}, difficulty={difficulty}")
        
        # Get GROQ API key from config or environment
        groq_api_key = config.QUIZ_GROQ_API_KEY if hasattr(config, "QUIZ_GROQ_API_KEY") else os.getenv('GROQ_API_KEY')
        if not groq_api_key:
            return JSONResponse(
                status_code=500,
                content={"error": "GROQ_API_KEY not configured"}
            )
        
        # Retrieve relevant chunks using hybrid retrieval (0.7 × Cosine + 0.3 × BM25)
        if use_expansion:
            query_expander = QuizSemanticQueryExpander(api_key=groq_api_key)
            retrieved_chunks = query_expander.retrieve_with_expansion(
                query=topic,
                retriever=quiz_retriever,
                num_expansions=num_expansions,
                chunks_per_query=5,
                session_id=session_id
            )
        else:
            # Direct retrieval from vector database with hybrid scoring
            retrieved_chunks = quiz_retriever.retrieve(topic, top_k=10, session_id=session_id)
        
        if not retrieved_chunks:
            return JSONResponse(
                status_code=400,
                content={"error": "No relevant content found for the topic. Try a different topic."}
            )
        
        logger.info(f"📊 Retrieved {len(retrieved_chunks)} relevant chunks")
        
        # Generate questions with configured model
        quiz_model = config.QUIZ_LLM_MODEL if hasattr(config, "QUIZ_LLM_MODEL") else "meta-llama/llama-4-scout-17b-16e-instruct"
        quiz_gen = QuizQuestionGenerator(api_key=groq_api_key, model=quiz_model)
        questions = quiz_gen.generate_questions(
            context_chunks=retrieved_chunks,
            topic=topic,
            num_questions=num_questions,
            difficulty=difficulty
        )
        
        # Save quiz to files
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"quiz_{topic.replace(' ', '_')}_{timestamp}"
        
        # Save JSON
        json_path = os.path.join(QUIZ_OUTPUT_DIR, f"{base_filename}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'topic': topic,
                'num_questions': len(questions),
                'difficulty': difficulty,
                'questions': questions,
                'metadata': {
                    'source_file': quiz_sessions[session_id]['filename'],
                    'num_chunks_retrieved': len(retrieved_chunks),
                    'use_expansion': use_expansion,
                    'generated_at': timestamp
                }
            }, f, indent=2, ensure_ascii=False)
        
        # Save TXT
        txt_path = os.path.join(QUIZ_OUTPUT_DIR, f"{base_filename}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"QUIZ: {topic}\n")
            f.write(f"Generated: {timestamp}\n")
            f.write(f"{'='*60}\n\n")
            
            for q in questions:
                f.write(f"Question {q['question_number']}: {q['question']}\n")
                for opt_key in ['A', 'B', 'C', 'D']:
                    f.write(f"  {opt_key}. {q['options'][opt_key]}\n")
                f.write(f"\nCorrect Answer: {q['correct_answer']}\n")
                if q.get('explanation'):
                    f.write(f"Explanation: {q['explanation']}\n")
                f.write(f"\n{'-'*60}\n\n")
        
        # Store in session
        quiz_sessions[session_id]['quiz'] = {
            'questions': questions,
            'json_path': json_path,
            'txt_path': txt_path,
            'json_filename': f"{base_filename}.json",
            'txt_filename': f"{base_filename}.txt"
        }
        
        logger.info(f"✓ Generated {len(questions)} questions successfully")
        
        return JSONResponse(content={
            'success': True,
            'questions': questions,
            'num_questions': len(questions),
            'num_chunks_used': len(retrieved_chunks),
            'json_filename': f"{base_filename}.json",
            'txt_filename': f"{base_filename}.txt",
            'metadata': {
                'topic': topic,
                'difficulty': difficulty,
                'use_expansion': use_expansion
            }
        })
    
    except Exception as e:
        logger.error(f"❌ Quiz generation error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/quiz/download/{filename}")
async def quiz_download(filename: str):
    """Download generated quiz file (JSON or TXT)."""
    try:
        file_path = os.path.join(QUIZ_OUTPUT_DIR, filename)
        
        if not os.path.exists(file_path):
            return JSONResponse(
                status_code=404,
                content={"error": "File not found"}
            )
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
    
    except Exception as e:
        logger.error(f"❌ Quiz download error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting RAG API on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)