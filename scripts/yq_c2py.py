"""
Translate simple Yamagi C functions into Python in the port's style, and
optionally replace the function (or its pasted C block) in a module.

usage: yq_c2py.py <module.py> <yamagi .c path under yquake2/src> <function> [...] [--write] [--show]

Handles Yamagi's layout (one statement per line, braces on their own lines):
if / else if / else, for loops of the form "for (i = a; i < b; i++)",
while, switch on integer cases, return, assignments, ++ / --, calls, and
local declarations (vec3_t locals become np.zeros arrays, others go into a
C-locals string). Names are resolved against the target module: a name the
module defines or imports is used as is; otherwise known engine globals get
their module prefix (g_main.gi, g_main.level, shared., local., ...).
Anything it can't resolve or translate is marked "# FIXME c2py".

The output still needs reading: C integer division, struct copies and
pointer arithmetic aren't detected.

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

FUNC_RE = re.compile(r"^((?:static\s+)?(?:const\s+)?[\w\s\*]+?)\s*\n([A-Za-z_]\w*)\(([^)]*)\)\s*\n\{\n(.*?)^\}\n", re.M | re.S)

G_MAIN = {"gi", "level", "game", "skill", "deathmatch", "coop", "dmflags", "g_edicts", "globals", "meansOfDeath",
	"maxclients", "sv_gravity", "g_monsterfootsteps", "g_footsteps", "g_fix_triggered", "sm_meat_index", "snd_fry",
	"st", "sv_maxvelocity", "g_commanderbody_nogod", "coop_elevator_delay", "aimfix", "sv_cheats"}
RENAME = {"globals": "glob", "NULL": "None", "true": "True", "false": "False", "randk": "rand.randk",
	"frandk": "rand.frandk", "crandk": "rand.crandk", "fabs": "abs", "fabsf": "abs", "sqrt": "math.sqrt", "atan2": "math.atan2",
	"M_PI": "math.pi", "floor": "math.floor", "ceil": "math.ceil", "world": "g_main.g_edicts[0]", "cos": "math.cos",
	"sin": "math.sin", "tan": "math.tan"}
TYPES = {"int", "float", "char", "qboolean", "double", "unsigned", "const", "static", "byte", "short", "long",
	"struct", "signed", "vec_t", "size_t", "void", "vec3_t", "edict_t", "trace_t", "gitem_t", "gclient_t", "mmove_t",
	"cvar_t", "cplane_t", "csurface_t"}
SEARCH = [("local", "game.header.local"), ("shared", "common.header.shared"), ("shared_c", "common.shared.shared"),
	("game_h", "game.header.game"), ("g_utils", "game.g_utils"), ("g_ai", "game.g_ai"), ("g_monster", "game.g_monster"),
	("g_combat", "game.g_combat"), ("g_weapon", "game.g_weapon"), ("g_misc", "game.g_misc"), ("m_move", "game.monster.misc.move"),
	("g_items", "game.g_items"), ("g_spawn", "game.g_spawn"), ("p_trail", "game.player.trail"),
	("p_weapon", "game.player.weapon"), ("p_client", "game.player.client"), ("g_chase", "game.g_chase"), ("flash", "common.shared.flash")]


BUILTINS = {"len", "range", "str", "type", "min", "max", "sum", "list", "dict", "set", "id", "input", "print",
	"float", "int", "next", "iter", "all", "any", "map", "filter", "abs", "round", "pow", "hash", "format", "object", "bytes"}


class Ctx(object):
	def __init__(self, mod, statics=()):
		self.mod = mod
		self.statics = set(statics)
		self.cfuncs = set()
		self.assigned = set()
		self.locals = set()
		self.fixmes = []
		self.mods = {alias: importlib.import_module(path) for alias, path in SEARCH}
		self.needed = set()

	def resolve(self, name):
		if name in self.locals: return name + "_" if name in BUILTINS else name
		if name in RENAME:
			r = RENAME[name]
			if "." in r: self.needed.add(r.split(".")[0].split("[")[0])
			return r
		if name in G_MAIN:
			self.needed.add("g_main")
			return "g_main." + RENAME.get(name, name)
		if hasattr(self.mod, name) or name in self.statics or name in self.cfuncs: return name
		for alias in sorted(dir(self.mod), key=lambda a: not a.endswith("_h")):
			m = getattr(self.mod, alias)
			if type(m).__name__ == "module" and alias not in ("np", "math", "rand") and hasattr(m, name) and \
				type(getattr(m, name)).__name__ != "module":
				return alias + "." + name
		for alias, m in self.mods.items():
			if hasattr(m, name) and not (alias == "shared_c" and name in ("rand",)):
				self.needed.add(alias)
				return alias + "." + name
		self.fixmes.append(name)
		return name


def tokens_to_py(expr, ctx):
	"""Translate one C expression."""
	e = expr.strip()
	e = re.sub(r"\(\s*(?:const\s+)?(?:int|float|unsigned|short|byte|char|double|qboolean|gitem_armor_t\s*\*|gitem_t\s*\*|edict_t\s*\*)\s*\)\s*(?=[\w(])", "", e)
	e = e.replace("->", ".")
	# strcmp(a, b) == 0 / != 0 / !strcmp(a, b)
	e = re.sub(r"!\s*strcmp\s*\(([^(),]+),\s*([^(),]+)\)", r"(\1 == \2)", e)
	e = re.sub(r"strcmp\s*\(([^(),]+),\s*([^(),]+)\)\s*==\s*0", r"(\1 == \2)", e)
	e = re.sub(r"strcmp\s*\(([^(),]+),\s*([^(),]+)\)\s*!=\s*0", r"(\1 != \2)", e)
	e = re.sub(r"(\d+\.\d*|\.\d+|\d+)[fF]\b", r"\1", e)
	e = e.replace("&&", " and ").replace("||", " or ")
	e = re.sub(r"!(?!=)", " not ", e)
	e = re.sub(r"(^|[(,=]\s*)&(?=\s*\w)", r"\1", e)	# address-of
	e = conv_ternary(e)
	out, i = [], 0
	for t in re.finditer(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)*|\S', e):
		tok = t.group(0)
		out.append(e[i:t.start()]); i = t.end()
		if tok[0] == "'" and len(tok) == 3:
			out.append(str(ord(tok[1]))); continue
		if (tok[0].isalpha() or tok[0] == "_") and e[:t.start()].rstrip().endswith("."):
			out.append(tok); continue	# attribute after "]." or ")."
		if tok[0].isalpha() or tok[0] == "_":
			head, _, rest = tok.partition(".")
			if head in ("and", "or", "not", "if", "else", "None", "True", "False"):
				out.append(tok); continue
			out.append(ctx.resolve(head) + ("." + rest if rest else ""))
		else:
			out.append(tok)
	out.append(e[i:])
	s = "".join(out)
	s = re.sub(r"\s+", " ", s).strip()
	s = re.sub(r"\(\s+", "(", s); s = re.sub(r"\s+\)", ")", s)
	s = s.replace("not  ", "not ")
	return s


def split_decl(line):
	"""'vec3_t a, b;' -> ('vec3_t', ['a', 'b'], {init})"""
	m = re.match(r"\s*((?:static\s+|const\s+)*(?:unsigned\s+)?[A-Za-z_]\w*(?:\s*\*)*)\s+(.*);\s*$", line)
	if not m: return None
	typ, rest = m.group(1), m.group(2)
	first = re.match(r"[A-Za-z_]\w*", typ).group(0)
	if first not in TYPES and not first.endswith("_t"): return None
	names = []
	for part in re.split(r",(?![^{]*\})", rest):
		part = part.strip()
		mm = re.match(r"(\**)\s*([A-Za-z_]\w*)\s*(\[[^\]]*\])?\s*(?:=\s*(.*))?$", part)
		if not mm: return None
		names.append((mm.group(2), mm.group(1), mm.group(3), mm.group(4)))
	return typ, names


def split_top(s, sep=","):
	"""Split at top-level separators (outside brackets and strings)."""
	parts, depth, cur, q = [], 0, "", None
	for ch in s:
		if q:
			cur += ch
			if ch == q and not cur.endswith("\\" + q): q = None
			continue
		if ch in "\"'": q = ch; cur += ch; continue
		if ch in "([{": depth += 1
		elif ch in ")]}": depth -= 1
		if ch == sep and depth == 0:
			parts.append(cur); cur = ""; continue
		cur += ch
	parts.append(cur)
	return parts


def conv_ternary(s):
	"""a ? b : c -> (b if a else c), at any nesting level; va(fmt, ...) -> (fmt % (...))."""
	# recurse into brackets first
	out, i, q = "", 0, None
	while i < len(s):
		ch = s[i]
		if ch in "\"'":
			j = i + 1
			while j < len(s) and not (s[j] == ch and s[j - 1] != "\\"): j += 1
			out += s[i:j + 1]; i = j + 1; continue
		if ch in "([":
			close = ")" if ch == "(" else "]"
			depth, j = 0, i
			while j < len(s):
				if s[j] in "\"'":
					k = j + 1
					while k < len(s) and not (s[k] == s[j] and s[k - 1] != "\\"): k += 1
					j = k + 1; continue
				if s[j] in "([": depth += 1
				elif s[j] in ")]":
					depth -= 1
					if depth == 0: break
				j += 1
			inner = s[i + 1:j]
			inner = ",".join(conv_ternary(p) for p in split_top(inner))
			m = re.search(r"\bva\s*$", out)
			if ch == "(" and m:
				args = split_top(inner)
				out = out[:m.start()] + "(%s %% (%s,))" % (args[0].strip(), ", ".join(a.strip() for a in args[1:])) if len(args) > 1 else out[:m.start()] + "(%s)" % args[0]
			else:
				out += ch + inner + close
			i = j + 1; continue
		out += ch; i += 1
	s = out
	# top-level ?:
	depth, qpos = 0, -1
	i = 0
	while i < len(s):
		ch = s[i]
		if ch in "\"'":
			j = i + 1
			while j < len(s) and not (s[j] == ch and s[j - 1] != "\\"): j += 1
			i = j + 1; continue
		if ch in "([": depth += 1
		elif ch in ")]": depth -= 1
		elif ch == "?" and depth == 0: qpos = i; break
		i += 1
	if qpos < 0: return s
	# matching ':'
	depth, nest, cpos, i = 0, 0, -1, qpos + 1
	while i < len(s):
		ch = s[i]
		if ch in "\"'":
			j = i + 1
			while j < len(s) and not (s[j] == ch and s[j - 1] != "\\"): j += 1
			i = j + 1; continue
		if ch in "([": depth += 1
		elif ch in ")]": depth -= 1
		elif depth == 0 and ch == "?": nest += 1
		elif depth == 0 and ch == ":":
			if nest == 0: cpos = i; break
			nest -= 1
		i += 1
	if cpos < 0: return s
	cond, a, b = s[:qpos].strip(), s[qpos + 1:cpos].strip(), s[cpos + 1:].strip()
	return "(%s if %s else %s)" % (conv_ternary(a), cond, conv_ternary(b))


class Src(object):
	"""A C function body as a stream of statements."""
	def __init__(self, text):
		self.t = text
		self.i = 0

	def ws(self):
		"""Skip whitespace; return any comments passed (as lines)."""
		comments = []
		while self.i < len(self.t):
			if self.t[self.i] in " \t\r\n": self.i += 1; continue
			if self.t.startswith("//", self.i):
				j = self.t.find("\n", self.i)
				j = len(self.t) if j < 0 else j
				comments.append(self.t[self.i + 2:j].strip()); self.i = j; continue
			if self.t.startswith("/*", self.i):
				j = self.t.find("*/", self.i)
				for l in self.t[self.i + 2:j].split("\n"):
					l = l.strip().lstrip("*").strip()
					if l: comments.append(l)
				self.i = j + 2; continue
			if self.t.startswith("#", self.i):	# preprocessor line
				j = self.t.find("\n", self.i)
				comments.append(self.t[self.i:j].strip()); self.i = j; continue
			break
		return comments

	def peek_word(self):
		m = re.match(r"[A-Za-z_]\w*", self.t[self.i:])
		return m.group(0) if m else None

	def group(self):
		"""Read a bracketed group starting at the current '('; return its inside."""
		assert self.t[self.i] == "(", self.t[self.i:self.i + 40]
		depth, j = 0, self.i
		while j < len(self.t):
			ch = self.t[j]
			if ch in "\"'":
				k = j + 1
				while self.t[k] != ch or self.t[k - 1] == "\\": k += 1
				j = k + 1; continue
			if ch == "(": depth += 1
			elif ch == ")":
				depth -= 1
				if depth == 0: break
			j += 1
		inner = self.t[self.i + 1:j]
		self.i = j + 1
		return inner

	def until_semicolon(self):
		depth, j = 0, self.i
		while j < len(self.t):
			ch = self.t[j]
			if ch in "\"'":
				k = j + 1
				while self.t[k] != ch or self.t[k - 1] == "\\": k += 1
				j = k + 1; continue
			if ch in "({[": depth += 1
			elif ch in ")}]": depth -= 1
			elif ch == ";" and depth == 0: break
			j += 1
		s = self.t[self.i:j]
		self.i = j + 1
		return re.sub(r"\s+", " ", re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", s))).strip()


def parse_stmt(src):
	"""-> list of (kind, ...) statement nodes; comments become ('comment', text)."""
	nodes = [("comment", c) for c in src.ws()]
	t, i = src.t, src.i
	if i >= len(t): return nodes
	if t[i] == "{":
		src.i += 1
		body = []
		while True:
			body += [("comment", c) for c in src.ws()]
			if src.t[src.i] == "}": src.i += 1; break
			body += parse_stmt(src)
		return nodes + [("block", body)]
	w = src.peek_word()
	if w == "if":
		src.i += 2; src.ws()
		cond = src.group()
		then = parse_stmt(src)
		save = src.i
		cm = src.ws()
		els = None
		if src.peek_word() == "else":
			src.i += 4
			els = parse_stmt(src)
		else:
			src.i = save
		return nodes + [("if", cond, then, els)]
	if w == "for":
		src.i += 3; src.ws()
		head = src.group()
		return nodes + [("for", head, parse_stmt(src))]
	if w == "while":
		src.i += 5; src.ws()
		cond = src.group()
		return nodes + [("while", cond, parse_stmt(src))]
	if w == "do":
		src.i += 2
		body = parse_stmt(src)
		src.ws(); assert src.peek_word() == "while"
		src.i += 5; src.ws()
		cond = src.group(); src.ws()
		if src.t[src.i] == ";": src.i += 1
		return nodes + [("do", cond, body)]
	if w == "switch":
		src.i += 6; src.ws()
		var = src.group(); src.ws()
		assert src.t[src.i] == "{"; src.i += 1
		cases = []	# (labels or None for default, body nodes)
		while True:
			cms = [("comment", c) for c in src.ws()]
			if src.t[src.i] == "}": src.i += 1; break
			w2 = src.peek_word()
			if w2 == "case" or w2 == "default":
				if w2 == "case":
					src.i += 4
					j = src.t.index(":", src.i)
					label = src.t[src.i:j].strip(); src.i = j + 1
				else:
					src.i += 7; src.ws(); src.i += 1; label = None
				if cases and not cases[-1][1] and cases[-1][0] is not None and label is not None:
					cases[-1][0].append(label)	# case a: case b:
				else:
					cases.append(([label] if label is not None else None, cms))
				continue
			cases[-1][1].extend(cms + parse_stmt(src))
		return nodes + [("switch", var, cases)]
	return nodes + [("stmt", src.until_semicolon())]


def emit(nodes, ctx, depth, out, indent="\t"):
	pad = indent * depth
	for n in nodes:
		k = n[0]
		if k == "comment":
			out.append(pad + "# " + n[1]); continue
		if k == "block":
			emit(n[1], ctx, depth, out); continue
		if k == "if":
			_, cond, then, els = n
			first = True
			while True:
				out.append(pad + ("if " if first else "elif ") + tokens_to_py(cond, ctx) + ":")
				out.append("")
				body = []
				emit(then, ctx, depth + 1, body)
				out.extend(body or [pad + indent + "pass"])
				out.append("")
				if els and len(els) == 1 and els[0][0] == "if":
					_, cond, then, els = els[0]; first = False; continue
				break
			if els:
				out.append(pad + "else:"); out.append("")
				body = []
				emit(els, ctx, depth + 1, body)
				out.extend(body or [pad + indent + "pass"])
				out.append("")
			out.append("")
			continue
		if k == "for":
			_, head, body = n
			parts = split_top(head, ";")
			init, cond, step = [p.strip() for p in parts]
			m1 = re.fullmatch(r"(\w+)\s*=\s*(.+)", init)
			m2 = m1 and re.fullmatch(r"%s\s*(<=|<|>=|>)\s*(.+)" % m1.group(1), cond)
			m3 = m1 and re.fullmatch(r"(?:%s\s*(\+\+|--)|(?:\+\+|--)%s|%s\s*(\+=|-=)\s*(.+))" % ((m1.group(1),) * 3), step)
			if m1 and m2 and m3:
				v = m1.group(1); ctx.locals.add(v)
				a = tokens_to_py(m1.group(2), ctx); op, b = m2.group(1), tokens_to_py(m2.group(2), ctx)
				if m3.group(1) == "++" or (m3.group(2) == "+=") or step.startswith("++"):
					kstep = tokens_to_py(m3.group(3), ctx) if m3.group(3) else "1"
					end = "%s + 1" % b if op == "<=" else b
					rng = ("range(%s)" % end if a == "0" and kstep == "1" else
						"range(%s, %s)" % (a, end) if kstep == "1" else "range(%s, %s, %s)" % (a, end, kstep))
				else:
					kstep = tokens_to_py(m3.group(3), ctx) if m3.group(3) else "1"
					end = "%s - 1" % b if op == ">=" else b
					rng = "range(%s, %s, -%s)" % (a, end, kstep)
				out.append(pad + "for %s in %s:" % (ctx.resolve(v), rng)); out.append("")
				body2 = []
				emit(body, ctx, depth + 1, body2)
				out.extend(body2 or [pad + indent + "pass"]); out.append(""); out.append("")
			else:
				# general for: init; while cond: body; step (a continue in the body would skip the step)
				if init: out.append(pad + stmt(init, ctx))
				out.append(pad + "while %s:" % (tokens_to_py(cond, ctx) if cond else "True")); out.append("")
				body2 = []
				emit(body, ctx, depth + 1, body2)
				if any("continue" in l for l in body2):
					out.append(pad + indent + "# FIXME c2py: continue in a for loop skips its step")
					ctx.fixmes.append("for/continue")
				out.extend(body2)
				for st in split_top(step):
					if st.strip(): out.append(pad + indent + stmt(st.strip(), ctx))
				out.append(""); out.append("")
			continue
		if k == "while":
			_, cond, body = n
			out.append(pad + "while %s:" % tokens_to_py(cond, ctx)); out.append("")
			body2 = []
			emit(body, ctx, depth + 1, body2)
			out.extend(body2 or [pad + indent + "pass"]); out.append(""); out.append("")
			continue
		if k == "do":
			_, cond, body = n
			out.append(pad + "while True:"); out.append("")
			emit(body, ctx, depth + 1, out)
			out.append(pad + indent + "if not (%s):" % tokens_to_py(cond, ctx))
			out.append(pad + indent + indent + "break")
			out.append(""); out.append("")
			continue
		if k == "switch":
			_, var, cases = n
			mpost = re.fullmatch(r"\s*(.+?)\s*(\+\+|--)\s*", var)
			if mpost:	# switch (x++)
				x = tokens_to_py(mpost.group(1), ctx)
				out.append(pad + "_switch = %s" % x)
				out.append(pad + "%s %s= 1" % (x, "+" if mpost.group(2) == "++" else "-"))
				v = "_switch"
			else:
				v = tokens_to_py(var, ctx)
			first = True
			for labels, body in cases:
				# drop the trailing break of a case
				b = list(body)
				while b and b[-1][0] == "stmt" and b[-1][1] == "break": b.pop()
				if labels is None:
					out.append(pad + "else:")
				else:
					out.append(pad + ("if " if first else "elif ") + " or ".join("%s == %s" % (v, tokens_to_py(l, ctx)) for l in labels) + ":")
				first = False
				out.append("")
				body2 = []
				emit(b, ctx, depth + 1, body2)
				out.extend(body2 or [pad + indent + "pass"]); out.append("")
			out.append("")
			continue
		if k == "stmt":
			s = n[1]
			if not s: continue
			d = split_decl(s + ";")
			if d:
				typ, names = d
				if depth == 1:
					ctx.decls.append(s + ";")
				else:
					out.append(pad + "#" + s + ";")
				for nm, ptr, arr, init in names:
					ctx.locals.add(nm)
					line = decl_init(typ, nm, ptr, arr, init, ctx)
					if line is None: continue
					if depth == 1: ctx.inits.append(line)
					else: out.append(pad + line)
				continue
			out.append(pad + stmt(s, ctx))


def decl_init(typ, nm, ptr, arr, init, ctx):
	pn = ctx.resolve(nm)
	if arr and not ptr and init is None:
		n = tokens_to_py(arr[1:-1], ctx)
		if typ.endswith("vec3_t"):
			return "%s = [np.zeros((3,), dtype=np.float32) for _ in range(%s)]" % (pn, n)
		if re.search(r"\b(float|vec_t|double)\b", typ):
			return "%s = np.zeros((%s,), dtype=np.float32)" % (pn, n)
		return "%s = [%s] * %s" % (pn, "0" if re.search(r"\b(int|short|byte|unsigned)\b", typ) else "None", n)
	if typ.endswith("vec3_t") and not ptr:
		if init and init.strip().startswith("{"):
			return "%s = np.array([%s], dtype=np.float32)" % (pn, init.strip()[1:-1])
		return "%s = np.zeros((3,), dtype=np.float32)" % pn
	if init is not None:
		return "%s = %s" % (pn, tokens_to_py(init, ctx))
	return None


def translate(cfunc, ctx, indent="\t"):
	rtype, name, params, body = cfunc
	pnames = []
	for p in params.split(","):
		p = p.strip()
		if not p or p == "void": continue
		p = re.sub(r"/\*.*?\*/", "", p).strip()
		p = re.sub(r"\[.*\]", "", p)
		pnames.append(re.findall(r"\w+", p)[-1])
	ctx.locals = set(pnames)
	ctx.decls, ctx.inits = [], []
	pnames = [p + "_" if p in BUILTINS else p for p in pnames]
	ctypes = ", ".join(re.sub(r"\s*\b\w+\s*$", "", re.sub(r"/\*.*?\*/", "", p).strip()) for p in params.split(",") if p.strip() and p.strip() != "void")
	rt = re.sub(r"\s+", " ", rtype.strip())
	comment = "#" + ctypes
	if rt not in ("void", "static void"):
		comment += " (returns %s)" % rt
	elif rt.startswith("static"):
		comment += " (static)"
	src = Src("{\n" + body + "\n}")
	nodes = parse_stmt(src)
	out = []
	emit(nodes, ctx, 1, out)
	# collapse runs of blank lines to at most two, and trim the end
	res, blank = [], 0
	for l in out:
		if not l.strip():
			blank += 1
			if blank > 2: continue
		else:
			blank = 0
		res.append(l)
	while res and not res[-1].strip(): res.pop()
	while res and not res[0].strip(): res.pop(0)
	head = ["def %s(%s): %s" % (name, ", ".join(pnames), comment)]
	if ctx.assigned:
		head.append(indent + "global " + ", ".join(sorted(ctx.assigned)))
	head.append("")
	if ctx.decls:
		head.append(indent + '"""')
		head += [indent + d for d in ctx.decls]
		head.append(indent + '"""')
	head += [indent + l for l in ctx.inits]
	if ctx.inits or ctx.decls: head.append("")
	if not any(l.strip() and not l.strip().startswith("#") for l in res): res.append(indent + "pass")
	return "\n".join(head + res) + "\n"


def stmt(s, ctx):
	s = s.rstrip(";").strip()
	if s == "return": return "return"
	if s.startswith("return "): return "return " + tokens_to_py(s[7:], ctx)
	if s == "break": return "break"
	if s == "continue": return "continue"
	m = re.fullmatch(r"([\w.\->\[\]]+)\s*(\+\+|--)", s) or re.fullmatch(r"(\+\+|--)\s*([\w.\->\[\]]+)", s)
	if m:
		g = m.groups()
		tgt, op = (g[0], g[1]) if g[1] in ("++", "--") else (g[1], g[0])
		return "%s %s= 1" % (tokens_to_py(tgt, ctx), "+" if op == "++" else "-")
	m = re.fullmatch(r"([\w.\->\[\]]+)\s*(=|\+=|-=|\*=|/=|\|=|&=|\^=)\s*(.+)", s)
	if m and m.group(2) == "=" and "=" in m.group(3) and re.search(r"[^=!<>]=[^=]", " " + m.group(3) + " "):
		# chained assignment a = b = c
		parts = [p.strip() for p in re.split(r"(?<![=!<>])=(?!=)", s)]
		return " = ".join(tokens_to_py(p, ctx) for p in parts)
	if m:
		if m.group(1) in ctx.statics: ctx.assigned.add(m.group(1))
		return "%s %s %s" % (tokens_to_py(m.group(1), ctx), m.group(2), tokens_to_py(m.group(3), ctx))
	return tokens_to_py(s, ctx)


def main(argv):
	write = "--write" in argv
	show = "--show" in argv
	argv = [a for a in argv if not a.startswith("--")]
	modpath, cpath, names = argv[0], argv[1], argv[2:]
	csrc = open(os.path.join(YQ, cpath), errors="replace").read()
	cfuncs = {m.group(2): m.groups() for m in FUNC_RE.finditer(csrc)}
	statics = dict((m.group(2), m.group(1)) for m in re.finditer(r"^static\s+(int|float|qboolean)\s+(\w+)\s*(?:=[^;]*)?;", csrc, re.M))
	defines = dict((m.group(1), m.group(2).strip()) for m in re.finditer(r"^#define\s+([A-Z_][A-Z0-9_]*)\s+([^\n/]+)", csrc, re.M))
	modname = os.path.relpath(os.path.abspath(modpath), ROOT)[:-3].replace(os.sep, ".")
	mod = importlib.import_module(modname)
	src = open(modpath).read()
	results = {}
	for n in names:
		if n not in cfuncs:
			print("%s: not found in %s" % (n, cpath)); continue
		ctx = Ctx(mod, list(statics) + list(defines))
		ctx.cfuncs = set(cfuncs)
		try:
			py = translate(cfuncs[n], ctx)
		except ValueError as e:
			print("%s: can't translate (%s)" % (n, e)); continue
		if ctx.fixmes:
			py = py.replace("\n", "\n\t# FIXME c2py: unresolved %s\n" % ", ".join(sorted(set(ctx.fixmes))), 1)
			print("%s: unresolved %s" % (n, ", ".join(sorted(set(ctx.fixmes)))))
		results[n] = (py, ctx.needed)
		if show: print(py)
	if not write: return
	tree = ast.parse(src)
	lines = src.splitlines(keepends=True)
	edits = []
	needed = set()
	for n, (py, nd) in results.items():
		needed |= nd
		done = False
		for st in tree.body:
			if isinstance(st, ast.FunctionDef) and st.name == n:
				edits.append((st.lineno - 1, st.end_lineno, py)); done = True; break
		if done: continue
		for st in tree.body:	# a pasted C block holding this function
			if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str) and \
				re.search(r"^%s\(" % re.escape(n), st.value.value, re.M) and "{" in st.value.value:
				v = st.value.value
				# keep the banner comment of the block
				bm = re.match(r"\s*/\*(.*?)\*/", v, re.S)
				banner = ""
				if bm:
					banner = '"""\n' + "\n".join(l.rstrip() for l in bm.group(1).strip("\n").split("\n")) + '\n"""\n'
				edits.append((st.lineno - 1, st.end_lineno, banner + py)); done = True; break
		if not done: print("%s: nowhere to put it" % n)
	for a, b, t in sorted(edits, reverse=True):
		lines[a:b] = [t]
	src = "".join(lines)
	imports = {"g_main": "from game import g_main\n", "local": "from game.header import local\n",
		"shared": "from common.header import shared\n", "shared_c": "from common.shared import shared as shared_c\n",
		"rand": "from common.shared import rand\n", "math": "import math\n", "game_h": "from game.header import game as game_h\n",
		"g_utils": "from game import g_utils\n", "g_ai": "from game import g_ai\n", "g_monster": "from game import g_monster\n",
		"g_combat": "from game import g_combat\n", "g_weapon": "from game import g_weapon\n", "g_misc": "from game import g_misc\n",
		"m_move": "from game.monster.misc import move as m_move\n", "g_items": "from game import g_items\n", "g_spawn": "from game import g_spawn\n",
		"p_trail": "from game.player import trail as p_trail\n", "p_weapon": "from game.player import weapon as p_weapon\n",
		"p_client": "from game.player import client as p_client\n", "g_chase": "from game import g_chase\n",
		"flash": "from common.shared import flash\n"}
	if "np.zeros" in src or "np.array" in src: needed.add("np")
	imports["np"] = "import numpy as np\n"
	# new file statics the functions use
	t1 = ast.parse(src)
	have = {st.targets[0].id for st in t1.body if isinstance(st, ast.Assign) and isinstance(st.targets[0], ast.Name)}
	allpy = "".join(p for p, _ in results.values())
	missing = [n for n in statics if n not in have and re.search(r"\b%s\b" % n, allpy)]
	mdefs = [n for n in defines if n not in have and re.search(r"\b%s\b" % n, allpy)]
	if missing or mdefs:
		k = re.search(r"^(def|class) ", src, re.M).start()
		k = src.rfind('"""', 0, k) if src.rfind('"""', 0, k) > src.rfind("\n\n", 0, k) else k
		src = src[:k] + "".join("%s = %s\n" % (n, defines[n]) for n in mdefs) + \
			"".join("%s = 0 #static %s\n" % (n, statics[n]) for n in missing) + "\n" + src[k:]
		print("added statics/defines: " + ", ".join(mdefs + missing))
	t2 = ast.parse(src)
	bound = set()
	for st in t2.body:
		if isinstance(st, (ast.Import, ast.ImportFrom)):
			for a in st.names: bound.add((a.asname or a.name).split(".")[0])
	add = "".join(imports[n] for n in sorted(needed) if n not in bound and n in imports)
	if add:
		k = src.index("from __future__ import annotations\n") + len("from __future__ import annotations\n")
		src = src[:k] + "\n" + add + src[k:]
	open(modpath, "w").write(src)
	print("wrote %d functions to %s" % (len(edits), modpath))


if __name__ == "__main__":
	main(sys.argv[1:])
