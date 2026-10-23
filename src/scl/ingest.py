"""Deterministic ingestion arms + agent-side matcher. No LLM.

All arms map an ingested document to predicted (norm_text, cue) pairs using
the SAME matcher logic; they differ only in the ingested representation:

- blind-plain:      plain-text concatenation; deontic-filter candidates,
                    cue guess = modal cue 'highlight' (honest prior: a blind
                    pipeline cannot see cues).
- cue-preserving:   run-level OOXML cues; multi-cue runs resolved by naive
                    canonical (alphabetical) order -> highlight+bold => 'bold'.
- cue-typed:        same parse, but cue resolution uses the pre-registered
                    lexicon priority -> highlight+bold => 'highlight'.
- strip-<cue>:      cue-preserving parse with that cue's OOXML properties
                    removed before resolution (leave-one-out).
"""
import re

from .synthesis import CANONICAL_ORDER, LEX_PRIORITY, LEXICON

DEONTIC_RE = re.compile(r"\b(shall|must|is required to|are required to)\b",
                        re.IGNORECASE)
WS_RE = re.compile(r"\s+")


def norm(text):
    return WS_RE.sub(" ", text.strip().lower())


def _plain_text(paras):
    return "\n".join("".join(t for t, _ in runs) for runs in paras)


def arm_blind(paras):
    preds = []
    for runs in paras:
        text = "".join(t for t, _ in runs)
        if DEONTIC_RE.search(text):
            preds.append((norm(text), "highlight"))
    return preds


def _resolve_canonical(cues):
    return min(cues, key=lambda c: CANONICAL_ORDER.index(c))


def _resolve_typed(cues):
    return min(cues, key=lambda c: LEX_PRIORITY.index(c))


def arm_preserving(paras, drop=()):
    drop = set(drop)
    preds = []
    for runs in paras:
        for t, cues in runs:
            cues = cues - drop
            if not cues:
                continue
            preds.append((norm(t), _resolve_canonical(cues)))
    return preds


def arm_typed(paras):
    preds = []
    for runs in paras:
        for t, cues in runs:
            if not cues:
                continue
            preds.append((norm(t), _resolve_typed(cues)))
    return preds


def typed_annotation(paras):
    """Human-readable typed view (for the writeup): (text, cue, type-label)."""
    out = []
    for runs in paras:
        for t, cues in runs:
            if not cues:
                continue
            cue = _resolve_typed(cues)
            out.append((norm(t), cue, LEXICON[cue]))
    return out


ARMS = {
    "blind-plain": lambda paras: arm_blind(paras),
    "cue-preserving": lambda paras: arm_preserving(paras),
    "cue-typed": lambda paras: arm_typed(paras),
    "strip-highlight": lambda paras: arm_preserving(paras, drop=("highlight",)),
    "strip-color": lambda paras: arm_preserving(paras, drop=("color",)),
    "strip-bold": lambda paras: arm_preserving(paras, drop=("bold",)),
    "strip-italic": lambda paras: arm_preserving(paras, drop=("italic",)),
    "strip-monospace": lambda paras: arm_preserving(paras, drop=("monospace",)),
}
