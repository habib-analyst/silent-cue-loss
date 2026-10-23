"""pytest suite for silent-cue-loss. Deterministic, no LLM, no network."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scl.docxio import write_docx, parse_docx
from scl.synthesis import synthesize, CUES
from scl.ingest import (ARMS, arm_blind, arm_preserving, arm_typed, norm,
                        typed_annotation)
from scl.stats import micro_f1, paired_bootstrap_ci, ci_excludes_zero
from scl.gates import check_gate


@pytest.fixture()
def tiny_corpus(tmp_path):
    outdir = str(tmp_path / "corpus")
    gold = synthesize(7, outdir, n_docs=4)
    return outdir, gold


def test_docx_roundtrip(tmp_path):
    p = str(tmp_path / "t.docx")
    write_docx(p, [[("hello", frozenset({"highlight"}))],
                   [("world", frozenset({"color", "bold"}))],
                   [("plain", frozenset())]])
    paras = parse_docx(p)
    assert len(paras) == 3
    assert paras[0][0] == ("hello", frozenset({"highlight"}))
    assert paras[1][0] == ("world", frozenset({"color", "bold"}))
    assert paras[2][0] == ("plain", frozenset())


def test_all_five_cues_roundtrip(tmp_path):
    p = str(tmp_path / "c.docx")
    write_docx(p, [[("x", frozenset({c}))] for c in CUES])
    paras = parse_docx(p)
    got = [list(r[0][1])[0] for r in paras]
    assert got == CUES


def test_gold_determinism(tmp_path):
    g1 = synthesize(42, str(tmp_path / "a"), n_docs=4)
    g2 = synthesize(42, str(tmp_path / "b"), n_docs=4)
    assert g1 == g2
    g3 = synthesize(43, str(tmp_path / "c"), n_docs=4)
    assert g1 != g3


def test_corpus_shape(tiny_corpus):
    outdir, gold = tiny_corpus
    assert len(gold) == 4
    for doc_id, reqs in gold.items():
        assert len(reqs) == 8
        assert all(r["cue"] in CUES for r in reqs)
        assert os.path.exists(os.path.join(outdir, "docs", doc_id))


def test_gold_json_sorted_keys(tiny_corpus):
    outdir, _ = tiny_corpus
    raw = open(os.path.join(outdir, "gold.json")).read()
    assert raw == json.dumps(json.loads(raw), indent=1, sort_keys=True)


def test_blind_arm_finds_deontic_ignores_plain(tmp_path):
    p = str(tmp_path / "b.docx")
    write_docx(p, [[("The vendor shall file Form 27-B by quarter-end.",
                     frozenset({"highlight"}))],
                   [("The vendor should consider filing eventually.",
                     frozenset())],
                   [("This policy applies to all field engagements.",
                     frozenset())]])
    paras = parse_docx(p)
    preds = arm_blind(paras)
    assert len(preds) == 1
    assert preds[0][1] == "highlight"  # modal-cue guess


def test_preserving_vs_typed_multicue(tmp_path):
    p = str(tmp_path / "m.docx")
    write_docx(p, [[("The auditor shall retain the log.", frozenset({"highlight", "bold"}))]])
    paras = parse_docx(p)
    assert arm_preserving(paras) == [(norm("The auditor shall retain the log."), "bold")]
    assert arm_typed(paras) == [(norm("The auditor shall retain the log."), "highlight")]
    ann = typed_annotation(paras)
    assert ann[0][2] == "mandatory-deadline"


def test_strip_cue_removes_only_that_cue(tmp_path):
    p = str(tmp_path / "s.docx")
    write_docx(p, [[("a", frozenset({"highlight"}))],
                   [("b", frozenset({"color"}))]])
    paras = parse_docx(p)
    got = ARMS["strip-highlight"](paras)
    assert got == [(norm("b"), "color")]
    got2 = ARMS["strip-color"](paras)
    assert got2 == [(norm("a"), "highlight")]


def test_all_arms_registered():
    assert set(ARMS) == {"blind-plain", "cue-preserving", "cue-typed",
                         "strip-highlight", "strip-color", "strip-bold",
                         "strip-italic", "strip-monospace"}


def test_micro_f1_known():
    gold = [("a", "highlight"), ("b", "color")]
    assert micro_f1(gold, gold) == 1.0
    assert micro_f1([], gold) == 0.0
    # 1 TP, 1 FP, 1 FN -> P=R=0.5 -> F1=0.5
    assert micro_f1([("a", "highlight"), ("c", "bold")], gold) == pytest.approx(0.5)


def test_bootstrap_ci_contains_truth_and_is_deterministic():
    diffs = [0.5] * 40 + [0.1] * 20
    m, lo, hi = paired_bootstrap_ci(diffs, B=500, seed=7)
    assert m == pytest.approx(sum(diffs) / len(diffs))
    assert lo <= m <= hi
    assert ci_excludes_zero(lo, hi)
    m2, lo2, hi2 = paired_bootstrap_ci(diffs, B=500, seed=7)
    assert (m, lo, hi) == (m2, lo2, hi2)
    # zero-centered diffs: CI must include 0
    z = [0.1, -0.1] * 30
    _, zlo, zhi = paired_bootstrap_ci(z, B=500, seed=7)
    assert not ci_excludes_zero(zlo, zhi)


def test_check_gate_modes():
    assert check_gate("g", 0.4, 0.3, 0.5, 0.30, "ge_ci")["pass"]
    assert not check_gate("g", 0.2, 0.1, 0.3, 0.30, "ge_ci")["pass"]
    assert not check_gate("g", 0.4, -0.1, 0.5, 0.30, "ge_ci")["pass"]
    assert check_gate("g", 0.05, -0.1, 0.2, 0.10, "abs_le")["pass"]
    assert not check_gate("g", 0.15, 0.1, 0.2, 0.10, "abs_le")["pass"]
    assert check_gate("g", 0.05, 0.01, 0.09, 0.0, "gt_ci")["pass"]


def test_norm():
    assert norm("  Hello   WORLD. ") == "hello world."
