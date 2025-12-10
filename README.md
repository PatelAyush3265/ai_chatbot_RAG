# ai_chatbot_RAG

# RAG-Based Quiz Generator with Hybrid Retrieval and Semantic Query Expansion

A sophisticated quiz generation system that uses Retrieval-Augmented Generation (RAG) to create high-quality quiz questions from PDF documents. The system implements **Hybrid Retrieval** (combining semantic similarity and keyword-based BM25) and **Semantic Query Expansion** to maximize retrieval quality and generate comprehensive quizzes covering both main topics and related concepts.

## 🌟 Features

- **📄 PDF Processing**: Automatic text extraction and intelligent chunking with overlap
- **🔍 Hybrid Retrieval**: Combines cosine similarity (0.7) and BM25 (0.3) for optimal chunk retrieval
- **🎯 Semantic Query Expansion**: Uses LLM to generate related topics and expand retrieval coverage
- **🤔 Intelligent Quiz Generation**: Creates multiple-choice questions with explanations
- **💾 Multiple Output Formats**: JSON, formatted text with answers, and quiz-only format
- **📊 Detailed Statistics**: Retrieval and generation metrics

## 🏗️ Architecture

### System Components

```
PDF Document
     ↓
[Document Processor] → Text Extraction & Chunking
     ↓
[Hybrid Retriever] → Semantic (Cosine) + Keyword (BM25) Scoring
     ↓
[Semantic Query Expander] → LLM-based Topic Expansion
     ↓
[Quiz Generator] → Question & Answer Generation
     ↓
Quiz Output (JSON + TXT)
```

### How It Works

#### 1. **Hybrid Retrieval**

Combines two scoring methods:
- **Cosine Similarity** (70%): Semantic meaning-based matching
- **BM25** (30%): Keyword frequency-based matching

```
Final Score = 0.7 × Cosine Similarity + 0.3 × BM25
```

**Example:**
For query "linear regression" on three chunks:
- Chunk A: "Linear regression is a statistical method..." → Score: 0.944
- Chunk B: "Multiple linear regression extends..." → Score: 0.551
- Chunk C: "Polynomial regression fits..." → Score: 0.449

#### 2. **Semantic Query Expansion (SQE)**

Expands the user's query to include related concepts:

```
Original Query: "linear regression"
         ↓
Expanded Queries:
  1. linear regression
  2. multiple linear regression
  3. predictor variables
  4. ordinary least squares
  5. cost function
  6. polynomial regression
```

Each expanded query retrieves additional chunks, significantly increasing coverage.

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- Groq API key (free at https://console.groq.com)

### Setup Steps

1. **Clone or download this repository**

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Get a free Groq API key:**
   - Visit https://console.groq.com
   - Sign up for a free account
   - Generate your API key

4. **Set up your Groq API key:**
   
   Create a `.env` file in the project directory:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

   Or set it as an environment variable:
   ```powershell
   $env:GROQ_API_KEY="your_groq_api_key_here"
   ```

## 🚀 Usage

### Basic Usage

```powershell
python main.py path/to/your/document.pdf
```

The system will prompt you for:
- Quiz topic
- Number of questions
- Difficulty level
- Whether to use semantic query expansion

### Example Session

```
Enter path to PDF file: lectures/linear_regression.pdf

QUIZ CONFIGURATION
==================

Enter quiz topic: linear regression
Number of questions (default 10): 10
Difficulty (easy/medium/hard/mixed, default 'mixed'): mixed
Use semantic query expansion? (y/n, default 'y'): y

[System processes document and generates quiz...]

Show answers? (y/n, default 'y'): y
```

### Programmatic Usage

```python
from main import RAGQuizSystem

# Initialize system
rag_system = RAGQuizSystem()

# Load document
rag_system.load_document("path/to/document.pdf")

# Generate quiz
result = rag_system.generate_quiz(
    topic="linear regression",
    num_questions=10,
    difficulty="mixed",
    use_expansion=True,
    num_expansions=5,
    output_file="my_quiz"
)

# Display quiz
rag_system.display_quiz(result, show_answers=True)
```

## 📁 Project Structure

```
QUIZ/
├── main.py                      # Main application orchestrator
├── document_processor.py        # PDF extraction and chunking
├── hybrid_retriever.py          # Hybrid retrieval system
├── semantic_query_expander.py   # Query expansion with LLM
├── quiz_generator.py            # Question generation
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

## 🔧 Configuration

### Document Processing
```python
DocumentProcessor(
    chunk_size=500,      # Characters per chunk
    chunk_overlap=100    # Overlapping characters
)
```

### Hybrid Retriever
```python
HybridRetriever(
    cosine_weight=0.7,   # Weight for semantic similarity
    bm25_weight=0.3,     # Weight for keyword matching
    threshold=0.45       # Minimum score for retrieval
)
```

### Quiz Generator
```python
QuizGenerator(
    model="llama-3.1-8b-instant"  # Groq model to use (fast & free)
)
```

## 📊 Output Files

When you generate a quiz, three files are created:

1. **`quiz_topic_timestamp.json`**: Raw quiz data in JSON format
2. **`quiz_topic_timestamp_with_answers.txt`**: Formatted quiz with answers and explanations
3. **`quiz_topic_timestamp_quiz_only.txt`**: Quiz questions only (for taking the quiz)

### Example Output Structure

```json
[
  {
    "question_number": 1,
    "question": "What is linear regression primarily used for?",
    "options": {
      "A": "Classification of categorical data",
      "B": "Modeling relationships between variables",
      "C": "Clustering similar data points",
      "D": "Dimensionality reduction"
    },
    "correct_answer": "B",
    "explanation": "Linear regression models relationships between variables...",
    "difficulty": "easy",
    "topic_area": "Basic Concepts",
    "source_topic": "linear regression"
  }
]
```

## 🎯 Key Advantages

### Why Hybrid Retrieval?

Traditional vector search (cosine similarity only) fails when:
- Different terminology is used for the same concept
- Important keywords are missing in semantic matches
- Need exact phrase matching for technical terms

Hybrid retrieval solves this by combining both approaches.

### Why Semantic Query Expansion?

When you ask for questions about "linear regression," you probably also want questions about:
- Multiple linear regression
- Regression coefficients
- OLS assumptions
- Cost functions

SQE automatically discovers and retrieves these related concepts.

## 🔍 Example: How It Works

**User Query:** "linear regression"

**Step 1: Query Expansion**
```
Expanded queries generated:
1. linear regression
2. multiple linear regression
3. predictor variables
4. ordinary least squares
5. cost function
6. polynomial regression
```

**Step 2: Hybrid Retrieval**

For each query, compute:
- Semantic similarity (embeddings)
- Keyword matching (BM25)
- Combined score

**Step 3: Merge & Deduplicate**
- Combine results from all queries
- Remove duplicate chunks
- Rank by hybrid score

**Step 4: Generate Questions**
- Send top chunks to LLM
- Generate diverse questions
- Include explanations

## 🛠️ Troubleshooting

### "Groq API key not found"
Create a `.env` file with your API key or set the `GROQ_API_KEY` environment variable. Get a free key at https://console.groq.com

### "PDF file not found"
Use the full absolute path to your PDF file, or ensure the file exists in the specified location.

### Low-quality questions
- Try increasing the number of chunks retrieved
- Adjust the threshold parameter in `HybridRetriever`
- Use query expansion to get more diverse content

### Questions don't cover related topics
- Ensure `use_expansion=True`
- Increase `num_expansions` parameter
- Check that your PDF contains related content

## 📝 Dependencies

- `sentence-transformers`: For creating text embeddings
- `rank-bm25`: For BM25 keyword scoring
- `PyPDF2`: For PDF text extraction
- `groq`: For LLM-based generation (Llama 3.1 8B Instant)
- `numpy`: For numerical operations
- `scikit-learn`: For cosine similarity
- `python-dotenv`: For environment variables

## 🤝 Contributing

Feel free to enhance this system by:
- Adding support for other document formats (DOCX, TXT, HTML)
- Implementing different question types (true/false, fill-in-the-blank)
- Adding difficulty estimation for questions
- Creating a web interface
- Supporting multiple languages

## 📄 License

This project is provided as-is for educational and research purposes.

## 🙏 Acknowledgments

This implementation demonstrates concepts from:
- Retrieval-Augmented Generation (RAG)
- Information Retrieval (BM25 algorithm)
- Neural Semantic Search (sentence transformers)
- Large Language Models for question generation

---

**Built with ❤️ for better learning through automated quiz generation**
>>>>>>> 1cb5ea7 (Initial import: RAG quiz generator web app)


