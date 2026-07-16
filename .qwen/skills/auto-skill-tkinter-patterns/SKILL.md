---
name: tkinter-patterns
description: Common Tkinter pitfalls and fixes — parent-child destroy recursion, keyboard shortcut conflicts with Entry widgets, cross-platform fonts, and canvas sizing.
source: auto-skill
extracted_at: '2026-07-07T12:12:29.263Z'
---

# Tkinter Patterns: Common Pitfalls and Fixes

## 1. Parent-Child Destroy Recursion

### The Problem

A `Toplevel` dialog that overrides `destroy()` and calls `self.master.destroy()` will cause infinite recursion:

```python
# BAD — triggers recursion
class SummaryDialog(tk.Toplevel):
    def destroy(self):
        self.master.destroy()  # ← master destroys ALL children including this dialog
        super().destroy()      # ← which calls destroy() again → infinite loop
```

When `self.master.destroy()` runs, Tkinter recursively destroys all children of `master`. The `SummaryDialog` is one of those children, so its `destroy()` is called again — which calls `self.master.destroy()` again, looping forever.

### The Fix

**Don't override `destroy()` at all.** Instead, let the parent-widget destruction cascade naturally:

```python
# GOOD
class SummaryDialog(tk.Toplevel):
    def _close(self):
        intro = self.intro_window      # save references before destroying
        self.master.destroy()          # destroys parent AND this dialog automatically
        intro.deiconify()              # show the intro window
```

If you need cleanup logic, put it in a regular method (e.g., `_close_dialog`, `_review_missed`) and **not** in `destroy()`.

### Key Insight

- `Toplevel(master=parent)` makes the dialog a child of `parent` in the Tk widget hierarchy
- Destroying a parent Tk widget automatically destroys all children (including Toplevels)
- An overridden `destroy()` that calls `self.master.destroy()` → re-enters itself → recursion

## 2. Keyboard Shortcut Conflicts with Text Entry

### The Problem

`bind_all("<Key-a>", callback)` captures **every** 'A' keypress in the application, including when the user is typing inside an `Entry` widget. This makes shortcuts like 'A' for "Show Answer" or 'F' for "Favorite" fire while the user is filling in cloze gaps.

### The Fix

**Remove keyboard shortcuts entirely** when the UI has text entry fields that the user types into. Rely on clickable buttons instead:

```python
# BAD — interferes with typing
self.bind_all("<Key-a>", lambda e: self._toggle_reference())
self.bind_all("<Key-f>", lambda e: self._toggle_favorite())

# GOOD — no letter-key bindings
ttk.Button(action_row, text="Show Answer", command=self._toggle_reference)
ttk.Button(action_row, text="★ Favorite", command=self._toggle_favorite)
```

As a rule of thumb: only use non-printable modifier keys (`<Return>`, `<Escape>`, `<Tab>`, `<F1>`–`<F12>`) when the user needs to type text. Letter keys (`a`–`z`, `0`–`9`) must be avoided.

## 3. Cross-Platform Font

### The Problem

Hardcoded Windows fonts like `"Segoe UI"` don't exist on Linux, causing Tkinter to fall back to an ugly default (often Courier or Times).

### The Fix

Use Tkinter's built-in alias:

```python
FONT_FAMILY = "TkDefaultFont"
ttk.Label(text="Hello", font=(FONT_FAMILY, 12, "bold"))
```

`"TkDefaultFont"` resolves to the system's default UI font on every platform.

## 4. Canvas Inner Frame Sizing

### The Problem

A `Canvas` with a `create_window` for a scrollable inner frame doesn't expand the inner frame's width when the canvas is resized.

### The Fix

Bind to `<Configure>` on the canvas and update the `create_window` item's width:

```python
self.canvas_window_id = canvas.create_window(
    (0, 0), window=inner_frame, anchor=tk.NW
)

def _expand_inner(event):
    canvas.itemconfig(self.canvas_window_id, width=event.width)

canvas.bind("<Configure>", _expand_inner)
```

## 5. Replace Auto-Advance Timers with Explicit "Next Question" Buttons

### The Problem

`self.after(ms, callback)` is often used to auto-advance after showing feedback:

```python
# BAD — auto-advance feels rushed, user can't read feedback at their own pace
def _submit(self):
    self.feedback.config(text="Score: 85%")
    self.after(1800, self._next)  # auto-advance after 1.8s
```

Users want to read the feedback, see which gaps they got wrong, and advance **when they're ready**.

### The Fix

Replace the timer with a button that changes from "Check Answers" to "Next Question":

```python
def _submit(self):
    self.feedback.config(text="Score: 85%")
    self.hint_btn.config(state=tk.DISABLED)
    self.submit_btn.config(text="Next Question", command=self._next)

def _next(self):
    self.submit_btn.config(state=tk.NORMAL)
    self.hint_btn.config(state=tk.NORMAL)
    # Restore the original button text based on the mode
    if self._last_mode_was_read:
        self.submit_btn.config(text="Got it — Next", command=self._submit)
    else:
        self.submit_btn.config(text="Check Answers", command=self._submit)
    self.index += 1
    self._show_current()
```

Use a flag to track which mode the button should revert to:

```python
self._last_mode_was_read = False  # set in __init__

# In _submit, for READ mode:
self._last_mode_was_read = True
self.submit_btn.config(text="Next Question", command=self._next)

# In _submit, for cloze mode:
self._last_mode_was_read = False
self.submit_btn.config(text="Next Question", command=self._next)
```

### Key Insight

- `self.after()` is for non-blocking delays, not for user pacing
- Learning tools especially benefit from user-controlled pacing — the learner decides when to move on
- Store the mode flag (`_last_mode_was_read`) so `_next()` can restore the correct button label

## 6. Tkinter System Dependency

### The Problem

`tkinter` is **not** a pip-installable package. It's a system package that must be installed separately.

### The Fix

Document the per-platform install command in `requirements.txt` and `QWEN.md`:

```
# requirements.txt
httpx>=0.27.0

# tkinter is a system package:
#   Ubuntu/Debian: sudo apt-get install python3-tk
#   Fedora:        sudo dnf install python3-tkinter
#   Arch:          sudo pacman -S tk
#   macOS:         included with Python.org installer
#   Windows:       included with the Windows installer
```