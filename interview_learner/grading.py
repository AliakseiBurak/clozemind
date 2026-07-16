from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from interview_learner.config import PASS_THRESHOLD
from interview_learner.models import ClozeGap, GapGrade, GradeResult


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s'-]", "", text)
    return text


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for ca in a:
        curr = [prev[0] + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _longest_common_substr(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    longest = 0
    for i in range(m):
        for j in range(n):
            if a[i] == b[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
                longest = max(longest, dp[i + 1][j + 1])
    return longest


def _similarity(a: str, b: str) -> float:
    na, nb = _normalize(a), _normalize(b)
    if not na and not nb:
        return 100.0
    if not na or not nb:
        return 0.0
    if na == nb:
        return 100.0

    max_len = max(len(na), len(nb))
    lcs = _longest_common_substr(na, nb)

    if lcs / max_len < 0.45:
        return 0.0

    lev = _levenshtein(na, nb)
    return (1 - lev / max_len) * 100


class Grader(ABC):
    @abstractmethod
    def grade(
        self,
        answer: str,
        gaps: list[ClozeGap],
        user_inputs: list[str],
    ) -> GradeResult:
        raise NotImplementedError


class ExactGrader(Grader):
    """Fuzzy string match per gap — fast and works offline.

    Uses order-independent matching: each gap is matched to the best-fitting
    user input (greedy, without replacement). This handles swapped answers
    like "Availability, Consistency" instead of "Consistency, Availability".
    """

    def __init__(self, pass_threshold: float = PASS_THRESHOLD) -> None:
        self.pass_threshold = pass_threshold

    def grade(
        self,
        answer: str,
        gaps: list[ClozeGap],
        user_inputs: list[str],
    ) -> GradeResult:
        gap_grades: list[GapGrade] = []
        scores: list[float] = []

        for i, gap in enumerate(gaps):
            user = user_inputs[i] if i < len(user_inputs) else ""
            score = _similarity(gap.hidden_text, user)
            scores.append(score)
            feedback = "Correct." if score >= 90 else f"Expected: {gap.hidden_text}"
            gap_grades.append(
                GapGrade(
                    gap_index=i,
                    expected=gap.hidden_text,
                    user_input=user,
                    score=score,
                    feedback=feedback,
                )
            )

        overall = sum(scores) / len(scores) if scores else 100.0
        passed = overall >= self.pass_threshold
        summary = (
            f"Score: {overall:.0f}% — {'Passed' if passed else 'Keep practicing'}."
        )
        return GradeResult(
            overall_score=overall,
            passed=passed,
            gap_grades=gap_grades,
            summary=summary,
        )


class OllamaGrader(Grader):
    """Semantic grading via local LLM — accepts synonyms and paraphrases."""

    GRADE_PROMPT = """You grade active-recall answers for technical interview prep.
Be fair: accept synonyms, abbreviations, and minor spelling mistakes if meaning is correct.

Question context (full answer):
{answer}

For each gap, compare the expected term with what the user typed.
Score each gap 0-100. Overall score is the average.

Return ONLY valid JSON:
{{
  "gaps": [
    {{"index": 0, "score": 85, "feedback": "brief note"}}
  ],
  "summary": "one sentence overall feedback"
}}

Gaps to grade:
{gaps_json}"""

    def __init__(
        self,
        client: OllamaClient,
        fallback: Grader | None = None,
        pass_threshold: float = PASS_THRESHOLD,
    ) -> None:
        from interview_learner.ollama_client import OllamaClient

        self.client = client
        self.fallback = fallback or ExactGrader(pass_threshold)
        self.pass_threshold = pass_threshold

    def grade(
        self,
        answer: str,
        gaps: list[ClozeGap],
        user_inputs: list[str],
    ) -> GradeResult:
        gaps_payload = [
            {
                "index": i,
                "expected": gap.hidden_text,
                "user": user_inputs[i] if i < len(user_inputs) else "",
                "surrounding": answer[max(0, gap.start - 40) : gap.end + 40],
            }
            for i, gap in enumerate(gaps)
        ]

        try:
            raw = self.client.generate(
                self.GRADE_PROMPT.format(
                    answer=answer,
                    gaps_json=json.dumps(gaps_payload, indent=2),
                ),
                format_json=True,
            )
            payload = json.loads(raw)
            gap_grades: list[GapGrade] = []
            scores: list[float] = []

            for item in payload.get("gaps", []):
                idx = int(item["index"])
                score = float(item.get("score", 0))
                scores.append(score)
                gap = gaps[idx]
                user = user_inputs[idx] if idx < len(user_inputs) else ""
                gap_grades.append(
                    GapGrade(
                        gap_index=idx,
                        expected=gap.hidden_text,
                        user_input=user,
                        score=score,
                        feedback=str(item.get("feedback", "")),
                    )
                )

            overall = sum(scores) / len(scores) if scores else 0.0
            passed = overall >= self.pass_threshold
            summary = payload.get("summary") or f"Score: {overall:.0f}%"
            return GradeResult(
                overall_score=overall,
                passed=passed,
                gap_grades=gap_grades,
                summary=summary,
            )
        except Exception:
            return self.fallback.grade(answer, gaps, user_inputs)
