# Reproduce the fall-through bug: teleport the player beside base1's func_wall *9 ledge
# and drive scripted movement into it on the server, logging position and overlap.
# usage: walk_test.py <start x y z> <yaw> <forwardmove> <seconds> <game args...>
import os, sys, time
sx, sy, sz, yaw, fwd, secs = [float(v) for v in sys.argv[1:7]]
sys.argv = ["main.py"] + sys.argv[7:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from linux import sys_linux
from client import cl_main
pass
from game import g_main
from common.header.shared import ANGLE2SHORT
from common.shared.shared import TO_SHORT
from common.header import shared
from server import sv_world
from game.player import client as p_client
from client import cl_main

st = {"phase": 0, "t0": None, "n": 0, "last": None}
o_think = p_client.ClientThink
def ClientThink(ent, ucmd):
	if cl_main.cls.state.name == "ca_active":
		if st["phase"] == 0:
			# teleport
			for i in range(3):
				ent.s.origin[i] = (sx, sy, sz)[i]
				ent.velocity[i] = 0
				ent.client.ps.pmove.origin[i] = int((sx, sy, sz)[i]*8)
				ent.client.ps.pmove.velocity[i] = 0
			g_main.gi.linkentity(ent)
			st["phase"] = 1; st["t0"] = time.time()
		ucmd.forwardmove = int(fwd); ucmd.sidemove = 0; ucmd.upmove = 0
		ucmd.angles[0] = TO_SHORT(-int(ent.client.ps.pmove.delta_angles[0]))
		ucmd.angles[1] = TO_SHORT(ANGLE2SHORT(yaw) - int(ent.client.ps.pmove.delta_angles[1]))
		ucmd.angles[2] = 0
	o_think(ent, ucmd)
	if st["phase"] == 1:
		st["n"] += 1
		mins = ent.mins; maxs = ent.maxs
		tr = sv_world.SV_Trace(ent.s.origin, mins, maxs, ent.s.origin, ent, shared.MASK_PLAYERSOLID)
		ge = ent.groundentity
		row = ([round(float(x), 1) for x in ent.s.origin], ge.classname if ge else None, bool(tr.startsolid), tr.ent.classname if tr.startsolid and tr.ent else "")
		if row != st["last"] or st["n"] % 20 == 0:
			print("walk: %.2f n %d org %s vel %s ground %s insolid %s %s" % (time.time()-st["t0"], st["n"], row[0], [round(float(x),1) for x in ent.velocity], row[1], row[2], row[3]))
			st["last"] = row
		if time.time() - st["t0"] > secs or ent.s.origin[2] < -500:
			ok = not row[2] and ent.s.origin[2] > sz - 64
			print("walk: %s (end z %.1f, start z %.1f, in solid %s)" % ("passed" if ok else "FELL", ent.s.origin[2], sz, row[2]))
			sys.stdout.flush(); os._exit(0)
p_client.ClientThink = ClientThink

sys_linux.main()
