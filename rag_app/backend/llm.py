from groq import Groq
import logging

logger = logging.getLogger(__name__)

class GroqLLM:
    """Groq LLM client for generating responses"""
    
    def __init__(self, api_key: str, model: str):
        """Initialize Groq client"""
        logger.info(f"Initializing Groq LLM with model: {model}")
        self.client = Groq(api_key=api_key)
        self.model = model
    
    def generate_response(self, prompt: str, context: str, query: str) -> str:
        """Generate response using Groq LLM"""
        logger.info("Generating LLM response")

        # Detect personal/identity questions and answer directly
        personal_questions = [
            "who am i", "what is my name", "tell me about myself", "introduce me", "about me", "my introduction"
        ]
        if any(q in query.lower() for q in personal_questions):
            direct_prompt = f"""The user asked a personal question: '{query}'.
If you know the user's name or grade, answer directly and briefly (e.g., 'You are Kira, a 12th standard student.').
Do NOT use or analyze any context. Do NOT summarize or add extra information. Just answer the question simply and directly in one line.
"""
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a professional assistant. For personal questions, answer simply and directly without context or extra info."},
                        {"role": "user", "content": direct_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=100
                )
                answer = response.choices[0].message.content
                logger.info(f"Direct personal answer: {answer}")
                return answer
            except Exception as e:
                logger.error(f"Error generating direct answer: {str(e)}")
                return f"Error: {str(e)}"

        # Otherwise, use context and full formatting
        full_prompt = f"""Use the context below to answer the user question.
If the answer is not in the context, say "I don't know based on the provided documents."

CONTEXT:
{context}

QUESTION:
{query}

FORMATTING REQUIREMENTS:
- Begin with a brief summary (1-2 sentences)
- Use headers (## for main sections)
- Use bullet points and numbered lists for clarity
- Use LaTeX for mathematical formulas: $$ formula $$
- Use **bold** for key concepts and terms
- Provide examples when relevant
- Structure the answer clearly - DO NOT return long unformatted paragraphs
- Make equations visually separate from text
- Keep the response professional and well-organized like ChatGPT

ANSWER (in well-formatted Markdown):"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional assistant that provides well-formatted, structured answers in Markdown. Always format your responses with headers, bullet points, LaTeX for math, and bold for key concepts."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            answer = response.choices[0].message.content
            logger.info(f"Generated response: {answer[:100]}...")
            return answer
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error: {str(e)}"