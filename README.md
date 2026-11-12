# duipai · 对拍

**English** | [中文](#中文说明)

A Claude Code plugin that finds the test case behind your **Wrong Answer**.

You give Claude a problem and your solution. It writes an **independent brute force**,
a **random small-data generator**, runs a **stress-test loop** (对拍) until the two
programs disagree, **shrinks** the failing input, and explains which line is wrong,
then checks the fix with thousands of new cases.

Works for Codeforces, AtCoder, LeetCode, Luogu, 蓝桥杯, ICPC/CCPC and OI problems ·
C++ / C / Python solutions · Windows, macOS, Linux · ask in any language.

```
COUNTEREXAMPLE FOUND
verdict  : WA
seed     : 898519184   scale: 1
reproduce: python "duipai/gen.py" 898519184 1
detail   : token #1 (sol output line 1): expected '-3', got '0'
--- input ---
1
-3
--- expected (brute) ---
-3
--- got (sol) ---
0
```

## Install

```text
/plugin marketplace add R8Ki0xx/duipai
/plugin install duipai@duipai
```

Or from a local clone: `/plugin marketplace add /path/to/duipai`.
You can also copy `skills/duipai/` into `~/.claude/skills/` to use it as a plain skill.

Requirements: Python ≥ 3.8, and `g++` or `clang++` for C/C++
(Windows: [MSYS2](https://www.msys2.org/) / MinGW-w64 on PATH; macOS: `xcode-select --install`).

## Use

Just ask, for example:

> My solution to CF 1234C gets WA on test 7. Find a counterexample. *(paste statement + code)*

> 这题我过了样例但是 WA 了，帮我对拍一下 `sol.cpp`

> LeetCode: my `maxProfit` fails a hidden case, stress-test it.

Claude will create a `duipai/` folder next to your code containing `brute.py`,
`gen.py`, (optionally) `checker.py`, `samples/`, and `fail/` with the saved
counterexample, so you can re-run everything yourself.

## The runner on its own

`skills/duipai/scripts/duipai.py` is a standalone, stdlib-only stress tester you
can use without Claude:

```bash
python duipai.py --sol sol.cpp --brute brute.py --gen gen.py
python duipai.py --sol sol.cpp --brute brute.py --gen gen.py --checker checker.py   # many valid answers
python duipai.py --sol sol.cpp --brute brute.py --gen gen.py --cmp float:1e-6
python duipai.py --sol sol.cpp --gen gen.py --no-brute --scale 200000                # RE / TLE hunt at max size
python duipai.py --sol sol.cpp --brute brute.py --input samples/                     # x.in + x.out files
```

| feature | details |
|---|---|
| generator protocol | `gen <seed> <scale>`; same seed ⇒ same test; scale ramps 1 → 10 so first failures are small |
| verdicts | WA, RE (with readable crash reason, e.g. `STACK_OVERFLOW`, `SIGSEGV`), TLE, plus `BRUTE_ERROR` / `GEN_ERROR` / `CHECKER_ERROR` so a broken brute force is never blamed on you |
| comparison | `tokens` (default, like Codeforces), `lines`, `exact`, `float:EPS`, or a checker `checker <in> <sol_out> <brute_out>` (exit 0 = OK) |
| shrinking | after a failure, searches smaller scales and other seeds and keeps the shortest failing input |
| compiling | `g++ -O2 -std=c++17`, cached by source hash; Windows builds are static with a 256 MB stack; Linux/macOS stack limit raised |
| speed | cases run in parallel (`-j`) |
| output | `fail/input.txt`, `sol_out.txt`, `brute_out.txt`, `info.json`; `--json` summary for tools |
| exit codes | 0 pass · 1 counterexample · 2 setup/compile error · 3 generator/brute/checker error |

`scripts/genlib.py` has helpers for generators: `rint`, `edgy` (boundary-biased
values), `rarr`, `distinct`, `perm`, `rstr`, `rword`, `split_sum`, `tree(n, shape)`
(random / chain / star / binary / caterpillar / deep / broom), `graph`, `dag`,
`weighted`, `grid`, `out`.

## Repository layout

```
.claude-plugin/          plugin.json + marketplace.json
skills/duipai/SKILL.md   the workflow Claude follows
skills/duipai/scripts/   duipai.py (runner), genlib.py (data helpers)
skills/duipai/templates/ gen.py, brute.py, brute.cpp, checker.py
skills/duipai/references/ brute-force patterns, generator patterns, common WA causes
examples/                three buggy solutions (with fixes) to try
tests/run_tests.py       end-to-end tests of the runner
```

Try an example:

```bash
python skills/duipai/scripts/duipai.py --sol examples/max-subarray/sol.cpp --brute examples/max-subarray/brute.py --gen examples/max-subarray/gen.py
```

Run the tests: `python tests/run_tests.py`.

---

## 中文说明

一个 Claude Code 插件：**自动对拍，帮你找出 WA 的反例。**

把题目和你的代码交给 Claude，它会写一个**和你思路无关的暴力解**、一个**小数据随机生成器**，
然后循环对拍直到两边输出不一致，自动**缩小反例**，逐行分析你的代码错在哪里，
修好之后再跑几千组数据验证。

适用于 Codeforces、AtCoder、LeetCode、洛谷、蓝桥杯、ICPC/CCPC、OI · 支持 C++ / C / Python ·
Windows、macOS、Linux 通用 · 用中文或英文提问都可以。

### 安装

```text
/plugin marketplace add R8Ki0xx/duipai
/plugin install duipai@duipai
```

本地克隆也可以：`/plugin marketplace add /path/to/duipai`。
也可以直接把 `skills/duipai/` 复制到 `~/.claude/skills/` 当普通 skill 使用。

依赖：Python ≥ 3.8；C/C++ 需要 `g++` 或 `clang++`
（Windows 推荐 [MSYS2](https://www.msys2.org/) / MinGW-w64，并加入 PATH）。

### 使用

直接说就行，例如：

> 这题我过了样例但是 WA on test 5，帮我对拍找反例（附题面和代码）

> 帮我给这道蓝桥杯题写个暴力和数据生成器，拍一下 `main.cpp`

> 我的 LeetCode 代码有个隐藏用例过不了，帮我找出来

Claude 会在你的代码旁边建一个 `duipai/` 文件夹：`brute.py`（暴力）、`gen.py`（生成器）、
需要时的 `checker.py`（SPJ）、`samples/`（样例）以及保存反例的 `fail/`，你可以随时自己重跑。

### 对拍器单独使用

`skills/duipai/scripts/duipai.py` 只依赖 Python 标准库，可以脱离 Claude 单独用：

```bash
python duipai.py --sol sol.cpp --brute brute.py --gen gen.py                         # 普通对拍
python duipai.py --sol sol.cpp --brute brute.py --gen gen.py --checker checker.py    # 多解题 / SPJ
python duipai.py --sol sol.cpp --brute brute.py --gen gen.py --cmp float:1e-6        # 浮点误差
python duipai.py --sol sol.cpp --gen gen.py --no-brute --scale 200000                 # 只跑大数据查 RE/TLE
python duipai.py --sol sol.cpp --brute brute.py --input samples/                      # 跑样例 x.in / x.out
```

- 生成器调用方式 `gen <seed> <scale>`：相同 seed 必然生成相同数据；scale 从 1 逐步增大，先找到的反例就很小。
- 结果分类：WA、RE（附可读的崩溃原因，如栈溢出、段错误）、TLE；暴力/生成器/SPJ 自己出错会单独报
  `BRUTE_ERROR` 等，不会冤枉你的代码。
- 比较方式：默认按 token 比较（与 Codeforces 一致），也支持 `lines`、`exact`、`float:EPS` 和自定义 checker。
- 找到反例后自动缩小：在更小的规模和其他种子里搜索，保留最短的失败输入。
- Windows 下静态链接并开 256MB 栈，深递归不会误报 RE；Linux/macOS 自动放开栈限制。
- 退出码：0 未找到反例 · 1 找到反例 · 2 编译/参数错误 · 3 生成器/暴力/SPJ 出错。

## License

MIT
