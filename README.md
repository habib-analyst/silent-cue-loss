# silent-cue-loss

Open deterministic replication of **arXiv 2610.30026** (Zhao, Pandey, Misra:
"What the Author Wrote, What the Agent Reads: Silent Cue Loss in Enterprise
Document Ingestion").

**Claim under test:** an ingestion layer (Word/PDF -> tokens) silently drops
meaning an author encodes in *formatting* — highlight and color — making agents
confidently wrong rather than visibly incomplete.

**What this repo does:** synthesizes `.docx` policy documents with known
formatting-encoded requirements (seeded, honest simulation — stated
everywhere), scores requirement recovery with a deterministic matcher against
OOXML run properties (zero LLM judge), and compares formatting-blind ingestion
against cue-preserving ingestion, plus a leave-one-out cue ablation and a
cue-typing fix.

## Measured results (seed 42, n=60 docs, paired bootstrap 95% CIs)

| condition | mean micro-F1 |
|---|---|
| formatting-blind (plain text) | 0.278 |
| cue-preserving (OOXML runs) | 0.850 |
| cue-typed (preserving + cue lexicon) | 1.000 |

- **Disease:** blind ingestion drops recovery **57.2pp** vs cue-preserving,
  95% CI [+51.6, +62.8] (bar: >=30pp, CI excludes 0). Paper: 0.690 -> 0.150.
- **Ablation (leave-one-out):** dropping highlight costs **13.1pp**
  [+10.5, +15.9]; dropping color costs **30.6pp** [+26.8, +34.6]; italic 6.4pp
  and monospace 3.7pp sit near zero. Paper: highlight +0.302, colour +0.262,
  bold/italic/monospace/strikethrough ~0.
- **Typing fix:** typing cues for the agent adds **+15.0pp** beyond merely
  preserving them, CI [+11.9, +18.5] (bar: +5pp). Paper: +0.085.
- Honest secondary finding: stripping **bold** *improves* recovery by ~10pp —
  bold acts as a confounder for the naive cue resolver on multi-cue runs
  (documented in PAPER.md, reported ungated per PREREG amendment A1).

Replication seed 20261023: all gates PASS with the same shape.

## Layout

- `PREREG.md` — locked protocol (written before any measurement; bars locked,
  amendment A1 pre-measurement)
- `src/scl/synthesis.py` — seeded .docx corpus generator
- `src/scl/docxio.py` — minimal OOXML writer + run-level parser (stdlib only)
- `src/scl/ingest.py` — deterministic ingestion arms (blind / preserving /
  typed / strip-cue x5)
- `src/scl/stats.py` — micro-F1 + paired bootstrap CIs (stdlib only)
- `src/scl/experiment.py`, `src/scl/gates.py` — runner + kill-gate evaluator
- `run_experiment.py` — CLI (`--seed 42 --outdir results`)
- `tests/test_scl.py` — 13 pytest tests
- `KILLGATE.md` — gate verdicts with measured numbers and CIs

## Reproduce

```bash
python -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python run_experiment.py --seed 42 --outdir results
.venv/bin/python -m pytest tests/ -q
```

Zero third-party runtime dependencies. CPU only, ~1 minute. No network, no LLM.

## Scope

Synthetic documents are an honest simulation of the paper's mechanism, not its
76 real policy documents. Deterministic matching only; no LLM anywhere.
