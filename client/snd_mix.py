"""
Copyright (C) 1997-2001 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

"""
import struct
import pygame
from linux import snd_linux
from client import snd_dma, snd_loc
"""
// snd_mix.c -- portable code to mix sounds for snd_dma.c

#include "client.h"
#include "snd_loc.h"
"""
PAINTBUFFER_SIZE = 2048
paintbuffer = []
for i in range(PAINTBUFFER_SIZE):
	paintbuffer.append(snd_loc.portable_samplepair_t())

"""
int		snd_scaletable[32][256];
int 	*snd_p, snd_linear_count, snd_vol;
short	*snd_out;

void S_WriteLinearBlastStereo16 (void);

#if !(defined __linux__ && defined __i386__)
#if	!id386

void S_WriteLinearBlastStereo16 (void)
{
	int		i;
	int		val;

	for (i=0 ; i<snd_linear_count ; i+=2)
	{
		val = snd_p[i]>>8;
		if (val > 0x7fff)
			snd_out[i] = 0x7fff;
		else if (val < (short)0x8000)
			snd_out[i] = (short)0x8000;
		else
			snd_out[i] = val;

		val = snd_p[i+1]>>8;
		if (val > 0x7fff)
			snd_out[i+1] = 0x7fff;
		else if (val < (short)0x8000)
			snd_out[i+1] = (short)0x8000;
		else
			snd_out[i+1] = val;
	}
}
#else
__declspec( naked ) void S_WriteLinearBlastStereo16 (void)
{
	__asm {

 push edi
 push ebx
 mov ecx,ds:dword ptr[snd_linear_count]
 mov ebx,ds:dword ptr[snd_p]
 mov edi,ds:dword ptr[snd_out]
LWLBLoopTop:
 mov eax,ds:dword ptr[-8+ebx+ecx*4]
 sar eax,8
 cmp eax,07FFFh
 jg LClampHigh
 cmp eax,0FFFF8000h
 jnl LClampDone
 mov eax,0FFFF8000h
 jmp LClampDone
LClampHigh:
 mov eax,07FFFh
LClampDone:
 mov edx,ds:dword ptr[-4+ebx+ecx*4]
 sar edx,8
 cmp edx,07FFFh
 jg LClampHigh2
 cmp edx,0FFFF8000h
 jnl LClampDone2
 mov edx,0FFFF8000h
 jmp LClampDone2
LClampHigh2:
 mov edx,07FFFh
LClampDone2:
 shl edx,16
 and eax,0FFFFh
 or edx,eax
 mov ds:dword ptr[-4+edi+ecx*2],edx
 sub ecx,2
 jnz LWLBLoopTop
 pop ebx
 pop edi
 ret
	}
}

#endif
#endif

void S_TransferStereo16 (unsigned long *pbuf, int endtime)
{
	int		lpos;
	int		lpaintedtime;
	
	snd_p = (int *) paintbuffer;
	lpaintedtime = paintedtime;

	while (lpaintedtime < endtime)
	{
	// handle recirculating buffer issues
		lpos = lpaintedtime & ((dma.samples>>1)-1);

		snd_out = (short *) pbuf + (lpos<<1);

		snd_linear_count = (dma.samples>>1) - lpos;
		if (lpaintedtime + snd_linear_count > endtime)
			snd_linear_count = endtime - lpaintedtime;

		snd_linear_count <<= 1;

	// write a linear blast of samples
		S_WriteLinearBlastStereo16 ();

		snd_p += snd_linear_count;
		lpaintedtime += (snd_linear_count>>1);
	}
}

/*
===================
S_TransferPaintBuffer

===================
*/
void S_TransferPaintBuffer(int endtime)
{
	int 	out_idx;
	int 	count;
	int 	out_mask;
	int 	*p;
	int 	step;
	int		val;
	unsigned long *pbuf;

	pbuf = (unsigned long *)dma.buffer;

	if (s_testsound->value)
	{
		int		i;
		int		count;

		// write a fixed sine wave
		count = (endtime - paintedtime);
		for (i=0 ; i<count ; i++)
			paintbuffer[i].left = paintbuffer[i].right = sin((paintedtime+i)*0.1)*20000*256;
	}


	if (dma.samplebits == 16 && dma.channels == 2)
	{	// optimized case
		S_TransferStereo16 (pbuf, endtime);
	}
	else
	{	// general case
		p = (int *) paintbuffer;
		count = (endtime - paintedtime) * dma.channels;
		out_mask = dma.samples - 1; 
		out_idx = paintedtime * dma.channels & out_mask;
		step = 3 - dma.channels;

		if (dma.samplebits == 16)
		{
			short *out = (short *) pbuf;
			while (count--)
			{
				val = *p >> 8;
				p+= step;
				if (val > 0x7fff)
					val = 0x7fff;
				else if (val < (short)0x8000)
					val = (short)0x8000;
				out[out_idx] = val;
				out_idx = (out_idx + 1) & out_mask;
			}
		}
		else if (dma.samplebits == 8)
		{
			unsigned char *out = (unsigned char *) pbuf;
			while (count--)
			{
				val = *p >> 8;
				p+= step;
				if (val > 0x7fff)
					val = 0x7fff;
				else if (val < (short)0x8000)
					val = (short)0x8000;
				out[out_idx] = (val>>8) + 128;
				out_idx = (out_idx + 1) & out_mask;
			}
		}
	}
}


/*
===============================================================================

CHANNEL MIXING

===============================================================================
*/

void S_PaintChannelFrom8 (channel_t *ch, sfxcache_t *sc, int endtime, int offset);
void S_PaintChannelFrom16 (channel_t *ch, sfxcache_t *sc, int endtime, int offset);

"""
raw_buff = bytearray()

def S_PaintChannels(endtime): #int

	global paintbuffer, PAINTBUFFER_SIZE
	global raw_buff

	"""
	int 	i;
	int 	end;
	channel_t *ch;
	sfxcache_t	*sc;
	int		ltime, count;
	playsound_t	*ps;
	"""

	#print (snd_dma.paintedtime, endtime, snd_dma.s_pendingplays)
	
	snd_vol = snd_dma.s_volume.value*256

	##Com_Printf ("%i to %i\n", snd_dma.paintedtime, endtime);
	while snd_dma.paintedtime < endtime:

		# if paintbuffer is smaller than DMA buffer
		end = endtime
		if endtime - snd_dma.paintedtime > PAINTBUFFER_SIZE:
			end = snd_dma.paintedtime + PAINTBUFFER_SIZE

		# start any playsounds
		
		while len(snd_dma.s_pendingplays) > 0:
		
			ps = snd_dma.s_pendingplays[0]

			if ps.begin <= snd_dma.paintedtime:
				
				ps = snd_dma.s_pendingplays.pop(0)
				snd_dma.S_IssuePlaysound (ps)
				continue
			
			#if ps.begin < end:
			#	end = ps.begin		# stop here
			break
		

		# clear the paint buffer
		if snd_dma.s_rawend < snd_dma.paintedtime:
		
			## Com_Printf ("clear\n");
			#memset(paintbuffer, 0, (end - paintedtime) * sizeof(portable_samplepair_t))
			for i in range(snd_dma.paintedtime, end):
				paintbuffer[i-snd_dma.paintedtime].clear()
		
		else:
			# copy from the streaming sound source
			#int		s;
			#int		stop;

			if end < snd_dma.s_rawend:
				stop = end
			else:
				stop = snd_dma.s_rawend

			for i in range(snd_dma.paintedtime, stop):
			
				s = i&(snd_loc.MAX_RAW_SAMPLES-1)
				paintbuffer[i-snd_dma.paintedtime] = snd_dma.s_rawsamples[s]			

##		if (i != end)
##			Com_Printf ("partial stream\n");
##		else
##			Com_Printf ("full stream\n");
			for i in range(stop, end):
				# Buffer underrun, so pad paint buffer with zeros
				paintbuffer[i-snd_dma.paintedtime].left = 0
				paintbuffer[i-snd_dma.paintedtime].right = 0

		"""

		# paint in the channels.
		ch = channels;
		for (i=0; i<MAX_CHANNELS ; i++, ch++)
		{
			ltime = paintedtime;
		
			while (ltime < end)
			{
				if (!ch->sfx || (!ch->leftvol && !ch->rightvol) )
					break;

				// max painting is to the end of the buffer
				count = end - ltime;

				// might be stopped by running out of data
				if (ch->end - ltime < count)
					count = ch->end - ltime;
		
				sc = S_LoadSound (ch->sfx);
				if (!sc)
					break;

				if (count > 0 && ch->sfx)
				{	
					if (sc->width == 1)// FIXME; 8 bit asm is wrong now
						S_PaintChannelFrom8(ch, sc, count,  ltime - paintedtime);
					else
						S_PaintChannelFrom16(ch, sc, count, ltime - paintedtime);
	
					ltime += count;
				}

			// if at end of loop, restart
				if (ltime >= ch->end)
				{
					if (ch->autosound)
					{	// autolooping sounds always go back to start
						ch->pos = 0;
						ch->end = ltime + sc->length;
					}
					else if (sc->loopstart >= 0)
					{
						ch->pos = sc->loopstart;
						ch->end = ltime + sc->length - ch->pos;
					}
					else				
					{	// channel just stopped
						ch->sfx = NULL;
					}
				}
			}
															  
		}
"""

		#if test is None:
		#	test = wave.open("test.wav", "w")
		#	test.setnchannels(2)
		#	test.setsampwidth(2)
		#	test.setframerate(44100//2)

		startrange = None
		endrange = None
		
		for i in range(snd_dma.paintedtime, end):
			s = i-snd_dma.paintedtime
			samp = paintbuffer[s]
			raw_buff += struct.pack("<hh", samp.left, samp.right)
			#test.writeframes(struct.pack("<hh", samp.left, samp.right))

			if startrange is None: startrange = s
			endrange = s

		if snd_linux.dma_channel.get_queue() is None:

			# transfer out according to DMA format
			raw_snd = pygame.mixer.Sound(buffer=raw_buff)
			snd_linux.dma_channel.queue(raw_snd)
			raw_buff = bytearray()

		snd_dma.paintedtime = end

def S_InitScaletable ():
	pass
	"""
	int		i, j;
	int		scale;

	s_volume->modified = false;
	for (i=0 ; i<32 ; i++)
	{
		scale = i * 8 * 256 * s_volume->value;
		for (j=0 ; j<256 ; j++)
			snd_scaletable[i][j] = ((signed char)j) * scale;
	}



#if !(defined __linux__ && defined __i386__)
#if	!id386

void S_PaintChannelFrom8 (channel_t *ch, sfxcache_t *sc, int count, int offset)
{
	int 	data;
	int		*lscale, *rscale;
	unsigned char *sfx;
	int		i;
	portable_samplepair_t	*samp;

	if (ch->leftvol > 255)
		ch->leftvol = 255;
	if (ch->rightvol > 255)
		ch->rightvol = 255;
		
	//ZOID-- >>11 has been changed to >>3, >>11 didn't make much sense
	//as it would always be zero.
	lscale = snd_scaletable[ ch->leftvol >> 3];
	rscale = snd_scaletable[ ch->rightvol >> 3];
	sfx = (signed char *)sc->data + ch->pos;

	samp = &paintbuffer[offset];

	for (i=0 ; i<count ; i++, samp++)
	{
		data = sfx[i];
		samp->left += lscale[data];
		samp->right += rscale[data];
	}
	
	ch->pos += count;
}

#else

__declspec( naked ) void S_PaintChannelFrom8 (channel_t *ch, sfxcache_t *sc, int count, int offset)
{
	__asm {
 push esi
 push edi
 push ebx
 push ebp
 mov ebx,ds:dword ptr[4+16+esp]
 mov esi,ds:dword ptr[8+16+esp]
 mov eax,ds:dword ptr[4+ebx]
 mov edx,ds:dword ptr[8+ebx]
 cmp eax,255
 jna LLeftSet
 mov eax,255
LLeftSet:
 cmp edx,255
 jna LRightSet
 mov edx,255
LRightSet:
 and eax,0F8h
 add esi,20
 and edx,0F8h
 mov edi,ds:dword ptr[16+ebx]
 mov ecx,ds:dword ptr[12+16+esp]
 add esi,edi
 shl eax,7
 add edi,ecx
 shl edx,7
 mov ds:dword ptr[16+ebx],edi
 add eax,offset snd_scaletable
 add edx,offset snd_scaletable
 sub ebx,ebx
 mov bl,ds:byte ptr[-1+esi+ecx*1]
 test ecx,1
 jz LMix8Loop
 mov edi,ds:dword ptr[eax+ebx*4]
 mov ebp,ds:dword ptr[edx+ebx*4]
 add edi,ds:dword ptr[paintbuffer+0-8+ecx*8]
 add ebp,ds:dword ptr[paintbuffer+4-8+ecx*8]
 mov ds:dword ptr[paintbuffer+0-8+ecx*8],edi
 mov ds:dword ptr[paintbuffer+4-8+ecx*8],ebp
 mov bl,ds:byte ptr[-2+esi+ecx*1]
 dec ecx
 jz LDone
LMix8Loop:
 mov edi,ds:dword ptr[eax+ebx*4]
 mov ebp,ds:dword ptr[edx+ebx*4]
 add edi,ds:dword ptr[paintbuffer+0-8+ecx*8]
 add ebp,ds:dword ptr[paintbuffer+4-8+ecx*8]
 mov bl,ds:byte ptr[-2+esi+ecx*1]
 mov ds:dword ptr[paintbuffer+0-8+ecx*8],edi
 mov ds:dword ptr[paintbuffer+4-8+ecx*8],ebp
 mov edi,ds:dword ptr[eax+ebx*4]
 mov ebp,ds:dword ptr[edx+ebx*4]
 mov bl,ds:byte ptr[-3+esi+ecx*1]
 add edi,ds:dword ptr[paintbuffer+0-8*2+ecx*8]
 add ebp,ds:dword ptr[paintbuffer+4-8*2+ecx*8]
 mov ds:dword ptr[paintbuffer+0-8*2+ecx*8],edi
 mov ds:dword ptr[paintbuffer+4-8*2+ecx*8],ebp
 sub ecx,2
 jnz LMix8Loop
LDone:
 pop ebp
 pop ebx
 pop edi
 pop esi
 ret
	}
}

#endif
#endif

void S_PaintChannelFrom16 (channel_t *ch, sfxcache_t *sc, int count, int offset)
{
	int data;
	int left, right;
	int leftvol, rightvol;
	signed short *sfx;
	int	i;
	portable_samplepair_t	*samp;

	leftvol = ch->leftvol*snd_vol;
	rightvol = ch->rightvol*snd_vol;
	sfx = (signed short *)sc->data + ch->pos;

	samp = &paintbuffer[offset];
	for (i=0 ; i<count ; i++, samp++)
	{
		data = sfx[i];
		left = (data * leftvol)>>8;
		right = (data * rightvol)>>8;
		samp->left += left;
		samp->right += right;
	}

	ch->pos += count;
}
"""
