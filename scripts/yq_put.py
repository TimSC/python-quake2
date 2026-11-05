"""
Put ported functions into a module: each top-level def in the snippet file
replaces the def of the same name in the module, or, if the function isn't
ported yet, the triple-quoted C block that holds it (the C is deleted, as the
porting style asks). A banner string just before a def in the snippet goes
with it. Anything else in the snippet (globals) is an error, put it in by hand.

usage: yq_put.py <module.py> <snippet.py> [--dry-run]
"""
from __future__ import annotations

import os
import re
import sys
import ast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yq_sync as ys


Q3 = '"' * 3


def units(src):
	"""(kind, name, start, end) of the module's defs and C blocks, as character offsets of whole lines."""
	tree = ast.parse(src)
	lines = src.splitlines(keepends=True)
	starts = [0]
	for l in lines: starts.append(starts[-1] + len(l))
	out = []
	for st in tree.body:
		a = starts[st.lineno - 1]
		if isinstance(st, ast.FunctionDef):
			a = starts[(st.decorator_list[0].lineno if st.decorator_list else st.lineno) - 1]
			out.append(("def", st.name, a, starts[st.end_lineno]))
			# the banner string right before the def (a short one, not a block of C)
			k = tree.body.index(st)
			prev = tree.body[k - 1] if k > 0 else None
			if prev is not None and isinstance(prev, ast.Expr) and isinstance(prev.value, ast.Constant) and \
					isinstance(prev.value.value, str) and not ys.c_block_functions(prev.value.value) and prev.value.value.count("\n") < 15:
				out.append(("banner", st.name, starts[prev.lineno - 1], starts[prev.end_lineno]))
		elif isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
			for f in ys.c_block_functions(st.value.value):
				out.append(("c", f, a, starts[st.end_lineno]))
	return out


def snippet_defs(src):
	tree = ast.parse(src)
	lines = src.splitlines(keepends=True)
	starts = [0]
	for l in lines: starts.append(starts[-1] + len(l))
	out = []; pending = None
	for st in tree.body:
		if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
			pending = starts[st.lineno - 1]; continue
		if isinstance(st, (ast.Import, ast.ImportFrom)):
			continue
		if not isinstance(st, ast.FunctionDef):
			sys.exit("snippet has a non-def statement at line %d" % st.lineno)
		a = pending if pending is not None else starts[st.lineno - 1]
		k = tree.body.index(st)
		b = starts[tree.body[k + 1].lineno - 1] if k + 1 < len(tree.body) else len(src)	# with comment lines after the body
		out.append((st.name, src[a:b].rstrip("\n") + "\n"))
		pending = None
	return out


def put(path, snippet, dry=False):
	src = open(path).read()
	done = []
	for name, text in snippet_defs(open(snippet).read()):
		u = [x for x in units(src) if x[1] == name]
		defs = [x for x in u if x[0] == "def"]
		cs = [x for x in u if x[0] == "c"]
		if defs:
			kind, n, a, b = defs[0]
			banners = [x for x in u if x[0] == "banner"]
			if banners and text.lstrip().startswith((Q3, "r" + Q3)):
				a = banners[0][2]	# the snippet brings its own banner: it replaces the old one
			# keep the banner string before the def (it isn't part of the def unit)
			src = src[:a] + text + ("\n" if src[b:b + 1] != "\n" else "") + src[b:]
			done.append(name + " (def replaced)")
		elif cs:
			kind, n, a, b = cs[0]
			block = src[a:b]
			others = [f for f in ys.c_block_functions(ast.literal_eval(block.strip())) if f != name]
			if others:
				sys.exit("%s: the C block of %s also holds %s; split it first" % (path, name, others))
			src = src[:a] + text + "\n" + src[b:].lstrip("\n")
			done.append(name + " (C replaced)")
		else:
			sys.exit("%s: no def or C block for %s" % (path, name))
	compile(src, path, "exec")
	print(path + ": " + ", ".join(done))
	if not dry:
		open(path, "w").write(src)


if __name__ == "__main__":
	args = [a for a in sys.argv[1:] if not a.startswith("--")]
	put(args[0], args[1], "--dry-run" in sys.argv)
