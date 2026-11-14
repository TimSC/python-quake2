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
from backends.unix import system, network
pass
from client import cl_main
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c
from common.shared import rand
from common import frame_timing
from common.engine import engine
from common import errors
from common import argproc
from common import clientserver
from common import cmdparser
from common import cvar
from common import filesystem
from common import zone
from common import collision
from common import netchan
from server import sv_main
from client import cl_keyboard
from client import cl_main
from client import cl_screen
from client.vid import vid

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


	versionString = "{} v{}".format(common_h.APPNAME, common_h.YQ2VERSION) #va("Yamagi Quake II v%s", YQ2VERSION);
	verLen = len(versionString)

	print("\n{}".format(versionString))

	print("=" * verLen) #for( i = 0; i < verLen; ++i) printf("=");


	#ifndef DEDICATED_ONLY
	print("Client build options:")

	#ifdef USE_CURL
	print(" + cURL HTTP downloads")
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

def Qcommon_Mainloop(): # (static)

	global curtime

	"""
	long long newtime;
	long long oldtime = Sys_Microseconds();
	"""
	oldtime = system.Sys_Microseconds()

	# The mainloop. The legend.
	while 1:

		#ifndef DEDICATED_ONLY
		if not cl_timedemo.value:

			# Throttle the game a little bit.
			if busywait.value:

				spintime = system.Sys_Microseconds()

				while 1:

					# Give the CPU a hint that this is a very tight
					# spinloop. One PAUSE instruction each loop is
					# enough to reduce power consumption and head
					# dispersion a lot, it's 95°C against 67°C on
					# a Kaby Lake laptop.
					system.Sys_CpuPause()

					if system.Sys_Microseconds() - spintime >= 5:

						break



			else:

				system.Sys_Nanosleep(5000)


		#else
		#Sys_Nanosleep(850000);
		#endif

		newtime = system.Sys_Microseconds()

		# Save global time for network- and input code.
		curtime = int(newtime // 1000)

		Qcommon_Frame(newtime - oldtime)
		oldtime = newtime

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

				print("{} v{}".format(common_h.APPNAME, common_h.YQ2VERSION))
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
	cl_keyboard.Key_Init()
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
	system.Sys_Init()
	network.NET_Init()
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
		cl_screen.SCR_EndLoadingPlaque()

	#endif

	clientserver.Com_Printf(f"==== {common_h.APPNAME} Initialized ====\n\n")
	clientserver.Com_Printf("*************************************\n\n")

	# Call the main loop
	#Qcommon_Mainloop();
	# Q2PORT: system.main calls Qcommon_Mainloop after this returns, until the platform layer (group 14) is ported


# Q2PORT: the client's Qcommon_Frame (#ifndef DEDICATED_ONLY); the dedicated
# server build's one isn't needed, CL_Frame returns early when dedicated is set

def Qcommon_Frame(usec: int): #int (static)

	global log_stats_file

	"""
	// Used for the dedicated server console.
	char *s;

	// Statistics.
	int time_before = 0;
	int time_between = 0;
	int time_after;

	// Target packetframerate.
	float pfps;

	// Target renderframerate.
	float rfps;
	"""
	time_before = 0
	time_between = 0

	# A packetframe runs the server and the client, but not the renderer;
	# a renderframe runs the renderer. See common/frame_timing.py.


	# Tells the client to shutdown.
	# Used by the signal handlers.
	if quitnextframe:

		cmdparser.Cbuf_AddText("quit")



	# In case of ERR_DROP we're jumping here. Don't know
	# if that's really save but it seems to work. So leave
	# it alone.
	try: # if (YQ2_SETJMP(abortframe)) return;

		if log_stats.modified:

			log_stats.modified = False

			if log_stats.value:

				if log_stats_file:

					log_stats_file.close()
					log_stats_file = None


				try:
					log_stats_file = open("stats.log", "w") # Q_fopen("stats.log", "w")
				except OSError:
					log_stats_file = None

				if log_stats_file:

					log_stats_file.write("entities,dlights,parts,frame time\n")


			else:

				if log_stats_file:

					log_stats_file.close()
					log_stats_file = None




		# Timing debug crap. Just for historical reasons.
		if fixedtime.value:

			usec = int(fixedtime.value)

		elif timescale.value:

			usec = int(usec * timescale.value)



		if showtrace.value:

			#extern int c_traces, c_brush_traces;
			#extern int c_pointcontents;

			clientserver.Com_Printf("%4i traces  %4i points\n", collision.c_traces, collision.c_pointcontents)
			collision.c_traces = 0
			collision.c_brush_traces = 0
			collision.c_pointcontents = 0



		# We can render 1000 frames at maximum, because the minimum
		# frametime of the client is 1 millisecond. And of course we
		# need to render something, the framerate can never be less
		# then 1. Cap vid_maxfps between 1 and 999.
		if vid_maxfps.value > 999 or vid_maxfps.value < 1:

			cvar.Cvar_SetValue("vid_maxfps", 999)


		if cl_maxfps.value > 250:

			cvar.Cvar_SetValue("cl_maxfps", 250)


		# The target render and packet frame rates, and which frames run now
		# (common/frame_timing.py)
		vsync = vid.R_IsVSyncActive()
		rfps, pfps = frame_timing.target_rates(vsync, vid.GLimp_GetRefreshRate() if vsync else 0,
			vid_maxfps.value, cl_maxfps.value, cl_async.value != 0.0)
		clock = engine.clock
		packetframe, renderframe = clock.advance(usec, rfps, pfps, bool(cl_timedemo.value),
			cl_async.value != 0.0)

		# Dedicated server terminal console.
		while True: # do { ... } while (s);
			s = system.Sys_ConsoleInput()

			if s:
				cmdparser.Cbuf_AddText("{}\n".format(s))

			if not s:
				break

		cmdparser.Cbuf_Execute()


		if host_speeds.value:

			time_before = system.Sys_Milliseconds()



		# Run the serverframe.
		if packetframe:
			sv_main.SV_Frame(clock.server_delta)
			clock.server_ran()



		if host_speeds.value:

			time_between = system.Sys_Milliseconds()



		# Run the client frame.
		if packetframe or renderframe:
			cl_main.CL_Frame(clock.packet_delta, clock.render_delta, clock.client_delta, packetframe, renderframe)
			clock.client_ran()



		if host_speeds.value:

			"""
			int all, sv, gm, cl, rf;
			"""

			time_after = system.Sys_Milliseconds()
			all_ = time_after - time_before
			sv = time_between - time_before
			cl = time_after - time_between
			gm = time_after_game - time_before_game
			rf = time_after_ref - time_before_ref
			sv -= gm
			cl -= rf
			clientserver.Com_Printf("all:%3i sv:%3i gm:%3i cl:%3i rf:%3i\n", all_, sv, gm, cl, rf)



		# Reset deltas and mark frame.
		clock.frame_done(packetframe, renderframe)

	except errors.DropError:

		return

def Qcommon_Shutdown ():
	# Q2PORT: FS_ShutdownFilesystem, Cvar_Fini, Key_Shutdown and Cmd_Shutdown aren't ported yet

	pass
	#FS_ShutdownFilesystem();
	#Cvar_Fini();
	##ifndef DEDICATED_ONLY
	#Key_Shutdown();
	##endif
	#Cmd_Shutdown();
