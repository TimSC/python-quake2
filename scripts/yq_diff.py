"""
Show what Yamagi Quake II changed in a function compared with id's Quake II
3.21, with the noise removed: formatting, comments, braces, and the
"if (!x) { return; }" null guards Yamagi adds to most game functions.

usage:
  yq_diff.py <function> [...]          diff these functions
  yq_diff.py --file <yquake2 .c file>  diff every function of a Yamagi file (path under yquake2/src)
  yq_diff.py --summary <dir>           one line per function of a Yamagi dir: same / guards only / changed / new

See docs/yquake2_plan.md.
"""
from __future__ import annotations

import os
import re
import sys
import difflib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yq_index as yi

TOKEN = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|0[xX][0-9a-fA-F]+[uUlL]*|\d+\.\d*(?:[eE][-+]?\d+)?[fF]?|\.\d+(?:[eE][-+]?\d+)?[fF]?|\d+[uUlLfF]*|\w+|->|\+\+|--|<<=|>>=|<<|>>|<=|>=|==|!=|&&|\|\||[-+*/%&|^]=|\S')


def tokens(body: str):
	"""Tokens of a C function body with comments and braces removed."""
	body = yi.strip_comments(body)
	body = re.sub(r'(?m)^[ \t]*#.*$', '', body)	# preprocessor lines are compared separately
	toks = [t for t in TOKEN.findall(body) if t not in ("{", "}")]
	# 1.0f == 1.0, (qboolean)0 style casts are left alone
	return [re.sub(r'^(\d+\.\d*|\.\d+)[fF]$', r'\1', t) for t in toks]


GUARD_TERM = re.compile(r'^(?:! \w+(?: (?:\.|->) \w+)*|\w+(?: (?:\.|->) \w+)* == NULL)$')


def drop_null_guards(toks):
	"""Remove Yamagi's null guards: 'if ( !a || !b->c || d == NULL ) return [value] ;'."""
	out = []; i = 0
	while i < len(toks):
		if toks[i] == "if" and i + 1 < len(toks) and toks[i + 1] == "(":
			depth = 0; j = i + 1
			while j < len(toks):
				if toks[j] == "(": depth += 1
				elif toks[j] == ")":
					depth -= 1
					if depth == 0: break
				j += 1
			cond = " ".join(toks[i + 2:j])
			terms = [t.strip() for t in cond.split("||")]
			if j + 1 < len(toks) and toks[j + 1] == "return" and terms and all(GUARD_TERM.match(t) for t in terms):
				k = j + 1
				while k < len(toks) and toks[k] != ";":
					k += 1
				i = k + 1
				continue
		out.append(toks[i]); i += 1
	return out


def statements(toks):
	"""Join tokens into one line per statement, for a readable diff."""
	lines = []; cur = []; depth = 0
	for t in toks:
		cur.append(t)
		if t == "(": depth += 1
		elif t == ")": depth -= 1
		elif t == ";" and depth == 0:
			lines.append(" ".join(cur)); cur = []
		elif t in ("else",) and depth == 0 and len(cur) == 1:
			lines.append("else"); cur = []
	if cur: lines.append(" ".join(cur))
	return lines


def load_functions(root, files):
	out = {}
	for rel in files:
		src = yi.strip_strings(open(os.path.join(root, rel), errors="replace").read()) if False else open(os.path.join(root, rel), errors="replace").read()
		for name, a, b, body in yi.c_functions(yi.strip_comments(src)):
			out.setdefault(name, (rel, body))
	return out


_ID = None
_YQ = None


def id_functions():
	global _ID
	if _ID is None:
		_ID = load_functions(yi.ID, list(yi.walk_c(yi.ID)))
	return _ID


def yq_functions():
	global _YQ
	if _YQ is None:
		_YQ = load_functions(yi.YQ, list(yi.walk_c(yi.YQ, yi.YQ_SCOPE, yi.YQ_SKIP)))
	return _YQ


def no_parens(line):
	return line.replace("( ", "").replace(" )", "").replace("(", "").replace(")", "")


def classify(name):
	"""(status, id_lines, yq_lines). status is:
	same: identical; guards: only null guards added; style: also only extra parentheses;
	changed: real changes; new: only in Yamagi; gone: only in id."""
	idf = id_functions().get(name); yqf = yq_functions().get(name)
	if not yqf: return "gone", None, None
	if not idf: return "new", None, statements(tokens(yqf[1]))
	a = tokens(idf[1]); b = tokens(yqf[1])
	if a == b: return "same", None, None
	a = drop_null_guards(a); b = drop_null_guards(b)
	if a == b: return "guards", None, None
	la = statements(a); lb = statements(b)
	if [no_parens(x) for x in la] == [no_parens(x) for x in lb]: return "style", None, None
	return "changed", la, lb


def show(name):
	status, a, b = classify(name)
	idf = id_functions().get(name); yqf = yq_functions().get(name)
	print("=== %s  [%s]  id: %s  yamagi: %s" % (name, status, idf[0] if idf else "-", yqf[0] if yqf else "-"))
	if status == "changed":
		# lines that differ only in parentheses count as equal
		ka = [no_parens(x) for x in a]; kb = [no_parens(x) for x in b]
		for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ka, kb, autojunk=False).get_opcodes():
			if tag == "equal": continue
			print("   @@ id %d yamagi %d" % (i1 + 1, j1 + 1))
			for l in a[max(i1 - 1, 0):i1]: print("     " + l)
			for l in a[i1:i2]: print("   - " + l)
			for l in b[j1:j2]: print("   + " + l)
	elif status == "new":
		for l in b: print("   + " + l)


def main(argv):
	if not argv:
		print(__doc__); return
	if argv[0] == "--file":
		rel = argv[1]
		src = open(os.path.join(yi.YQ, rel), errors="replace").read()
		for name, a, b, body in yi.c_functions(yi.strip_comments(src)):
			show(name)
	elif argv[0] == "--summary":
		d = argv[1]
		import collections
		tot = collections.Counter()
		for rel in yi.walk_c(yi.YQ, [d], yi.YQ_SKIP):
			if not rel.endswith(".c"): continue
			src = open(os.path.join(yi.YQ, rel), errors="replace").read()
			for name, a, b, body in yi.c_functions(yi.strip_comments(src)):
				st = classify(name)[0]
				tot[st] += 1
				print("%-8s %-28s %s" % (st, name, rel))
		print("total:", dict(tot))
	else:
		for n in argv: show(n)


if __name__ == "__main__":
	main(sys.argv[1:])
