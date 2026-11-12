// T test cases; each: n, then n values in [1, 100]. Print the number of distinct values.
// BUG: `seen` is global and never cleared between test cases.
#include <bits/stdc++.h>
using namespace std;
bool seen[105];
int main() {
    int T;
    scanf("%d", &T);
    while (T--) {
        int n, cnt = 0;
        scanf("%d", &n);
        for (int i = 0; i < n; i++) {
            int x;
            scanf("%d", &x);
            if (!seen[x]) { seen[x] = true; cnt++; }
        }
        printf("%d\n", cnt);
    }
}
