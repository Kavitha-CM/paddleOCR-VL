import streamlit as st
import requests
import json
import fitz  # PyMuPDF
import os

# Configure page layout
st.set_page_config(layout="wide", page_title="PaddleOCR-VL Extractor")

# Configuration for backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Custom styling injection
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* Apply font globally */
html, body, [class*="css"], .stMarkdown, p, div, span, h1, h2, h3, h4, h5, h6, button, input {
    font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif !important;
}

/* App Background Gradient */
.stApp {
    background: radial-gradient(circle at 50% 50%, #0f172a 0%, #020617 100%) !important;
    color: #f8fafc !important;
}

/* Premium Main Header card */
.main-header-card {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 2.2rem 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.4);
    text-align: center;
}

.main-header-card h1 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important;
    font-size: 2.5rem !important;
    background: linear-gradient(to right, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 0.6rem 0 !important;
    padding: 0 !important;
}

.main-header-card p {
    color: #94a3b8;
    font-size: 1.1rem;
    margin: 0 !important;
    font-weight: 400;
}

/* Glassmorphic columns containers */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(15, 23, 42, 0.5) !important;
    backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 16px !important;
    padding: 1.8rem !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.25) !important;
    transition: transform 0.3s ease, border-color 0.3s ease !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(99, 102, 241, 0.2) !important;
}

/* Scrollbar customization */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: rgba(2, 6, 23, 0.4);
}
::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.25);
    border-radius: 99px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(168, 85, 247, 0.45);
}

/* Premium Primary Button Styling */
div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    border-radius: 10px !important;
    padding: 0.75rem 1.8rem !important;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.35) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    width: 100% !important;
}

div[data-testid="stButton"] button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(99, 102, 241, 0.5) !important;
}

div[data-testid="stButton"] button[kind="primary"]:active {
    transform: translateY(1px) !important;
}

/* File Uploader custom styling */
div[data-testid="stFileUploader"] {
    border: 2px dashed rgba(99, 102, 241, 0.2) !important;
    border-radius: 12px !important;
    background: rgba(15, 23, 42, 0.3) !important;
    padding: 1.5rem !important;
    transition: all 0.3s ease !important;
}
div[data-testid="stFileUploader"]:hover {
    border-color: rgba(99, 102, 241, 0.6) !important;
    background: rgba(99, 102, 241, 0.02) !important;
}

/* DataFrame custom border */
.stDataFrame {
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 10px !important;
    background: rgba(2, 6, 23, 0.2) !important;
}

/* Subheadings and headings styling */
h2, h3, h4 {
    color: #f1f5f9 !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}

/* Expander custom look */
div[data-testid="stExpander"] {
    background: rgba(15, 23, 42, 0.3) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 10px !important;
}

/* Success/Error alert styling */
div[data-testid="stNotification"] {
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
}

/* Sidebar override if any */
section[data-testid="stSidebar"] {
    background-color: #0b0f19 !important;
}
</style>
<div class="main-header-card">
    <h1>PaddleOCR-VL Document Extractor Pipeline</h1>
    <p>Upload a scanned document or image to extract structured key-value pairs, tables, lists, and paragraphs using advanced OCR-VL parsing.</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state for results
if "result" not in st.session_state:
    st.session_state["result"] = None

# Show the extracted document title prominently at the top
if st.session_state["result"]:
    doc_title = st.session_state["result"]["data"].get("document_title")
    if doc_title:
        st.subheader(f"📄 {doc_title}")

# Define 3 equal columns
col1, col2, col3 = st.columns(3)

# Function to render PDF pages as images using PyMuPDF
def display_pdf(file_bytes):
    """Convert each PDF page to a PNG image and display with st.image().
    This avoids the ~2 MB browser data-URI limit that causes large PDFs
    to render as a blank iframe."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = len(doc)
    st.caption(f"📄 {total_pages} page(s)")
    for page_num in range(total_pages):
        page = doc[page_num]
        # Render at 1.5x zoom for crisp text (default 72 dpi → 108 dpi)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_bytes = pix.tobytes("png")
        st.image(img_bytes, caption=f"Page {page_num + 1}", use_container_width=True)
    doc.close()

# Note: We must process the uploader first so the file is available to col1,
# but we write it into col2 so it appears in the middle.

# ---------------------------------------------------------
# MIDDLE COLUMN: Controls and JSON Output
# ---------------------------------------------------------
with col2:
    st.header("Controls & Output")
    with st.container(height=800, border=True):
        # Upload area
        uploaded_file = st.file_uploader("Upload Image or PDF", type=["pdf", "png", "jpg", "jpeg"])
        
        # Extract Button
        if st.button("Extract Data", type="primary", use_container_width=True) and uploaded_file is not None:
            with st.spinner("Processing document... This may take a moment."):
                try:
                    # Send to FastAPI
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    response = requests.post(f"{BACKEND_URL}/process-document", files=files)
                    
                    if response.status_code == 200:
                        st.session_state["result"] = response.json()
                        st.success(f"Extracted in {st.session_state['result']['process_time_seconds']}s")
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error(f"Could not connect to backend at {BACKEND_URL}. Please ensure the FastAPI server is running.")

        st.divider()
        
        # JSON Output Viewer
        st.subheader("Raw JSON Output")
        if st.session_state["result"]:
            # Expanded by default so the user can just scroll the container
            with st.expander("View Full Structured JSON", expanded=True):
                st.code(json.dumps(st.session_state["result"]["data"], indent=2, ensure_ascii=False), language="json", wrap_lines=True)
        else:
            st.info("Upload and extract a document to see JSON here.")

# ---------------------------------------------------------
# LEFT COLUMN: Document Viewer
# ---------------------------------------------------------
with col1:
    st.header("Document Viewer")
    with st.container(height=800, border=True):
        if uploaded_file is not None:
            file_type = uploaded_file.type
            if "pdf" in file_type:
                display_pdf(uploaded_file.getvalue())
            else:
                st.image(uploaded_file, use_container_width=True)
        else:
            st.info("Uploaded document will preview here.")

# ---------------------------------------------------------
# RIGHT COLUMN: Tabular / Structured Data Viewer
# ---------------------------------------------------------
with col3:
    st.header("Extracted Data")
    with st.container(height=800, border=True):
        if st.session_state["result"]:
            data = st.session_state["result"]["data"]
            
            # 1. Document-level Key-Values
            if data.get("document_key_values"):
                st.markdown("### Document Metadata")
                kv_list = [{"Key": k, "Value": ", ".join(v) if isinstance(v, list) else v} 
                           for k, v in data["document_key_values"].items()]
                if kv_list:
                    st.dataframe(kv_list, use_container_width=True, hide_index=True)
                    
            # 3. Iterate over Pages
            for page in data.get("pages", []):
                st.markdown(f"## Page {page.get('page_no', 1)}")
                st.markdown("---")
                
                # Combine sections and unassigned for display
                all_sections = page.get("sections", {})
                if any(page.get("unassigned", {}).values()):
                    all_sections["Unassigned Content"] = page["unassigned"]
                    
                for section_name, section_content in all_sections.items():
                    if section_name != "Unassigned Content":
                        st.markdown(f"### {section_name}")
                    else:
                        st.markdown(f"### *{section_name}*")
                    
                    # Key-Values
                    if section_content.get("key_values"):
                        kv_list = [{"Key": k, "Value": ", ".join(v) if isinstance(v, list) else v} 
                                   for k, v in section_content["key_values"].items()]
                        st.dataframe(kv_list, use_container_width=True, hide_index=True)
                        
                    # Tables
                    for idx, table in enumerate(section_content.get("tables", [])):
                        st.markdown(f"**Table {idx+1}**")
                        
                        # Table Metadata
                        if table.get("metadata"):
                            st.caption("Table Metadata:")
                            meta_df = [{"Key": k, "Value": v} for k, v in table["metadata"].items()]
                            st.dataframe(meta_df, use_container_width=True, hide_index=True)
                        
                        # Table Rows
                        if table.get("rows"):
                            st.dataframe(table["rows"], use_container_width=True, hide_index=True)
                            
                        # Table Summary
                        if table.get("summary"):
                            st.caption("Table Summary:")
                            sum_df = [{"Key": k, "Value": v} for k, v in table["summary"].items()]
                            st.dataframe(sum_df, use_container_width=True, hide_index=True)
                    
                    # Paragraphs
                    if section_content.get("paragraphs"):
                        st.markdown("**Text Content:**")
                        for p in section_content["paragraphs"]:
                            st.markdown(f"> {p}")
                            
                    # Lists
                    if section_content.get("list_items"):
                        st.markdown("**Lists:**")
                        for l in section_content["list_items"]:
                            st.markdown(f"- {l}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.info("Structured data will be formatted here after extraction.")
