"""
Index the C sources of id's Quake II (quake2-original/) and Yamagi Quake II
(yquake2/src/), and map every top-level symbol of the Python port to the Yamagi
file it belongs in.

Used by the yquake2 branch tools (yq_map.py, yq_diff.py, yq_move.py). See
docs/yquake2_plan.md.
"""
from __future__ import annotations

import os
import re
import ast
import json
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YQ = os.path.join(ROOT, "yquake2", "src")
ID = os.path.join(ROOT, "quake2-original")

# Yamagi code that the port mirrors (see the plan's scope section)
YQ_SCOPE = [
	"common", "server", "game", "client",
	"backends/unix", "backends/generic",
]
YQ_SKIP = [
	"client/refresh/soft", "client/refresh/gl3", "client/refresh/vk", "client/curl",
	"client/refresh/gl1/glad-gles1", "common/unzip", "client/vid/glimp_sdl3.c",
	"client/input/sdl3.c", "client/sound/openal.c", "client/sound/qal.c",
	"client/refresh/files/stb_image.h", "client/refresh/files/stb_image_resize.h",
]

# Python package dirs of the port before the move, and the Yamagi dirs to search
# for their symbols, most likely first.
AREAS = {
	"game": ["game", "common/shared", "common/header"],
	"server": ["server", "common/header", "common"],
	"qcommon": ["common", "common/shared", "common/header"],
	"client": ["client/header", "client", "common/header"],
	"ref_gl": ["client/refresh/gl1", "client/refresh/files", "client/refresh", "client/vid/header"],
	"linux": ["client/vid", "client/input", "backends/unix", "backends/generic", "common", "client/sound", "client/menu", "client/refresh/gl1"],
}

KEYWORDS = {"if", "while", "for", "switch", "return", "sizeof", "else", "do", "case"}


def strip_comments(s: str) -> str:
	s = re.sub(r'/\*.*?\*/', lambda m: "\n" * m.group(0).count("\n"), s, flags=re.S)
	return re.sub(r'//[^\n]*', '', s)


def strip_strings(s: str) -> str:
	return re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', s)


FUNC = re.compile(r'^(?:static\s+|inline\s+|extern\s+|const\s+)*(?!(?:if|while|for|switch|return|else|do|typedef|struct|enum)\b)[A-Za-z_][\w \t\*]*?[\s\*](\w+)\s*\(([^;{}()]*(?:\([^()]*\)[^;{}()]*)*)\)\s*\{', re.M)


def c_functions(src: str):
	"""(name, start, end, body) of each function definition, in order."""
	out = []
	for m in FUNC.finditer(src):
		name = m.group(1)
		if name in KEYWORDS:
			continue
		i = m.end(); depth = 1
		while i < len(src) and depth:
			c = src[i]
			if c == "{": depth += 1
			elif c == "}": depth -= 1
			i += 1
		out.append((name, m.start(), i, src[m.end():i - 1]))
	return out


def depth0(src: str) -> str:
	"""The source with every {...} block replaced by {} (function bodies, struct bodies, initialisers)."""
	out = []; depth = 0
	for c in src:
		if c == "{":
			if depth == 0: out.append("{")
			depth += 1
		elif c == "}":
			depth = max(depth - 1, 0)
			if depth == 0: out.append("}")
		elif depth == 0:
			out.append(c)
	return "".join(out)


def c_symbols(path: str):
	"""Index one C file: functions (ordered), defines, typedefs/tags, enum members and variables."""
	raw = open(path, errors="replace").read()
	src = strip_strings(strip_comments(raw))
	sym = {"functions": [], "defines": [], "types": [], "enums": [], "vars": []}
	for name, a, b, body in c_functions(src):
		sym["functions"].append(name)
	for m in re.finditer(r'(?m)^[ \t]*#[ \t]*define[ \t]+(\w+)', src):
		sym["defines"].append(m.group(1))
	for m in re.finditer(r'\b(?:struct|union|enum)\s+(\w+)\s*\{', src):
		sym["types"].append(m.group(1))
	for m in re.finditer(r'\benum\s*\w*\s*\{([^}]*)\}', src, re.S):
		for e in m.group(1).split(","):
			e = e.split("=")[0].strip()
			if re.match(r'^\w+$', e): sym["enums"].append(e)
	d0 = re.sub(r'(?m)^[ \t]*#(?:[^\n]*\\\n)*[^\n]*$', '', src)	# preprocessor lines, with continuations
	d0 = re.sub(r'extern\s*""\s*\{', '', d0)	# C++ linkage blocks would hide the whole header
	d0 = depth0(d0)
	for st in d0.split(";"):
		st = " ".join(st.split())
		if not st: continue
		if st.startswith("typedef"):
			m = re.search(r'(\w+)\s*(?:\[[^\]]*\])*\s*$', re.sub(r'\([^()]*\)\s*$', '', st))
			fp = re.search(r'\(\s*\*\s*(\w+)\s*\)', st)
			if fp: sym["types"].append(fp.group(1))
			elif m: sym["types"].append(m.group(1))
			continue
		if st.startswith("extern") or "{}" in st and "=" not in st.split("{}")[0]:
			continue
		if re.search(r'\w\s*\([^)]*\)\s*$', st) and "=" not in st:
			continue	# prototype
		decl = st.split("=")[0]
		for part in decl.split(","):
			m = re.search(r'(\w+)\s*(?:\[[^\]]*\])*\s*$', part.strip())
			if m and m.group(1) not in ("void", "int", "float", "char", "const", "static", "unsigned"):
				sym["vars"].append(m.group(1))
	return sym


def walk_c(root: str, scope=None, skip=()):
	for dp, dn, fs in os.walk(root):
		rel_dir = os.path.relpath(dp, root)
		if any(rel_dir == s or rel_dir.startswith(s + "/") for s in skip if not s.endswith((".c", ".h"))):
			continue
		for f in sorted(fs):
			if not f.endswith((".c", ".h")): continue
			rel = os.path.normpath(os.path.join(rel_dir, f))
			if rel in skip: continue
			if scope and not any(rel == s or rel.startswith(s + "/") for s in scope): continue
			yield rel


def yq_py_path(rel: str) -> str:
	"""The Python file that mirrors a Yamagi file (path relative to yquake2/src)."""
	stem, ext = os.path.splitext(rel)
	if ext == ".h" and os.path.exists(os.path.join(YQ, stem + ".c")):
		return stem + "_h.py"	# a header next to a .c of the same name
	return stem + ".py"


def module_name(py_path: str) -> str:
	return py_path[:-3].replace("/", ".")


def build_yq_index():
	"""Per kind, symbol -> [Yamagi files], and the ordered function list of each file."""
	index = {k: collections.defaultdict(list) for k in ("functions", "defines", "types", "enums", "vars")}
	order = {}
	for rel in walk_c(YQ, YQ_SCOPE, YQ_SKIP):
		s = c_symbols(os.path.join(YQ, rel))
		order[rel] = s["functions"]	# headers are listed too, with no functions
		for k in index:
			for n in s[k]:
				if rel not in index[k][n]: index[k][n].append(rel)
	return index, order


def build_id_index():
	index = {k: collections.defaultdict(list) for k in ("functions", "defines", "types", "enums", "vars")}
	for rel in walk_c(ID):
		s = c_symbols(os.path.join(ID, rel))
		for k in index:
			for n in s[k]:
				index[k][n].append(rel)
	return index


def py_modules():
	"""The port's Python modules in scope, as repo-relative paths."""
	out = []
	for d in AREAS:
		for f in sorted(os.listdir(os.path.join(ROOT, d))):
			if f.endswith(".py"):
				out.append(d + "/" + f)
	return out


def is_alias(value, imported):
	"""A module-level assignment that only re-exports something imported (x = mod.y, x = Enum.X.value)."""
	while isinstance(value, ast.Attribute):
		value = value.value
	return isinstance(value, ast.Name) and value.id in imported


def py_imported_names(tree):
	names = set()
	for node in ast.walk(tree):
		if isinstance(node, (ast.Import, ast.ImportFrom)):
			for a in node.names:
				names.add((a.asname or a.name).split(".")[0])
	return names


def py_toplevel(path: str):
	"""Top-level symbols of a Python module in source order: (name, kind, lineno).
	kind is def, class, var or alias (a re-export of an imported name, which stays put)."""
	tree = ast.parse(open(os.path.join(ROOT, path)).read())
	imported = py_imported_names(tree)
	out = []; seen = set()
	def add(n, kind, line):
		if n not in seen:
			seen.add(n); out.append((n, kind, line))
	for node in tree.body:
		if isinstance(node, ast.FunctionDef): add(node.name, "def", node.lineno)
		elif isinstance(node, ast.ClassDef): add(node.name, "class", node.lineno)
		elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
			targets = node.targets if isinstance(node, ast.Assign) else [node.target]
			kind = "alias" if isinstance(node, ast.Assign) and is_alias(node.value, imported) else "var"
			for t in targets:
				for x in ast.walk(t):
					if isinstance(x, ast.Name): add(x.id, kind, node.lineno)
		elif isinstance(node, ast.For):
			# a loop filling a table: the loop variable is not a symbol of its own
			for x in ast.walk(node.target):
				if isinstance(x, ast.Name): add(x.id, "alias", node.lineno)
		elif isinstance(node, (ast.If, ast.With, ast.Try)):
			for x in ast.walk(node):
				if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store): add(x.id, "var", node.lineno)
	# names created with 'global' inside functions
	for node in ast.walk(tree):
		if isinstance(node, ast.Global):
			for n in node.names: add(n, "var", node.lineno)
	return out


def resolve(name, kind, area, yq, prefer=()):
	"""The Yamagi file a Python symbol belongs to, or None. prefer lists files tried first."""
	dirs = AREAS[area]
	for k in ("functions", "defines", "types", "enums", "vars"):
		for c in yq[k].get(name, []):
			if c in prefer:
				return c
	kinds = ["functions", "defines", "types", "enums", "vars"] if kind == "def" else ["types", "defines", "enums", "vars", "functions"]
	if kind == "var":
		kinds = ["vars", "defines", "enums", "types", "functions"]
		if name.isupper() or re.match(r'^[A-Z][A-Z0-9_]*$', name):
			kinds = ["defines", "enums", "vars", "types", "functions"]	# constants are #defines
	for k in kinds:
		cands = yq[k].get(name, [])
		if not cands: continue
		for d in dirs:
			for c in cands:
				if c == d or c.startswith(d + "/"):
					return c
		return cands[0]
	return None


def build_map():
	yq, order = build_yq_index()
	result = {}
	for mod in py_modules():
		area = mod.split("/")[0]
		syms = py_toplevel(mod)
		# default target: the file most of the module's functions (else symbols) go to
		c = collections.Counter(resolve(n, k, area, yq) for n, k, l in syms if k == "def")
		c.pop(None, None)
		if not c:
			c = collections.Counter(resolve(n, k, area, yq) for n, k, l in syms if k != "alias")
			c.pop(None, None)
		default = c.most_common(1)[0][0] if c else None
		prefer = []
		if default:
			stem = os.path.splitext(default)[0]
			updir = os.path.dirname(os.path.dirname(stem))
			prefer = [stem + ".h", os.path.join(updir, "header", os.path.basename(stem) + ".h"), default]
			prefer += [f for f in order if os.path.dirname(f) == os.path.dirname(default)]
			prefer += [os.path.dirname(stem) + "/header/" + h for h in ("local.h", os.path.basename(stem) + ".h")]
		entries = []
		for name, kind, line in syms:
			target = default if kind == "alias" else resolve(name, kind, area, yq, prefer)
			entries.append({"name": name, "kind": kind, "line": line, "yq": target})
		result[mod] = {"default": default, "symbols": entries}
	return result, order


if __name__ == "__main__":
	m, order = build_map()
	out = os.path.join(ROOT, "scripts", "yq_map.json")
	json.dump({"modules": m, "yq_order": order}, open(out, "w"), indent=1)
	print("wrote", out)
