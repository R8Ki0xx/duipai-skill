# -*- coding: utf-8 -*-
"""
genlib - small helpers for duipai random-test generators.

    from genlib import *
    scale = init()            # seeds `random` from argv[1]; scale = argv[2] (default 10)
    n = rint(1, scale)
    a = rarr(n, -5, 5)
    out(n); out(*a)

Conventions
  * The generator is called as  gen.py <seed> <scale>.  The same (seed, scale)
    must always print the same test, so use only the `random` module that
    init() seeds (never time(), uuid, os.urandom, set iteration order, ...).
  * `scale` is a size budget: scale 1..10 = tiny tests a brute force can solve.
    Use it as the upper bound for n (or for n*m, string length, ...).
  * Node labels are 1-based by default (base=1); pass base=0 for 0-based problems.

All functions use the global `random` module, so you can freely mix them with
random.randint / random.choice / random.shuffle.
"""
import random
import sys

__all__ = [
    "init", "random", "rint", "edgy", "rarr", "distinct", "perm", "rstr", "rword",
    "split_sum", "interval", "tree_parents", "tree", "graph", "dag", "weighted",
    "grid", "matrix", "chance", "out", "out_lines", "SHAPES",
]

SEED = 0
SCALE = 10


def init(default_scale=10):
    """Read <seed> <scale> from the command line, seed `random`, return scale."""
    global SEED, SCALE
    argv = sys.argv[1:]
    SEED = int(argv[0]) if len(argv) > 0 else random.randrange(1 << 30)
    SCALE = int(argv[1]) if len(argv) > 1 else default_scale
    random.seed(SEED)
    return SCALE


# ----------------------------------------------------------------- numbers ---
def rint(lo, hi):
    """Uniform integer in [lo, hi]."""
    return random.randint(lo, hi)


def chance(p):
    """True with probability p."""
    return random.random() < p


def edgy(lo, hi, p=0.3):
    """Integer in [lo, hi] that hits the boundaries (lo, lo+1, hi-1, hi, 0) with probability p.

    Boundaries are where off-by-one and overflow bugs live."""
    if hi <= lo or not chance(p):
        return random.randint(lo, hi)
    cands = [lo, hi, min(lo + 1, hi), max(hi - 1, lo)]
    if lo <= 0 <= hi:
        cands.append(0)
    return random.choice(cands)


def rarr(n, lo, hi, p_edge=0.0):
    """List of n integers in [lo, hi]; p_edge > 0 biases values toward the boundaries."""
    if p_edge > 0:
        return [edgy(lo, hi, p_edge) for _ in range(n)]
    return [random.randint(lo, hi) for _ in range(n)]


def distinct(n, lo, hi):
    """n pairwise-distinct integers in [lo, hi], random order."""
    if hi - lo + 1 < n:
        raise ValueError("distinct(%d, %d, %d): range too small" % (n, lo, hi))
    return random.sample(range(lo, hi + 1), n)


def perm(n, base=1):
    """Random permutation of base..base+n-1."""
    p = list(range(base, base + n))
    random.shuffle(p)
    return p


def split_sum(total, k, min_part=1):
    """k random integers >= min_part that add up to total (e.g. sizes of multi-test cases)."""
    if k <= 0:
        return []
    free = total - k * min_part
    if free < 0:
        raise ValueError("split_sum: total %d too small for %d parts >= %d" % (total, k, min_part))
    cuts = sorted(random.randint(0, free) for _ in range(k - 1))
    parts, prev = [], 0
    for c in cuts + [free]:
        parts.append(c - prev + min_part)
        prev = c
    return parts


def interval(lo, hi):
    """Random (l, r) with lo <= l <= r <= hi."""
    a, b = random.randint(lo, hi), random.randint(lo, hi)
    return (a, b) if a <= b else (b, a)


# ----------------------------------------------------------------- strings ---
def rstr(n, alphabet="ab"):
    """Random string of length n. Small alphabets ('ab') find string bugs fastest."""
    return "".join(random.choice(alphabet) for _ in range(n))


def rword(n, alphabet="abc", p_repeat=0.5):
    """String with lots of repetition (periodic chunks) - good for hashing / KMP / Z bugs."""
    if n == 0:
        return ""
    if not chance(p_repeat):
        return rstr(n, alphabet)
    period = random.randint(1, max(1, n // 2))
    unit = rstr(period, alphabet)
    s = (unit * (n // period + 1))[:n]
    if chance(0.5):  # one mutation breaks perfect periodicity
        i = random.randrange(n)
        s = s[:i] + random.choice(alphabet) + s[i + 1:]
    return s


# ------------------------------------------------------------------- trees ---
SHAPES = ("random", "chain", "star", "binary", "caterpillar", "deep", "broom")


def tree_parents(n, shape="random"):
    """Parents p[2..n] with p[i] < i (labels are NOT shuffled): returns list of length n-1.

    Use for input formats like "p_2 p_3 ... p_n, p_i < i"."""
    if shape == "any":
        shape = random.choice(SHAPES)
    par = []
    for v in range(2, n + 1):
        if shape == "chain":
            p = v - 1
        elif shape == "star":
            p = 1
        elif shape == "binary":
            p = v // 2
        elif shape == "caterpillar":
            spine = max(1, n // 2)
            p = v - 1 if v <= spine else random.randint(1, spine)
        elif shape == "deep":
            p = random.randint(max(1, v - 3), v - 1)
        elif shape == "broom":
            p = v - 1 if v <= max(1, n // 2) else max(1, n // 2)
        else:
            p = random.randint(1, v - 1)
        par.append(p)
    return par


def tree(n, shape="random", base=1, shuffle=True):
    """Edges (u, v) of a random tree on n nodes. shape in SHAPES or 'any'.

    With shuffle=True node labels, edge order and edge direction are randomized,
    so the tree is NOT guaranteed to be rooted at node `base`."""
    par = tree_parents(n, shape)
    edges = [(par[i], i + 2) for i in range(n - 1)]
    if shuffle:
        lab = perm(n, 1)
        edges = [(lab[u - 1], lab[v - 1]) for u, v in edges]
        edges = [(v, u) if chance(0.5) else (u, v) for u, v in edges]
        random.shuffle(edges)
    return [(u - 1 + base, v - 1 + base) for u, v in edges]


# ------------------------------------------------------------------ graphs ---
def graph(n, m, connected=False, directed=False, self_loops=False, multi=False, base=1):
    """m random edges on n nodes. Simple graph unless self_loops / multi are allowed.

    connected=True (undirected) starts from a random spanning tree, so m >= n-1."""
    max_m = n * (n - 1) // (1 if directed else 2) + (n if self_loops else 0)
    if not multi and m > max_m:
        raise ValueError("graph: m=%d exceeds %d possible edges for n=%d" % (m, max_m, n))
    if connected and m < n - 1:
        raise ValueError("graph: connected graph on %d nodes needs m >= %d" % (n, n - 1))
    edges, seen = [], set()

    def key(u, v):
        return (u, v) if directed else (min(u, v), max(u, v))

    if connected:
        for u, v in tree(n, base=1):
            edges.append((u, v))
            seen.add(key(u, v))
    while len(edges) < m:
        u, v = random.randint(1, n), random.randint(1, n)
        if u == v and not self_loops:
            continue
        k = key(u, v)
        if not multi and k in seen:
            continue
        seen.add(k)
        edges.append((u, v))
    random.shuffle(edges)
    return [(u - 1 + base, v - 1 + base) for u, v in edges]


def dag(n, m, base=1):
    """m distinct edges of a random DAG (edges go forward in a hidden random order)."""
    if m > n * (n - 1) // 2:
        raise ValueError("dag: too many edges")
    order = perm(n, 1)
    seen, edges = set(), []
    while len(edges) < m:
        i, j = random.randint(0, n - 1), random.randint(0, n - 1)
        if i == j:
            continue
        if i > j:
            i, j = j, i
        if (i, j) in seen:
            continue
        seen.add((i, j))
        edges.append((order[i], order[j]))
    random.shuffle(edges)
    return [(u - 1 + base, v - 1 + base) for u, v in edges]


def weighted(edges, lo, hi):
    """Attach a random weight in [lo, hi] to each edge: [(u, v, w), ...]."""
    return [(u, v, random.randint(lo, hi)) for u, v in edges]


# ------------------------------------------------------------------- grids ---
def grid(h, w, chars=".#", weights=None):
    """List of h strings of length w over `chars` (optional weights, e.g. [3, 1])."""
    return ["".join(random.choices(chars, weights=weights, k=w)) for _ in range(h)]


def matrix(h, w, lo, hi):
    return [[random.randint(lo, hi) for _ in range(w)] for _ in range(h)]


# ------------------------------------------------------------------ output ---
def out(*xs):
    """Print values on one line separated by spaces (lists/tuples are expanded)."""
    flat = []
    for x in xs:
        if isinstance(x, (list, tuple)):
            flat.extend(x)
        else:
            flat.append(x)
    print(*flat)


def out_lines(rows):
    """Print each row (a value or a list/tuple) on its own line."""
    for r in rows:
        out(r)
