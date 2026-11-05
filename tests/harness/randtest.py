# Python twin of randtest.c: common/shared/rand.py must give the same numbers.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from common.shared import rand
rand.randk_seed()
for i in range(2000): print(rand.randk())
for i in range(20):
	a = rand.frandk(); b = rand.crandk()
	print("%.6f %.6f" % (a, b))
rand.randk_seed(); print(rand.randk())
