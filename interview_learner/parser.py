from __future__ import annotations

import hashlib
import re
from pathlib import Path

from interview_learner.models import Question

_SEPARATOR_RE = re.compile(r"^---\s*$", re.MULTILINE)

# New format:  ### Q1: Question text  /  **Answer:** answer text
_FORMAT_RE = re.compile(
    r"^###\s+Q\d+:\s*(.+?)$\s*\*\*Answer:\*\*\s*(.+?)(?=^---)",
    re.MULTILINE | re.DOTALL,
)

# Strips **A:** or **Answer:** prefix from the answer body
_ANSWER_PREFIX_RE = re.compile(r"^\*\*(?:A|Answer)\s*:\*\*\s*", re.IGNORECASE)

# Human-readable theme name mappings
_THEME_LABEL_OVERRIDES: dict[str, str] = {
    "api_rate": "API Rate Limiting",
    "db_sso": "Database SSO",
    "distributed_systems": "Distributed Systems",
    "encryption": "Encryption",
    "cqrs": "CQRS",
    "laravel": "Laravel",
    "laravel2": "Laravel II",
    "oauth": "OAuth",
    "php_ii": "PHP II",
    "symfony": "Symfony",
    "symfony_ii": "Symfony II",
}

_THEME_PREFIXES = ("en_q&a_", "q&a_")


def theme_name_from_path(path: Path) -> str:
    stem = path.stem
    for prefix in _THEME_PREFIXES:
        if stem.startswith(prefix):
            return stem[len(prefix) :]
    return stem


def theme_display_name(raw_name: str) -> str:
    """Convert a raw theme key to a human-readable label."""
    if raw_name in _THEME_LABEL_OVERRIDES:
        return _THEME_LABEL_OVERRIDES[raw_name]
    return raw_name.replace("_", " ").replace("&", "and").title()


def _make_id(theme: str, index: int, question: str) -> str:
    digest = hashlib.sha256(f"{theme}:{index}:{question}".encode()).hexdigest()[:12]
    return f"{theme}:{digest}"


_SOURCE_REF_RE = re.compile(
    r"^\*\*(?:Source|References?)\s*:\*\*.*", re.IGNORECASE | re.MULTILINE
)


def _extract_source_ref(answer: str) -> tuple[str, str]:
    """Extract **Source:** and **Reference:** lines from answer.
    Returns (clean_answer, source_text).
    """
    lines = answer.split("\n")
    source_lines: list[str] = []
    clean_lines: list[str] = []
    for line in lines:
        if _SOURCE_REF_RE.match(line):
            source_lines.append(line.strip())
        else:
            clean_lines.append(line)
    return "\n".join(clean_lines).strip(), "\n".join(source_lines).strip()


def _clean_answer(raw: str) -> str:
    text = raw.strip()
    text = _ANSWER_PREFIX_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_code_blocks(content: str) -> tuple[str, list[tuple[int, int, str]]]:
    """Temporarily remove fenced code blocks so separators inside them are ignored."""
    blocks: list[tuple[int, int, str]] = []
    result = list(content)
    for m in re.finditer(r"```.*?\n(.*?)```", content, re.DOTALL):
        start, end = m.start(), m.end()
        blocks.append((start, end, content[start:end]))
        placeholder = "\n" * (end - start)
        for i in range(start, end):
            result[i] = placeholder[i - start]
    return "".join(result), blocks


def _parse_by_format(content: str, theme: str, filename: str) -> list[Question]:
    """Parse questions in the new format:
    ### Q1: Question text
    **Answer:** Answer text
    """
    questions: list[Question] = []
    for idx, match in enumerate(_FORMAT_RE.finditer(content)):
        question_text = match.group(1).strip()
        answer_raw = match.group(2).strip()
        if not question_text or not answer_raw:
            continue
        answer_clean = _clean_answer(answer_raw)
        answer, source = _extract_source_ref(answer_clean)
        questions.append(
            Question(
                id=_make_id(theme, idx, question_text),
                theme=theme,
                theme_file=filename,
                question=question_text,
                answer=answer,
                source=source,
                index=idx,
            )
        )
    return questions


def parse_markdown_file(path: Path) -> list[Question]:
    """Parse a markdown question file.

    Auto-detects the format:
    - New:  ### Q1: ...  /  **Answer:** ... / ---
    """
    content = path.read_text(encoding="utf-8")
    theme = theme_name_from_path(path)

    return _parse_by_format(content, theme, path.name)


def question_count_in_file(path: Path) -> int:
    """Quick count of questions in a markdown file without building full objects."""
    content = path.read_text(encoding="utf-8")
    return len(_FORMAT_RE.findall(content))


def discover_themes(questions_dir: Path) -> dict[str, Path]:
    themes: dict[str, Path] = {}
    if not questions_dir.is_dir():
        return themes
    for path in sorted(questions_dir.glob("*.md")):
        try:
            if path.stat().st_size == 0:
                continue
            items = parse_markdown_file(path)
            if items:
                themes[items[0].theme] = path
        except OSError:
            continue
    return themes


def discover_themes_with_counts(questions_dir: Path) -> dict[str, tuple[Path, int]]:
    """Like discover_themes but also returns question count per file."""
    result: dict[str, tuple[Path, int]] = {}
    if not questions_dir.is_dir():
        return result
    for path in sorted(questions_dir.glob("*.md")):
        try:
            if path.stat().st_size == 0:
                continue
            items = parse_markdown_file(path)
            if items:
                result[items[0].theme] = (path, len(items))
        except OSError:
            continue
    return result


def load_questions(paths: list[Path]) -> list[Question]:
    all_questions: list[Question] = []
    for path in paths:
        all_questions.extend(parse_markdown_file(path))
    return all_questions