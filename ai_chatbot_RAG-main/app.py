"""
Flask Web Application for RAG-Based Quiz Generator
Provides a web interface for uploading PDFs and generating quizzes.
"""

from flask import Flask, render_template, request, jsonify, send_file, session, make_response
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
import secrets

from document_processor import DocumentProcessor
from hybrid_retriever import HybridRetriever
from semantic_query_expander import SemanticQueryExpander
from quiz_generator import QuizGenerator

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.after_request
def add_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

# Global instances
doc_processor = DocumentProcessor()
retriever = HybridRetriever()
query_expander = SemanticQueryExpander()
quiz_gen = QuizGenerator()

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_pdf():
    """Handle PDF upload and processing."""
    try:
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['pdf_file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process PDF
        chunks = doc_processor.process_pdf(filepath)
        
        # Index chunks
        retriever.index_chunks(chunks)
        
        # Store info in session
        session['pdf_filename'] = filename
        session['pdf_path'] = filepath
        session['num_chunks'] = len(chunks)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'num_chunks': len(chunks),
            'message': f'Successfully processed {len(chunks)} chunks from {filename}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate', methods=['POST'])
def generate_quiz():
    """Generate quiz based on topic."""
    try:
        data = request.json
        
        # Get parameters
        topic = data.get('topic', '').strip()
        num_questions = int(data.get('num_questions', 5))
        difficulty = data.get('difficulty', 'mixed')
        use_expansion = data.get('use_expansion', True)
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        if 'pdf_path' not in session:
            return jsonify({'error': 'Please upload a PDF first'}), 400
        
        # Validate parameters
        if num_questions < 1 or num_questions > 20:
            return jsonify({'error': 'Number of questions must be between 1 and 20'}), 400
        
        # Retrieve relevant chunks
        if use_expansion:
            expanded_queries = query_expander.expand_query(topic)
            all_chunks = []
            for query in expanded_queries:
                chunks = retriever.retrieve(query, top_k=10)
                all_chunks.extend(chunks)
            
            # Remove duplicates based on text
            seen = set()
            unique_chunks = []
            for chunk in all_chunks:
                text = chunk.get('text', '')
                if text not in seen:
                    seen.add(text)
                    unique_chunks.append(chunk)
            
            chunks = unique_chunks[:15]  # Take top 15 unique chunks
        else:
            chunks = retriever.retrieve(topic, top_k=10)
        
        if not chunks:
            return jsonify({'error': 'No relevant content found for this topic'}), 404
        
        # Generate questions
        questions = quiz_gen.generate_questions(
            chunks,
            topic=topic,
            num_questions=num_questions,
            difficulty=difficulty
        )
        
        # Store quiz in session
        quiz_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        session['current_quiz'] = {
            'id': quiz_id,
            'topic': topic,
            'questions': questions,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'quiz_id': quiz_id,
            'questions': questions,
            'num_chunks': len(chunks)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download/<format>')
def download_quiz(format):
    """Download quiz in specified format."""
    try:
        if 'current_quiz' not in session:
            return jsonify({'error': 'No quiz available'}), 404
        
        quiz = session['current_quiz']
        topic = quiz['topic'].replace(' ', '_')
        quiz_id = quiz['id']
        
        if format == 'json':
            # Save as JSON
            filename = f"quiz_{topic}_{quiz_id}.json"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(quiz['questions'], f, indent=2, ensure_ascii=False)
            
            return send_file(filepath, as_attachment=True, download_name=filename)
        
        elif format == 'txt_with_answers':
            # Save as text with answers
            filename = f"quiz_{topic}_{quiz_id}_with_answers.txt"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            content = quiz_gen.format_quiz(quiz['questions'], show_answers=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return send_file(filepath, as_attachment=True, download_name=filename)
        
        elif format == 'txt_quiz_only':
            # Save as text without answers
            filename = f"quiz_{topic}_{quiz_id}_quiz_only.txt"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            content = quiz_gen.format_quiz(quiz['questions'], show_answers=False)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return send_file(filepath, as_attachment=True, download_name=filename)
        
        else:
            return jsonify({'error': 'Invalid format'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/status')
def status():
    """Get current system status."""
    return jsonify({
        'pdf_uploaded': 'pdf_filename' in session,
        'pdf_filename': session.get('pdf_filename', None),
        'num_chunks': session.get('num_chunks', 0),
        'quiz_available': 'current_quiz' in session
    })


if __name__ == '__main__':
    print("\n" + "="*80)
    print(" RAG-BASED QUIZ GENERATOR - WEB INTERFACE")
    print("="*80)
    print("\n🌐 Starting Flask server...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("⏹️  Press CTRL+C to stop the server\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
