# Brute force: len(set(...)) per test case.
import sys

it = iter(map(int, sys.stdin.read().split()))
res = []
for _ in range(next(it)):
    n = next(it)
    res.append(len({next(it) for _ in range(n)}))
print("\n".join(map(str, res)))
