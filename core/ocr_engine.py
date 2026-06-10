from pathlib import Path
import time

from paddleocr import PaddleOCRVL


class DocumentParser:
    def __init__(self):
        start = time.perf_counter()

        self.pipeline = PaddleOCRVL(
            pipeline_version="v1.6"
        )

        print(
            f"[TIMING] Model loaded in "
            f"{time.perf_counter() - start:.2f}s"
        )

    def parse(self, file_path: str):
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Measure prediction time
        start = time.perf_counter()

        results = self.pipeline.predict(file_path)

        predict_time = time.perf_counter() - start

        print(
            f"[TIMING] predict() completed in "
            f"{predict_time:.2f}s"
        )

        # Measure per-page processing
        for idx, result in enumerate(results):
            print(f"\n===== PAGE {idx + 1} =====")

            page_start = time.perf_counter()

            result.print()

            print_time = time.perf_counter() - page_start

            json_start = time.perf_counter()

            result.save_to_json(
                save_path=str(output_dir)
            )

            json_time = time.perf_counter() - json_start

            md_start = time.perf_counter()

            result.save_to_markdown(
                save_path=str(output_dir)
            )

            md_time = time.perf_counter() - md_start

            total_page_time = time.perf_counter() - page_start

            print(
                f"[TIMING] Page {idx+1}: "
                f"print={print_time:.2f}s, "
                f"json={json_time:.2f}s, "
                f"markdown={md_time:.2f}s, "
                f"total={total_page_time:.2f}s"
            )

        return results


if __name__ == "__main__":
    total_start = time.perf_counter()

    parser = DocumentParser()

    parser.parse(
        r"C:\Users\Dell\Desktop\paddleOCR-VL\data\5- Land and Lease documents-8-10.pdf"
    )

    print(
        f"\n[TIMING] Entire run took "
        f"{time.perf_counter() - total_start:.2f}s"
    )