# Fixed: look up first, then insert.
import sys


def main():
    data = list(map(int, sys.stdin.read().split()))
    n, t, a = data[0], data[1], data[2:]
    seen = {}
    for j, x in enumerate(a, 1):
        if t - x in seen:
            print(seen[t - x], j)
            return
        seen.setdefault(x, j)
    print(-1)


main()
