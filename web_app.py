from __future__ import annotations

import contextlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import jinja2
import markdown as md_lib
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from interview_learner.cloze import RuleBasedClozeGenerator
from interview_learner.config import AppSettings
from interview_learner.grading import ExactGrader
from interview_learner.memory_progress import MemoryProgressStore
from interview_learner.models import (
    BLANK_CHAR,
    ClozeState,
    LearningStage,
    QuestionResult,
    progressive_reveal,
)
from interview_learner.ollama_client import OllamaClient
from interview_learner.parser import (
    discover_themes_with_counts,
    load_questions,
    theme_display_name,
)
from interview_learner.service import LearningService

# ---------------------------------------------------------------------------
# Jinja2 setup — fresh environment, no template cache
# (avoids LRUCache hashability issues in some Jinja2 versions)
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=True,
    cache_size=0,
)

# Markdown-to-HTML filter
_extensions = ["fenced_code", "codehilite", "tables"]


def _md_filter(text: str) -> str:
    return md_lib.markdown(text, extensions=_extensions)


_env.filters["markdown"] = _md_filter
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)


def _render(name: str, **context: Any) -> str:
    template = _env.get_template(name)
    return template.render(**context)


def _fmt_time(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    secs = int(seconds)
    if secs < 60:
        return f"{secs}s"
    return f"{secs // 60}m {secs % 60}s"


# ---------------------------------------------------------------------------
# Global state (single-user local app)
# ---------------------------------------------------------------------------

settings = AppSettings()
service = LearningService(settings)
themes = discover_themes_with_counts(settings.questions_dir)

ollama_available = False
ollama_models: list[str] = []

sessions: dict[str, dict[str, Any]] = {}

STAGE_LABELS = {
    LearningStage.READ: "Read (100%)",
    LearningStage.CLOZE_75: "Recall (75% visible)",
    LearningStage.CLOZE_50: "Recall (50% visible)",
    LearningStage.CLOZE_25: "Recall (25% visible)",
    LearningStage.MASTERED: "Mastered",
}


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    global ollama_available, ollama_models
    client = OllamaClient(settings.ollama_url, settings.ollama_model)
    ollama_available = client.is_available()
    if ollama_available:
        ollama_models = client.list_models()
    yield


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Interview Learner", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "interview-learner-dev-secret-change-in-prod"),
    max_age=86400,
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _get_session(request: Request) -> dict[str, Any]:
    sid = request.session.get("sid")
    if sid and sid in sessions:
        return sessions[sid]
    sid = uuid.uuid4().hex[:16]
    request.session["sid"] = sid
    data: dict[str, Any] = {
        "questions": [],
        "all_questions": None,
        "index": 0,
        "results": [],
        "cloze": None,
        "submitted": False,
        "grade": None,
        "exam_mode": False,
        "progress_data": {},
    }
    sessions[sid] = data
    return data


def _end_session(request: Request) -> None:
    sid = request.session.pop("sid", None)
    if sid and sid in sessions:
        del sessions[sid]


def _get_question(request: Request) -> tuple[dict, Any, int | None]:
    sd = _get_session(request)
    idx = sd["index"]
    questions = sd["questions"]
    if idx >= len(questions) or not questions:
        return sd, None, None
    return sd, questions[idx], idx


# ---------------------------------------------------------------------------
# Cloze helpers
# ---------------------------------------------------------------------------

def _build_masked_parts(cs: ClozeState, reveal_all: bool = False) -> list[dict]:
    parts: list[dict] = []
    text = cs.result.original
    gaps = cs.result.gaps
    pos = 0
    for i, gap in enumerate(gaps):
        if gap.start > pos:
            parts.append({"type": "text", "content": text[pos : gap.start]})
        cnt = cs.revealed_counts.get(i, 0)
        if reveal_all:
            label = gap.hidden_text
        else:
            label = progressive_reveal(gap.hidden_text, cnt) if cnt > 0 else ""
        parts.append(
            {
                "type": "blank",
                "index": i,
                "hinted": cnt > 0,
                "label": label,
            }
        )
        pos = gap.end
    if pos < len(text):
        parts.append({"type": "text", "content": text[pos:]})
    return parts


def _build_masked_text(cs: ClozeState, reveal_all: bool = False) -> str:
    text = cs.result.original
    gaps = cs.result.gaps
    result: list[str] = []
    pos = 0
    for i, gap in enumerate(gaps):
        if gap.start > pos:
            result.append(text[pos : gap.start])
        if reveal_all:
            result.append(gap.hidden_text)
        else:
            cnt = cs.revealed_counts.get(i, 0)
            result.append(progressive_reveal(gap.hidden_text, cnt) if cnt > 0 else BLANK_CHAR * max(4, len(gap.hidden_text)))
        pos = gap.end
    if pos < len(text):
        result.append(text[pos:])
    return "".join(result)


def _cloze_to_dict(cs: ClozeState, reveal_all: bool = False) -> dict:
    parts = _build_masked_parts(cs, reveal_all=reveal_all)
    masked_text = _build_masked_text(cs, reveal_all=reveal_all)
    gaps = [
        {
            "index": i,
            "hidden_text": g.hidden_text,
            "hinted": i in cs.hinted_indices,
            "revealed_count": cs.revealed_counts.get(i, 0),
            "width": max(12, len(g.hidden_text) + 2),
            "display_text": progressive_reveal(g.hidden_text, cs.revealed_counts.get(i, 0)) if cs.revealed_counts.get(i, 0) > 0 else "",
        }
        for i, g in enumerate(cs.result.gaps)
    ]
    remaining = 0 if cs.next_hint_index() is None else 1
    return {
        "is_read_mode": cs.is_read_mode,
        "masked_parts": parts,
        "masked_text": masked_text,
        "gaps": gaps,
        "hint_count": remaining,
        "total_hints": len(cs.result.gaps),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def intro_page(request: Request) -> HTMLResponse:
    _end_session(request)
    themedata = sorted(
        [
            {"name": name, "display": theme_display_name(name), "count": count}
            for name, (_, count) in themes.items()
        ],
        key=lambda x: x["name"],
    )
    html = _render(
        "intro.html",
        themes=themedata,
        ollama_available=ollama_available,
        ollama_models=ollama_models,
        default_model=settings.ollama_model,
    )
    return HTMLResponse(content=html)


@app.post("/start")
def start_session(
    request: Request,
    selected_themes: list[str] = Form(default=[], alias="themes"),
    count: int = Form(default=5),
    use_ollama_cloze: bool = Form(False),
    use_ollama_grading: bool = Form(False),
    ollama_model: str = Form(""),
    exam_mode: bool = Form(False),
    visibility: float = Form(1.0),
    timer_enabled: bool = Form(False),
    progress_data: str = Form(default="{}"),
) -> RedirectResponse:
    if not selected_themes:
        return RedirectResponse(url="/", status_code=303)

    paths = [themes[t][0] for t in selected_themes if t in themes]
    questions = load_questions(paths)
    if not questions:
        return RedirectResponse(url="/", status_code=303)

    settings.use_ollama_cloze = use_ollama_cloze
    settings.use_ollama_grading = use_ollama_grading
    if ollama_model:
        settings.ollama_model = ollama_model

    mem_store = MemoryProgressStore.from_dict(json.loads(progress_data))
    local_service = LearningService(settings, progress_store=mem_store)
    picked = local_service.prepare_session(questions, count)

    sd = _get_session(request)
    sd["questions"] = picked
    sd["index"] = 0
    sd["results"] = []
    sd["cloze"] = None
    sd["submitted"] = False
    sd["grade"] = None
    sd["exam_mode"] = exam_mode
    sd["visibility"] = visibility
    sd["fill_mode"] = not exam_mode and visibility < 1.0
    sd["timer_enabled"] = timer_enabled or (not exam_mode and visibility >= 1.0)
    sd["start_time"] = time.time() if timer_enabled else None
    sd["question_start_time"] = time.time() if timer_enabled else None
    sd["progress_data"] = mem_store.to_dict()

    return RedirectResponse(url="/session", status_code=303)


@app.get("/session", response_class=HTMLResponse)
def session_page(request: Request) -> HTMLResponse:
    sd, q, idx = _get_question(request)
    if q is None:
        return RedirectResponse(url="/summary", status_code=303)

    exam_mode = sd.get("exam_mode", False)
    visibility = sd.get("visibility", 1.0)

    if sd["cloze"] is None and not exam_mode:
        cloze_gen = RuleBasedClozeGenerator()
        cloze_result = cloze_gen.generate(q.answer, visibility)
        cs = ClozeState(result=cloze_result)
        sd["cloze"] = cs
        sd["submitted"] = False
        sd["grade"] = None

    cs: ClozeState | None = sd.get("cloze")
    grade = sd.get("grade")

    progress_json = json.dumps(sd.get("progress_data", {}))

    html = _render(
        "session.html",
        question=q,
        progress=f"{idx + 1} / {len(sd['questions'])}",
        theme_display=theme_display_name(q.theme),
        cloze=_cloze_to_dict(cs, reveal_all=sd["submitted"]) if cs else None,
        submitted=sd["submitted"],
        grade=grade,
        exam_mode=exam_mode,
        total_questions=len(sd["questions"]),
        progress_json=progress_json,
    )
    return HTMLResponse(content=html)


@app.post("/submit")
async def submit_answer(request: Request) -> RedirectResponse:
    sd = _get_session(request)
    exam_mode = sd.get("exam_mode", False)
    if sd["submitted"]:
        return RedirectResponse(url="/session", status_code=303)

    idx = sd["index"]
    questions = sd["questions"]
    if idx >= len(questions):
        return RedirectResponse(url="/summary", status_code=303)

    q = questions[idx]
    cs: ClozeState | None = sd.get("cloze")
    local_service = LearningService(settings)

    form = await request.form()

    progress_data_str = form.get("progress_data", "{}")
    mem_store = MemoryProgressStore.from_dict(json.loads(progress_data_str))
    local_service = LearningService(settings, progress_store=mem_store)

    # ----- Exam mode (textarea full answer graded by Ollama) -----
    if exam_mode:
        user_answer = form.get("user_answer", "")
        expected_raw = q.answer
        if q.source:
            expected_raw += "\n\n" + q.source
        exam_grade = _grade_full_answer(user_answer, expected_raw)
        exam_grade["user_answer"] = user_answer
        attempt = sum(1 for r in sd["results"] if r.question.id == q.id) + 1
        time_spent = None
        if sd.get("timer_enabled") and sd.get("question_start_time") is not None:
            time_spent = time.time() - sd["question_start_time"]
        sd["results"].append(
            QuestionResult(
                question=q,
                stage_before=local_service.stage_for(q),
                stage_after=local_service.stage_for(q),
                score=exam_grade["overall_score"],
                passed=exam_grade["overall_score"] >= settings.pass_threshold,
                cloze=None,
                attempt=attempt,
                time_spent=time_spent,
            )
        )
        sd["submitted"] = True
        sd["grade"] = exam_grade
        sd["progress_data"] = mem_store.to_dict()
        return RedirectResponse(url="/session", status_code=303)

    # ----- Learning mode: cloze (gap inputs) -----
    user_inputs: list[str] = []
    i = 0
    while f"gap_{i}" in form:
        user_inputs.append(form[f"gap_{i}"])
        i += 1

    grader = ExactGrader(settings.pass_threshold)
    grade = grader.grade(q.answer, cs.result.gaps, user_inputs)
    new_stage = local_service.complete_question(q, grade)
    attempt = sum(1 for r in sd["results"] if r.question.id == q.id) + 1
    time_spent = None
    if sd.get("timer_enabled") and sd.get("question_start_time") is not None:
        time_spent = time.time() - sd["question_start_time"]
    sd["results"].append(
        QuestionResult(
            question=q,
            stage_before=local_service.stage_for(q),
            stage_after=new_stage,
            score=grade.overall_score,
            passed=grade.passed,
            cloze=cs.result,
            attempt=attempt,
            time_spent=time_spent,
        )
    )
    sd["submitted"] = True
    sd["grade"] = {
        "overall_score": grade.overall_score,
        "passed": grade.passed,
        "summary": grade.summary,
        "gap_grades": [
            {
                "index": g.gap_index,
                "expected": g.expected,
                "user_input": g.user_input,
                "score": g.score,
                "feedback": g.feedback,
            }
            for g in grade.gap_grades
        ],
    }
    sd["progress_data"] = mem_store.to_dict()

    return RedirectResponse(url="/session", status_code=303)


def _grade_full_answer(user_answer: str, expected_answer: str) -> dict:
    """Grade a full-text answer using Ollama, fall back to simple comparison."""
    if ollama_available:
        try:
            client = OllamaClient(settings.ollama_url, settings.ollama_model)
            prompt = (
                "You are grading an interview answer. Compare the user's answer to the expected answer.\n\n"
                f"Expected answer:\n{expected_answer}\n\n"
                f"User's answer:\n{user_answer}\n\n"
                "Return ONLY valid JSON: {\"score\": <0-100>, \"feedback\": \"<brief feedback>\"}\n"
                "Score 100 for a perfect answer, 70+ for acceptable, below 70 for insufficient."
            )
            raw = client.generate(prompt, format_json=True)
            import json
            payload = json.loads(raw)
            score = max(0, min(100, int(payload.get("score", 0))))
            return {
                "overall_score": score,
                "passed": score >= settings.pass_threshold,
                "summary": payload.get("feedback", ""),
                "gap_grades": [],
            }
        except Exception:
            pass

    # Fallback: string similarity
    from interview_learner.grading import _similarity
    score = _similarity(user_answer, expected_answer)
    return {
        "overall_score": score,
        "passed": score >= settings.pass_threshold,
        "summary": "Similarity score (no Ollama available).",
        "gap_grades": [],
    }


@app.post("/next")
def next_question(request: Request) -> RedirectResponse:
    sd = _get_session(request)
    sd["index"] += 1
    sd["cloze"] = None
    sd["submitted"] = False
    sd["grade"] = None
    if sd.get("timer_enabled"):
        sd["question_start_time"] = time.time()
    return RedirectResponse(url="/session", status_code=303)


@app.post("/mark-read")
async def mark_read(request: Request) -> RedirectResponse:
    sd = _get_session(request)
    idx = sd["index"]
    questions = sd["questions"]
    if idx < len(questions):
        q = questions[idx]
        form = await request.form()
        progress_data_str = form.get("progress_data", "{}")
        mem_store = MemoryProgressStore.from_dict(json.loads(progress_data_str))
        local_service = LearningService(settings, progress_store=mem_store)
        cs: ClozeState | None = sd.get("cloze")
        new_stage = local_service.complete_question(q, grade=None)
        attempt = sum(1 for r in sd["results"] if r.question.id == q.id) + 1
        time_spent = None
        if sd.get("timer_enabled") and sd.get("question_start_time") is not None:
            time_spent = time.time() - sd["question_start_time"]
        sd["results"].append(
            QuestionResult(
                question=q,
                stage_before=local_service.stage_for(q),
                stage_after=new_stage,
                score=None,
                passed=True,
                cloze=cs.result if cs else None,
                attempt=attempt,
                time_spent=time_spent,
            )
        )
        sd["progress_data"] = mem_store.to_dict()
    sd["index"] += 1
    sd["cloze"] = None
    sd["submitted"] = False
    sd["grade"] = None
    if sd.get("timer_enabled"):
        sd["question_start_time"] = time.time()
    return RedirectResponse(url="/session", status_code=303)


@app.post("/hint")
def hint_question(request: Request) -> RedirectResponse:
    sd = _get_session(request)
    if sd.get("exam_mode", False):
        return RedirectResponse(url="/session", status_code=303)
    cs: ClozeState = sd.get("cloze")
    if cs and not sd["submitted"]:
        cs.reveal_hint()
    return RedirectResponse(url="/session", status_code=303)


@app.get("/summary", response_class=HTMLResponse)
def summary_page(request: Request) -> HTMLResponse:
    sd = _get_session(request)
    results = sd["results"]
    questions = sd.get("all_questions") or sd["questions"]
    exam_mode = sd.get("exam_mode", False)

    scores = [r.score for r in results if r.score is not None]
    overall = sum(scores) / len(scores) if scores else None
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if r.score is not None and not r.passed)

    elapsed_seconds = None
    if sd.get("timer_enabled") and sd.get("start_time") is not None:
        elapsed_seconds = time.time() - sd["start_time"]

    sorted_results = sorted(results, key=lambda x: x.question.index)

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
    for row in table_rows:
        row["first_score_fmt"] = f"{row['first_score']:.0f}%" if row["first_score"] is not None else "-"
        row["last_score_fmt"] = f"{row['last_score']:.0f}%" if row["last_score"] is not None else "-"
        row["first_time_fmt"] = _fmt_time(row["first_time_spent"])
        row["last_time_fmt"] = _fmt_time(row["last_time_spent"])
    has_any_not_passed = any(not row["passed"] for row in table_rows)

    progress_json = json.dumps(sd.get("progress_data", {}))

    html = _render(
        "summary.html",
        total_questions=len(questions),
        completed=len(results),
        overall_score=f"{overall:.0f}%" if overall is not None else "N/A",
        passed_count=passed,
        failed_count=failed,
        table_rows=table_rows,
        has_any_not_passed=has_any_not_passed,
        exam_mode=exam_mode,
        elapsed_seconds=elapsed_seconds,
        show_table=sd.get("exam_mode") or sd.get("fill_mode"),
        progress_json=progress_json,
    )
    return HTMLResponse(content=html)


@app.post("/review")
def review_missed(request: Request) -> RedirectResponse:
    sd = _get_session(request)
    # Only consider the final result per question to determine missed
    final_by_q: dict[str, bool] = {}
    for r in sd["results"]:
        if r.score is not None:
            final_by_q[r.question.id] = r.passed
    missed_ids = [qid for qid, passed in final_by_q.items() if not passed]
    all_questions = sd["questions"]
    missed_qs = [q for q in all_questions if q.id in missed_ids]

    if not missed_qs:
        return RedirectResponse(url="/", status_code=303)

    if sd["all_questions"] is None:
        sd["all_questions"] = all_questions[:]
    sd["questions"] = missed_qs
    sd["index"] = 0
    sd["cloze"] = None
    sd["submitted"] = False
    sd["grade"] = None

    return RedirectResponse(url="/session", status_code=303)