import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas import ReviewInput


settings = get_settings()


def stable_hash(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(("reviewer_", "reviewee_", "hash_")):
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"hash_{digest}"


def normalize_record(record: dict[str, Any]) -> ReviewInput:
    source_payload = dict(record.get("source_payload") or {})
    if not source_payload:
        source_payload = {k: v for k, v in record.items() if k not in ReviewInput.model_fields}

    return ReviewInput(
        project_name=str(record.get("project_name") or record.get("project") or "").strip().lower(),
        campus=str(record.get("campus") or settings.default_campus).strip().lower(),
        language=str(record.get("language") or settings.default_language).strip().lower(),
        reviewer_id_hash=stable_hash(record.get("reviewer_id_hash") or record.get("reviewer_id")),
        reviewee_id_hash=stable_hash(record.get("reviewee_id_hash") or record.get("reviewee_id")),
        score=record.get("score"),
        passed=record.get("passed"),
        created_at=record.get("created_at"),
        raw_text=str(record.get("raw_text") or record.get("comment") or record.get("feedback") or "").strip(),
        source_type=str(record.get("source_type") or "api_json"),
        source_payload=source_payload,
    )


def load_records(path: str | Path) -> list[ReviewInput]:
    source = Path(path)
    if source.suffix.lower() == ".jsonl":
        return [
            normalize_record(json.loads(line))
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    payload = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("reviews", [])
    if not isinstance(payload, list):
        raise ValueError("Ingest file must be a JSON list, a JSON object with reviews, or JSONL.")
    return [normalize_record(item) for item in payload]
