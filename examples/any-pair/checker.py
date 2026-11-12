# Special judge: any valid pair i < j is accepted.
# Called as: python checker.py <input> <sol_out> <brute_out>
# Exit 0 = accepted, 1 = wrong answer (print the reason), 3 = checker bug.
# Rule: check that sol's answer is VALID for the input and AS GOOD AS brute's answer.
import sys


def wa(msg):
    print(msg)
    sys.exit(1)


def main():
    inp = open(sys.argv[1], encoding="utf-8").read().split()
    sol = open(sys.argv[2], encoding="utf-8").read().split()
    ref = open(sys.argv[3], encoding="utf-8").read().split()

    # ---- edit: parse the input ----
    it = iter(inp)
    n, target = int(next(it)), int(next(it))
    a = [int(next(it)) for _ in range(n)]

    # ---- edit: example "print indices i < j with a_i + a_j = target, or -1" ----
    if ref == ["-1"]:
        if sol != ["-1"]:
            wa("no pair exists but sol printed %s" % " ".join(sol[:5]))
        return
    try:
        i, j = map(int, sol)
    except ValueError:
        wa("expected two integers, got %r" % " ".join(sol[:5]))
    if not (1 <= i < j <= n):
        wa("indices out of range or not i < j: %d %d" % (i, j))
    if a[i - 1] + a[j - 1] != target:
        wa("a[%d] + a[%d] = %d != %d" % (i, j, a[i - 1] + a[j - 1], target))


try:
    main()
except SystemExit:
    raise
except Exception as e:          # bad sol output is WA; anything else is a checker bug
    print("checker crashed: %r" % e)
    sys.exit(3)
sys.exit(0)
