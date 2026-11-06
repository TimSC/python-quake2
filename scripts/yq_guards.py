"""
Add Yamagi's leading null guards ("if (!ent || !ent->client) { return; }")
to the ported Python functions that don't have them yet.

usage: yq_guards.py <module.py> <yamagi .c path under yquake2/src> [--dry-run]
       yq_guards.py --dedupe <module.py> ... [--dry-run]   remove leading checks an earlier one covers

Only guards at the top of a C function (after its declarations) are copied,
and only when every name in the condition is a parameter of the function
(the first guard that isn't ends the list).
Each guard goes before the first statement of the Python function, after its
banner and C-locals strings. Functions that already test the same condition
near their top are left alone.

See docs/yquake2_plan.md.
"""
from __future__ import annotations

import os
import re
import sys
import ast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YQ = os.path.join(ROOT, "yquake2", "src")

TYPES = {"int", "float", "char", "qboolean", "double", "unsigned", "const", "static", "byte", "short",
	"long", "struct", "signed", "vec_t", "size_t", "void"}

FUNC_RE = re.compile(r"^([A-Za-z_]\w*)\(([^)]*)\)\s*\n\{\n(.*?)\n\}\n", re.M | re.S)
GUARD_RE = re.compile(r"\tif \((?P<cond>[^{}]*?)\)\n\t\{\n\t\treturn(?: (?P<val>[^;]+))?;\n\t\}\n", re.S)


def c_functions(src):
	out = {}
	for m in FUNC_RE.finditer(src):
		name, params, body = m.group(1), m.group(2), m.group(3) + "\n"
		pnames, arrays = [], set()
		for p in params.split(","):
			p = p.strip()
			if not p or p == "void" or p == "...": continue
			arr = "[" in p
			p = re.sub(r"\[.*\]", "", p)
			pn = re.findall(r"\w+", p)[-1]
			pnames.append(pn)
			# vectors and numeric buffers are numpy arrays / bytearrays: test them with "is None"
			# and strings: "" is a valid C string, only NULL fails the test
			if arr or re.search(r"\b(vec3_t|vec_t|float|int|byte|short|double|char)\b\s*\*?\s*$", p[:p.rindex(pn)]) and ("*" in p or "vec3_t" in p):
				arrays.add(pn)
		out.setdefault(name, (pnames, body, arrays))
	return out


def is_decl(line):
	s = line.strip()
	if not s.endswith(";") or not line.startswith("\t") or line.startswith("\t\t"): return False
	w = re.match(r"[A-Za-z_]\w*", s)
	if not w: return False
	w = w.group(0)
	return (w in TYPES or w.endswith("_t")) and "->" not in s.split("=")[0]


def leading_guards(body):
	"""The guard blocks at the top of a C function body, after its declarations."""
	pos = 0
	lines = body.split("\n")
	# skip declarations and blank lines
	i = 0
	while i < len(lines) and (not lines[i].strip() or is_decl(lines[i])):
		i += 1
	pos = sum(len(l) + 1 for l in lines[:i])
	guards = []
	while True:
		while body[pos:pos + 1] == "\n": pos += 1
		m = GUARD_RE.match(body, pos)
		if not m: break
		guards.append((" ".join(m.group("cond").split()), m.group("val")))
		pos = m.end()
	return guards


def py_cond(cond, rename, arrays=()):
	"""'!ent || !ent->client' -> 'not ent or not ent.client'; None if a name isn't a parameter."""
	parts = []
	for term in cond.split("||"):
		t = term.strip()
		m = re.fullmatch(r"!\s*\(?([A-Za-z_][\w>.\-]*)\)?", t) or re.fullmatch(r"\(?([A-Za-z_][\w>.\-]*)\s*==\s*NULL\)?", t)
		if not m: return None
		expr = m.group(1).replace("->", ".")
		root = re.match(r"\w+", expr).group(0)
		if root not in rename: return None
		if expr == root and root in arrays:
			parts.append(rename[root] + " is None")
			continue
		expr = rename[root] + expr[len(root):]
		parts.append("not " + expr)
	return " or ".join(parts)


def terms_of(expr):
	"""The 'or' terms of a condition, without the brackets ast.unparse adds."""
	return set(re.sub(r"^\((.*)\)$", r"\1", t.strip()) for t in expr.split(" or "))


def is_init(s):
	"""A local variable set to a constant or a new zeroed array."""
	if not isinstance(s, ast.Assign) or not all(isinstance(t, (ast.Name, ast.Tuple)) for t in s.targets): return False
	v = s.value
	if isinstance(v, ast.Constant): return True
	if isinstance(v, ast.UnaryOp) and isinstance(v.operand, ast.Constant): return True
	u = ast.unparse(v)
	return u.startswith(("np.zeros", "bytearray(", "[None]", "[0]", "[]")) or isinstance(v, ast.Tuple) and all(isinstance(e, ast.Constant) for e in v.elts)


def py_value(val):
	if val is None: return ""
	v = val.strip()
	return " " + {"false": "False", "true": "True", "NULL": "None"}.get(v, v)


def dedupe(mod, dry):
	"""Remove leading 'if <test>: return [v]' checks that an earlier leading check already covers."""
	src = open(mod).read()
	tree = ast.parse(src)
	lines = src.splitlines(keepends=True)
	n = 0
	for st in tree.body:
		if not isinstance(st, ast.FunctionDef): continue
		seen = []	# (terms, return value)
		for s in st.body:
			if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant): continue
			if isinstance(s, ast.Global) or is_init(s): continue
			if not (isinstance(s, ast.If) and not s.orelse and len(s.body) == 1 and isinstance(s.body[0], ast.Return)): break
			tt = terms_of(ast.unparse(s.test))
			rv = ast.unparse(s.body[0].value) if s.body[0].value else ""
			if any(tt <= t and rv == v for t, v in seen):
				for i in range(s.lineno - 1, s.end_lineno): lines[i] = ""
				j = s.end_lineno
				while j < len(lines) and not lines[j].strip() and j < s.end_lineno + 2:
					lines[j] = ""; j += 1
				n += 1
				print("%s: removed duplicate check '%s'" % (st.name, ast.unparse(s.test)))
				continue
			seen.append((tt, rv))
	if n and not dry:
		open(mod, "w").write("".join(lines))


def main(argv):
	dry = "--dry-run" in argv
	argv = [a for a in argv if a != "--dry-run"]
	if argv[0] == "--dedupe":
		for m in argv[1:]: dedupe(m, dry)
		return
	mod, cpath = argv[0], argv[1]
	src = open(mod).read()
	cfun = c_functions(open(os.path.join(YQ, cpath), errors="replace").read())
	tree = ast.parse(src)
	lines = src.splitlines(keepends=True)
	inserts = []	# (line index, text)
	for st in tree.body:
		if not isinstance(st, ast.FunctionDef) or st.name not in cfun: continue
		cparams, body, arrays = cfun[st.name]
		guards = leading_guards(body)
		if not guards: continue
		pyparams = [a.arg for a in st.args.args]
		rename = dict(zip(cparams, pyparams))
		# first real statement (skip string expressions: banners, C locals; and global lines)
		body_st = [s for s in st.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
		while body_st and isinstance(body_st[0], ast.Global): body_st.pop(0)
		if not body_st: continue
		first = body_st[0]
		indent = re.match(r"[ \t]*", lines[first.lineno - 1]).group(0)
		# the port's own leading "if <test>: return [value]" checks
		old_checks = []
		for s in body_st:
			if isinstance(s, ast.If) and not s.orelse and len(s.body) == 1 and isinstance(s.body[0], ast.Return):
				old_checks.append(s)
			elif is_init(s):
				continue	# C local initialisers ("ent = None", "v = np.zeros(...)") may come first
			else:
				break
		text, terms = "", set()
		for cond, val in guards:
			pc = py_cond(cond, rename, arrays)
			if pc is None:
				print("%s: guard '%s' not translated (names aren't parameters); stopping there" % (st.name, cond))
				break
			text += "%sif %s:\n\n%s\treturn%s\n\n\n" % (indent, pc, indent, py_value(val))
			terms.update(terms_of(pc))
		if not text: continue
		# already guarded exactly like Yamagi?
		have = set()
		for s in old_checks:
			have |= terms_of(ast.unparse(s.test))
			if have == terms: break
		if have == terms:
			continue
		# drop the port's leading checks that the new guard covers
		drop = []
		for s in old_checks:
			tt = terms_of(ast.unparse(s.test))
			if tt <= terms: drop.append(s)
			else: break
		for s in drop:
			for i in range(s.lineno - 1, s.end_lineno):
				lines[i] = ""
			# and the blank line after it
			if s.end_lineno < len(lines) and not lines[s.end_lineno].strip(): lines[s.end_lineno] = ""
		inserts.append((first.lineno - 1, text, st.name))
	for ln, text, name in sorted(inserts, reverse=True):
		lines.insert(ln, text)
		print("%s: added guard" % name)
	if not dry and inserts:
		open(mod, "w").write("".join(lines))


if __name__ == "__main__":
	main(sys.argv[1:])
