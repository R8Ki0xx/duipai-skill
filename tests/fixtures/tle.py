# Correct max-subarray answer, but loops forever when n >= 4 (tests TLE detection).
import sys
data = list(map(int, sys.stdin.read().split()))
n, a = data[0], data[1:]
while n >= 4:
    pass
print(max(sum(a[l:r + 1]) for l in range(n) for r in range(l, n)))
