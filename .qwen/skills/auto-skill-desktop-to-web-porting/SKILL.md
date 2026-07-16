---
name: desktop-to-web-porting
description: Convert a Tkinter desktop application to a FastAPI web application — session management, template mapping, dynamic form handling, and backend reuse.
source: auto-skill
extracted_at: '2026-07-07T13:15:55.091Z'
---

# Desktop-to-Web Porting: Tkinter → FastAPI

When porting a Tkinter desktop app to a FastAPI web app, follow this pattern to reuse the existing business logic while replacing the UI layer.

## Architecture

```
Before (Tkinter):
  main.py → IntroWindow (tk.Tk) → SessionWindow (tk.Toplevel) → SessionSummaryDialog

After (FastAPI):
  web_app.py → GET / (intro template) → POST /start → GET /session → POST /submit → GET /summary
```

## File Structure

```
project/
├── web_app.py              # FastAPI app with routes
├── templates/
│   ├── base.html            # Layout template
│   ├── intro.html           # Theme selection / settings
│   ├── session.html         # Question display + cloze input
│   └── summary.html         # Session results
├── static/
│   └── style.css            # Stylesheet
└── interview_learner/       # Existing business logic (unchanged)
    ├── models.py
    ├── parser.py
    ├── progress.py
    ├── service.py
    ├── cloze.py
    └── grading.py
```

## Step-by-Step Mapping

### 1. Tkinter Instance Variables → Session State

Tkinter stores session state as instance attributes on window objects. In a web app, use a server-side dict keyed by a session ID stored in a signed cookie:

```python
from starlette.middleware.sessions import SessionMiddleware
import uuid

app.add_middleware(SessionMiddleware, secret_key="change-me", max_age=86400)

sessions: dict[str, dict] = {}

def _get_session(request: Request) -> dict:
    sid = request.session.get("sid")
    if sid and sid in sessions:
        return sessions[sid]
    sid = uuid.uuid4().hex[:16]
    request.session["sid"] = sid
    data = {"questions": [], "index": 0, "results": [], "cloze": None, ...}
    sessions[sid] = data
    return data
```

### 2. Tkinter Widgets → Jinja2 Templates

| Tkinter Widget | Jinja2 Equivalent |
|---|---|
| `ttk.LabelFrame` | `<div class="card">` |
| `ttk.Checkbutton` | `<input type="checkbox">` |
| `ttk.Entry` | `<input type="text">` |
| `ttk.Combobox` | `<select>` with `<option>` |
| `ttk.Label` | `<span>` or `<p>` |
| `ttk.Button` | `<button>` or `<a>` |
| `tk.Canvas` with scrollable frame | CSS `overflow-y: auto` on a `<div>` |
| `messagebox.showwarning` | Inline form validation + redirect |

### 3. Event-Driven Callbacks → HTTP Routes

| Tkinter Event | Web Route |
|---|---|
| Button click → `self._start()` | `POST /start` → redirect to `/session` |
| Button click → `self._submit()` | `POST /submit` → redirect to `/session` |
| Button click → `self._next()` | `POST /next` → redirect to `/session` |
| Button click → `self._hint()` | `POST /hint` → redirect to `/session` |
| `self.after(ms, callback)` | **Remove.** Replace with explicit "Next Question" button. |

### 4. Dynamic Form Fields (Variable Number of Gap Inputs)

Tkinter creates a dynamic number of `Entry` widgets based on the cloze gaps. In the web app, render numbered inputs and parse them on the server:

**Template:**
```html
<input type="text" name="gap_0" ...>
<input type="text" name="gap_1" ...>
```

**Server (async endpoint):**
```python
@app.post("/submit")
async def submit_answer(request: Request):
    form = await request.form()
    user_inputs = []
    i = 0
    while f"gap_{i}" in form:
        user_inputs.append(form[f"gap_{i}"])
        i += 1
```

### 5. Reusing Business Logic

The existing `LearningService`, `ProgressStore`, `RuleBasedClozeGenerator`, and `ExactGrader` work unchanged. Create a new instance per request — they're lightweight:

```python
local_service = LearningService(settings)
stage = local_service.stage_for(question)
cloze_gen = RuleBasedClozeGenerator()
cloze_result = cloze_gen.generate(question.answer, visibility)
```

### 6. Ollama Integration in a Web Context

Check availability at startup, not on every request:

```python
@app.on_event("startup")
def startup():
    client = OllamaClient(settings.ollama_url, settings.ollama_model)
    ollama_available = client.is_available()
    if ollama_available:
        ollama_models = client.list_models()
```

Pass `ollama_available` and `ollama_models` to the template. If unavailable, disable the section with a warning.

### 7. Session State Serialization for Templates

Tkinter stores Python objects directly. For the web, serialize complex objects to dicts:

```python
def _cloze_to_dict(cs: ClozeState) -> dict:
    return {
        "is_read_mode": cs.is_read_mode,
        "masked_parts": _build_masked_parts(cs),
        "gaps": [
            {"index": i, "hidden_text": g.hidden_text, "hinted": i in cs.hinted_indices}
            for i, g in enumerate(cs.result.gaps)
        ],
        "hint_count": remaining_hints,
        "total_hints": len(cs.result.gaps),
    }
```

## Common Pitfalls

### 8. Jinja2 LRUCache `unhashable type: 'dict'` Error

When using `starlette.templating.Jinja2Templates` (or `fastapi.templating.Jinja2Templates` which re-exports it), you may encounter:

```
File "jinja2/utils.py", line 515, in __getitem__
    rv = self._mapping[key]
TypeError: unhashable type: 'dict'
```

**Root cause:** `Jinja2Templates` wraps Jinja2's `Environment` with default settings that include an `LRUCache` (capacity 400). In certain Jinja2 versions, the `LRUCache.__getitem__` method is called with a cache key that contains a dict, which is not hashable. This happens during template loading when the cache key tuple includes a `globals` dict or when the `_load_template` method constructs a cache key that includes an unhashable type.

**Fix:** Replace `Jinja2Templates` with a raw `jinja2.Environment` and disable the template cache entirely:

```python
# BEFORE (breaks):
from fastapi.templating import Jinja2Templates
TEMPLATES = Jinja2Templates(directory="templates")
return TEMPLATES.TemplateResponse("template.html", {"request": req, ...})

# AFTER (works):
import jinja2
from fastapi.responses import HTMLResponse

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
    autoescape=True,
    cache_size=0,  # disable template cache entirely
)

def _render(name: str, **context: Any) -> str:
    template = _env.get_template(name)
    return template.render(**context)

# In your route handler:
return HTMLResponse(content=_render("template.html", ...))
```

**Key points:**
- `cache_size=0` disables template caching. This is fine for a single-user local app.
- The `request` object is no longer automatically available in templates — pass it explicitly if needed.
- `_render()` returns a string, not a `TemplateResponse`. Wrap it with `HTMLResponse()`.
- `cache_size=0` is safe because `get_template()` is fast with a `FileSystemLoader` for small projects.

### 9. Markdown Rendering in Cloze-Masked Text

When the answer text contains Markdown formatting (`**bold**`, `*italic*`, `` `code` ``, code blocks, lists, tables), the web app must render it as HTML **while preserving the gap placeholders**.

#### Approach

Render the entire masked text (with placeholders) as a single Markdown string, then display the rendered HTML with `|safe`:

**Server-side** — build the masked text with placeholder characters:

```python
def _build_masked_text(cs: ClozeState) -> str:
    """Build the masked answer text with placeholder characters for blanks."""
    text = cs.result.original
    gaps = cs.result.gaps
    result = []
    pos = 0
    for i, gap in enumerate(gaps):
        if gap.start > pos:
            result.append(text[pos:gap.start])
        if gap.token_index in cs.hinted_indices:
            result.append(gap.hidden_text)          # revealed
        else:
            result.append("\u25a8" * max(4, len(gap.hidden_text)))  # hidden
        pos = gap.end
    if pos < len(text):
        result.append(text[pos:])
    return "".join(result)
```

**Jinja2 environment** — register a custom Markdown filter:

```python
import markdown as md_lib

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
    autoescape=True,
    cache_size=0,
)

_extensions = ["fenced_code", "codehilite", "tables"]

def _md_filter(text: str) -> str:
    return md_lib.markdown(text, extensions=_extensions)

_env.filters["markdown"] = _md_filter
```

**Template** — render the masked text as Markdown, then mark as safe HTML:

```html
{% if cloze.is_read_mode %}
<div class="answer-text">
    {{ question.answer|markdown|safe }}
</div>
{% else %}
<div class="masked-text">
    {{ cloze.masked_text|markdown|safe }}
</div>
{% endif %}
```

**CSS** — add styles for the rendered HTML elements (p, code, pre, ul, ol, table, strong, em):

```css
.answer-text p, .masked-text p { margin: 0 0 10px; }
.answer-text code, .masked-text code { background: #f0f2f5; padding: 1px 4px; border-radius: 3px; }
.answer-text pre, .masked-text pre { background: #f0f2f5; padding: 12px; border-radius: 6px; }
.answer-text ul, .answer-text ol, .masked-text ul, .masked-text ol { margin: 6px 0; padding-left: 24px; }
.answer-text table, .masked-text table { border-collapse: collapse; margin: 8px 0; }
.answer-text th, .answer-text td, .masked-text th, .masked-text td { border: 1px solid #ddd; padding: 6px 10px; }
```

#### Why this works

- The placeholder character (`▨`) is a Unicode block character that has no Markdown syntax meaning — it's treated as plain text by the Markdown parser
- `[...]` (bracketed text) could be interpreted as a link reference in some Markdown parsers, so `▨` is safer
- Each gap is rendered as a separate `<input>` field below the masked text, so the placeholders are purely visual
- The `|safe` filter is required because `|markdown` returns HTML that Jinja2 would otherwise escape

---

| Pitfall | Fix |
| `request.form()` is async in Starlette | Use `async def` for the endpoint |
| Missing `python-multipart` dependency | Add to `requirements.txt` |
| Session state gets stale after browser refresh | Add `_end_session()` on the intro page to clear old state |
| Template tries to access `None` attributes | Use `{% if ... %}` guards around all nullable fields |
| Jinja2 `|int` filter fails on string | Use `|trim('%')|int` for percentage strings |
| `Jinja2Templates` from `starlette.templating` causes `unhashable type: 'dict'` | Replace with raw `jinja2.Environment` with `cache_size=0` (see section below) |

### 10. Cloze Rebuild on Every Request Discards Hints

**The Problem**

When a user clicks "Hint", the backend records the hint in the `ClozeState` and redirects to `/session`. But the `session_page()` endpoint rebuilds the cloze if the condition `sd["cloze"] is None or not sd["submitted"]` is true. Since `submitted` is `False` before submitting, the cloze is **rebuilt from scratch on every request**, discarding all hints.

**The Fix**

Change the condition to only rebuild when the cloze state is `None` (which happens after navigating to the next question):

```python
# BAD — rebuilds cloze on every GET /session before submission
if sd["cloze"] is None or not sd["submitted"]:
    ...

# GOOD — only rebuilds when cloze state doesn't exist yet
if sd["cloze"] is None:
    ...
```

The `next_question` endpoint already sets `sd["cloze"] = None` before redirecting, so the next question gets a fresh cloze:

```python
@app.post("/next")
def next_question(request: Request):
    sd = _get_session(request)
    sd["index"] += 1
    sd["cloze"] = None    # ← triggers rebuild on next GET /session
    sd["submitted"] = False
    sd["grade"] = None
    return RedirectResponse(url="/session", status_code=303)
```

### 11. Reveal All Words After "Check Answers" Submission

**The Problem**

After submitting answers, the user sees the grading feedback but the masked text still shows placeholder characters (`▨▨▨▨`). The user can't see the correct words in context alongside the feedback.

**The Fix**

Pass a `reveal_all` flag through the cloze rendering pipeline. When `submitted` is `True`, show the full hidden text for every gap instead of placeholders or partial reveals.

**Cloze helpers** — accept `reveal_all` parameter:

```python
def _build_masked_text(cs: ClozeState, reveal_all: bool = False) -> str:
    ...
    for i, gap in enumerate(gaps):
        if gap.start > pos:
            result.append(text[pos:gap.start])
        if reveal_all:
            result.append(gap.hidden_text)                    # full reveal
        elif gap.token_index in cs.hinted_indices:
            result.append(partial_reveal(gap.hidden_text))    # partial hint
        else:
            result.append("\u25a8" * max(4, len(gap.hidden_text)))  # hidden
        pos = gap.end
    ...

def _cloze_to_dict(cs: ClozeState, reveal_all: bool = False) -> dict:
    parts = _build_masked_parts(cs, reveal_all=reveal_all)
    masked_text = _build_masked_text(cs, reveal_all=reveal_all)
    ...
```

**Route handler** — pass `reveal_all` based on the submitted state:

```python
@app.get("/session", response_class=HTMLResponse)
def session_page(request: Request):
    ...
    return HTMLResponse(content=_render(
        "session.html",
        cloze=_cloze_to_dict(cs, reveal_all=sd["submitted"]),
        submitted=sd["submitted"],
        ...
    ))
```

**Template** — unchanged; the `reveal_all` flag is handled at the rendering level, not the template level.

| Parameter | `submitted=False` | `submitted=True` |
|---|---|---|
| **Unhinted gaps** | `▨▨▨▨` (placeholder) | Full text (revealed) |
| **Hinted gaps** | Partial reveal (~30% chars) | Full text (revealed) |