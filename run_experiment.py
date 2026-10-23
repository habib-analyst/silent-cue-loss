#!/usr/bin/env python3
"""CLI: run experiment + evaluate kill gates."""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from scl.experiment import run
from scl.gates import evaluate, render_killgate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--gates-only", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    if not args.gates_only:
        results_path = run(args.seed, args.outdir, resume=args.resume)
    else:
        results_path = os.path.join(args.outdir,
                                    "results_seed%d.jsonl" % args.seed)
    verdict, checks, doc_ids = evaluate(results_path)
    path = render_killgate(args.outdir, args.seed, verdict, checks, doc_ids)
    print("verdict:", verdict)
    print("wrote:", path)
    for c in checks:
        bar = "-" if c["bar"] is None else "%.3f" % c["bar"]
        print("  %-42s mean=%+.4f CI=[%+.4f,%+.4f] bar=%s %s" % (
            c["gate"], c["mean"], c["ci_lo"], c["ci_hi"], bar,
            "PASS" if c["pass"] else "FAIL"))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
