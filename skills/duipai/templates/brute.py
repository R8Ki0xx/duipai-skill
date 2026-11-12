# Brute force for duipai: simplest obviously-correct approach, independent of sol.
# Complexity: O(...) - fine for scale <= 10.
import sys
from itertools import combinations, permutations, product


def solve(n, a):
    # ---- edit: enumerate everything the statement allows, check it directly ----
    best = None
    for l in range(n):
        for r in range(l, n):
            s = sum(a[l:r + 1])
            if best is None or s > best:
                best = s
    return best


def main():
    data = sys.stdin.read().split()
    it = iter(data)
    T = int(next(it))
    res = []
    for _ in range(T):
        n = int(next(it))
        a = [int(next(it)) for _ in range(n)]
        res.append(str(solve(n, a)))
    print("\n".join(res))


main()
