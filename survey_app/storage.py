import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List


AnswersDict = Dict[str, List[object]]  # {"q1": [question: str, value: bool], ...}


def load_answers(path: Path) -> AnswersDict:
    try:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Basic validation to ensure expected structure
        if not isinstance(data, dict):
            return {}
        return data  # type: ignore[return-value]
    except Exception:
        # Corrupt or unreadable; start fresh
        return {}


def save_answers(path: Path, answers: AnswersDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="responses_", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(answers, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


