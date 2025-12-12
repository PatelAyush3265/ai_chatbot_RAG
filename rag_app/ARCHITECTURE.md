# OCR Pipeline Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                             │
│                    (React Frontend / API Client)                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Upload File
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND (main.py)                       │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    /upload Endpoint                          │ │
│  │                  (ENHANCED WITH OCR)                         │ │
│  └──────────────────────┬───────────────────────────────────────┘ │
│                         │                                           │
│                         │ Detect File Type                          │
│                         ▼                                           │
│              ┌──────────────────────┐                               │
│              │   File Type Check    │                               │
│              └──────────┬───────────┘                               │
│                         │                                           │
│         ┌───────────────┼───────────────┐                           │
│         │               │               │                           │
│         ▼               ▼               ▼                           │
│     ┌──────┐       ┌──────┐       ┌──────┐                         │
│     │ .txt │       │ .pdf │       │ .png │                         │
│     │ file │       │ file │       │ .jpg │                         │
│     └──┬───┘       └──┬───┘       └──┬───┘                         │
│        │              │              │                              │
│        │              │              │                              │
│        │         ┌────┴────┐         │                              │
│        │         │         │         │                              │
│        │         ▼         ▼         │                              │
│        │    ┌────────┐  ┌────────┐   │                              │
│        │    │  Has   │  │Scanned/│   │                              │
│        │    │  Text  │  │ Image  │   │                              │
│        │    └───┬────┘  └────┬───┘   │                              │
│        │        │            │       │                              │
│        │        │            │       │                              │
│        │        │            ▼       │                              │
│        │        │    ┌───────────────────────┐                      │
│        │        │    │   OCR PROCESSOR       │                      │
│        │        │    │   (ocr_utils.py)      │◄─────────────────────┤
│        │        │    │                       │                      │
│        │        │    │  ┌─────────────────┐  │                      │
│        │        │    │  │ 1. Preprocess   │  │                      │
│        │        │    │  │    - Denoise    │  │                      │
│        │        │    │  │    - CLAHE      │  │                      │
│        │        │    │  │    - Threshold  │  │                      │
│        │        │    │  └─────────────────┘  │                      │
│        │        │    │                       │                      │
│        │        │    │  ┌─────────────────┐  │                      │
│        │        │    │  │ 2. Run Tesseract│  │                      │
│        │        │    │  │    OCR Engine   │  │                      │
│        │        │    │  └─────────────────┘  │                      │
│        │        │    │                       │                      │
│        │        │    │  ┌─────────────────┐  │                      │
│        │        │    │  │ 3. Extract Text │  │                      │
│        │        │    │  └─────────────────┘  │                      │
│        │        │    └───────────┬───────────┘                      │
│        │        │                │                                  │
│        ▼        ▼                ▼                                  │
│    ┌────────────────────────────────┐                               │
│    │      EXTRACTED TEXT            │                               │
│    └───────────────┬────────────────┘                               │
│                    │                                                 │
└────────────────────┼─────────────────────────────────────────────────┘
                     │
                     │ Pass to RAG Pipeline
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      RAG PIPELINE (unchanged)                       │
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐       │
│  │   Document   │────▶│  Text        │────▶│   Vector     │       │
│  │   Loader     │     │  Splitter    │     │   Store      │       │
│  └──────────────┘     └──────────────┘     └──────┬───────┘       │
│                                                     │               │
│  ┌──────────────┐                                  │               │
│  │  Embeddings  │◄─────────────────────────────────┘               │
│  └──────┬───────┘                                                  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                  │
│  │  ChromaDB    │                                                  │
│  │  (Indexed)   │                                                  │
│  └──────┬───────┘                                                  │
└─────────┼───────────────────────────────────────────────────────────┘
          │
          │ Ready for Queries
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        QUERY ENDPOINT                               │
│                                                                     │
│  User Question → Retrieval → LLM → Answer                          │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. OCR Processor (ocr_utils.py)
**Location:** `rag_app/backend/ocr_utils.py`

**Key Classes:**
- `OCRProcessor` - Main OCR handling class

**Key Methods:**
- `extract_text()` - Auto-detect and extract from any file
- `extract_text_from_image()` - Process images
- `extract_text_from_pdf()` - Process PDFs with OCR
- `preprocess_image()` - Enhance image quality for OCR

**Dependencies:**
- pytesseract (OCR engine wrapper)
- pdf2image (PDF to image conversion)
- OpenCV (image preprocessing)
- Pillow (image handling)

### 2. Backend Integration (main.py)
**Location:** `rag_app/backend/main.py`

**Changes:**
- Imported `OCRProcessor`
- Initialized OCR processor on startup
- Enhanced `/upload` endpoint with:
  - File type detection
  - OCR processing for images/PDFs
  - Fallback to standard processing
  - Error handling

**Flow:**
```python
1. File uploaded → Save to disk
2. Detect extension (.png, .pdf, etc.)
3. If image/PDF → Run OCR extraction
4. If text file → Direct processing
5. Pass extracted text → RAG pipeline
6. Return: chunks created, files processed
```

### 3. RAG Pipeline (unchanged)
**Location:** `rag_app/backend/rag_pipeline.py`

**No modifications made** - OCR integration is transparent:
- Receives text (from OCR or direct)
- Processes same as before
- No changes to existing logic

## Data Flow

```
Image/PDF Upload
       ↓
   Save File
       ↓
OCR Processing
   ┌───┴───┐
   │ Step 1│ Convert PDF to images (if needed)
   └───┬───┘
       ↓
   ┌───┴───┐
   │ Step 2│ Preprocess each image
   │       │  - Grayscale conversion
   │       │  - Denoising (median blur)
   │       │  - Border removal
   │       │  - Contrast enhancement (CLAHE)
   │       │  - Adaptive thresholding
   └───┬───┘
       ↓
   ┌───┴───┐
   │ Step 3│ Run Tesseract OCR
   └───┬───┘
       ↓
   ┌───┴───┐
   │ Step 4│ Extract & clean text
   └───┬───┘
       ↓
  Extracted Text
       ↓
  RAG Pipeline
       ↓
  Vector Database
       ↓
  Ready for Queries
```

## Error Handling Flow

```
Try OCR Processing
       ↓
   ┌───┴───┐
   │Success│──────────────────────┐
   └───────┘                      │
       ↓                          │
   Use Extracted Text             │
       ↓                          │
   ┌───────┐                      │
   │ Error │                      │
   └───┬───┘                      │
       ↓                          │
   Log Warning                    │
       ↓                          │
   ┌────────────┐                 │
   │ Is PDF?    │                 │
   └─────┬──────┘                 │
         │                        │
     Yes │  No                    │
         │   │                    │
         ▼   ▼                    │
   Standard  Return               │
   PDF Text  Error                │
   Extract                        │
         │                        │
         └────────────────────────┤
                                  ↓
                          Continue Processing
```

## Integration Benefits

✅ **Modular Design**
- OCR logic isolated in separate module
- Easy to maintain and update
- Can be reused in other parts of the system

✅ **Backward Compatible**
- Existing functionality unchanged
- Standard PDFs/text files work as before
- No breaking changes

✅ **Robust Error Handling**
- Graceful degradation if OCR fails
- Fallback to standard processing
- Comprehensive logging

✅ **Flexible Configuration**
- Easy to change Tesseract/Poppler paths
- Adjustable preprocessing parameters
- Configurable OCR settings

✅ **Production Ready**
- Tested error scenarios
- Logging for monitoring
- Performance optimized

## Performance Characteristics

| File Type | Processing Time | Notes |
|-----------|----------------|-------|
| Text file | < 1 second | Direct processing |
| Text PDF | 1-2 seconds | Native text extraction |
| Scanned PDF (1 page) | 3-5 seconds | OCR with preprocessing |
| Scanned PDF (10 pages) | 30-50 seconds | Depends on resolution |
| Image (PNG/JPG) | 2-4 seconds | OCR with preprocessing |

## Future Enhancements

Potential improvements:
- [ ] Multi-language support (currently English only)
- [ ] Parallel processing for multi-page PDFs
- [ ] OCR confidence scoring
- [ ] Automatic language detection
- [ ] GPU acceleration for preprocessing
- [ ] Caching of OCR results
- [ ] Advanced layout analysis
