# Run a dedicated server on base1 for a few seconds of server frames and report.
import os, sys, time
os.environ.setdefault("Q2PORT_NOMOUSE", "1")  # no mouse capture (tests)
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backends.unix import system
from server import sv_main, sv_init
st = {"n": 0, "t0": None}
o = sv_main.SV_Frame
def SV_Frame(usec):
	o(usec)
	st["n"] += 1
	if st["t0"] is None: st["t0"] = time.time()
	if time.time() - st["t0"] > 8:
		print("dedicated: %d calls, server framenum %d, state %s, map %s" % (st["n"], sv_init.sv.framenum, sv_init.sv.state.name, sv_init.sv.name))
		sys.stdout.flush(); os._exit(0)
sv_main.SV_Frame = SV_Frame
system.main()
