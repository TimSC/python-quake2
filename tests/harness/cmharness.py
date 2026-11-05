# Python counterpart of cmharness.c: same stdin format and output, using qcommon/cmodel.py.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
pass
from common import filesystem
from common import collision
def FS_LoadFile(path):
	d = open(os.environ["BSP"], "rb").read()
	return len(d), d
filesystem.FS_LoadFile = FS_LoadFile
cm, checksum = collision.CM_LoadMap("maps/x.bsp", False)
print("checksum %u numinline %d" % (checksum & 0xffffffff, collision.CM_NumInlineModels()))
for line in sys.stdin:
	v = line.split()
	if len(v) != 20: continue
	model = int(v[0]); f = [np.array([float(x) for x in v[i:i+3]], dtype=np.float32) for i in range(1, 19, 3)]
	o, a, s, e, mn, mx = f; mask = int(v[19])
	headnode = collision.CM_InlineModel("*%d" % model).headnode if model else 0
	t = collision.CM_TransformedBoxTrace(s, e, mn, mx, headnode, mask, o, a)
	print("frac %.4f end %.2f %.2f %.2f startsolid %d allsolid %d normal %.4f %.4f %.4f contents %d" % (t.fraction, t.endpos[0], t.endpos[1], t.endpos[2], t.startsolid, t.allsolid, t.plane.normal[0], t.plane.normal[1], t.plane.normal[2], t.contents))
