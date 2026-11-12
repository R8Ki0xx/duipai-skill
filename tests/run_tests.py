#!/usr/bin/env python3
"""End-to-end tests for skills/duipai/scripts/duipai.py.  Run:  python tests/run_tests.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "skills", "duipai", "scripts", "duipai.py")
EX = os.path.join(ROOT, "examples")
FX = os.path.join(ROOT, "tests", "fixtures")
WORK = tempfile.mkdtemp(prefix="duipai_test_")

results = []


def run(*args, expect_code):
    cmd = [sys.executable, RUNNER, "--json", "--workdir", WORK, "--progress", "1000"] + list(args)
    t0 = time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    out = p.stdout.decode("utf-8", "replace").strip().splitlines()
    data = json.loads(out[-1]) if out else {}
    ok = p.returncode == expect_code
    return ok, p.returncode, data, p.stderr.decode("utf-8", "replace"), time.time() - t0


def case(name, *args, expect_code, check=None):
    ok, code, data, err, el = run(*args, expect_code=expect_code)
    why = ""
    if ok and check:
        try:
            check(data)
        except AssertionError as e:
            ok, why = False, str(e) or "check failed"
    elif not ok:
        why = "exit %d, expected %d" % (code, expect_code)
    results.append(ok)
    print("[%s] %-42s %5.1fs  %s" % ("PASS" if ok else "FAIL", name, el, why), flush=True)
    if not ok:
        print("      json:", json.dumps(data, ensure_ascii=False)[:500])
        print("      stderr tail:\n        " + "\n        ".join(err.strip().splitlines()[-25:]))
    return data


def ex(*parts):
    return os.path.join(EX, *parts)


def fx(name):
    return os.path.join(FX, name)


def read_fail(name):
    with open(os.path.join(WORK, "fail", name), "rb") as f:
        return f.read()


def check_wa_small(max_bytes):
    def chk(d):
        assert d["status"] == "WA", "status %s" % d.get("status")
        inp = read_fail("input.txt")
        assert len(inp) <= max_bytes, "counterexample not shrunk: %d bytes" % len(inp)
        assert read_fail("sol_out.txt").split() != read_fail("brute_out.txt").split(), "outputs equal"
    return chk


def status_is(s):
    def chk(d):
        assert d.get("status") == s, "status %s, expected %s" % (d.get("status"), s)
    return chk


def main():
    ms, mt, ap = "max-subarray", "multitest-reset", "any-pair"
    common = ["-n", "1500", "--time-limit", "90"]

    case("max-subarray: finds WA, shrinks", "--sol", ex(ms, "sol.cpp"), "--brute", ex(ms, "brute.py"),
         "--gen", ex(ms, "gen.py"), *common, expect_code=1, check=check_wa_small(8))
    case("max-subarray: fixed passes", "--sol", ex(ms, "sol_fixed.cpp"), "--brute", ex(ms, "brute.py"),
         "--gen", ex(ms, "gen.py"), "-n", "400", expect_code=0, check=status_is("PASS"))
    case("max-subarray: samples catch buggy sol", "--sol", ex(ms, "sol.cpp"), "--brute", ex(ms, "brute.py"),
         "--input", ex(ms, "samples"), expect_code=1)
    case("max-subarray: samples pass fixed + brute", "--sol", ex(ms, "sol_fixed.cpp"), "--brute",
         ex(ms, "brute.py"), "--input", ex(ms, "samples"), expect_code=0)

    case("multitest-reset: finds WA", "--sol", ex(mt, "sol.cpp"), "--brute", ex(mt, "brute.py"),
         "--gen", ex(mt, "gen.py"), *common, expect_code=1, check=check_wa_small(20))
    case("multitest-reset: fixed passes", "--sol", ex(mt, "sol_fixed.cpp"), "--brute", ex(mt, "brute.py"),
         "--gen", ex(mt, "gen.py"), "-n", "400", expect_code=0)

    chk = ex(ap, "checker.py")
    case("any-pair: checker finds WA", "--sol", ex(ap, "sol.py"), "--brute", ex(ap, "brute.py"),
         "--gen", ex(ap, "gen.py"), "--checker", chk, *common, expect_code=1, check=status_is("WA"))
    case("any-pair: fixed passes with checker", "--sol", ex(ap, "sol_fixed.py"), "--brute", ex(ap, "brute.py"),
         "--gen", ex(ap, "gen.py"), "--checker", chk, "-n", "300", expect_code=0)
    case("any-pair: fixed differs w/o checker", "--sol", ex(ap, "sol_fixed.py"), "--brute", ex(ap, "brute.py"),
         "--gen", ex(ap, "gen.py"), *common, expect_code=1, check=status_is("WA"))

    case("RE detected", "--sol", fx("re.cpp"), "--brute", ex(ms, "brute.py"), "--gen", ex(ms, "gen.py"),
         *common, expect_code=1, check=status_is("RE"))
    case("TLE detected", "--sol", fx("tle.py"), "--brute", ex(ms, "brute.py"), "--gen", ex(ms, "gen.py"),
         "--timeout", "1", "--shrink-time", "2", *common, expect_code=1, check=status_is("TLE"))
    case("broken brute -> BRUTE_ERROR", "--sol", ex(ms, "sol_fixed.cpp"), "--brute", fx("bad_brute.py"),
         "--gen", ex(ms, "gen.py"), *common, expect_code=3, check=status_is("BRUTE_ERROR"))
    case("--no-brute big run passes", "--sol", ex(ms, "sol_fixed.cpp"), "--gen", ex(ms, "gen.py"),
         "--no-brute", "--scale", "50000", "-n", "8", expect_code=0)
    case("compile error -> exit 2", "--sol", fx("compile_error.cpp"), "--brute", ex(ms, "brute.py"),
         "--gen", ex(ms, "gen.py"), expect_code=2, check=status_is("SETUP_ERROR"))
    case("missing file -> exit 2", "--sol", fx("nope.cpp"), "--brute", ex(ms, "brute.py"),
         "--gen", ex(ms, "gen.py"), expect_code=2)
    case("non-ASCII output does not crash", "--sol", fx("unicode_out.py"), "--brute", ex(ms, "brute.py"),
         "--gen", ex(ms, "gen.py"), "-n", "50", expect_code=1, check=status_is("WA"))

    # reproducibility: same --seed -> same counterexample
    a = run("--sol", ex(ms, "sol.cpp"), "--brute", ex(ms, "brute.py"), "--gen", ex(ms, "gen.py"),
            "--seed", "12345", "-j", "2", expect_code=1)[2]
    b = run("--sol", ex(ms, "sol.cpp"), "--brute", ex(ms, "brute.py"), "--gen", ex(ms, "gen.py"),
            "--seed", "12345", "-j", "2", expect_code=1)[2]
    same = (a.get("seed"), a.get("input")) == (b.get("seed"), b.get("input")) and a.get("seed") is not None
    results.append(same)
    print("[%s] %-42s" % ("PASS" if same else "FAIL", "same --seed reproduces the same case"))

    shutil.rmtree(WORK, ignore_errors=True)
    print("\n%d/%d passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
