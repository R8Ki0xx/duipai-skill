# Generators that find bugs (随机数据怎么造)

Generator contract: `gen.py <seed> <scale>` prints exactly one valid test to
stdout. `scale = init()` (from `genlib`) seeds `random` from `<seed>`.

## Rules
1. **Valid input only.** Implement every constraint and guarantee of the
   statement: ranges, distinctness, sortedness, "the graph is connected",
   "a solution exists", "sum of n over all tests ≤ 2·10⁵", string alphabet,
   1-based labels. Invalid data creates fake counterexamples. When the guarantee
   is hard to generate directly, generate-and-reject (loop until the condition
   holds) – inputs are tiny, so this is cheap.
2. **Small first.** `n ≤ scale`, values from a tiny range. Most WA bugs show up
   with n ≤ 5. The runner ramps scale 1 → 10 and then shrinks the failure.
3. **Small value ranges create structure**: duplicates, ties, zeros, equal
   neighbours, all-equal arrays. Use `[1, 3]`, `[-3, 3]`, alphabet `"ab"`.
4. **Mix distributions per case** – pick one at random each time:
   uniform, all equal, sorted, reversed, boundary-heavy (`edgy`), alternating.
5. **Multi-test**: print `T = rint(1, 4)` cases, so state leaking between test
   cases (uncleared arrays, globals) is exercised.
6. **Deterministic**: only the `random` module seeded by `init()`.

## genlib cheat sheet

| need | call |
|---|---|
| int in [lo, hi] | `rint(lo, hi)` |
| int that likes boundaries | `edgy(lo, hi, p=0.3)` |
| array | `rarr(n, lo, hi)`, boundary-biased `rarr(n, lo, hi, p_edge=0.3)` |
| distinct values | `distinct(n, lo, hi)` |
| permutation of 1..n | `perm(n)` (0-based: `perm(n, 0)`) |
| string | `rstr(n, "ab")`, periodic/repetitive `rword(n, "abc")` |
| sizes summing to S | `split_sum(S, k)` |
| interval l ≤ r | `interval(lo, hi)` |
| tree edges | `tree(n, shape)` – shapes: random chain star binary caterpillar deep broom any |
| parent array p_i < i | `tree_parents(n, shape)` |
| graph | `graph(n, m, connected=True, directed=False, self_loops=False, multi=False)` |
| DAG | `dag(n, m)` |
| weights | `weighted(edges, 1, 10)` |
| grid | `grid(h, w, ".#", weights=[3, 1])` |
| print | `out(n)`, `out(a)` (list → space separated), `out_lines(edges)` |

## Recipes

```python
# array problem, values with many ties and negatives
n = rint(1, scale)
mode = rint(0, 3)
if mode == 0:   a = rarr(n, -3, 3)
elif mode == 1: a = [rint(-3, 3)] * n                    # all equal
elif mode == 2: a = sorted(rarr(n, -3, 3))
else:           a = rarr(n, -10**9, 10**9, p_edge=0.5)   # boundaries / overflow
out(n); out(a)

# tree problem
n = rint(1, scale)
out(n)
out_lines(tree(n, "any"))

# connected weighted graph
n = rint(2, scale)
m = rint(n - 1, min(n * (n - 1) // 2, n + 3))
out(n, m)
out_lines(weighted(graph(n, m, connected=True), 1, 5))

# queries
n, q = rint(1, scale), rint(1, scale)
out(n, q); out(rarr(n, 1, 5))
for _ in range(q):
    if chance(0.5):
        l, r = interval(1, n); out(1, l, r)
    else:
        out(2, rint(1, n), rint(1, 5))

# guarantee "an answer exists": build the answer first, then the input from it
# guarantee hard to construct: generate-and-reject
while True:
    a = rarr(n, 1, 5)
    if valid(a): break
```

## Big tests (`--no-brute`)
To hunt RE / TLE / overflow, let large scales produce maximum constraints, e.g.

```python
n = scale if scale > 10 else rint(1, scale)   # --scale 200000 => n = 200000 exactly
V = 10**9 if scale > 10 else 5
```

then run `duipai.py --sol sol.cpp --gen gen.py --no-brute --scale 200000 -n 10`.
Include worst cases for the algorithm: sorted input for naive quicksort, chain
trees for recursion depth, star trees for per-node loops, all-equal values for hashing.
