# Python counterpart of pmharness.c: same stdin format and output, using qcommon/pmove.py and cmodel.py.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
pass
from common.header import shared
from common.shared import shared as shared_c
from common import filesystem
from common import collision
from common.header import shared as shared_h
from common import pmove

def FS_LoadFile(path):
	d = open(os.environ["BSP"], "rb").read()
	return len(d), d
filesystem.FS_LoadFile = FS_LoadFile
collision.CM_LoadMap("maps/x.bsp", False)

WORLD, MODEL = object(), object()
models = []
origin0 = np.zeros((3,), dtype=np.float32)

def H_Trace(start, mins, maxs, end):
	tr = collision.CM_BoxTrace(start, end, mins, maxs, 0, shared.MASK_PLAYERSOLID)
	tr.ent = WORLD
	if tr.fraction == 0:
		return tr
	for m in models:
		if tr.allsolid:
			return tr
		t = collision.CM_TransformedBoxTrace(start, end, mins, maxs, collision.CM_InlineModel("*%d" % m).headnode, shared.MASK_PLAYERSOLID, origin0, shared_c.vec3_origin)
		if t.allsolid or t.startsolid or t.fraction < tr.fraction:
			t.ent = MODEL
			if tr.startsolid:
				tr = t; tr.startsolid = True
			else:
				tr = t
		elif t.startsolid:
			tr.startsolid = True
	return tr

def H_PointContents(p):
	return collision.CM_PointContents(p, 0)

toks = sys.stdin.read().split()
while toks:
	v = [int(x) for x in toks[:24]]; toks = toks[24:]
	nm = v[23]; models[:] = [int(x) for x in toks[:nm]]; toks = toks[nm:]
	pm = shared_h.pmove_t()
	pm.s.pm_type = v[0]
	for i in range(3):
		pm.s.origin[i] = v[1+i]; pm.s.velocity[i] = v[4+i]; pm.s.delta_angles[i] = v[10+i]
	pm.s.pm_flags = v[7]; pm.s.pm_time = v[8]; pm.s.gravity = v[9]
	for f in range(v[22]):
		c = shared.usercmd_t()
		c.msec = v[13]; c.buttons = v[14]; c.angles = [v[15], v[16], v[17]]
		c.forwardmove = v[18]; c.sidemove = v[19]; c.upmove = v[20]
		pm.cmd = c
		pm.snapinitial = bool(v[21]) if f == 0 else False
		pm.trace = H_Trace; pm.pointcontents = H_PointContents
		pmove.Pmove(pm)
		g = "None" if pm.groundentity is None else ("world" if pm.groundentity is WORLD else "model")
		print("f %d origin %d %d %d velocity %d %d %d flags %d time %d ground %s" % (f, pm.s.origin[0], pm.s.origin[1], pm.s.origin[2],
			pm.s.velocity[0], pm.s.velocity[1], pm.s.velocity[2], pm.s.pm_flags, pm.s.pm_time, g))
