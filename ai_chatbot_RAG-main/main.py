"""
RAG-Based Quiz Generator - Main Application
Orchestrates the entire pipeline: PDF processing, hybrid retrieval, 
semantic query expansion, and quiz generation.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

from document_processor import DocumentProcessor
from hybrid_retriever import HybridRetriever
from semantic_query_expander import SemanticQueryExpander
from quiz_generator import QuizGenerator


class RAGQuizSystem:
    """Complete RAG-based quiz generation system."""
    
    def __init__(self):
        """Initialize all components of the RAG system."""
        print("Initializing RAG Quiz System...")
        print("="*80)
        
        # Initialize components
        self.doc_processor = DocumentProcessor(chunk_size=500, chunk_overlap=100)
        self.retriever = HybridRetriever(
            cosine_weight=0.7,
            bm25_weight=0.3,
            threshold=0.45
        )
        self.query_expander = SemanticQueryExpander()
        self.quiz_generator = QuizGenerator()
        
        # State
        self.chunks = None
        self.pdf_path = None
        
        print("✓ System initialized successfully!")
        print("="*80)
    
    def load_document(self, pdf_path: str):
        """
        Load and process a PDF document.
        
        Args:
            pdf_path: Path to PDF file
        """
        print(f"\n📄 Loading document: {pdf_path}")
        print("-"*80)
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.pdf_path = pdf_path
        
        # Extract and chunk text
        self.chunks = self.doc_processor.process_pdf(pdf_path)
        
        # Index chunks for retrieval
        self.retriever.index_chunks(self.chunks)
        
        print(f"\n✓ Document loaded and indexed successfully!")
        print(f"  Total chunks: {len(self.chunks)}")
        print(f"  Ready for question generation!")
    
    def generate_quiz(self, 
                     topic: str,
                     num_questions: int = 10,
                     difficulty: str = "mixed",
                     use_expansion: bool = True,
                     num_expansions: int = 5,
                     output_file: str = None) -> dict:
        """
        Generate a quiz on the specified topic.
        
        Args:
            topic: Main topic/query for the quiz
            num_questions: Number of questions to generate
            difficulty: Question difficulty ("easy", "medium", "hard", "mixed")
            use_expansion: Whether to use semantic query expansion
            num_expansions: Number of query expansions to generate
            output_file: Optional filename to save quiz (JSON and TXT)
            
        Returns:
            Dictionary with quiz questions and metadata
        """
        if self.chunks is None:
            raise ValueError("No document loaded. Call load_document() first.")
        
        print(f"\n🎯 Generating quiz on topic: '{topic}'")
        print("="*80)
        
        # Step 1: Retrieve relevant chunks
        if use_expansion:
            print(f"\n📊 Using Semantic Query Expansion (SQE)...")
            retrieved_chunks = self.query_expander.retrieve_with_expansion(
                query=topic,
                retriever=self.retriever,
                num_expansions=num_expansions,
                top_k_per_query=5
            )
        else:
            print(f"\n📊 Using standard hybrid retrieval...")
            retrieved_chunks = self.retriever.retrieve(topic, top_k=10)
        
        # Print retrieval stats
        print(f"\n📈 Retrieval Results:")
        print(f"  Chunks retrieved: {len(retrieved_chunks)}")
        if retrieved_chunks:
            print(f"  Top score: {retrieved_chunks[0]['hybrid_score']:.3f}")
            print(f"  Avg score: {sum(r['hybrid_score'] for r in retrieved_chunks) / len(retrieved_chunks):.3f}")
        
        # Step 2: Generate quiz questions
        print(f"\n🤔 Generating {num_questions} questions...")
        print("-"*80)
        
        questions = self.quiz_generator.generate_questions(
            context_chunks=retrieved_chunks,
            topic=topic,
            num_questions=num_questions,
            difficulty=difficulty
        )
        
        # Step 3: Save output if requested
        if output_file:
            self._save_quiz_output(questions, output_file, topic)
        
        # Prepare result
        result = {
            'topic': topic,
            'num_questions': len(questions),
            'difficulty': difficulty,
            'questions': questions,
            'retrieval_stats': {
                'chunks_retrieved': len(retrieved_chunks),
                'used_expansion': use_expansion,
                'num_expansions': num_expansions if use_expansion else 0
            },
            'source_document': os.path.basename(self.pdf_path) if self.pdf_path else None
        }
        
        print(f"\n✅ Quiz generation complete!")
        print("="*80)
        
        return result
    
    def _save_quiz_output(self, questions: list, output_file: str, topic: str):
        """
        Save quiz to files (JSON and formatted TXT).
        
        Args:
            questions: List of questions
            output_file: Base filename (without extension)
            topic: Quiz topic
        """
        # Remove extension if provided
        base_name = os.path.splitext(output_file)[0]
        
        # Save JSON
        json_file = f"{base_name}.json"
        self.quiz_generator.save_quiz(questions, json_file)
        
        # Save formatted text (with answers)
        txt_file_answers = f"{base_name}_with_answers.txt"
        formatted_with_answers = self.quiz_generator.format_quiz(questions, show_answers=True)
        with open(txt_file_answers, 'w', encoding='utf-8') as f:
            f.write(formatted_with_answers)
        print(f"Quiz with answers saved to: {txt_file_answers}")
        
        # Save formatted text (without answers - for taking the quiz)
        txt_file_quiz = f"{base_name}_quiz_only.txt"
        formatted_quiz_only = self.quiz_generator.format_quiz(questions, show_answers=False)
        with open(txt_file_quiz, 'w', encoding='utf-8') as f:
            f.write(formatted_quiz_only)
        print(f"Quiz (no answers) saved to: {txt_file_quiz}")
    
    def display_quiz(self, result: dict, show_answers: bool = True):
        """
        Display quiz in console.
        
        Args:
            result: Quiz result dictionary from generate_quiz()
            show_answers: Whether to show answers
        """
        formatted = self.quiz_generator.format_quiz(
            result['questions'],
            show_answers=show_answers
        )
        print(formatted)


def main():
    """Main entry point for the application."""
    print("\n" + "="*80)
    print(" RAG-BASED QUIZ GENERATOR WITH HYBRID RETRIEVAL AND SEMANTIC EXPANSION")
    print("="*80 + "\n")
    
    # Example usage
    try:
        # Initialize system
        rag_system = RAGQuizSystem()
        
        # Get PDF path from user
        if len(sys.argv) > 1:
            pdf_path = sys.argv[1]
        else:
            pdf_path = input("Enter path to PDF file: ").strip().strip('"')
        
        # Load document
        rag_system.load_document(pdf_path)
        
        # Get quiz parameters
        print("\n" + "="*80)
        print("QUIZ CONFIGURATION")
        print("="*80)
        
        topic = input("\nEnter quiz topic (e.g., 'linear regression'): ").strip()
        if not topic:
            topic = "document content"
        
        try:
            num_questions = int(input("Number of questions (default 10): ").strip() or "10")
        except ValueError:
            num_questions = 10
        
        difficulty = input("Difficulty (easy/medium/hard/mixed, default 'mixed'): ").strip() or "mixed"
        
        use_expansion_input = input("Use semantic query expansion? (y/n, default 'y'): ").strip().lower()
        use_expansion = use_expansion_input != 'n'
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"quiz_{topic.replace(' ', '_')}_{timestamp}"
        
        # Generate quiz
        result = rag_system.generate_quiz(
            topic=topic,
            num_questions=num_questions,
            difficulty=difficulty,
            use_expansion=use_expansion,
            num_expansions=5,
            output_file=output_file
        )
        
        # Display quiz
        print("\n" + "="*80)
        print("GENERATED QUIZ")
        print("="*80 + "\n")
        
        show_answers = input("Show answers? (y/n, default 'y'): ").strip().lower() != 'n'
        rag_system.display_quiz(result, show_answers=show_answers)
        
        print("\n" + "="*80)
        print("Quiz generation completed successfully!")
        print(f"Files saved with prefix: {output_file}")
        print("="*80 + "\n")
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
