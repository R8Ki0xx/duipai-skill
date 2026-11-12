# python gen.py <seed> <scale>
import os, sys
sys.path.insert(0, os.environ.get("DUIPAI_LIB", ""))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "skills", "duipai", "scripts"))
from genlib import *

scale = init()
n = rint(1, scale)
out(n, rint(2, 10))
out(rarr(n, 1, 5))
