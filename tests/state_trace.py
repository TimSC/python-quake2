# Report client state changes and the server message types parsed, for a local game.
import os, sys, collections
os.environ.setdefault("Q2PORT_NOMOUSE", "1")  # no mouse capture (tests)
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backends.unix import system
from client import cl_main, cl_parse
from common import movemsg
from server import sv_entities, sv_send
from client import cl_main
seen = {"state": None, "n": 0}
msgs = collections.Counter()
calls = collections.Counter()
orig_frame = cl_main.CL_Frame
def CL_Frame(*args):
	orig_frame(*args)
	seen["n"] += 1
	st = (cl_main.cls.state, cl_main.cls.key_dest, cl_main.cl.refresh_prepped, cl_main.cls.disable_screen)
	if st != seen["state"]:
		print("state_trace: frame %d state %s key_dest %s refresh_prepped %s disable_screen %s" % (seen["n"], st[0].name, st[1].name, st[2], st[3]))
		seen["state"] = st
	import time
	if "t0" not in seen: seen["t0"] = time.time(); seen["next"] = 10
	if time.time() - seen["t0"] > seen["next"]:
		seen["next"] += 10
		print("state_trace: %ds frame %d calls %s" % (seen["next"]-10, seen["n"], dict(calls)))
	if time.time() - seen["t0"] > 40:
		sys.stdout.flush(); os._exit(0)
cl_main.CL_Frame = CL_Frame
orig_rb = movemsg.MSG_ReadByte
for name in ("CL_ParseFrame",):
	o = getattr(cl_parse, name)
	def w(*a, _o=o, _n=name):
		calls[_n] += 1; return _o(*a)
	setattr(cl_parse, name, w)
for name in ("write_frame_to_client", "build_client_frame", "_send_client_datagram"):
	mod = sv_entities if hasattr(sv_entities, name) else sv_send
	o = getattr(mod, name)
	def w(*a, _o=o, _n=name):
		calls[_n] += 1; return _o(*a)
	setattr(mod, name, w)
system.main()
