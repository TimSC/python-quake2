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

Platform independent initialization, main loop and frame handling.

=======================================================================
"""
from __future__ import annotations

import sys
import random
pass
from linux import sys_linux, q_shlinux, net_udp
pass
from client import cl_main, cl_scrn, keys
import pygame
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common.shared import rand
from common import argproc
from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from common import zone
from common import netchan
from server import sv_main

"""
#include "header/common.h"
#include <setjmp.h>
"""

developer = None #cvar_t *
modder = None #cvar_t *
timescale = None #cvar_t *
fixedtime = None #cvar_t *
cl_maxfps = None #cvar_t *
dedicated = None #cvar_t *

#extern cvar_t *color_terminal;
#extern cvar_t *logfile_active;
#extern jmp_buf abortframe; /* an ERR_DROP occured, exit the entire frame */

#ifndef DEDICATED_ONLY
log_stats_file = None #FILE *
busywait = None #cvar_t *
cl_async = None #cvar_t *
cl_timedemo = None #cvar_t *
vid_maxfps = None #cvar_t *
host_speeds = None #cvar_t *
log_stats = None #cvar_t *
showtrace = None #cvar_t *
#endif

# host_speeds times
time_before_game = 0 #int
time_after_game = 0 #int
time_before_ref = 0 #int
time_after_ref = 0 #int

# Used in the network- and input paths.
curtime = 0 #int

# Is the game portable?
is_portable = False #qboolean

# Game given by user
userGivenGame = "" #char [MAX_QPATH]

# Game should quit next frame.
# Hack for the signal handlers.
quitnextframe = False #qboolean

# Q2PORT: id's frand and crand, until their users (the client effects, group 11) use frandk and crandk
def frand(): # 0 to 1
	return random.random()

def crand(): # -1 to 1
	return random.random() * 2.0 - 1.0

"""
static YQ2_ATTR_INLINE void Sys_CpuPause(void)
{
#if defined(__GNUC__)
#if (__i386 || __x86_64__)
	asm volatile("pause");
#elif defined(__aarch64__) || (defined(__ARM_ARCH) && __ARM_ARCH >= 7) || defined(__ARM_ARCH_6K__)
	asm volatile("yield");
#elif defined(__powerpc__) || defined(__powerpc64__)
	asm volatile("or 27,27,27");
#elif defined(__riscv) && __riscv_xlen == 64
	asm volatile(".insn i 0x0F, 0, x0, x0, 0x010");
#endif
#elif defined(_MSC_VER)
#if defined(_M_IX86) || defined(_M_X64)
	_mm_pause();
#elif defined(_M_ARM) || defined(_M_ARM64)
	__yield();
#endif
#endif
}
"""

def Qcommon_Buildstring(): #void

	"""
	int i;
	size_t verLen;
	const char* versionString;
	"""


	versionString = "Yamagi Quake II v{}".format(common_h.YQ2VERSION) #va("Yamagi Quake II v%s", YQ2VERSION);
	verLen = len(versionString)

	print("\n{}".format(versionString))

	print("=" * verLen) #for( i = 0; i < verLen; ++i) printf("=");


	#ifndef DEDICATED_ONLY
	print("Client build options:")

	#ifdef USE_CURL
	print(" - cURL HTTP downloads")
	#endif

	#ifdef USE_OPENAL
	print(" - OpenAL audio")
	#endif

	#ifdef SYSTEMWIDE
	print(" - Systemwide installation")
	#endif
	#endif

	#ifdef USE_XDG
	print(" - XDG directory support")
	#endif

	print("Platform: {}".format(common_h.YQ2OSTYPE))
	print("Architecture: {}".format(common_h.YQ2ARCH))

"""
static void
Qcommon_Mainloop(void)
{
	long long newtime;
	long long oldtime = Sys_Microseconds();

	/* The mainloop. The legend. */
	while (1)
	{
#ifndef DEDICATED_ONLY
		if (!cl_timedemo->value)
		{
			// Throttle the game a little bit.
			if (busywait->value)
			{
				long long spintime = Sys_Microseconds();

				while (1)
				{
					/* Give the CPU a hint that this is a very tight
					   spinloop. One PAUSE instruction each loop is
					   enough to reduce power consumption and head
					   dispersion a lot, it's 95°C against 67°C on
					   a Kaby Lake laptop. */
					Sys_CpuPause();

					if (Sys_Microseconds() - spintime >= 5)
					{
						break;
					}
				}
			}
			else
			{
				Sys_Nanosleep(5000);
			}
		}
#else
		Sys_Nanosleep(850000);
#endif

		newtime = Sys_Microseconds();

		// Save global time for network- and input code.
		curtime = (int)(newtime / 1000ll);

		Qcommon_Frame(newtime - oldtime);
		oldtime = newtime;
	}
}
"""

def Qcommon_ExecConfigs(gameStartUp: bool): #qboolean

	cmdparser.Cbuf_AddText("exec default.cfg\n")
	cmdparser.Cbuf_AddText("exec yq2.cfg\n")
	cmdparser.Cbuf_AddText("exec config.cfg\n")
	cmdparser.Cbuf_AddText("exec autoexec.cfg\n")

	if gameStartUp:

		# Process cmd arguments only startup.
		cmdparser.Cbuf_AddEarlyCommands(True)


	cmdparser.Cbuf_Execute()

def checkForHelp(argc: int, argv: list)->bool: #int, char ** (returns qboolean)

	helpArgs = [ "--help", "-h", "-help", "-?", "/?" ]
	numHelpArgs = len(helpArgs) #ARRLEN(helpArgs)

	for i in range(1, argc):

		arg = argv[i]

		for h in range(numHelpArgs):

			if shared_c.Q_stricmp(arg, helpArgs[h]) == 0:

				print("Yamagi Quake II v{}".format(common_h.YQ2VERSION))
				print("Most interesting commandline arguments:")
				print("-h or --help: Show this help")
				print("-cfgdir <path>")
				print("  set the name of your config directory")
				print("-datadir <path>")
				print("  set path to your Quake2 game data (the directory baseq2/ is in)")
				print("-portable")
				print("  Write (savegames, configs, ...) in the binary directory")
				print("+exec <config>")
				print("  execute the given config (mainly relevant for dedicated servers)")
				print("+set <cvarname> <value>")
				print("  Set the given cvar to the given value, e.g. +set vid_fullscreen 0")

				print("\nSome interesting cvars:")
				print("+set game <gamename>")
				print("  start the given addon/mod, e.g. +set game xatrix")
				#ifndef DEDICATED_ONLY
				print("+set vid_fullscreen <0 or 1>")
				print("  start game in windowed (0) or desktop fullscreen (1)")
				print("  or classic fullscreen (2) mode")
				print("+set r_mode <modenumber>")
				print("  start game in resolution belonging to <modenumber>,")
				print("  use -1 for custom resolutions:")
				print("+set r_customwidth <size in pixels>")
				print("+set r_customheight <size in pixels>")
				print("  if r_mode is set to -1, these cvars allow you to specify the")
				print("  width/height of your custom resolution")
				print("+set vid_renderer <renderer>")
				print("  Selects the render backend. Currently available:")
				print("    'gl1'  (the OpenGL 1.x renderer),")
				print("    'gl3'  (the OpenGL 3.2 renderer),")
				print("    'soft' (the software renderer)")
				#endif // DEDICATED_ONLY
				print("\nSee https://github.com/yquake2/yquake2/blob/master/doc/04_cvarlist.md\nfor some more cvars")

				return True




	return False

"""
=================
Qcommon_Init
=================
"""

def Qcommon_Init(): #int argc, char **argv
	# Q2PORT: argc and argv are sys.argv, read by COM_InitArgv

	global developer, modder, timescale, fixedtime, cl_maxfps, dedicated, \
		busywait, cl_async, cl_timedemo, vid_maxfps, host_speeds, log_stats, showtrace, userGivenGame

	# Jump point used in emergency situations.
	#if (YQ2_SETJMP(abortframe))
	#	Sys_Error("Error during initialization");
	# Q2PORT: a Com_Error during initialization ends the program with the abortframe exception

	if checkForHelp(len(sys.argv), sys.argv):

		# ok, --help or similar commandline option was given
		# and info was printed, exit the game now
		sys.exit(1)


	# Print the build and version string
	Qcommon_Buildstring()

	# Q2PORT: pygame stands in for SDL, which Yamagi starts in the backends
	pygame.mixer.pre_init(44100//2)
	pygame.init()

	# Seed PRNG
	rand.randk_seed()

	# Initialize zone malloc().
	zone.Z_Init()

	# Start early subsystems.
	argproc.COM_InitArgv() #argc, argv
	shared_c.Swap_Init()
	cmdparser.Cbuf_Init()
	cmdparser.Cmd_Init()
	cvar.Cvar_Init()

	#ifndef DEDICATED_ONLY
	keys.Key_Init()
	#endif

	# we need to add the early commands twice, because
	# a basedir or cddir needs to be set before execing
	# config files, but we want other parms to override
	# the settings of the config files
	cmdparser.Cbuf_AddEarlyCommands(False)
	cmdparser.Cbuf_Execute()

	# remember the initial game name that might have been set on commandline
	gameCvar = cvar.Cvar_Get("game", "", shared.CVAR_LATCH | shared.CVAR_SERVERINFO)
	game = ""

	if gameCvar.string:

		game = gameCvar.string


	userGivenGame = game[:shared.MAX_QPATH - 1] #Q_strlcpy(userGivenGame, game, sizeof(userGivenGame));

	# The filesystems needs to be initialized after the cvars.
	filesystem.FS_InitFilesystem()

	# Add and execute configuration files.
	Qcommon_ExecConfigs(True)

	# Zone malloc statistics.
	cmdparser.Cmd_AddCommand("z_stats", zone.Z_Stats_f)

	# cvars

	cl_maxfps = cvar.Cvar_Get("cl_maxfps", "-1", shared.CVAR_ARCHIVE)

	developer = cvar.Cvar_Get("developer", "0", 0)
	fixedtime = cvar.Cvar_Get("fixedtime", "0", 0)

	clientserver.color_terminal = cvar.Cvar_Get("colorterminal", "1", shared.CVAR_ARCHIVE)
	clientserver.logfile_active = cvar.Cvar_Get("logfile", "1", shared.CVAR_ARCHIVE)
	modder = cvar.Cvar_Get("modder", "0", 0)
	timescale = cvar.Cvar_Get("timescale", "1", 0)

	#char *s;
	s = "{} {} {} {}".format(common_h.YQ2VERSION, common_h.YQ2ARCH, common_h.BUILD_DATE, common_h.YQ2OSTYPE)
	cvar.Cvar_Get("version", s, shared.CVAR_SERVERINFO | shared.CVAR_NOSET)

	#ifndef DEDICATED_ONLY
	busywait = cvar.Cvar_Get("busywait", "1", shared.CVAR_ARCHIVE)
	cl_async = cvar.Cvar_Get("cl_async", "1", shared.CVAR_ARCHIVE)
	cl_timedemo = cvar.Cvar_Get("timedemo", "0", 0)
	dedicated = cvar.Cvar_Get("dedicated", "0", shared.CVAR_NOSET)
	vid_maxfps = cvar.Cvar_Get("vid_maxfps", "300", shared.CVAR_ARCHIVE)
	host_speeds = cvar.Cvar_Get("host_speeds", "0", 0)
	log_stats = cvar.Cvar_Get("log_stats", "0", 0)
	showtrace = cvar.Cvar_Get("showtrace", "0", 0)
	#else
	#dedicated = Cvar_Get("dedicated", "1", CVAR_NOSET);
	#endif

	# We can't use the clients "quit" command when running dedicated.
	if dedicated.value:

		cmdparser.Cmd_AddCommand("quit", clientserver.Com_Quit)


	# Start late subsystem.
	sys_linux.Sys_Init()
	net_udp.NET_Init()
	netchan.Netchan_Init()
	sv_main.SV_Init()
	#ifndef DEDICATED_ONLY
	cl_main.CL_Init()
	#endif

	# Everythings up, let's add + cmds from command line.
	if not cmdparser.Cbuf_AddLateCommands():

		if not dedicated.value:

			# Start demo loop...
			cmdparser.Cbuf_AddText("d1\n")

		else:

			# ...or dedicated server.
			cmdparser.Cbuf_AddText("dedicated_start\n")


		cmdparser.Cbuf_Execute()

	#ifndef DEDICATED_ONLY
	else:

		# the user asked for something explicit
		# so drop the loading plaque
		cl_scrn.SCR_EndLoadingPlaque()

	#endif

	clientserver.Com_Printf("==== Yamagi Quake II Initialized ====\n\n")
	clientserver.Com_Printf("*************************************\n\n")

	# Call the main loop
	#Qcommon_Mainloop();
	# Q2PORT: sys_linux.main runs the main loop until the platform layer (group 14) is ported


"""
=================
Qcommon_Frame
=================
"""
def Qcommon_Frame (msec): #int
	# Q2PORT: id's Qcommon_Frame(msec), until the client has Yamagi's CL_Frame with packet and
	# render frames (group 10) and Qcommon_Mainloop runs the loop (group 14)

	global host_speeds
	global time_before_game, time_after_game, time_before_ref, time_after_ref

	"""
	char	*s;
	int		time_before, time_between, time_after;

	if (setjmp (abortframe) )
		return;			// an ERR_DROP was thrown

	if ( log_stats->modified )
	{
		log_stats->modified = false;
		if ( log_stats->value )
		{
			if ( log_stats_file )
			{
				fclose( log_stats_file );
				log_stats_file = 0;
			}
			log_stats_file = fopen( "stats.log", "w" );
			if ( log_stats_file )
				fprintf( log_stats_file, "entities,dlights,parts,frame time\n" );
		}
		else
		{
			if ( log_stats_file )
			{
				fclose( log_stats_file );
				log_stats_file = 0;
			}
		}
	}

	if (fixedtime->value)
		msec = fixedtime->value;
	else if (timescale->value)
	{
		msec *= timescale->value;
		if (msec < 1)
			msec = 1;
	}

	if (showtrace->value)
	{
		extern	int c_traces, c_brush_traces;
		extern	int	c_pointcontents;

		Com_Printf ("%4i traces  %4i points\n", c_traces, c_pointcontents);
		c_traces = 0;
		c_brush_traces = 0;
		c_pointcontents = 0;
	}
"""
	try: # if (setjmp (abortframe) ) return;, an ERR_DROP was thrown
		firstLoop = True
		s = None
		while firstLoop or s is not None:
			firstLoop = False
			s = sys_linux.Sys_ConsoleInput ()
			if s is not None:
				cmdparser.Cbuf_AddText ("{}\n".format(s))
	
		cmdparser.Cbuf_Execute ()
	


		if host_speeds.value:
			time_before = q_shlinux.Sys_Milliseconds ()
	
		sv_main.SV_Frame (msec)
	
		if host_speeds.value:
			time_between = q_shlinux.Sys_Milliseconds ()
	
		cl_main.CL_Frame (msec)
	
		if host_speeds.value:
			time_after = q_shlinux.Sys_Milliseconds ()

		if host_speeds.value:
	
			#int			all, sv, gm, cl, rf;

			allt = time_after - time_before
			sv = time_between - time_before
			cl = time_after - time_between
			gm = time_after_game - time_before_game
			rf = time_after_ref - time_before_ref
			sv -= gm
			cl -= rf
			clientserver.Com_Printf ("all:{: 3d} sv:{: 3d} gm:{: 3d} cl:{: 3d} rf:{: 3d}\n".format(
				allt, sv, gm, cl, rf))
	except clientserver.abortframe:
		return

r"""
static void
Qcommon_Frame(int usec)
{
	// For the dedicated server terminal console.
	char *s;

	// Target packetframerate.
	int pfps;

	// Time since last packetframe in microsec.
	static int packetdelta = 1000000;

	// Accumulated time since last server run.
	static int servertimedelta = 0;

	/* A packetframe runs the server and the client,
	   but not the renderer. The minimal interval of
	   packetframes is about 10.000 microsec. If run
	   more often the movement prediction in pmove.c
	   breaks. That's the Q2 variant if the famous
	   125hz bug. */
	qboolean packetframe = true;


	/* Tells the client to shutdown.
	   Used by the signal handlers. */
	if (quitnextframe)
	{
		Cbuf_AddText("quit");
	}


	/* In case of ERR_DROP we're jumping here. Don't know
	   if that' really save but it seems to work. So leave
	   it alone. */
	if (YQ2_SETJMP(abortframe))
	{
		return;
	}


	// Timing debug crap. Just for historical reasons.
	if (fixedtime->value)
	{
		usec = (int)fixedtime->value;
	}
	else if (timescale->value)
	{
		usec *= timescale->value;
	}


	// Target framerate.
	pfps = (int)cl_maxfps->value;


	// Calculate timings.
	packetdelta += usec;
	servertimedelta += usec;


	// Network frame time.
	if (packetdelta < (1000000.0f / pfps)) {
		packetframe = false;
	}


	// Dedicated server terminal console.
	do {
		s = Sys_ConsoleInput();

		if (s) {
			Cbuf_AddText(va("%s\n", s));
		}
	} while (s);

	Cbuf_Execute();


	// Run the serverframe.
	if (packetframe) {
		SV_Frame(servertimedelta);
		servertimedelta = 0;

		// Reset deltas if necessary.
		packetdelta = 0;
	}
}
"""

def Qcommon_Shutdown ():
	# Q2PORT: FS_ShutdownFilesystem, Cvar_Fini, Key_Shutdown and Cmd_Shutdown aren't ported yet

	pass
	#FS_ShutdownFilesystem();
	#Cvar_Fini();
	##ifndef DEDICATED_ONLY
	#Key_Shutdown();
	##endif
	#Cmd_Shutdown();
