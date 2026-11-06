"""
Move Python modules and symbols to their Yamagi Quake II locations and rewrite
every import and reference in the tree to match.

A move plan is a Python file defining:

  RENAMES = {"old/path.py": "new/path.py", ...}
      whole modules moving to a new place

  SPLITS = {"old/path.py": {"default": "new/path.py",
                            "symbols": {"Name": "other/path.py", ...}}, ...}
      modules whose top-level symbols go to several files; symbols not
      listed go to "default"

usage:
  yq_move.py <plan.py> [--dry-run]

Every top-level statement of a split module goes with the symbol it defines.
Strings (banners, unported C) go with the next definition. Imports are copied
to every new module. References to moved symbols are rewritten everywhere,
also inside the moved code, and assignments through "global" to symbols now
in another module become attribute assignments on that module.

See docs/yquake2_plan.md.
"""
from __future__ import annotations

import os
import re
import ast
import sys
import shutil
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES = ("game", "server", "client", "qcommon", "ref_gl", "linux", "common", "backends")


def mod_of(path):	# "client/cl_main.py" -> "client.cl_main"
	return path[:-3].replace("/", ".")


def path_of(mod):
	return mod.replace(".", "/") + ".py"


def scope_files():
	out = []
	for dp, dn, fs in os.walk(ROOT):
		rel = os.path.relpath(dp, ROOT)
		top = rel.split("/")[0]
		if rel != "." and top not in PACKAGES + ("tests", "scripts"):
			dn[:] = []; continue
		if rel == ".":
			dn[:] = [d for d in dn if d in PACKAGES + ("tests", "scripts")]
		for f in fs:
			if f.endswith(".py"):
				out.append(os.path.normpath(os.path.join(rel, f)) if rel != "." else f)
	return sorted(out)


# --------------------------------------------------------------- text edits
class Edits:
	def __init__(self, src):
		self.src = src
		self.lines = src.splitlines(keepends=True)
		self.starts = [0]
		for l in self.lines:
			self.starts.append(self.starts[-1] + len(l))
		self.edits = []

	def off(self, lineno, col):	# ast col offsets are utf-8 byte offsets
		line = self.lines[lineno - 1]
		return self.starts[lineno - 1] + len(line.encode("utf-8")[:col].decode("utf-8", errors="ignore"))

	def replace(self, node, text):
		self.edits.append((self.off(node.lineno, node.col_offset), self.off(node.end_lineno, node.end_col_offset), text))

	def replace_span(self, a, b, text):
		self.edits.append((a, b, text))

	def apply(self):
		out = self.src
		for a, b, t in sorted(set(self.edits), key=lambda e: (e[0], e[1]), reverse=True):
			out = out[:a] + t + out[b:]
		return out


# --------------------------------------------------------------- scopes
def bound_names(fn):
	"""Names bound locally in a function (params, assignments, loops, imports, except/with targets)."""
	names = set()
	a = fn.args
	for x in a.args + a.kwonlyargs + getattr(a, "posonlyargs", []):
		names.add(x.arg)
	if a.vararg: names.add(a.vararg.arg)
	if a.kwarg: names.add(a.kwarg.arg)
	globs = set()
	for n in ast.walk(fn):
		if isinstance(n, ast.Global): globs |= set(n.names)
	for n in ast.walk(fn):
		if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)): names.add(n.id)
		elif isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n is not fn: names.add(n.name)
		elif isinstance(n, ast.ExceptHandler) and n.name: names.add(n.name)
		elif isinstance(n, (ast.Import, ast.ImportFrom)):
			for x in n.names: names.add((x.asname or x.name).split(".")[0])
		elif isinstance(n, ast.arg): names.add(n.arg)
	return names - globs, globs


def parents(tree):
	p = {}
	for n in ast.walk(tree):
		for c in ast.iter_child_nodes(n):
			p[c] = n
	return p


def enclosing_functions(node, par):
	out = []
	while node in par:
		node = par[node]
		if isinstance(node, (ast.FunctionDef, ast.Lambda, ast.AsyncFunctionDef)):
			out.append(node)
	return out


# --------------------------------------------------------------- the plan
class Plan:
	def __init__(self, renames, splits):
		renames = {o: n for o, n in renames.items() if o != n}	# a module that keeps its path isn't moved
		self.renames = renames
		self.splits = splits
		self.owner = {}		# (old_mod, symbol) -> new_mod
		self.whole = {}		# old_mod -> new_mod for whole renames
		for old, new in renames.items():
			self.whole[mod_of(old)] = mod_of(new)
		for old, spec in splits.items():
			om = mod_of(old)
			for sym, new in spec.get("symbols", {}).items():
				self.owner[(om, sym)] = mod_of(new)
			self.whole[om] = None	# split
		self.split_default = {mod_of(o): mod_of(s["default"]) for o, s in splits.items()}

	def target(self, old_mod, sym=None):
		"""Where old_mod.sym lives after the move (old_mod itself if not moved)."""
		if old_mod in self.whole and self.whole[old_mod]:
			return self.whole[old_mod]
		if old_mod in self.split_default:
			return self.owner.get((old_mod, sym), self.split_default[old_mod])
		return old_mod

	def moved(self, old_mod):
		return old_mod in self.whole


# --------------------------------------------------------------- splitting
def split_module(path, spec, plan):
	"""Return {new_mod: source} for a split module (before reference rewriting)."""
	src = open(os.path.join(ROOT, path)).read()
	tree = ast.parse(src)
	ed = Edits(src)
	om = mod_of(path)
	body = tree.body
	# header: leading docstring and __future__ import
	head_end = 0; header = []
	for st in body:
		if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str) and not header) or \
		   (isinstance(st, ast.ImportFrom) and st.module == "__future__"):
			header.append(st); head_end = ed.off(st.end_lineno, st.end_col_offset)
		else:
			break
	header_text = src[:head_end].rstrip("\n") + "\n"
	imports = [st for st in body if isinstance(st, (ast.Import, ast.ImportFrom)) and st not in header]
	import_text = "".join(src[ed.off(st.lineno, 0):ed.off(st.end_lineno, st.end_col_offset)] + "\n" for st in imports)
	# owner of each remaining statement
	def stmt_symbols(st):
		if isinstance(st, (ast.FunctionDef, ast.ClassDef)): return [st.name]
		if isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
			ts = st.targets if isinstance(st, ast.Assign) else [st.target]
			return [x.id for t in ts for x in ast.walk(t) if isinstance(x, ast.Name)]
		return []
	rest = [st for st in body if st not in header and st not in imports]
	owners = []
	pending = []	# strings/other statements waiting for the next definition
	last = None
	for st in rest:
		syms = stmt_symbols(st)
		if syms:
			tgt = plan.target(om, syms[0])
			for p in pending: owners.append((p, tgt))
			pending = []
			owners.append((st, tgt)); last = tgt
		elif isinstance(st, (ast.For, ast.If, ast.With, ast.Try)) and last is not None:
			owners.append((st, last))	# e.g. a loop filling the table defined just before
		else:
			pending.append(st)
	for p in pending:
		owners.append((p, last or plan.split_default[om]))
	# text of each statement, including the blank/comment lines before it
	starts = [ed.off(st.lineno, 0) for st, _ in owners]
	prev_end = head_end
	chunks = collections.OrderedDict()
	ends_sorted = []
	last_tgt = None
	import_ends = sorted(ed.off(st.end_lineno, st.end_col_offset) for st in imports)
	for st, tgt in owners:
		a = ed.off(st.lineno, 0)
		# take comment lines directly above the statement (but not import lines, copied into every part)
		prev_end = max([prev_end] + [e for e in import_ends if e <= a])
		pre = src[prev_end:a]
		b = ed.off(st.end_lineno, st.end_col_offset)
		eol = src.find("\n", b)
		if eol >= 0 and src[b:eol].strip().startswith("#"): b = eol	# keep a trailing comment on the last line
		first = tgt not in chunks
		if not first and last_tgt != tgt and not pre.startswith("\n\n"):
			pre = "\n" + pre	# a blank line where statements that went elsewhere were cut out
		chunks.setdefault(tgt, []).append((pre.lstrip("\n") if first else pre) + src[a:b])	# pre starts with the newline ending the statement before
		last_tgt = tgt
		prev_end = b
	out = {}
	for tgt, parts in chunks.items():
		out[tgt] = header_text + "\n" + import_text + "\n" + "".join(parts) + "\n"	# the original spacing between statements
	# make sure the default exists even if everything moved away
	out.setdefault(plan.split_default[om], header_text + "\n" + import_text)
	return out


# --------------------------------------------------------------- rewriting references
def local_name_for(new_mod, taken, prefer=None):
	base = new_mod.split(".")[-1]
	cands = [prefer] if prefer else []
	cands += [base]
	parent = new_mod.split(".")[-2] if "." in new_mod else ""
	if parent == "header": cands.append(base + "_h")
	cands.append(parent + "_" + base)
	for c in cands:
		if c and c not in taken:
			return c
	i = 2
	while base + str(i) in taken: i += 1
	return base + str(i)


def rewrite_file(path, src, plan, self_mod=None, self_old=None, own_mod=None):
	"""Rewrite imports and references in one file. self_mod/self_old: for code moved out of a split module,
	the new module the code lives in and the module it came from."""
	tree = ast.parse(src)
	par = parents(tree)
	ed = Edits(src)
	# names bound anywhere in the file (to avoid clashes when choosing local names)
	all_bound = set()
	for n in ast.walk(tree):
		if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store): all_bound.add(n.id)
		elif isinstance(n, (ast.FunctionDef, ast.ClassDef)): all_bound.add(n.name)
		elif isinstance(n, ast.arg): all_bound.add(n.arg)
		elif isinstance(n, ast.ExceptHandler) and n.name: all_bound.add(n.name)
		elif isinstance(n, (ast.Import, ast.ImportFrom)):
			for a in n.names: all_bound.add((a.asname or a.name).split(".")[0])
	notes = []

	# --- collect module imports:  local name -> old module
	mod_alias = {}		# local name -> old module (moved)
	sym_imports = []	# (node, old module, [(name, asname)])
	import_nodes = []
	for n in ast.walk(tree):
		if isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
			# from pkg import mod
			for a in n.names:
				full = n.module + "." + a.name
				if plan.moved(full):
					mod_alias.setdefault(a.asname or a.name, full)
			if plan.moved(n.module):
				sym_imports.append(n)
			if any(plan.moved(n.module + "." + a.name) for a in n.names) or plan.moved(n.module):
				import_nodes.append(n)
		elif isinstance(n, ast.Import):
			for a in n.names:
				if plan.moved(a.name):
					import_nodes.append(n)

	# --- references through module aliases:  alias.sym
	needed = {}		# new module -> local name
	taken = set(all_bound) - set(mod_alias)
	def local_for(new_mod, old_alias=None):
		if new_mod in needed: return needed[new_mod]
		nm = local_name_for(new_mod, taken | set(needed.values()))
		needed[new_mod] = nm
		return nm

	for n in ast.walk(tree):
		if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in mod_alias:
			alias = n.value.id
			shadow = False
			for fn in enclosing_functions(n, par):
				if isinstance(fn, ast.Lambda):
					if alias in {a.arg for a in fn.args.args}: shadow = True
					continue
				b, g = bound_names(fn)
				if alias in b: shadow = True; break
			if shadow: continue
			new_mod = plan.target(mod_alias[alias], n.attr)
			if new_mod == own_mod and isinstance(n.ctx, ast.Load) and not any(
					not isinstance(fn, ast.Lambda) and n.attr in bound_names(fn)[0] for fn in enclosing_functions(n, par)):
				ed.replace(n, n.attr)	# the symbol now lives in this module
				continue
			ed.replace(n.value, local_for(new_mod))
		elif isinstance(n, ast.Name) and n.id in mod_alias and isinstance(n.ctx, ast.Load):
			p = par.get(n)
			if isinstance(p, ast.Attribute) and p.value is n: continue
			# bare use of a module object: keep a binding under its old name
			shadow = any(not isinstance(fn, ast.Lambda) and n.id in bound_names(fn)[0] for fn in enclosing_functions(n, par))
			if not shadow:
				notes.append("%s:%d bare module reference %s" % (path, n.lineno, n.id))
				old = mod_alias[n.id]
				if plan.whole.get(old):
					needed.setdefault(plan.whole[old], n.id)

	# --- symbol imports: from old.mod import a, b
	sym_lines = collections.defaultdict(list)	# (indent, node) -> list of import lines
	for n in sym_imports:
		groups = collections.OrderedDict()
		for a in n.names:
			tgt = plan.target(n.module, a.name)
			groups.setdefault(tgt, []).append(a.name + (" as " + a.asname if a.asname else ""))
		indent = " " * 0
		lines = []
		for tgt, names in groups.items():
			if tgt == own_mod:
				continue	# the names are defined in this module now
			lines.append("from %s import %s" % (tgt, ", ".join(names)))
		sym_lines[n] = lines

	# --- code moved out of a split module: unqualified references to symbols now elsewhere
	if self_mod and self_old:
		here = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
		for st in tree.body:
			if isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
				ts = st.targets if isinstance(st, ast.Assign) else [st.target]
				here |= {x.id for t in ts for x in ast.walk(t) if isinstance(x, ast.Name)}
		for fn in [x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef)]:
			b, globs = bound_names(fn)
			moved_globs = {g for g in globs if g not in here and plan.target(self_old, g) != self_mod}
			for x in ast.walk(fn):
				if isinstance(x, ast.Global):
					keep = [g for g in x.names if g not in moved_globs]
					if keep != x.names:
						ed.replace(x, ("global " + ", ".join(keep)) if keep else "pass")
				if isinstance(x, ast.Name) and x.id not in b and x.id not in here:
					tgt = plan.target(self_old, x.id)
					if tgt != self_mod and (x.id in moved_globs or is_symbol_of(self_old, x.id)):
						ed.replace(x, local_for(tgt) + "." + x.id)
		for x in ast.walk(tree):
			if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and x.id not in here and not enclosing_functions(x, par):
				tgt = plan.target(self_old, x.id)
				if tgt != self_mod and is_symbol_of(self_old, x.id):
					ed.replace(x, local_for(tgt) + "." + x.id)

	# --- rewrite the import statements
	for n in import_nodes:
		indent = src.splitlines()[n.lineno - 1][:n.col_offset]
		new_lines = []
		if enclosing_functions(n, par) and isinstance(n, ast.ImportFrom) and n not in sym_lines:
			# an import inside a function (usually to break an import cycle): rewrite it in
			# place under the same local name, so the function body is unchanged
			for a in n.names:
				full = n.module + "." + a.name
				local = a.asname or a.name
				if plan.moved(full):
					tgt = plan.whole.get(full) or plan.split_default[full]
					pkg, _, base = tgt.rpartition(".")
					new_lines.append("from %s import %s" % (pkg, base) + ("" if base == local else " as " + local))
				else:
					new_lines.append("from %s import %s" % (n.module, a.name) + (" as " + a.asname if a.asname else ""))
			ed.replace(n, ("\n" + indent).join(new_lines))
			continue
		if isinstance(n, ast.ImportFrom):
			if n in sym_lines:
				new_lines += sym_lines[n]
			else:
				keep = []; drop = []
				for a in n.names:
					full = n.module + "." + a.name
					if plan.moved(full) and not (full in plan.split_default and plan.split_default[full] == full):
						drop.append(a)
					else: keep.append(a.name + (" as " + a.asname if a.asname else ""))	# (a split module that keeps its path stays)
				if keep:
					new_lines.append("from %s import %s" % (n.module, ", ".join(keep)))
				for a in drop:
					local = a.asname or a.name
					full = n.module + "." + a.name
					if plan.whole.get(full) and local in [v for k, v in needed.items() if k == plan.whole[full]]:
						pass	# re-imported below under its chosen name
		else:
			for a in n.names:
				if plan.moved(a.name) and plan.whole.get(a.name):
					new_lines.append("import %s" % plan.whole[a.name] + (" as " + a.asname if a.asname else ""))
				else:
					new_lines.append("import %s" % a.name + (" as " + a.asname if a.asname else ""))
		ed.replace(n, ("\n" + indent).join(new_lines) if new_lines else "pass")

	# --- add imports for the new modules used
	if own_mod in needed:
		del needed[own_mod]	# qualified uses that must stay qualified get a self-import below
		self_refs = True
	if needed:
		add = []
		for new_mod, local in sorted(needed.items()):
			pkg, _, base = new_mod.rpartition(".")
			if local == base:
				add.append("from %s import %s" % (pkg, base) if pkg else "import %s" % base)
			else:
				add.append("from %s import %s as %s" % (pkg, base, local) if pkg else "import %s as %s" % (base, local))
		# insert after the last top-level import (or after the module docstring / __future__)
		pos_node = None
		for st in tree.body:
			if isinstance(st, (ast.FunctionDef, ast.ClassDef)): break	# only the imports at the top
			if isinstance(st, (ast.Import, ast.ImportFrom)): pos_node = st
		if pos_node is not None:
			at = ed.off(pos_node.end_lineno, pos_node.end_col_offset)
		else:
			at = 0
			for st in tree.body:
				if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant): at = ed.off(st.end_lineno, st.end_col_offset)
				else: break
		ed.replace_span(at, at, "\n" + "\n".join(add) + ("\n" if pos_node is None else ""))
	return ed.apply(), notes


def merge_parts(texts):
	"""Join module sources: the first keeps its docstring and __future__ import, later ones drop them."""
	out = [texts[0].rstrip("\n") + "\n"]
	for t in texts[1:]:
		tree = ast.parse(t)
		ed = Edits(t)
		cut = 0
		for st in tree.body:
			if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str) and cut == 0) or \
			   (isinstance(st, ast.ImportFrom) and st.module == "__future__"):
				cut = ed.off(st.end_lineno, st.end_col_offset)
			else:
				break
		out.append("\n" + t[cut:].strip("\n") + "\n")
	return "".join(out)


def prune_imports(src):
	"""Drop top-level imports whose names the module never uses (extra imports make extra import cycles)."""
	tree = ast.parse(src)
	used = set()
	for n in ast.walk(tree):
		if isinstance(n, ast.Name): used.add(n.id)
		elif isinstance(n, ast.Global): used |= set(n.names)
	ed = Edits(src)
	for st in tree.body:
		if isinstance(st, ast.ImportFrom) and st.module == "__future__": continue
		if not isinstance(st, (ast.Import, ast.ImportFrom)): continue
		keep = [a for a in st.names if (a.asname or a.name).split(".")[0] in used or a.name == "*"]
		if len(keep) == len(st.names): continue
		if not keep:
			a = ed.off(st.lineno, 0); b = ed.off(st.end_lineno, st.end_col_offset)
			if src[b:b + 1] == "\n": b += 1
			ed.replace_span(a, b, "")
		else:
			names = ", ".join(x.name + (" as " + x.asname if x.asname else "") for x in keep)
			ed.replace(st, ("from %s import %s" % (st.module, names)) if isinstance(st, ast.ImportFrom) else "import " + names)
	return ed.apply()


_SYMS = {}
def is_symbol_of(old_mod, name):
	"""Whether name is a top-level symbol of the (original) module old_mod."""
	return name in _SYMS.get(old_mod, ())


def toplevel_names(src):
	tree = ast.parse(src)
	names = set()
	for st in tree.body:
		if isinstance(st, (ast.FunctionDef, ast.ClassDef)): names.add(st.name)
		elif isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
			ts = st.targets if isinstance(st, ast.Assign) else [st.target]
			names |= {x.id for t in ts for x in ast.walk(t) if isinstance(x, ast.Name)}
		elif isinstance(st, (ast.For, ast.If, ast.With, ast.Try)):
			names |= {x.id for x in ast.walk(st) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store)}
	for n in ast.walk(tree):
		if isinstance(n, ast.Global): names |= set(n.names)
	return names


# --------------------------------------------------------------- driver
def run(plan_path, dry=False):
	ns = {}
	exec(open(plan_path).read(), ns)
	plan = Plan(ns.get("RENAMES", {}), ns.get("SPLITS", {}))
	files = scope_files()
	for old in list(plan.renames) + list(plan.splits):
		assert old in files, "not found: " + old
		_SYMS[mod_of(old)] = toplevel_names(open(os.path.join(ROOT, old)).read())
	new_sources = collections.defaultdict(list)	# new path -> [(source, self_mod, self_old)]
	for old, new in plan.renames.items():
		new_sources[new].append((open(os.path.join(ROOT, old)).read(), None, None))
	for old, spec in plan.splits.items():
		for nm, text in split_module(old, spec, plan).items():
			new_sources[path_of(nm)].append((text, nm, mod_of(old)))
	moved_away = set(plan.renames) | set(plan.splits)
	results = {}; notes = []
	for f in files:
		if f in moved_away: continue
		src = open(os.path.join(ROOT, f)).read()
		out, n = rewrite_file(f, src, plan, own_mod=mod_of(f))
		notes += n
		if f in new_sources:
			results[f] = out	# merged with the parts moving in, below
		elif out != src:
			results[f] = out
	for p, parts in new_sources.items():
		texts = [results[p]] if p in results else []
		for text, self_mod, self_old in parts:
			out, n = rewrite_file(p, text, plan, self_mod, self_old, own_mod=mod_of(p))
			notes += n
			if self_mod is not None:
				out = prune_imports(out)	# a split part gets all of the old module's imports
			texts.append(out)
		results[p] = merge_parts(texts)
	for p, text in results.items():
		compile(text, p, "exec")	# every result must be valid Python
	print("files rewritten: %d, new files: %d, removed: %d" % (len(results), len(new_sources), len(moved_away)))
	for n in notes: print("note:", n)
	if dry: return
	for p, text in results.items():
		os.makedirs(os.path.dirname(os.path.join(ROOT, p)) or ROOT, exist_ok=True)
		open(os.path.join(ROOT, p), "w").write(text)
	for old in moved_away:
		if old not in results:
			os.remove(os.path.join(ROOT, old))


if __name__ == "__main__":
	run(sys.argv[1], "--dry-run" in sys.argv)
