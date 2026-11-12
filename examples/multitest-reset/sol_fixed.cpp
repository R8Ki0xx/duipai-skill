// Fixed: clear `seen` for every test case (only the values used, to stay O(n)).
#include <bits/stdc++.h>
using namespace std;
bool seen[105];
int main() {
    int T;
    scanf("%d", &T);
    while (T--) {
        int n, cnt = 0;
        scanf("%d", &n);
        vector<int> a(n);
        for (int i = 0; i < n; i++) {
            scanf("%d", &a[i]);
            if (!seen[a[i]]) { seen[a[i]] = true; cnt++; }
        }
        for (int x : a) seen[x] = false;
        printf("%d\n", cnt);
    }
}
