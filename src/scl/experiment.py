"""Run the full experiment: synthesize corpus, run all arms, score per doc.

Resume-safe: per-doc JSONL appends + DONE marker; --resume skips docs already
scored in results.jsonl.
"""
import json
import os

from .docxio import parse_docx
from .ingest import ARMS, norm
from .stats import micro_f1
from .synthesis import N_DOCS, synthesize


def _load_scored(path):
    scored = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    scored.add((r["doc_id"], r["arm"]))
    return scored


def run(seed, outdir, resume=False):
    corpus_dir = os.path.join(outdir, "corpus_seed%d" % seed)
    results_path = os.path.join(outdir, "results_seed%d.jsonl" % seed)
    done_path = os.path.join(outdir, "DONE_seed%d" % seed)

    gold_path = os.path.join(corpus_dir, "gold.json")
    if os.path.exists(gold_path) and os.path.exists(done_path) and resume:
        with open(gold_path) as f:
            gold = json.load(f)
    else:
        if os.path.exists(done_path):
            os.remove(done_path)
        if os.path.exists(results_path):
            os.remove(results_path)
        gold = synthesize(seed, corpus_dir)

    scored = _load_scored(results_path) if resume else set()
    doc_ids = sorted(gold.keys())
    assert len(doc_ids) == N_DOCS, "expected %d docs, got %d" % (N_DOCS, len(doc_ids))

    with open(results_path, "a") as out:
        for doc_id in doc_ids:
            gold_pairs = [(norm(g["text"]), g["cue"]) for g in gold[doc_id]]
            paras = parse_docx(os.path.join(corpus_dir, "docs", doc_id))
            for arm_name, arm_fn in ARMS.items():
                if (doc_id, arm_name) in scored:
                    continue
                preds = arm_fn(paras)
                f1 = micro_f1(preds, gold_pairs)
                out.write(json.dumps({
                    "seed": seed, "doc_id": doc_id, "arm": arm_name,
                    "f1": f1, "n_pred": len(preds), "n_gold": len(gold_pairs),
                }) + "\n")
                out.flush()
    with open(done_path, "w") as f:
        f.write("ok\n")
    return results_path
