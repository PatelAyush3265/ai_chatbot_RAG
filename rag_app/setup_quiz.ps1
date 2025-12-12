# Quiz Generator - Complete Setup & Fix Script
# Run this in PowerShell with your virtual environment activated

Write-Host "🔧 QUIZ GENERATOR - DEPENDENCY FIX & SETUP" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

# Step 1: Fix the dependency conflict
Write-Host "`n📦 Step 1: Fixing sentence-transformers compatibility issue..." -ForegroundColor Yellow
Write-Host "Problem: sentence-transformers 2.2.2 is incompatible with modern huggingface_hub" -ForegroundColor Red
Write-Host "Solution: Upgrading to sentence-transformers 2.7.0" -ForegroundColor Green

pip install --upgrade sentence-transformers==2.7.0

# Step 2: Install quiz-specific dependencies
Write-Host "`n📦 Step 2: Installing quiz generator dependencies..." -ForegroundColor Yellow
pip install PyPDF2==3.0.1 rank-bm25==0.2.2 python-dotenv==1.0.0

# Step 3: Verify installations
Write-Host "`n✅ Step 3: Verifying installations..." -ForegroundColor Yellow
python -c "import sentence_transformers; print(f'✓ sentence-transformers: {sentence_transformers.__version__}')"
python -c "import PyPDF2; print(f'✓ PyPDF2: {PyPDF2.__version__}')"
python -c "import rank_bm25; print('✓ rank-bm25: installed')"
python -c "from dotenv import load_dotenv; print('✓ python-dotenv: installed')"

# Step 4: Check for .env file
Write-Host "`n🔑 Step 4: Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "⚠️  .env file not found. Creating from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
    Write-Host "✓ Created .env file. Please update with your API keys." -ForegroundColor Green
}

# Step 5: Start the backend server
Write-Host "`n🚀 Step 5: Starting backend server..." -ForegroundColor Yellow
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Cyan
Write-Host ""

uvicorn backend.main:app --reload --port 8000
