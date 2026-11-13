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

import pycurl

from common import clientserver

#ifdef USE_CURL

# --------

#include <curl/curl.h>

#include "header/qcurl.h"
#include "../../common/header/common.h"

# Q2PORT: libcurl is used through pycurl (in requirements.txt), which links
# libcurl itself. So there's no library to find and load (the cl_libcurl cvar)
# and no function pointers to connect (qcurl_easy_init, ...): download.py calls
# pycurl's objects, pycurl.Curl for an easy handle and pycurl.CurlMulti for the
# multi handle.

# --------

# True if cURL is initialized.
qcurlInitialized = False #qboolean

# --------

"""
 * Load libcurl, connect the function pointer
 * and call cURLs global init function.
"""
def qcurlInit()->bool: #void (returns qboolean)

	global qcurlInitialized

	clientserver.Com_Printf("------- curl initialization -------\n")

	assert not qcurlInitialized, "cURL already initialized?!"

	clientserver.Com_Printf("Using %s\n", pycurl.version) # Q2PORT: in place of the library loading

	# And finally the global cURL initialization.
	pycurl.global_init(pycurl.GLOBAL_NOTHING)
	qcurlInitialized = True

	clientserver.Com_Printf("------------------------------------\n\n")

	return True

"""
 * Calls cURLs global shutdown funtion,
 * unloads libcurl and set the function
 * pointers to NULL.
"""
def qcurlShutdown(): #void

	global qcurlInitialized

	if qcurlInitialized:

		clientserver.Com_Printf("Shutting down curl.\n")

		pycurl.global_cleanup()
		qcurlInitialized = False

# --------

#endif // USE_CURL
