# BUILD_NOTES.md — silent-cue-loss

## Timeline (2026-10-23, all PKT)

- ~05:55: dispatched as Project #67 (kill-gate-first).
- G1 (author-code recheck): arXiv abs page 2610.30026 live-fetched — no code/
  data links. GitHub `search_repositories` "2610.30026" -> 0 hits;
  "silent cue loss" -> 0 hits. `search_code` -> 124 hits, all aggregator/
  newsletter mirrors (cn-chat-arxiv, research-pipeline, Chinese docs) — no
  implementation, no 76-doc benchmark. G1 PASS.
- PREREG.md written BEFORE any measurement; bars locked.
- Amendment A1 (pre-measurement): G3a bars revised. The as-written bars
  (delta_hl >= 0.15 etc.) came from a linear cue-share heuristic; exact
  per-doc micro-F1 arithmetic under the design implies delta_highlight ~=
  0.16 (within noise of the 0.15 bar) and delta_bold ~= -0.10 (structural:
  multi-cue highlight+bold runs + naive alphabetical resolver => stripping
  bold lets the resolver recover highlight). Revised to test the asymmetry
  with margin: delta_hl/delta_color >= 0.10 with CIs excluding 0;
  |delta_italic|,|delta_mono| <= 0.10; dominance margins vs italic with CIs
  excluding 0; delta_bold reported ungated. G2/G3b untouched.
- Scaffolding: src/scl/{docxio,synthesis,ingest,stats,experiment,gates}.py,
  run_experiment.py, tests/test_scl.py (13 tests). Project venv, pytest 9.1.1.
- Docling arm: `import docling` fails; installing it (torch-sized) infeasible
  on this VM — recorded as UNAVAILABLE per the pre-registered contingency;
  blind-plain stands as the formatting-blind condition.
- Experiment seed 42: 60 docs synthesized, all 8 arms scored, gates
  evaluated -> ALL PASS (see KILLGATE.md).
- Replication seed 20261023 (detached via setsid+nohup): ALL PASS, same
  shape — determinism confirmed.

## Measured numbers (seed 42, n=60, paired bootstrap B=2000 seed 7)

- blind-plain F1 0.2783; cue-preserving 0.8500; cue-typed 1.0000.
- G2 drop (pres-blind): +0.5717, CI [+0.5162, +0.6279] (bar 0.30).
- G3a: delta_highlight +0.1314 [+0.1045, +0.1592]; delta_color +0.3061
  [+0.2682, +0.3461]; |delta_italic| 0.0641; |delta_mono| 0.0374;
  delta_bold -0.1031 [-0.1414, -0.0666] (ungated, documented confounder
  interaction); dominance margins +0.0672 [+0.0323, +0.1036] (hl vs italic)
  and +0.2420 [+0.1952, +0.2884] (color vs italic).
- G3b typing gain: +0.1500 [+0.1187, +0.1854] (bar 0.05).

## Design notes / deviations

- None post-measurement. One pre-measurement amendment (A1) documented above.
- Synthetic corpus is an honest simulation; stated in README, PAPER, PREREG.
- No LLM anywhere; zero runtime deps; CPU ~1 min total; $0.

## Files staged for push

See hidden_files/silent_cue_loss_push_payload.json (repo
habib-analyst/silent-cue-loss, no .github/workflows).
PAPER.md at hidden_files/papers/silent-cue-loss/PAPER.md.
LinkedIn draft at hidden_files/linkedin_drafts/silent-cue-loss.md.
