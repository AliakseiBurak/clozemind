---
name: cloze-grading
description: Order-independent matching for cloze/gap-fill grading — greedy best-match algorithm that handles swapped or reordered answers.
source: auto-skill
extracted_at: '2026-07-07T13:24:46.404Z'
---

# Cloze Gap-Fill Grading: Order-Independent Matching

When grading cloze (gap-fill) exercises, the naive positional approach compares each gap's expected value with the user input at the same index. This fails when the user knows the answer but writes items in a different order (e.g., comma-separated lists, "and"-separated alternatives).

## The Problem

```
Gap 1: expected "Consistency"    user wrote "Availability"    → 26% (wrong)
Gap 2: expected "Availability"   user wrote "Consistency"     → 26% (wrong)
Gap 3: expected "Partition tolerance"  user wrote "Partition tolerance" → 100% (correct)
Overall: 51% — Keep practicing.
```

The user clearly knows the three terms but swapped the first two. Positional grading penalizes this.

## The Solution: Greedy Best-Match Without Replacement

For each gap, find the **best-matching** user input among the remaining (unmatched) inputs. Remove that input from the pool so it can't be reused.

```
Gap 1 (Consistency) → best match: "Consistency" (100%)  → pop "Consistency"
Gap 2 (Availability) → best match: "Availability" (100%) → pop "Availability"
Gap 3 (Partition tolerance) → best match: "Partition tolerance" (100%) → pop "Partition tolerance"
Overall: 100% — Passed.
```

## Algorithm

```python
def grade(self, answer: str, gaps: list[ClozeGap], user_inputs: list[str]) -> GradeResult:
    remaining = list(user_inputs)  # copy, mutate as we match
    gap_grades = []

    for i, gap in enumerate(gaps):
        # Find the best-matching remaining user input
        best_score = 0.0
        best_idx = 0
        for j, ui in enumerate(remaining):
            score = _similarity(gap.hidden_text, ui)
            if score > best_score:
                best_score = score
                best_idx = j

        # Remove the matched input from the pool
        user = remaining.pop(best_idx) if remaining else ""
        gap_grades.append(GapGrade(
            gap_index=i,
            expected=gap.hidden_text,
            user_input=user,
            score=best_score,
            feedback="Correct." if best_score >= 90 else f"Expected: {gap.hidden_text}",
        ))

    overall = sum(g.score for g in gap_grades) / len(gap_grades)
    passed = overall >= self.pass_threshold
    ...
```

## Edge Cases

| Scenario | Behavior |
|---|---|
| **Fewer inputs than gaps** | Remaining inputs are empty strings; score is 0% for unmatched gaps |
| **More inputs than gaps** | Extra inputs are never matched; they simply remain in the pool |
| **Duplicate expected values** (e.g., two gaps both expect "Consistency") | First gap matches the first occurrence of "Consistency", second gap matches the next occurrence — correct behavior |
| **All inputs identical** (e.g., user writes "Consistency" for every gap) | First gap matches at 100%, subsequent gaps get 0% because "Consistency" was already consumed — correctly penalizes |
| **Similar but wrong answers** (user writes "Partition tolerance" instead of "Availability") | Greedy matching may pair them if the similarity is higher than the remaining options; overall score still correctly indicates failure |

## Limitations

- **Greedy matching is not globally optimal.** The Hungarian algorithm would find the optimal assignment, but greedy is simpler and works well for this domain. The only failure mode is when two similar-but-wrong answers compete for the same correct term — the overall score still correctly indicates failure.
- **Does not handle synonyms.** For semantic grading (accepting "Consistency" ↔ "Consistent behavior"), use a separate LLM-based grader (OllamaGrader) as a fallback.

## Integration

Works with any grader class that accepts `(answer, gaps, user_inputs)`:

```python
# Before (positional):
for i, gap in enumerate(gaps):
    user = user_inputs[i] if i < len(user_inputs) else ""

# After (order-independent):
remaining = list(user_inputs)
for i, gap in enumerate(gaps):
    best_score, best_idx = max(
        (_similarity(gap.hidden_text, ui), j) for j, ui in enumerate(remaining)
    )
    user = remaining.pop(best_idx) if remaining else ""
```

The `_similarity()` function (fuzzy string matching via `difflib.SequenceMatcher` or similar) remains unchanged.