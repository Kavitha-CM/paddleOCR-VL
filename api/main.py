import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn
import time
import traceback
import json

# Import the individual steps
from core.ocr_engine import DocumentParser as OCRParser
from core.paddle_parser import parse_page
from core.universal_parser import UniversalDocumentParser

app = FastAPI(title="PaddleOCR-VL Pipeline API")

# Initialize models lazily
ocr_pipeline = None
universal_parser = None

def get_ocr_pipeline():
    global ocr_pipeline
    if ocr_pipeline is None:
        print("Loading OCR Pipeline...")
        ocr_pipeline = OCRParser()
    return ocr_pipeline

def get_universal_parser():
    global universal_parser
    if universal_parser is None:
        print("Loading Universal Parser...")
        universal_parser = UniversalDocumentParser()
    return universal_parser

def is_scanned(file_path: Path) -> bool:
    """
    Check if a document is scanned.
    Currently, we treat all images as scanned.
    For PDFs, ideally you would check for a text layer using fitz (PyMuPDF).
    We'll default to True to trigger the OCR pipeline as requested.
    """
    if file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
        return True
    
    # Placeholder for PDF text extraction check. 
    # For now, we assume all uploaded PDFs need OCR processing.
    return True

@app.post("/process-document")
async def process_document(file: UploadFile = File(...)):
    start_time = time.time()
    
    # Save the uploaded file temporarily
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    temp_path = upload_dir / file.filename
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"File uploaded: {temp_path}")
        
        # 1. Check if scanned
        if not is_scanned(temp_path):
            return {"status": "error", "message": "Document is not scanned. Text extraction directly from PDF is not implemented yet."}
            
        # 2. Run OCR (returns a list of page results)
        print("Running OCR...")
        ocr = get_ocr_pipeline()
        results = ocr.pipeline.predict(str(temp_path))
        
        # 3. Store in a single page structure (like native PaddleOCR-VL)
        print("Consolidating pages via JSON serialization...")
        parsed_pages = []
        
        # Create a temporary directory for this request's OCR JSON output
        temp_out_dir = upload_dir / f"out_{start_time}"
        temp_out_dir.mkdir(exist_ok=True)
        
        for idx, result in enumerate(results):
            # Save the result to JSON to guarantee exact PaddleOCR dict format
            result.save_to_json(str(temp_out_dir))
            
        # Read the saved JSONs back
        json_files = sorted(temp_out_dir.glob("*.json"))
        
        # Make sure they are sorted by page index correctly
        # PaddleOCR usually names them like: original_name_0_res.json
        for j_file in json_files:
            with open(j_file, "r", encoding="utf-8") as f:
                raw_page = json.load(f)
                
                # 4. Run PaddleOCR Parser
                structured_page = parse_page(raw_page)
                parsed_pages.append(structured_page)
                
        # Sort parsed pages securely by their page_index
        parsed_pages.sort(key=lambda p: p.get("page_index", 0))
            
        # Combine pages into the intermediate structured format
        intermediate_structured = {
            "input_path": str(temp_path),
            "total_pages": len(parsed_pages),
            "pages": parsed_pages
        }
        
        # 5. Run Universal Parser
        print("Running Universal Parser...")
        univ_parser = get_universal_parser()
        final_json = univ_parser.parse(intermediate_structured)
        
        # Cleanup temp JSON dir
        try:
            shutil.rmtree(temp_out_dir)
        except Exception as e:
            print(f"Cleanup warning: {e}")
        
        process_time = time.time() - start_time
        print(f"Processing complete in {process_time:.2f}s")
        
        return {
            "status": "success",
            "process_time_seconds": round(process_time, 2),
            "filename": file.filename,
            "data": final_json
        }
        
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Optional: cleanup temp file
        # if temp_path.exists():
        #     temp_path.unlink()
        pass

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
