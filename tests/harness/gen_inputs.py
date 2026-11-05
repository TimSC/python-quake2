"""
Write seeded random inputs for the collision and pmove harnesses, and extract a
map from the game's pak files to a scratch directory (game data never goes into
the repository).

usage: gen_inputs.py <outdir> [map=base1] [seed=1]
writes <outdir>/<map>.bsp, <outdir>/cm_in.txt, <outdir>/pm_in.txt
"""
from __future__ import annotations

import os
import sys
import glob
import random
import struct


def extract(basedir, name, out):
	for pak in sorted(glob.glob(os.path.join(basedir, "baseq2", "pak*.pak"))):
		with open(pak, "rb") as f:
			ident, dirofs, dirlen = struct.unpack("<4sii", f.read(12))
			f.seek(dirofs)
			for i in range(dirlen // 64):
				fn, pos, ln = struct.unpack("<56sii", f.read(64))
				if fn.split(b"\0")[0].decode("ascii").lower() == name:
					f.seek(pos); open(out, "wb").write(f.read(ln)); return True
	loose = os.path.join(basedir, "baseq2", name)
	if os.path.exists(loose):
		open(out, "wb").write(open(loose, "rb").read()); return True
	return False


def bounds(bsp):
	"""World bounds and inline model count from the bsp's model lump."""
	d = open(bsp, "rb").read()
	ofs, ln = struct.unpack_from("<ii", d, 8 + 13 * 8)	# LUMP_MODELS
	n = ln // 48
	mins = struct.unpack_from("<3f", d, ofs); maxs = struct.unpack_from("<3f", d, ofs + 12)
	return mins, maxs, n


def main(argv):
	out = argv[0]; mapname = argv[1] if len(argv) > 1 else "base1"; seed = int(argv[2]) if len(argv) > 2 else 1
	basedir = os.environ.get("Q2DATA", "/home/tim/dev/quake2data/Data")
	os.makedirs(out, exist_ok=True)
	bsp = os.path.join(out, mapname + ".bsp")
	if not extract(basedir, "maps/%s.bsp" % mapname, bsp):
		sys.exit("map not found in " + basedir)
	mins, maxs, nmodels = bounds(bsp)
	r = random.Random(seed)
	def pt(): return [round(r.uniform(mins[i], maxs[i]), 3) for i in range(3)]
	MASKS = [33619971, 1, 33554433 | 2 | 0x10000]	# MASK_PLAYERSOLID, CONTENTS_SOLID, solid|window|playerclip
	with open(os.path.join(out, "cm_in.txt"), "w") as f:
		for i in range(4000):
			model = 0 if r.random() < 0.4 else r.randrange(1, nmodels)
			o = [0, 0, 0] if r.random() < 0.5 else [round(r.uniform(-64, 64), 3) for _ in range(3)]
			a = [0, 0, 0] if r.random() < 0.6 else [round(r.uniform(-180, 180), 3) for _ in range(3)]
			s = pt()
			e = s[:] if r.random() < 0.1 else [round(s[k] + r.uniform(-300, 300), 3) for k in range(3)]
			box = r.choice([(0, 0, 0, 0, 0, 0), (-4, -4, -4, 4, 4, 4), (-16, -16, -24, 16, 16, 32), (-16, -16, -24, 16, 16, 4)])
			f.write(" ".join(str(x) for x in [model] + o + a + s + e + list(box) + [r.choice(MASKS)]) + "\n")
	with open(os.path.join(out, "pm_in.txt"), "w") as f:
		for i in range(1500):
			p = pt()
			org = [int(p[k] * 8) for k in range(3)]
			vel = [r.randint(-3000, 3000) for _ in range(3)]
			flags = r.choice([0, 0, 1, 2, 4, 8, 16, 32])
			cmd = [r.choice([11, 16, 25, 50]), r.choice([0, 0, 1]), r.randint(-32768, 32767), r.randint(-32768, 32767), 0,
				r.choice([-400, -200, 0, 200, 400]), r.choice([-200, 0, 200]), r.choice([-200, 0, 0, 200])]
			models = r.sample(range(1, nmodels), min(3, nmodels - 1))
			v = [r.choice([0, 0, 0, 1, 2, 3, 4])] + org + vel + [flags, r.choice([0, 0, 8, 50]), 800] + [0, r.randint(-8000, 8000), 0] \
				+ cmd + [r.choice([0, 1]), r.choice([1, 8, 20]), len(models)] + models
			f.write(" ".join(str(x) for x in v) + "\n")
	print("wrote", bsp, "and inputs for", nmodels, "models")


if __name__ == "__main__":
	main(sys.argv[1:])
