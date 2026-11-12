"""
Static checks over the whole port, with no game data needed:
 - every module compiles and imports;
 - names read inside functions exist (local, parameter, module global or builtin);
 - every 'module.name' reference through an imported module exists in that module;
 - monster frame tables have as many frames as their first..last range (reported as notes:
   id's own tables have some of these bugs).

usage: env/bin/python tests/check_static.py [file.py ...]   (default: every package module)
Exit status 1 if anything is reported.
"""
from __future__ import annotations

import os
import sys
import ast
import builtins
import importlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
SKIP_DIRS = {"env", "yquake2", "quake2-original", "tests", "scripts", "benchmarks", "docs", "DOCS", "baseq2", ".git", "__pycache__"}


def package_files():
	out = []
	for dp, dn, fs in os.walk(ROOT):
		rel = os.path.relpath(dp, ROOT)
		dn[:] = [d for d in dn if d not in SKIP_DIRS and not d.startswith(".") and not os.path.exists(os.path.join(dp, d, "pyvenv.cfg"))]
		if rel == ".": continue
		for f in fs:
			if f.endswith(".py"): out.append(os.path.join(rel, f))
	return sorted(out)


def bound_in(fn):
	local = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
	if fn.args.vararg: local.add(fn.args.vararg.arg)
	if fn.args.kwarg: local.add(fn.args.kwarg.arg)
	for n in ast.walk(fn):
		if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)): local.add(n.id)
		elif isinstance(n, (ast.Import, ast.ImportFrom)):
			for a in n.names: local.add((a.asname or a.name).split(".")[0])
		elif isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n is not fn: local.add(n.name)
		elif isinstance(n, ast.ExceptHandler) and n.name: local.add(n.name)
		elif isinstance(n, ast.arg): local.add(n.arg)
	return local


_DECLARED = {}


def declared(m):
	"""Names a module defines, including globals first assigned inside functions (cvars set by a register function)."""
	f = getattr(m, "__file__", None)
	if not f: return set()
	if not f.endswith(".py"): return set(vars(m))	# a compiled extension (e.g. _ctypes): no source to scan
	if f not in _DECLARED:
		names = set(vars(m))
		for n in ast.walk(ast.parse(open(f).read())):
			if isinstance(n, ast.Global): names |= set(n.names)
		_DECLARED[f] = names
	return _DECLARED[f]


def check(p):
	problems = []
	src = open(os.path.join(ROOT, p)).read()
	try:
		tree = ast.parse(src)
	except SyntaxError as e:
		return ["%s: syntax error %s" % (p, e)]
	modname = p[:-3].replace("/", ".")
	try:
		mod = importlib.import_module(modname)
	except Exception as e:
		return ["%s: import failed: %r" % (p, e)]
	g = declared(mod) | set(dir(builtins))
	outer = {}	# nested function -> names bound by the functions around it
	for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
		b = bound_in(fn) | outer.get(fn, set())
		for n in ast.walk(fn):
			if isinstance(n, ast.FunctionDef) and n is not fn: outer[n] = outer.get(n, set()) | b
	for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
		local = bound_in(fn) | outer.get(fn, set())
		for n in ast.walk(fn):
			if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in local and n.id not in g:
				problems.append("%s:%d: %s: undefined name %s" % (p, n.lineno, fn.name, n.id))
	# module.attr references (module-level aliases only; a function that rebinds the alias is skipped)
	mods = {k: v for k, v in vars(mod).items() if type(v).__name__ == "module"}
	shadow = {}
	for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
		b = bound_in(fn)
		for n in ast.walk(fn):
			shadow.setdefault(id(n), set()).update(b)
	for n in ast.walk(tree):
		if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in mods:
			if n.value.id in shadow.get(id(n), ()): continue
			m = mods[n.value.id]
			if n.attr not in declared(m) and isinstance(n.ctx, ast.Load):
				f = getattr(m, "__file__", None) or ""
				if f.startswith(ROOT) and "/site-packages/" not in f:
					problems.append("%s:%d: %s.%s does not exist (%s)" % (p, n.lineno, n.value.id, n.attr, m.__name__))
	# modules imported inside a function: their attributes must exist too
	for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
		for imp in [n for n in ast.walk(fn) if isinstance(n, ast.ImportFrom) and n.module and n.level == 0]:
			for a in imp.names:
				try:
					m = importlib.import_module(imp.module + "." + a.name)
				except ImportError:
					continue
				f = getattr(m, "__file__", None) or ""
				if not f.startswith(ROOT) or "/site-packages/" in f: continue
				loc = a.asname or a.name
				for x in ast.walk(fn):
					if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id == loc and \
							isinstance(x.ctx, ast.Load) and x.attr not in declared(m):
						problems.append("%s:%d: %s.%s does not exist (%s, imported in %s)" % (p, x.lineno, loc, x.attr, m.__name__, fn.name))
	return problems


def frame_tables(p):
	out = []
	modname = p[:-3].replace("/", ".")
	mod = sys.modules.get(modname)
	if mod is None: return out
	for k, v in vars(mod).items():
		if type(v).__name__ == "mmove_t" and v.firstframe is not None:
			n = v.lastframe - v.firstframe + 1
			if n != len(v.frame): out.append("%s: frame table %s has %d frames, range says %d" % (p, k, len(v.frame), n))
	return out


def main(argv):
	files = argv or package_files()
	problems = []
	for p in files:
		problems += check(p)
	notes = []
	for p in files:
		notes += frame_tables(p)	# id's data has some of these; Yamagi fixes several (group 8)
	for x in problems: print(x)
	for x in notes: print("note:", x)
	print("check_static: %d files, %d problems" % (len(files), len(problems)))
	return 1 if problems else 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
