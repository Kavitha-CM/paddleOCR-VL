"""
PaddleOCR-VL JSON → Structured JSON Parser
Handles mixed documents: paragraphs, titles, tables, lists — all in one pass.
"""

import json
import glob
from pathlib import Path
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Block label categories (from your actual OCR output)
# ---------------------------------------------------------------------------
TITLE_LABELS    = {"doc_title", "paragraph_title"}
TEXT_LABELS     = {"text", "header", "footer"}
TABLE_LABELS    = {"table"}
SKIP_LABELS     = {"number", "footnote", 
                   "header_image", "footer_image", "aside_text"}


# ---------------------------------------------------------------------------
# Individual block parsers
# ---------------------------------------------------------------------------

def parse_title(block: dict) -> dict:
    return {
        "type": "title",
        "label": block["block_label"],        # doc_title vs paragraph_title
        "content": block["block_content"].strip(),
        "block_id": block["block_id"],
        "bbox": block["block_bbox"],
    }


def parse_text(block: dict) -> dict:
    content = block["block_content"].strip()
    # Detect bullet points
    is_bullet = content.startswith(("•", "-", "*", "·"))
    return {
        "type": "list_item" if is_bullet else "paragraph",
        "content": content.lstrip("•-*· ").strip() if is_bullet else content,
        "block_id": block["block_id"],
        "bbox": block["block_bbox"],
    }


def parse_table(block: dict) -> dict:
    """
    Parse an HTML table block. Uses `colspan` to ensure rows with merged cells
    align correctly with the headers. Returns a single table block.
    """
    html = block["block_content"]
    soup = BeautifulSoup(html, "html.parser")

    all_rows = soup.find_all("tr")
    if not all_rows:
        return {"type": "table", "headers": [], "rows": [], "block_id": block["block_id"], "bbox": block["block_bbox"]}

    # Extract headers and rows respecting colspan
    def extract_cells_with_colspan(tr):
        cells = []
        for td in tr.find_all(["td", "th"]):
            text = td.get_text(strip=True)
            colspan = int(td.get("colspan", 1))
            cells.append(text)
            # Pad empty columns for merged cells so the array length matches the grid
            for _ in range(colspan - 1):
                cells.append("")
        return cells

    first_row_cells = extract_cells_with_colspan(all_rows[0])
    
    has_th = bool(all_rows[0].find("th"))
    has_colon = any(":" in cell for cell in first_row_cells if cell)
    # A row is usually NOT a header if it contains digits (like prices, IDs, quantities)
    has_numbers = any(any(char.isdigit() for char in cell) for cell in first_row_cells if cell)
    
    if has_th or (not has_colon and not has_numbers):
        headers = first_row_cells
        data_rows = all_rows[1:]
    else:
        headers = []
        data_rows = all_rows

    rows = []
    for tr in data_rows:
        cells = extract_cells_with_colspan(tr)
        if any(cells):
            if headers and len(cells) == len(headers):
                # Standard row that aligns perfectly
                rows.append(dict(zip(headers, cells)))
            else:
                # Mismatched row (fallback to col_N)
                rows.append({f"col_{i}": v for i, v in enumerate(cells)})

    return {
        "type": "table",
        "headers": headers,
        "rows": rows,
        "block_id": block["block_id"],
        "bbox": block["block_bbox"],
    }


# ---------------------------------------------------------------------------
# Main block router
# ---------------------------------------------------------------------------

def parse_block(block: dict) -> dict | None:
    label = block.get("block_label", "")

    if label in SKIP_LABELS:
        return None
    elif label in TITLE_LABELS:
        return parse_title(block)
    elif label in TEXT_LABELS:
        return parse_text(block)
    elif label in TABLE_LABELS:
        return parse_table(block)
    else:
        # Unknown label — store as raw so nothing is lost
        return {
            "type": "unknown",
            "label": label,
            "content": block.get("block_content", ""),
            "block_id": block.get("block_id"),
            "bbox": block.get("block_bbox"),
        }


# ---------------------------------------------------------------------------
# Page parser
# ---------------------------------------------------------------------------

def parse_page(raw: dict) -> dict:
    blocks = raw.get("parsing_res_list", [])

    # Sort by spatial position (y, then x) because some blocks like tables lack block_order
    def sort_key(b):
        bbox = b.get("block_bbox", [0, 0, 0, 0])
        return (bbox[1], bbox[0])

    sorted_blocks = sorted(blocks, key=sort_key)

    parsed_blocks = []
    for block in sorted_blocks:
        result = parse_block(block)
        if result:
            parsed_blocks.append(result)

    return {
        "page_index": raw.get("page_index"),
        "page_count": raw.get("page_count"),
        "input_path": raw.get("input_path"),
        "width": raw.get("width"),
        "height": raw.get("height"),
        "blocks": parsed_blocks,
    }


# ---------------------------------------------------------------------------
# Document parser — handles multi-page (multiple JSON files from output/)
# ---------------------------------------------------------------------------

def parse_document(json_dir: str) -> dict:
    json_files = sorted(glob.glob(f"{json_dir}/*.json"))

    if not json_files:
        raise FileNotFoundError(f"No JSON files found in: {json_dir}")

    pages = []
    input_path = None

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if input_path is None:
            input_path = raw.get("input_path")

        pages.append(parse_page(raw))

    return {
        "input_path": input_path,
        "total_pages": len(pages),
        "pages": pages,
    }


# ---------------------------------------------------------------------------
# Single file parser
# ---------------------------------------------------------------------------

def parse_single_file(json_path: str) -> dict:
    """Parse one PaddleOCR-VL JSON file and return structured dict."""
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    page = parse_page(raw)
    return {
        "input_path": raw.get("input_path"),
        "total_pages": raw.get("page_count"),
        "pages": [page],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # -----------------------------------------------------------------------
    # ✏️  Set your input JSON file path here (or pass it as a CLI argument)
    # -----------------------------------------------------------------------
    if len(sys.argv) > 1:
        INPUT_JSON = sys.argv[1]          # python parse_paddleocr.py path/to/file.json
    else:
        INPUT_JSON = r"C:\Users\Dell\Desktop\paddleOCR-VL\output\scanned_GRB_Dairy_Invoice_1_res.json"  # ← change this to test a specific file

    input_path = Path(INPUT_JSON)
    if not input_path.exists():
        print(f"File not found: {INPUT_JSON}")
        sys.exit(1)

    SAVE_PATH = str(input_path.parent / f"structured_{input_path.stem}.json")

    structured = parse_single_file(INPUT_JSON)

    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=2, ensure_ascii=False)

    print(f"Structured JSON saved to : {SAVE_PATH}")
    print(f"   Source file             : {INPUT_JSON}")
    for page in structured["pages"]:
        block_types = [b["type"] for b in page["blocks"]]
        print(f"   Page {page['page_index'] + 1}: {len(page['blocks'])} blocks -> {set(block_types)}")