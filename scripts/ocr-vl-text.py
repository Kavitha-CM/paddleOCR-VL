from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from paddleocr import PaddleOCRVL


TABLE_LABELS = {"table"}


def table_to_text(html):
    import re
    html = re.sub(r'<br\s*/?>', ' ', html)          # <br> → space
    html = re.sub(r'\\n', ' ', html)                # literal \n → space
    html = re.sub(r'\s+', ' ', html)                # collapse whitespace

    class _T(HTMLParser):
        def __init__(self):
            super().__init__()
            self.rows = []
            self.current_row = []
            self.in_td = False
        def handle_starttag(self, tag, attrs):
            if tag == "td":
                self.in_td = True
                self.current_row.append("")
        def handle_endtag(self, tag):
            if tag == "td":
                self.in_td = False
            elif tag == "tr":
                if self.current_row:
                    self.rows.append(self.current_row)
                    self.current_row = []
        def handle_data(self, data):
            if self.in_td and data.strip():
                if self.current_row[-1]:
                    self.current_row[-1] += " " + data.strip()
                else:
                    self.current_row[-1] = data.strip()
    p = _T()
    p.feed(html)
    return "\n".join(" | ".join(row) for row in p.rows)


class DocumentParser:
    def __init__(self):
        self.pipeline = PaddleOCRVL(pipeline_version="v1.6")

    def parse(self, file_path: str):
        results = self.pipeline.predict(file_path)
        output_lines = []

        for page_num, page in enumerate(results, start=1):
            output_lines.append(f"===== PAGE {page_num} =====")

            try:
                blocks = page["parsing_res_list"]
            except (TypeError, KeyError):
                blocks = getattr(page, "parsing_res_list", [])

            for block in blocks:
                if isinstance(block, dict):
                    label = block.get("block_label", "")
                    content = block.get("block_content", "")
                else:
                    label = getattr(block, "block_label", getattr(block, "label", ""))
                    content = getattr(block, "block_content", getattr(block, "content", ""))

                content = unescape(str(content)).strip()

                if not content:
                    continue

                if label in TABLE_LABELS:
                    output_lines.append(table_to_text(content))
                else:
                    output_lines.append(content)

        full_text = "\n".join(output_lines)
        Path("output_9.txt").write_text(full_text, encoding="utf-8")
        print(full_text)
        return full_text


if __name__ == "__main__":
    parser = DocumentParser()
    parser.parse(r"C:\Users\Dell\Desktop\paddleOCR-VL\data\sv600_c_automatic.pdf")
