"""
Public Domain C source implementation of RFC 1320
      -  The MD4 Message-Digest Algorithm  -

       http://www.faqs.org/rfcs/rfc1320.html
                   by Steven Fuller
"""
from __future__ import annotations

import struct

"""
#include <inttypes.h>
"""
# Q2PORT: UINT4 is a 32 bit word. The C "unsigned long" is 64 bits on x86-64 Linux,
# so the values are masked to 32 bits here, as on the 32 bit machines Quake II shipped for.

UINT4_MASK = 0xFFFFFFFF

# MD4 context.
class MD4_CTX(object):

	def __init__(self):

		self.state = [0, 0, 0, 0] #UINT4 [4], state (ABCD)
		self.count = [0, 0] #UINT4 [2], number of bits, modulo 2^64 (lsb first)
		self.buffer = bytearray(64) #unsigned char [64], input buffer


"""
MD4C.C - RSA Data Security, Inc., MD4 message-digest algorithm
Copyright (C) 1990-2, RSA Data Security, Inc. All rights reserved.

License to copy and use this software is granted provided that it is identified as the
RSA Data Security, Inc. MD4 Message-Digest Algorithm
 in all material mentioning or referencing this software or this function.
License is also granted to make and use derivative works provided that such works are identified as
derived from the RSA Data Security, Inc. MD4 Message-Digest Algorithm
in all material mentioning or referencing the derived work.
RSA Data Security, Inc. makes no representations concerning either the merchantability of this software or the suitability of this software for any particular purpose. It is provided
as is without express or implied warranty of any kind.

These notices must be retained in any copies of any part of this documentation and/or software.
"""

# Constants for MD4Transform routine.
S11	= 3
S12	= 7
S13	= 11
S14	= 19
S21	= 3
S22	= 5
S23	= 9
S24	= 13
S31	= 3
S32	= 9
S33	= 11
S34	= 15

PADDING = bytes([0x80] + [0] * 63) #static unsigned char [64]

# F, G and H are basic MD4 functions, and ROTATE_LEFT rotates x left n bits.
# FF, GG and HH are transformations for rounds 1, 2 and 3; they are C macros and are
# written out in place in MD4Transform (Q2PORT: calling a function per step is too slow).
#define F(x, y, z) (((x) & (y)) | ((~x) & (z)))
#define G(x, y, z) (((x) & (y)) | ((x) & (z)) | ((y) & (z)))
#define H(x, y, z) ((x) ^ (y) ^ (z))
#define ROTATE_LEFT(x, n) (((x) << (n)) | ((x) >> (32-(n))))
#define FF(a, b, c, d, x, s) {(a) += F ((b), (c), (d)) + (x); (a) = ROTATE_LEFT ((a), (s));}
#define GG(a, b, c, d, x, s) {(a) += G ((b), (c), (d)) + (x) + (UINT4)0x5a827999; (a) = ROTATE_LEFT ((a), (s));}
#define HH(a, b, c, d, x, s) {(a) += H ((b), (c), (d)) + (x) + (UINT4)0x6ed9eba1; (a) = ROTATE_LEFT ((a), (s));}


# MD4 initialization. Begins an MD4 operation, writing a new context.
def MD4Init (context): #MD4_CTX *

	context.count[0] = context.count[1] = 0

	# Load magic initialization constants.
	context.state[0] = 0x67452301
	context.state[1] = 0xefcdab89
	context.state[2] = 0x98badcfe
	context.state[3] = 0x10325476


# MD4 block update operation. Continues an MD4 message-digest operation, processing another message block, and updating the context.
def MD4Update (context, input, inputLen): #MD4_CTX *, unsigned char *, unsigned int

	#unsigned int i, index, partLen;

	# Compute number of bytes mod 64
	index = (context.count[0] >> 3) & 0x3F

	# Update number of bits
	context.count[0] = (context.count[0] + (inputLen << 3)) & UINT4_MASK
	if context.count[0] < ((inputLen << 3) & UINT4_MASK):
		context.count[1] = (context.count[1] + 1) & UINT4_MASK

	context.count[1] = (context.count[1] + (inputLen >> 29)) & UINT4_MASK

	partLen = 64 - index

	# Transform as many times as possible.
	if inputLen >= partLen:

		context.buffer[index:index+partLen] = input[0:partLen] # memcpy
		MD4Transform (context.state, context.buffer, 0)

		i = partLen
		while i + 63 < inputLen:
			MD4Transform (context.state, input, i) # &input[i]
			i += 64

		index = 0

	else:
		i = 0

	# Buffer remaining input
	context.buffer[index:index+inputLen-i] = input[i:inputLen] # memcpy


# MD4 finalization. Ends an MD4 message-digest operation, writing the the message digest and zeroizing the context.
def MD4Final (digest, context): #unsigned char [16], MD4_CTX *

	#unsigned char bits[8];
	#unsigned int index, padLen;

	# Save number of bits
	bits = bytearray(8)
	Encode (bits, context.count, 8)

	# Pad out to 56 mod 64.
	index = (context.count[0] >> 3) & 0x3f
	padLen = (56 - index) if (index < 56) else (120 - index)
	MD4Update (context, PADDING, padLen)

	# Append length (before padding)
	MD4Update (context, bits, 8)

	# Store state in digest
	Encode (digest, context.state, 16)

	# Zeroize sensitive information.
	context.__init__() # memset ((POINTER)context, 0, sizeof (*context));


# MD4 basic transformation. Transforms state based on block.
def MD4Transform (state, block, offset): #UINT4 [4], unsigned char [64] (Q2PORT: block is a buffer plus an offset)

	M = UINT4_MASK
	a = state[0]; b = state[1]; c = state[2]; d = state[3]
	x = struct.unpack_from("<16I", block, offset) # Decode (x, block, 64);

	# Round 1
	a = (a + ((b & c) | (~b & d)) + x[ 0]) & M; a = ((a << S11) | (a >> (32-S11))) & M	# 1
	d = (d + ((a & b) | (~a & c)) + x[ 1]) & M; d = ((d << S12) | (d >> (32-S12))) & M	# 2
	c = (c + ((d & a) | (~d & b)) + x[ 2]) & M; c = ((c << S13) | (c >> (32-S13))) & M	# 3
	b = (b + ((c & d) | (~c & a)) + x[ 3]) & M; b = ((b << S14) | (b >> (32-S14))) & M	# 4
	a = (a + ((b & c) | (~b & d)) + x[ 4]) & M; a = ((a << S11) | (a >> (32-S11))) & M	# 5
	d = (d + ((a & b) | (~a & c)) + x[ 5]) & M; d = ((d << S12) | (d >> (32-S12))) & M	# 6
	c = (c + ((d & a) | (~d & b)) + x[ 6]) & M; c = ((c << S13) | (c >> (32-S13))) & M	# 7
	b = (b + ((c & d) | (~c & a)) + x[ 7]) & M; b = ((b << S14) | (b >> (32-S14))) & M	# 8
	a = (a + ((b & c) | (~b & d)) + x[ 8]) & M; a = ((a << S11) | (a >> (32-S11))) & M	# 9
	d = (d + ((a & b) | (~a & c)) + x[ 9]) & M; d = ((d << S12) | (d >> (32-S12))) & M	# 10
	c = (c + ((d & a) | (~d & b)) + x[10]) & M; c = ((c << S13) | (c >> (32-S13))) & M	# 11
	b = (b + ((c & d) | (~c & a)) + x[11]) & M; b = ((b << S14) | (b >> (32-S14))) & M	# 12
	a = (a + ((b & c) | (~b & d)) + x[12]) & M; a = ((a << S11) | (a >> (32-S11))) & M	# 13
	d = (d + ((a & b) | (~a & c)) + x[13]) & M; d = ((d << S12) | (d >> (32-S12))) & M	# 14
	c = (c + ((d & a) | (~d & b)) + x[14]) & M; c = ((c << S13) | (c >> (32-S13))) & M	# 15
	b = (b + ((c & d) | (~c & a)) + x[15]) & M; b = ((b << S14) | (b >> (32-S14))) & M	# 16

	# Round 2
	a = (a + ((b & c) | (b & d) | (c & d)) + x[ 0] + 0x5a827999) & M; a = ((a << S21) | (a >> (32-S21))) & M	# 17
	d = (d + ((a & b) | (a & c) | (b & c)) + x[ 4] + 0x5a827999) & M; d = ((d << S22) | (d >> (32-S22))) & M	# 18
	c = (c + ((d & a) | (d & b) | (a & b)) + x[ 8] + 0x5a827999) & M; c = ((c << S23) | (c >> (32-S23))) & M	# 19
	b = (b + ((c & d) | (c & a) | (d & a)) + x[12] + 0x5a827999) & M; b = ((b << S24) | (b >> (32-S24))) & M	# 20
	a = (a + ((b & c) | (b & d) | (c & d)) + x[ 1] + 0x5a827999) & M; a = ((a << S21) | (a >> (32-S21))) & M	# 21
	d = (d + ((a & b) | (a & c) | (b & c)) + x[ 5] + 0x5a827999) & M; d = ((d << S22) | (d >> (32-S22))) & M	# 22
	c = (c + ((d & a) | (d & b) | (a & b)) + x[ 9] + 0x5a827999) & M; c = ((c << S23) | (c >> (32-S23))) & M	# 23
	b = (b + ((c & d) | (c & a) | (d & a)) + x[13] + 0x5a827999) & M; b = ((b << S24) | (b >> (32-S24))) & M	# 24
	a = (a + ((b & c) | (b & d) | (c & d)) + x[ 2] + 0x5a827999) & M; a = ((a << S21) | (a >> (32-S21))) & M	# 25
	d = (d + ((a & b) | (a & c) | (b & c)) + x[ 6] + 0x5a827999) & M; d = ((d << S22) | (d >> (32-S22))) & M	# 26
	c = (c + ((d & a) | (d & b) | (a & b)) + x[10] + 0x5a827999) & M; c = ((c << S23) | (c >> (32-S23))) & M	# 27
	b = (b + ((c & d) | (c & a) | (d & a)) + x[14] + 0x5a827999) & M; b = ((b << S24) | (b >> (32-S24))) & M	# 28
	a = (a + ((b & c) | (b & d) | (c & d)) + x[ 3] + 0x5a827999) & M; a = ((a << S21) | (a >> (32-S21))) & M	# 29
	d = (d + ((a & b) | (a & c) | (b & c)) + x[ 7] + 0x5a827999) & M; d = ((d << S22) | (d >> (32-S22))) & M	# 30
	c = (c + ((d & a) | (d & b) | (a & b)) + x[11] + 0x5a827999) & M; c = ((c << S23) | (c >> (32-S23))) & M	# 31
	b = (b + ((c & d) | (c & a) | (d & a)) + x[15] + 0x5a827999) & M; b = ((b << S24) | (b >> (32-S24))) & M	# 32

	# Round 3
	a = (a + (b ^ c ^ d) + x[ 0] + 0x6ed9eba1) & M; a = ((a << S31) | (a >> (32-S31))) & M	# 33
	d = (d + (a ^ b ^ c) + x[ 8] + 0x6ed9eba1) & M; d = ((d << S32) | (d >> (32-S32))) & M	# 34
	c = (c + (d ^ a ^ b) + x[ 4] + 0x6ed9eba1) & M; c = ((c << S33) | (c >> (32-S33))) & M	# 35
	b = (b + (c ^ d ^ a) + x[12] + 0x6ed9eba1) & M; b = ((b << S34) | (b >> (32-S34))) & M	# 36
	a = (a + (b ^ c ^ d) + x[ 2] + 0x6ed9eba1) & M; a = ((a << S31) | (a >> (32-S31))) & M	# 37
	d = (d + (a ^ b ^ c) + x[10] + 0x6ed9eba1) & M; d = ((d << S32) | (d >> (32-S32))) & M	# 38
	c = (c + (d ^ a ^ b) + x[ 6] + 0x6ed9eba1) & M; c = ((c << S33) | (c >> (32-S33))) & M	# 39
	b = (b + (c ^ d ^ a) + x[14] + 0x6ed9eba1) & M; b = ((b << S34) | (b >> (32-S34))) & M	# 40
	a = (a + (b ^ c ^ d) + x[ 1] + 0x6ed9eba1) & M; a = ((a << S31) | (a >> (32-S31))) & M	# 41
	d = (d + (a ^ b ^ c) + x[ 9] + 0x6ed9eba1) & M; d = ((d << S32) | (d >> (32-S32))) & M	# 42
	c = (c + (d ^ a ^ b) + x[ 5] + 0x6ed9eba1) & M; c = ((c << S33) | (c >> (32-S33))) & M	# 43
	b = (b + (c ^ d ^ a) + x[13] + 0x6ed9eba1) & M; b = ((b << S34) | (b >> (32-S34))) & M	# 44
	a = (a + (b ^ c ^ d) + x[ 3] + 0x6ed9eba1) & M; a = ((a << S31) | (a >> (32-S31))) & M	# 45
	d = (d + (a ^ b ^ c) + x[11] + 0x6ed9eba1) & M; d = ((d << S32) | (d >> (32-S32))) & M	# 46
	c = (c + (d ^ a ^ b) + x[ 7] + 0x6ed9eba1) & M; c = ((c << S33) | (c >> (32-S33))) & M	# 47
	b = (b + (c ^ d ^ a) + x[15] + 0x6ed9eba1) & M; b = ((b << S34) | (b >> (32-S34))) & M	# 48

	state[0] = (state[0] + a) & M
	state[1] = (state[1] + b) & M
	state[2] = (state[2] + c) & M
	state[3] = (state[3] + d) & M

	# Zeroize sensitive information.
	#memset ((POINTER)x, 0, sizeof (x));


# Encodes input (UINT4) into output (unsigned char). Assumes len is a multiple of 4.
def Encode (output, input, len): #unsigned char *, UINT4 *, unsigned int

	#unsigned int i, j;

	i = 0
	j = 0
	while j < len:
		output[j] = input[i] & 0xff
		output[j+1] = (input[i] >> 8) & 0xff
		output[j+2] = (input[i] >> 16) & 0xff
		output[j+3] = (input[i] >> 24) & 0xff
		i += 1
		j += 4


# Decodes input (unsigned char) into output (UINT4). Assumes len is a multiple of 4.
def Decode (output, input, len): #UINT4 *, unsigned char *, unsigned int

	#unsigned int i, j;

	i = 0
	j = 0
	while j < len:
		output[i] = input[j] | (input[j+1] << 8) | (input[j+2] << 16) | (input[j+3] << 24)
		i += 1
		j += 4

#===================================================================

"""
static void
DoMD4()
{
	AA = A;
	BB = B;
	CC = C;
	DD = D;

	S(A, B, C, D, 0, 3);
	S(D, A, B, C, 1, 7);
	S(C, D, A, B, 2, 11);
	S(B, C, D, A, 3, 19);
	S(A, B, C, D, 4, 3);
	S(D, A, B, C, 5, 7);
	S(C, D, A, B, 6, 11);
	S(B, C, D, A, 7, 19);
	S(A, B, C, D, 8, 3);
	S(D, A, B, C, 9, 7);
	S(C, D, A, B, 10, 11);
	S(B, C, D, A, 11, 19);
	S(A, B, C, D, 12, 3);
	S(D, A, B, C, 13, 7);
	S(C, D, A, B, 14, 11);
	S(B, C, D, A, 15, 19);

	T(A, B, C, D, 0, 3);
	T(D, A, B, C, 4, 5);
	T(C, D, A, B, 8, 9);
	T(B, C, D, A, 12, 13);
	T(A, B, C, D, 1, 3);
	T(D, A, B, C, 5, 5);
	T(C, D, A, B, 9, 9);
	T(B, C, D, A, 13, 13);
	T(A, B, C, D, 2, 3);
	T(D, A, B, C, 6, 5);
	T(C, D, A, B, 10, 9);
	T(B, C, D, A, 14, 13);
	T(A, B, C, D, 3, 3);
	T(D, A, B, C, 7, 5);
	T(C, D, A, B, 11, 9);
	T(B, C, D, A, 15, 13);

	U(A, B, C, D, 0, 3);
	U(D, A, B, C, 8, 9);
	U(C, D, A, B, 4, 11);
	U(B, C, D, A, 12, 15);
	U(A, B, C, D, 2, 3);
	U(D, A, B, C, 10, 9);
	U(C, D, A, B, 6, 11);
	U(B, C, D, A, 14, 15);
	U(A, B, C, D, 1, 3);
	U(D, A, B, C, 9, 9);
	U(C, D, A, B, 5, 11);
	U(B, C, D, A, 13, 15);
	U(A, B, C, D, 3, 3);
	U(D, A, B, C, 11, 9);
	U(C, D, A, B, 7, 11);
	U(B, C, D, A, 15, 15);

	A += AA;
	B += BB;
	C += CC;
	D += DD;
}
"""

"""
static void
PerformMD4(const unsigned char *buf, int length, unsigned char *digest)
{
	int len = length / 64; /* number of full blocks */
	int rem = length % 64; /* number of left over bytes */

	int i, j;
	const unsigned char *ptr = buf;

	/* initialize the MD buffer */
	A = 0x67452301;
	B = 0xEFCDAB89;
	C = 0x98BADCFE;
	D = 0x10325476;

	for (i = 0; i < len; i++)
	{
		for (j = 0; j < 16; j++)
		{
			X[j] = ((ptr[0] << 0) | (ptr[1] << 8) |
					(ptr[2] << 16) | (ptr[3] << 24));

			ptr += 4;
		}

		DoMD4();
	}

	i = rem / 4;

	for (j = 0; j < i; j++)
	{
		X[j] = ((ptr[0] << 0) | (ptr[1] << 8) |
				(ptr[2] << 16) | (ptr[3] << 24));

		ptr += 4;
	}

	switch (rem % 4)
	{
		case 0:
			X[j] = 0x80U;
			break;
		case 1:
			X[j] = ((ptr[0] << 0) | ((0x80U) << 8));
			break;
		case 2:
			X[j] = ((ptr[0] << 0) | (ptr[1] << 8) | ((0x80U) << 16));
			break;
		case 3:
			X[j] =
				((ptr[0] <<
				  0) | (ptr[1] << 8) | (ptr[2] << 16) | ((0x80U) << 24));
			break;
	}

	j++;

	if (j > 14)
	{
		for ( ; j < 16; j++)
		{
			X[j] = 0;
		}

		DoMD4();

		j = 0;
	}

	for ( ; j < 14; j++)
	{
		X[j] = 0;
	}

	X[14] = (length & 0x1FFFFFFF) << 3;
	X[15] = (length & ~0x1FFFFFFF) >> 29;

	DoMD4();

	digest[0] = (A & 0x000000FF) >> 0;
	digest[1] = (A & 0x0000FF00) >> 8;
	digest[2] = (A & 0x00FF0000) >> 16;
	digest[3] = (A & 0xFF000000) >> 24;
	digest[4] = (B & 0x000000FF) >> 0;
	digest[5] = (B & 0x0000FF00) >> 8;
	digest[6] = (B & 0x00FF0000) >> 16;
	digest[7] = (B & 0xFF000000) >> 24;
	digest[8] = (C & 0x000000FF) >> 0;
	digest[9] = (C & 0x0000FF00) >> 8;
	digest[10] = (C & 0x00FF0000) >> 16;
	digest[11] = (C & 0xFF000000) >> 24;
	digest[12] = (D & 0x000000FF) >> 0;
	digest[13] = (D & 0x0000FF00) >> 8;
	digest[14] = (D & 0x00FF0000) >> 16;
	digest[15] = (D & 0xFF000000) >> 24;

	A = AA = 0;
	B = BB = 0;
	C = CC = 0;
	D = DD = 0;

	for (j = 0; j < 16; j++)
	{
		X[j] = 0;
	}
}
"""

def Com_BlockChecksum (buffer, length): #void *, int (returns unsigned)

	#int			digest[4];
	#unsigned	val;
	#MD4_CTX		ctx;

	ctx = MD4_CTX()
	digest = bytearray(16)

	MD4Init (ctx)
	MD4Update (ctx, buffer, length)
	MD4Final (digest, ctx)

	d = struct.unpack("<4I", digest) # (int *)digest
	val = d[0] ^ d[1] ^ d[2] ^ d[3]

	return val
