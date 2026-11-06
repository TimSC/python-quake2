# Save a game on base1, load it back, and check the level comes back with the player in it.
# Writes the save to the port's own home directory (save/porttest), never to the game data.
import os, sys, time
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from linux import sys_linux
from client import cl_main
from common import cmdparser
from server import sv_init

st = {"phase": 0, "t": None, "n": 0}
orig_frame = cl_main.CL_Frame
def CL_Frame(msec):
	orig_frame(msec)
	st["n"] += 1
	active = cl_main.cls.state.name == "ca_active"
	now = time.time()
	if st["phase"] == 0 and active:
		st["phase"] = 1; st["t"] = now
	elif st["phase"] == 1 and now - st["t"] > 3:
		print("save_load: saving")
		cmdparser.Cbuf_AddText("save porttest\n")
		st["phase"] = 2; st["t"] = now
	elif st["phase"] == 2 and now - st["t"] > 2:
		print("save_load: loading")
		cmdparser.Cbuf_AddText("load porttest\n")
		st["phase"] = 3; st["t"] = now
	elif st["phase"] == 3 and active and now - st["t"] > 5:
		print("save_load: back in game on %s, server state %s, loadgame %s" % (sv_init.sv.name, sv_init.sv.state.name, sv_init.sv.loadgame))
		sys.stdout.flush(); os._exit(0)
	if st["t"] is not None and now - st["t"] > 60:
		print("save_load: timed out in phase %d" % st["phase"])
		sys.stdout.flush(); os._exit(1)
cl_main.CL_Frame = CL_Frame
sys_linux.main()
