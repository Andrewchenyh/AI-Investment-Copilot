import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from evals.schemas import GoldenQuery


GOLDEN_PATH = Path(__file__).parent / "golden_queries.jsonl"


def load_golden_queries(path: Path = GOLDEN_PATH) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                parsed_record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} in {path}: {exc}"
                ) from exc

            try:
                validated_record = GoldenQuery.model_validate(parsed_record)
            except ValidationError as exc:
                raise ValueError(
                    f"Invalid golden query schema on line {line_number} "
                    f"in {path}: {exc}"
                ) from exc

            records.append(validated_record.model_dump())

    return records
