---
name: partial-hint-reveal
description: Deterministic partial reveal of hidden text — show ~30% of random characters as a hint without giving away the full answer. Used in cloze/fill-in-the-blank learning tools.
source: auto-skill
extracted_at: '2026-07-07T13:37:34.249Z'
---

# Partial Hint Reveal for Cloze Exercises

When a user clicks "Hint" in a cloze (fill-in-the-blank) exercise, revealing the entire hidden word gives away the answer too easily. Instead, reveal a **few random characters** (~30%) and replace the rest with underscores. This provides a nudge while still requiring the user to recall the full term.

## The Algorithm

```python
import random

def partial_reveal(text: str) -> str:
    """Reveal ~30% of characters randomly, replace the rest with underscores.

    The same input always produces the same output (deterministic from hash).
    Words of 2 characters or fewer are fully revealed.
    """
    if len(text) <= 2:
        return text

    # Deterministic seed so the same word always shows the same partial reveal
    rng = random.Random(hash(text) % (2**31))

    chars = list(text)
    num_to_reveal = max(1, len(text) * 30 // 100)
    indices = set(rng.sample(range(len(text)), num_to_reveal))

    return "".join(c if i in indices else "\u2017" for i, c in enumerate(chars))
```

## Behavior

| Input | Output (example) | Notes |
|---|---|---|
| `"Consistency"` | `"‗‗‗sis‗‗‗‗‗"` | ~30% of chars revealed |
| `"Availability"` | `"A‗‗i‗a‗‗‗‗‗‗"` | 4 of 12 chars visible |
| `"NoSQL"` | `"‗o‗‗‗"` | 1 of 5 chars |
| `"OK"` | `"OK"` | ≤2 chars → fully revealed |
| `"ACID"` | `"A‗‗‗"` or `"‗C‗‗"` | 1 of 4 chars |

## Key Design Decisions

### Deterministic (Same Input → Same Output)

The seed is derived from `hash(text) % (2**31)`. This ensures that:

- The same word always reveals the same characters — the user sees consistency across page loads
- Different words reveal different patterns — no predictability across gaps
- The hint is **repeatable** — refreshing the page doesn't change which characters are shown

```python
assert partial_reveal("Consistency") == partial_reveal("Consistency")  # always True
```

### Short Words Fully Revealed

Words of 2 characters or fewer are too short to be meaningfully partial — showing 30% of 2 chars is ≤1 character, which is indistinguishable from random guessing. So short words are fully revealed to avoid frustration.

### Underscore Character Choice

The `\u2017` (double low line `‗`) character is used instead of regular underscore `_` to avoid confusion with actual underscores in the text. Alternative options:

| Character | Code | Pros | Cons |
|---|---|---|---|
| `‗` (double low line) | `\u2017` | Distinct from `_`, clearly a placeholder | Less common font support |
| `_` (underscore) | `\u005f` | Universal | Can be confused with actual underscores |
| `▨` (block) | `\u25a8` | Very visible placeholder | Large, may distract |
| `□` (white square) | `\u25a1` | Neutral | Hard to see at small sizes |

## Integration

### In a Web App (Python → Jinja2)

Pass the partial reveal text through the cloze rendering pipeline:

```python
# cloze_helpers.py
from interview_learner.models import partial_reveal

def _build_masked_text(cs, reveal_all=False):
    ...
    for i, gap in enumerate(gaps):
        if reveal_all:
            result.append(gap.hidden_text)                    # full reveal
        elif gap.token_index in cs.hinted_indices:
            result.append(partial_reveal(gap.hidden_text))    # partial hint
        else:
            result.append("▨" * max(4, len(gap.hidden_text))) # fully hidden
        ...
```

### In a Tkinter GUI

On hint, re-render the answer text with the partial reveal and pre-fill the entry field with the partial text:

```python
def _hint(self):
    idx = self.cloze_state.reveal_hint()
    if idx is not None:
        self._render_answer(self.questions[self.index])  # rebuilds display with partial_reveal
        self.feedback.config(text=f"🧠 Revealed gap {idx+1} of {total}.")

# Inside _render_answer, for hinted gaps:
if gap.token_index in cloze_state.hinted_indices:
    entry.insert(0, partial_reveal(gap.hidden_text))  # partial text, not full
    entry.config(state=tk.DISABLED)
```

## Alternatives Considered

| Approach | Pros | Cons |
|---|---|---|
| **Reveal first/last character** | Simple, predictable | Too easy for short words, too hard for long |
| **Reveal vowels only** | Pedagogically useful | Doesn't work for acronyms or technical terms |
| **Reveal a fixed number** | Consistent | Doesn't scale with word length |
| **Reveal by syllable** | Mimics natural hints | Requires syllable detection library |
| **Full reveal** | Simplest to implement | Gives away the answer entirely |

The 30% random reveal strikes a balance between being helpful and not giving away the answer. The user still needs to recall the remaining 70% of characters, which is the point of active recall.