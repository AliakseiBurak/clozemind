# Interview Learner

A Python application for active-recall interview preparation using progressive cloze deletion. Ships as both a **Tkinter desktop app** and a **FastAPI web app**.

## Quick Start

```bash
# 1. Install system dependency (tkinter — not a pip package)
#    Ubuntu/Debian:
sudo apt-get install python3-tk
#    Fedora:
sudo dnf install python3-tkinter
#    Arch:
sudo pacman -S tk
#    macOS: included with Python.org installer
#    Windows: included with the Windows installer

# 2. Install Python dependencies
pip install -r requirements.txt

# 3a. Desktop
python main.py

# 3b. Web (http://localhost:8000)
python web_app.py
```

## Project Structure

```
/workspace/
├── main.py                          # Desktop entry point
├── web_app.py                       # Web entry point (FastAPI)
├── requirements.txt                 # httpx + uvicorn + fastapi + jinja2 + markdown
├── .gitignore
├── QWEN.md
├── README.md
├── interview_learner/               # Application package
│   ├── __init__.py                  # Version: 0.1.0
│   ├── config.py                    # Constants, paths, AppSettings dataclass
│   ├── models.py                    # Data classes (Question, ClozeResult, ClozeState, etc.)
│   ├── parser.py                    # Markdown Q&A file parser (strips Source/Reference)
│   ├── cloze.py                     # Cloze generation (rule-based + Ollama LLM)
│   ├── grading.py                   # Answer grading (fuzzy match + Ollama LLM)
│   ├── progress.py                  # SQLite progress store + SM-2 algorithm
│   ├── service.py                   # Orchestration layer
│   ├── ollama_client.py             # HTTP client for local Ollama LLM
│   └── gui.py                       # Tkinter UI (IntroWindow, SessionWindow, SummaryDialog)
├── templates/                       # Jinja2 templates for web app
│   ├── base.html
│   ├── intro.html
│   ├── session.html
│   └── summary.html
├── static/
│   └── style.css                    # Web app styles
├── questions/                       # Markdown Q&A files (one per theme)
│   ├── example_general.md
│   ├── en_q&a_general.md
│   ├── en_q&a_db_internals.md
│   ├── en_q&a_distributed_systems.md
│   ├── en_q&a_laravel.md
│   └── ...                          # 18 theme files total
└── data/                            # Created at runtime (gitignored)
    └── progress.db                  # SQLite database
```

## Learning Modes

| Mode | Button | Behaviour |
|---|---|---|
| **Learn** | "Learn" | Full answer shown — read mode. Click "Got it — Next" to mark as read. |
| **Fill in gaps** | "Fill in X%" | Some content words replaced by `▨` blanks. Type missing words into input fields. Graded by fuzzy matching. |
| **Start Exam** | "Start Exam" | Full free-form textarea. Answer graded by Ollama (or difflib fallback). Requires Ollama to be running. |

### Gaps (%) control

A spinbox/input below "Questions per session" controls what percentage of content words are hidden:

- **0%** = full answer visible (same as Learn)
- **50%** = half of content words hidden (default)
- **100%** = all content words hidden

Visibility is computed as `max(0.0, 1.0 - gaps / 100)`. Learn mode always uses 1.0 regardless of the spinbox value.

## Architecture

### Learning Pipeline

1. **Parse** — Markdown files in `questions/` are parsed into `Question` objects (`parser.py`). Lines starting with `**Source:**` or `**Reference:**` are stripped from the answer and stored as `Question.source`.
2. **Select** — `ProgressStore.pick_questions()` selects questions using SM-2 priority sorting.
3. **Cloze** — Answer text is transformed into a cloze exercise at the user-specified visibility level (`cloze.py`). Source/Reference text is never hidden.
4. **Display** — Tkinter GUI or web template shows the question and cloze answer.
5. **Grade** — User input is scored against expected terms (`grading.py`); exam mode uses Ollama.
6. **Advance** — Progress is recorded; SM-2 state is updated.

### Learning Stages (legacy)

Before the configurable gaps % was introduced, stages defined fixed visibility levels. These are still used internally for progress tracking:

| Stage | Visibility | Description |
|---|---|---|
| READ (0) | 100% | First pass — read the full Q&A |
| CLOZE_75 (1) | 75% | 25% of content words hidden |
| CLOZE_50 (2) | 50% | 50% of content words hidden |
| CLOZE_25 (3) | 25% | 75% of content words hidden |
| MASTERED (4) | — | Question is "graduated"; still appears occasionally |

When using "Fill in gaps" mode, `service.build_cloze_state()` accepts a `visibility` parameter that overrides the stage-based visibility.

### Cloze Generation

- **Rule-based** (default): Hides content words proportionally by importance (word length, capitalization). Stopwords and short words are kept visible.
- **Ollama LLM** (optional): Asks a local LLM to pick key concepts to hide. Falls back to rule-based on failure.

### Blank Character

All hidden text uses `BLANK_CHAR = "\u25a8"` (`▨`):

- Un-hinted blanks: `▨` repeated to fill the gap width
- Hinted blanks: first N characters shown, rest remain `▨`

This constant is defined in `models.py` and used by both the desktop and web UI.

### Hints

Hints progressively reveal letters in hidden words using a round-robin pattern:

- **Hint 1**: gap[0] gets 2 letters, gap[1] gets 1 letter
- **Hint 2**: gap[0] gets +1, gap[1] gets +2, gap[2] gets +1
- **Hint N**: gap[N-1] gets +1, gap[N] gets +2, gap[N+1] gets +1
- When the window passes beyond the last gap, remaining characters are filled 1-at-a-time starting from the first unrevealed gap

Revealed letters are shown in the masked paragraph display (not in the input fields). The hint button disables once all gaps are fully revealed.

### Grading

- **ExactGrader** (default / fill mode): String similarity via LCS gate + Levenshtein distance. Two different words sharing scattered characters score 0%; a minor typo or suffix variant scores proportionally to edit distance.
- **OllamaGrader** (exam mode): Asks a local LLM to evaluate answers semantically (accepts synonyms, rephrasing). Falls back to ExactGrader on failure.

### Spaced Repetition (SM-2)

SM-2 state is stored per question in the SQLite database:

- `easiness_factor` (EF, default 2.5, min 1.3)
- `interval_days` (days until next review)
- `next_review_date` (ISO date)
- `repetitions` (consecutive correct recalls)

**`pick_questions()` priority order** (lowest sort key first):
1. Due for review (`next_review_date <= today`)
2. Lower learning stage
3. Fewer times seen
4. Least recently reviewed

## Question File Format

Place `.md` files in `questions/`. Each file contains questions separated by `---` lines:

```markdown
# Optional Title

## What is the CAP theorem?

The **CAP theorem** states that a distributed system can provide at most two of
three guarantees simultaneously: **Consistency**, **Availability**, and
**Partition tolerance**.

---

## Describe the SOLID principles.

**SOLID** stands for: Single Responsibility, Open/Closed, Liskov Substitution,
Interface Segregation, and Dependency Inversion.
```

- Each question starts with a `## Question text` heading
- Answer follows the heading (may include code blocks, tables, lists)
- Questions are separated by `---` on its own line
- `**A:**` prefix at the start of an answer is stripped automatically
- Lines starting with `**Source:**` or `**Reference:**` are extracted into `Question.source` and displayed separately (never hidden by cloze)

### Theme Detection

Theme name is derived from the filename: `en_q&a_db_internals.md` → `"db_internals"`. Display names are mapped via `_THEME_LABEL_OVERRIDES` in `parser.py` (e.g., `"db_internals"` → `"Database Internals"`).

## GUI Features

### Intro (Desktop + Web)

- Scrollable theme list with Select All / Deselect All buttons
- Questions per session spinner (1–50)
- Gaps % input (0–100, default 50)
- Three action buttons: **Learn**, **Fill in gaps** (uses gaps %), **Start Exam**
- Exam button disabled when Ollama is unavailable (web) or hidden (desktop)
- All action buttons disabled when no themes are selected (web JS)
- Optional Ollama AI settings with connection check
- Exam requires Ollama; button is disabled when Ollama unavailable

### Session (Desktop)

- **Keyboard shortcuts**: `Enter`/`Space` submit, `Escape` exit, `H` hint
- **Hints**: Progressive letter reveal via the hint button or `H` key
- **Answer reference**: Toggle full answer text without breaking the exercise (press `A` or click button)
- **Stage indicator**: Shows current SM-2 stage

### Session (Web)

- Masked paragraph display shows `▨` blanks with progressive hint reveal
- Gap input fields for fill mode
- Textarea for exam mode with "Check Answer" button
- End Session button right-aligned on the same row as the primary action button

### Summary Dialog (Desktop) / Summary Page (Web)

- Overall score percentage
- Answers Given count (total attempts across all review cycles)
- Passed / Failed counts
- Per-question table with First Score, Attempts, Final Score, and Passed status
- Questions are sorted by original question index
- "Review Missed Questions" button (only shown when at least one question remains not passed)
- "All questions passed!" message when every question has passed on its final attempt
- Save PDF button

## Configuration (`interview_learner/config.py`)

| Constant | Default | Description |
|---|---|---|
| `PASS_THRESHOLD` | 70 | Minimum score (0–100) to advance a stage |
| `SM2_DEFAULT_EF` | 2.5 | Initial SM-2 easiness factor |
| `SM2_MIN_EF` | 1.3 | Minimum SM-2 easiness factor |
| `DEFAULT_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `DEFAULT_OLLAMA_MODEL` | `llama3.2` | Default LLM model |
| `PROGRESS_DB` | `data/progress.db` | SQLite database path |
| `QUESTIONS_DIR` | `questions/` | Default questions directory |

## Ollama Integration (Optional)

Enable in the intro window under "Ollama AI":
- **Semantic cloze**: LLM picks key concepts to hide instead of rule-based selection
- **AI grading (fill mode)**: LLM evaluates answers semantically (accepts synonyms/paraphrases)
- **AI grading (exam mode)**: LLM evaluates full-text free-form answers (used by default in exam mode)
- Connection is tested when toggling checkboxes; falls back to local algorithms if unavailable

## Data Storage

Progress is stored in `data/progress.db` (SQLite, auto-created, gitignored). Schema:

```sql
CREATE TABLE question_progress (
    question_id     TEXT PRIMARY KEY,
    theme           TEXT NOT NULL,
    stage           INTEGER NOT NULL DEFAULT 0,
    times_seen      INTEGER NOT NULL DEFAULT 0,
    last_score      REAL,
    last_reviewed   TEXT,
    easiness_factor REAL DEFAULT 2.5,
    interval_days   INTEGER DEFAULT 0,
    next_review_date TEXT,
    repetitions     INTEGER DEFAULT 0
);
```

Column migrations for SM-2 fields are applied automatically on startup via `ALTER TABLE ADD COLUMN`.

## Key Design Decisions

- **Source/Reference never hidden**: Parser strips `**Source:**` / `**Reference:**` lines into `Question.source`. Displayed separately below the answer; hidden in fill/exam modes.
- **Three-button model**: Learn (read), Fill in gaps (cloze), Start Exam (full-answer textarea). No toggle between read/exam within a session.
- **Gaps % replaces fixed stages**: The user controls exactly how much of the answer is hidden via a spinbox, rather than being locked into predefined stage visibilities.
- **Favorite removed**: The `favorite` column and all related UI/code have been removed.
- **Hints show in masked text only**: Hint-revealed letters appear in the paragraph display of the masked answer, not in the gap input fields.
- **`BLANK_CHAR = "\u25a8"`** (`▨`) is used consistently across both UIs as the placeholder for hidden characters.
- **Review preserves history**: "Review Missed Questions" no longer clears previous results; all attempts accumulate and are shown in the summary table.
- **Attempt tracking**: Each `QuestionResult` stores an `attempt` counter per question within the session.
- **Grading uses LCS gate + Levenshtein**: Replaced `difflib.SequenceMatcher` with a hybrid algorithm — longest common substring ratio acts as a gate to reject different words, then normalized Levenshtein distance scores the edit similarity.

## Development Notes

- **Desktop**: Uses `tkinter` (standard library). No external GUI framework.
- **Web**: Uses `FastAPI` + `Jinja2` + `uvicorn`. CSS in `/workspace/static/style.css`.
- **Runtime dependencies**: `httpx` (Ollama HTTP), `fastapi`, `uvicorn`, `jinja2`, `markdown`.
- **No test suite yet**: The package structure supports pytest; tests would go in `/workspace/tests/`.
- The existing `en_q&a_general.md` has one malformed entry (`## Layers?` with no answer) — it is silently skipped by the parser.
