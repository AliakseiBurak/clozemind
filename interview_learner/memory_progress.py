from __future__ import annotations

from datetime import date, timedelta, datetime, timezone
from typing import Any

from interview_learner.config import SM2_DEFAULT_EF, SM2_MIN_EF
from interview_learner.models import LearningStage, Question
from interview_learner.progress import QuestionProgress, score_to_quality, sm2_next


def _today_str() -> str:
    return date.today().isoformat()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryProgressStore:
    def __init__(self, data: dict[str, dict[str, Any]] | None = None) -> None:
        self._records: dict[str, dict[str, Any]] = data or {}

    def get(self, question_id: str) -> QuestionProgress | None:
        d = self._records.get(question_id)
        if d is None:
            return None
        return QuestionProgress(
            question_id=d["question_id"],
            stage=LearningStage(d["stage"]),
            times_seen=d["times_seen"],
            last_score=d.get("last_score"),
            last_reviewed=d.get("last_reviewed"),
            easiness_factor=d.get("easiness_factor", SM2_DEFAULT_EF),
            interval_days=d.get("interval_days", 0),
            next_review_date=d.get("next_review_date"),
            repetitions=d.get("repetitions", 0),
            favorite=d.get("favorite", False),
        )

    def record_review(
        self,
        question: Question,
        score: float | None,
        advance: bool,
    ) -> LearningStage:
        existing = self._records.get(question.id)

        if existing:
            stage = LearningStage(existing["stage"])
            times_seen = existing["times_seen"] + 1
            ef = existing.get("easiness_factor", SM2_DEFAULT_EF)
            interval_days = existing.get("interval_days", 0)
            repetitions = existing.get("repetitions", 0)
        else:
            stage = LearningStage.READ
            times_seen = 1
            ef = SM2_DEFAULT_EF
            interval_days = 0
            repetitions = 0

        if advance and int(stage) < int(LearningStage.MASTERED):
            stage = LearningStage(int(stage) + 1)

        if score is not None:
            quality = score_to_quality(score)
            repetitions, interval_days, ef = sm2_next(
                quality, repetitions, ef, interval_days
            )

        now = _utc_now()
        next_review = _today_str() if interval_days == 0 else None
        if next_review is None and interval_days > 0:
            next_review = (date.today() + timedelta(days=interval_days)).isoformat()

        self._records[question.id] = {
            "question_id": question.id,
            "theme": question.theme,
            "stage": int(stage),
            "times_seen": times_seen,
            "last_score": score,
            "last_reviewed": now,
            "easiness_factor": ef,
            "interval_days": interval_days,
            "next_review_date": next_review,
            "repetitions": repetitions,
            "favorite": existing.get("favorite", False) if existing else False,
        }
        return stage

    def pick_questions(
        self,
        pool: list[Question],
        count: int,
    ) -> list[Question]:
        today = _today_str()

        def sort_key(q: Question) -> tuple:
            rec = self._records.get(q.id)
            if rec is None:
                return (0, 0, 0, 0, "")
            stage = rec.get("stage", 0)
            fav = 0 if rec.get("favorite", False) else 1
            due = 0 if (rec.get("next_review_date") and rec["next_review_date"] <= today) else 1
            times = rec.get("times_seen", 0)
            reviewed = rec.get("last_reviewed", "")
            return (due, fav, stage, times, reviewed)

        ordered = sorted(pool, key=sort_key)
        return ordered[:count]

    def toggle_favorite(self, question_id: str) -> bool:
        rec = self._records.get(question_id)
        new_val = not (rec.get("favorite", False) if rec else False)
        if rec:
            rec["favorite"] = new_val
        else:
            self._records[question_id] = {
                "question_id": question_id,
                "theme": "",
                "stage": 0,
                "times_seen": 0,
                "last_score": None,
                "last_reviewed": None,
                "easiness_factor": SM2_DEFAULT_EF,
                "interval_days": 0,
                "next_review_date": None,
                "repetitions": 0,
                "favorite": new_val,
            }
        return new_val

    def get_stats(self) -> dict[str, Any]:
        total = len(self._records)
        mastered = sum(1 for r in self._records.values() if r.get("stage", 0) >= 4)
        scores = [r.get("last_score") for r in self._records.values() if r.get("last_score") is not None]
        avg = sum(scores) / len(scores) if scores else None
        favorites = sum(1 for r in self._records.values() if r.get("favorite", False))
        return {
            "total": total,
            "mastered": mastered,
            "avg_score": avg,
            "favorites": favorites,
        }

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return dict(self._records)

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, Any]]) -> MemoryProgressStore:
        return cls(data=dict(data))
