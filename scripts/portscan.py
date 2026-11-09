#!/usr/bin/env python3
"""portscan.py - complete structural scan of a ported .py file.

One pass over the file producing:
  * exact line of every triple-quote (string open/close, with running state)
  * C banners (/* ===== name ===== */ blocks) - string vs live
  * def/class lines
  * live C-looking lines (outside strings)
  * unterminated string at EOF
  * ast.parse result

Usage:
  python3 scripts/portscan.py FILE [FILE ...]
  python3 scripts/portscan.py --all
"""
from __future__ import annotations

import argparse
import ast
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BANNER_RE = re.compile(r'^\s*=*\s*$')  # ============ line
C_STARTERS = (
    'void', 'int ', 'float ', 'char *', 'qboolean', 'typedef', 'struct',
    'vec3_t', 'edict_t', 'trace_t', 'moveclip_t', 'cmodel_t', 'memset',
    'strncpy', 'strdup', 'strcpy',
)


class Scan:
    def __init__(self, src):
        self.src = src
        self.lines = src.replace('\r', '').split('\n')
        self.events = []        # (line, 'OPEN'/'CLOSE')
        self.line_str = []      # bool per line: inside string at line start
        self.unterminated = False
        self._walk()

    def _walk(self):
        src = self.src
        in_str = False
        line = 1
        i = 0
        n = len(src)
        self.line_str = [False] * (len(self.lines) + 1)
        while i < n:
            if src.startswith('"""', i):
                self.events.append((line, 'OPEN' if not in_str else 'CLOSE'))
                in_str = not in_str
                i += 3
                continue
            if in_str:
                self.line_str[line] = True
                if src[i] == '\\':
                    i += 2
                    continue
            if src[i] == '\n':
                line += 1
            i += 1
        self.unterminated = in_str

    def in_string(self, line):
        return bool(self.line_str[line])


def report(path):
    src = open(path).read()
    sc = Scan(src)
    print(f"=== {path} ({len(sc.lines)} lines) ===")

    # 1. string events
    print(" strings:")
    for ln, kind in sc.events:
        print(f"   {ln:5d} {kind}")
    print(f"   unterminated@EOF: {sc.unterminated}")

    # 2. defs/classes + C-looking live lines + banner detection
    print(" interesting lines:")
    banner = None
    for n, l in enumerate(sc.lines, 1):
        s = l.strip()
        ins = sc.in_string(n)
        if not s:
            continue
        tag = None
        # banners: lines of =s
        if BANNER_RE.match(l):
            if '=' in s and (banner is None or n - banner[0] <= 3
                             and (banner == 'search' or True)):
                pass
        if l.strip().startswith('/*') and not ins:
            tag = 'LIVE-C-OPEN'
        if s.startswith('*/') and not ins:
            tag = 'LIVE-C-CLOSE'
        if s.startswith('def ') or s.startswith('class '):
            tag = ('def' if s.startswith('def') else 'class') + ('|str' if ins else '|live')
        if s.startswith(('void', 'int ', 'float ', 'char *', 'typedef',
                         'memset', 'strncpy', 'struct ')) and not ins:
            tag = 'LIVE-C'
        if tag:
            print(f"   {n:5d} {tag:12s} {s[:80]}")

    # 3. AST
    try:
        ast.parse(src)
        print(" AST: OK")
    except SyntaxError as e:
        print(f" AST: SyntaxError line {e.lineno}: {e.msg}")
        if e.lineno:
            ln = e.lineno
            print(f"     {ln-1:5d} {sc.lines[ln-2].rstrip()[:90]}")
            print(f"     {ln  :5d} {sc.lines[ln-1].rstrip()[:90]}")
            print(f"     {ln+1:5d} {sc.lines[ln].rstrip()[:90]}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    files = a.files
    if a.all:
        files = sorted(set(p for d in ('qcommon', 'server', 'game', 'client')
                           for p in glob.glob(os.path.join(ROOT, d, '*.py'))))
    for f in files:
        report(f)


if __name__ == '__main__':
    main()
