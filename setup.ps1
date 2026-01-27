# PDF RAG - Windows Setup Script


Write-Host "=== PDF RAG Setup ===" -ForegroundColor Cyan

# Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python not found. Install from https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "Python: $((python --version))" -ForegroundColor Green

# Backend setup
Write-Host "`nCreating backend venv..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\backend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend setup
Write-Host "`nCreating frontend venv..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\frontend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

Write-Host "`n=== Setup complete! ===" -ForegroundColor Green
Write-Host @"

Start the system:

1. Terminal 1 (Backend):
   cd "$PSScriptRoot\backend"
   .\venv\Scripts\Activate.ps1
   uvicorn app.main:app --reload

2. Terminal 2 (Frontend):
   cd "$PSScriptRoot\frontend"
   .\venv\Scripts\Activate.ps1
   streamlit run app.py

3. Open: http://localhost:8501

"@
