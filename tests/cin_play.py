# Play a cinematic in the real client and report decoded frames and decode time.
import os, sys, time
os.environ.setdefault("Q2PORT_NOMOUSE", "1")  # no mouse capture (tests)
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backends.unix import system
from client import cl_cin
st = {"n": 0, "t": 0.0, "t0": time.time(), "none": 0}
o = cl_cin.Huff1Decompress
def H(d, n):
	t = time.perf_counter(); r = o(d, n); st["t"] += time.perf_counter() - t; st["n"] += 1
	if st["n"] % 20 == 0: print("cin: %d frames decoded, avg %.1f ms, %d bytes/frame" % (st["n"], st["t"] / st["n"] * 1000, len(r)))
	return r
cl_cin.Huff1Decompress = H
o2 = cl_cin.SCR_FinishCinematic
def F():
	print("cin: finished after %d frames in %.1f s" % (st["n"], time.time() - st["t0"])); return o2()
cl_cin.SCR_FinishCinematic = F
system.main()
