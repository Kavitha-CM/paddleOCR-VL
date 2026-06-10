import json
import re


class DocumentNormalizer:

    KV_PATTERN = re.compile(
        r"^\s*([^:\n]{1,100})\s*:\s*(.+?)\s*$"
    )

    def clean_text(self, text):
        if not text:
            return ""

        return text.strip()

    def parse_multiline_kv(self, text):
        """
        Example:

        PO Number: PO123
        Registered Office: ABC Pvt Ltd
        Chennai
        India

        =>
        [
            {
                "key": "PO Number",
                "value": "PO123"
            },
            {
                "key": "Registered Office",
                "value": [
                    "ABC Pvt Ltd",
                    "Chennai",
                    "India"
                ]
            }
        ]
        """

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if not lines:
            return None

        results = []

        current_key = None
        current_value = []

        found = False

        for line in lines:

            match = self.KV_PATTERN.match(line)

            if match:

                found = True

                if current_key:

                    value = (
                        current_value[0]
                        if len(current_value) == 1
                        else current_value
                    )

                    results.append({
                        "key": current_key,
                        "value": value
                    })

                current_key = match.group(1).strip()

                current_value = [
                    match.group(2).strip()
                ]

            else:

                if current_key:
                    current_value.append(line)

        if current_key:

            value = (
                current_value[0]
                if len(current_value) == 1
                else current_value
            )

            results.append({
                "key": current_key,
                "value": value
            })

        if found:
            return results

        return None

    def normalize(self, data):

        output = {
            "document": {
                "titles": [],
                "key_values": {},
                "paragraphs": [],
                "list_items": [],
                "tables": []
            },
            "metadata": {
                "input_path": data.get("input_path"),
                "total_pages": data.get("total_pages")
            }
        }

        doc = output["document"]

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

                # ------------------------
                # TABLE
                # ------------------------

                if block_type == "table":

                    rows = (
                        block.get("rows")
                        or block.get("line_items")
                        or []
                    )

                    doc["tables"].append({
                        "headers": block.get(
                            "headers",
                            []
                        ),
                        "rows": rows
                    })

                    continue

                content = self.clean_text(
                    block.get("content", "")
                )

                if not content:
                    continue

                # ------------------------
                # TITLE
                # ------------------------

                if block_type == "title":

                    doc["titles"].append(
                        content
                    )

                    continue

                # ------------------------
                # LIST ITEM
                # ------------------------

                if block_type == "list_item":

                    doc["list_items"].append(
                        content
                    )

                    continue

                # ------------------------
                # MULTILINE KV
                # ------------------------

                kv_pairs = self.parse_multiline_kv(
                    content
                )

                if kv_pairs:

                    for kv in kv_pairs:

                        key = kv["key"]
                        value = kv["value"]

                        if key not in doc["key_values"]:

                            doc["key_values"][key] = value

                        else:

                            existing = (
                                doc["key_values"][key]
                            )

                            if not isinstance(
                                existing,
                                list
                            ):
                                existing = [
                                    existing
                                ]

                            existing.append(
                                value
                            )

                            doc["key_values"][
                                key
                            ] = existing

                    continue

                # ------------------------
                # PARAGRAPH
                # ------------------------

                doc["paragraphs"].append(
                    content
                )

        return output


if __name__ == "__main__":

    INPUT_FILE = r"C:\Users\Dell\Desktop\paddleOCR-VL\output\structured_Naac_appLetter 1 1_4_res.json"
    OUTPUT_FILE = "appletter_output.json"

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    normalizer = DocumentNormalizer()

    result = normalizer.normalize(data)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )