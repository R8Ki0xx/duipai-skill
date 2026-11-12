---
name: duipai
description: >-
  Stress-test (对拍) a competitive-programming solution to find the input that
  makes it fail. Writes an independent brute force, a random small-data generator
  and runs a compare loop until a minimal counterexample (反例) shows up, then
  explains the bug. Use when someone's code gets Wrong Answer / WA / RE / TLE /
  "fails on hidden test" / "过了样例但WA" / "找反例" / "帮我对拍" / "卡数据" / "hack",
  or asks for a brute force (暴力), random test data (随机数据) or a stress test
  for a Codeforces, AtCoder, LeetCode, Luogu, 蓝桥杯, ICPC/CCPC or OI problem.
  Supports C++, C and Python solutions on Windows, macOS and Linux.
---

# duipai — find the counterexample behind a Wrong Answer

**Reply in the user's language** (中文 → 中文, English → English, etc.). File
contents (code, comments) can stay in English.

The goal is a **small, concrete failing input + the root cause + a verified fix**,
not a code review. Do not guess at bugs before the counterexample is in hand —
the stress test is cheap, guessing is not.

Tools in this skill (paths relative to this SKILL.md's folder):

| file | role |
|---|---|
| `scripts/duipai.py` | runner: compiles, loops `gen → sol vs brute`, shrinks, saves the failing case |
| `scripts/genlib.py` | random data helpers (arrays, permutations, strings, trees, graphs, grids) |
| `templates/` | `gen.py`, `brute.py`, `brute.cpp`, `checker.py` starting points |
| `references/brute-force-patterns.md` | how to write a brute force you can trust |
| `references/generator-patterns.md` | how to generate valid, bug-revealing data |
| `references/common-wa-causes.md` | checklist when random testing finds nothing |

Requirements: Python ≥ 3.8; `g++` or `clang++` for C/C++ code.

## Workflow

### 1. Gather
Get (ask only for what is missing):
- the **problem statement** – pasted text, a URL (fetch it), or a screenshot;
  especially input format, constraints, multi-test (`T` cases), and whether
  **several answers are accepted** ("print any");
- the user's **solution** – a file path or pasted code.

Create a work folder `duipai/` next to the user's solution (or in the current
directory). Put the solution there as `sol.cpp` / `sol.py` **unchanged**, except:
- remove/disable `freopen(...)` and file I/O so it reads stdin and writes stdout;
- for **LeetCode-style** code (`class Solution` with a method), add a small
  `main` that reads the test from stdin, calls the method, prints the result.
  Write the brute force with the same stdin format.

Copy `scripts/genlib.py` into `duipai/` so `gen.py` also runs standalone.

### 2. Write the brute force (`duipai/brute.py`)
Read `references/brute-force-patterns.md` the first time. Rules:
- **Independent** of the user's idea – no greedy/DP insight copied from their code.
  Prefer exhaustive search: all subsets, all permutations, all intervals, direct
  simulation of the statement, BFS over all states, O(n³)/O(2ⁿ·n) is fine.
- **Obviously correct** by reading it once. Shorter is better.
- Python by default; C++ (`templates/brute.cpp`) only if Python is too slow even
  for scale ≤ 10.
- Match the output format exactly (same "-1"/"NO"/"YES" spelling, same case).
- Tell the user its complexity and why it is correct, in one or two lines.

### 3. Write the generator (`duipai/gen.py`)
Start from `templates/gen.py`; read `references/generator-patterns.md` the first time.
- Called as `gen.py <seed> <scale>`; `scale = init()` seeds `random`. Never use
  time-based randomness – every case must be reproducible from its seed.
- `scale` is the size budget (1‥10 by default): use it as the max `n`. Small sizes
  and **small value ranges** (e.g. values in [-5, 5] or [1, 3]) find bugs fastest:
  duplicates, ties, negatives, n = 1, all-equal arrays.
- Respect **every guarantee** in the statement (distinct values, connected tree,
  sorted input, `sum n ≤ …`, answer exists, …). Data that violates the constraints
  produces fake counterexamples.
- For multi-test problems print `T ≥ 2` cases most of the time – that is how
  "forgot to reset between test cases" bugs are caught.

### 4. Checker (only if several answers are valid)
If the problem accepts any valid answer (any path, any pair, any permutation,
floating answers with a tolerance), write `duipai/checker.py` from
`templates/checker.py`: verify the sol's answer is *valid* and *as good as* the
brute's. For floating outputs use `--cmp float:1e-6` instead of a checker.

### 5. Sanity-check the brute force on the samples
Save the statement's samples as `duipai/samples/1.in`, `1.out`, … and run:

```bash
python <skill>/scripts/duipai.py --sol duipai/sol.cpp --brute duipai/brute.py --input duipai/samples
```

If the **brute** fails a sample, fix the brute before going on. (If the sol fails a
sample, that is already the counterexample.)

### 6. Stress test

```bash
python <skill>/scripts/duipai.py --sol duipai/sol.cpp --brute duipai/brute.py --gen duipai/gen.py
```

Useful options: `--checker duipai/checker.py`, `--cmp lines|exact|float:1e-6`,
`-n 5000`, `--time-limit 120`, `--max-scale 8` (smaller if the brute is
exponential), `--seed S` to reproduce, `--timeout 2` per sol run, `--json`
for a machine-readable summary. Run with a Bash timeout above `--time-limit`.

Exit codes: **0** no counterexample · **1** counterexample (WA/RE/TLE) saved in
`duipai/fail/` · **2** setup/compile error · **3** generator/brute/checker broke
(`BRUTE_ERROR` is never the user's bug – fix your brute/gen and rerun).

The runner ramps the scale up from 1, so the first failure is already small; it
then spends a few seconds **shrinking** (smaller scales, other seeds) and keeps the
shortest failing input.

### 7. Diagnose and fix
1. Show the user the counterexample: input, expected (brute), got (sol).
2. **Hand-trace** their code on that input and point to the exact line(s) where
   it goes wrong and why (e.g. "`ans` starts at 0, so an all-negative array
   returns 0 instead of −3"). Name the general bug class.
3. Propose the minimal fix (diff-style, in their code style). Edit their original
   file only if they asked you to fix it; otherwise put the fix in `duipai/sol_fixed.*`.
4. **Re-run the stress test on the fixed code** (e.g. `-n 5000`) and report the
   result. Also rerun the samples. A fix that is not re-verified is not done.

If a second, different counterexample appears after the fix, repeat.

### 8. If nothing is found
Random testing passing ≠ proof. Escalate in this order and tell the user what was tried:
1. Widen value ranges / change the value distribution (`edgy`, all-equal, sorted,
   reversed), try special shapes (chain, star, `tree(n, "any")`), more cases
   (`-n 20000 --time-limit 300`).
2. Bugs that need **large** input (overflow, TLE, stack overflow, array size):
   make the generator honour big scales, then run sol alone at max constraints:
   `--no-brute --scale 200000 --timeout 2 -n 20` (catches RE/TLE, prints slowest time).
   Compile with sanitizers to catch silent UB:
   `--cxxflags "-O1 -std=c++17 -g -fsanitize=address,undefined"` (Linux/macOS; not MinGW).
3. Walk `references/common-wa-causes.md` against the code line by line.
4. Re-read the statement with the user: misread constraints and output format are
   frequent "WA with correct algorithm" causes.

Be honest: if no counterexample was found, say so and list the remaining suspects.

## Reporting format (adapt to the user's language)

```
反例 / Counterexample (found after N cases, shrunk to K bytes):
<input>
期望 / Expected: …     你的输出 / Got: …
原因 / Root cause: <one or two sentences, with line reference>
修复 / Fix: <minimal diff>
验证 / Verified: 5000 random cases + samples pass after the fix.
```

Keep the work folder (`duipai/`) so the user can re-run it; mention the exact
command. Don't commit it to git unless asked.
