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

        self._hint_count += 1

        unfinished = [(i, g) for i, g in enumerate(gaps)
                      if self.revealed_counts.get(i, 0) < len(g.hidden_text)]
        if not unfinished:
            return None

        total_hidden = sum(len(g.hidden_text) - self.revealed_counts.get(i, 0)
                           for i, g in unfinished)
        target = max(1, round(total_hidden * 0.1))

        # Distribute reveals: first spread first-3-position reveals across
        # all words, then give extras to larger words.
        result_idx = unfinished[0][0]
        revealed = 0

        def _revealed_in_first3(i: int) -> int:
            return min(3, self.revealed_counts.get(i, 0))

        for i, g in sorted(
            unfinished,
            key=lambda x: (_revealed_in_first3(x[0]), -len(x[1].hidden_text)),
        ):
            if revealed >= target:
                break
            current = self.revealed_counts.get(i, 0)
            if current < len(g.hidden_text):
                self.revealed_counts[i] = current + 1
                revealed += 1
                result_idx = i
                if current + 1 >= len(g.hidden_text):
                    self.hinted_indices.add(i)

        return result_idx


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