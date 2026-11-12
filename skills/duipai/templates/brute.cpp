// Brute force for duipai (C++ version - use only when brute.py is too slow).
// Simplest obviously-correct approach, independent of sol. Complexity: O(...)
#include <bits/stdc++.h>
using namespace std;
using ll = long long;   // use long long everywhere in a brute force

ll solve(int n, const vector<ll>& a) {
    // ---- edit: enumerate everything the statement allows, check it directly ----
    ll best = LLONG_MIN;
    for (int l = 0; l < n; l++)
        for (int r = l; r < n; r++) {
            ll s = 0;
            for (int i = l; i <= r; i++) s += a[i];
            best = max(best, s);
        }
    return best;
}

int main() {
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n; cin >> n;
        vector<ll> a(n);
        for (auto& x : a) cin >> x;
        cout << solve(n, a) << '\n';
    }
}
