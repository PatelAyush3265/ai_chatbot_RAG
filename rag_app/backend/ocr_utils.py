"""
OCR Utilities Module
Provides OCR functionality for extracting text from PDFs and images.
Uses pytesseract for OCR, pdf2image for PDF conversion, and OpenCV for image preprocessing.
"""

import os
from pathlib import Path
from PIL import Image
import numpy as np
import cv2
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# Configure paths for Tesseract and Poppler
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"A:\Tesseract11\Release-25.12.0-0\poppler-25.12.0\Library\bin"


class OCRProcessor:
    """Handles OCR processing for images and PDFs."""
    
    def __init__(self, tesseract_path: str = TESSERACT_PATH, poppler_path: str = POPPLER_PATH):
        """
        Initialize OCR processor with paths to external tools.
        
        Args:
            tesseract_path: Path to tesseract executable
            poppler_path: Path to poppler bin directory
        """
        self.tesseract_path = tesseract_path
        self.poppler_path = poppler_path
        
        # Configure pytesseract
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            self.pytesseract = pytesseract
            logger.info(f"✅ Tesseract configured at: {self.tesseract_path}")
        except ImportError:
            logger.error("❌ pytesseract not installed. Run: pip install pytesseract")
            raise
        
        # Verify poppler path exists
        if not Path(self.poppler_path).exists():
            logger.warning(f"⚠️ Poppler path not found: {self.poppler_path}")
    
    def pil_to_cv(self, img_pil: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format (BGR)."""
        arr = np.array(img_pil)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    
    def cv_to_pil(self, img_cv: np.ndarray) -> Image.Image:
        """Convert OpenCV image (BGR or grayscale) to PIL RGB."""
        if len(img_cv.shape) == 2:
            return Image.fromarray(img_cv)
        else:
            img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
            return Image.fromarray(img_rgb)
    
    def remove_border(self, img_gray: np.ndarray, pad: int = 10) -> np.ndarray:
        """
        Crop large white borders from image.
        
        Args:
            img_gray: Grayscale image array
            pad: Padding to add around detected content
            
        Returns:
            Cropped grayscale image
        """
        _, th = cv2.threshold(img_gray, 250, 255, cv2.THRESH_BINARY)
        th = 255 - th  # invert -> foreground is white
        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return img_gray
        
        # Find bounding box around all contours
        x_min, y_min = img_gray.shape[1], img_gray.shape[0]
        x_max, y_max = 0, 0
        
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            x_min = min(x_min, x)
            y_min = min(y_min, y)
            x_max = max(x_max, x + w)
            y_max = max(y_max, y + h)
        
        # Apply padding and clamp to image boundaries
        x0 = max(x_min - pad, 0)
        y0 = max(y_min - pad, 0)
        x1 = min(x_max + pad, img_gray.shape[1])
        y1 = min(y_max + pad, img_gray.shape[0])
        
        return img_gray[y0:y1, x0:x1]
    
    def resize_and_pad(self, img_gray: np.ndarray, target_size: tuple = (1024, 1024), 
                      background: int = 255) -> np.ndarray:
        """
        Resize image while preserving aspect ratio, then pad to target size.
        
        Args:
            img_gray: Grayscale image array
            target_size: Target (height, width)
            background: Background color for padding
            
        Returns:
            Resized and padded image
        """
        th, tw = target_size
        h, w = img_gray.shape
        scale = min(tw / w, th / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized = cv2.resize(img_gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Create padded canvas
        canvas = np.ones((th, tw), dtype=np.uint8) * background
        
        # Center the image
        x_offset = (tw - new_w) // 2
        y_offset = (th - new_h) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        return canvas
    
    def preprocess_image(self, pil_img: Image.Image, 
                        target_size: tuple = (1024, 1024),
                        denoise: bool = True,
                        remove_border_flag: bool = True,
                        adaptive_thresh: bool = True) -> Image.Image:
        """
        Preprocess image for optimal OCR results.
        
        Steps:
        - Convert to grayscale
        - Optional denoising
        - Optional border removal
        - Contrast normalization (CLAHE)
        - Optional adaptive thresholding
        - Resize and pad to target size
        
        Args:
            pil_img: Input PIL image
            target_size: Target dimensions
            denoise: Apply median blur denoising
            remove_border_flag: Remove white borders
            adaptive_thresh: Apply adaptive thresholding
            
        Returns:
            Preprocessed PIL image
        """
        # Convert to OpenCV grayscale
        img_cv = self.pil_to_cv(pil_img)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        if denoise:
            gray = cv2.medianBlur(gray, 3)
        
        # Remove borders
        if remove_border_flag:
            gray = self.remove_border(gray)
        
        # Contrast enhancement using CLAHE
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # Adaptive thresholding for better OCR
        if adaptive_thresh:
            gray = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 
                blockSize=25, 
                C=10
            )
        
        # Resize and pad
        gray = self.resize_and_pad(gray, target_size=target_size, background=255)
        
        # Final morphological cleaning
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        
        return self.cv_to_pil(gray)
    
    def extract_text_from_image(self, image_path: str, preprocess: bool = True) -> str:
        """
        Extract text from an image file using OCR.
        
        Args:
            image_path: Path to image file
            preprocess: Apply preprocessing before OCR
            
        Returns:
            Extracted text
        """
        try:
            # Load image
            img = Image.open(image_path).convert("RGB")
            
            # Preprocess if requested
            if preprocess:
                img = self.preprocess_image(img)
            else:
                # Simple grayscale + threshold
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                img = Image.fromarray(gray)
            
            # Perform OCR
            text = self.pytesseract.image_to_string(img, lang='eng')
            logger.info(f"✅ OCR extracted {len(text)} characters from image")
            return text
            
        except Exception as e:
            logger.error(f"❌ OCR failed for image {image_path}: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_path: str, preprocess: bool = True) -> str:
        """
        Extract text from a PDF file using OCR.
        
        Args:
            pdf_path: Path to PDF file
            preprocess: Apply preprocessing before OCR
            
        Returns:
            Extracted text from all pages
        """
        try:
            from pdf2image import convert_from_path
        except ImportError:
            logger.error("❌ pdf2image not installed. Run: pip install pdf2image")
            raise
        
        try:
            # Convert PDF pages to images
            pages = convert_from_path(pdf_path, poppler_path=self.poppler_path)
            logger.info(f"📄 Converting {len(pages)} pages from PDF")
            
            all_text = []
            
            # Process each page
            for i, page in enumerate(pages, start=1):
                # Preprocess if requested
                if preprocess:
                    page = self.preprocess_image(page)
                else:
                    # Simple grayscale + threshold
                    img_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                    page = Image.fromarray(gray)
                
                # Perform OCR
                text = self.pytesseract.image_to_string(page, lang='eng')
                all_text.append(f"--- Page {i} ---\n{text}")
                logger.info(f"✅ OCR page {i}/{len(pages)}: {len(text)} characters")
            
            combined_text = "\n\n".join(all_text)
            logger.info(f"✅ OCR completed: {len(combined_text)} total characters from {len(pages)} pages")
            return combined_text
            
        except Exception as e:
            logger.error(f"❌ OCR failed for PDF {pdf_path}: {e}")
            raise
    
    def extract_text(self, file_path: str, preprocess: bool = True) -> str:
        """
        Extract text from a file (auto-detects PDF or image).
        
        Args:
            file_path: Path to file
            preprocess: Apply preprocessing before OCR
            
        Returns:
            Extracted text
        """
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path, preprocess)
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
            return self.extract_text_from_image(file_path, preprocess)
        else:
            raise ValueError(f"Unsupported file type: {ext}")


# Convenience function for quick usage
def extract_text_from_file(file_path: str, preprocess: bool = True) -> str:
    """
    Convenience function to extract text from any supported file.
    
    Args:
        file_path: Path to file (PDF or image)
        preprocess: Apply image preprocessing
        
    Returns:
        Extracted text
    """
    ocr = OCRProcessor()
    return ocr.extract_text(file_path, preprocess)
