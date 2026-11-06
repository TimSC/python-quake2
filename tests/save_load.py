# Save a game on base1, load it back, and check the level comes back with the player in it,
# the same entities, and the player's health and position.
# Writes the save to the port's own home directory (save/porttest), never to the game data.
import os, sys, time
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from linux import sys_linux
from client import cl_main
from common import cmdparser
from server import sv_init
from game import g_main

st = {"phase": 0, "t": None, "n": 0}

def snapshot():
	ents = sorted((i, e.classname, e.inuse) for i, e in enumerate(g_main.g_edicts[:g_main.glob.num_edicts]) if e.inuse)
	player = g_main.g_edicts[1]
	return {"ents": ents, "health": player.health, "origin": [round(float(x)) for x in player.s.origin],
		"monsters": (g_main.level.total_monsters, g_main.level.killed_monsters)}

orig_frame = cl_main.CL_Frame
def CL_Frame(msec):
	orig_frame(msec)
	st["n"] += 1
	active = cl_main.cls.state.name == "ca_active"
	now = time.time()
	if st["phase"] == 0 and active:
		st["phase"] = 1; st["t"] = now
	elif st["phase"] == 1 and now - st["t"] > 3:
		g_main.g_edicts[1].health = 57	# something the load must bring back
		# take the snapshot as the level is written, so nothing changes in between
		from game.savegame import savegame
		orig_write = savegame.WriteLevel
		def WriteLevel(filename):
			st["before"] = snapshot()
			orig_write(filename)
		orig_read = savegame.ReadLevel
		def ReadLevel(filename):
			orig_read(filename)
			st["loaded"] = snapshot()	# the entities, before the game runs on
		# (GetGameAPI picks these up from the module when the game restarts)
		savegame.WriteLevel = WriteLevel
		savegame.ReadLevel = ReadLevel
		from server import sv_game
		sv_game.ge.WriteLevel = WriteLevel
		print("save_load: saving")
		cmdparser.Cbuf_AddText("save porttest\n")
		st["phase"] = 2; st["t"] = now
	elif st["phase"] == 2 and now - st["t"] > 2:
		print("save_load: loading")
		g_main.g_edicts[1].health = 100
		cmdparser.Cbuf_AddText("load porttest\n")
		st["phase"] = 3; st["t"] = now
	elif st["phase"] == 3 and active and "loaded" in st:
		print("save_load: back in game on %s, server state %s, loadgame %s" % (sv_init.sv.name, sv_init.sv.state.name, sv_init.sv.loadgame))
		after, before = snapshot(), st["before"]
		ok = True
		if after["health"] != before["health"]:
			print("save_load: health %s, saved %s" % (after["health"], before["health"])); ok = False
		if max(abs(a - b) for a, b in zip(after["origin"], before["origin"])) > 2:
			print("save_load: player at %s, saved at %s" % (after["origin"], before["origin"])); ok = False
		if after["monsters"] != before["monsters"]:
			print("save_load: monsters %s, saved %s" % (after["monsters"], before["monsters"])); ok = False
		lost = set(before["ents"]) - set(st["loaded"]["ents"])
		if lost:
			print("save_load: %d entities not restored, e.g. %s" % (len(lost), sorted(lost)[:5])); ok = False
		print("save_load: level contents %s" % ("restored" if ok else "NOT restored"))
		sys.stdout.flush(); os._exit(0 if ok else 1)
	if st["t"] is not None and now - st["t"] > 60:
		print("save_load: timed out in phase %d" % st["phase"])
		sys.stdout.flush(); os._exit(1)
cl_main.CL_Frame = CL_Frame
sys_linux.main()
