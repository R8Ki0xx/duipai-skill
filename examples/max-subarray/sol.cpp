// Max subarray sum (non-empty). n <= 2e5, |a_i| <= 1e9.
// BUG: ans and cur start at 0, so an all-negative array prints 0.
#include <bits/stdc++.h>
using namespace std;
int main() {
    int n;
    scanf("%d", &n);
    long long cur = 0, ans = 0;
    for (int i = 0; i < n; i++) {
        long long x;
        scanf("%lld", &x);
        cur = max(0LL, cur + x);
        ans = max(ans, cur);
    }
    printf("%lld\n", ans);
}
