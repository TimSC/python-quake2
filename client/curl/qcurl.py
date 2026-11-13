"""
 * Copyright (C) 2018 Yamagi
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or (at
 * your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 *
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 *
 * =======================================================================
 *
 * CURL backend for Quake II.
 *
 * =======================================================================
"""
from __future__ import annotations

from ctypes import c_char_p, c_int, c_long, c_void_p, POINTER

from backends.unix import system
from client.curl.header import qcurl as qcurl_h
from common import clientserver
from common import cvar
from common.header import shared

#ifdef USE_CURL

# --------

#include <curl/curl.h>

#include "header/qcurl.h"
#include "../../common/header/common.h"

# --------

# True if cURL is initialized.
qcurlInitialized = False #qboolean

# Pointer to the dynamic library.
curlhandle = None #static void *

# CVars
cl_libcurl = None #static cvar_t *

# Function pointers to cURL.
qcurl_easy_cleanup = None #void (*)(CURL *curl)
qcurl_easy_init = None #CURL *(*)(void)
qcurl_easy_getinfo = None #CURLcode (*)(CURL *curl, CURLINFO info, ...)
qcurl_easy_setopt = None #CURLcode (*)(CURL *curl, CURLoption option, ...)
qcurl_easy_strerror = None #const char *(*)(CURLcode)

qcurl_global_cleanup = None #void (*)(void)
qcurl_global_init = None #CURLcode (*)(long flags)

qcurl_multi_add_handle = None #CURLMcode (*)(CURLM *multi_handle, CURL *curl_handle)
qcurl_multi_cleanup = None #CURLMcode (*)(CURLM *multi_handle)
qcurl_multi_info_read = None #CURLMsg *(*)(CURLM *multi_handle, int *msgs_in_queue)
qcurl_multi_init = None #CURLM *(*)(void)
qcurl_multi_perform = None #CURLMcode (*)(CURLM *multi_handle, int *running_handles)
qcurl_multi_remove_handle = None #CURLMcode (*)(CURLM *multi_handle, CURL *curl_handle)
qcurl_multi_strerror = None #const char *(*)(CURLMcode)

# Q2PORT: the prototypes of the function pointers above, as ctypes (restype,
# argtypes). curl_easy_getinfo and curl_easy_setopt are variadic: ctypes passes
# the extra arguments as given, so the callers wrap them in c_long, c_char_p, ...
_prototypes = {
	"curl_easy_cleanup": (None, [c_void_p]),
	"curl_easy_init": (c_void_p, []),
	"curl_easy_getinfo": (c_int, [c_void_p, c_int]),
	"curl_easy_setopt": (c_int, [c_void_p, c_int]),
	"curl_easy_strerror": (c_char_p, [c_int]),

	"curl_global_cleanup": (None, []),
	"curl_global_init": (c_int, [c_long]),

	"curl_multi_add_handle": (c_int, [c_void_p, c_void_p]),
	"curl_multi_cleanup": (c_int, [c_void_p]),
	"curl_multi_info_read": (POINTER(qcurl_h.CURLMsg), [c_void_p, POINTER(c_int)]),
	"curl_multi_init": (c_void_p, []),
	"curl_multi_perform": (c_int, [c_void_p, POINTER(c_int)]),
	"curl_multi_remove_handle": (c_int, [c_void_p, c_void_p]),
	"curl_multi_strerror": (c_char_p, [c_int]),
}

# --------

"""
 * Load libcurl, connect the function pointer
 * and call cURLs global init function.
"""
def qcurlInit()->bool: #void (returns qboolean)

	global qcurlInitialized, curlhandle, cl_libcurl
	global qcurl_easy_cleanup, qcurl_easy_init, qcurl_easy_getinfo, qcurl_easy_setopt, qcurl_easy_strerror
	global qcurl_global_cleanup, qcurl_global_init
	global qcurl_multi_add_handle, qcurl_multi_cleanup, qcurl_multi_info_read, qcurl_multi_init, \
		qcurl_multi_perform, qcurl_multi_remove_handle, qcurl_multi_strerror

	clientserver.Com_Printf("------- curl initialization -------\n")

	assert not qcurlInitialized, "cURL already initialized?!"

	# Most systems have only one distinct name for the
	# libcurl, loading that one will be successfull in
	# at least 99% of all cases. But Linux, the mother
	# of chaos, is more complicated. Debian / Ubuntu
	# alone has 6 possible names... So:
	#  - Let's try whatever the user has written into
	#    the cl_libcurl cvar first.
	#  - If that fails try all possible names until we
	#    find a working one.
	#  - If we found one put it into cl_libcurl, so we
	#    don't need to iterate trought the whole list
	#    the next time the game is started.
	#  - If we found none error out.
	#ifdef __APPLE__
	#elif __linux__
	libcurl = [ "libcurl.so.3", "libcurl.so.4", "libcurl-gnutls.so.3", #const char *libcurl[]
		"libcurl-gnutls.so.4", "libcurl-nss.so.3", "libcurl-nss.so.4", "libcurl.so",
		None ]
	#endif

	# Mkay, let's try to find a working libcurl.
	cl_libcurl = cvar.Cvar_Get("cl_libcurl", libcurl[0], shared.CVAR_ARCHIVE)
	if (".." in cl_libcurl.string) or (":" in cl_libcurl.string) or ("/" in cl_libcurl.string) or ("\\" in cl_libcurl.string):

		clientserver.Com_Printf("cl_libcurl must not contain '..', ':', '/' or '\\': %s\n", cl_libcurl.string)
		return _qcurlInit_error() # goto error;


	clientserver.Com_Printf("Loading library: %s\n", cl_libcurl.string)
	_, curlhandle = system.Sys_LoadLibrary(cl_libcurl.string, None)

	if not curlhandle:

		clientserver.Com_Printf("Loading %s failed!\n", cl_libcurl.string)

		i = 0
		while libcurl[i] is not None:

			# Tried that one already.
			if cl_libcurl.string == libcurl[i]:

				i += 1
				continue


			clientserver.Com_Printf("Loading library: %s\n", libcurl[i])
			_, curlhandle = system.Sys_LoadLibrary(libcurl[i], None)

			if not curlhandle:

				# No luck with this one.
				clientserver.Com_Printf("Loading %s failed!\n", libcurl[i])
				i += 1
				continue

			else:

				# Got one!
				cvar.Cvar_Set("cl_libcurl", libcurl[i])
				break


		if not curlhandle:

			return _qcurlInit_error() # goto error;



	# libcurl loaded sucessfully, connect the pointers.
	qcurl_easy_cleanup = CONCURL("curl_easy_cleanup")
	qcurl_easy_init = CONCURL("curl_easy_init")
	qcurl_easy_getinfo = CONCURL("curl_easy_getinfo")
	qcurl_easy_setopt = CONCURL("curl_easy_setopt")
	qcurl_easy_strerror = CONCURL("curl_easy_strerror")

	qcurl_global_cleanup = CONCURL("curl_global_cleanup")
	qcurl_global_init = CONCURL("curl_global_init")

	qcurl_multi_add_handle = CONCURL("curl_multi_add_handle")
	qcurl_multi_cleanup = CONCURL("curl_multi_cleanup")
	qcurl_multi_info_read = CONCURL("curl_multi_info_read")
	qcurl_multi_init = CONCURL("curl_multi_init")
	qcurl_multi_perform = CONCURL("curl_multi_perform")
	qcurl_multi_remove_handle = CONCURL("curl_multi_remove_handle")
	qcurl_multi_strerror = CONCURL("curl_multi_strerror")

	# Q2PORT: CONCURL's "if (!var) goto error;", for all of them at once
	if None in (qcurl_easy_cleanup, qcurl_easy_init, qcurl_easy_getinfo, qcurl_easy_setopt,
		qcurl_easy_strerror, qcurl_global_cleanup, qcurl_global_init, qcurl_multi_add_handle,
		qcurl_multi_cleanup, qcurl_multi_info_read, qcurl_multi_init, qcurl_multi_perform,
		qcurl_multi_remove_handle, qcurl_multi_strerror):

		return _qcurlInit_error() # goto error;


	# And finally the global cURL initialization.
	qcurl_global_init(qcurl_h.CURL_GLOBAL_NOTHING)
	qcurlInitialized = True

	clientserver.Com_Printf("------------------------------------\n\n")

	return True

def _qcurlInit_error()->bool: # Q2PORT: the error: label of qcurlInit()

	qcurlShutdown()

	clientserver.Com_Printf("------------------------------------\n\n")

	return False

def CONCURL(sym: str): # Q2PORT: #define CONCURL(var, sym), returns var

	# var = Sys_GetProcAddress(curlhandle, sym);
	func = system.Sys_GetProcAddress(curlhandle, sym)
	if func is not None:
		func.restype, func.argtypes = _prototypes[sym] # Q2PORT: the type of the pointer the C assigns it to
	return func

"""
 * Calls cURLs global shutdown funtion,
 * unloads libcurl and set the function
 * pointers to NULL.
"""
def qcurlShutdown(): #void

	global qcurlInitialized, curlhandle
	global qcurl_easy_cleanup, qcurl_easy_init, qcurl_easy_getinfo, qcurl_easy_setopt, qcurl_easy_strerror
	global qcurl_global_cleanup, qcurl_global_init
	global qcurl_multi_add_handle, qcurl_multi_cleanup, qcurl_multi_info_read, qcurl_multi_init, \
		qcurl_multi_perform, qcurl_multi_remove_handle

	if qcurlInitialized:

		clientserver.Com_Printf("Shutting down curl.\n")

		qcurl_global_cleanup()
		qcurlInitialized = False


	qcurl_easy_cleanup = None
	qcurl_easy_init = None
	qcurl_easy_getinfo = None
	qcurl_easy_setopt = None
	qcurl_easy_strerror = None

	qcurl_global_cleanup = None
	qcurl_global_init = None

	qcurl_multi_add_handle = None
	qcurl_multi_cleanup = None
	qcurl_multi_info_read = None
	qcurl_multi_init = None
	qcurl_multi_perform = None
	qcurl_multi_remove_handle = None

	if curlhandle:

		system.Sys_FreeLibrary(curlhandle)
		curlhandle = None

# --------

#endif // USE_CURL
