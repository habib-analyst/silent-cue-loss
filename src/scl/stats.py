"""Scoring (micro-F1) and paired bootstrap CIs. stdlib only."""
import random


def micro_f1(pred, gold):
    """pred, gold: iterables of (norm_text, cue)."""
    ps, gs = set(pred), set(gold)
    inter = len(ps & gs)
    p = inter / len(ps) if ps else 0.0
    r = inter / len(gs) if gs else 0.0
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def paired_bootstrap_ci(diffs, B=2000, seed=7):
    """Paired bootstrap 95% percentile CI of the mean of per-unit diffs."""
    rng = random.Random(seed)
    n = len(diffs)
    if n == 0:
        raise ValueError("empty diffs")
    means = []
    for _ in range(B):
        means.append(sum(diffs[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int(0.025 * B)]
    hi = means[int(0.975 * B)]
    return sum(diffs) / n, lo, hi


def ci_excludes_zero(lo, hi):
    return hi < 0 or lo > 0
