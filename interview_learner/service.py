from __future__ import annotations

from interview_learner.cloze import ClozeGenerator, OllamaClozeGenerator, RuleBasedClozeGenerator
from interview_learner.config import PROGRESS_DB, STAGE_VISIBILITY, AppSettings
from interview_learner.grading import ExactGrader, Grader, OllamaGrader
from interview_learner.models import (
    ClozeResult,
    ClozeState,
    GradeResult,
    LearningStage,
    Question,
    QuestionResult,
    SessionSummary,
)
from interview_learner.ollama_client import OllamaClient
from interview_learner.progress import ProgressStore


class LearningService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.progress = ProgressStore(PROGRESS_DB)
        self.ollama: OllamaClient | None = None
        self._cloze: ClozeGenerator = RuleBasedClozeGenerator()
        self._grader: Grader = ExactGrader(settings.pass_threshold)
        self._configure_ai()

    def _configure_ai(self) -> None:
        if not (self.settings.use_ollama_cloze or self.settings.use_ollama_grading):
            return

        self.ollama = OllamaClient(
            base_url=self.settings.ollama_url,
            model=self.settings.ollama_model,
        )
        if not self.ollama.is_available():
            self.ollama = None
            return

        rule_cloze = RuleBasedClozeGenerator()
        exact = ExactGrader(self.settings.pass_threshold)

        if self.settings.use_ollama_cloze:
            self._cloze = OllamaClozeGenerator(self.ollama, fallback=rule_cloze)
        if self.settings.use_ollama_grading:
            self._grader = OllamaGrader(
                self.ollama,
                fallback=exact,
                pass_threshold=self.settings.pass_threshold,
            )

    @property
    def ollama_connected(self) -> bool:
        return self.ollama is not None

    def prepare_session(
        self,
        questions: list[Question],
        count: int,
    ) -> list[Question]:
        return self.progress.pick_questions(questions, count)

    def stage_for(self, question: Question) -> LearningStage:
        prog = self.progress.get(question.id)
        return prog.stage if prog else LearningStage.READ

    def visibility_for_stage(self, stage: LearningStage) -> float:
        if stage == LearningStage.MASTERED:
            return STAGE_VISIBILITY[LearningStage.CLOZE_25]
        return STAGE_VISIBILITY.get(int(stage), 1.0)

    def is_favorite(self, question: Question) -> bool:
        prog = self.progress.get(question.id)
        return prog.favorite if prog else False

    def toggle_favorite(self, question: Question) -> bool:
        return self.progress.toggle_favorite(question.id)

    def build_cloze(self, question: Question, exam_mode: bool = False, visibility: float | None = None) -> ClozeResult:
        if exam_mode:
            return self._cloze.generate(question.answer, 0.25)
        if visibility is not None:
            return self._cloze.generate(question.answer, visibility)
        stage = self.stage_for(question)
        vis = self.visibility_for_stage(stage)
        return self._cloze.generate(question.answer, vis)

    def build_cloze_state(self, question: Question, exam_mode: bool = False, visibility: float | None = None) -> ClozeState:
        return ClozeState(result=self.build_cloze(question, exam_mode=exam_mode, visibility=visibility))

    def grade_attempt(
        self,
        question: Question,
        cloze: ClozeResult,
        user_inputs: list[str],
    ) -> GradeResult:
        return self._grader.grade(question.answer, cloze.gaps, user_inputs)

    def complete_question(
        self,
        question: Question,
        grade: GradeResult | None,
    ) -> LearningStage:
        stage = self.stage_for(question)
        if stage == LearningStage.READ:
            return self.progress.record_review(question, score=None, advance=True)

        score = grade.overall_score if grade else 0.0
        advance = grade.passed if grade else False
        return self.progress.record_review(question, score=score, advance=advance)

    def build_session_summary(
        self,
        questions: list[Question],
        results: list[QuestionResult],
    ) -> SessionSummary:
        scores = [r.score for r in results if r.score is not None]
        overall = sum(scores) / len(scores) if scores else None
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if r.score is not None and not r.passed)

        return SessionSummary(
            total_questions=len(questions),
            completed=len(results),
            overall_score=overall,
            passed_count=passed,
            failed_count=failed,
            results=results,
        )

    def get_stats(self) -> dict:
        return self.progress.get_stats()