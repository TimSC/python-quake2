"""
Bring a moved Python module into line with the Yamagi .c file it mirrors:

 - the ported functions (defs) are put in Yamagi's function order;
 - each Yamagi function that isn't ported yet is added as Yamagi's C, in a
   triple-quoted block of its own (banner comment through the closing brace);
 - id's C blocks of functions are removed: a function that Yamagi still has is
   now either a def or a block of Yamagi's C, and one that Yamagi dropped is gone;
 - everything else stays with the def that follows it (globals, classes,
   non-function C such as typedefs), and defs Yamagi doesn't have (port-only
   helpers) stay right after the def they followed.

usage: yq_sync.py <module.py> [<yamagi .c under yquake2/src>] [--head] [--dry-run]
--head: also use Yamagi's file comment as the docstring, and its #include lines in
place of id's file comment and #include text after the imports.
The Yamagi file defaults to the module's own path with .c.
The bodies of ported functions are not changed: compare them with
"yq_diff.py <function>" and port them by hand.
"""
from __future__ import annotations

import os
import re
import sys
import ast

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yq_index as yi


def blank_comments_strings(s: str) -> str:
	"""Same length and line structure, with comments, strings and char literals blanked."""
	out = []; i = 0; n = len(s)
	while i < n:
		c = s[i]
		if s.startswith("/*", i):
			j = s.find("*/", i + 2); j = n if j < 0 else j + 2
			out.append(re.sub(r'[^\n]', ' ', s[i:j])); i = j
		elif s.startswith("//", i):
			j = s.find("\n", i); j = n if j < 0 else j
			out.append(" " * (j - i)); i = j
		elif c in "\"'":
			j = i + 1
			while j < n and s[j] != c and s[j] != "\n":
				j += 2 if s[j] == "\\" else 1
			j = min(j + 1, n)
			out.append(c + " " * (j - i - 2) + (c if j - i >= 2 else "")); i = j
		else:
			out.append(c); i += 1
	return "".join(out)


def c_units(path):
	"""The functions of a C file in order: (name, text) where text is the banner comment and the function."""
	raw = open(path, errors="replace").read()
	bl = blank_comments_strings(raw)
	# preprocessor lines are blanked too (an #if 0 block may hide a function)
	bl = re.sub(r'(?m)^[ \t]*#(?:[^\n]*\\\n)*[^\n]*$', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), bl)
	out = []; prev_end = 0
	for name, a, b, body in yi.c_functions(bl):
		# banner: comment lines directly above the function (blank lines allowed between)
		start = a
		k = raw.rfind("\n", 0, a)
		lines_above = raw[prev_end:a].split("\n")
		keep = []
		for line in reversed(lines_above[:-1] if lines_above and lines_above[-1].strip() == "" else lines_above):
			t = line.strip()
			if t.startswith(("/*", "*", "//")) or t.endswith("*/") or (keep and t == ""):
				keep.append(line)
			else:
				break
		while keep and keep[-1].strip() == "": keep.pop()
		banner = "\n".join(reversed(keep))
		# a block comment cut in the middle (we went up only through comment-looking lines): make sure it opens
		if banner and "/*" not in banner.split("\n")[0] and not banner.lstrip().startswith("//"):
			banner = ""
		out.append((name, (banner + "\n" if banner else "") + raw[a:b].rstrip() + "\n"))
		prev_end = b
	return out


PP_LINE = re.compile(r'(?m)^[ \t]*#(?:[^\n]*\\\n)*[^\n]*$')


def yamagi_head(path):
	"""Yamagi's file comment as docstring text, and its #include lines (with their #if guards) as C text."""
	raw = open(path, errors="replace").read()
	doc = ""
	m = re.match(r'\s*/\*(.*?)\*/', raw, re.S)
	if m:
		lines = [re.sub(r'^ ?\* ?', '', l) for l in m.group(1).split("\n")]
		doc = "\n".join(l.rstrip() for l in lines).strip("\n") + "\n"
	bl = PP_LINE.sub(lambda m: re.sub(r'[^\n]', ' ', m.group(0)), blank_comments_strings(raw))
	first = yi.c_functions(bl)
	end = first[0][1] if first else len(raw)
	# #include lines, with the conditionals around them; conditionals that hold no #include are dropped
	def block(lines, k):
		"""Parse from k to the matching #else/#elif/#endif: (kept lines, next index, has include)."""
		out = []; has = False
		while k < len(lines):
			t = lines[k].strip()
			if re.match(r'#\s*(if|ifdef|ifndef)\b', t):
				head = lines[k]; k += 1
				parts = []; any_inc = False
				while True:
					sub, k, h = block(lines, k)
					parts.append(sub); any_inc |= h
					if k >= len(lines): break
					t2 = lines[k].strip()
					if re.match(r'#\s*endif\b', t2):
						parts.append([lines[k]]); k += 1; break
					parts.append([lines[k]]); k += 1	# #else / #elif
				if any_inc and not re.match(r'#\s*ifndef\s+\w+_H\b', head.strip()):
					out.append(head); [out.extend(p) for p in parts]; has = True
				elif any_inc:	# an include guard: keep what's inside only
					[out.extend(p) for p in parts[:-1]]; has = True
			elif re.match(r'#\s*(else|elif|endif)\b', t):
				return out, k, has
			elif re.match(r'#\s*include\b', t):
				out.append(lines[k]); has = True; k += 1
			else:
				k += 1
		return out, k, has
	pp = [l.rstrip() for l in raw[:end].split("\n") if l.strip().startswith("#")]
	inc, k, has = block(pp, 0)
	inc = [l for l in inc if not re.match(r'#\s*(else|elif)\b', l.strip()) or True]
	return doc, "\n".join(inc)


def c_block_functions(text):
	"""Names of the C functions defined in a block of C text."""
	bl = blank_comments_strings(text)
	bl = re.sub(r'(?m)^[ \t]*#.*$', '', bl)
	return [n for n, a, b, body in yi.c_functions(bl)]


def is_banner_text(text):
	"""Whether a statement's source is just a short banner string (the one right before a def)."""
	try:
		v = ast.literal_eval(text.strip())
	except (ValueError, SyntaxError):
		return False
	return isinstance(v, str) and is_banner(v)


def is_banner(s):
	return bool(re.match(r'^\s*=+\s*\n\s*\w+.*\n\s*=+\s*$', s)) or len(s.strip().split("\n")) <= 3 and not c_block_functions(s)


def c_text_block(ctext):
	"""C text as a triple-quoted Python string, kept verbatim (a raw string when it has backslashes)."""
	ctext = ctext.replace('"""', "'''")
	if ctext.rstrip().endswith("\\"):
		ctext += " "
	return ("r" if "\\" in ctext else "") + '"""\n' + ctext + '"""\n\n'


def sync(py_path, yq_c, dry=False, head=False):
	src = open(py_path).read()
	tree = ast.parse(src)
	lines = src.splitlines(keepends=True)
	starts = [0]
	for l in lines: starts.append(starts[-1] + len(l))
	def off(lineno): return starts[lineno - 1]
	body = tree.body
	# preamble: docstring, imports, and the leading C text block (file comment, #includes)
	i = 0
	# (imports, 'pass' lines and text blocks that hold no C function, up to the first other statement)
	while i < len(body) and (isinstance(body[i], (ast.Import, ast.ImportFrom, ast.Pass)) or
			(isinstance(body[i], ast.Expr) and isinstance(body[i].value, ast.Constant) and isinstance(body[i].value.value, str) and
			 not c_block_functions(body[i].value.value))):
		i += 1
	# but a text block right before the first statement is that statement's banner
	while i > 0 and isinstance(body[i - 1], ast.Expr) and i - 1 > 0 and \
			not any(isinstance(x, (ast.Import, ast.ImportFrom)) for x in body[i - 1:i]) and \
			any(isinstance(x, (ast.Import, ast.ImportFrom)) for x in body[:i - 1]) and \
			not isinstance(body[i - 2], ast.Expr) and is_banner(body[i - 1].value.value):
		i -= 1
	pre_end = off(body[i].lineno) if i < len(body) else len(src)
	preamble = src[:pre_end]
	if head:
		# Yamagi's file comment replaces the docstring; its #includes replace id's file comment and #include text
		doc, inc = yamagi_head(os.path.join(yi.YQ, yq_c))
		parts = []
		for st in body[:i]:
			if isinstance(st, ast.Pass):
				continue
			if isinstance(st, ast.Expr):
				if st is body[0]:
					parts.append('"""\n' + (doc or st.value.value.strip("\n") + "\n").replace('"""', "'''") + '"""\n')
				continue
			parts.append(src[off(st.lineno):off(st.end_lineno + 1) if st.end_lineno < len(lines) else len(src)])
		text = "".join(parts).replace("from __future__ import annotations\n", "from __future__ import annotations\n\n", 1)
		last = body[i - 1] if i > 0 else None
		tail = src[off(last.end_lineno + 1) if last is not None and last.end_lineno < len(lines) else pre_end:pre_end]
		preamble = text + ('\n"""\n' + inc + '\n"""\n' if inc else "") + tail	# tail: comments before the first statement
	# units: text of each remaining statement with the blank lines before it
	units = []
	for k in range(i, len(body)):
		st = body[k]
		a = off(st.lineno) if k > i else pre_end
		b = off(body[k + 1].lineno) if k + 1 < len(body) else len(src)
		text = src[a:b]
		if isinstance(st, ast.FunctionDef):
			units.append(["def", st.name, text])
		elif isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
			fns = c_block_functions(st.value.value)
			units.append(["cblock", fns, text] if fns else ["text", None, text])
		else:
			units.append(["other", None, text])
	yq = c_units(os.path.join(yi.YQ, yq_c))
	yq_names = [n for n, t in yq]
	yq_set = set(yq_names)
	# group: leading non-def units travel with the def that follows; a banner string right before a def is part of it
	groups = []	# [name or None, [texts]]
	pending = []
	lead = []; lead_done = False
	notes = []
	for kind, name, text in units:
		if kind == "def":
			if not groups and not lead_done:
				# what comes before the first def (types, globals) stays at the top
				lead.extend(p for p in pending if not p.strip().startswith(('"""', "r\"\"\"")) or not is_banner_text(p))
				pending = [p for p in pending if p.strip().startswith(('"""', "r\"\"\"")) and is_banner_text(p)]
				lead_done = True
			groups.append([name, pending + [text]]); pending = []
		elif kind == "cblock":
			gone = [f for f in name if f not in yq_set]
			if gone: notes.append("dropped id C of %s (not in Yamagi's %s)" % (", ".join(gone), yq_c))
			# keep the non-function part of the block? only if it has more than the functions: report it
			pending = [p for p in pending if not (is_banner(ast.literal_eval(p.strip())) if p.strip().startswith('"""') else False)]
		else:
			pending.append(text)
	tail = pending
	have = {g[0] for g in groups}
	# order: Yamagi's functions; port-only defs stay after the def they followed
	by_name = {g[0]: g for g in groups}
	follow = {}	# yamagi-def name -> [port-only groups after it]
	last = None; head_only = []
	for g in groups:
		if g[0] in yq_set:
			last = g[0]
		else:
			(follow.setdefault(last, []) if last else head_only).append(g)
	out = [preamble.rstrip("\n") + "\n\n"] + lead
	for g in head_only: out.append("".join(g[1]))
	added = 0
	emitted = set()
	for name, ctext in yq:
		if name in by_name and name not in emitted:
			out.append("".join(by_name[name][1]))
			emitted.add(name)
			for g in follow.get(name, []): out.append("".join(g[1]))
		else:
			# not ported, or a second variant of a ported function (#ifdef'd): Yamagi's C
			out.append(c_text_block(ctext)); added += 1
	out.append("".join(tail))
	text = "".join(out)
	text = re.sub(r'\n{4,}', '\n\n\n', text)
	compile(text, py_path, "exec")
	old_order = [g[0] for g in groups if g[0] in yq_set]
	new_order = [n for n in yq_names if n in have]
	print("%s: %d defs (%d port-only), %d Yamagi functions added as C, order %s" % (
		py_path, len(groups), len(groups) - len(old_order), added, "unchanged" if old_order == new_order else "changed"))
	for n in notes: print("  note:", n)
	if not dry:
		open(py_path, "w").write(text)


if __name__ == "__main__":
	args = [a for a in sys.argv[1:] if not a.startswith("--")]
	py = args[0]
	c = args[1] if len(args) > 1 else os.path.relpath(os.path.join(yi.ROOT, py), yi.ROOT)[:-3] + ".c"
	sync(os.path.join(yi.ROOT, py), c, "--dry-run" in sys.argv, "--head" in sys.argv)
