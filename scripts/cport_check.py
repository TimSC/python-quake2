#!/usr/bin/env python3
"""cport_check.py - structural checker for the Quake 2 C->Python port.

For each .py file it:
  1. Walks the source tracking triple-quoted string state (per-line).
  2. Reports "live C" lines: C-looking code OUTSIDE string blocks.
  3. Reports unterminated string state at EOF.
  4. Tries ast.parse and reports the first SyntaxError.
  5. (with --funcs) lists functions that still have a C body: i.e. a
     live `def` immediately preceded/followed by a C-looking live line.

Usage:
  python3 scripts/cport_check.py [file.py ...]
  python3 scripts/cport_check.py --all          # scan server/ game/ qcommon/ client/
  python3 scripts/cport_check.py --funcs FILE   # detail mode for one file
"""
from __future__ import annotations

import ast
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

C_STARTERS = (
    'void', 'int', 'float', 'char *', 'char*', 'qboolean', 'byte',
    'typedef', 'struct', 'vec3_t', 'edict_t', 'cmodel_t', 'trace_t',
    'link_t', 'moveclip_t', 'areanode_t', 'int32', 'float32',
    'memset (', 'memset(&', 'memcmp (', 'strcpy (', 'strcat (',
    'strncpy (', 'memcpy (', 'sprintf (', 'sscanf (', 'sscanf(',
)


def line_string_mask(src):
    """For each line index, True if the line starts inside a triple-quoted
    string (roughly; assumes all strings are triple-quoted docstrings)."""
    n = len(src)
    mask = []
    in_str = False
    line_start = 0
    while line_start <= n:
        # find next newline
        nl = src.find('\n', line_start)
        if nl == -1:
            mask.append(in_str)
            break
        # walk from line_start to nl to get state at line start (already have)
        mask.append(in_str)
        # advance state to next line start
        j = line_start
        while j < nl:
            if src.startswith('"""', j):
                in_str = not in_str
                j += 3
                continue
            if in_str and src[j] == '\\':
                j += 2
                continue
            j += 1
        line_start = nl + 1
    return mask


def looks_like_c(stripped, raw):
    if stripped.startswith(('/*', '*/', '//')) or raw.startswith('/*'):
        return True
    if stripped.startswith(('#if', '#endif', '#else', '#define', '#include',
                            '#undef', '#pragma')):
        return True
    if stripped.startswith(C_STARTERS):
        return True
    # C return with a C type-ish payload is ambiguous; skip
    return False


def check_file(path, funcs=False):
    src = open(path).read()
    lines = [l.replace('\r', '') for l in src.split('\n')]
    mask = line_string_mask(src)
    if len(mask) < len(lines):
        mask += [False] * (len(lines) - len(mask))

    print(f"=== {path} ===")
    issues = 0
    for n, l in enumerate(lines, 1):
        stripped = l.strip()
        if not stripped:
            continue
        if not mask[n - 1] and looks_like_c(stripped, l):
            issues += 1
            print(f"  live-C line {n}: {stripped[:90]}")
    if not issues:
        print("  (no live C-looking lines)")

    # unterminated string at EOF
    in_str = False
    i = 0
    while i < len(src):
        if src.startswith('"""', i):
            in_str = not in_str
            i += 3
            continue
        if in_str and src[i] == '\\':
            i += 2
            continue
        i += 1
    if in_str:
        print("  WARNING: unterminated triple-quoted string at EOF")

    try:
        ast.parse(src)
        print("  AST: OK")
    except SyntaxError as e:
        print(f"  AST: SyntaxError line {e.lineno}: {e.msg}")

    if funcs:
        report_c_bodies(src, lines)
    return issues


def report_c_bodies(src, lines):
    """Report defs whose body (live code, between def and next def) contains
    C-looking lines - i.e. unported function bodies."""
    tree = ast.parse(src) if True else None
    if tree is None:
        return
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            names.append((node.name, node.lineno))
    names.sort(key=lambda t: t[1])
    for idx, (name, ln) in enumerate(names):
        end = names[idx + 1][1] - 1 if idx + 1 < len(names) else len(lines)
        c_count = 0
        for n in range(ln + 1, end + 1):
            s = lines[n - 1].strip()
            if s and looks_like_c(s, lines[n - 1]):
                c_count += 1
        if c_count:
            print(f"  unported? {name} (line {ln}, {c_count} C-looking body lines)")


def main(argv):
    args = [a for a in argv[1:] if a != '--all' and a != '--funcs']
    funcs = '--funcs' in argv
    if '--all' in argv:
        pats = [os.path.join(ROOT, d, '*.py') for d in
                ('qcommon', 'server', 'game', 'client', 'ctf')]
        args = sorted(set(glob.glob(p) for pat in pats for p in glob.glob(pat)))
    if not args:
        print(__doc__)
        return 1
    total = 0
    for p in args:
        total += check_file(p, funcs=funcs)
        print()
    print(f"total live-C lines: {total}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
