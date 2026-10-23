"""Evaluate kill gates against the PREREG.md (as amended by A1) bars.

Reads results_seed{seed}.jsonl, computes per-doc paired diffs + bootstrap CIs,
checks every bar. Writes KILLGATE.md. Returns (verdict, details).
"""
import json
import os

from .stats import paired_bootstrap_ci, ci_excludes_zero

# Locked bars (PREREG.md sections 6 + amendment A1)
G2_DROP_BAR = 0.30
G3A_DOM_BAR = 0.10
G3A_ZERO_BAR = 0.10
G3B_BAR = 0.05


def load_f1(results_path):
    f1 = {}  # (doc_id, arm) -> f1
    with open(results_path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                f1[(r["doc_id"], r["arm"])] = r["f1"]
    return f1


def diffs(f1, doc_ids, arm_a, arm_b):
    return [f1[(d, arm_a)] - f1[(d, arm_b)] for d in doc_ids]


def check_gate(name, mean, lo, hi, bar, mode):
    if mode == "ge_ci":
        ok = mean >= bar and ci_excludes_zero(lo, hi)
    elif mode == "abs_le":
        ok = abs(mean) <= bar
    elif mode == "gt_ci":
        ok = mean > 0 and ci_excludes_zero(lo, hi)
    else:
        raise ValueError(mode)
    return {"gate": name, "mean": mean, "ci_lo": lo, "ci_hi": hi,
            "bar": bar, "mode": mode, "pass": ok}


def evaluate(results_path):
    f1 = load_f1(results_path)
    doc_ids = sorted({d for (d, _a) in f1})
    arms = {a for (_d, a) in f1}
    need = {"blind-plain", "cue-preserving", "cue-typed", "strip-highlight",
            "strip-color", "strip-bold", "strip-italic", "strip-monospace"}
    assert need <= arms, "missing arms: %s" % (need - arms)

    def ci(a, b):
        return paired_bootstrap_ci(diffs(f1, doc_ids, a, b))

    checks = []
    # G2: disease — blind drops >= 30pp vs preserving, CI excludes 0
    m, lo, hi = ci("cue-preserving", "blind-plain")
    checks.append(check_gate("G2 disease (pres - blind)", m, lo, hi,
                             G2_DROP_BAR, "ge_ci"))
    # G3a: ablation asymmetry (A1)
    d = {}
    for cue in ["highlight", "color", "bold", "italic", "monospace"]:
        m, lo, hi = ci("cue-preserving", "strip-" + cue)
        d[cue] = (m, lo, hi)
    m, lo, hi = d["highlight"]
    checks.append(check_gate("G3a delta_highlight", m, lo, hi,
                             G3A_DOM_BAR, "ge_ci"))
    m, lo, hi = d["color"]
    checks.append(check_gate("G3a delta_color", m, lo, hi,
                             G3A_DOM_BAR, "ge_ci"))
    for cue in ["italic", "monospace"]:
        m, lo, hi = d[cue]
        checks.append(check_gate("G3a |delta_%s|" % cue, m, lo, hi,
                                 G3A_ZERO_BAR, "abs_le"))
    mb, _, _ = d["bold"]
    checks.append({"gate": "G3a delta_bold (reported, ungated)", "mean": mb,
                   "ci_lo": d["bold"][1], "ci_hi": d["bold"][2],
                   "bar": None, "mode": "report", "pass": True})
    for pair in [("highlight", "italic"), ("color", "italic")]:
        dd = [x - y for x, y in zip(diffs(f1, doc_ids, "cue-preserving",
                                          "strip-" + pair[0]),
                                    diffs(f1, doc_ids, "cue-preserving",
                                          "strip-" + pair[1]))]
        m, lo, hi = paired_bootstrap_ci(dd)
        checks.append(check_gate(
            "G3a dominance delta_%s - delta_%s" % pair, m, lo, hi,
            0.0, "gt_ci"))
    # G3b: typing beats preserving
    m, lo, hi = ci("cue-typed", "cue-preserving")
    checks.append(check_gate("G3b typing gain (typed - pres)", m, lo, hi,
                             G3B_BAR, "ge_ci"))

    verdict = "PASS" if all(c["pass"] for c in checks) else "KILL"
    return verdict, checks, doc_ids


def render_killgate(outdir, seed, verdict, checks, doc_ids):
    lines = ["# KILLGATE.md — silent-cue-loss (seed %d)" % seed, "",
             "Verdict: **%s**" % verdict, "",
             "Bars: PREREG.md sections 6 + amendment A1 (pre-measurement).",
             "Units: %d documents, paired bootstrap B=2000 seed 7." % len(doc_ids),
             "",
             "| check | mean | 95% CI | bar | verdict |",
             "|---|---|---|---|---|"]
    for c in checks:
        bar = "-" if c["bar"] is None else ("%.3f" % c["bar"])
        lines.append("| %s | %.4f | [%.4f, %.4f] | %s | %s |" % (
            c["gate"], c["mean"], c["ci_lo"], c["ci_hi"], bar,
            "PASS" if c["pass"] else "FAIL"))
    lines += ["", "Verdict recorded: %s" % verdict]
    path = os.path.join(outdir, "KILLGATE_seed%d.md" % seed)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path
