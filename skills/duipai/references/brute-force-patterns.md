# Writing a brute force you can trust (暴力怎么写才可信)

The brute force is the oracle. If it is wrong, every "counterexample" is fake and
the user loses trust. Optimise for **obviously correct**, never for speed.

## Principles
1. **Re-read the statement, not the user's code.** Implement the definition
   literally. Never reuse the user's formula, greedy choice, DP transition, or
   "observation" – a shared misunderstanding makes both programs agree on the
   wrong answer.
2. **Enumerate the search space** the statement describes, then filter by the
   conditions and take min / max / count. Exponential is fine: scale ≤ 10.
3. **Use big integers / long long everywhere** (Python ints are exact; in C++ use
   `long long` / `__int128`). Use exact fractions (`fractions.Fraction`) instead of
   floats when the answer is rational.
4. **Count modulo at the end**: compute exact counts in Python, then `% MOD`.
5. **Same output format** as the expected answer: spelling and case of
   `YES/NO/Yes/-1/IMPOSSIBLE`, one answer per line for multi-test, precision.
6. **Validate on the samples** (`duipai.py --brute brute.py --input samples/`).
7. If the statement allows several answers, the brute only needs *one*; the
   checker compares quality (see `templates/checker.py`).

## Patterns by problem type

| problem says… | brute force |
|---|---|
| max/min/count over subarrays / substrings | all `(l, r)` pairs, compute directly: O(n³) |
| choose a subset / subsequence | `for mask in range(1 << n)` or `itertools.combinations` |
| order / arrangement / permutation | `itertools.permutations` (n ≤ 8) |
| assign each item one of k options | `itertools.product(range(k), repeat=n)` |
| game (two players, optimal play) | memoised minimax over full state (`functools.lru_cache`) |
| min operations to reach a state | BFS over all states (encode state as tuple) |
| process a sequence of operations / queries | simulate each query naively on a plain list |
| shortest path | Floyd–Warshall or Bellman–Ford on the small graph |
| tree queries (LCA, path sums, subtree) | walk parent pointers / DFS per query |
| counting with constraints mod p | enumerate all objects, count exact, mod at the end |
| number theory (gcd, divisors, primes) | trial loops up to the value (values are small) |
| "minimum k such that…" (binary search answers) | try k = 0, 1, 2, … in order |
| geometry | exact integer / Fraction arithmetic, check all pairs/triples |
| interactive problem | write a local interactor instead; duipai covers offline problems only |

## Snippets

```python
# all subsets
for mask in range(1 << n):
    chosen = [a[i] for i in range(n) if mask >> i & 1]

# all subarrays
for l in range(n):
    for r in range(l, n):
        seg = a[l:r + 1]

# BFS over states
from collections import deque
dist = {start: 0}; q = deque([start])
while q:
    s = q.popleft()
    for t in neighbours(s):
        if t not in dist:
            dist[t] = dist[s] + 1; q.append(t)

# game with memo
from functools import lru_cache
@lru_cache(None)
def win(state):          # True if player to move wins
    return any(not win(t) for t in moves(state))
```

## Speed
If Python is too slow even for `--max-scale 8`, first shrink the scale (bugs
appear on tiny inputs far more often than people expect), then switch to
`templates/brute.cpp`. Raise `--brute-timeout` rather than making the brute clever.

## LeetCode
Write the brute as a standalone stdin → stdout program over the *same* input
format that the sol harness uses (e.g. first line `n`, second line the array).
