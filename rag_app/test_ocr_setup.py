"""
OCR Integration Test Script
Tests the OCR functionality before running the full RAG application.
"""

import sys
from pathlib import Path

def test_imports():
    """Test if all required packages are installed."""
    print("=" * 60)
    print("Testing Package Imports...")
    print("=" * 60)
    
    packages = {
        'pytesseract': 'pytesseract',
        'pdf2image': 'pdf2image',
        'PIL': 'Pillow',
        'cv2': 'opencv-python',
        'numpy': 'numpy'
    }
    
    all_ok = True
    for module, package in packages.items():
        try:
            __import__(module)
            print(f"✅ {package:20} - Installed")
        except ImportError:
            print(f"❌ {package:20} - NOT INSTALLED")
            all_ok = False
    
    return all_ok


def test_system_tools():
    """Test if Tesseract and Poppler are available."""
    print("\n" + "=" * 60)
    print("Testing System Tools...")
    print("=" * 60)
    
    # Test Tesseract
    tesseract_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if tesseract_path.exists():
        print(f"✅ Tesseract found at: {tesseract_path}")
        tesseract_ok = True
    else:
        print(f"❌ Tesseract NOT found at: {tesseract_path}")
        print("   Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        tesseract_ok = False
    
    # Test Poppler
    poppler_path = Path(r"A:\Tesseract11\Release-25.12.0-0\poppler-25.12.0\Library\bin")
    pdfinfo_exe = poppler_path / "pdfinfo.exe"
    
    if pdfinfo_exe.exists():
        print(f"✅ Poppler found at: {poppler_path}")
        poppler_ok = True
    else:
        print(f"❌ Poppler NOT found at: {poppler_path}")
        print("   Download from: https://github.com/oschwartz10612/poppler-windows/releases")
        poppler_ok = False
    
    return tesseract_ok and poppler_ok


def test_ocr_processor():
    """Test OCR processor initialization."""
    print("\n" + "=" * 60)
    print("Testing OCR Processor...")
    print("=" * 60)
    
    try:
        from backend.ocr_utils import OCRProcessor
        
        ocr = OCRProcessor()
        print("✅ OCR Processor initialized successfully!")
        print(f"   Tesseract: {ocr.tesseract_path}")
        print(f"   Poppler:   {ocr.poppler_path}")
        return True
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   Make sure you're in the correct directory (rag_app)")
        return False
    except Exception as e:
        print(f"❌ Initialization Error: {e}")
        return False


def test_tesseract_version():
    """Test Tesseract OCR version."""
    print("\n" + "=" * 60)
    print("Testing Tesseract Version...")
    print("=" * 60)
    
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract Version: {version}")
        return True
    except Exception as e:
        print(f"❌ Error getting Tesseract version: {e}")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "OCR INTEGRATION TEST" + " " * 23 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Run tests
    results.append(("Package Imports", test_imports()))
    results.append(("System Tools", test_system_tools()))
    results.append(("OCR Processor", test_ocr_processor()))
    results.append(("Tesseract Version", test_tesseract_version()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} - {test_name}")
    
    print("=" * 60)
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! OCR integration is ready to use.")
        print("\nNext steps:")
        print("1. Start the RAG backend: uvicorn backend.main:app --reload")
        print("2. Upload an image or PDF to test OCR")
        print("3. Query the RAG system with questions about the content")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print("\nInstallation guide:")
        print("1. Install missing Python packages: pip install -r backend/requirements.txt")
        print("2. Install Tesseract-OCR from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("3. Download Poppler from: https://github.com/oschwartz10612/poppler-windows/releases")
    
    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
