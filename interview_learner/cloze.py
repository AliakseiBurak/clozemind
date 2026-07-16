from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from interview_learner.models import ClozeGap, ClozeResult

# Common English stopwords — kept visible to preserve sentence context.
_STOPWORDS = frozenset(
    """
    a an the and or but if then else when at by for with about against between
    into through during before after above below to from up down in out on off
    over under again further once here there all each few more most other some
    such no nor not only own same so than too very can will just don should now
    is are was were be been being have has had do does did of as it its this that
    these those i you he she they we me him her them my your his their our what
    which who whom how why where
    """.split()
)

_WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)


def _is_hideable(word: str) -> bool:
    cleaned = word.strip("`'\"*_")
    if len(cleaned) < 2:
        return False
    if cleaned.lower() in _STOPWORDS:
        return False
    if cleaned.isdigit():
        return False
    return True


class ClozeGenerator(ABC):
    @abstractmethod
    def generate(self, text: str, visibility: float) -> ClozeResult:
        raise NotImplementedError


class RuleBasedClozeGenerator(ClozeGenerator):
    """Hide content words proportionally; prioritizes longer / capitalized terms."""

    def generate(self, text: str, visibility: float) -> ClozeResult:
        if visibility >= 1.0:
            return ClozeResult(original=text, visibility=1.0, gaps=[])

        matches = list(_WORD_RE.finditer(text))
        candidates = [
            (idx, m)
            for idx, m in enumerate(matches)
            if _is_hideable(m.group())
        ]
        if not candidates:
            return ClozeResult(original=text, visibility=visibility, gaps=[])

        hide_ratio = 1.0 - visibility
        hide_count = max(1, round(len(candidates) * hide_ratio))

        def importance(item: tuple[int, re.Match[str]]) -> tuple[int, int, int]:
            _, m = item
            word = m.group()
            return (
                len(word),
                1 if word[:1].isupper() else 0,
                -item[0],
            )

        ranked = sorted(candidates, key=importance, reverse=True)
        to_hide = {idx for idx, _ in ranked[:hide_count]}

        gaps: list[ClozeGap] = []
        for idx, m in enumerate(matches):
            if idx not in to_hide:
                continue
            gaps.append(
                ClozeGap(
                    start=m.start(),
                    end=m.end(),
                    hidden_text=m.group(),
                    token_index=idx,
                )
            )

        return ClozeResult(original=text, visibility=visibility, gaps=gaps)


class OllamaClozeGenerator(ClozeGenerator):
    """Ask a local LLM which terms are most important to hide for active recall."""

    CLOZE_PROMPT = """You help design active-recall exercises for technical interview prep.

Given the answer text below, choose exactly {hide_count} words or short phrases to hide.
Pick terms that test real understanding (concepts, protocols, patterns, trade-offs),
not filler words. Each selection MUST match the answer text exactly (case-sensitive).

Return ONLY valid JSON:
{{"hide": ["exact term 1", "exact term 2"]}}

Answer text:
{text}"""

    def __init__(self, client, fallback: ClozeGenerator | None = None) -> None:
        self.client = client
        self.fallback = fallback or RuleBasedClozeGenerator()

    def generate(self, text: str, visibility: float) -> ClozeResult:
        if visibility >= 1.0:
            return ClozeResult(original=text, visibility=1.0, gaps=[])

        matches = list(_WORD_RE.finditer(text))
        candidates = [m for m in matches if _is_hideable(m.group())]
        if not candidates:
            return ClozeResult(original=text, visibility=visibility, gaps=[])

        hide_count = max(1, round(len(candidates) * (1.0 - visibility)))
        try:
            raw = self.client.generate(
                self.CLOZE_PROMPT.format(hide_count=hide_count, text=text),
                format_json=True,
            )
            payload = json.loads(raw)
            hide_terms = payload.get("hide", [])
            gaps = _gaps_from_terms(text, hide_terms)
            if gaps:
                return ClozeResult(original=text, visibility=visibility, gaps=gaps)
        except Exception:
            pass

        return self.fallback.generate(text, visibility)


def _gaps_from_terms(text: str, terms: list[str]) -> list[ClozeGap]:
    gaps: list[ClozeGap] = []
    used_spans: set[tuple[int, int]] = set()

    for term in terms:
        if not term:
            continue
        for m in re.finditer(re.escape(term), text):
            span = (m.start(), m.end())
            if span in used_spans:
                continue
            used_spans.add(span)
            gaps.append(
                ClozeGap(
                    start=m.start(),
                    end=m.end(),
                    hidden_text=m.group(),
                    token_index=len(gaps),
                )
            )
            break

    gaps.sort(key=lambda g: g.start)
    for i, gap in enumerate(gaps):
        gap.token_index = i
    return gaps
