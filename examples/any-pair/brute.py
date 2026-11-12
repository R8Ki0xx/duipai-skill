# Brute force: first pair (i, j), i < j, in lexicographic order. O(n^2).
import sys

data = list(map(int, sys.stdin.read().split()))
n, t, a = data[0], data[1], data[2:]
for i in range(n):
    for j in range(i + 1, n):
        if a[i] + a[j] == t:
            print(i + 1, j + 1)
            sys.exit(0)
print(-1)
