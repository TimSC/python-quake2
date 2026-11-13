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

import ctypes
from ctypes import c_int, c_int64, c_size_t, c_void_p

#ifdef USE_CURL

#ifndef QCURL_H
#define QCURL_H

# --------

#include <curl/curl.h>
#include "../../../common/header/common.h"

# Q2PORT: the values and types of the cURL headers (curl.h, multi.h) the
# download code uses. qcurlInitialized and the function pointers
# (qcurl_easy_init, ...) are the module globals of client/curl/qcurl.py.

CURLOPTTYPE_LONG			= 0 # curl.h
CURLOPTTYPE_OBJECTPOINT		= 10000
CURLOPTTYPE_FUNCTIONPOINT	= 20000
CURLOPTTYPE_STRINGPOINT		= CURLOPTTYPE_OBJECTPOINT
CURLOPTTYPE_CBPOINT			= CURLOPTTYPE_OBJECTPOINT

CURLOPT_WRITEDATA				= CURLOPTTYPE_CBPOINT + 1
CURLOPT_URL						= CURLOPTTYPE_STRINGPOINT + 2
CURLOPT_PROXY					= CURLOPTTYPE_STRINGPOINT + 4
CURLOPT_WRITEFUNCTION			= CURLOPTTYPE_FUNCTIONPOINT + 11
CURLOPT_REFERER					= CURLOPTTYPE_STRINGPOINT + 16
CURLOPT_USERAGENT				= CURLOPTTYPE_STRINGPOINT + 18
CURLOPT_LOW_SPEED_LIMIT			= CURLOPTTYPE_LONG + 19
CURLOPT_LOW_SPEED_TIME			= CURLOPTTYPE_LONG + 20
CURLOPT_NOPROGRESS				= CURLOPTTYPE_LONG + 43
CURLOPT_FOLLOWLOCATION			= CURLOPTTYPE_LONG + 52
CURLOPT_XFERINFODATA			= CURLOPTTYPE_CBPOINT + 57
CURLOPT_SSL_VERIFYPEER			= CURLOPTTYPE_LONG + 64
CURLOPT_MAXREDIRS				= CURLOPTTYPE_LONG + 68
CURLOPT_CONNECTTIMEOUT			= CURLOPTTYPE_LONG + 78
CURLOPT_ACCEPT_ENCODING			= CURLOPTTYPE_STRINGPOINT + 102
CURLOPT_ENCODING				= CURLOPT_ACCEPT_ENCODING # the old name
CURLOPT_XFERINFOFUNCTION		= CURLOPTTYPE_FUNCTIONPOINT + 219
CURLOPT_PROXY_SSL_VERIFYPEER	= CURLOPTTYPE_LONG + 248
CURLOPT_PROTOCOLS_STR			= CURLOPTTYPE_STRINGPOINT + 318 # libcurl 7.85
CURLOPT_REDIR_PROTOCOLS_STR		= CURLOPTTYPE_STRINGPOINT + 319 # libcurl 7.85

CURLINFO_LONG	= 0x200000
CURLINFO_OFF_T	= 0x600000
CURLINFO_RESPONSE_CODE				= CURLINFO_LONG + 2
CURLINFO_CONTENT_LENGTH_DOWNLOAD_T	= CURLINFO_OFF_T + 15

CURLE_OK					= 0 # CURLcode
CURLE_UNSUPPORTED_PROTOCOL	= 1
CURLE_COULDNT_RESOLVE_PROXY	= 5
CURLE_COULDNT_RESOLVE_HOST	= 6
CURLE_COULDNT_CONNECT		= 7
CURLE_HTTP_RETURNED_ERROR	= 22

CURLM_CALL_MULTI_PERFORM	= -1 # CURLMcode, multi.h
CURLM_OK					= 0

CURLMSG_NONE	= 0 # CURLMSG, multi.h
CURLMSG_DONE	= 1

CURL_GLOBAL_NOTHING = 0

curl_off_t = c_int64

# size_t (*curl_write_callback)(char *buffer, size_t size, size_t nitems, void *outstream)
curl_write_callback = ctypes.CFUNCTYPE(c_size_t, c_void_p, c_size_t, c_size_t, c_void_p)

# int (*curl_xferinfo_callback)(void *clientp, curl_off_t dltotal, curl_off_t dlnow, curl_off_t ultotal, curl_off_t ulnow)
curl_xferinfo_callback = ctypes.CFUNCTYPE(c_int, c_void_p, curl_off_t, curl_off_t, curl_off_t, curl_off_t)

class _CURLMsg_data(ctypes.Union):

	_fields_ = [
		("whatever", c_void_p),	# message-specific data
		("result", c_int),		# CURLcode, return code for transfer
	]

class CURLMsg(ctypes.Structure): # multi.h

	_fields_ = [
		("msg", c_int),				# CURLMSG, what this message means
		("easy_handle", c_void_p),	# CURL *, the handle it concerns
		("data", _CURLMsg_data),
	]

# --------

#endif // QCURL_H
#endif // USE_CURL
