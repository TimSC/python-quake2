"""Translate the top-level data declarations of a C file into the port's module-level Python,
and insert each chunk before the function that follows it in the C.
usage: yq_cdata.py <module.py> <file.c> [--dry]"""
import re, sys, ast
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
modp, cpath = sys.argv[1], sys.argv[2]
dry = "--dry" in sys.argv
c = open(cpath).read()
QUAL = {"NUM_ADDRESSBOOK_ENTRIES": "client_h.NUM_ADDRESSBOOK_ENTRIES", "MAX_QPATH": "shared.MAX_QPATH", "MAX_OSPATH": "shared.MAX_OSPATH"}
OTHER = {"netadr_t": "common_h.netadr_t", "strlist_t": "shared.strlist_t"}
STRUCTS = {"menuframework_s", "menubitmap_s", "menufield_s", "menuslider_s", "menulist_s", "menuaction_s", "menuseparator_s", "menucommon_s", "menupopup_s"}
lines = c.split("\n")
chunks = []  # (text, nextfunc)
cur = []; infunc = False
for i, l in enumerate(lines):
	m = re.match(r"^([A-Za-z_]\w*)\(.*", l)
	if not infunc and m and not l.rstrip().endswith(";"):
		# drop the return type lines and the banner comment kept with the function by yq_sync
		while cur and (re.match(r"^(static\s+)?(const\s+)?[\w\s\*]+$", cur[-1]) and cur[-1].strip() and not cur[-1].strip().endswith(";")):
			cur.pop()
		# drop trailing comment block (banner)
		j = len(cur)
		while j > 0 and not cur[j-1].strip(): j -= 1
		if j > 0 and cur[j-1].strip().endswith("*/"):
			k = j - 1
			while k >= 0 and "/*" not in cur[k]: k -= 1
			if k >= 0 and not any(x.strip().endswith(";") for x in cur[k:j]):
				cur = cur[:k]
		chunks.append(("\n".join(cur), m.group(1))); cur = []; infunc = True; continue
	if infunc:
		if l.startswith("}"): infunc = False
		continue
	cur.append(l)
chunks.append(("\n".join(cur), None))

def strip_comments(s):
	s = re.sub(r"/\*.*?\*/", lambda m: "", s, flags=re.S)
	out = []
	for l in s.split("\n"):
		instr = False
		for k, ch in enumerate(l):
			if ch == '"' and (k == 0 or l[k-1] != "\\"): instr = not instr
			if not instr and l[k:k+2] == "//":
				l = l[:k]; break
		out.append(l)
	return "\n".join(out)

def cstr_join(s):
	# "a" "b" -> "ab"
	parts = re.findall(r'"((?:\\.|[^"\\])*)"', s)
	return '"' + "".join(parts) + '"'

def init_to_py(v):
	v = v.strip()
	if v.startswith("{"):
		inner = v[1:v.rindex("}")]
		items, depth, buf, instr = [], 0, "", False
		k = 0
		while k < len(inner):
			ch = inner[k]
			if ch == '"' and (k == 0 or inner[k-1] != "\\"): instr = not instr
			if not instr:
				if ch == "{": depth += 1
				elif ch == "}": depth -= 1
				elif ch == "," and depth == 0:
					items.append(buf); buf = ""; k += 1; continue
			buf += ch; k += 1
		if buf.strip(): items.append(buf)
		return "[" + ", ".join(init_to_py(x) for x in items if x.strip()) + "]"
	if v.startswith('"'): return cstr_join(v)
	if v == "NULL": return "None"
	if v in ("true", "false"): return v.capitalize()
	v = re.sub(r"(\d+\.\d*)f\b", r"\1", v)
	if re.fullmatch(r"'.'", v): return str(ord(v[1]))
	return v

out_chunks = []
for text, nextfunc in chunks:
	t = strip_comments(text)
	py = []
	# defines
	for m in re.finditer(r"^#define\s+(\w+)\s+(.+)$", t, re.M):
		py.append("%s\t= %s" % (m.group(1), init_to_py(m.group(2))))
	t2 = re.sub(r"^#.*$", "", t, flags=re.M)
	# statements
	stmts, buf, depth, instr = [], "", 0, False
	for ch in t2:
		if ch == '"': instr = not instr
		if not instr:
			if ch == "{": depth += 1
			elif ch == "}": depth -= 1
		buf += ch
		if ch == ";" and depth == 0 and not instr:
			stmts.append(buf.strip()); buf = ""
	cblock = []
	for st in stmts:
		s = re.sub(r"\s+", " ", st[:-1]).strip()
		if re.match(r"^(extern\b|.*\(.*\)$)", s) and "=" not in s:   # extern or prototype
			cblock.append(st); continue
		m = re.match(r"^(static\s+)?(const\s+)?(unsigned\s+)?(struct\s+)?(\w+)\s*(\*?)\s*(const\s+)?(\w+)((?:\s*\[[^\]]*\])*)\s*(?:=\s*(.*))?$", s, re.S)
		if not m:
			cblock.append(st); continue
		static, const, uns, _, typ, ptr, _, name, dims, init = m.groups()
		ctype = "%s%s%s%s" % ("static " if static else "", "const " if const else "", "unsigned " if uns else "", typ) + (" *" if ptr else "") + dims.replace(" ", "")
		dl = re.findall(r"\[([^\]]*)\]", dims)
		if init is not None:
			v = init_to_py(init)
		elif (typ in STRUCTS or typ in OTHER) and not ptr:
			ctor = ("qmenu_h.%s()" % typ) if typ in STRUCTS else ("%s()" % OTHER[typ])
			if dl:
				n = dl[0].strip()
				n = re.sub(r"ARRLEN\((\w+)\)", r"len(\1)", n)
				n = re.sub(r"\b\w+\b", lambda mm: QUAL.get(mm.group(0), mm.group(0)), n)
				v = "[%s for i in range(%s)]" % (ctor, n)
			else:
				v = ctor
		elif dl:
			n = re.sub(r"ARRLEN\((\w+)\)", r"len(\1)", dl[0].strip()) or "0"
			n = re.sub(r"\b\w+\b", lambda mm: QUAL.get(mm.group(0), mm.group(0)), n)
			if typ == "char" and not ptr and len(dl) == 1:
				v = '""'
			elif typ == "char" and not ptr:
				v = '["" for i in range(%s)]' % n
			else:
				fill = "None" if (ptr or typ == "char") else ("False" if typ == "qboolean" else ("0.0" if typ == "float" else "0"))
				v = "[%s] * %s" % (fill, n)
		else:
			v = "None" if ptr else ("False" if typ == "qboolean" else ("0.0" if typ == "float" else ('""' if typ == "char" else ("0" if typ in ("int", "short", "byte", "unsigned", "size_t", "long") else "None"))))
		py.append("%s = %s #%s" % (name, v, ctype))
	txt = ""
	if cblock:
		txt += '"""\n' + "\n".join(cblock) + '\n"""\n\n'
	if py:
		txt += "\n".join(py) + "\n\n"
	if txt.strip():
		out_chunks.append((txt, nextfunc))

src = open(modp).read()
if dry:
	for txt, nf in out_chunks: print("----- before", nf); print(txt)
	sys.exit()
tree = ast.parse(src); L = src.splitlines(keepends=True)
pos = {}
body = tree.body
for idx, st in enumerate(body):
	name = None
	if isinstance(st, ast.FunctionDef): name = st.name
	elif isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
		mm = re.search(r"^([A-Za-z_]\w*)\(", st.value.value, re.M)
		if mm and "{" in st.value.value: name = mm.group(1)
	if name and name not in pos:
		start = st.lineno - 1
		prev = body[idx-1] if idx > 0 else None
		if isinstance(prev, ast.Expr) and isinstance(prev.value, ast.Constant) and isinstance(prev.value.value, str) and "{" not in prev.value.value:
			start = prev.lineno - 1
		pos[name] = start
ins = []
for txt, nf in out_chunks:
	if nf is None: ins.append((len(L), txt)); continue
	if nf not in pos: print("no place for", nf); continue
	ins.append((pos[nf], txt))
for p_, txt in sorted(ins, key=lambda x: -x[0]):
	L[p_:p_] = [txt]
open(modp, "w").write("".join(L))
print("inserted", len(ins), "chunks")
