"""
Write game/savegame/tables/*.py from Yamagi's game/savegame/tables/*.h:
the field tables (entfields, levelfields, clientfields, stfields), the
function lists (gamefunc_list) and the mmove list (gamemmove_list).

usage: yq_savetables.py

The C lists hold function and mmove_t pointers; the Python lists hold their
names, and savegame.py finds the objects by name when it first needs them.

See docs/yquake2_plan.md.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = os.path.join(ROOT, "yquake2", "src", "game", "savegame", "tables")
OUT = os.path.join(ROOT, "game", "savegame", "tables")


def head(src):
	h = src[:src.index("*/") + 2]
	lines = [l[3:] if l.startswith(" * ") else ("" if l.strip() in ("*", "/*", "*/") else l) for l in h.splitlines()]
	return '"""\n' + "\n".join(lines).strip("\n") + '\n"""\nfrom __future__ import annotations\n\n'


def fields(name):
	src = open(os.path.join(TABLES, name + ".h")).read()
	out = head(src) + "from game.header import local\n\n%s = [ #field_t []\n" % name
	for m in re.finditer(r'^\{\s*"([^"]+)",\s*(?:(\w+)\(([\w.\[\]]+)\)|0),\s*(\w+)(?:,\s*([\w|]+))?(?:,\s*(\d+))?\s*,?\s*\},', src, re.M):
		nm, macro, path, typ, flags, ver = m.groups()
		ofs = 'local.%s("%s")' % (macro, path) if macro else "0"
		args = '"%s", %s, local.fieldtype_t.%s' % (nm, ofs, typ)
		if flags and flags != "0":
			args += ", " + " | ".join("local." + f for f in flags.split("|"))
		elif ver:
			args += ", 0"
		if ver:
			args += ", " + ver
		out += "\tlocal.field_t(%s),\n" % args
	out += "]\n"
	open(os.path.join(OUT, name + ".py"), "w").write(out)


def funclist():
	src = open(os.path.join(TABLES, "gamefunc_list.h")).read()
	out = head(src)
	out += "# Q2PORT: the C entries are {\"name\", (byte *)function}; here they are the names,\n"
	out += "# and savegame.py looks the functions up by name.\n\n"
	for m in re.finditer(r"static const fnlist_entry_t (\w+)\[\]\s*=\s*\{(.*?)\};", src, re.S):
		names = re.findall(r'\{"(\w+)",', m.group(2))
		out += "%s = [ #fnlist_entry_t []\n" % m.group(1) + "".join('\t"%s",\n' % n for n in names) + "]\n"
	for m in re.finditer(r"static const functionList_t (\w+)\s*=\s*\{\s*\"(\w+)\",\s*(\w+),", src, re.S):
		out += '%s = ("%s", %s) #functionList_t: name, entries\n' % m.groups()
	open(os.path.join(OUT, "gamefunc_list.py"), "w").write(out)


def mmovelist():
	src = open(os.path.join(TABLES, "gamemmove_list.h")).read()
	out = head(src)
	out += "# Q2PORT: the C entries are {\"name\", &mmove}; here they are the names.\n\n"
	names = re.findall(r'^\{"(\w+)", &\w+\},', src, re.M)
	out += "mmoveList = [ #mmoveList_t []\n" + "".join('\t"%s",\n' % n for n in names) + "]\n"
	open(os.path.join(OUT, "gamemmove_list.py"), "w").write(out)


def main():
	os.makedirs(OUT, exist_ok=True)
	for n in ("entfields", "levelfields", "clientfields", "stfields"):
		fields(n)
	funclist()
	mmovelist()
	for f in sorted(os.listdir(OUT)):
		if f.endswith(".py"): print(f, sum(1 for _ in open(os.path.join(OUT, f))))


if __name__ == "__main__":
	main()
