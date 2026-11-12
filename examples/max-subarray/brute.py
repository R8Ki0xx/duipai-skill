# Brute force: try every non-empty subarray. O(n^3), fine for n <= 10.
import sys

data = list(map(int, sys.stdin.read().split()))
n, a = data[0], data[1:1 + data[0]]
print(max(sum(a[l:r + 1]) for l in range(n) for r in range(l, n)))
