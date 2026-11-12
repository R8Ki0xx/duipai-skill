# Input: n target, then a_1..a_n. Print any i < j with a_i + a_j = target, or -1.
# BUG: the value is inserted into `seen` BEFORE the lookup, so a_i = target/2
#      pairs with itself and prints "i i".
import sys


def main():
    data = list(map(int, sys.stdin.read().split()))
    n, t, a = data[0], data[1], data[2:]
    seen = {}
    for j, x in enumerate(a, 1):
        seen.setdefault(x, j)
        if t - x in seen:
            print(seen[t - x], j)
            return
    print(-1)


main()
