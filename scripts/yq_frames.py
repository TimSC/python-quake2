"""
Compare a monster module's frame tables (mframe_t lists and mmove_t moves)
with Yamagi's C, and optionally rewrite the ones that differ.

usage: yq_frames.py <module.py> <yamagi .c path under yquake2/src> [--fix]

A table is rewritten from the C as a list of _mf(aifunc, dist, thinkfunc)
entries, three to a line; a move as _mm(<header>.FRAME_first,
<header>.FRAME_last, table, endfunc). The functions a rewritten table names
must already exist in the module.

See docs/yquake2_plan.md.
"""
from __future__ import annotations

import os
import re
import sys
import ast
import importlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YQ = os.path.join(ROOT, "yquake2", "src")
sys.path.insert(0, ROOT)

FRAMES_RE = re.compile(r"mframe_t\s+(\w+)\s*\[\s*\]\s*=\s*\{(.*?)\};", re.S)
ENTRY_RE = re.compile(r"\{\s*(\w+)\s*,\s*([-+\w.]+?)f?\s*,\s*(\w+)\s*\}")
MOVE_RE = re.compile(r"mmove_t\s+(\w+)\s*=\s*\{\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*\}", re.S)


def c_tables(src):
	src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
	defines = dict(re.findall(r"^#define\s+(\w+)\s+([-+\d.]+)f?\s*$", src, re.M))
	def num(d):
		return float(defines.get(d, d))
	frames = {m.group(1): [(a, num(d), t, d) for a, d, t in ENTRY_RE.findall(m.group(2))] for m in FRAMES_RE.finditer(src)}
	moves = {m.group(1): m.groups()[1:] for m in MOVE_RE.finditer(src)}
	return frames, moves


def fname(f):
	return "NULL" if f is None else f.__name__


def qual(mod, name):
	"""A function name as the module can reach it: its own, or through a module it imports."""
	if hasattr(mod, name): return name
	for alias in dir(mod):
		m = getattr(mod, alias)
		if type(m).__name__ == "module" and hasattr(m, name):
			return alias + "." + name
	return name


def fmt_num(d):
	return str(int(d)) if d == int(d) else repr(d)


def main(argv):
	fix = "--fix" in argv
	argv = [a for a in argv if a != "--fix"]
	modpath, cpath = argv[0], argv[1]
	cframes, cmoves = c_tables(open(os.path.join(YQ, cpath), errors="replace").read())
	modname = os.path.relpath(os.path.abspath(modpath), ROOT)[:-3].replace(os.sep, ".")
	mod = importlib.import_module(modname)
	src = open(modpath).read()
	tree = ast.parse(src)
	lines = src.splitlines(keepends=True)
	assigns = {}
	for st in tree.body:
		if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
			assigns[st.targets[0].id] = st
	# the header module the moves use for FRAME_ names
	hdr = None
	for st in tree.body:
		if isinstance(st, ast.ImportFrom) and st.module and st.module.startswith("game.monster."):
			for a in st.names:
				if (a.asname or a.name).endswith("_h") and a.name != "player":
					hdr = a.asname or a.name
	edits = []
	for name, entries in cframes.items():
		py = getattr(mod, name, None)
		if py is None:
			print("missing table %s" % name); continue
		have = [(fname(f.aifunc), float(f.dist), fname(f.thinkfunc)) for f in py]
		if have != [e[:3] for e in entries]:
			print("table %s differs (%d entries here, %d in C)" % (name, len(have), len(entries)))
			for i, (h, c) in enumerate(zip(have, entries)):
				if h != c[:3]: print("   [%d] %s -> %s" % (i, h, c[:3]))
			if fix and name in assigns and entries:
				ents = ["_mf(%s, %s, %s)" % (qual(mod, a), raw if re.match(r"[A-Za-z_]", raw) else fmt_num(d), "None" if t == "NULL" else qual(mod, t))
					for a, d, t, raw in entries]
				rows = [", ".join(ents[i:i + 3]) for i in range(0, len(ents), 3)]
				text = "%s = [\n\t%s]\n" % (name, ",\n\t".join(rows))
				st = assigns[name]
				edits.append((st.lineno - 1, st.end_lineno, text))
	for name, (first, last, frames, endfunc) in cmoves.items():
		py = getattr(mod, name, None)
		if py is None:
			print("missing move %s" % name); continue
		hv = getattr(mod, hdr) if hdr else None
		want_first = getattr(hv, first, None) if hv else None
		want_last = getattr(hv, last, None) if hv else None
		frames_ok = py.frame is getattr(mod, frames, None)
		if (py.firstframe, py.lastframe) != (want_first, want_last) or not frames_ok or fname(py.endfunc) != endfunc:
			print("move %s differs: here (%s, %s, frames ok %s, %s), C (%s, %s, %s, %s)" % (
				name, py.firstframe, py.lastframe, frames_ok, fname(py.endfunc), first, last, frames, endfunc))
			if fix and name in assigns and hdr:
				text = "%s = _mm(%s.%s, %s.%s, %s, %s)\n" % (name, hdr, first, hdr, last, frames, "None" if endfunc == "NULL" else endfunc)
				st = assigns[name]
				edits.append((st.lineno - 1, st.end_lineno, text))
	for name in assigns:
		pass
	if fix and edits:
		for a, b, text in sorted(edits, reverse=True):
			lines[a:b] = [text]
		open(modpath, "w").write("".join(lines))
		print("rewrote %d tables/moves" % len(edits))


if __name__ == "__main__":
	main(sys.argv[1:])
