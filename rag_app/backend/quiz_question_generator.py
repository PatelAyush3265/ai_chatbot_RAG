"""
Quiz Question Generator for RAG System
Uses retrieved context chunks and LLM to generate quiz questions and answers.
"""

from groq import Groq
from typing import List, Dict
import os
from dotenv import load_dotenv
import json
import re
import random


class QuizQuestionGenerator:
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
        # Take top chunks by score if available
        top_chunks = sorted(chunks, key=lambda x: x.get('score', 0), reverse=True)[:max_chunks]
        
        context_parts = []
        for i, chunk in enumerate(top_chunks, 1):
            text = chunk.get('text', chunk.get('chunk', {}).get('text', ''))
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
        
        # Define difficulty-specific instructions
        difficulty_instructions = {
            "easy": """
DIFFICULTY: EASY
- Focus on basic concepts, definitions, and fundamental understanding
- Questions should test recall and basic comprehension
- Keep questions straightforward and direct
- Use clear, simple language""",
            
            "medium": """
DIFFICULTY: MEDIUM
- Focus on deeper conceptual understanding and application
- Include numerical problems and calculations if present in the text
- Test understanding of relationships between concepts
- Can go slightly beyond the text to related concepts
- Include formula-based questions if applicable""",
            
            "hard": """
DIFFICULTY: HARD
- Focus on advanced conceptual analysis and critical thinking
- Include complex numerical problems and multi-step calculations
- Test ability to synthesize information from different parts
- Can explore related concepts beyond the text
- Include advanced applications, edge cases, and theoretical implications
- Use technical terms and expect deep understanding""",
            
            "mixed": """
DIFFICULTY: MIXED (Variety of Easy, Medium, and Hard)
- Distribute questions across all difficulty levels
- Include basic definitions (Easy)
- Include conceptual applications and numerical problems (Medium)
- Include advanced analysis and theoretical questions (Hard)
- Can explore related concepts beyond the text for harder questions
- Balance straightforward recall with deeper understanding"""
        }
        
        # Get difficulty instructions
        diff_instructions = difficulty_instructions.get(difficulty.lower(), difficulty_instructions["mixed"])
        
        # Enhanced prompt for creative, engaging, and well-formatted questions
        prompt = f"""You are a professional quiz generator. Create {num_questions} engaging, creative, and high-quality quiz questions covering DIFFERENT concepts from this text about {topic}.

{diff_instructions}

TEXT:
{context}

CRITICAL REQUIREMENTS:
- DO NOT copy questions or options directly from the source text. Always rephrase and add creativity.
- Make questions and answer options engaging, clear, and professionally worded.
- Focus on CONCEPTUAL understanding - test comprehension, application, and analysis
- DO NOT ask trivia questions like "Who invented X?" or "When was X discovered?"
- If numerical values, formulas, or equations are present in the text, include calculation-based questions
- For medium/hard/mixed levels: You can generate questions on related concepts if they help test deeper understanding
- Cover variety: core concepts, mathematical relationships, interpretations, applications, theoretical implications
- Questions should span the ENTIRE text, not just the first paragraph
- Each question MUST cover a DIFFERENT concept, formula, or aspect
- Add a little creativity to the questions and options to make them more engaging and high-quality

OUTPUT FORMAT - Valid JSON array using "answers" and "correct":
[{{"question":"What is the primary purpose of the least squares method in linear regression?","answers":["To maximize prediction errors","To minimize the sum of squared residuals","To create non-linear relationships","To eliminate all outliers"],"correct":1}}]

Rules:
1. Use "answers" (array of 4 options) and "correct" (index 0-3)
2. Start with [ and end with ]
3. NO text before [ or after ]
4. Generate exactly {num_questions} DIVERSE questions
5. Follow the {difficulty.upper()} difficulty level

Generate the JSON:"""

        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"  Retry {attempt}...")
                
                response = self.client.chat.completions.create(
                    model=self.model,
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
                    raise ValueError("No JSON found in response")
                
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
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
                
                # Parse JSON
                if json_str.startswith('{'):
                    temp = json.loads(json_str)
                    if isinstance(temp, dict) and 'questions' in temp:
                        questions = temp['questions']
                    else:
                        raise ValueError("Response is object but doesn't contain 'questions' key")
                else:
                    questions = json.loads(json_str)
                
                # Validate structure
                if not isinstance(questions, list) or len(questions) == 0:
                    raise ValueError("Invalid response structure")
                
                # Validate and fix each question
                valid = []
                for i, q in enumerate(questions):
                    if not isinstance(q, dict):
                        continue
                    
                    if 'question' not in q:
                        continue
                    
                    # Handle different answer formats
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
                            letters = ['A', 'B', 'C', 'D']
                            if isinstance(correct_idx, int) and 0 <= correct_idx < 4:
                                q['correct_answer'] = letters[correct_idx]
                            else:
                                q['correct_answer'] = 'A'
                    
                    # Check if we have the required fields
                    if 'options' not in q or 'correct_answer' not in q:
                        continue
                    
                    # Validate options
                    opts = q.get('options', {})
                    if isinstance(opts, list) and len(opts) >= 4:
                        opts = {
                            "A": str(opts[0]),
                            "B": str(opts[1]),
                            "C": str(opts[2]),
                            "D": str(opts[3])
                        }
                        q['options'] = opts
                    elif not isinstance(opts, dict):
                        continue
                    
                    missing = [k for k in ['A', 'B', 'C', 'D'] if k not in opts]
                    if missing:
                        continue
                    
                    # Normalize correct_answer
                    correct = str(q['correct_answer']).upper().strip()
                    if correct not in ['A', 'B', 'C', 'D']:
                        match = re.search(r'[ABCD]', correct.upper())
                        if match:
                            correct = match.group()
                        else:
                            correct = 'A'
                    q['correct_answer'] = correct
                    
                    # Shuffle answer options
                    if self.shuffle_answers:
                        self._shuffle_options(q)
                    
                    # Add defaults
                    if 'explanation' not in q:
                        q['explanation'] = f"The correct answer is {q['correct_answer']}."
                    if 'difficulty' not in q:
                        q['difficulty'] = difficulty
                    if 'topic_area' not in q:
                        q['topic_area'] = topic
                    
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
                if attempt < max_retries - 1:
                    print(f"  Attempt {attempt + 1} failed: {str(e)[:50]}...")
                    continue
                else:
                    print(f"\n❌ All {max_retries} attempts failed: {str(e)}")
                    return self._generate_fallback_questions(topic, num_questions)
    
    def _shuffle_options(self, question: Dict) -> None:
        """Shuffle answer options while maintaining correctness."""
        opts = question['options']
        correct_letter = question['correct_answer']
        
        letters = ['A', 'B', 'C', 'D']
        options_list = [(letter, opts[letter]) for letter in letters]
        random.shuffle(options_list)
        
        new_options = {}
        for new_letter, (old_letter, text) in zip(letters, options_list):
            new_options[new_letter] = text
            if old_letter == correct_letter:
                question['correct_answer'] = new_letter
        
        question['options'] = new_options
    
    def _generate_fallback_questions(self, topic: str, num: int) -> List[Dict[str, any]]:
        """Generate fallback questions if LLM fails."""
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
