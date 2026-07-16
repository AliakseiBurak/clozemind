---
name: code-review
description: Systematic review of Python application codebases — architecture analysis, bug detection, quality assessment, and improvement proposals.
source: auto-skill
extracted_at: '2026-07-06T12:12:25.995Z'
---

# Code Review: Python Application

Use this approach when reviewing a Python application codebase for bugs, design issues, and improvement opportunities.

## Steps

### 1. Understand the requirements first
Read the prompt, README, or requirements document to establish what the app should do. This gives you a baseline to compare the actual code against.

### 2. Read every source file
Read all modules systematically (not just diffs). For each file, note:
- What it exports/defines
- What it imports from other modules
- The data flow in and out

### 3. Cross-module import audit
Verify every cross-module import actually resolves. This catches the most common class of Python bug — **NameError from missing imports**. Cross-reference usage against the import statement.

### 4. Evaluate architecture
- Is there a clean separation of concerns? (models, business logic, I/O, UI)
- Are abstract base classes / protocols used where multiple implementations exist?
- Is there a graceful fallback chain for optional features (e.g., AI → rule-based)?
- Are external dependencies injected, or hard-coded?

### 5. Evaluate each quality dimension
| Dimension | Look for |
|---|---|
| **Correctness** | NameError, TypeError, off-by-one, edge cases with empty inputs |
| **Test coverage** | Any tests at all? Are the core algorithms tested? |
| **Cross-platform** | Hardcoded Windows fonts on Linux/macOS, path separators |
| **UX** | Keyboard shortcuts, progress indicators for slow operations, resizing behavior |
| **Parser robustness** | Input that can fool the parser (e.g., `---` in code blocks, unicode) |
| **Data persistence** | SQL injection, concurrent access, hardcoded paths, missing `.gitignore` |
| **Error handling** | Silent failures, blanket `except`, unhelpful error messages |

### 6. Domain-relevant feature gaps
Think about what domain the app operates in and identify features a user in that domain would naturally expect:
- **Learning tools**: spaced repetition (SM-2), session summaries, keyboard shortcuts, progress visualization
- **CLI tools**: progress bars, dry-run mode, colored output
- **Web APIs**: pagination, rate limiting, idempotency keys, health endpoint
- **Data pipelines**: checkpoint/resume, data validation, schema evolution

### 7. Organize findings by priority
| Level | Criteria |
|---|---|
| **Critical** | Runtime crash, data loss, security vulnerability |
| **High** | Missing core UX flow, no test coverage for core logic, no tests at all |
| **Medium** | Missing quality-of-life features, cosmetic issues, parser edge cases |
| **Low** | Code style, docstrings, optional enhancements |

### 8. Present with actionable recommendations
For each finding, state:
- **What** the issue is
- **Where** it lives (file:line)
- **Why** it matters
- **How** to fix it (specific code change when possible)