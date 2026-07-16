---
name: review-implement
description: After a code review identifies bugs and improvement opportunities, implement all changes systematically — prioritize by impact, batch related changes, and verify each layer bottom-up.
source: auto-skill
extracted_at: '2026-07-06T12:38:18.481Z'
---

# Review + Implement: Full-stack Python Application Improvements

When the user asks you to implement all the improvements from a code review, follow this batched, bottom-up approach to avoid broken intermediate states and maximize parallel work.

## Principles

- **Bottom-up ordering**: Foundation (models/config) → business logic (store/service) → I/O (parser/cloze) → UI (GUI)
- **Batch writes**: Write each complete file once, using `edit` only for trivial fixes to existing code
- **Verify each layer**: Before moving to the next layer, do a syntax/import check that everything compiles
- **Don't guess — read first**: Read every file that needs changes before writing anything
- **Todo list**: Use `todo_write` to track progress across a multi-file implementation

## Steps

### 1. Categorize every finding from the review

Group findings into:

| Bucket | Examples |
|---|---|
| **Critical bugs** | NameError, crash paths, data loss |
| **Foundation** | New models, config defaults, SM-2 fields |
| **Data layer** | Progress store, migrations, SQL |
| **Business logic** | Service orchestrator, grading, cloze |
| **I/O / Parsing** | File parsing, display mappings |
| **UI** | GUI windows, keyboard bindings, dialogs |
| **Infra** | .gitignore, requirements.txt, docs |

### 2. Order the implementation

Implement in this order:

1. **Fix critical bugs first** — usually a single `edit` call
2. **Foundation** — update models.py, config.py (add new dataclasses, enums, constants)
3. **Data layer** — update progress.py (SM-2 algorithm, DB migrations, new queries)
4. **Parsing / I/O** — update parser.py (robust splitting, display names, counts)
5. **Business logic** — update service.py (wire new features into orchestrator)
6. **Cloze / Grading** — update cloze.py or grading.py only if new algorithm logic is needed
7. **UI** — update gui.py (all UX improvements in one batch write)
8. **Infra** — .gitignore, config files, docs

### 3. Write complete files, batch by batch

For each major file change:
- Design the full file in your head first, reading the current version for context
- Write it as one `write_file` call (not 20 `edit` calls)
- Exception: single-line fixes (like adding an import) can use `edit`

### 4. Verify after each layer

After writing files in a layer, run:

```python
python3 -c "py_compile.compile('file.py', doraise=True)"
```

Or batch-check all files at once. For import-heavy changes, do a full import smoke test:

```python
python3 -c "from interview_learner.config import ...; from interview_learner.progress import ...; ..."
```

### 5. Handle edge cases discovered during verification

- `sqlite3.Row` objects do NOT have a `.get()` method — convert with `dict(row)` first
- Theme display names need manual overrides for acronyms (PHP, OAuth, CQRS, CV)
- Parser `---` splitting must not break inside fenced code blocks — strip them first
- SM-2 needs a `score_to_quality()` mapper between percentage scores (0-100) and SM-2 quality (0-5)

### 6. Final checklist

- [ ] All files compile (`py_compile`)
- [ ] Core modules import successfully without Ollama/network
- [ ] Theme discovery works with correct counts
- [ ] SM-2 computes reasonable intervals (quality=4, reps=1 → interval=6)
- [ ] Progress store records and retrieves all fields
- [ ] Cloze generator produces gaps at different visibility levels
- [ ] GUI classes instantiate without Tkinter errors
- [ ] .gitignore covers `data/`, `__pycache__/`, `.venv/`

## Common traps

| Trap | Fix |
|---|---|
| `sqlite3.Row.get()` doesn't exist | Convert with `dict(row)` then use `.get()` on the dict |
| Tkinter `Segoe UI` font doesn't exist on Linux | Use `"TkDefaultFont"` as `FONT_FAMILY` constant |
| Parser `---` split hits code blocks | Strip fenced blocks first, then split on `^---$` |
| Old DB lacks new columns | Run `ALTER TABLE ... ADD COLUMN` in try/except loop |
| Keyboard bindings leak between windows | Call `unbind_all()` in window destructor |
| Session window `iconify`/`deiconify` breaks | Call `withdraw()` on intro, `deiconify()` on close |