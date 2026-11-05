# Hold the attack button and trace every blaster bolt: spawn, touch/free, server frames sent, client receipt.
import os, sys, time
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from linux import sys_linux
from client import cl_main, cl_ents, client
pass
from game import g_main, g_weapon, g_utils, p_client

st = {"t0": None, "bolts": {}, "seq": 0, "fired": 0}
def T(): return time.time() - st["t0"] if st["t0"] else 0

pass
from common.header import shared
from server import sv_entities
from server import sv_init
o_tr = g_main.gi
_trace_log = []
def wrap_trace():
	o = g_main.gi.trace
	def tr(start, mins, maxs, end, passent, mask):
		r = o(start, mins, maxs, end, passent, mask)
		if passent is not None and passent.classname == "bolt" and r.fraction < 1.0:
			print("fire: %.2f bolt trace hit fraction %.3f startsolid %s ent %s (edict %s inuse %s) plane %s" % (T(), r.fraction, r.startsolid, r.ent.classname if r.ent else None, g_main.g_edicts.index(r.ent) if r.ent in g_main.g_edicts else "?", r.ent.inuse if r.ent else None, r.plane.normal))
		return r
	g_main.gi.trace = tr
o_fb = g_weapon.fire_blaster
def fire_blaster(self, start, dir, damage, speed, effect, hyper):
	n_before = g_main.glob.num_edicts
	o_fb(self, start, dir, damage, speed, effect, hyper)
	st["fired"] += 1
	# find the bolt just spawned
	for i in range(1, g_main.glob.num_edicts):
		e = g_main.g_edicts[i]
		if e.inuse and e.classname == "bolt" and id(e) not in [b["id"] for b in st["bolts"].values() if b["alive"]]:
			st["seq"] += 1
			st["bolts"][st["seq"]] = {"id": id(e), "num": i, "alive": True, "t": T(), "sent": 0, "recv": 0, "end": None}
			print("fire: %.2f bolt %d spawned edict %d origin %s" % (T(), st["seq"], i, [round(float(x)) for x in e.s.origin]))
			break
	else:
		print("fire: %.2f fire_blaster called but no live bolt found (freed immediately?)" % T())
g_weapon.fire_blaster = fire_blaster

o_free = g_utils.G_FreeEdict
def G_FreeEdict(ed):
	for k, b in st["bolts"].items():
		if b["alive"] and b["id"] == id(ed):
			b["alive"] = False; b["end"] = T()
			print("fire: %.2f bolt %d freed after %.2fs sent-in-frames %d received %d" % (T(), k, b["end"] - b["t"], b["sent"], b["recv"]))
	return o_free(ed)
g_utils.G_FreeEdict = G_FreeEdict

o_think = p_client.ClientThink
def ClientThink(ent, ucmd):
	if cl_main.cls.state.name == "ca_active":
		if st["t0"] is None: st["t0"] = time.time(); wrap_trace()
		if T() > 1 and T() < 5:
			ucmd.buttons |= shared.BUTTON_ATTACK
	o_think(ent, ucmd)
	if st["t0"] and T() > 8:
		print("fire: done fired %d bolts tracked %d" % (st["fired"], len(st["bolts"])))
		sys.stdout.flush(); os._exit(0)
p_client.ClientThink = ClientThink

o_build = sv_entities.SV_BuildClientFrame
def SV_BuildClientFrame(cl):
	o_build(cl)
	frame = cl.frames[sv_init.sv.framenum & 15]
	nums = set()
	for i in range(frame.num_entities):
		s = sv_init.svs.client_entities[(frame.first_entity + i) % sv_init.svs.num_client_entities]
		nums.add(s.number)
	for b in st["bolts"].values():
		if b["alive"] and b["num"] in nums: b["sent"] += 1
sv_entities.SV_BuildClientFrame = SV_BuildClientFrame

o_cf = cl_main.CL_Frame
def CL_Frame(msec):
	o_cf(msec)
	if cl_main.cls.state.name != "ca_active": return
	fr = cl_main.cl.frame
	nums = set()
	for i in range(fr.num_entities):
		s = cl_main.cl_parse_entities[(fr.parse_entities + i) & (client.MAX_PARSE_ENTITIES - 1)]
		nums.add(s.number)
	for b in st["bolts"].values():
		if b["alive"] and b["num"] in nums: b["recv"] += 1
cl_main.CL_Frame = CL_Frame
sys_linux.main()
