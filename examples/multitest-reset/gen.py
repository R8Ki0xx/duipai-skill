# python gen.py <seed> <scale>
import os, sys
sys.path.insert(0, os.environ.get("DUIPAI_LIB", ""))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "skills", "duipai", "scripts"))
from genlib import *

scale = init()
T = rint(1, 3)
out(T)
for _ in range(T):
    n = rint(1, scale)
    out(n)
    out(rarr(n, 1, 5))
