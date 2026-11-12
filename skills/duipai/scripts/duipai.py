#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
duipai.py - stress tester ("duipai") for competitive programming.

Runs   gen <seed> <scale>  ->  sol  vs  brute   in a loop until the outputs
disagree, then shrinks the failing case and reports a minimal counterexample.

Stress mode (default):
    python duipai.py --sol sol.cpp --brute brute.py --gen gen.py
Crash / time-limit hunt without a brute force:
    python duipai.py --sol sol.cpp --gen gen.py --no-brute --scale 200000
Check programs on fixed inputs (e.g. the problem's samples, *.in + *.out):
    python duipai.py --sol sol.cpp --brute brute.py --input samples/

Exit codes: 0 = no counterexample, 1 = counterexample found (WA/RE/TLE),
            2 = setup error (missing file, compile error, bad arguments),
            3 = tool error (generator / brute force / checker misbehaved).

Only the Python standard library is used (Python >= 3.8).
Supported programs: .cpp/.cc/.cxx (g++ or clang++), .c, .py, prebuilt executables.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

VERSION = "1.0.0"
IS_WIN = os.name == "nt"
HERE = os.path.dirname(os.path.abspath(__file__))

EXIT_PASS, EXIT_FOUND, EXIT_SETUP, EXIT_TOOL = 0, 1, 2, 3
FOUND_VERDICTS = ("WA", "RE", "TLE")
TOOL_VERDICTS = ("GEN_ERROR", "BRUTE_ERROR", "CHECKER_ERROR")

REPORT = sys.stdout  # switched to stderr in --json mode


class SetupError(Exception):
    """Problem the user has to fix before stress testing can start (exit 2)."""


# --------------------------------------------------------------------------- #
# console / formatting helpers
# --------------------------------------------------------------------------- #
def setup_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass


def say(msg=""):
    print(msg, file=REPORT, flush=True)


def warn(msg):
    print("[warn] " + msg, file=sys.stderr, flush=True)


def text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def clip(data: bytes, max_lines=40, max_chars=3000) -> str:
    s = text(data).replace("\r\n", "\n")
    lines = s.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    cut = False
    if len(lines) > max_lines:
        lines, cut = lines[:max_lines], True
    out = "\n".join(lines)
    if len(out) > max_chars:
        out, cut = out[:max_chars], True
    if not out:
        out = "<empty>"
    if cut:
        out += "\n... (truncated, see the saved file)"
    return out


WIN_CODES = {
    0xC0000005: "ACCESS_VIOLATION - out-of-bounds access / null pointer",
    0xC00000FD: "STACK_OVERFLOW - recursion too deep or huge local array",
    0xC0000094: "INTEGER_DIVIDE_BY_ZERO",
    0xC0000095: "INTEGER_OVERFLOW",
    0xC0000409: "STACK_BUFFER_OVERRUN / fast-fail - abort(), failed assert, uncaught exception",
    0xC000001D: "ILLEGAL_INSTRUCTION",
    0xC0000374: "HEAP_CORRUPTION - writing outside a vector/array",
    0xC0000135: "DLL_NOT_FOUND - compiler runtime DLLs are not on PATH",
    0xC0000139: "ENTRYPOINT_NOT_FOUND - wrong libstdc++ DLL found on PATH",
}
SIGNALS = {
    6: "SIGABRT - abort(), failed assert, uncaught exception",
    8: "SIGFPE - division by zero",
    9: "SIGKILL - killed (memory limit?)",
    11: "SIGSEGV - out-of-bounds access / null pointer / stack overflow",
}


def describe_exit(code):
    if code is None:
        return "could not start"
    if code < 0:
        return "killed by signal %d (%s)" % (-code, SIGNALS.get(-code, "?"))
    if IS_WIN and code >= 0xC0000000:
        return "0x%08X (%s)" % (code, WIN_CODES.get(code, "Windows exception"))
    if code == 3 and IS_WIN:
        return "exit code 3 (abort() / failed assert on MinGW)"
    if code == 1:
        return "exit code 1 (Python exception, or the program returned 1)"
    return "exit code %d" % code


# --------------------------------------------------------------------------- #
# programs: compile + run
# --------------------------------------------------------------------------- #
CPP_EXT = (".cpp", ".cc", ".cxx", ".c++")


def find_compiler(is_c: bool) -> str:
    env_name = "CC" if is_c else "CXX"
    cands = [os.environ[env_name]] if os.environ.get(env_name) else []
    cands += ["gcc", "clang", "cc"] if is_c else ["g++", "clang++", "c++"]
    for c in cands:
        p = shutil.which(c)
        if p:
            return p
    raise SetupError(
        "No %s compiler found (tried %s). Install one - Windows: MSYS2 / MinGW-w64 "
        "(add its bin folder to PATH); macOS: `xcode-select --install`; Linux: "
        "`sudo apt install g++` - or set the %s environment variable."
        % ("C" if is_c else "C++", ", ".join(cands), env_name))


def compile_source(src: str, build_dir: str, role: str, flags_override) -> str:
    is_c = src.lower().endswith(".c")
    cc = find_compiler(is_c)
    if flags_override is not None:
        flags = shlex.split(flags_override)
    else:
        flags = ["-O2", "-std=c11" if is_c else "-std=c++17"]
    # Windows: big stack (deep DFS) + static runtime (no DLL hell). Linux/macOS:
    # the stack limit is raised for child processes in raise_stack_limit().
    link = ["-static", "-Wl,--stack=268435456"] if IS_WIN else []
    with open(src, "rb") as f:
        data = f.read()
    key = hashlib.sha1(data + repr((cc, flags, link)).encode()).hexdigest()[:10]
    stem = os.path.splitext(os.path.basename(src))[0]
    os.makedirs(build_dir, exist_ok=True)
    exe = os.path.join(build_dir, "%s_%s%s" % (stem, key, ".exe" if IS_WIN else ""))
    if os.path.isfile(exe):
        return exe
    say("compiling %s: %s %s" % (role, os.path.basename(cc), " ".join(flags)))
    attempts = [link, []] if link else [[]]
    last = None
    for extra in attempts:
        cmd = [cc] + flags + [src, "-o", exe] + extra
        last = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if last.returncode == 0 and os.path.isfile(exe):
            return exe
    raise SetupError("Compilation of %s (%s) failed:\n%s"
                     % (role, src, clip(last.stdout, max_lines=60, max_chars=6000)))


class RunResult:
    __slots__ = ("status", "out", "err", "code", "elapsed")

    def __init__(self, status, out, err, code, elapsed):
        self.status, self.out, self.err, self.code, self.elapsed = status, out, err, code, elapsed


class Program:
    def __init__(self, path, role, build_dir, cxxflags=None, python=None):
        self.role = role
        self.path = os.path.abspath(path)
        if not os.path.isfile(self.path):
            raise SetupError("%s: file not found: %s" % (role, path))
        ext = os.path.splitext(self.path)[1].lower()
        if ext == ".py":
            self.cmd = (shlex.split(python) if python else [sys.executable]) + [self.path]
        elif ext in CPP_EXT or ext == ".c":
            self.cmd = [compile_source(self.path, build_dir, role, cxxflags)]
        elif ext == ".exe" or (not IS_WIN and os.access(self.path, os.X_OK)):
            self.cmd = [self.path]
        else:
            raise SetupError("%s: unsupported file type '%s' (supported: .cpp .cc .cxx .c "
                             ".py or an executable)" % (role, ext or path))

    def run(self, args, stdin_data: bytes, timeout, env) -> RunResult:
        t0 = time.perf_counter()
        try:
            p = subprocess.run(self.cmd + list(args), input=stdin_data, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=timeout, env=env)
        except subprocess.TimeoutExpired as e:
            return RunResult("TLE", e.stdout or b"", e.stderr or b"", None, timeout)
        except OSError as e:
            return RunResult("RE", b"", str(e).encode(), None, 0.0)
        el = time.perf_counter() - t0
        return RunResult("OK" if p.returncode == 0 else "RE", p.stdout, p.stderr, p.returncode, el)


def raise_stack_limit():
    """Linux/macOS: let child programs use a big stack (deep recursion like on most OJs)."""
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        target = hard if hard != resource.RLIM_INFINITY else resource.RLIM_INFINITY
        if soft != target:
            try:
                resource.setrlimit(resource.RLIMIT_STACK, (target, hard))
            except (ValueError, OSError):
                resource.setrlimit(resource.RLIMIT_STACK, (min(hard, 1 << 29), hard))
    except Exception:
        pass


def child_env():
    env = os.environ.copy()
    env["PYTHONPATH"] = HERE + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["DUIPAI_LIB"] = HERE
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


# --------------------------------------------------------------------------- #
# output comparison
# --------------------------------------------------------------------------- #
TOKEN_RE = re.compile(rb"\S+")


def token_line(data: bytes, k: int) -> int:
    for i, m in enumerate(TOKEN_RE.finditer(data)):
        if i == k:
            return data.count(b"\n", 0, m.start()) + 1
    return data.count(b"\n") + 1


def show_tok(t: bytes, limit=60) -> str:
    s = text(t)
    return "'" + (s if len(s) <= limit else s[:limit] + "...") + "'"


def cmp_tokens(got: bytes, exp: bytes, eps=None):
    tg, te = got.split(), exp.split()
    for k in range(min(len(tg), len(te))):
        a, b = tg[k], te[k]
        if a == b:
            continue
        if eps is not None:
            try:
                x, y = float(a), float(b)
                if abs(x - y) <= eps * max(1.0, abs(y)):
                    continue
            except ValueError:
                pass
        return False, "token #%d (sol output line %d): expected %s, got %s" % (
            k + 1, token_line(got, k), show_tok(b), show_tok(a))
    if len(tg) != len(te):
        if len(tg) < len(te):
            return False, "sol printed too few tokens: %d instead of %d (next expected %s)" % (
                len(tg), len(te), show_tok(te[len(tg)]))
        return False, "sol printed too many tokens: %d instead of %d (first extra %s)" % (
            len(tg), len(te), show_tok(tg[len(te)]))
    return True, ""


def norm_lines(data: bytes):
    lines = [ln.rstrip() for ln in data.replace(b"\r\n", b"\n").split(b"\n")]
    while lines and lines[-1] == b"":
        lines.pop()
    return lines


def cmp_lines(got: bytes, exp: bytes):
    lg, le = norm_lines(got), norm_lines(exp)
    for k in range(min(len(lg), len(le))):
        if lg[k] != le[k]:
            return False, "line %d: expected %s, got %s" % (k + 1, show_tok(le[k], 120), show_tok(lg[k], 120))
    if len(lg) != len(le):
        return False, "sol printed %d lines, expected %d" % (len(lg), len(le))
    return True, ""


def cmp_exact(got: bytes, exp: bytes):
    g, e = got.replace(b"\r\n", b"\n"), exp.replace(b"\r\n", b"\n")
    if g == e:
        return True, ""
    k = next((i for i in range(min(len(g), len(e))) if g[i] != e[i]), min(len(g), len(e)))
    return False, "outputs differ at byte %d (line %d)" % (k, g.count(b"\n", 0, k) + 1)


def parse_cmp(spec: str):
    spec = (spec or "tokens").strip().lower()
    if spec == "tokens":
        return lambda g, e: cmp_tokens(g, e)
    if spec == "lines":
        return cmp_lines
    if spec == "exact":
        return cmp_exact
    if spec.startswith("float"):
        eps = 1e-6
        if ":" in spec:
            try:
                eps = float(spec.split(":", 1)[1])
            except ValueError:
                raise SetupError("bad --cmp value %r, use e.g. float:1e-6" % spec)
        return lambda g, e: cmp_tokens(g, e, eps)
    raise SetupError("unknown --cmp %r (use tokens | lines | exact | float:EPS)" % spec)


# --------------------------------------------------------------------------- #
# one test case
# --------------------------------------------------------------------------- #
class Case:
    def __init__(self, verdict, seed=None, scale=None, inp=b"", sol=None, exp=b"", detail="",
                 brute=None, gen=None):
        self.verdict, self.seed, self.scale, self.inp = verdict, seed, scale, inp
        self.sol, self.exp, self.detail, self.brute, self.gen = sol, exp, detail, brute, gen


class Ctx:
    def __init__(self, args, sol, brute, gen, checker, judge, env, workdir):
        self.args, self.sol, self.brute, self.gen, self.checker = args, sol, brute, gen, checker
        self.judge, self.env, self.workdir = judge, env, workdir


def check_with(ctx, inp: bytes, got: bytes, exp: bytes):
    """Returns (verdict, detail) with verdict in OK / WA / CHECKER_ERROR."""
    if ctx.checker is None:
        ok, detail = ctx.judge(got, exp)
        return ("OK" if ok else "WA"), detail
    tmp_root = os.path.join(ctx.workdir, "tmp")
    os.makedirs(tmp_root, exist_ok=True)
    d = tempfile.mkdtemp(prefix="case_", dir=tmp_root)
    try:
        paths = []
        for name, data in (("input.txt", inp), ("sol_out.txt", got), ("brute_out.txt", exp)):
            p = os.path.join(d, name)
            with open(p, "wb") as f:
                f.write(data)
            paths.append(p)
        r = ctx.checker.run(paths, b"", ctx.args.checker_timeout, ctx.env)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    msg = (text(r.out) + "\n" + text(r.err)).strip()
    if r.status == "TLE":
        return "CHECKER_ERROR", "checker timed out"
    if r.code == 0:
        return "OK", ""
    if r.code in (1, 2):
        return "WA", "checker: " + (msg.splitlines()[0][:300] if msg else "wrong answer")
    return "CHECKER_ERROR", "checker %s\n%s" % (describe_exit(r.code), msg[:2000])


def run_case(ctx, seed, scale) -> Case:
    a = ctx.args
    g = ctx.gen.run([str(seed), str(scale)], b"", a.gen_timeout, ctx.env)
    if g.status != "OK":
        why = "timed out" if g.status == "TLE" else describe_exit(g.code)
        return Case("GEN_ERROR", seed, scale, g.out, detail="generator %s\n%s" % (why, clip(g.err)), gen=g)
    inp = g.out.replace(b"\r\n", b"\n")  # Linux-style input, like real judges (getline-safe)
    if not inp.strip():
        return Case("GEN_ERROR", seed, scale, inp, detail="generator printed nothing", gen=g)
    s = ctx.sol.run([], inp, a.timeout, ctx.env)
    if s.status == "TLE":
        return Case("TLE", seed, scale, inp, s, detail="sol exceeded %.2fs" % a.timeout)
    if s.status == "RE":
        return Case("RE", seed, scale, inp, s, detail="sol crashed: " + describe_exit(s.code))
    if ctx.brute is None:
        return Case("OK", seed, scale, inp, s)
    b = ctx.brute.run([], inp, a.brute_timeout, ctx.env)
    if b.status != "OK":
        why = ("timed out after %.1fs (input too big for the brute force? lower --max-scale)"
               % a.brute_timeout) if b.status == "TLE" else describe_exit(b.code)
        return Case("BRUTE_ERROR", seed, scale, inp, s, b.out, "brute %s\n%s" % (why, clip(b.err)), brute=b)
    verdict, detail = check_with(ctx, inp, s.out, b.out)
    return Case(verdict, seed, scale, inp, s, b.out, detail, brute=b)


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
def gen_cmd_hint(ctx, seed, scale):
    try:
        p = os.path.relpath(ctx.gen.path)
    except ValueError:  # Windows: different drive
        p = ctx.gen.path
    pre = "python " if p.lower().endswith(".py") else ""
    return '%s"%s" %d %d' % (pre, p, seed, scale)


def save_case(ctx, c: Case, extra: dict) -> str:
    fail_dir = os.path.join(ctx.workdir, "fail")
    os.makedirs(fail_dir, exist_ok=True)
    files = {"input.txt": c.inp, "sol_out.txt": c.sol.out if c.sol else b"",
             "brute_out.txt": c.exp or b"", "sol_stderr.txt": c.sol.err if c.sol else b""}
    for name, data in files.items():
        with open(os.path.join(fail_dir, name), "wb") as f:
            f.write(data or b"")
    info = {"verdict": c.verdict, "seed": c.seed, "scale": c.scale, "detail": c.detail,
            "reproduce": gen_cmd_hint(ctx, c.seed, c.scale) if c.seed is not None else None,
            "sol": ctx.sol.path if ctx.sol else None,
            "brute": ctx.brute.path if ctx.brute else None,
            "gen": ctx.gen.path if ctx.gen else None,
            "input_bytes": len(c.inp)}
    if c.sol is not None:
        info["sol_exit"] = describe_exit(c.sol.code) if c.sol.status == "RE" else c.sol.status
        info["sol_time"] = round(c.sol.elapsed, 3)
    info.update(extra)
    with open(os.path.join(fail_dir, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    return fail_dir


def print_case(ctx, c: Case, fail_dir, title, extra_lines=()):
    bar = "=" * 64
    say(bar)
    say(title)
    say("verdict  : %s" % c.verdict)
    if c.seed is not None:
        say("seed     : %d   scale: %d" % (c.seed, c.scale))
        say("reproduce: %s" % gen_cmd_hint(ctx, c.seed, c.scale))
    for ln in extra_lines:
        say(ln)
    if c.detail:
        say("detail   : %s" % c.detail.strip())
    say("saved to : %s" % fail_dir)
    say("--- input (%d bytes) ---" % len(c.inp))
    say(clip(c.inp))
    if c.verdict in ("WA", "CHECKER_ERROR") or (c.exp and c.verdict != "BRUTE_ERROR"):
        say("--- expected (brute) ---")
        say(clip(c.exp))
    if c.sol is not None and c.verdict != "GEN_ERROR":
        say("--- got (sol) ---")
        say(clip(c.sol.out))
        if c.sol.err.strip():
            say("--- sol stderr ---")
            say(clip(c.sol.err, max_lines=15))
    if c.verdict == "BRUTE_ERROR" and c.brute is not None and c.brute.err.strip():
        say("--- brute stderr ---")
        say(clip(c.brute.err, max_lines=15))
    say(bar)


def emit_json(args, obj):
    if args.json:
        print(json.dumps(obj, ensure_ascii=False), flush=True)


# --------------------------------------------------------------------------- #
# stress loop + shrink
# --------------------------------------------------------------------------- #
def scale_for(args, base, k):
    if args.scale is not None:
        return args.scale
    if k < args.ramp * args.max_scale:
        return 1 + k // args.ramp
    return random.Random(base * 1000003 + k).randint(1, args.max_scale)


def shrink(ctx, pool, first: Case):
    a = ctx.args
    best, tries = first, 0
    if a.no_shrink:
        return best, tries
    rnd = random.Random(first.seed * 7919 + 17)
    deadline = time.time() + a.shrink_time
    batch = max(2, a.jobs * 2)
    while time.time() < deadline and tries < a.shrink_tries:
        if best.scale <= 1 and len(best.inp) <= 4:
            break
        cands = [(rnd.randrange(1, 2 ** 31 - 1), rnd.randint(1, best.scale)) for _ in range(batch)]
        for c in pool.map(lambda sc: run_case(ctx, sc[0], sc[1]), cands):
            tries += 1
            if c.verdict in FOUND_VERDICTS and (len(c.inp), c.scale) < (len(best.inp), best.scale):
                best = c
    return best, tries


def stress(ctx) -> int:
    a = ctx.args
    base = a.seed if a.seed is not None else random.SystemRandom().randrange(1, 10 ** 9)
    mode = "sol only (RE/TLE hunt)" if ctx.brute is None else (
        "checker " + os.path.basename(ctx.checker.path) if ctx.checker else "compare=" + a.cmp)
    scales = ("%d (fixed)" % a.scale) if a.scale is not None else "1..%d" % a.max_scale
    say("duipai %s | seed %d | scales %s | %s | jobs %d | up to %d cases / %ss"
        % (VERSION, base, scales, mode, a.jobs, a.n, a.time_limit))

    # generator sanity: must run and must be deterministic for a fixed seed
    s0 = scale_for(a, base, 0)
    g1 = ctx.gen.run([str(base), str(s0)], b"", a.gen_timeout, ctx.env)
    if g1.status != "OK" or not g1.out.strip():
        c = Case("GEN_ERROR", base, s0, g1.out,
                 detail="generator failed on its first run: %s\n%s" % (
                     "timed out" if g1.status == "TLE" else (describe_exit(g1.code) if g1.status == "RE"
                                                             else "printed nothing"), clip(g1.err)))
        d = save_case(ctx, c, {})
        print_case(ctx, c, d, "GENERATOR ERROR - fix gen before stress testing")
        emit_json(a, {"status": "GEN_ERROR", "seed": base, "detail": c.detail, "fail_dir": d})
        return EXIT_TOOL
    g2 = ctx.gen.run([str(base), str(s0)], b"", a.gen_timeout, ctx.env)
    if g2.out != g1.out:
        warn("generator output differs for the same seed - it must seed its RNG from argv[1] "
             "(genlib: scale = init()), otherwise counterexamples are not reproducible")

    t0 = time.time()
    done, last_print, slow = 0, t0, (0.0, None, None)
    batch = max(2, a.jobs * 2)
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        while done < a.n and time.time() - t0 < a.time_limit:
            ks = list(range(done, min(a.n, done + batch)))
            results = list(pool.map(lambda k: run_case(ctx, base + k, scale_for(a, base, k)), ks))
            for k, c in zip(ks, results):
                if c.verdict == "OK":
                    if c.sol is not None and c.sol.elapsed > slow[0]:
                        slow = (c.sol.elapsed, c.seed, c.scale)
                    continue
                if c.verdict in TOOL_VERDICTS:
                    d = save_case(ctx, c, {"case_index": k})
                    hint = {"GEN_ERROR": "fix the generator",
                            "BRUTE_ERROR": "the brute force failed - fix it or lower --max-scale; "
                                           "this is NOT a bug in sol",
                            "CHECKER_ERROR": "the checker crashed - fix the checker"}[c.verdict]
                    print_case(ctx, c, d, "%s on case #%d - %s" % (c.verdict, k + 1, hint))
                    emit_json(a, {"status": c.verdict, "case": k + 1, "seed": c.seed, "scale": c.scale,
                                  "detail": c.detail, "fail_dir": d})
                    return EXIT_TOOL
                # counterexample
                found_after = time.time() - t0
                orig_len = len(c.inp)
                best, tries = shrink(ctx, pool, c)
                extra = {"case_index": k, "found_after_sec": round(found_after, 2),
                         "original_input_bytes": orig_len, "shrink_tries": tries, "base_seed": base}
                d = save_case(ctx, best, extra)
                lines = ["found on : case #%d after %.1fs" % (k + 1, found_after)]
                if best is not c:
                    lines.append("shrunk   : %d -> %d bytes (%d extra runs)" % (orig_len, len(best.inp), tries))
                print_case(ctx, best, d, "COUNTEREXAMPLE FOUND", lines)
                emit_json(a, {"status": best.verdict, "case": k + 1, "seed": best.seed,
                              "scale": best.scale, "detail": best.detail, "fail_dir": d,
                              "input": text(best.inp) if len(best.inp) <= 4000 else None,
                              "expected": text(best.exp) if best.exp and len(best.exp) <= 4000 else None,
                              "got": text(best.sol.out) if best.sol and len(best.sol.out) <= 4000 else None})
                return EXIT_FOUND
            done = ks[-1] + 1
            if time.time() - last_print >= a.progress:
                last_print = time.time()
                say("  ... %d cases OK (%.1fs, scale %d)" % (done, last_print - t0, scale_for(a, base, done - 1)))
    el = time.time() - t0
    why = "" if done >= a.n else " (stopped by --time-limit)"
    say("PASS: %d cases, no counterexample%s. seed %d, scales %s, %.1fs" % (done, why, base, scales, el))
    if slow[1] is not None:
        say("slowest sol run: %.3fs (seed %d, scale %d)" % slow)
    emit_json(a, {"status": "PASS", "cases": done, "seed": base, "seconds": round(el, 2),
                  "slowest_sol_sec": round(slow[0], 3)})
    return EXIT_PASS


# --------------------------------------------------------------------------- #
# --input mode: run on fixed files (samples)
# --------------------------------------------------------------------------- #
def expand_inputs(items):
    files = []
    for it in items:
        if os.path.isdir(it):
            found = sorted(glob.glob(os.path.join(it, "*.in")))
            if not found:
                found = sorted(p for p in glob.glob(os.path.join(it, "*"))
                               if os.path.isfile(p) and not p.endswith((".out", ".ans")))
            files += found
        elif os.path.isfile(it):
            files.append(it)
        else:
            raise SetupError("--input: not found: %s" % it)
    if not files:
        raise SetupError("--input: no input files found")
    return files


def find_answer(path):
    stem = os.path.splitext(path)[0]
    for ext in (".out", ".ans", ".a"):
        if os.path.isfile(stem + ext) and stem + ext != path:
            return stem + ext
    return None


def input_mode(ctx) -> int:
    a = ctx.args
    progs = [p for p in (ctx.sol, ctx.brute) if p is not None]
    bad = 0
    for path in expand_inputs(a.input):
        with open(path, "rb") as f:
            inp = f.read().replace(b"\r\n", b"\n")
        ans_path = find_answer(path)
        ans = None
        if ans_path:
            with open(ans_path, "rb") as f:
                ans = f.read()
        outs = {}
        say("== %s%s" % (path, "  (answer: %s)" % os.path.basename(ans_path) if ans_path else ""))
        for p in progs:
            r = p.run([], inp, a.timeout if p is ctx.sol else a.brute_timeout, ctx.env)
            outs[p.role] = r
            if r.status != "OK":
                bad += 1
                say("  %-5s %s  %s" % (p.role, r.status, describe_exit(r.code) if r.status == "RE" else ""))
                if r.err.strip():
                    say("        " + clip(r.err, 8).replace("\n", "\n        "))
                continue
            if ans is not None:
                v, detail = check_with(ctx, inp, r.out, ans)
                if v != "OK":
                    bad += 1
                say("  %-5s %s (%.3fs)%s" % (p.role, v, r.elapsed, "  " + detail if detail else ""))
                if v != "OK":
                    say("        got     : " + clip(r.out, 6).replace("\n", "\n                  "))
                    say("        expected: " + clip(ans, 6).replace("\n", "\n                  "))
            else:
                say("  %-5s ran (%.3fs): %s" % (p.role, r.elapsed, clip(r.out, 6).replace("\n", " | ")))
        if ans is None and len(progs) == 2 and all(r.status == "OK" for r in outs.values()):
            v, detail = check_with(ctx, inp, outs["sol"].out, outs["brute"].out)
            if v != "OK":
                bad += 1
            say("  sol vs brute: %s%s" % (v, "  " + detail if detail else ""))
    say("RESULT: %s" % ("all OK" if bad == 0 else "%d problem(s)" % bad))
    emit_json(a, {"status": "PASS" if bad == 0 else "MISMATCH", "problems": bad})
    return EXIT_PASS if bad == 0 else EXIT_FOUND


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(
        prog="duipai.py",
        description="Stress tester (duipai): gen -> sol vs brute until they disagree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Exit codes:")[0].split("\n", 2)[2])
    p.add_argument("--sol", help="solution under test (.cpp/.c/.py/executable)")
    p.add_argument("--brute", help="trusted brute force (.cpp/.c/.py/executable)")
    p.add_argument("--gen", help="generator, called as: gen <seed> <scale>")
    p.add_argument("--checker", help="special judge: checker <input> <sol_out> <brute_out>; "
                                     "exit 0 = accept, 1/2 = wrong answer, other = checker failure")
    p.add_argument("--cmp", default="tokens", help="tokens (default) | lines | exact | float:EPS")
    p.add_argument("-n", type=int, default=2000, help="max number of cases (default 2000)")
    p.add_argument("--time-limit", type=float, default=60, help="total seconds for the loop (default 60)")
    p.add_argument("--timeout", type=float, default=2.0, help="per-run limit for sol in seconds (default 2)")
    p.add_argument("--brute-timeout", type=float, default=10.0, help="per-run limit for brute (default 10)")
    p.add_argument("--gen-timeout", type=float, default=10.0, help="per-run limit for gen (default 10)")
    p.add_argument("--checker-timeout", type=float, default=10.0)
    p.add_argument("--seed", type=int, help="base seed; case k uses seed+k (default: random)")
    p.add_argument("--max-scale", type=int, default=10, help="scales ramp 1..MAX (default 10)")
    p.add_argument("--scale", type=int, help="use this fixed scale for every case")
    p.add_argument("--ramp", type=int, default=20, help="cases per scale step during the ramp (default 20)")
    p.add_argument("--no-shrink", action="store_true", help="report the first failure as-is")
    p.add_argument("--shrink-time", type=float, default=5.0, help="seconds spent shrinking (default 5)")
    p.add_argument("--shrink-tries", type=int, default=1000)
    p.add_argument("--no-brute", action="store_true", help="run sol alone, only look for RE/TLE")
    p.add_argument("--input", nargs="+", help="run on these files/dirs instead of generating "
                                              "(x.in with optional x.out/x.ans answers)")
    p.add_argument("--jobs", "-j", type=int, default=max(1, min(8, (os.cpu_count() or 2) // 2)),
                   help="parallel cases (default: half the CPU cores, max 8)")
    p.add_argument("--workdir", help="where build/ and fail/ go (default: folder of --gen or --sol)")
    p.add_argument("--cxxflags", help="replace the default compiler flags (-O2 -std=c++17), "
                                      "e.g. \"-O2 -std=c++20 -fsanitize=address,undefined\"")
    p.add_argument("--python", help="interpreter for .py files (default: this Python), e.g. pypy3")
    p.add_argument("--progress", type=float, default=10.0, help="seconds between progress lines")
    p.add_argument("--json", action="store_true", help="print a JSON summary on stdout (human report -> stderr)")
    p.add_argument("--version", action="version", version="duipai " + VERSION)
    return p


def main(argv=None) -> int:
    global REPORT
    setup_console()
    args = build_parser().parse_args(argv)
    if args.json:
        REPORT = sys.stderr
    try:
        if args.input:
            if not (args.sol or args.brute):
                raise SetupError("--input needs --sol and/or --brute")
        else:
            if not args.sol or not args.gen:
                raise SetupError("stress mode needs --sol and --gen (and --brute unless --no-brute)")
            if not args.brute and not args.no_brute:
                raise SetupError("missing --brute (or pass --no-brute to only hunt RE/TLE)")
        if args.jobs < 1 or args.n < 1 or args.max_scale < 1 or args.ramp < 1:
            raise SetupError("-n, --jobs, --max-scale and --ramp must be >= 1")
        anchor = args.gen or args.sol or args.brute
        workdir = os.path.abspath(args.workdir or os.path.dirname(os.path.abspath(anchor)))
        build = os.path.join(workdir, "build")
        raise_stack_limit()
        env = child_env()
        mk = lambda path, role: Program(path, role, build, args.cxxflags, args.python) if path else None
        sol = mk(args.sol, "sol")
        brute = None if args.no_brute else mk(args.brute, "brute")
        gen = mk(args.gen, "gen")
        checker = mk(args.checker, "checker")
        judge = parse_cmp(args.cmp)
        ctx = Ctx(args, sol, brute, gen, checker, judge, env, workdir)
        if args.input:
            return input_mode(ctx)
        return stress(ctx)
    except SetupError as e:
        say("SETUP ERROR: %s" % e)
        emit_json(args, {"status": "SETUP_ERROR", "detail": str(e)})
        return EXIT_SETUP
    except KeyboardInterrupt:
        say("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
