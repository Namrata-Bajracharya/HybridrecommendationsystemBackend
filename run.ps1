# Activate the virtual environment
& .\.venv\Scripts\Activate.ps1

# Start the FastAPI application
uvicorn app.main:app --reload