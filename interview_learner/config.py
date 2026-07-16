from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Learning stages: fraction of answer text kept visible (rest becomes cloze gaps).
STAGE_VISIBILITY = {
    0: 1.0,   # first pass — read full Q&A
    1: 0.75,
    2: 0.50,
    3: 0.25,
}

PASS_THRESHOLD = 70  # minimum score (0-100) to advance a stage

# SM-2 spaced repetition defaults
SM2_DEFAULT_EF = 2.5
SM2_MIN_EF = 1.3

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = PROJECT_ROOT / "questions"
PROGRESS_DB = PROJECT_ROOT / "data" / "progress.db"


@dataclass
class AppSettings:
    questions_dir: Path = QUESTIONS_DIR
    ollama_url: str = DEFAULT_OLLAMA_URL
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    use_ollama_cloze: bool = False
    use_ollama_grading: bool = False
    pass_threshold: int = PASS_THRESHOLD
