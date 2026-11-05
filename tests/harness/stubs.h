// Stubbed engine services for the collision and pmove harnesses.
// Built with -DYQ2 against Yamagi's src/common, otherwise against id's 3.21 source.
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#ifdef YQ2
#include "header/common.h"
#define CSTR const char
#else
#include "qcommon.h"
#define CSTR char
#endif

static cvar_t dummy_cvar;
cvar_t *Cvar_Get (CSTR *name, CSTR *value, int flags) { dummy_cvar.name = (char *)name; dummy_cvar.string = (char *)value; dummy_cvar.value = 0; return &dummy_cvar; }
float Cvar_VariableValue (CSTR *name) { return 0; }
#ifdef HARNESS_PRINT
void Com_Printf (CSTR *fmt, ...) { va_list a; va_start (a, fmt); vprintf (fmt, a); va_end (a); }
#else
void Com_Printf (CSTR *fmt, ...) { }
#endif
void Com_DPrintf (CSTR *fmt, ...) { }
void Com_Error (int code, CSTR *fmt, ...) { va_list a; va_start (a, fmt); vfprintf (stderr, fmt, a); va_end (a); fprintf (stderr, "\n"); exit (1); }
int FS_LoadFile (CSTR *path, void **buffer)
{
	FILE *f = fopen (getenv ("BSP"), "rb"); long n;
	if (!f) { if (buffer) *buffer = NULL; return -1; }
	fseek (f, 0, SEEK_END); n = ftell (f); fseek (f, 0, SEEK_SET);
	if (buffer) { *buffer = malloc (n); fread (*buffer, 1, n, f); }
	fclose (f); return n;
}
void FS_FreeFile (void *buf) { free (buf); }
#ifdef YQ2
void *Z_Malloc (size_t size) { return calloc (1, size); }
void Z_Free (void *ptr) { free (ptr); }
int FS_Read (void *buffer, int size, fileHandle_t f) { return 0; }
static cvar_t sv_entfile_cvar;
cvar_t *sv_entfile = &sv_entfile_cvar;	/* value 0: use the map's own entity string */
unsigned short CRC_Block (const byte *start, int count) { return 0; }
qboolean snd_is_underwater;	/* pmove.c sets it for the client's sound */
#else
void FS_Read (void *buffer, int len, FILE *f) { fread (buffer, 1, len, f); }
#endif
