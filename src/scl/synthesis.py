"""Seeded synthesis of .docx policy documents with formatting-encoded requirements.

Design (PREREG.md sections 2, 5):
- 60 docs x 16 sentences: 8 requirements (deontic + exactly one formatting cue),
  4 deontic confounders (no formatting), 4 plain distractors.
- Cue shares: highlight .40 / color .35 / bold .10 / italic .10 / monospace .05.
- 15% of requirements carry highlight+BOLD (gold cue stays 'highlight' per the
  lexicon dominance rule). Multi-cue runs are highlight+bold only.
"""
import json
import os
import random

from .docxio import write_docx

CUES = ["highlight", "color", "bold", "italic", "monospace"]
CUE_SHARES = {"highlight": 0.40, "color": 0.35, "bold": 0.10,
              "italic": 0.10, "monospace": 0.05}
CANONICAL_ORDER = ["bold", "color", "highlight", "italic", "monospace"]
LEXICON = {"highlight": "mandatory-deadline", "color": "restriction",
           "bold": "role-assignment", "italic": "conditional-note",
           "monospace": "system-identifier"}
LEX_PRIORITY = ["highlight", "color", "bold", "italic", "monospace"]

N_DOCS = 60
REQ_PER_DOC = 8
CONF_PER_DOC = 4
PLAIN_PER_DOC = 4
MULTI_CUE_FRAC = 0.15

# --- deontic template families (requirement + confounder text pool) ---
_A1 = ["The contractor", "The vendor", "The system operator", "The data auditor"]
_V1 = ["submit", "file", "retain", "update", "disclose"]
_O1 = ["the quarterly access report", "Form 27-B", "the audit log archive",
       "the incident register", "the compliance attestation"]
_D1 = ["the 15th of each quarter", "quarter-end", "30 days after discovery",
       "the annual review date"]

_A2 = ["The service provider", "The maintenance team", "The records custodian",
       "The security officer"]
_V2 = ["complete", "rotate", "verify", "quarantine"]
_O2 = ["the credential rotation", "the access recertification",
       "the backup integrity check", "the vulnerability scan"]
_P2 = ["72 hours", "one business week", "14 calendar days",
       "the maintenance window"]

_A3 = ["The facility manager", "The training coordinator", "The incident commander"]
_V3 = ["rehearse", "document", "escalate", "archive"]
_O3 = ["the evacuation drill", "the chain-of-custody log",
       "the after-action review", "the retention schedule"]
_F3 = ["each quarter", "twice per year", "after every incident"]


def deontic_pool():
    pool = []
    for a in _A1:
        for v in _V1:
            for o in _O1:
                for d in _D1:
                    pool.append("%s shall %s %s by %s." % (a, v, o, d))
    for a in _A2:
        for v in _V2:
            for o in _O2:
                for p in _P2:
                    pool.append("%s must %s %s within %s." % (a, v, o, p))
    for a in _A3:
        for v in _V3:
            for o in _O3:
                for f in _F3:
                    pool.append("%s is required to %s %s %s." % (a, v, o, f))
    return pool  # 400 + 256 + 144 = 800


# --- plain (non-deontic) distractor templates ---
_PS = ["field", "remote", "third-party", "cross-border"]
_PD = ["governance charter", "operating manual", "service agreement",
       "oversight framework"]
_PB = ["the review board", "the compliance office", "senior leadership",
       "the audit committee"]
_PC = ["a quarterly", "an annual", "a biennial"]
_PQ = ["day-to-day operations", "record keeping", "vendor coordination",
       "internal reporting"]
_PR = ["the document owner", "the policy steward", "the designated contact",
       "the records office"]
_PW = ["plain language", "the approved template", "the standard format"]
_PU = ["supersedes all prior versions", "takes effect on publication",
       "remains in force until revoked", "is archived after five years"]


def plain_pool():
    pool = []
    for s in _PS:
        for q in _PQ:
            pool.append("This policy applies to all %s engagements covering %s." % (s, q))
    for d in _PD:
        for b in _PB:
            for c in _PC:
                pool.append("The %s is reviewed by %s on %s basis." % (d, b, c))
    for r in _PR:
        for w in _PW:
            pool.append("Questions about interpretation should be directed to %s in %s." % (r, w))
    for u in _PU:
        for s in _PS:
            pool.append("This revision %s and applies to %s activities." % (u, s))
    return pool  # 16 + 48 + 12 + 16 = 92 -> need 240; cycle with index suffix is NOT used;
                 # instead we reuse across docs is forbidden -> see synthesize (draw with
                 # replacement across docs but never twice in one doc)


def synthesize(seed, outdir, n_docs=N_DOCS):
    """Generate corpus. Returns gold dict {doc_id: [{text, cue}]}.

    Writes outdir/docs/doc_XXXX.docx and outdir/gold.json.
    Plain distractors: drawn without replacement *within* a doc; the 92-pool
    cycles across docs with a seeded offset (texts may repeat across docs,
    never within a doc — distractors carry no gold labels so this is safe).
    """
    rng = random.Random(seed)
    os.makedirs(os.path.join(outdir, "docs"), exist_ok=True)
    dpool = deontic_pool()
    rng.shuffle(dpool)
    ppool = plain_pool()

    need_deontic = n_docs * (REQ_PER_DOC + CONF_PER_DOC)
    assert len(dpool) >= need_deontic, "deontic pool too small"

    # assign cues to every requirement slot
    all_cues = rng.choices(CUES,
                           weights=[CUE_SHARES[c] for c in CUES],
                           k=n_docs * REQ_PER_DOC)
    # multi-cue: 15% of requirement slots, restricted to highlight-cue slots
    n_multi = int(round(MULTI_CUE_FRAC * n_docs * REQ_PER_DOC))
    hl_slots = [i for i, c in enumerate(all_cues) if c == "highlight"]
    multi_slots = set(rng.sample(hl_slots, min(n_multi, len(hl_slots))))

    gold = {}
    di = 0
    for doc_id in range(n_docs):
        req_texts = dpool[di:di + REQ_PER_DOC]; di += REQ_PER_DOC
        conf_texts = dpool[di:di + CONF_PER_DOC]; di += CONF_PER_DOC
        sentences = []  # (text, frozenset(cues), is_requirement)
        greqs = []
        for j in range(REQ_PER_DOC):
            slot = doc_id * REQ_PER_DOC + j
            cue = all_cues[slot]
            cues = {cue} | ({"bold"} if slot in multi_slots else set())
            sentences.append((req_texts[j], frozenset(cues), True))
            greqs.append({"text": req_texts[j], "cue": cue})
        for t in conf_texts:
            sentences.append((t, frozenset(), False))
        # plain distractors: 4 distinct per doc, seeded offset into cycled pool
        start = rng.randrange(len(ppool))
        chosen, k = [], 0
        while len(chosen) < PLAIN_PER_DOC:
            t = ppool[(start + k) % len(ppool)]; k += 1
            if t not in chosen:
                chosen.append(t)
        for t in chosen:
            sentences.append((t, frozenset(), False))
        rng.shuffle(sentences)
        paras = [[(t, cues)] for (t, cues, _req) in sentences]
        doc_name = "doc_%04d.docx" % doc_id
        write_docx(os.path.join(outdir, "docs", doc_name), paras)
        gold[doc_name] = greqs

    with open(os.path.join(outdir, "gold.json"), "w") as f:
        json.dump(gold, f, indent=1, sort_keys=True)
    return gold
