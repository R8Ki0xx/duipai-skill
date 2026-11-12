# Common WA / RE / TLE causes (常见错误清单)

Use when random stress testing finds nothing, or to name the bug class once a
counterexample is found. Check the code line by line against each item.

## Overflow & numbers
- `int` products/sums that exceed 2³¹−1 (`a[i] * a[j]`, `n * n`, prefix sums,
  answer accumulators). Literal `1 << 40` (needs `1LL << 40`). `INF = 1e9` too small
  when distances add up; `INF = 0x3f3f3f3f` added twice overflows.
- Modular arithmetic: missing `% MOD` after multiplication, negative result of
  `(a - b) % MOD` (add `MOD`), division without modular inverse.
- `pow`, `sqrt`, `log2`, `ceil(a / b)` with floating point → off by one for large
  values. Use integer `isqrt`, `(a + b - 1) / b` for positive ceil, and beware
  negative numbers (`/` truncates toward 0 in C++, floors in Python `//`).
- `abs` of `long long` via `int abs`, `max(int, long long)` mismatches.
- Floating output precision: print with `setprecision(10)` / `fixed`; `-0.000`.

## Initialisation & state
- Multi-test: global arrays / vectors / maps / counters not reset between cases;
  resetting only `n` elements while the next case uses `n+1`; `memset` on the
  whole array each case → TLE when T is large.
- Answer initialised to 0 / INT_MAX when the true answer can be negative / larger
  (max-subarray with all negatives, min over empty set).
- Uninitialised local variables (works on your machine, WA on the judge).
- Early `return`/`break` while reading input → the rest of the case is read as the
  next case.

## Indices & boundaries
- 0-based vs 1-based mix-ups; `<` vs `<=` in loops; `l == r`; empty ranges.
- n = 1, n = 0 (if allowed), k = 0, k = n, all elements equal, already sorted.
- Array sizes `N = 1e5` when n can be exactly 1e5 and the code writes `a[n]` or
  `a[n+1]`; sizes for 2·n (segment tree needs 4·n), edges array for undirected
  graphs needs 2·m.
- Binary search: wrong `mid` rounding → infinite loop; wrong final `lo/hi`.
- Two pointers / sliding window not shrinking correctly on duplicates.

## Algorithmic assumptions
- Greedy that fails on ties or on a specific order (counterexample usually n ≤ 4).
- DP: wrong base case, wrong iteration order, missing state, 0/1 vs unbounded
  knapsack loop direction, not taking the max over all end states.
- Graphs: assuming connected / no multi-edges / no self-loops when the statement
  allows them; directed vs undirected; 1 vs multiple components; visited reset.
- Trees: assuming node 1 is the root when edges come in arbitrary order; deep
  recursion (chain of 2·10⁵) → stack overflow (use iterative DFS or bigger stack).
- Sorting comparator not a strict weak order (`<=`) → RE/UB in `std::sort`.
- Hashing collisions (single mod, `unordered_map` anti-hash tests on Codeforces).
- Strings: off-by-one in KMP/Z, forgetting the case where the pattern is longer.

## Output
- `Yes` vs `YES`, missing newline between multi-test answers, extra spaces when
  the checker is strict (use `--cmp lines` / `exact` to test).
- Printing debug output to stdout; `endl` in a loop with 10⁶ lines → TLE.
- Python: `print` in a loop with 10⁵ lines → TLE; use `sys.stdout.write` / join.
  Recursion limit (`sys.setrecursionlimit`) and still crashing on deep recursion.

## Input
- Reading with `scanf("%d")` into `long long`; mixing `cin` and `getline`.
- Not using fast IO for 10⁶ numbers (`ios::sync_with_stdio(false); cin.tie(0);`).
- Python `input()` on 10⁵ lines → TLE; read `sys.stdin.buffer` at once.

## Judge / environment
- Windows vs Linux: `%lld` vs `%I64d` on very old judges, stack size (Codeforces
  has 256 MB stack; many OJs have 8 MB), `long` is 32-bit on Windows.
- Undefined behaviour that happens to work locally: compile with
  `--cxxflags "-O1 -g -fsanitize=address,undefined -std=c++17"` (Linux/macOS) or
  `-D_GLIBCXX_DEBUG` (any g++) for checked STL containers.
