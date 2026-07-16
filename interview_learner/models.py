from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


BLANK_CHAR = "\u25a8"


def progressive_reveal(text: str, count: int) -> str:
    """Reveal the first `count` characters, replace the rest with BLANK_CHAR."""
    if count <= 0:
        return BLANK_CHAR * len(text)
    if count >= len(text):
        return text
    return text[:count] + BLANK_CHAR * (len(text) - count)


class LearningStage(IntEnum):
    READ = 0
    CLOZE_75 = 1
    CLOZE_50 = 2
    CLOZE_25 = 3
    MASTERED = 4


@dataclass(frozen=True)
class Question:
    id: str
    theme: str
    theme_file: str
    question: str
    answer: str
    index: int
    source: str = ""


@dataclass
class ClozeGap:
    """A hidden span in the answer the user must fill in."""

    start: int
    end: int
    hidden_text: str
    token_index: int


@dataclass
class ClozeResult:
    original: str
    visibility: float
    gaps: list[ClozeGap] = field(default_factory=list)

    @property
    def is_read_mode(self) -> bool:
        return self.visibility >= 1.0 or not self.gaps


@dataclass
class ClozeState:
    """Tracks active cloze session state, including revealed hints."""

    result: ClozeResult
    hinted_indices: set[int] = field(default_factory=set)
    revealed_counts: dict[int, int] = field(default_factory=dict)
    _hint_count: int = 0

    @property
    def is_read_mode(self) -> bool:
        return self.result.is_read_mode

    def next_hint_index(self) -> int | None:
        gaps = self.result.gaps
        for i, g in enumerate(gaps):
            if self.revealed_counts.get(i, 0) < len(g.hidden_text):
                return i
        return None

    def reveal_hint(self) -> int | None:
        gaps = self.result.gaps
        if not gaps:
            return None

        hint_num = self._hint_count
        self._hint_count += 1

        targets: list[tuple[int, int]] = []
        if hint_num == 0:
            targets = [(0, 2), (1, 1)]
        else:
            targets = [(hint_num - 1, 1), (hint_num, 2), (hint_num + 1, 1)]

        any_applied = False
        for gap_idx, add_count in targets:
            if 0 <= gap_idx < len(gaps):
                gap = gaps[gap_idx]
                current = self.revealed_counts.get(gap_idx, 0)
                if current < len(gap.hidden_text):
                    new_count = min(current + add_count, len(gap.hidden_text))
                    self.revealed_counts[gap_idx] = new_count
                    any_applied = True
                    if new_count >= len(gap.hidden_text):
                        self.hinted_indices.add(gap_idx)

        # If no targets applied (window beyond end), fill first
        # unrevealed gap 1 character at a time
        if not any_applied:
            for i, g in enumerate(gaps):
                current = self.revealed_counts.get(i, 0)
                if current < len(g.hidden_text):
                    new_count = current + 1
                    self.revealed_counts[i] = new_count
                    if new_count >= len(g.hidden_text):
                        self.hinted_indices.add(i)
                    break

        return targets[0][0] if targets else None


@dataclass
class GapGrade:
    gap_index: int
    expected: str
    user_input: str
    score: float
    feedback: str


@dataclass
class GradeResult:
    overall_score: float
    passed: bool
    gap_grades: list[GapGrade]
    summary: str


@dataclass
class QuestionResult:
    """Result for a single question in a session."""

    question: Question
    stage_before: LearningStage
    stage_after: LearningStage
    score: float | None
    passed: bool
    cloze: ClozeResult | None
    attempt: int = 1
    time_spent: float | None = None


@dataclass
class SessionSummary:
    """Summary of a completed learning session."""

    total_questions: int
    completed: int
    overall_score: float | None
    passed_count: int
    failed_count: int
    results: list[QuestionResult]
    elapsed_seconds: float | None = None

    @property
    def missed_questions(self) -> list[QuestionResult]:
        return [r for r in self.results if r.score is not None and not r.passed]