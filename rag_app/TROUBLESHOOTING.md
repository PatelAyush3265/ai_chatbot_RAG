# OCR Integration - Troubleshooting Guide

## Quick Diagnostics

Run this command first to check your setup:
```bash
cd D:\gw\env\rag_app
python test_ocr_setup.py
```

---

## Common Issues & Solutions

### ❌ Issue 1: "ModuleNotFoundError: No module named 'pytesseract'"

**Problem:** OCR Python packages not installed

**Solution:**
```bash
# Activate environment
cd D:\gw
.\env\Scripts\Activate.ps1

# Install packages
pip install pytesseract pdf2image Pillow opencv-python numpy
```

**Verify:**
```bash
python -c "import pytesseract; import pdf2image; import cv2; print('✅ All packages installed')"
```

---

### ❌ Issue 2: "TesseractNotFoundError: tesseract is not installed"

**Problem:** Tesseract-OCR not installed or path incorrect

**Solution 1 - Install Tesseract:**
1. Download: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to: `C:\Program Files\Tesseract-OCR`
3. During installation, make sure to add to PATH

**Solution 2 - Verify Installation:**
```bash
# Check if tesseract is accessible
tesseract --version

# If not found, check installation path
dir "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

**Solution 3 - Fix Path in Code:**
Edit `rag_app/backend/ocr_utils.py`:
```python
# Line ~15
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# Update to your actual path
```

---

### ❌ Issue 3: "PDFInfoNotInstalledError" or Poppler errors

**Problem:** Poppler not installed or path incorrect

**Solution 1 - Check Poppler:**
```bash
# Check if poppler exists
dir "A:\Tesseract11\Release-25.12.0-0\poppler-25.12.0\Library\bin\pdfinfo.exe"
```

**Solution 2 - Download Poppler:**
1. Download: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract to a permanent location
3. Note the path to the `bin` folder

**Solution 3 - Update Path:**
Edit `rag_app/backend/ocr_utils.py`:
```python
# Line ~16
POPPLER_PATH = r"A:\Tesseract11\Release-25.12.0-0\poppler-25.12.0\Library\bin"
# Update to your actual path
```

---

### ❌ Issue 4: Backend fails to start

**Problem:** Import errors or initialization failures

**Check Logs:**
```bash
cd D:\gw\env\rag_app\backend
uvicorn main:app --reload
# Watch for error messages
```

**Common Causes:**

1. **Missing dependencies:**
```bash
pip install -r requirements.txt
```

2. **OCR processor initialization failed:**
- Check if warning appears: "⚠️ OCR processor initialization failed"
- System will work but without OCR support
- Fix Tesseract/Poppler paths

3. **Python version issues:**
```bash
python --version
# Should be Python 3.8 or higher
```

---

### ❌ Issue 5: OCR produces gibberish or poor results

**Problem:** Low image quality or wrong settings

**Solution 1 - Image Quality:**
- Use higher resolution images (300 DPI minimum)
- Ensure good contrast between text and background
- Avoid blurry or skewed images

**Solution 2 - Adjust Preprocessing:**
Edit `rag_app/backend/ocr_utils.py` in `preprocess_image()`:
```python
# Try different preprocessing settings
preprocessed = self.preprocess_image(
    img,
    denoise=True,           # Set False if over-smoothed
    remove_border_flag=True,# Set False to keep borders
    adaptive_thresh=True    # Set False for simple threshold
)
```

**Solution 3 - Skip Preprocessing:**
```python
# In extract_text_from_image() or extract_text_from_pdf()
text = ocr_processor.extract_text(file_path, preprocess=False)
```

---

### ❌ Issue 6: Upload fails with images

**Problem:** Unsupported format or file too large

**Check File:**
- Supported: .png, .jpg, .jpeg, .tiff, .bmp, .gif
- Size limit: 16MB (configurable)

**Solution - Increase Size Limit:**
Edit `rag_app/backend/main.py`:
```python
# Add after app initialization
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
```

---

### ❌ Issue 7: "OCR failed" in logs but no error

**Problem:** OCR encountered error but system continued

**Check Logs:**
```bash
# Look for these messages:
# "⚠️ OCR failed for {filename}: {error}"
# "↩️ Attempting standard processing"
```

**Solution:**
- For PDFs: System falls back to standard text extraction
- For images: Cannot process without OCR - fix OCR setup
- Check previous issues for OCR setup problems

---

### ❌ Issue 8: Slow processing

**Problem:** OCR is processing intensive

**Expected Times:**
- Small image (< 1MB): 2-4 seconds
- Large image (> 5MB): 5-10 seconds
- PDF (1 page): 3-5 seconds
- PDF (10 pages): 30-60 seconds

**Optimization:**
1. Reduce image resolution before upload
2. Use preprocessing=False for faster (but less accurate) results
3. Consider batch processing for multiple files

---

### ❌ Issue 9: Cannot import ocr_utils

**Problem:** Module path issues

**Solution:**
```bash
# Make sure you're in the right directory
cd D:\gw\env\rag_app

# Run from parent directory, not inside backend
python -c "from backend.ocr_utils import OCRProcessor; print('✅ Import works')"
```

---

### ❌ Issue 10: CORS errors in frontend

**Problem:** Frontend cannot access backend

**Solution - Check CORS Settings:**
Edit `rag_app/backend/main.py`:
```python
# Make sure your frontend URL is in allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        # Add your frontend URL here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Diagnostic Commands

### Check Python Environment
```bash
python --version
pip list | findstr "pytesseract\|pdf2image\|Pillow\|opencv\|numpy"
```

### Check Tesseract
```bash
tesseract --version
"C:\Program Files\Tesseract-OCR\tesseract.exe" --version
```

### Check Poppler
```bash
dir "A:\Tesseract11\Release-25.12.0-0\poppler-25.12.0\Library\bin"
```

### Test OCR Setup
```bash
cd D:\gw\env\rag_app
python test_ocr_setup.py
```

### Test Backend
```bash
cd D:\gw\env\rag_app\backend
uvicorn main:app --reload
# Open browser: http://localhost:8000
# Should see: {"status": "running", ...}
```

---

## Getting Help

### Step 1: Run Diagnostics
```bash
cd D:\gw\env\rag_app
python test_ocr_setup.py > diagnostic_output.txt
```

### Step 2: Check Logs
```bash
# When running backend, check terminal for:
# ✅ Green checkmarks = working
# ⚠️  Yellow warnings = working but degraded
# ❌ Red errors = not working
```

### Step 3: Review Files
- `OCR_INTEGRATION_GUIDE.md` - Complete documentation
- `OCR_INTEGRATION_SUMMARY.md` - Quick reference
- `ARCHITECTURE.md` - System design
- `QUICK_REFERENCE.txt` - At-a-glance guide

---

## Checklist for New Setup

When setting up on a new machine:

- [ ] Python 3.8+ installed
- [ ] Virtual environment activated
- [ ] Python packages installed (`pip install -r requirements.txt`)
- [ ] Tesseract-OCR installed
- [ ] Tesseract path verified
- [ ] Poppler downloaded and extracted
- [ ] Poppler path verified
- [ ] `test_ocr_setup.py` all tests pass
- [ ] Backend starts without errors
- [ ] Test file upload successful
- [ ] OCR processing works
- [ ] Query functionality works

---

## Emergency Fallback

If OCR completely fails and you need the system to work:

The system is designed to work WITHOUT OCR:
- Standard text PDFs will still be processed
- Text files will still work
- Only image and scanned PDF processing will fail
- RAG functionality remains intact

To disable OCR warnings:
```python
# In backend/main.py, comment out OCR initialization:
# ocr_processor = OCRProcessor()
ocr_processor = None
```

---

## Performance Tips

1. **Optimize Images Before Upload:**
   - Convert to PNG or JPG
   - Reduce to 300 DPI
   - Crop unnecessary borders

2. **Batch Processing:**
   - Upload multiple files at once
   - System processes sequentially

3. **Skip Preprocessing:**
   - If images are already high quality
   - Set `preprocess=False` in OCR calls

4. **Monitor Resource Usage:**
   - OCR is CPU intensive
   - Each page uses ~100-200MB RAM temporarily
   - Consider system resources for large batches

---

## Contact & Support

If issues persist:
1. Check all documentation files in `rag_app/`
2. Run `test_ocr_setup.py` for diagnostics
3. Review backend logs for specific errors
4. Verify all paths are correct for your system
5. Ensure all system requirements are installed

Remember: The system is designed to gracefully handle OCR failures and continue working with standard file types.
