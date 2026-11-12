# Random test generator for duipai.  Usage: python gen.py <seed> <scale>
# Same (seed, scale) -> same test. scale = size budget (max n), 1..10 by default.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # genlib.py copied next to this file
sys.path.insert(0, os.environ.get("DUIPAI_LIB", ""))              # or provided by duipai.py
from genlib import *

scale = init()

# ---- edit below: follow the input format and EVERY constraint of the statement ----
T = rint(1, 3)                      # multi-test? print T >= 2 often to catch "forgot to reset" bugs
out(T)
for _ in range(T):
    n = rint(1, scale)
    a = rarr(n, -5, 5)              # small value range => duplicates, ties, zeros, negatives
    out(n)
    out(a)
