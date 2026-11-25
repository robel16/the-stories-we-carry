
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORYBOARD = PROJECT_ROOT / "storyboard.json"
DEFAULT_SCHEMA = PROJECT_ROOT / "schema" / "storyboard.schema.json"


def load_storyboard(path: Path = DEFAULT_STORYBOARD) -> dict[str, Any]:
    """Load a storyboard JSON file."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise ValueError(f"Storyboard file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {path}, line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError("Storyboard root must be a JSON object.")

    return data


def load_schema(path: Path = DEFAULT_SCHEMA) -> dict[str, Any]:
    """Load the JSON Schema used to validate storyboards."""
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise ValueError(f"Storyboard schema not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid schema JSON: {exc}") from exc
