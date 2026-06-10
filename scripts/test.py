import json
import re


KV_COLON_PATTERN = re.compile(
    r"^\s*([^:]{1,100})\s*:\s*(.+?)\s*$"
)

KV_SPACE_PATTERN = re.compile(
    r"^([A-Za-z][A-Za-z0-9.\-/ ]{2,50})\s+([0-9A-Za-z][0-9A-Za-z.\-/]+)$"
)


def normalize_text(text):
    if not text:
        return ""

    return " ".join(str(text).split())


def extract_kv(text):
    text = normalize_text(text)

    m = KV_COLON_PATTERN.match(text)
    if m:
        return {
            "key": m.group(1).strip(),
            "value": m.group(2).strip()
        }

    m = KV_SPACE_PATTERN.match(text)
    if m:
        key = m.group(1).strip()
        value = m.group(2).strip()

        if len(key.split()) <= 6:
            return {
                "key": key,
                "value": value
            }

    return None


def get_or_create_section(result, section_name):
    if section_name not in result["sections"]:
        result["sections"][section_name] = {
            "paragraphs": [],
            "list_items": [],
            "key_values": {},
            "tables": []
        }

    return result["sections"][section_name]


def transform_document(data):

    result = {
        "document_title": None,
        "document_key_values": {},
        "sections": {},
        "unassigned": {
            "paragraphs": [],
            "list_items": [],
            "tables": []
        },
        "metadata": {
            "total_pages": data.get("total_pages")
        }
    }

    current_section = None

    for page in data.get("pages", []):

        blocks = sorted(
            page.get("blocks", []),
            key=lambda b: (
                b.get("bbox", [0, 0, 0, 0])[1],
                b.get("bbox", [0, 0, 0, 0])[0]
            )
        )

        for block in blocks:

            block_type = block.get("type")
            content = normalize_text(
                block.get("content", "")
            )

            # --------------------------
            # DOCUMENT TITLE
            # --------------------------
            if (
                block_type == "title"
                and result["document_title"] is None
            ):
                result["document_title"] = content
                continue

            # --------------------------
            # SECTION TITLE
            # --------------------------
            if block_type == "title":

                current_section = content

                get_or_create_section(
                    result,
                    current_section
                )

                continue

            # --------------------------
            # TABLE
            # --------------------------
            if block_type == "table":

                table_data = {
                    "headers": block.get("headers", []),
                    "rows": block.get("rows", [])
                }

                if current_section:
                    result["sections"][
                        current_section
                    ]["tables"].append(table_data)
                else:
                    result["unassigned"][
                        "tables"
                    ].append(table_data)

                continue

            # --------------------------
            # PARAGRAPH
            # --------------------------
            if block_type == "paragraph":

                kv = extract_kv(content)

                if kv:

                    if current_section:
                        result["sections"][
                            current_section
                        ]["key_values"][
                            kv["key"]
                        ] = kv["value"]

                    else:
                        result["document_key_values"][
                            kv["key"]
                        ] = kv["value"]

                else:

                    if current_section:
                        result["sections"][
                            current_section
                        ]["paragraphs"].append(
                            content
                        )
                    else:
                        result["unassigned"][
                            "paragraphs"
                        ].append(content)

                continue

            # --------------------------
            # LIST ITEMS
            # --------------------------
            if block_type == "list_item":

                if current_section:

                    result["sections"][
                        current_section
                    ]["list_items"].append(
                        content
                    )

                else:

                    result["unassigned"][
                        "list_items"
                    ].append(content)

                continue

    return result


if __name__ == "__main__":

    with open(
        r"C:\Users\Dell\Desktop\paddleOCR-VL\output\structured_Naac_appLetter 1 1_4_res.json",
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    structured = transform_document(data)

    with open(
        "structured_output_naac_appletter_1_1_4.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            structured,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        json.dumps(
            structured,
            indent=2,
            ensure_ascii=False
        )
    )