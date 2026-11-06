# Spawn every newly ported monster near the player on a live map and drive all of its code paths.
import os, sys, time, traceback
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from linux import sys_linux
from client import cl_main
from game import g_main, g_utils, g_spawn, g_ai
from game.header import local
from game.monster.brain import brain as m_brain
from game.monster.chick import chick as m_chick
from game.monster.flipper import flipper as m_flipper
from game.monster.float import float as m_float
from game.monster.gladiator import gladiator as m_gladiator
from game.monster.hover import hover as m_hover
from game.monster.insane import insane as m_insane
from game.monster.medic import medic as m_medic
from game.monster.mutant import mutant as m_mutant
from game.monster.parasite import parasite as m_parasite
from game.monster.supertank import supertank as m_supertank
from game.monster.tank import tank as m_tank

SPAWNS = [("monster_brain", 0), ("monster_chick", 0), ("monster_flipper", 0), ("monster_floater", 0), ("monster_gladiator", 0),
	("monster_hover", 0), ("misc_insane", 0), ("misc_insane", 4), ("misc_insane", 8), ("misc_insane", 16), ("monster_medic", 0),
	("monster_mutant", 0), ("monster_parasite", 0), ("monster_supertank", 0), ("monster_tank", 0), ("monster_tank_commander", 0)]
if os.environ.get("MON_ONLY"): SPAWNS = [x for x in SPAWNS if x[0] == os.environ["MON_ONLY"]]
MODS = {"monster_brain": m_brain, "monster_chick": m_chick, "monster_flipper": m_flipper, "monster_floater": m_float,
	"monster_gladiator": m_gladiator, "monster_hover": m_hover, "misc_insane": m_insane, "monster_medic": m_medic,
	"monster_mutant": m_mutant, "monster_parasite": m_parasite, "monster_supertank": m_supertank,
	"monster_tank": m_tank, "monster_tank_commander": m_tank}
st = {"t0": None, "phase": 0, "ents": [], "moves": {}, "errors": 0, "calls": 0}

def guard(label, fn, *a):
	st["calls"] += 1
	try:
		fn(*a)
	except Exception:
		st["errors"] += 1
		print("mon: ERROR in %s" % label)
		traceback.print_exc(limit=6, file=sys.stdout)

def mons():
	return [(e, c) for e, c in st["ents"] if e.inuse and e.classname == c]	# a freed edict may be reused by another entity

o = cl_main.CL_Frame
def CL_Frame(msec):
	o(msec)
	if cl_main.cls.state.name != "ca_active": return
	if st["t0"] is None: st["t0"] = time.time()
	t = time.time() - st["t0"]
	player = g_main.g_edicts[1]
	if os.environ.get("MON_ONLY") and st["ents"]:
		e = st["ents"][0][0]
		row = (st["phase"], e.inuse, e.health, e.deadflag, e.classname, [round(float(x)) for x in e.s.origin])
		if row != st.get("lastrow"):
			print("mon: state", row); st["lastrow"] = row
	if st["phase"] == 0 and t > 1:
		i = len(st["ents"])
		if t < 1 + 0.4 * i: return
		for i, (cls, flags) in [(i, SPAWNS[i])]:
			e = g_utils.G_Spawn()
			e.classname = cls
			e.spawnflags = flags
			ang = i * (2 * np.pi / len(SPAWNS))
			for j, v in enumerate((player.s.origin[0] + 160 * np.cos(ang), player.s.origin[1] + 160 * np.sin(ang), player.s.origin[2] + 8)):
				e.s.origin[j] = v
			guard("spawn " + cls, g_spawn.ED_CallSpawn, e)
			st["ents"].append((e, cls))
		if len(st["ents"]) < len(SPAWNS): return
		print("mon: spawned", [(c, e.inuse, e.health) for e, c in st["ents"]])
		st["phase"] = 1; st["pt"] = t
	elif st["phase"] == 1 and t > st["pt"] + 1:
		for e, cls in mons():
			e.enemy = player
			mi = e.monsterinfo
			for name in ("stand", "walk", "run", "attack", "melee", "search", "idle", "checkattack"):
				f = getattr(mi, name)
				if f: guard("%s.%s" % (cls, name), f, e)
			if mi.sight: guard(cls + ".sight", mi.sight, e, player)
			if mi.dodge: guard(cls + ".dodge", mi.dodge, e, player, 0.5)
		print("mon: callbacks done")
		st["phase"] = 4 if os.environ.get("MON_SKIP23") else 2
	elif st["phase"] == 2 and t > st["pt"] + 2:
		# every frame's think function, with s.frame set as during that frame
		# (one monster per frame, so the reliable message buffer does not overflow)
		todo = st.setdefault("think_todo", list(mons()))
		if not todo: st["phase"] = 3; st["mt"] = t; print("mon: think functions done"); return
		for e, cls in [todo.pop(0)]:
			mod = MODS[cls]
			for k, v in sorted(vars(mod).items()):
				if isinstance(v, local.mmove_t):
					for i, fr in enumerate(v.frame[:v.lastframe - v.firstframe + 1]):
						if fr.thinkfunc and e.inuse:
							e.enemy = player
							if fr.thinkfunc.__name__ == "medic_cable_attack":
								# the medic heals a (dead) monster, not the player
								others = [o for o, c in mons() if o is not e and c != "monster_medic"]
								if others: e.enemy = others[0]
							e.s.frame = v.firstframe + i
							guard("%s %s[%d] %s" % (cls, k, i, fr.thinkfunc.__name__), fr.thinkfunc, e)
					if v.endfunc and e.inuse:
						e.enemy = player
						guard("%s %s end %s" % (cls, k, v.endfunc.__name__), v.endfunc, e)
		return
	elif st["phase"] == 3:
		# cycle each monster through all its moves, letting the game run them
		for e, cls in mons():
			moves = st["moves"].setdefault(id(e), [v for k, v in sorted(vars(MODS[cls]).items()) if isinstance(v, local.mmove_t)])
			if moves and int((t - st["mt"]) * 4) < len(moves) * 1:
				idx = int((t - st["mt"]) * 4) % len(moves)
				if e.monsterinfo.currentmove is not moves[idx]:
					e.monsterinfo.currentmove = moves[idx]
					e.monsterinfo.nextframe = 0
			e.enemy = player
		if t - st["mt"] > (0 if os.environ.get("MON_NOCYCLE") else 12):
			print("mon: move cycling done"); st["phase"] = 4
	elif st["phase"] == 4:
		for e, cls in mons():
			for dmg in (5, 20, 50):
				e.pain_debounce_time = 0
				guard("%s.pain(%d)" % (cls, dmg), e.pain, e, player, 0, dmg)
		print("mon: pain done"); st["phase"] = 5; st["dt"] = t
	elif st["phase"] == 5 and t - st["dt"] > 1:
		for i, (e, cls) in enumerate(mons()):
			if e.die is None or e.classname != cls:
				continue	# already killed (monsters can fight each other) and the edict reused or gibbed
			e.health = -1 if i % 2 == 0 else -500
			guard(cls + ".die", e.die, e, player, player, 600, e.s.origin)
		print("mon: die done"); st["phase"] = 6; st["dt"] = t
	elif st["phase"] == 6 and t - st["dt"] > 4:
		print("mon: finished calls %d errors %d" % (st["calls"], st["errors"]))
		sys.stdout.flush(); os._exit(0)
cl_main.CL_Frame = CL_Frame
import ast as _ast
FILES = ["game/monster/%s/%s.py" % (m, m) for m in ("brain","chick","flipper","float","gladiator","hover","insane","medic","mutant","parasite","supertank","tank")]
called = set()
def prof(frame, event, arg):
	if event == "call":
		f = frame.f_code.co_filename
		if "/game/monster/" in f: called.add((f.split("/quake2/")[-1], frame.f_code.co_name))
import threading
sys.setprofile(prof)
_o_exit = os._exit
def _exit(code):
	missing = []
	for p in FILES:
		for n in _ast.parse(open(p).read()).body:
			if isinstance(n, _ast.FunctionDef) and n.name not in ("_mf", "_mm") and (p, n.name) not in called:
				missing.append("%s:%s" % (p.split("/")[-1], n.name))
	print("mon: coverage: %d functions never called: %s" % (len(missing), " ".join(missing)))
	sys.stdout.flush(); _o_exit(code)
os._exit = _exit
sys_linux.main()
