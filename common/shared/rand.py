"""
KISS PRNG (c) 2011 Shinobu

This file was optained from zuttobenkyou.wordpress.com
and modified by the Yamagi Quake II developers.

LICENSE: Public domain

=======================================================================

KISS PRNG, as devised by Dr. George Marsaglia

=======================================================================
"""
from __future__ import annotations

import numpy as np

"""
#include <stdint.h>
"""

# Q2PORT: Python ints are unbounded, so every uint64_t result is masked
U64 = 0xFFFFFFFFFFFFFFFF

QSIZE = 0x200000
def CNG(): #define CNG (cng = 6906969069ULL * cng + 13579)
	global cng
	cng = (6906969069 * cng + 13579) & U64
	return cng
def XS(): #define XS (xs ^= (xs << 13), xs ^= (xs >> 17), xs ^= (xs << 43))
	global xs
	xs ^= (xs << 13) & U64
	xs ^= (xs >> 17)
	xs ^= (xs << 43) & U64
	return xs
def KISS(): return (B64MWC() + CNG() + XS()) & U64 #define KISS (B64MWC() + CNG + XS)

QARY = np.zeros((QSIZE,), dtype=np.uint64) #static uint64_t [QSIZE]
j = 0 #static int
carry = 0 #static uint64_t
xs = 0 #static uint64_t
cng = 0 #static uint64_t

def B64MWC(): #(returns uint64_t)

	global j, carry

	"""
	uint64_t t, x;
	"""

	j = (j + 1) & (QSIZE - 1)
	x = int(QARY[j])
	t = ((x << 28) + carry) & U64
	carry = ((x >> 36) - (1 if t < x else 0)) & U64
	QARY[j] = (t - x) & U64
	return (t - x) & U64

"""
 * Generate a pseudorandom
 * integer >0.
"""
def randk()->int: #(returns int)

	"""
	int r;
	"""

	r = KISS() & 0xFFFFFFFF #r = (int)KISS;
	if r >= 0x80000000: r -= 0x100000000
	r = (r * -1) if (r < 0) else r
	if r > 0x7FFFFFFF: r -= 0x100000000	# Q2PORT: INT_MIN * -1 wraps in C

	return r

"""
 * Generate a pseudorandom
 * signed float between
 * 0 and 1.
"""
def frandk()->float: #(returns float)

	return (randk()&32767)* (1.0/32767)

"""
 * Generate a pseudorandom
 * float between -1 and 1.
"""
def crandk()->float: #(returns float)

	return (randk()&32767)* (2.0/32767) - 1

"""
 * Seeds the PRNG
"""
def randk_seed(): #void

	global cng

	"""
	uint64_t i;
	"""

	# Seed QARY[] with CNG+XS:
	#for (i = 0; i < QSIZE; i++)
	#{
	#	QARY[i] = CNG + XS;
	#}
	# Q2PORT: the loop is done with numpy. xs is never seeded, so XS is always 0, and CNG is
	# a linear congruential sequence: cng after k steps = A^k * cng + C * (A^0 + ... + A^(k-1)).
	# numpy's uint64 arithmetic wraps modulo 2^64, as C's does.
	assert xs == 0
	A = np.uint64(6906969069); C = np.uint64(13579)
	with np.errstate(over="ignore"):
		pw = np.empty((QSIZE + 1,), dtype=np.uint64)
		pw[0] = 1
		pw[1:] = np.cumprod(np.full((QSIZE,), A, dtype=np.uint64))	# A^0 .. A^QSIZE
		geo = np.cumsum(pw[:QSIZE])	# A^0 + .. + A^(k-1), for k = 1 .. QSIZE
		QARY[:] = pw[1:] * np.uint64(cng) + C * geo
	cng = int(QARY[QSIZE - 1])

	# Run through several rounds
	#  to warm up the state
	for i in range(256):

		randk()
