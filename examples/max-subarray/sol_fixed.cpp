// Max subarray sum (non-empty) - fixed Kadane.
#include <bits/stdc++.h>
using namespace std;
int main() {
    int n;
    scanf("%d", &n);
    long long cur = 0, ans = LLONG_MIN;
    for (int i = 0; i < n; i++) {
        long long x;
        scanf("%lld", &x);
        cur = (i == 0) ? x : max(x, cur + x);
        ans = max(ans, cur);
    }
    printf("%lld\n", ans);
}
