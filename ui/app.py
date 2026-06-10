import streamlit as st
import requests
import json
import fitz  # PyMuPDF

# Configure page layout
st.set_page_config(layout="wide", page_title="PaddleOCR-VL Extractor")

st.title("PaddleOCR-VL Document Extractor Pipeline")

# Initialize session state for results
if "result" not in st.session_state:
    st.session_state["result"] = None

# Show the extracted document title prominently at the top
if st.session_state["result"]:
    doc_title = st.session_state["result"]["data"].get("document_title")
    if doc_title:
        st.subheader(f"\U0001f4c4 {doc_title}")

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
                    response = requests.post("http://localhost:8000/process-document", files=files)
                    
                    if response.status_code == 200:
                        st.session_state["result"] = response.json()
                        st.success(f"Extracted in {st.session_state['result']['process_time_seconds']}s")
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to backend. Please start the FastAPI server: `python -m uvicorn api.main:app`")

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
