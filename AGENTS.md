# Interview Learner

Python active-recall interview prep. Two entry points: `main.py` (Tkinter desktop) and `web_app.py` (FastAPI web).

## Commands

```bash
pip install -r requirements.txt                  # deps: httpx, fastapi, uvicorn, jinja2, markdown
sudo apt install python3-tk                      # tkinter — not pip-installable
python main.py                                   # desktop
python web_app.py                                # web → http://localhost:8000
uvicorn web_app:app                              # alternative web start
```

No test, lint, typecheck, or CI pipeline exists.

## Progress Storage

- **Desktop**: SQLite via `ProgressStore` → `data/progress.db` (auto-created, gitignored)
- **Web**: browser `localStorage`. Backend uses `MemoryProgressStore` (in-memory dict), serialized as JSON and synced with client. No SQLite touched.
- SM-2 algorithm in `progress.py` (`sm2_next()`)
- `ProgressStore.pick_questions()` sort order: due for review → favorite → stage → times_seen → last_reviewed
- Column migrations applied on startup via `ALTER TABLE ADD COLUMN`
- On Vercel: `DATA_DIR=/tmp/data` (ephemeral), `VERCEL` env var set

## Web Peculiarities

- Session state in global `sessions` dict, keyed by `sid` cookie (24h via `SessionMiddleware`)
- Progress flows: client reads from `localStorage`, sends as hidden form field `progress_data` on every POST; server embeds updated progress JSON in rendered pages
- Ollama availability checked once on startup via `lifespan` handler
- Template engine: Jinja2 with `cache_size=0`, Markdown filter via `markdown` lib (fenced_code + codehilite + tables)
- `SessionMiddleware` secret from `SESSION_SECRET` env, default `interview-learner-dev-secret-change-in-prod`

## Key Conventions

- `BLANK_CHAR = "\u25a8"` (`▨`) in `models.py` — used by both UIs
- Visibility: `max(0.0, 1.0 - gaps / 100)`
- `Source:` / `Reference:` lines stripped from answer → never hidden by cloze; hidden in fill/exam modes
- Theme name from filename: `en_q&a_db_internals.md` → `"db_internals"`; display overrides in `parser._THEME_LABEL_OVERRIDES`
- `en_q&a_general.md` has one malformed entry (`## Layers?` with no answer) — silently skipped
- Grading: ExactGrader uses LCS gate (>45%) + Levenshtein; order-independent matching per gap
- Hints use round-robin reveal pattern in `ClozeState.reveal_hint()`
- Review Missed Questions preserves all attempt history
- New question format: `### Q1: question / **Answer:** answer / ---` (parser auto-detects)

## Files to Know

| File | Role |
|---|---|
| `interview_learner/config.py` | Paths, constants, `AppSettings` |
| `interview_learner/progress.py` | SM-2, SQLite schema |
| `interview_learner/memory_progress.py` | In-memory progress store (web), JSON-serializable |
| `interview_learner/models.py` | `ClozeState`, `Question`, `QuestionResult` — core data flow types |
| `interview_learner/cloze.py` | `RuleBasedClozeGenerator` — stopwords list, priority by word length/caps |
| `interview_learner/parser.py` | `_FORMAT_RE` for new-style Q&A, `_make_id()` for stable question IDs |
