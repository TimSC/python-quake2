#!/usr/bin/env python3
"""map_strings.py - show triple-quoted string structure of a file.

Usage:
  python3 scripts/map_strings.py FILE
  python3 scripts/map_strings.py FILE --around N
  python3 scripts/map_strings.py FILE --summary
"""
from __future__ import annotations

import argparse
import sys


def find_events(src):
    """Return (list of (line, 'OPEN'|'CLOSE'), unterminated_at_eof)."""
    events = []
    in_str = False
    i = 0
    n = len(src)
    line = 1
    while i < n:
        if src.startswith('"""', i):
            events.append((line, 'OPEN' if not in_str else 'CLOSE'))
            in_str = not in_str
            i += 3
            continue
        if in_str and src[i] == '\\':
            i += 2
            continue
        if src[i] == '\n':
            line += 1
        i += 1
    return events, in_str


def line_state(events, target):
    """True if `target` line starts inside a string."""
    state = False
    for ln, kind in events:
        if ln > target:
            break
        state = (kind == 'OPEN')
    return state


def main(path, around=None, summary=False):
    src = open(path).read()
    lines = src.replace('\r', '').split('\n')
    events, unterminated = find_events(src)
    print(f"=== {path} ===")
    if summary:
        for ln, kind in events:
            print(f"  {ln:5d} {kind}")
        print(f"  unterminated at EOF: {unterminated}")
        return
    lo, hi = (max(1, around - 10), min(len(lines), around + 10)) if around \
        else (1, len(lines))
    for n in range(lo, hi + 1):
        ins = line_state(events, n)
        mark = ' ' * 6
        for ln, kind in events:
            if ln == n:
                mark = kind.ljust(6)
        print(f"{n:5d} {mark} {'|' if ins else ' '} {lines[n - 1].rstrip()[:100]}")
    if unterminated:
        print("  !! unterminated triple-quoted string at EOF")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', metavar='FILE')
    parser.add_argument('--around', type=int, help='show context around this line')
    parser.add_argument('--summary', action='store_true',
                        help='only print open/close events')
    args = parser.parse_args()
    for p in args.files:
        main(p, around=args.around, summary=args.summary)
