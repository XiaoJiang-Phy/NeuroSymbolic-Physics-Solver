# PowerShell script to setup the neuro-physics conda environment

Write-Host "--- Starting Environment Configuration for NeuroSymbolic-Physics-Solver ---" -ForegroundColor Cyan

# Check if conda is available
if (!(Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Error "Conda not found. Please install Anaconda or Miniconda."
    exit 1
}

# Create the environment from environment.yml
Write-Host "Creating conda environment 'neuro-physics'..." -ForegroundColor Yellow
conda env create -f environment.yml

if ($LASTEXITCODE -ne 0) {
    Write-Host "Environment creation failed or already exists. Attempting update..." -ForegroundColor Gray
    conda env update -f environment.yml
}

Write-Host "--- Configuration Complete ---" -ForegroundColor Green
Write-Host "To activate the environment, run:"
Write-Host "conda activate neuro-physics" -ForegroundColor Magenta
