// Correct max-subarray answer, but crashes whenever n is even (tests RE detection).
#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; scanf("%d", &n);
    vector<long long> a(n);
    for (auto& x : a) scanf("%lld", &x);
    if (n % 2 == 0) abort();
    long long cur = 0, ans = LLONG_MIN;
    for (int i = 0; i < n; i++) { cur = i ? max(a[i], cur + a[i]) : a[i]; ans = max(ans, cur); }
    printf("%lld\n", ans);
}
