# A broken brute force: crashes when n >= 3 (tests BRUTE_ERROR reporting).
import sys
data = list(map(int, sys.stdin.read().split()))
n, a = data[0], data[1:]
if n >= 3:
    raise RuntimeError("brute bug")
print(max(sum(a[l:r + 1]) for l in range(n) for r in range(l, n)))
