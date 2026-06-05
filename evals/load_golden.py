import json
from pathlib import Path
from typing import Any


GOLDEN_PATH = Path(__file__).parent / "golden_queries.jsonl"


def load_golden_queries(path: Path = GOLDEN_PATH) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} in {path}: {exc}"
                ) from exc

    return records