import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


SESSIONS_FILE = Path("data/sessions.jsonl")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_session_id() -> str:
    return f"sdlc-session-{uuid.uuid4()}"


def ensure_sessions_file() -> None:
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SESSIONS_FILE.exists():
        SESSIONS_FILE.write_text("", encoding="utf-8")


def save_session_record(record: Dict[str, Any]) -> Dict[str, Any]:
    ensure_sessions_file()

    if "session_id" not in record or not record["session_id"]:
        record["session_id"] = generate_session_id()

    if "created_at" not in record or not record["created_at"]:
        record["created_at"] = utc_now_iso()

    with SESSIONS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


def load_session_records(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    ensure_sessions_file()

    records: List[Dict[str, Any]] = []

    with SESSIONS_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    records = sorted(
        records,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )

    if limit:
        return records[:limit]

    return records


def get_latest_session_record(session_id: str) -> Optional[Dict[str, Any]]:
    records = load_session_records()

    for record in records:
        if record.get("session_id") == session_id:
            return record

    return None


def build_continuation_context(session_id: str) -> str:
    record = get_latest_session_record(session_id)

    if not record:
        return ""

    user_idea = record.get("user_idea", "")
    response = record.get("response", "")
    trace_id = record.get("trace_id", "")

    return f"""
Contexto persistido de sesión anterior:

Session ID:
{session_id}

Idea original:
{user_idea}

Trace ID anterior:
{trace_id}

Resultado anterior resumido:
{response[:4000]}
"""