import logging
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Sentiment analysis using DistilBERT fine-tuned model"""
    
    def __init__(self, model_path=None):
        """Initialize sentiment analyzer with trained model"""
        try:
            # Use the pretrained distilbert-base-uncased-finetuned-sst-2-english from HuggingFace
            model_name = "distilbert-base-uncased-finetuned-sst-2-english"
            
            logger.info(f"Loading sentiment model: {model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Try to load your fine-tuned model, fallback to pretrained
            if model_path:
                try:
                    self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
                    logger.info(f"✅ Loaded fine-tuned model from {model_path}")
                except Exception as e:
                    logger.warning(f"Could not load custom model from {model_path}: {e}")
                    logger.info("Loading default pretrained model...")
                    self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            else:
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            self.model.eval()
            logger.info("✅ Sentiment model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Error loading sentiment model: {e}")
            raise
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of the given text"""
        try:
            if not text or not text.strip():
                return {
                    "success": False,
                    "error": "Text is empty"
                }
            
            # Tokenize and predict
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_class = torch.argmax(predictions, dim=-1).item()
                confidence = predictions[0][predicted_class].item()
            
            # Map prediction to sentiment
            sentiment_map = {0: "Negative", 1: "Positive"}
            sentiment = sentiment_map.get(predicted_class, "Unknown")
            
            logger.info(f"Sentiment: {sentiment} (confidence: {confidence:.2%})")
            
            return {
                "success": True,
                "sentiment": sentiment,
                "confidence": round(confidence * 100, 2),
                "text": text
            }
        
        except Exception as e:
            logger.error(f"❌ Sentiment analysis error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }