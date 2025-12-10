"""
Quiz Question Generator
Uses retrieved context chunks and LLM to generate quiz questions and answers.
"""

from groq import Groq
from typing import List, Dict
import os
from dotenv import load_dotenv
import json
import re
import random


class QuizGenerator:
    """Generate quiz questions from retrieved document chunks."""
    
    def __init__(self, api_key: str = None, model: str = "meta-llama/llama-4-scout-17b-16e-instruct", shuffle_answers: bool = True):
        """
        Initialize quiz generator.
        
        Args:
            api_key: Groq API key (if None, reads from environment)
            model: Groq model to use (default: meta-llama/llama-4-scout-17b-16e-instruct)
            shuffle_answers: Whether to shuffle answer options to avoid position bias (default: True)
        """
        load_dotenv()
        
        if api_key is None:
            api_key = os.getenv('GROQ_API_KEY')
        
        if not api_key:
            raise ValueError(
                "Groq API key not found. Set GROQ_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = Groq(api_key=api_key)
        self.model = model
        self.shuffle_answers = shuffle_answers
    
    def generate_questions(self, 
                          context_chunks: List[Dict[str, any]], 
                          topic: str,
                          num_questions: int = 10,
                          difficulty: str = "mixed") -> List[Dict[str, any]]:
        """
        Generate quiz questions from context chunks.
        
        Args:
            context_chunks: List of retrieved chunks with text
            topic: Main topic/query
            num_questions: Number of questions to generate
            difficulty: Question difficulty ("easy", "medium", "hard", "mixed")
            
        Returns:
            List of questions with answers and metadata
        """
        if not context_chunks:
            raise ValueError("No context chunks provided")
        
        # Combine context from chunks
        context = self._prepare_context(context_chunks)
        
        # Generate questions
        print(f"\nGenerating {num_questions} questions about '{topic}'...")
        questions = self._generate_with_llm(context, topic, num_questions, difficulty)
        
        return questions
    
    def _prepare_context(self, chunks: List[Dict[str, any]], max_chunks: int = 10) -> str:
        """
        Prepare context from chunks for question generation.
        
        Args:
            chunks: Retrieved chunks
            max_chunks: Maximum number of chunks to use
            
        Returns:
            Combined context string
        """
        # Take top chunks by score
        top_chunks = chunks[:max_chunks]
        
        # Combine text
        context_parts = []
        for i, chunk in enumerate(top_chunks, 1):
            text = chunk.get('text', chunk.get('chunk', {}).get('text', ''))
            # Limit each chunk to avoid token overflow
            if len(text) > 500:
                text = text[:500] + "..."
            context_parts.append(f"[{i}] {text}")
        
        return "\n\n".join(context_parts)
    
    def _generate_with_llm(self, 
                           context: str, 
                           topic: str, 
                           num_questions: int,
                           difficulty: str) -> List[Dict[str, any]]:
        """
        Use LLM to generate questions from context.
        
        Args:
            context: Combined context text
            topic: Main topic
            num_questions: Number of questions
            difficulty: Question difficulty
            
        Returns:
            List of generated questions
        """
        # Limit context to prevent token overflow
        if len(context) > 2500:
            context = context[:2500] + "..."
        
        # Improved prompt emphasizing diversity
        prompt = f"""You are a quiz generator. Create {num_questions} DIVERSE quiz questions covering DIFFERENT concepts from this text about {topic}.

TEXT:
{context}

CRITICAL REQUIREMENTS:
- Each question MUST cover a DIFFERENT concept, formula, or aspect
- DO NOT create multiple questions about the same formula or definition
- Cover variety: definitions, calculations, interpretations, applications, history, examples
- Questions should span the ENTIRE text, not just the first paragraph

OUTPUT FORMAT - Valid JSON array using "answers" and "correct":
[{{"question":"Who pioneered linear regression?","answers":["Newton","Galton","Einstein","Gauss"],"correct":1}}]

Rules:
1. Use "answers" (array of 4 options) and "correct" (index 0-3)
2. Start with [ and end with ]
3. NO text before [ or after ]
4. Generate exactly {num_questions} DIVERSE questions

Generate the JSON:"""

        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"  Retry {attempt}...")
                
                # Try with response_format for JSON mode
                try:
                    response = self.client.chat.completions.create(
                        model="meta-llama/llama-4-scout-17b-16e-instruct",
                        messages=[
                            {"role": "system", "content": "You generate quiz questions in JSON format only. Always output valid JSON arrays."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=4000,
                        response_format={"type": "json_object"}
                    )
                except:
                    # Fallback without JSON mode if not supported
                    response = self.client.chat.completions.create(
                        model="meta-llama/llama-4-scout-17b-16e-instruct",
                        messages=[
                            {"role": "system", "content": "You generate quiz questions in JSON format only. Always output valid JSON arrays."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=4000
                    )
                
                content = response.choices[0].message.content.strip()
                
                # Print preview for debugging
                if attempt == 0:
                    print(f"  Model response preview: {content[:150]}...")
                
                # Aggressive JSON extraction
                # Remove markdown code blocks
                if '```' in content:
                    parts = content.split('```')
                    for part in parts:
                        part = part.strip()
                        if part.lower().startswith('json'):
                            part = part[4:].strip()
                        if part.startswith('[') or part.startswith('{'):
                            content = part
                            break
                
                # Remove everything before first [ or {
                bracket_pos = content.find('[')
                brace_pos = content.find('{')
                
                if bracket_pos == -1 and brace_pos == -1:
                    raise ValueError("No JSON found in response - model returned plain text")
                
                # Prefer [ over { (we want array)
                if bracket_pos != -1:
                    start_pos = bracket_pos
                    end_char = ']'
                    end_pos = content.rfind(']')
                else:
                    start_pos = brace_pos
                    end_char = '}'
                    end_pos = content.rfind('}')
                
                if end_pos == -1:
                    raise ValueError(f"No closing {end_char} found")
                
                # Extract JSON string
                json_str = content[start_pos:end_pos+1]
                
                # Clean various garbage characters
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)  # Control chars
                json_str = re.sub(r'[¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿×÷]', '', json_str)  # Math symbols
                
                # If response is object with "questions" key, extract that
                if json_str.startswith('{'):
                    try:
                        temp = json.loads(json_str)
                        if isinstance(temp, dict) and 'questions' in temp:
                            questions = temp['questions']
                        else:
                            raise ValueError("Response is object but doesn't contain 'questions' key")
                    except json.JSONDecodeError:
                        raise ValueError("Invalid JSON object")
                else:
                    # Parse array
                    try:
                        questions = json.loads(json_str)
                    except json.JSONDecodeError as je:
                        print(f"  JSON parse error: {je.msg} at position {je.pos}")
                        # Show the problematic area
                        start = max(0, je.pos - 50)
                        end = min(len(json_str), je.pos + 50)
                        print(f"  Context: ...{json_str[start:end]}...")
                        raise ValueError(f"Failed to parse JSON: {je.msg}")
                
                # Validate structure
                if not isinstance(questions, list) or len(questions) == 0:
                    raise ValueError("Invalid response structure")
                
                # Validate and fix each question
                valid = []
                for i, q in enumerate(questions):
                    if not isinstance(q, dict):
                        print(f"  Skipping question {i+1}: not a dict")
                        continue
                    
                    # Debug: show actual structure for first question on first attempt
                    if attempt == 0 and i == 0:
                        print(f"  DEBUG: First question keys: {list(q.keys())}")
                        print(f"  DEBUG: First question sample: {str(q)[:200]}...")
                    
                    # Check required fields
                    if 'question' not in q:
                        print(f"  Skipping question {i+1}: missing 'question' field")
                        continue
                    
                    # Handle different answer formats
                    # Format 1: Model uses 'answers' array + 'correct' index
                    if 'answers' in q and 'correct' in q:
                        answers = q['answers']
                        correct_idx = q['correct']
                        if isinstance(answers, list) and len(answers) >= 4:
                            q['options'] = {
                                'A': str(answers[0]),
                                'B': str(answers[1]),
                                'C': str(answers[2]),
                                'D': str(answers[3])
                            }
                            # Convert index to letter (0->A, 1->B, 2->C, 3->D)
                            letters = ['A', 'B', 'C', 'D']
                            if isinstance(correct_idx, int) and 0 <= correct_idx < 4:
                                q['correct_answer'] = letters[correct_idx]
                            else:
                                q['correct_answer'] = 'A'  # Default fallback
                            print(f"  ✓ Converted question {i+1} from 'answers' format")
                    
                    # Format 2: Model uses separate 'A', 'B', 'C', 'D' keys + 'correct' 
                    elif 'A' in q and 'B' in q and 'C' in q and 'D' in q and 'correct' in q:
                        q['options'] = {
                            'A': str(q['A']),
                            'B': str(q['B']),
                            'C': str(q['C']),
                            'D': str(q['D'])
                        }
                        # Normalize correct answer to letter
                        correct = str(q['correct']).upper().strip()
                        if correct in ['A', 'B', 'C', 'D']:
                            q['correct_answer'] = correct
                        elif correct in ['0', '1', '2', '3']:
                            q['correct_answer'] = ['A', 'B', 'C', 'D'][int(correct)]
                        else:
                            q['correct_answer'] = 'A'
                        print(f"  ✓ Converted question {i+1} from separate keys format")
                    
                    # Now check if we have the required fields after conversion
                    if 'options' not in q:
                        print(f"  Skipping question {i+1}: missing 'options' field")
                        print(f"    Keys found: {list(q.keys())}")
                        continue
                    if 'correct_answer' not in q:
                        print(f"  Skipping question {i+1}: missing 'correct_answer' field")
                        continue
                    
                    # Validate and normalize options
                    opts = q.get('options', {})
                    
                    # Handle both array and dict formats for options
                    if isinstance(opts, list):
                        # Convert array to dict: [opt1, opt2, opt3, opt4] -> {"A": opt1, "B": opt2, ...}
                        if len(opts) >= 4:
                            opts = {
                                "A": str(opts[0]),
                                "B": str(opts[1]),
                                "C": str(opts[2]),
                                "D": str(opts[3])
                            }
                            q['options'] = opts
                        else:
                            print(f"  Skipping question {i+1}: options array has only {len(opts)} items, need 4")
                            continue  # Not enough options
                    elif isinstance(opts, dict):
                        # Ensure all options exist
                        missing = [k for k in ['A', 'B', 'C', 'D'] if k not in opts]
                        if missing:
                            print(f"  Skipping question {i+1}: options missing keys: {missing}")
                            continue
                    else:
                        print(f"  Skipping question {i+1}: options is {type(opts).__name__}, not list or dict")
                        continue  # Invalid options format
                    
                    # Normalize correct_answer to uppercase letter
                    correct = str(q['correct_answer']).upper().strip()
                    if correct not in ['A', 'B', 'C', 'D']:
                        # Try to extract letter from string like "Option A" or "a)"
                        match = re.search(r'[ABCD]', correct.upper())
                        if match:
                            correct = match.group()
                        else:
                            correct = 'A'  # Default
                    q['correct_answer'] = correct
                    
                    # Shuffle answer options to avoid bias (optional - can be toggled)
                    if hasattr(self, 'shuffle_answers') and self.shuffle_answers:
                        self._shuffle_options(q)
                    
                    # Add defaults for missing fields
                    if 'explanation' not in q:
                        q['explanation'] = f"The correct answer is {q['correct_answer']}."
                    if 'difficulty' not in q:
                        q['difficulty'] = difficulty
                    if 'topic_area' not in q:
                        q['topic_area'] = topic
                    
                    print(f"  ✓ Question {i+1} validated: {q['question'][:60]}...")
                    valid.append(q)
                
                if not valid:
                    raise ValueError("No valid questions in response")
                
                # Add metadata
                for i, q in enumerate(valid[:num_questions], 1):
                    q['question_number'] = i
                    q['source_topic'] = topic
                
                result = valid[:num_questions]
                print(f"✓ Successfully generated {len(result)} questions")
                return result
            
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    print(f"  Attempt {attempt + 1} failed: {error_msg[:50]}...")
                    continue
                else:
                    print(f"\n❌ All {max_retries} attempts failed")
                    print(f"   Last error: {error_msg}")
                    if 'content' in locals():
                        print(f"   Response preview: {content[:100]}...")
                    print("\n⚠️  Using placeholder questions")
                    print("💡 Troubleshooting tips:")
                    print("   1. Try with fewer questions (2-3)")
                    print("   2. Use a simpler topic")
                    print("   3. Check if Groq service is working: https://console.groq.com\n")
                    return self._generate_fallback_questions(topic, num_questions)
    
    def _shuffle_options(self, question: Dict) -> None:
        """
        Shuffle the answer options randomly while maintaining correctness.
        
        Args:
            question: Question dictionary to shuffle (modified in place)
        """
        # Get current options and correct answer
        opts = question['options']
        correct_letter = question['correct_answer']
        
        # Create list of (letter, text) pairs
        letters = ['A', 'B', 'C', 'D']
        options_list = [(letter, opts[letter]) for letter in letters]
        
        # Shuffle the options
        random.shuffle(options_list)
        
        # Rebuild options dict and find new position of correct answer
        new_options = {}
        for new_letter, (old_letter, text) in zip(letters, options_list):
            new_options[new_letter] = text
            if old_letter == correct_letter:
                question['correct_answer'] = new_letter
        
        question['options'] = new_options
    
    def _generate_fallback_questions(self, topic: str, num: int) -> List[Dict[str, any]]:
        """
        Generate simple fallback questions if LLM generation fails.
        
        Args:
            topic: Topic
            num: Number of questions
            
        Returns:
            Basic question structure
        """
        return [
            {
                "question_number": i,
                "question": f"Question about {topic} - {i}",
                "options": {
                    "A": "Option A",
                    "B": "Option B", 
                    "C": "Option C",
                    "D": "Option D"
                },
                "correct_answer": "A",
                "explanation": "This is a placeholder question. Please regenerate.",
                "difficulty": "medium",
                "topic_area": topic,
                "source_topic": topic
            }
            for i in range(1, num + 1)
        ]
    
    def format_quiz(self, questions: List[Dict[str, any]], show_answers: bool = False) -> str:
        """
        Format quiz questions as readable text.
        
        Args:
            questions: List of questions
            show_answers: Whether to show answers and explanations
            
        Returns:
            Formatted quiz string
        """
        output = []
        output.append("=" * 80)
        output.append(f"QUIZ: {questions[0]['source_topic'] if questions else 'Quiz'}")
        output.append(f"Total Questions: {len(questions)}")
        output.append("=" * 80)
        output.append("")
        
        for q in questions:
            output.append(f"Question {q['question_number']}: {q['question']}")
            output.append("")
            
            for opt_key in ['A', 'B', 'C', 'D']:
                if opt_key in q['options']:
                    output.append(f"  {opt_key}. {q['options'][opt_key]}")
            
            output.append("")
            
            if show_answers:
                output.append(f"✓ Correct Answer: {q['correct_answer']}")
                output.append(f"  Explanation: {q['explanation']}")
                output.append(f"  Difficulty: {q.get('difficulty', 'N/A')}")
                output.append("")
            
            output.append("-" * 80)
            output.append("")
        
        return "\n".join(output)
    
    def save_quiz(self, questions: List[Dict[str, any]], filename: str):
        """
        Save quiz to a JSON file.
        
        Args:
            questions: List of questions
            filename: Output filename
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        
        print(f"Quiz saved to: {filename}")


if __name__ == "__main__":
    # Example usage
    print("Quiz Generator Example")
    print("="*60)
    
    try:
        generator = QuizGenerator()
        
        # Sample context chunks
        sample_chunks = [
            {
                'text': 'Linear regression is a statistical method used to model the relationship between variables.',
                'hybrid_score': 0.95
            },
            {
                'text': 'Multiple linear regression extends simple linear regression by using more than one predictor variable.',
                'hybrid_score': 0.87
            }
        ]
        
        questions = generator.generate_questions(
            sample_chunks, 
            topic="linear regression",
            num_questions=3,
            difficulty="mixed"
        )
        
        print("\nGenerated Quiz:")
        print(generator.format_quiz(questions, show_answers=True))
    
    except Exception as e:
        print(f"\nNote: {str(e)}")
        print("\nTo use this module, you need to:")
        print("1. Set GROQ_API_KEY in your .env file")
        print("2. Get a free API key from: https://console.groq.com")
        print("3. Install required packages: pip install -r requirements.txt")
