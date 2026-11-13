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

Prototypes witch are shared between the client, the server and the
game. This is the main game API, changes here will most likely
requiere changes to the game ddl.

=======================================================================
"""
from __future__ import annotations

import time
import platform
from enum import Enum

"""
#include "shared.h"
#include "crc.h"
#include "files.h"
#include "zone.h"
"""

YQ2VERSION = "8.71pre"
BASEDIRNAME	= "baseq2"
APPNAME = "Python Quake II" # Q2PORT: allow the app name to change since we are forked from Yamagi.
VERSION = 3.21	# Q2PORT: id's version number, until its users (common.c, sv_main.c, console.c) are ported

# Q2PORT: YQ2OSTYPE, YQ2ARCH and BUILD_DATE are set by Yamagi's build system; here they come from Python
YQ2OSTYPE = platform.system()	#ifndef YQ2OSTYPE #error YQ2OSTYPE should be defined by the build system

BUILD_DATE = time.strftime("%b %d %Y")	#define BUILD_DATE __DATE__

CFGDIRNAME_SHORT = "yq2"

#if defined(USE_XDG) || defined(_WIN32)
#    #define CFGDIRNAME "YamagiQ2"
#else
CFGDIRNAME = "." + CFGDIRNAME_SHORT
#endif

YQ2ARCH = {"x86_64": "x86_64", "AMD64": "x86_64", "aarch64": "arm64", "arm64": "arm64", "i386": "x86", "i686": "x86"}.get(platform.machine(), platform.machine())

"""
//============================================================================
"""
class sizebuf_t(object):

	def __init__(self):

		self.allowoverflow = False #qboolean, if false, do a Com_Error
		self.overflowed = False #qboolean, set to true if the buffer size failed
		self.data = None #byte	*
		self.maxsize = 0 # int
		self.cursize = 0 # int
		self.readcount = 0 # int

	

"""
void SZ_Init (sizebuf_t *buf, byte *data, int length);
void SZ_Clear (sizebuf_t *buf);
void *SZ_GetSpace (sizebuf_t *buf, int length);
void SZ_Write (sizebuf_t *buf, void *data, int length);
void SZ_Print (sizebuf_t *buf, char *data);	// strcats onto the sizebuf

//============================================================================

struct usercmd_s;
struct entity_state_s;

void MSG_WriteChar (sizebuf_t *sb, int c);
void MSG_WriteByte (sizebuf_t *sb, int c);
void MSG_WriteShort (sizebuf_t *sb, int c);
void MSG_WriteLong (sizebuf_t *sb, int c);
void MSG_WriteFloat (sizebuf_t *sb, float f);
void MSG_WriteString (sizebuf_t *sb, char *s);
void MSG_WriteCoord (sizebuf_t *sb, float f);
void MSG_WritePos (sizebuf_t *sb, vec3_t pos);
void MSG_WriteAngle (sizebuf_t *sb, float f);
void MSG_WriteAngle16 (sizebuf_t *sb, float f);
void MSG_WriteDeltaUsercmd (sizebuf_t *sb, struct usercmd_s *from, struct usercmd_s *cmd);
void MSG_WriteDeltaEntity (struct entity_state_s *from, struct entity_state_s *to, sizebuf_t *msg, qboolean force, qboolean newentity);
void MSG_WriteDir (sizebuf_t *sb, vec3_t vector);


void	MSG_BeginReading (sizebuf_t *sb);

int		MSG_ReadChar (sizebuf_t *sb);
int		MSG_ReadByte (sizebuf_t *sb);
int		MSG_ReadShort (sizebuf_t *sb);
int		MSG_ReadLong (sizebuf_t *sb);
float	MSG_ReadFloat (sizebuf_t *sb);
char	*MSG_ReadString (sizebuf_t *sb);
char	*MSG_ReadStringLine (sizebuf_t *sb);

float	MSG_ReadCoord (sizebuf_t *sb);
void	MSG_ReadPos (sizebuf_t *sb, vec3_t pos);
float	MSG_ReadAngle (sizebuf_t *sb);
float	MSG_ReadAngle16 (sizebuf_t *sb);
void	MSG_ReadDeltaUsercmd (sizebuf_t *sb, struct usercmd_s *from, struct usercmd_s *cmd);

void	MSG_ReadDir (sizebuf_t *sb, vec3_t vector);

void	MSG_ReadData (sizebuf_t *sb, void *buffer, int size);

//============================================================================

extern	qboolean		bigendien;

extern	short	BigShort (short l);
extern	short	LittleShort (short l);
extern	int		BigLong (int l);
extern	int		LittleLong (int l);
extern	float	BigFloat (float l);
extern	float	LittleFloat (float l);

//============================================================================


int	COM_Argc (void);
char *COM_Argv (int arg);	// range and null checked
void COM_ClearArgv (int arg);
int COM_CheckParm (char *parm);
void COM_AddParm (char *parm);

void COM_Init (void);
void COM_InitArgv (int argc, char **argv);

char *CopyString (char *in);

//============================================================================

void Info_Print (char *s);


/* crc.h */

void CRC_Init(unsigned short *crcvalue);
void CRC_ProcessByte(unsigned short *crcvalue, byte data);
unsigned short CRC_Value(unsigned short crcvalue);
unsigned short CRC_Block (byte *start, int count);


"""
"""
==============================================================

PROTOCOL

==============================================================
"""

# protocol.h -- communications protocols

PROTOCOL_VERSION	= 34

#=========================================

PORT_MASTER	= 27900
PORT_CLIENT	= 27901
PORT_SERVER	= 27910

#=========================================

UPDATE_BACKUP	= 16	# copies of entity_state_t to keep buffered
							# must be power of two
UPDATE_MASK		= (UPDATE_BACKUP-1)


#==================
# the svc_strings[] array in cl_parse.c should mirror this
#==================

#
# server to client
#
class svc_ops_e(Enum):

	svc_bad = 0

	# these ops are known to the game dll
	svc_muzzleflash = 1
	svc_muzzleflash2 = 2
	svc_temp_entity = 3
	svc_layout = 4
	svc_inventory = 5

	# the rest are private to the client and server
	svc_nop = 6
	svc_disconnect = 7
	svc_reconnect = 8
	svc_sound = 9					# <see code>
	svc_print = 10					# [byte] id [string] null terminated string
	svc_stufftext = 11				# [string] stuffed into client's console buffer, should be \n terminated
	svc_serverdata = 12				# [long] protocol ...
	svc_configstring = 13			# [short] [string]
	svc_spawnbaseline = 14		
	svc_centerprint = 15				# [string] to put in center of the screen
	svc_download = 16				# [short] size [size bytes]
	svc_playerinfo = 17				# variable
	svc_packetentities = 18			# [...]
	svc_deltapacketentities = 19		# [...]
	svc_frame = 20


#==============================================

#
# client to server
#
class clc_ops_e(Enum):

	clc_bad = 0
	clc_nop = 1 		
	clc_move = 2				# [[usercmd_t]
	clc_userinfo = 3			# [[userinfo string]
	clc_stringcmd = 4			# [string] message


#==============================================

# plyer_state_t communication

PS_M_TYPE			= (1<<0)
PS_M_ORIGIN			= (1<<1)
PS_M_VELOCITY		= (1<<2)
PS_M_TIME			= (1<<3)
PS_M_FLAGS			= (1<<4)
PS_M_GRAVITY		= (1<<5)
PS_M_DELTA_ANGLES	= (1<<6)

PS_VIEWOFFSET		= (1<<7)
PS_VIEWANGLES		= (1<<8)
PS_KICKANGLES		= (1<<9)
PS_BLEND			= (1<<10)
PS_FOV				= (1<<11)
PS_WEAPONINDEX		= (1<<12)
PS_WEAPONFRAME		= (1<<13)
PS_RDFLAGS			= (1<<14)

#==============================================

# user_cmd_t communication

# ms and light always sent, the others are optional
CM_ANGLE1 	= (1<<0)
CM_ANGLE2 	= (1<<1)
CM_ANGLE3 	= (1<<2)
CM_FORWARD	= (1<<3)
CM_SIDE		= (1<<4)
CM_UP		= (1<<5)
CM_BUTTONS	= (1<<6)
CM_IMPULSE	= (1<<7)

#==============================================

# a sound without an ent or pos will be a local only sound
SND_VOLUME		= (1<<0)		# a byte
SND_ATTENUATION	= (1<<1)		# a byte
SND_POS			= (1<<2)		# three coordinates
SND_ENT			= (1<<3)		# a short 0-2: channel, 3-12: entity
SND_OFFSET		= (1<<4)		# a byte, msec offset from frame start

DEFAULT_SOUND_PACKET_VOLUME	= 1.0
DEFAULT_SOUND_PACKET_ATTENUATION = 1.0

#==============================================

# entity_state_t communication

# try to pack the common update flags into the first byte
U_ORIGIN1	= (1<<0)
U_ORIGIN2	= (1<<1)
U_ANGLE2	= (1<<2)
U_ANGLE3	= (1<<3)
U_FRAME8	= (1<<4)		# frame is a byte
U_EVENT		= (1<<5)
U_REMOVE	= (1<<6)		# REMOVE this entity, don't add it
U_MOREBITS1	= (1<<7)		# read one additional byte

# second byte
U_NUMBER16	= (1<<8)		# NUMBER8 is implicit if not set
U_ORIGIN3	= (1<<9)
U_ANGLE1	= (1<<10)
U_MODEL		= (1<<11)
U_RENDERFX8	= (1<<12)		# fullbright, etc
U_EFFECTS8	= (1<<14)		# autorotate, trails, etc
U_MOREBITS2	= (1<<15)		# read one additional byte

# third byte
U_SKIN8		= (1<<16)
U_FRAME16	= (1<<17)		# frame is a short
U_RENDERFX16 = (1<<18)	# 8 + 16 = 32
U_EFFECTS16	= (1<<19)		# 8 + 16 = 32
U_MODEL2	= (1<<20)		# weapons, flags, etc
U_MODEL3	= (1<<21)
U_MODEL4	= (1<<22)
U_MOREBITS3	= (1<<23)		# read one additional byte

# fourth byte
U_OLDORIGIN	= (1<<24)		# FIXME: get rid of this
U_SKIN16	= (1<<25)
U_SOUND		= (1<<26)
U_SOLID		= (1<<27)


"""
==============================================================

CMD

Command text buffering and command execution

==============================================================
*/

/*

Any number of commands can be added in a frame, from several different sources.
Most commands come from either keybindings or console line input, but remote
servers can also send across commands and entire text files can be execed.

The + command line options are also added to the command buffer.

The game starts with a Cbuf_AddText ("exec quake.rc\n"); Cbuf_Execute ();

*/

#define	EXEC_NOW	0		// don't return until completed
#define	EXEC_INSERT	1		// insert at current position, but don't run yet
#define	EXEC_APPEND	2		// add to end of the command buffer

void Cbuf_Init (void);
// allocates an initial text buffer that will grow as needed

void Cbuf_AddText (char *text);
// as new commands are generated from the console or keybindings,
// the text is added to the end of the command buffer.

void Cbuf_InsertText (char *text);
// when a command wants to issue other commands immediately, the text is
// inserted at the beginning of the buffer, before any remaining unexecuted
// commands.

void Cbuf_ExecuteText (int exec_when, char *text);
// this can be used in place of either Cbuf_AddText or Cbuf_InsertText

void Cbuf_AddEarlyCommands (qboolean clear);
// adds all the +set commands from the command line

qboolean Cbuf_AddLateCommands (void);
// adds all the remaining + commands from the command line
// Returns true if any late commands were added, which
// will keep the demoloop from immediately starting

void Cbuf_Execute (void);
// Pulls off \n terminated lines of text from the command buffer and sends
// them through Cmd_ExecuteString.  Stops when the buffer is empty.
// Normally called once per frame, but may be explicitly invoked.
// Do not call inside a command function!

void Cbuf_CopyToDefer (void);
void Cbuf_InsertFromDefer (void);
// These two functions are used to defer any pending commands while a map
// is being loaded

//===========================================================================

/*

Command execution takes a null terminated string, breaks it into tokens,
then searches for a command or variable that matches the first token.

*/

typedef void (*xcommand_t) (void);

void	Cmd_Init (void);

void	Cmd_AddCommand (char *cmd_name, xcommand_t function);
// called by the init functions of other parts of the program to
// register commands and functions to call for them.
// The cmd_name is referenced later, so it should not be in temp memory
// if function is NULL, the command will be forwarded to the server
// as a clc_stringcmd instead of executed locally
void	Cmd_RemoveCommand (char *cmd_name);

qboolean Cmd_Exists (char *cmd_name);
// used by the cvar code to check for cvar / command name overlap

char 	*Cmd_CompleteCommand (char *partial);
// attempts to match a partial command for automatic command line completion
// returns NULL if nothing fits

int		Cmd_Argc (void);
char	*Cmd_Argv (int arg);
char	*Cmd_Args (void);
// The functions that execute commands get their parameters with these
// functions. Cmd_Argv () will return an empty string, not a NULL
// if arg > argc, so string operations are always safe.

void	Cmd_TokenizeString (char *text, qboolean macroExpand);
// Takes a null terminated string.  Does not need to be /n terminated.
// breaks the string up into arg tokens.

void	Cmd_ExecuteString (char *text);
// Parses a single line of text into arguments and tries to execute it
// as if it was typed at the console

void	Cmd_ForwardToServer (void);
// adds the current command line as a clc_stringcmd to the client message.
// things like godmode, noclip, etc, are commands directed to the server,
// so when they are typed in at the console, they will need to be forwarded.
"""
"""
/*
==============================================================

CVAR

==============================================================
*/

/*

cvar_t variables are used to hold scalar or string variables that can be changed or displayed at the console or prog code as well as accessed directly
in C code.

The user can access cvars from the console in three ways:
r_draworder			prints the current value
r_draworder 0		sets the current value to 0
set r_draworder 0	as above, but creates the cvar if not present
Cvars are restricted from having the same names as commands to keep this
interface from being ambiguous.
*/

extern	cvar_t	*cvar_vars;

cvar_t *Cvar_Get (char *var_name, char *value, int flags);
// creates the variable if it doesn't exist, or returns the existing one
// if it exists, the value will not be changed, but flags will be ORed in
// that allows variables to be unarchived without needing bitflags

cvar_t 	*Cvar_Set (char *var_name, char *value);
// will create the variable if it doesn't exist

cvar_t *Cvar_ForceSet (char *var_name, char *value);
// will set the variable even if NOSET or LATCH

cvar_t 	*Cvar_FullSet (char *var_name, char *value, int flags);

void	Cvar_SetValue (char *var_name, float value);
// expands value to a string and calls Cvar_Set

float	Cvar_VariableValue (char *var_name);
// returns 0 if not defined or non numeric

char	*Cvar_VariableString (char *var_name);
// returns an empty string if not defined

char 	*Cvar_CompleteVariable (char *partial);
// attempts to match a partial variable name for command line completion
// returns NULL if nothing fits

void	Cvar_GetLatchedVars (void);
// any CVAR_LATCHED variables that have been set will now take effect

qboolean Cvar_Command (void);
// called by Cmd_ExecuteString when Cmd_Argv(0) doesn't match a known
// command.  Returns true if the command was a variable reference that
// was handled. (print or change)

void 	Cvar_WriteVariables (char *path);
// appends lines containing "set variable value" for all variables
// with the archive flag set to true.

void	Cvar_Init (void);

char	*Cvar_Userinfo (void);
// returns an info string containing all the CVAR_USERINFO cvars

char	*Cvar_Serverinfo (void);
// returns an info string containing all the CVAR_SERVERINFO cvars

extern	qboolean	userinfo_modified;
// this is set each time a CVAR_USERINFO variable is changed
// so that the client knows to send it to the server
"""
"""
/*
==============================================================

NET

==============================================================
*/

// net.h -- quake's interface to the networking layer
"""
PORT_ANY	= -1
MAX_MSGLEN		= 1400		# max length of a message
PACKET_HEADER	= 10			# two ints and a short

class netadrtype_t(Enum):
	NA_LOOPBACK = 0
	NA_BROADCAST = 1
	NA_IP = 2
	NA_IPX = 3
	NA_BROADCAST_IPX = 4
	NA_IP6 = 5
	NA_MULTICAST6 = 6

class netsrc_t(Enum):
	NS_CLIENT = 0
	NS_SERVER = 1

class netadr_t(object):

	def __init__(self):

		self.type = netadrtype_t.NA_LOOPBACK

		self.ip = bytes(16) #byte	[16], an IPv4 address is the first 4
		self.scope_id = 0 #unsigned int
		self.ipx = bytes(10) #byte	[10]

		self.port = 0 #unsigned short, network byte order as in C

	def copy(self):
		# struct assignment, C copies netadr_t by value
		out = netadr_t()
		out.type = self.type
		out.ip = self.ip
		out.scope_id = self.scope_id
		out.ipx = self.ipx
		out.port = self.port
		return out

"""
void		NET_Init (void);
void		NET_Shutdown (void);

void		NET_Config (qboolean multiplayer);

qboolean	NET_GetPacket (netsrc_t sock, netadr_t *net_from, sizebuf_t *net_message);
void		NET_SendPacket (netsrc_t sock, int length, void *data, netadr_t to);

qboolean	NET_CompareAdr (netadr_t a, netadr_t b);
qboolean	NET_CompareBaseAdr (netadr_t a, netadr_t b);
qboolean	NET_IsLocalAddress (netadr_t adr);
char		*NET_AdrToString (netadr_t a);
qboolean	NET_StringToAdr (char *s, netadr_t *a);
void		NET_Sleep(int msec);

//============================================================================
"""

OLD_AVG = 0.99
MAX_LATENT = 32

# netchan_t is common/net_channel.py's NetChannel

"""
extern	netadr_t	net_from;
extern	sizebuf_t	net_message;
extern	byte		net_message_buffer[MAX_MSGLEN];


void Netchan_Init (void);
void Netchan_Setup (netsrc_t sock, netchan_t *chan, netadr_t adr, int qport);

qboolean Netchan_NeedReliable (netchan_t *chan);
void Netchan_Transmit (netchan_t *chan, int length, byte *data);
void Netchan_OutOfBand (int net_socket, netadr_t adr, int length, byte *data);
void Netchan_OutOfBandPrint (int net_socket, netadr_t adr, char *format, ...);
qboolean Netchan_Process (netchan_t *chan, sizebuf_t *msg);

qboolean Netchan_CanReliable (netchan_t *chan);
"""
"""
/*
==============================================================

CMODEL

==============================================================
*/


#include "../qcommon/qfiles.h"

cmodel_t	*CM_LoadMap (char *name, qboolean clientload, unsigned *checksum);
cmodel_t	*CM_InlineModel (char *name);	// *1, *2, etc

int			CM_NumClusters (void);
int			CM_NumInlineModels (void);
char		*CM_EntityString (void);

// creates a clipping hull for an arbitrary box
int			CM_HeadnodeForBox (vec3_t mins, vec3_t maxs);


// returns an ORed contents mask
int			CM_PointContents (vec3_t p, int headnode);
int			CM_TransformedPointContents (vec3_t p, int headnode, vec3_t origin, vec3_t angles);

trace_t		CM_BoxTrace (vec3_t start, vec3_t end,
						  vec3_t mins, vec3_t maxs,
						  int headnode, int brushmask);
trace_t		CM_TransformedBoxTrace (vec3_t start, vec3_t end,
						  vec3_t mins, vec3_t maxs,
						  int headnode, int brushmask,
						  vec3_t origin, vec3_t angles);

byte		*CM_ClusterPVS (int cluster);
byte		*CM_ClusterPHS (int cluster);

int			CM_PointLeafnum (vec3_t p);

// call with topnode set to the headnode, returns with topnode
// set to the first node that splits the box
int			CM_BoxLeafnums (vec3_t mins, vec3_t maxs, int *list,
							int listsize, int *topnode);

int			CM_LeafContents (int leafnum);
int			CM_LeafCluster (int leafnum);
int			CM_LeafArea (int leafnum);

void		CM_SetAreaPortalState (int portalnum, qboolean open);
qboolean	CM_AreasConnected (int area1, int area2);

int			CM_WriteAreaBits (byte *buffer, int area);
qboolean	CM_HeadnodeVisible (int headnode, byte *visbits);

void		CM_WritePortalState (FILE *f);
void		CM_ReadPortalState (FILE *f);
"""
"""
/*
==============================================================

PLAYER MOVEMENT CODE

Common between server and client so prediction matches

==============================================================
*/

extern float pm_airaccelerate;

void Pmove (pmove_t *pmove);
"""
"""
/*
==============================================================

FILESYSTEM

==============================================================
*/
"""

SFF_INPACK = 0x20

"""

void	FS_InitFilesystem (void);
void	FS_SetGamedir (char *dir);
char	*FS_Gamedir (void);
char	*FS_NextPath (char *prevpath);
void	FS_ExecAutoexec (void);

int		FS_FOpenFile (char *filename, FILE **file);
void	FS_FCloseFile (FILE *f);
// note: this can't be called from another DLL, due to MS libc issues

int		FS_LoadFile (char *path, void **buffer);
// a null buffer will just return the file length without loading
// a -1 length is not present

void	FS_Read (void *buffer, int len, FILE *f);
// properly handles partial reads

void	FS_FreeFile (void *buffer);

void	FS_CreatePath (char *path);
"""
"""
/*
==============================================================

MISC

==============================================================
*/
"""
ERR_FATAL	= 0		# exit the entire game with a popup window
ERR_DROP	= 1		# print to console and disconnect from game
ERR_QUIT	= 2		# not an error, just a normal exit

EXEC_NOW	= 0		# don't return until completed
EXEC_INSERT	= 1		# insert at current position, but don't run yet
EXEC_APPEND	= 2		# add to end of the command buffer

PRINT_ALL		= 0
PRINT_DEVELOPER	= 1	# only print when "developer 1"
"""
void		Com_BeginRedirect (int target, char *buffer, int buffersize, void (*flush));
void		Com_EndRedirect (void);
void 		Com_Printf (char *fmt, ...);
void 		Com_DPrintf (char *fmt, ...);
void 		Com_Error (int code, char *fmt, ...);
void 		Com_Quit (void);

int			Com_ServerState (void);		// this should have just been a cvar...
void		Com_SetServerState (int state);

unsigned	Com_BlockChecksum (void *buffer, int length);
byte		COM_BlockSequenceCRCByte (byte *base, int length, int sequence);

float	frand(void);	// 0 ti 1
float	crand(void);	// -1 to 1

extern	cvar_t	*developer;
extern	cvar_t	*dedicated;
extern	cvar_t	*host_speeds;
extern	cvar_t	*log_stats;

extern	FILE *log_stats_file;

// host_speeds times
extern	int		time_before_game;
extern	int		time_after_game;
extern	int		time_before_ref;
extern	int		time_after_ref;

void Z_Free (void *ptr);
void *Z_Malloc (int size);			// returns 0 filled memory
void *Z_TagMalloc (int size, int tag);
void Z_FreeTags (int tag);

void Qcommon_Init (int argc, char **argv);
void Qcommon_Frame (int msec);
void Qcommon_Shutdown (void);
"""
NUMVERTEXNORMALS = 162
"""
extern	vec3_t	bytedirs[NUMVERTEXNORMALS];

// this is in the client code, but can be used for debugging from server
void SCR_DebugGraph (float value, int color);
"""
"""
/*
==============================================================

NON-PORTABLE SYSTEM SERVICES

==============================================================
*/

void	Sys_Init (void);

void	Sys_AppActivate (void);

void	Sys_UnloadGame (void);
void	*Sys_GetGameAPI (void *parms);
// loads the game dll and calls the api init function

char	*Sys_ConsoleInput (void);
void	Sys_ConsoleOutput (char *string);
void	Sys_SendKeyEvents (void);
void	Sys_Error (char *error, ...);
void	Sys_Quit (void);
char	*Sys_GetClipboardData( void );
void	Sys_CopyProtect (void);
"""
"""
/*
==============================================================

CLIENT / SERVER SYSTEMS

==============================================================
*/

void CL_Init (void);
void CL_Drop (void);
void CL_Shutdown (void);
void CL_Frame (int msec);
void Con_Print (char *text);
void SCR_BeginLoadingPlaque (void);

void SV_Init (void);
void SV_Shutdown (char *finalmsg, qboolean reconnect);
void SV_Frame (int msec);
"""

def FS_FileExists(path: str)->bool: #define FS_FileExists(path) (FS_LoadFile2(path, NULL, 0) >= 0)

	from common import filesystem # Q2PORT: the macro, as a function
	return filesystem.FS_LoadFile2(path, 0)[0] >= 0
