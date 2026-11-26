import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_LOG_PATH = PROJECT_ROOT / "runs.jsonl"
CACHE_FILE_PATH = PROJECT_ROOT / "outputs" / ".stage_cache.json"


def compute_input_hash(payload: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash of a JSON-serializable payload."""
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def log_run(
    stage: str,
    model: str,
    status: str,
    latency_seconds: float,
    scene_id: str | None = None,
    parameters: dict[str, Any] | None = None,
    seed: int | None = None,
    estimated_cost_usd: float = 0.0,
    output_path: str | None = None,
    note: str | None = None,
    log_path: Path = RUNS_LOG_PATH,
) -> None:
    """Append a structured model/stage execution record to runs.jsonl."""
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "scene_id": scene_id,
        "model": model,
        "parameters": parameters or {},
        "seed": seed,
        "latency_seconds": round(latency_seconds, 3),
        "estimated_cost_usd": round(estimated_cost_usd, 6),
        "status": status,
        "output_path": output_path,
    }
    if note:
        record["note"] = note

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class StageCache:
    """Simple JSON-backed input-hash cache so unchanged shots are skipped."""

    def __init__(self, cache_path: Path = CACHE_FILE_PATH) -> None:
        self.cache_path = cache_path
        self._data: dict[str, str] = {}
        if self.cache_path.is_file():
            try:
                self._data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def is_fresh(self, key: str, input_hash: str, output_path: Path) -> bool:
        """Return True if output exists and its recorded input hash matches."""
        return output_path.is_file() and self._data.get(key) == input_hash

    def update(self, key: str, input_hash: str) -> None:
        """Persist the latest input hash for a stage/shot key."""
        self._data[key] = input_hash
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self._data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
