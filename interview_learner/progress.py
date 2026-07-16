from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from interview_learner.config import SM2_DEFAULT_EF, SM2_MIN_EF
from interview_learner.models import LearningStage, Question


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_str() -> str:
    return date.today().isoformat()


def score_to_quality(score: float) -> int:
    """Map a percentage score (0-100) to SM-2 quality (0-5)."""
    if score >= 95:
        return 5
    if score >= 85:
        return 4
    if score >= 70:
        return 3
    if score >= 50:
        return 2
    if score >= 30:
        return 1
    return 0


def sm2_next(
    quality: int,
    repetitions: int,
    easiness_factor: float,
    interval: int,
) -> tuple[int, int, float]:
    """Compute next SM-2 state given the quality of the last recall.

    Returns (repetitions, interval_days, easiness_factor).
    """
    ef = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(SM2_MIN_EF, ef)

    if quality >= 3:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        repetitions += 1
    else:
        repetitions = 0
        interval = 1

    return repetitions, interval, ef


@dataclass
class QuestionProgress:
    question_id: str
    stage: LearningStage
    times_seen: int
    last_score: float | None
    last_reviewed: str | None
    easiness_factor: float = SM2_DEFAULT_EF
    interval_days: int = 0
    next_review_date: str | None = None
    repetitions: int = 0
    favorite: bool = False


class ProgressStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._migrate_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS question_progress (
                    question_id TEXT PRIMARY KEY,
                    theme TEXT NOT NULL,
                    stage INTEGER NOT NULL DEFAULT 0,
                    times_seen INTEGER NOT NULL DEFAULT 0,
                    last_score REAL,
                    last_reviewed TEXT
                )
                """
            )

    def _migrate_db(self) -> None:
        """Add SM-2 and favorite columns if they don't exist."""
        migrations = [
            ("easiness_factor", "REAL DEFAULT 2.5"),
            ("interval_days", "INTEGER DEFAULT 0"),
            ("next_review_date", "TEXT"),
            ("repetitions", "INTEGER DEFAULT 0"),
            ("favorite", "INTEGER DEFAULT 0"),
        ]
        with self._connect() as conn:
            for col_name, col_def in migrations:
                try:
                    conn.execute(f"ALTER TABLE question_progress ADD COLUMN {col_name} {col_def}")
                except sqlite3.OperationalError:
                    pass  # column already exists

    def _row_to_progress(self, row: sqlite3.Row) -> QuestionProgress:
        """Convert a sqlite3.Row to QuestionProgress, handling optional columns."""
        d = dict(row)
        return QuestionProgress(
            question_id=d["question_id"],
            stage=LearningStage(d["stage"]),
            times_seen=d["times_seen"],
            last_score=d["last_score"],
            last_reviewed=d["last_reviewed"],
            easiness_factor=d.get("easiness_factor", SM2_DEFAULT_EF),
            interval_days=d.get("interval_days", 0),
            next_review_date=d.get("next_review_date"),
            repetitions=d.get("repetitions", 0),
            favorite=bool(d.get("favorite", 0)),
        )

    def get(self, question_id: str) -> QuestionProgress | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM question_progress WHERE question_id = ?",
                (question_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_progress(row)

    def record_review(
        self,
        question: Question,
        score: float | None,
        advance: bool,
    ) -> LearningStage:
        existing = self.get(question.id)
        stage = existing.stage if existing else LearningStage.READ
        times_seen = (existing.times_seen if existing else 0) + 1
        ef = existing.easiness_factor if existing else SM2_DEFAULT_EF
        interval_days = existing.interval_days if existing else 0
        repetitions = existing.repetitions if existing else 0

        if advance and stage < LearningStage.MASTERED:
            stage = LearningStage(stage + 1)

        # SM-2 update if we have a score
        if score is not None:
            quality = score_to_quality(score)
            repetitions, interval_days, ef = sm2_next(
                quality, repetitions, ef, interval_days
            )

        now = _utc_now()
        next_review = _today_str() if interval_days == 0 else None
        if next_review is None and interval_days > 0:
            from datetime import timedelta

            next_review = (date.today() + timedelta(days=interval_days)).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO question_progress
                    (question_id, theme, stage, times_seen, last_score,
                     last_reviewed, easiness_factor, interval_days,
                     next_review_date, repetitions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(question_id) DO UPDATE SET
                    stage = excluded.stage,
                    times_seen = excluded.times_seen,
                    last_score = excluded.last_score,
                    last_reviewed = excluded.last_reviewed,
                    easiness_factor = excluded.easiness_factor,
                    interval_days = excluded.interval_days,
                    next_review_date = excluded.next_review_date,
                    repetitions = excluded.repetitions
                """,
                (
                    question.id,
                    question.theme,
                    int(stage),
                    times_seen,
                    score,
                    now,
                    ef,
                    interval_days,
                    next_review,
                    repetitions,
                ),
            )
        return stage

    def toggle_favorite(self, question_id: str) -> bool:
        """Toggle favorite status. Returns new state."""
        existing = self.get(question_id)
        new_val = 0 if (existing and existing.favorite) else 1
        with self._connect() as conn:
            if existing:
                conn.execute(
                    "UPDATE question_progress SET favorite = ? WHERE question_id = ?",
                    (new_val, question_id),
                )
            else:
                conn.execute(
                    """INSERT INTO question_progress
                       (question_id, theme, stage, times_seen, favorite)
                       VALUES (?, '', 0, 0, ?)""",
                    (question_id, new_val),
                )
        return bool(new_val)

    def pick_questions(
        self,
        pool: list[Question],
        count: int,
    ) -> list[Question]:
        """Pick questions prioritizing SM-2 due items, then favorites, then lower-stage items."""

        today = _today_str()

        def sort_key(q: Question) -> tuple:
            prog = self.get(q.id)
            if prog is None:
                return (0, 0, 0, 0, "")
            stage = int(prog.stage)
            fav = 0 if prog.favorite else 1
            due = 0 if (prog.next_review_date and prog.next_review_date <= today) else 1
            times = prog.times_seen
            reviewed = prog.last_reviewed or ""
            return (due, fav, stage, times, reviewed)

        ordered = sorted(pool, key=sort_key)
        return ordered[:count]

    def get_stats(self) -> dict:
        """Return aggregate progress stats."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN stage >= 4 THEN 1 ELSE 0 END) AS mastered,
                    AVG(last_score) AS avg_score,
                    SUM(CASE WHEN favorite = 1 THEN 1 ELSE 0 END) AS favorites
                FROM question_progress
                """
            ).fetchone()
        return dict(row) if row else {}