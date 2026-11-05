"""
Copyright (C) 1997-2001 Id Software, Inc.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.

=======================================================================

Global string matching

=======================================================================
"""
from __future__ import annotations

"""
#include <stdio.h>
#include "header/glob.h"
"""

# Q2PORT: the C pointers p and t are offsets into pattern and text; reading past the end gives '\0'

def _at(s: str, i: int)->str:	# Q2PORT: *p with the terminating NUL
	return s[i] if i < len(s) else '\0'

"""
 * Like glob_match, but match PATTERN against any final segment of TEXT.
"""
def glob_match_after_star(pattern: str, text: str, p: int = 0, t: int = 0)->int: #char *, char * (returns int)

	"""
	register char *p = pattern, *t = text;
	register char c, c1;
	"""

	c = _at(pattern, p); p += 1
	while c == '?' or c == '*':

		if c == '?':
			c2 = _at(text, t); t += 1
			if c2 == '\0':

				return 0

		c = _at(pattern, p); p += 1


	if c == '\0':

		return 1


	if c == '\\':

		c1 = _at(pattern, p)

	else:

		c1 = c


	while 1:

		if (c == '[' or _at(text, t) == c1) and glob_match(pattern, text, p - 1, t):

			return 1


		c2 = _at(text, t); t += 1
		if c2 == '\0':

			return 0

"""
 * Match the pattern PATTERN against the string TEXT;
 * return 1 if it matches, 0 otherwise.
 *
 * A match means the entire string TEXT is used up in matching.
 *
 * In the pattern string, `*' matches any sequence of characters,
 * `?' matches any character, [SET] matches any character in the specified set,
 * [!SET] matches any character not in the specified set.
 *
 * A set is composed of characters or ranges; a range looks like
 * character hyphen character (as in 0-9 or A-Z).
 * [0-9a-zA-Z_] is the set of characters allowed in C identifiers.
 * Any other character in the pattern must be matched exactly.
 *
 * To suppress the special syntactic significance of any of `[]*?!-\',
 * and match the character exactly, precede it with a `\'.
"""
def glob_match(pattern: str, text: str, p: int = 0, t: int = 0)->int: #char *, char * (returns int)

	"""
	register char *p = pattern, *t = text;
	register char c;
	"""

	c = _at(pattern, p); p += 1
	while c != '\0':

		if c == '?':

			if _at(text, t) == '\0':

				return 0

			else:

				t += 1


		elif c == '\\':

			a = _at(pattern, p); p += 1
			b = _at(text, t); t += 1
			if a != b:

				return 0


		elif c == '*':

			return glob_match_after_star(pattern, text, p, t)

		elif c == '[':

			c1 = _at(text, t); t += 1

			if c1 == '\0':

				return 0


			invert = ((_at(pattern, p) == '!') or (_at(pattern, p) == '^'))

			if invert:

				p += 1


			c = _at(pattern, p); p += 1

			matched = False
			while 1:

				cstart = c; cend = c

				if c == '\\':

					cstart = _at(pattern, p); p += 1
					cend = cstart


				if c == '\0':

					return 0


				c = _at(pattern, p); p += 1

				if c == '-' and _at(pattern, p) != ']':

					cend = _at(pattern, p); p += 1

					if cend == '\\':

						cend = _at(pattern, p); p += 1


					if cend == '\0':

						return 0


					c = _at(pattern, p); p += 1


				if c1 >= cstart and c1 <= cend:

					matched = True
					break #goto match;


				if c == ']':

					break



			if not matched:

				if not invert:

					return 0


			else: #match:

				# Skip the rest of the [...] construct that already matched.
				while c != ']':

					if c == '\0':

						return 0


					c = _at(pattern, p); p += 1

					if c == '\0':

						return 0

					elif c == '\\':

						p += 1



				if invert:

					return 0



		else:

			b = _at(text, t); t += 1
			if c != b:

				return 0


		c = _at(pattern, p); p += 1


	return 1 if _at(text, t) == '\0' else 0
