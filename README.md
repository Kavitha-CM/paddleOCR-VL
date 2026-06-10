# PaddleOCR-VL Pipeline

A complete Document Extraction pipeline built with PaddleOCR-VL, FastAPI, and Streamlit. This project processes scanned documents and extracts structured hierarchical data including titles, paragraphs, lists, and tables.

## Project Structure
- `api/`: FastAPI backend for document processing.
- `ui/`: Streamlit frontend for uploading and viewing extracted data.
- `core/`: Core OCR engine and parsing logic using PaddleOCR-VL.
- `scripts/`: Testing and sample scripts.

## Requirements
Ensure you have the dependencies installed:
```bash
pip install -r requirements.txt
```

## How to Run

1. **Start the FastAPI Backend:**
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

2. **Start the Streamlit UI:**
```bash
python -m streamlit run ui/app.py
```
