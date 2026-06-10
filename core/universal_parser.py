import json
import re

class UniversalDocumentParser:
    def __init__(self):
        self.KV_COLON_PATTERN = re.compile(r"^\s*([^:\n]{1,100})\s*:\s*(.+?)\s*$")
        self.KV_SPACE_PATTERN = re.compile(r"^([A-Za-z][A-Za-z0-9.\-/ ]{2,50})\s+([0-9A-Za-z][0-9A-Za-z.\-/]+)$")

    def clean_text(self, text):
        if not text:
            return ""
        return text.strip()

    def normalize_text(self, text):
        if not text:
            return ""
        return " ".join(str(text).split())

    def parse_multiline_kv(self, text):
        """
        Parses multi-line text to extract Key-Value pairs.
        Only explicit 'Key: Value' lines are extracted.
        Non-matching lines are returned as leftover text.
        Returns: (kv_pairs_list, leftover_lines_list) or (None, None)
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None, None

        results = []
        leftover = []

        for line in lines:
            match = self.KV_COLON_PATTERN.match(line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                results.append({"key": key, "value": value})
            else:
                leftover.append(line)

        if results:
            return results, leftover
        return None, None

    def get_or_create_section(self, target_node, section_name):
        if section_name not in target_node["sections"]:
            target_node["sections"][section_name] = {
                "paragraphs": [],
                "list_items": [],
                "key_values": {},
                "tables": []
            }
        return target_node["sections"][section_name]

    def add_kv_to_dict(self, target_dict, key, value):
        if key not in target_dict:
            target_dict[key] = value
        else:
            existing = target_dict[key]
            if not isinstance(existing, list):
                existing = [existing]
            existing.append(value)
            target_dict[key] = existing

    def parse(self, data):
        result = {
            "document_title": None,
            "document_key_values": {},
            "pages": [],
            "metadata": {
                "input_path": data.get("input_path"),
                "total_pages": data.get("total_pages")
            }
        }

        current_section = None
        current_subheader = None

        for page in data.get("pages", []):
            page_no = (page.get("page_index") or 0) + 1
            print(f"[{result['metadata']['input_path']}] Processing Page {page_no} / {result['metadata']['total_pages']}...")

            page_node = {
                "page_no": page_no,
                "sections": {},
                "unassigned": {
                    "paragraphs": [],
                    "list_items": [],
                    "tables": []
                }
            }
            result["pages"].append(page_node)

            blocks = sorted(
                page.get("blocks", []),
                key=lambda b: (
                    b.get("bbox", [0, 0, 0, 0])[1],
                    b.get("bbox", [0, 0, 0, 0])[0]
                )
            )

            for block in blocks:
                block_type = block.get("type")
                raw_content = block.get("content", "")
                content_clean = self.clean_text(raw_content)

                # ------------------------
                # TABLE
                # ------------------------
                if block_type == "table":
                    current_subheader = None
                    rows = block.get("rows") or block.get("line_items") or []
                    table_data = {
                        "headers": block.get("headers", []),
                        "rows": rows
                    }
                    if block.get("metadata"):
                        table_data["metadata"] = block["metadata"]
                    if block.get("summary"):
                        table_data["summary"] = block["summary"]
                    if current_section:
                        self.get_or_create_section(page_node, current_section)["tables"].append(table_data)
                    else:
                        page_node["unassigned"]["tables"].append(table_data)
                    continue

                if not content_clean:
                    continue

                # ------------------------
                # TITLE (Section)
                # ------------------------
                if block_type == "title":
                    normalized_title = self.normalize_text(content_clean)
                    
                    if normalized_title.endswith(":"):
                        current_subheader = normalized_title[:-1].strip()
                        continue
                    else:
                        if result["document_title"] is None:
                            result["document_title"] = normalized_title
                        current_section = normalized_title
                        current_subheader = None
                        self.get_or_create_section(page_node, current_section)
                    continue

                # ------------------------
                # LIST ITEM
                # ------------------------
                if block_type == "list_item":
                    if current_subheader and current_section:
                        target_dict = self.get_or_create_section(page_node, current_section)["key_values"]
                        self.add_kv_to_dict(target_dict, current_subheader, content_clean)
                        current_subheader = None  # Reset to prevent swallowing following items
                    elif current_section:
                        self.get_or_create_section(page_node, current_section)["list_items"].append(content_clean)
                    else:
                        page_node["unassigned"]["list_items"].append(content_clean)
                    continue

                # ------------------------
                # PARAGRAPH / KEY-VALUES
                # ------------------------
                if block_type in ("paragraph", "footnote"):
                    kv_pairs, leftover = self.parse_multiline_kv(raw_content)
                    
                    if kv_pairs:
                        for kv in kv_pairs:
                            target_dict = (self.get_or_create_section(page_node, current_section)["key_values"] 
                                           if current_section else result["document_key_values"])
                            self.add_kv_to_dict(target_dict, kv["key"], kv["value"])
                        # Store leftover non-KV lines as paragraphs
                        if leftover:
                            for lo in leftover:
                                normalized = self.normalize_text(lo)
                                if not normalized:
                                    continue
                                if len(normalized) < 60 and normalized.endswith(":"):
                                    current_subheader = normalized[:-1].strip()
                                elif current_subheader and current_section:
                                    target_dict = self.get_or_create_section(page_node, current_section)["key_values"]
                                    self.add_kv_to_dict(target_dict, current_subheader, normalized)
                                    current_subheader = None  # Reset to prevent swallowing following paragraphs
                                elif current_section:
                                    self.get_or_create_section(page_node, current_section)["paragraphs"].append(normalized)
                                else:
                                    page_node["unassigned"]["paragraphs"].append(normalized)
                    else:
                        lines = [line.strip() for line in raw_content.splitlines() if line.strip()]
                        for lo in lines:
                            normalized = self.normalize_text(lo)
                            if not normalized:
                                continue
                            if len(normalized) < 60 and normalized.endswith(":"):
                                current_subheader = normalized[:-1].strip()
                            elif current_subheader and current_section:
                                target_dict = self.get_or_create_section(page_node, current_section)["key_values"]
                                self.add_kv_to_dict(target_dict, current_subheader, normalized)
                                current_subheader = None  # Reset to prevent swallowing following paragraphs
                            elif current_section:
                                self.get_or_create_section(page_node, current_section)["paragraphs"].append(normalized)
                            else:
                                page_node["unassigned"]["paragraphs"].append(normalized)
                    continue

        return result

if __name__ == "__main__":
    INPUT_FILE = r"C:\Users\Dell\Desktop\paddleOCR-VL\output\structured_combined_5- Land and Lease documents-8-10.json"
    OUTPUT_FILE = "universal_output_final_ta.json"
    
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        parser = UniversalDocumentParser()
        result = parser.parse(data)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Successfully processed {INPUT_FILE} -> {OUTPUT_FILE}")
    except FileNotFoundError:
        print(f"File not found: {INPUT_FILE}")
