# Quiz Generator Integration - Setup Guide

## 🎯 Overview

The Quiz Generator feature has been fully integrated into your RAG chatbot application. It allows users to:
- Upload PDF, TXT, or MD documents
- Generate intelligent quiz questions using RAG + LLM
- Use semantic query expansion for better topic coverage
- Download quizzes in JSON and TXT formats

## 📦 Installation

### Backend Setup

1. **Install Required Dependencies**
   ```powershell
   cd d:\gw\env\rag_app
   pip install PyPDF2==3.0.1 sentence-transformers==2.2.2 rank-bm25==0.2.2 scikit-learn==1.3.0
   ```

2. **Configure Environment Variables**
   
   Create or update `.env` file in `d:\gw\env\rag_app\`:
   ```env
   # Main RAG API Key
   GROQ_API_KEY=your_groq_api_key_here
   
   # Quiz Generator API Key
   QUIZ_GROQ_API_KEY=your_quiz_groq_api_key_here
   ```

3. **Start Backend Server**
   ```powershell
   cd d:\gw\env\rag_app
   uvicorn backend.main:app --reload --port 8000
   ```

### Frontend Setup

1. **Install Dependencies** (if needed)
   ```powershell
   cd d:\gw\env\ai-chat-react
   npm install
   ```

2. **Start React App**
   ```powershell
   npm start
   ```

## 🚀 Usage

### Accessing Quiz Generator

1. Open your application at `http://localhost:3000`
2. Click the **hamburger menu** (☰) in the top-left corner
3. Select **"Quiz Generator"** from the menu

### Generating a Quiz

**Step 1: Upload Document**
- Click "Choose File" or drag & drop a PDF, TXT, or MD file
- Click "Upload & Process"
- Wait for document processing (chunking + embedding)

**Step 2: Configure Quiz**
- **Topic**: Enter the main subject (e.g., "linear regression", "machine learning")
- **Number of Questions**: Adjust slider (1-20 questions)
- **Difficulty**: Choose Easy, Medium, Hard, or Mixed
- **Semantic Query Expansion**: Toggle ON to cover related concepts (recommended)

**Step 3: Generate & Download**
- Click "Generate Quiz"
- Wait for AI processing (may take 10-30 seconds)
- Review generated questions in the preview
- Download as JSON or TXT format

## 🏗️ Architecture

### Backend Components

#### Quiz Modules (in `d:\gw\env\rag_app\backend\`)

1. **`quiz_document_processor.py`**
   - Extracts text from PDF, TXT, MD files
   - Splits text into overlapping chunks (500 chars, 100 overlap)
   - Cleans and normalizes text

2. **`quiz_hybrid_retriever.py`**
   - Combines Cosine Similarity (70%) + BM25 (30%)
   - Creates sentence embeddings using `all-MiniLM-L6-v2`
   - Retrieves most relevant chunks for quiz generation

3. **`quiz_semantic_query_expander.py`**
   - Uses LLM to expand user's topic into related concepts
   - Improves retrieval coverage
   - Example: "linear regression" → ["multiple linear regression", "predictor variables", "OLS", etc.]

4. **`quiz_question_generator.py`**
   - Generates MCQ questions using `meta-llama/llama-4-scout-17b-16e-instruct`
   - Validates and formats questions
   - Shuffles answer options to avoid bias
   - Provides explanations for correct answers

#### API Endpoints

- **POST `/quiz/upload`** - Upload and process document
- **POST `/quiz/generate`** - Generate quiz questions
- **GET `/quiz/download/{filename}`** - Download quiz file

### Frontend Components

#### React Components

1. **`QuizGeneratorModal.jsx`**
   - Modern UI with dark mode styling
   - Three-step wizard interface
   - Real-time progress indicators
   - Quiz preview with correct answer highlighting

2. **Updated Files**
   - `App.jsx` - Added quiz modal state management
   - `Header.jsx` - Added "Quiz Generator" menu option
   - `services/api.js` - Added quiz API endpoints

## ⚙️ Configuration

### Backend Config (`backend/config.py`)

```python
# Quiz Generator Settings
QUIZ_GROQ_API_KEY = "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"
QUIZ_LLM_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
QUIZ_CHUNK_SIZE = 500
QUIZ_CHUNK_OVERLAP = 100
QUIZ_COSINE_WEIGHT = 0.7
QUIZ_BM25_WEIGHT = 0.3
QUIZ_RETRIEVAL_THRESHOLD = 0.45
```

### Directories Created

- `quiz_uploads/` - Temporary storage for uploaded documents
- `quiz_outputs/` - Generated quiz files (JSON + TXT)

## 🎨 UI Features

### Design System
- **Dark Mode**: Consistent with app theme
- **Light Blue Accents**: `#4da6ff` (neon-green in config)
- **Rounded Cards**: Modern, clean interface
- **Loading Animations**: Spinner overlays during processing
- **Responsive**: Works on all screen sizes

### User Experience
- ✅ Step-by-step wizard interface
- ✅ Real-time validation
- ✅ Clear error messages
- ✅ Quiz preview with highlighted correct answers
- ✅ One-click download (JSON/TXT)
- ✅ Session persistence during workflow

## 📊 Technical Details

### Hybrid Retrieval Algorithm

```
Final Score = 0.7 × Cosine Similarity + 0.3 × BM25
```

**Why Hybrid?**
- Cosine captures semantic meaning
- BM25 captures keyword relevance
- Combined approach yields better results

### Semantic Query Expansion

Original query → LLM generates 5 related topics → Retrieve chunks for each → Deduplicate → Generate quiz

**Example:**
```
User Query: "machine learning"
↓
Expanded: ["machine learning", "supervised learning", "neural networks", 
           "training algorithms", "model evaluation"]
↓
Retrieve 5 chunks per query (25 total)
↓
Deduplicate by score → Top 10 chunks
↓
Generate 10 MCQ questions
```

## 🐛 Troubleshooting

### Common Issues

**1. "GROQ_API_KEY not configured"**
- Check `.env` file exists in `rag_app/` folder
- Verify `QUIZ_GROQ_API_KEY` is set correctly
- Restart backend server after updating `.env`

**2. "No relevant content found for the topic"**
- Try a broader topic name
- Enable "Semantic Query Expansion"
- Check if document was processed correctly

**3. "Upload failed" / "File not supported"**
- Ensure file is PDF, TXT, or MD format
- Check file isn't corrupted
- Verify file size < 16MB

**4. Backend import errors**
- Install missing packages:
  ```powershell
  pip install PyPDF2 sentence-transformers rank-bm25 scikit-learn
  ```

**5. Quiz generation takes too long**
- Reduce number of questions
- Disable semantic expansion for faster generation
- Check Groq API status at https://console.groq.com

## 📝 API Examples

### Upload Document
```javascript
const formData = new FormData();
formData.append('file', selectedFile);

const response = await fetch('http://localhost:8000/quiz/upload', {
  method: 'POST',
  body: formData
});

const data = await response.json();
// Returns: { session_id, filename, num_chunks }
```

### Generate Quiz
```javascript
const response = await fetch('http://localhost:8000/quiz/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: 'quiz_abc123',
    topic: 'linear regression',
    num_questions: 10,
    difficulty: 'mixed',
    use_expansion: true,
    num_expansions: 5
  })
});

const data = await response.json();
// Returns: { questions[], json_filename, txt_filename }
```

## 🔒 Security Notes

- Quiz sessions are stored in memory (not persistent across restarts)
- For production, use Redis or database for session storage
- API keys should be kept in `.env` and never committed to git
- Add `.env` to `.gitignore`

## 📚 Resources

- **Groq Console**: https://console.groq.com
- **Sentence Transformers**: https://www.sbert.net/
- **BM25 Algorithm**: https://en.wikipedia.org/wiki/Okapi_BM25
- **Original Quiz Generator**: `d:\gw\env\ai_chatbot_RAG-main\README.md`

## ✅ Integration Checklist

- [x] Backend quiz modules created
- [x] FastAPI endpoints implemented
- [x] React quiz modal component created
- [x] App.jsx updated with modal state
- [x] Header.jsx updated with menu option
- [x] Config updated with quiz settings
- [x] API endpoints configured
- [x] Dependencies added to requirements.txt
- [x] .env.example created
- [ ] Install backend dependencies
- [ ] Test file upload
- [ ] Test quiz generation
- [ ] Test file downloads

## 🎉 Next Steps

1. Install the new dependencies
2. Restart your backend server
3. Open the app and test the quiz generator
4. Generate your first quiz!

---

**Integration Complete!** The quiz generator is now fully integrated into your RAG chatbot application with a modern, beautiful UI that matches your existing design system.
