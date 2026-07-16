from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk

from interview_learner.config import AppSettings, STAGE_VISIBILITY
from interview_learner.models import (
    ClozeState,
    LearningStage,
    QuestionResult,
    progressive_reveal, BLANK_CHAR,
)
from interview_learner.parser import (
    discover_themes_with_counts,
    load_questions,
    theme_display_name,
)
from interview_learner.service import LearningService


STAGE_LABELS = {
    LearningStage.READ: "Read (100%)",
    LearningStage.CLOZE_75: "Recall (75% visible)",
    LearningStage.CLOZE_50: "Recall (50% visible)",
    LearningStage.CLOZE_25: "Recall (25% visible)",
    LearningStage.MASTERED: "Mastered",
}

FONT_FAMILY = "TkDefaultFont"


def _fmt_time(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    secs = int(seconds)
    if secs < 60:
        return f"{secs}s"
    return f"{secs // 60}m {secs % 60}s"


class IntroWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Interview Learner")
        self.geometry("680x740")
        self.minsize(540, 640)

        self.settings = AppSettings()
        self.theme_vars: dict[str, tk.BooleanVar] = {}
        self.question_count = tk.IntVar(value=5)
        self.use_ollama_cloze = tk.BooleanVar(value=False)
        self.use_ollama_grading = tk.BooleanVar(value=False)
        self.ollama_model = tk.StringVar(value=self.settings.ollama_model)
        self.timer_var = tk.BooleanVar(value=False)
        self._ollama_available = False
        self._ollama_widgets: list[ttk.Widget] = []

        self._build()
        self._load_themes()
        self._check_ollama_on_startup()

    def _build(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            container,
            text="Interview Question Learner",
            font=(FONT_FAMILY, 16, "bold"),
        ).pack(anchor=tk.W)

        ttk.Label(
            container,
            text=(
                "Select themes and how many questions to practice. "
                "Each question progresses through read \u2192 75% \u2192 50% \u2192 25% visibility."
            ),
            wraplength=620,
        ).pack(anchor=tk.W, pady=(8, 16))

        themes_frame = ttk.LabelFrame(container, text="Themes", padding=8)
        themes_frame.pack(fill=tk.BOTH, expand=True)

        # Select / Deselect All row
        theme_controls = ttk.Frame(themes_frame)
        theme_controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(theme_controls, text="Select All", command=self._select_all_themes).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(theme_controls, text="Deselect All", command=self._deselect_all_themes).pack(
            side=tk.LEFT
        )

        self.themes_canvas = tk.Canvas(themes_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            themes_frame, orient=tk.VERTICAL, command=self.themes_canvas.yview
        )
        self.themes_inner = ttk.Frame(self.themes_canvas)

        self.themes_inner.bind(
            "<Configure>",
            lambda e: self.themes_canvas.configure(
                scrollregion=self.themes_canvas.bbox("all")
            ),
        )
        self.themes_canvas.create_window(
            (0, 0), window=self.themes_inner, anchor=tk.NW
        )
        self.themes_canvas.configure(yscrollcommand=scrollbar.set)

        self.themes_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.theme_count_label = ttk.Label(container, text="", foreground="#555")
        self.theme_count_label.pack(anchor=tk.W)

        options = ttk.Frame(container)
        options.pack(fill=tk.X, pady=12)

        ttk.Label(options, text="Questions per session:").pack(side=tk.LEFT)
        ttk.Spinbox(
            options,
            from_=1,
            to=50,
            textvariable=self.question_count,
            width=5,
        ).pack(side=tk.LEFT, padx=(8, 24))

        self.gaps_var = tk.IntVar(value=50)
        ttk.Label(options, text="Gaps:").pack(side=tk.LEFT, padx=(16, 0))
        ttk.Spinbox(
            options,
            from_=0,
            to=100,
            textvariable=self.gaps_var,
            width=5,
        ).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Label(options, text="% (0 = full answer)").pack(side=tk.LEFT)

        ttk.Checkbutton(
            options, text="Enable session timer", variable=self.timer_var
        ).pack(side=tk.LEFT, padx=(24, 0))

        ai_frame = ttk.LabelFrame(container, text="Ollama AI (optional)", padding=8)
        ai_frame.pack(fill=tk.X, pady=(0, 12))
        self.ai_frame = ai_frame
        self._ollama_widgets = []

        self.ai_status_label = ttk.Label(ai_frame, text="", foreground="#888")
        self.ai_status_label.pack(anchor=tk.W, pady=(0, 4))

        cloze_cb = ttk.Checkbutton(
            ai_frame,
            text="Semantic cloze \u2014 hide key concepts, not random words",
            variable=self.use_ollama_cloze,
        )
        cloze_cb.pack(anchor=tk.W)
        self._ollama_widgets.append(cloze_cb)

        grading_cb = ttk.Checkbutton(
            ai_frame,
            text="AI grading \u2014 accept synonyms and paraphrases",
            variable=self.use_ollama_grading,
        )
        grading_cb.pack(anchor=tk.W)
        self._ollama_widgets.append(grading_cb)

        model_row = ttk.Frame(ai_frame)
        model_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(model_row, text="Model:").pack(side=tk.LEFT)
        self.model_combo = ttk.Combobox(
            model_row,
            textvariable=self.ollama_model,
            width=28,
            state="readonly",
        )
        self.model_combo.pack(side=tk.LEFT, padx=8)
        self._ollama_widgets.append(model_row)

        self.status_label = ttk.Label(container, text="", foreground="#555")
        self.status_label.pack(anchor=tk.W)

        btn_row = ttk.Frame(container)
        btn_row.pack(fill=tk.X, pady=(8, 0))

        self.learn_btn = ttk.Button(btn_row, text="Learn", command=lambda: self._start(mode="learn"))
        self.learn_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.fill_btn = ttk.Button(btn_row, text="Fill in gaps", command=lambda: self._start(mode="fill"))
        self.fill_btn.pack(side=tk.LEFT, padx=6)

        self.exam_btn = ttk.Button(btn_row, text="Start Exam", command=lambda: self._start(mode="exam"))
        self.exam_btn.pack(side=tk.LEFT, padx=(6, 0))
        if not self._ollama_available:
            self.exam_btn.config(state=tk.DISABLED)

    def _select_all_themes(self) -> None:
        for var in self.theme_vars.values():
            var.set(True)
        self._update_theme_count()

    def _deselect_all_themes(self) -> None:
        for var in self.theme_vars.values():
            var.set(False)
        self._update_theme_count()

    def _update_theme_count(self) -> None:
        selected = sum(1 for var in self.theme_vars.values() if var.get())
        self.theme_count_label.config(text=f"{selected} theme(s) selected")

    def _load_themes(self) -> None:
        themes = discover_themes_with_counts(self.settings.questions_dir)
        if not themes:
            ttk.Label(
                self.themes_inner,
                text="No readable .md files found in questions/",
                foreground="#a00",
            ).pack(anchor=tk.W)
            return

        for theme in sorted(themes):
            path, count = themes[theme]
            var = tk.BooleanVar(
                value=theme in ("example_general", "general")
            )
            self.theme_vars[theme] = var

            display = theme_display_name(theme)
            cb = ttk.Checkbutton(
                self.themes_inner,
                text=f"{display}  ({count} questions)",
                variable=var,
                command=self._update_theme_count,
            )
            cb.pack(anchor=tk.W)

        self.status_label.config(text=f"{len(themes)} theme(s) available")
        self._update_theme_count()

    def _check_ollama_on_startup(self) -> None:
        """Check Ollama availability and populate the model dropdown.

        If the server is unreachable, the entire Ollama section is disabled
        with a warning so the user can't enable features that won't work.
        """
        from interview_learner.ollama_client import OllamaClient

        self.ai_status_label.config(
            text="Checking Ollama connection...", foreground="#888"
        )
        self.update_idletasks()

        client = OllamaClient(
            base_url=self.settings.ollama_url,
            model=self.settings.ollama_model,
        )
        self._ollama_available = client.is_available()
        models = client.list_models() if self._ollama_available else []

        if self._ollama_available and models:
            self.model_combo["values"] = models
            # Pre-select the configured model if it's in the list, else the first one
            default = self.settings.ollama_model
            self.ollama_model.set(
                default if default in models else models[0]
            )
            self.ai_status_label.config(
                text=f"\u2705 Ollama connected \u2014 {len(models)} model(s) available",
                foreground="#070",
            )
            self.exam_btn.config(state=tk.NORMAL)
        elif self._ollama_available and not models:
            self.ai_status_label.config(
                text="\u26a0 Ollama connected but no models found (pull one first)",
                foreground="#a60",
            )
            self._disable_ollama_section()
        else:
            self.ai_status_label.config(
                text="\u26a0 Ollama not available at localhost:11434 \u2014 AI features disabled",
                foreground="#a00",
            )
            self._disable_ollama_section()

    def _disable_ollama_section(self) -> None:
        """Disable all Ollama widgets and uncheck the toggles."""
        self.use_ollama_cloze.set(False)
        self.use_ollama_grading.set(False)
        for w in self._ollama_widgets:
            try:
                w.config(state=tk.DISABLED)
            except tk.TclError:
                pass
        self.model_combo.config(state=tk.DISABLED)

    def _start(self, mode: str = "learn") -> None:
        selected = [t for t, var in self.theme_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("Select themes", "Pick at least one theme.")
            return

        themes = discover_themes_with_counts(self.settings.questions_dir)
        paths = [themes[t][0] for t in selected if t in themes]
        questions = load_questions(paths)
        if not questions:
            messagebox.showerror("No questions", "Selected themes contain no questions.")
            return

        count = self.question_count.get()
        self.settings.use_ollama_cloze = self.use_ollama_cloze.get()
        self.settings.use_ollama_grading = self.use_ollama_grading.get()
        self.settings.ollama_model = self.ollama_model.get().strip() or self.settings.ollama_model

        service = LearningService(self.settings)
        session_questions = service.prepare_session(questions, count)

        gaps = self.gaps_var.get()
        exam_mode = mode == "exam"
        fill_mode = mode == "fill"
        visibility = 1.0 if mode == "learn" else max(0.0, 1.0 - gaps / 100.0)

        self.withdraw()
        SessionWindow(
            master=self,
            service=service,
            questions=session_questions,
            exam_mode=exam_mode,
            fill_mode=fill_mode,
            visibility=visibility,
            timer_enabled=True if mode == "learn" else self.timer_var.get(),
        )


class SessionWindow(tk.Toplevel):
    def __init__(
        self,
        master: IntroWindow,
        service: LearningService,
        questions: list,
        exam_mode: bool = False,
        fill_mode: bool = False,
        visibility: float = 1.0,
        timer_enabled: bool = False,
    ) -> None:
        super().__init__(master)
        self.master_intro = master
        self.service = service
        self.questions = questions
        self.index = 0
        self.gap_entries: list[tk.Entry] = []
        self.cloze_state: ClozeState | None = None
        self.results: list[QuestionResult] = []
        self.all_results: list[QuestionResult] = []
        self.all_questions: list = list(questions)
        self.answer_visible = False
        self.exam_mode = exam_mode
        self.fill_mode = fill_mode
        self._forced_visibility = visibility
        self._exam_results: list[dict] = []
        self._timer_enabled = timer_enabled
        self._start_time: float | None = time.time() if timer_enabled else None
        self._question_start_time: float | None = None

        title = "Exam" if exam_mode else "Learning"
        self.title(title)
        self.geometry("800x740")
        self.minsize(600, 540)
        self.protocol("WM_DELETE_WINDOW", self._close)

        self._build()
        self._show_current()

    def _build(self) -> None:
        self.progress_label = ttk.Label(self, text="", font=(FONT_FAMILY, 10))
        self.progress_label.pack(anchor=tk.W, padx=16, pady=(12, 0))

        info_row = ttk.Frame(self)
        info_row.pack(fill=tk.X, padx=16, pady=(4, 8))
        self.stage_label = ttk.Label(info_row, text="", foreground="#006")
        if not self.exam_mode:
            self.stage_label.pack(side=tk.LEFT)
        q_frame = ttk.LabelFrame(self, text="Question", padding=12)
        q_frame.pack(fill=tk.X, padx=16, pady=4)
        self.question_label = ttk.Label(
            q_frame, text="", wraplength=740, font=(FONT_FAMILY, 11, "bold")
        )
        self.question_label.pack(anchor=tk.W)

        a_frame = ttk.LabelFrame(self, text="Answer", padding=12)
        a_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        self.answer_canvas = tk.Canvas(a_frame, highlightthickness=0)
        a_scroll = ttk.Scrollbar(
            a_frame, orient=tk.VERTICAL, command=self.answer_canvas.yview
        )
        self.answer_inner = ttk.Frame(self.answer_canvas)

        self.answer_inner.bind(
            "<Configure>",
            lambda e: self.answer_canvas.configure(
                scrollregion=self.answer_canvas.bbox("all")
            ),
        )
        self.canvas_window_id = self.answer_canvas.create_window(
            (0, 0), window=self.answer_inner, anchor=tk.NW
        )
        self.answer_canvas.configure(yscrollcommand=a_scroll.set)

        # Expand inner frame width when canvas is resized
        def _expand_inner(event: tk.Event) -> None:
            self.answer_canvas.itemconfig(self.canvas_window_id, width=event.width)

        self.answer_canvas.bind("<Configure>", _expand_inner)

        self.answer_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        a_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Action button row
        action_row = ttk.Frame(self)
        action_row.pack(fill=tk.X, padx=16, pady=(4, 0))

        self.hint_btn = ttk.Button(
            action_row, text="\U0001f9e0 Hint", command=self._hint
        )
        if not self.exam_mode:
            self.hint_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.ref_btn = ttk.Button(
            action_row,
            text="Show Answer",
            command=self._toggle_reference,
        )
        self.ref_btn.pack(side=tk.LEFT)

        # Bottom button row
        btn_row = ttk.Frame(self)
        btn_row.pack(fill=tk.X, padx=16, pady=12)
        self.submit_btn = ttk.Button(
            btn_row, text="Submit / Next", command=self._submit
        )
        self.submit_btn.pack(side=tk.RIGHT)
        self.got_it_btn = ttk.Button(
            btn_row, text="Got it \u2014 Next", command=self._mark_read
        )
        ttk.Button(btn_row, text="End Session", command=self._close).pack(
            side=tk.RIGHT, padx=8
        )

        self.ai_indicator = ttk.Label(
            btn_row, text="", foreground="#888", font=(FONT_FAMILY, 9)
        )
        self.ai_indicator.pack(side=tk.LEFT)

    def _update_ui(self) -> None:
        q = self.questions[self.index]
        stage = self.service.stage_for(q)

        self.progress_label.config(
            text=f"{'Exam' if self.exam_mode else 'Question'} {self.index + 1} of {len(self.questions)}  \u00b7  Theme: {theme_display_name(q.theme)}"
        )
        if not self.exam_mode:
            self.stage_label.config(
                text=f"Stage: {STAGE_LABELS.get(stage, stage.name)}"
            )
        self.question_label.config(text=f"Q{q.index + 1}: {q.question}")

    def _clear_answer(self) -> None:
        for child in self.answer_inner.winfo_children():
            child.destroy()
        self.gap_entries.clear()
        self.answer_visible = False
        self.ref_btn.config(text="Show Answer")

    def _render_answer(self, question) -> None:
        self._clear_answer()
        if self.exam_mode:
            cloze_state = self.service.build_cloze_state(question, exam_mode=True)
        elif self.fill_mode:
            cloze_state = self.service.build_cloze_state(question, visibility=self._forced_visibility)
        else:
            cloze_state = self.service.build_cloze_state(question, visibility=1.0)
        self.cloze_state = cloze_state
        cloze = cloze_state.result

        if not self.exam_mode and cloze.is_read_mode:
            ttk.Label(
                self.answer_inner,
                text=question.answer,
                wraplength=720,
                justify=tk.LEFT,
            ).pack(anchor=tk.W)
            self.submit_btn.config(text="Next Question", command=self._next)
            self.hint_btn.config(state=tk.DISABLED)
            self.got_it_btn.pack(side=tk.RIGHT)
        else:
            self.submit_btn.config(text="Check Answers")
            self.hint_btn.config(state=tk.NORMAL if not self.exam_mode else tk.DISABLED)
            self.got_it_btn.pack_forget()

            # Show masked text with blanks
            masked = cloze.original
            gap_idx = {g.token_index: i for i, g in enumerate(cloze.gaps)}
            for gap in reversed(cloze.gaps):
                gi = gap_idx[gap.token_index]
                cnt = cloze_state.revealed_counts.get(gi, 0)
                blank = progressive_reveal(gap.hidden_text, cnt) if cnt > 0 else BLANK_CHAR * max(4, len(gap.hidden_text))
                masked = (
                    masked[: gap.start] + f"[{blank}]" + masked[gap.end :]
                )

            ttk.Label(
                self.answer_inner,
                text=masked,
                wraplength=720,
                justify=tk.LEFT,
                font=(FONT_FAMILY, 10),
            ).pack(anchor=tk.W, pady=(0, 12))

            if not cloze.gaps:
                ttk.Label(
                    self.answer_inner, text=question.answer, wraplength=720
                ).pack(anchor=tk.W)
            else:
                ttk.Label(
                    self.answer_inner,
                    text="Fill in the blanks:",
                    font=(FONT_FAMILY, 10, "bold"),
                ).pack(anchor=tk.W, pady=(4, 8))

                for i, gap in enumerate(cloze.gaps):
                    row = ttk.Frame(self.answer_inner)
                    row.pack(anchor=tk.W, fill=tk.X, pady=2)
                    ttk.Label(row, text=f"{i + 1}.", width=3).pack(side=tk.LEFT)

                    entry = ttk.Entry(
                        row, width=max(20, len(gap.hidden_text) + 4)
                    )
                    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                    self.gap_entries.append(entry)

                if self.gap_entries:
                    self.gap_entries[0].focus()

        if question.source and not self.fill_mode and not self.exam_mode:
            ttk.Label(
                self.answer_inner,
                text="\u2500" * 40,
                foreground="#aaa",
                font=(FONT_FAMILY, 8),
            ).pack(anchor=tk.W, pady=(8, 2))
            ttk.Label(
                self.answer_inner,
                text=question.source,
                wraplength=720,
                justify=tk.LEFT,
                foreground="#555",
                font=(FONT_FAMILY, 9),
            ).pack(anchor=tk.W)

        self.feedback_label = ttk.Label(
            self.answer_inner, text="", wraplength=720, justify=tk.LEFT
        )
        self.feedback_label.pack(anchor=tk.W, pady=(4, 0))

    def _show_reference(self) -> None:
        if self.cloze_state is None or self.cloze_state.is_read_mode:
            return
        ref_label = ttk.Label(
            self.answer_inner,
            text="\u2500" * 40 + "\nFull answer reference:\n" + self.questions[self.index].answer,
            wraplength=720,
            justify=tk.LEFT,
            foreground="#555",
            font=(FONT_FAMILY, 9),
        )
        ref_label.pack(anchor=tk.W, pady=(12, 0))
        self._reference_widget = ref_label

    def _show_current(self) -> None:
        if self.index >= len(self.questions):
            self._show_summary()
            return

        q = self.questions[self.index]
        self._update_ui()
        self._render_answer(q)
        if self._timer_enabled:
            self._question_start_time = time.time()

    def _submit(self) -> None:
        if self.index >= len(self.questions):
            return

        q = self.questions[self.index]
        stage = self.service.stage_for(q)
        cloze_state = self.cloze_state

        if cloze_state is None:
            return

        time_spent = None
        if self._timer_enabled and self._question_start_time is not None:
            time_spent = time.time() - self._question_start_time

        # Exam mode: always grade, never read/advance
        if self.exam_mode:
            user_inputs = [e.get() for e in self.gap_entries]
            grade = self.service.grade_attempt(q, cloze_state.result, user_inputs)
            attempt = sum(1 for r in self._exam_results if r.get("question") and r["question"].id == q.id) + 1
            self._exam_results.append({
                "question": q,
                "score": grade.overall_score,
                "passed": grade.passed,
                "grade": grade,
                "attempt": attempt,
                "time_spent": time_spent,
            })
            lines = [grade.summary]
            for g in grade.gap_grades:
                if g.score < 90:
                    lines.append(f"  \u2022 Expected '{g.expected}' \u2192 you wrote '{g.user_input}' ({g.score:.0f}%)")
            self.feedback_label.config(text="\n".join(lines))
            self.submit_btn.config(state=tk.DISABLED)
            self.hint_btn.config(state=tk.DISABLED)
            self.submit_btn.config(text="Next Question", command=self._next)
            return

        user_inputs = [e.get() for e in self.gap_entries]
        grade = self.service.grade_attempt(q, cloze_state.result, user_inputs)
        new_stage = self.service.complete_question(q, grade)

        attempt = sum(1 for r in self.results if r.question.id == q.id) + 1
        qr = QuestionResult(
            question=q,
            stage_before=stage,
            stage_after=new_stage,
            score=grade.overall_score,
            passed=grade.passed,
            cloze=cloze_state.result,
            attempt=attempt,
            time_spent=time_spent,
        )
        self.results.append(qr)
        self.all_results.append(qr)

        lines = [grade.summary]
        for g in grade.gap_grades:
            if g.score < 90:
                lines.append(f"  \u2022 Expected '{g.expected}' \u2192 you wrote '{g.user_input}' ({g.score:.0f}%)")
        self.feedback_label.config(text="\n".join(lines))

        self.hint_btn.config(state=tk.DISABLED)
        self.submit_btn.config(text="Next Question", command=self._next)

    def _next(self) -> None:
        self.submit_btn.config(state=tk.NORMAL)
        self.hint_btn.config(state=tk.NORMAL)
        self.submit_btn.config(text="Check Answers", command=self._submit)
        self.index += 1
        self._show_current()

    def _hint(self) -> None:
        if self.cloze_state is None or self.cloze_state.is_read_mode:
            return
        saved = [e.get() for e in self.gap_entries]
        idx = self.cloze_state.reveal_hint()
        if idx is not None:
            self._render_answer(self.questions[self.index])
            for e, val in zip(self.gap_entries, saved):
                if val.strip():
                    e.delete(0, tk.END)
                    e.insert(0, val)
            remaining_available = self.cloze_state.next_hint_index() is not None
            self.feedback_label.config(
                text=f"\U0001f9e0 Hint applied. Click again for more letters.",
            )
            if not remaining_available:
                self.hint_btn.config(state=tk.DISABLED)
        else:
            self.feedback_label.config(text="All gaps already revealed.")
            self.hint_btn.config(state=tk.DISABLED)

    def _mark_read(self) -> None:
        q = self.questions[self.index]
        stage = self.service.stage_for(q)
        new_stage = self.service.complete_question(q, grade=None)
        attempt = sum(1 for r in self.results if r.question.id == q.id) + 1
        time_spent = None
        if self._timer_enabled and self._question_start_time is not None:
            time_spent = time.time() - self._question_start_time
        qr = QuestionResult(
            question=q,
            stage_before=stage,
            stage_after=new_stage,
            score=None,
            passed=True,
            cloze=self.cloze_state.result if self.cloze_state else None,
            attempt=attempt,
            time_spent=time_spent,
        )
        self.results.append(qr)
        self.all_results.append(qr)
        self._next()

    def _toggle_reference(self) -> None:
        if self.cloze_state is None or self.cloze_state.is_read_mode:
            return

        if self.answer_visible:
            # Hide reference — re-render without it
            self.answer_visible = False
            self.ref_btn.config(text="Show Answer")
            self._render_answer(self.questions[self.index])
        else:
            self.answer_visible = True
            self.ref_btn.config(text="Hide Answer")
            self._show_reference()

    def _show_summary(self) -> None:
        elapsed = None
        if self._timer_enabled and self._start_time is not None:
            elapsed = time.time() - self._start_time
        if self.exam_mode:
            ExamSummaryDialog(self, self._exam_results, self.master_intro, elapsed)
            return
        summary = self.service.build_session_summary(
            self.all_questions, self.all_results
        )
        summary.elapsed_seconds = elapsed
        SessionSummaryDialog(self, summary, self.service, self.master_intro, self.fill_mode)

    def _close(self) -> None:
        self.destroy()
        self.master_intro.deiconify()


class SessionSummaryDialog(tk.Toplevel):
    def __init__(
        self,
        master: SessionWindow,
        summary,
        service: LearningService,
        intro_window: IntroWindow,
        fill_mode: bool = False,
    ) -> None:
        super().__init__(master)
        self.summary = summary
        self.service = service
        self.intro_window = intro_window
        self.master_session = master
        self.review_started = False
        self.fill_mode = fill_mode

        self.title("Session Complete")
        self.geometry("760x480")
        self.minsize(640, 360)
        self.transient(master)
        self.grab_set()

        self._build()

    def _build(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            container,
            text="Session Summary",
            font=(FONT_FAMILY, 14, "bold"),
        ).pack(anchor=tk.W)

        s = self.summary
        details = f"Passed: {s.passed_count} of {s.total_questions}"
        if s.elapsed_seconds is not None:
            minutes, secs = divmod(int(s.elapsed_seconds), 60)
            details += f"\nTime: {minutes}m {secs}s"

        ttk.Label(container, text=details, justify=tk.LEFT).pack(
            anchor=tk.W, pady=12
        )

        # Aggregate results by question
        sorted_results = sorted(s.results, key=lambda r: r.question.index)
        question_map: dict[str, dict] = {}
        for r in sorted_results:
            qid = r.question.id
            if qid not in question_map:
                question_map[qid] = {
                    "number": r.question.index + 1,
                    "question": r.question.question,
                    "first_score": None,
                    "first_time_spent": None,
                    "attempts": 0,
                    "last_score": None,
                    "last_time_spent": None,
                    "passed": False,
                }
            entry = question_map[qid]
            if entry["first_score"] is None and r.score is not None:
                entry["first_score"] = r.score
                entry["first_time_spent"] = r.time_spent
            if r.score is not None:
                entry["last_score"] = r.score
                entry["last_time_spent"] = r.time_spent
                entry["passed"] = r.passed
            entry["attempts"] += 1

        table_rows = list(question_map.values())
        has_any_not_passed = any(not row["passed"] for row in table_rows)

        # Treeview table — skip in learn mode
        if self.fill_mode or self.master_session.exam_mode:
            list_frame = ttk.Frame(container)
            list_frame.pack(fill=tk.BOTH, expand=True)

            columns = ("num", "question", "first_score", "first_time", "last_score", "last_time", "passed", "attempts")
            tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=min(len(table_rows), 12))
            tree.heading("num", text="#")
            tree.heading("question", text="Question")
            tree.heading("first_score", text="First Score")
            tree.heading("first_time", text="First Time")
            tree.heading("last_score", text="Last Score")
            tree.heading("last_time", text="Last Time")
            tree.heading("passed", text="Passed")
            tree.heading("attempts", text="Att.")

            tree.column("num", width=40, anchor=tk.CENTER)
            tree.column("question", width=220, anchor=tk.W)
            tree.column("first_score", width=70, anchor=tk.CENTER)
            tree.column("first_time", width=70, anchor=tk.CENTER)
            tree.column("last_score", width=70, anchor=tk.CENTER)
            tree.column("last_time", width=70, anchor=tk.CENTER)
            tree.column("passed", width=55, anchor=tk.CENTER)
            tree.column("attempts", width=45, anchor=tk.CENTER)

            for row in table_rows:
                first_score = f"{row['first_score']:.0f}%" if row['first_score'] is not None else "-"
                last_score = f"{row['last_score']:.0f}%" if row['last_score'] is not None else "-"
                passed_str = "Yes" if row["passed"] else "No"
                tree.insert("", tk.END, values=(
                    f"Q{row['number']}",
                    row["question"],
                    first_score,
                    _fmt_time(row['first_time_spent']),
                    last_score,
                    _fmt_time(row['last_time_spent']),
                    passed_str,
                    row["attempts"],
                ))

            tree.pack(fill=tk.BOTH, expand=True)

            if has_any_not_passed:
                ttk.Button(
                    container,
                    text="Review Missed Questions",
                    command=self._review_missed,
                ).pack(anchor=tk.W, pady=(8, 0))
            else:
                ttk.Label(
                    container,
                    text="\u2705 All questions passed! Great job.",
                    foreground="#070",
                ).pack(anchor=tk.W, pady=(8, 0))

        ttk.Button(
            container, text="Back to Themes", command=self._close_dialog
        ).pack(anchor=tk.E, pady=8)

    def _review_missed(self) -> None:
        self.review_started = True
        missed_qs = [r.question for r in self.summary.missed_questions]
        all_results = list(self.master_session.all_results)
        all_questions = list(self.master_session.all_questions)
        intro = self.intro_window
        service = self.service
        self.master_session.destroy()
        sw = SessionWindow(master=intro, service=service, questions=missed_qs)
        sw.all_results = all_results
        sw.all_questions = all_questions

    def _close_dialog(self) -> None:
        self.review_started = False
        intro = self.intro_window
        # Destroy the session window (parent) — this also destroys this dialog
        self.master_session.destroy()
        intro.deiconify()

    # No custom destroy() — Tkinter's default handles parent-child cleanup safely


class ExamSummaryDialog(tk.Toplevel):
    def __init__(
        self,
        master: SessionWindow,
        exam_results: list[dict],
        intro_window: IntroWindow,
        elapsed_seconds: float | None = None,
    ) -> None:
        super().__init__(master)
        self.exam_results = exam_results
        self.intro_window = intro_window
        self.master_session = master
        self.elapsed_seconds = elapsed_seconds

        self.title("Exam Results")
        self.geometry("520x480")
        self.minsize(420, 360)
        self.transient(master)
        self.grab_set()

        self._build()

    def _build(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            container,
            text="Exam Results",
            font=(FONT_FAMILY, 14, "bold"),
        ).pack(anchor=tk.W)

        scores = [r["score"] for r in self.exam_results if r["score"] is not None]
        overall = sum(scores) / len(scores) if scores else 0.0
        passed = sum(1 for r in self.exam_results if r["passed"])
        failed = sum(1 for r in self.exam_results if not r["passed"])

        details = (
            f"Questions: {len(self.exam_results)}\n"
            f"Overall score: {overall:.0f}%\n"
            f"Passed: {passed}  |  Failed: {failed}"
        )
        if self.elapsed_seconds is not None:
            minutes, secs = divmod(int(self.elapsed_seconds), 60)
            details += f"\nTime: {minutes}m {secs}s"
        ttk.Label(container, text=details, justify=tk.LEFT).pack(
            anchor=tk.W, pady=12
        )

        if self.exam_results:
            ttk.Label(
                container,
                text="Results per question:",
                font=(FONT_FAMILY, 10, "bold"),
            ).pack(anchor=tk.W, pady=(12, 4))

            list_frame = ttk.Frame(container)
            list_frame.pack(fill=tk.BOTH, expand=True)

            canvas = tk.Canvas(list_frame, highlightthickness=0)
            scrollbar = ttk.Scrollbar(
                list_frame, orient=tk.VERTICAL, command=canvas.yview
            )
            inner = ttk.Frame(canvas)

            inner.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
            )
            canvas.create_window((0, 0), window=inner, anchor=tk.NW)
            canvas.configure(yscrollcommand=scrollbar.set)

            for r in self.exam_results:
                score = r["score"]
                text = f"\u2022 {r['question'].question} ({score:.0f}%)" if score is not None else f"\u2022 {r['question'].question}"
                ttk.Label(
                    inner,
                    text=text,
                    wraplength=420,
                ).pack(anchor=tk.W, pady=1)

            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_row = ttk.Frame(container)
        btn_row.pack(fill=tk.X, pady=8)
        ttk.Button(
            btn_row, text="Back to Themes", command=self._close_dialog
        ).pack(side=tk.RIGHT)

    def _close_dialog(self) -> None:
        self.master_session.destroy()
        self.intro_window.deiconify()