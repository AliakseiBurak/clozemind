# Interview Learner

A Python application for active-recall interview preparation using progressive cloze deletion. Comes in two flavors:

- **Desktop**: Tkinter GUI (`python main.py`)
- **Web**: FastAPI web app (`python web_app.py`)

## Quick Start

```bash
# Desktop (Tkinter)
pip install -r requirements.txt
python main.py

# Web (FastAPI)
pip install -r requirements.txt
python web_app.py
# → http://localhost:8000
```

## Learning Modes

| Mode | What it does |
|---|---|
| **Learn** | Shows full answer — read mode. "Got it — Next" marks as read and advances. |
| **Fill in gaps** | Hides a configurable % of content words (0–100) behind ▨ blanks; type in the missing words |
| **Start Exam** | Full free-form answer in a textarea; graded by Ollama (or similarity fallback) |

A **Gaps** spinbox sets how much of the answer is hidden (0 = full answer, 100 = all content words hidden).

## Key Features

- **Source/Reference lines** are extracted from answers and displayed separately — they are never hidden by cloze; hidden in fill/exam modes
- **Hints** progressively reveal letters in hidden words (shown in masked text only, not input fields)
- **Ollama integration** for semantic cloze generation and answer grading (optional)
- **SM-2 spaced repetition** tracks progress per question
- **Attempt tracking** records how many times each question was answered in a session
- **Session summary** shows a per-question table with first score, attempts, final score, and pass status

## Project Structure

```
interview_learner/
├── main.py              # Desktop entry point (Tkinter)
├── web_app.py           # Web entry point (FastAPI)
├── templates/           # Jinja2 templates (web)
├── static/              # CSS (web)
├── interview_learner/
│   ├── config.py        # AppSettings, constants
│   ├── models.py        # Data classes (Question, ClozeState, etc.)
│   ├── parser.py        # Markdown Q&A parser
│   ├── cloze.py         # Cloze generation (rule-based + Ollama)
│   ├── grading.py       # Answer grading
│   ├── progress.py      # SQLite progress store + SM-2
│   ├── service.py       # Orchestration layer
│   ├── ollama_client.py # HTTP client for Ollama LLM
│   └── gui.py           # Tkinter UI
└── questions/           # Markdown Q&A files
```
