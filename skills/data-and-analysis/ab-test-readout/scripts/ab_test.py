#!/usr/bin/env python3
"""A/B test readout for conversion metrics: sample-ratio check, lift, CI, p-value, power. Stdlib only.

Usage:
    python3 ab_test.py --group control:48210:2893 --group variant:48544:3107
    python3 ab_test.py --group A:10000:520 --group B:10050:571 --group C:9980:498 --split 1:1:1
    python3 ab_test.py --group control:48210:2893 --group variant:48544:3107 --mde 0.003

Each --group is NAME:USERS:CONVERSIONS; the first group is the control.
--split is the planned allocation (default equal). --alpha defaults to 0.05.
--mde (absolute, e.g. 0.003 = 0.3 points) reports the sample size needed per group at 80% power.
With more than one variant, p-values and intervals are Bonferroni-corrected.
Requires Python 3.8+ (statistics.NormalDist).
"""
import argparse
import math
import sys
from statistics import NormalDist

N = NormalDist()


def chi2_sf(x, df):
    """Survival function of the chi-square distribution (regularized upper incomplete gamma)."""
    if x <= 0:
        return 1.0
    a, x2 = df / 2.0, x / 2.0
    if x2 < a + 1:  # series for the lower gamma, then complement
        term = total = 1.0 / a
        n = a
        while abs(term) > abs(total) * 1e-15:
            n += 1
            term *= x2 / n
            total += term
        return max(0.0, 1.0 - total * math.exp(-x2 + a * math.log(x2) - math.lgamma(a)))
    # continued fraction for the upper gamma (Lentz)
    b = x2 + 1 - a
    c, d = 1e300, 1 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-x2 + a * math.log(x2) - math.lgamma(a)) * h


def parse_group(text):
    try:
        name, users, conv = text.rsplit(":", 2)
        users, conv = int(users), int(conv)
    except ValueError:
        raise SystemExit(f"error: --group must be NAME:USERS:CONVERSIONS, got {text!r}")
    if users <= 0 or not 0 <= conv <= users:
        raise SystemExit(f"error: group {name!r} needs USERS > 0 and 0 <= CONVERSIONS <= USERS")
    return name, users, conv


def sample_size(p1, mde, alpha, power=0.8):
    p2 = p1 + mde
    if not 0 < p2 < 1:
        return None
    za, zb = N.inv_cdf(1 - alpha / 2), N.inv_cdf(power)
    pbar = (p1 + p2) / 2
    n = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / mde ** 2
    return math.ceil(n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", action="append", required=True, help="NAME:USERS:CONVERSIONS (first = control)")
    ap.add_argument("--split", help="planned allocation like 50:50 or 1:1:1 (default equal)")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--mde", type=float, help="minimum detectable effect, absolute (0.003 = 0.3 points)")
    args = ap.parse_args()

    groups = [parse_group(g) for g in args.group]
    if len(groups) < 2:
        raise SystemExit("error: need a control and at least one variant")
    weights = [float(w) for w in args.split.split(":")] if args.split else [1.0] * len(groups)
    if len(weights) != len(groups):
        raise SystemExit("error: --split needs one weight per group")

    total = sum(u for _, u, _ in groups)
    expected = [total * w / sum(weights) for w in weights]
    chi = sum((u - e) ** 2 / e for (_, u, _), e in zip(groups, expected))
    srm_p = chi2_sf(chi, len(groups) - 1)
    print("## Sample ratio check")
    print("  " + " / ".join(f"{n} {u:,}" for n, u, _ in groups)
          + f" vs planned {':'.join(f'{w:g}' for w in weights)} -> chi2 = {chi:.2f}, p = {srm_p:.3g}")
    if srm_p < 0.001:
        print("  SRM DETECTED (p < 0.001): the split is broken. Do not interpret the results below;")
        print("  find the cause (assignment bug, bot filtering, redirects, logging) first.")
    else:
        print("  OK: no sample ratio mismatch.")

    comparisons = len(groups) - 1
    alpha = args.alpha / comparisons
    z_crit = N.inv_cdf(1 - alpha / 2)
    cname, cu, cc = groups[0]
    p1 = cc / cu
    print(f"\n## Conversion (alpha {args.alpha}" + (f", Bonferroni-corrected to {alpha:.4f}" if comparisons > 1 else "") + ")")
    print(f"  {'group':<12} {'users':>10} {'conv':>8} {'rate':>8}")
    for name, u, c in groups:
        print(f"  {name:<12} {u:>10,} {c:>8,} {c / u:>8.2%}")

    for name, u, c in groups[1:]:
        p2 = c / u
        diff = p2 - p1
        se = math.sqrt(p1 * (1 - p1) / cu + p2 * (1 - p2) / u)
        pool = (cc + c) / (cu + u)
        se_pool = math.sqrt(pool * (1 - pool) * (1 / cu + 1 / u))
        z = diff / se_pool if se_pool else 0.0
        p = 2 * (1 - N.cdf(abs(z)))
        lo, hi = diff - z_crit * se, diff + z_crit * se
        level = 1 - alpha
        verdict = ("significant" if p < alpha else "not significant")
        print(f"\n  {name} vs {cname}: {diff * 100:+.2f} pts ({diff / p1:+.1%} relative) "
              f"{level:.1%} CI [{lo * 100:+.2f}, {hi * 100:+.2f}] pts, p = {p:.3g} -> {verdict}")
        if p >= alpha and diff != 0:
            need = sample_size(p1, abs(diff), alpha)
            if need:
                print(f"  To detect a {abs(diff) * 100:.2f}-pt effect at 80% power: ~{need:,} users per group "
                      f"(have {min(cu, u):,}).")

    if args.mde:
        need = sample_size(p1, args.mde, alpha)
        print(f"\n## Power\n  Detecting {args.mde * 100:.2f} pts from a {p1:.2%} baseline at 80% power "
              f"needs ~{need:,} users per group." if need else "\n## Power\n  --mde out of range for this baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
