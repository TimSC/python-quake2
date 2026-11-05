"""
Give each moved module the same local import name in every file, e.g. always
"from common.shared import shared as shared_c". Rewrites the import and every
reference through the old local name (top-level imports only; a name rebound in
a function is left alone there).

usage: yq_alias.py module=local [...] [--dry-run]
  e.g. yq_alias.py common.header.shared=shared common.shared.shared=shared_c

See docs/yquake2_plan.md.
"""
from __future__ import annotations

import os
import sys
import ast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yq_move as ym


def rewrite(path, src, canon):
	tree = ast.parse(src)
	par = ym.parents(tree)
	ed = ym.Edits(src)
	rename = {}	# old local -> new local
	for st in tree.body:
		if isinstance(st, ast.ImportFrom) and st.module and st.level == 0:
			parts = []
			changed = False
			for a in st.names:
				full = st.module + "." + a.name
				loc = a.asname or a.name
				if full in canon and canon[full] != loc:
					rename[loc] = canon[full]; changed = True
					new = canon[full]
					parts.append(a.name if new == a.name else "%s as %s" % (a.name, new))
				else:
					parts.append(a.name if not a.asname else "%s as %s" % (a.name, a.asname))
			if changed:
				ed.replace(st, "from %s import %s" % (st.module, ", ".join(parts)))
	if not rename:
		return src, []
	# the new names must be free in the file
	bound = set()
	for n in ast.walk(tree):
		if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store): bound.add(n.id)
		elif isinstance(n, (ast.FunctionDef, ast.ClassDef)): bound.add(n.name)
		elif isinstance(n, ast.arg): bound.add(n.arg)
		elif isinstance(n, (ast.Import, ast.ImportFrom)):
			for a in n.names:
				loc = (a.asname or a.name).split(".")[0]
				if loc not in rename: bound.add(loc)
	clash = [new for old, new in rename.items() if new in bound]
	if clash:
		return None, ["%s: new local name(s) %s already bound" % (path, clash)]
	for n in ast.walk(tree):
		if isinstance(n, ast.Name) and n.id in rename:
			if any(not isinstance(fn, ast.Lambda) and n.id in ym.bound_names(fn)[0] for fn in ym.enclosing_functions(n, par)):
				continue
			ed.replace(n, rename[n.id])
	return ed.apply(), []


def main(argv):
	dry = "--dry-run" in argv
	canon = dict(a.split("=") for a in argv if "=" in a)
	results = {}; notes = []
	for f in ym.scope_files():
		src = open(os.path.join(ym.ROOT, f)).read()
		out, n = rewrite(f, src, canon)
		notes += n
		if out is not None and out != src:
			compile(out, f, "exec")
			results[f] = out
	for n in notes: print("note:", n)
	print("files rewritten: %d" % len(results))
	if dry or notes: return
	for f, t in results.items():
		open(os.path.join(ym.ROOT, f), "w").write(t)


if __name__ == "__main__":
	main(sys.argv[1:])
