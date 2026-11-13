"""
 * Copyright (C) 1997-2001 Id Software, Inc.
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
 * Asset downloads over HTTP with CURL.
 *
 * =======================================================================
"""
from __future__ import annotations

import ctypes
import math
from ctypes import c_char_p, c_int, c_long, c_void_p
from enum import Enum

from backends.unix import system
from client import cl_download
from client import cl_main
from client.curl import qcurl
from client.curl.header import download as download_h
from client.curl.header import qcurl as qcurl_h
from client.header import client as client_h
from common import clientserver
from common import cvar
from common import filesystem
from common.header import common as common_h
from common.header import shared
from common.shared import shared as shared_c

#include <ctype.h>
#include "../header/client.h"
#include "header/qcurl.h"

#ifdef USE_CURL

cl_http_downloads = None #cvar_t *
cl_http_filelists = None #cvar_t *
cl_http_verifypeer = None #cvar_t *
cl_http_proxy = None #cvar_t *
cl_http_max_connections = None #cvar_t *
cl_http_show_dw_progress = None #cvar_t *
cl_http_bw_limit_rate = None #cvar_t *
cl_http_bw_limit_tmout = None #cvar_t *

dlquirks = download_h.dlquirks_t() #dlquirks_t dlquirks = { .error = false, .filelist = true, .gamedir = {'\0'} };
dlquirks.filelist = True

class http_abort_t(Enum):

	HTTPDL_ABORT_NONE = 0
	HTTPDL_ABORT_SOFT = 1
	HTTPDL_ABORT_HARD = 2

multi = None #static CURLM *
handleCount = 0 #static int
pendingCount = 0 #static int
abortDownloads = http_abort_t.HTTPDL_ABORT_NONE.value #static int
downloadingPak = False #static qboolean
httpDown = False #static qboolean

#if defined(CURLOPT_XFERINFODATA)
CL_Progresstype = qcurl_h.curl_off_t #typedef curl_off_t CL_Progresstype;
PROGRESSDATA = qcurl_h.CURLOPT_XFERINFODATA
PROGRESSFUNCTION = qcurl_h.CURLOPT_XFERINFOFUNCTION
#endif

# --------

# CURL callback functions
# -----------------------

def _CL_DLHandle(ptr: int)->download_h.dlhandle_t: # Q2PORT: (dlhandle_t *)ptr

	# Q2PORT: the void * given to cURL with CURLOPT_WRITEDATA and PROGRESSDATA
	# is id() of the dlhandle_t in cls.HTTPHandles
	for dl in cl_main.cls.HTTPHandles:

		if id(dl) == ptr:

			return dl

	return None

"""
 * In memory buffer for receiving files. Used
 * as special CURL callback for filelists.
"""
def CL_HTTP_Recv(ptr: int, size: int, nmemb: int, stream: int)->int: #void *, size_t, size_t, void * (returns static size_t)

	dl = _CL_DLHandle(stream) #dlhandle_t *dl = (dlhandle_t *)stream;
	bytes_ = size * nmemb #size_t bytes

	if not dl.fileSize:

		length = qcurl_h.curl_off_t(0) #curl_off_t length = 0;

		qcurl.qcurl_easy_getinfo(dl.curl, qcurl_h.CURLINFO_CONTENT_LENGTH_DOWNLOAD_T, ctypes.byref(length))
		length = length.value

		# Mkay, the remote file should be at least one byte long.
		# Since this is used for paclists only we assume that the
		# file cannot be longer then 256k. Everythings else is
		# considered malicious or a broken server.
		if length < 1 or length > 262144:

			length = 262144.0


		dl.fileSize = math.ceil(length) + 1
		dl.tempBuffer = bytearray(dl.fileSize) # malloc(dl->fileSize)

	# Q2PORT: fix, while instead of else if. The C doubles the buffer once, so a
	# server that says the list is 1 byte long and then sends more than 2 bytes
	# overflows it
	while dl.position + bytes_ >= dl.fileSize:

		dl.fileSize *= 2
		dl.tempBuffer.extend(bytearray(dl.fileSize - len(dl.tempBuffer))) # realloc(dl->tempBuffer, dl->fileSize)


	dl.tempBuffer[dl.position:dl.position + bytes_] = ctypes.string_at(ptr, bytes_) # memcpy (dl->tempBuffer + dl->position, ptr, bytes);
	dl.position += bytes_
	dl.tempBuffer[dl.position] = 0

	return bytes_

def CL_HTTP_CurlWriteCB(data: int, size: int, nmemb: int, userdata: int)->int: #char *, size_t, size_t, void * (returns static size_t)

	dl = _CL_DLHandle(userdata) #dlhandle_t *dl = (dlhandle_t *)userdata;
	return dl.file.write(ctypes.string_at(data, size * nmemb)) # fwrite(data, size, nmemb, dl->file) * size

def CL_HTTP_CurlProgressCB(ptr: int, total: int, now: int, uptotal: int, upnow: int)->int: #void *, CL_Progresstype x4 (returns static int)

	dl = _CL_DLHandle(ptr) #dlhandle_t *dl = (dlhandle_t *)ptr;
	if now:
		dl.fileDownloadedSize = now
		clientserver.Com_DPrintf("CL_HTTP_CurlProgressCB: Downloaded %d/%d\n", dl.fileDownloadedSize, dl.fileSize)

	return 0

# Q2PORT: the callbacks as C function pointers for cURL, kept alive here
_CL_HTTP_Recv_cb = qcurl_h.curl_write_callback(CL_HTTP_Recv)
_CL_HTTP_CurlWriteCB_cb = qcurl_h.curl_write_callback(CL_HTTP_CurlWriteCB)
_CL_HTTP_CurlProgressCB_cb = qcurl_h.curl_xferinfo_callback(CL_HTTP_CurlProgressCB)

# --------

# Helper functions
# ----------------

"""
 * Escapes a path with HTTP encoding. We can't use the
 * function provided by CURL because it encodes to many
 * characters and filter some characters needed by Quake
 * out. Oh Yeah.
"""
def CL_EscapeHTTPPath(filePath: str)->str: #const char *, char *escaped (returns escaped)

	escaped = "" #char *p = escaped;
	length = len(filePath) #size_t len

	for i in range(length):

		c = filePath[i]

		# isalnum((unsigned char)c) in the C locale, ASCII only
		if not (c.isascii() and c.isalnum()) and c != ';' and c != '/' and \
			c != '?' and c != ':' and c != '@' and c != '&' and \
			c != '=' and c != '+' and c != '$' and c != ',' and \
			c != '[' and c != ']' and c != '-' and c != '_' and \
			c != '.' and c != '!' and c != '~' and c != '*' and \
			c != '\'' and c != '(' and c != ')':

			escaped += "%{:02x}".format(ord(c) & 0xff) # sprintf(p, "%%%02x", (byte)filePath[i]);

		else:

			escaped += c



	# Using ./ in a url is legal, but all browsers condense
	# the path and some IDS / request filtering systems act
	# a bit funky if http requests come in with uncondensed
	# paths.
	p = escaped.find("./")

	while p != -1:

		escaped = escaped[:p] + escaped[p + 2:] # memmove (p, p+2, len - (p - escaped) - 1);
		p = escaped.find("./", p)


	return escaped

"""
 * Removes an entry from the download queue.
"""
def CL_RemoveFromQueue(entry: download_h.dlqueue_t)->bool: #dlqueue_t * (returns static qboolean)

	for i, cur in enumerate(cl_main.cls.downloadQueue):

		if cur is entry:

			del cl_main.cls.downloadQueue[i] # last->next = cur->next; free(cur);

			return True


	return False

"""
 * Starts a download. Generates an URL, brings the
 * download handle into defined state and adds it
 * to the CURL multihandle.
"""
def CL_StartHTTPDownload (entry: download_h.dlqueue_t, dl: download_h.dlhandle_t): #dlqueue_t *, dlhandle_t * (static)

	global handleCount, pendingCount

	#char tempFile[MAX_OSPATH];
	#char escapedFilePath[MAX_QPATH*4] = {0};

	length = len(entry.quakePath) #size_t len

	if length > 9 and entry.quakePath[length - 9:] == ".filelist":

		# Special case for filelists. The code identifies
		# filelist by the special handle NULL...
		dl.file = None
		escapedFilePath = CL_EscapeHTTPPath(entry.quakePath)

	else:

		# Full path to the local file.
		dl.filePath = "{}/{}".format(filesystem.FS_Gamedir(), entry.quakePath)

		# Full path to the remote file.
		if dlquirks.gamedir == "":

			tempFile = "/{}".format(entry.quakePath)

		else:

			tempFile = "/{}/{}".format(dlquirks.gamedir, entry.quakePath)


		escapedFilePath = CL_EscapeHTTPPath (tempFile)

		# Create a temporary file where the downloaded data is stored...
		dl.filePath += ".tmp"
		filesystem.FS_CreatePath (dl.filePath)

		# ...and put it into the download handle.
		try:
			dl.file = open(dl.filePath, "wb") # Q_fopen(dl->filePath, "wb")
		except OSError:
			dl.file = None

		if not dl.file:

			clientserver.Com_Printf("HTTP download: Couldn't open %s for writing\n", dl.filePath)
			CL_RemoveFromQueue(entry)
			pendingCount -= 1

			return



	# Make sure that the download handle is in empty state.
	dl.tempBuffer = None # free(dl->tempBuffer)
	dl.fileSize = 0
	dl.position = 0
	dl.fileDownloadedSize = 0
	dl.queueEntry = entry

	# Setup and configure the CURL part of our download handle.
	if not dl.curl:

		dl.curl = qcurl.qcurl_easy_init()


	dl.URL = "{}{}".format(cl_main.cls.downloadServer, escapedFilePath)[:576 - 1]

	setopt = qcurl.qcurl_easy_setopt # Q2PORT: the variadic arguments as their C types
	setopt(dl.curl, qcurl_h.CURLOPT_ENCODING, c_char_p(b""))
	setopt(dl.curl, qcurl_h.CURLOPT_WRITEDATA, c_void_p(id(dl)))

	if dl.file:

		setopt(dl.curl, qcurl_h.CURLOPT_WRITEFUNCTION, _CL_HTTP_CurlWriteCB_cb)

	else:

		setopt(dl.curl, qcurl_h.CURLOPT_WRITEFUNCTION, _CL_HTTP_Recv_cb)


	setopt(dl.curl, qcurl_h.CURLOPT_SSL_VERIFYPEER, c_long(int(cl_http_verifypeer.value)))
	setopt(dl.curl, qcurl_h.CURLOPT_PROXY_SSL_VERIFYPEER, c_long(int(cl_http_verifypeer.value)))
	setopt(dl.curl, qcurl_h.CURLOPT_PROXY, c_char_p(cl_http_proxy.string.encode("latin-1")))
	setopt(dl.curl, qcurl_h.CURLOPT_LOW_SPEED_TIME, c_long(int(cl_http_bw_limit_tmout.value)))
	setopt(dl.curl, qcurl_h.CURLOPT_LOW_SPEED_LIMIT, c_long(int(cl_http_bw_limit_rate.value)))
	setopt(dl.curl, qcurl_h.CURLOPT_CONNECTTIMEOUT, c_long(30))
	setopt(dl.curl, qcurl_h.CURLOPT_FOLLOWLOCATION, c_long(1))
	setopt(dl.curl, qcurl_h.CURLOPT_MAXREDIRS, c_long(5))
	setopt(dl.curl, qcurl_h.CURLOPT_NOPROGRESS, c_long(cl_http_show_dw_progress.value != 1.0))
	setopt(dl.curl, PROGRESSDATA, c_void_p(id(dl)))
	setopt(dl.curl, PROGRESSFUNCTION, _CL_HTTP_CurlProgressCB_cb)
	setopt(dl.curl, qcurl_h.CURLOPT_USERAGENT, c_char_p(cvar.Cvar_VariableString ("version").encode("latin-1")))
	setopt(dl.curl, qcurl_h.CURLOPT_REFERER, c_char_p(cl_main.cls.downloadReferer.encode("latin-1")))
	setopt(dl.curl, qcurl_h.CURLOPT_URL, c_char_p(dl.URL.encode("latin-1")))

	# Q2PORT: fix, the server chooses the URL (dlserver=), so only HTTP and HTTPS,
	# also after a redirect: no file://, smb://, ... (libcurl 7.85, an older one
	# ignores the options)
	setopt(dl.curl, qcurl_h.CURLOPT_PROTOCOLS_STR, c_char_p(b"http,https"))
	setopt(dl.curl, qcurl_h.CURLOPT_REDIR_PROTOCOLS_STR, c_char_p(b"http,https"))

	ret = qcurl.qcurl_multi_add_handle(multi, dl.curl) #size_t ret;

	if ret != qcurl_h.CURLM_OK:

		clientserver.Com_Printf("HTTP download: cURL error - %s\n", qcurl.qcurl_easy_strerror(ret).decode("latin-1"))
		CL_RemoveFromQueue(entry)
		dl.queueEntry = None

		if dl.file:

			dl.file.close()
			dl.file = None
			system.Sys_Remove(dl.filePath)


		if pendingCount:

			pendingCount -= 1


		return


	handleCount += 1

	clientserver.Com_DPrintf("CL_StartHTTPDownload: Fetching %s...\n", dl.URL)
	dl.queueEntry.state = download_h.dlq_state.DLQ_STATE_RUNNING

"""
 * Checks if a line given in a filelist is a
 * valid file and puts it into the download
 * queue.
"""
def CL_CheckAndQueueDownload(path: str): #char * (static)

	# NOTE: The original r1q2 download code in r1q2 allowed
	# only // paths made of plain ASCII chars. YQ2 is more
	# or less UTF-8 clean, so we're allowing all characters.

	# Malicious filelists may have very long lines.
	length = len(path) #size_t

	if length >= shared.MAX_QPATH:

		return


	# The good, old problem with Windows being case sensitive
	# and Unix platforms are not. We're asuming that the
	# the server admin did the right things(tm). That should
	# be more or less save since r1q2, q2pro and q2dos are
	# doing the same. But for the sake of readbility and the
	# general state of my brain we're doing the security
	# checks on an lower case copy of the path.
	lowerPath = path.lower() #char lowerPath[MAX_QPATH]; Q_strlcpy, Q_strlwr

	# All files must have an extension, extensionsless
	# files just make no sense for Quake II.
	i = lowerPath.rfind('.') #char *ext = strrchr(lowerPath, '.');

	if i == -1:

		return


	ext = lowerPath[i + 1:] # ext++;

	if not ext:

		return


	# These file extensions must be in sync with
	# fs_packtypes in filesystem.c!
	pak = False

	if ext == "pak" or ext == "pk2" or \
			ext == "pk3" or ext == "zip":

		pak = True


	# Filter out all filetypes not understood by Quake II.
	if not pak and ext != "pcx" and ext != "wal" and ext != "wav" and ext != "md2" and \
		ext != "sp2" and ext != "tga" and ext != "png" and ext != "jpg" and \
		ext != "bsp" and ext != "ent" and ext != "txt" and ext != "dm2" and \
		ext != "loc":

		clientserver.Com_Printf ("HTTP download: Illegal file type '%s' in filelist\n", ext)

		return


	# Files starting with @ are game local. For example the code
	# wouldn't download conchars.pcx because it already exists in
	# the global scope. If it's prefixed with @ it's downloaded
	# anyways if it doesn't exists in the current game dir.
	gameLocal = False

	if path[:1] == '@':

		if pak:

			clientserver.Com_Printf("HTTP download: @ prefix used on a pak file '%s' in filelist\n", path)

			return


		gameLocal = True
		path = path[1:] # path++;
		length -= 1


	# Make sure that there're no evil paths in the filelist. Most
	# of these should be pretty okay with YQ2 since we've got a much
	# better filesystem as other clients but let's stay consistent.
	#
	# .. -> Don't change to upper dirs.
	# // -> Should be okay
	# \\ -> May fuck some string functions and CURL up. They
	#		 aren't valid URL characters anyways.
	#
	# !pak && !strchr (path, '/') -> Plain files are always loaded
	#								  from and into subdirs.
	#	(pak && strchr(path, '/') -> Paks are always loaded from and
	#								 into the toplevel dir.
	if (".." in path) or ("//" in path) or ('\\' in path) or \
			(not pak and '/' not in path) or (pak and '/' in path):

		clientserver.Com_Printf("HTTP download: Illegal path '%s' in filelist\n", path)

		return


	# Let's see if we've already got that file.
	exists = False

	if gameLocal or pak:

		if pak:

			# We need to check paks ourself.
			gamePath = "{}/{}".format(filesystem.FS_Gamedir(), path) #char gamePath[MAX_OSPATH];

			try:
				f = open(gamePath, "rb") # Q_fopen(gamePath, "rb")
			except OSError:
				f = None

			if f:

				exists = True
				f.close()


		else:

			# All other files are checked by the filesystem.
			exists = filesystem.FS_FileInGamedir(path)


		if not exists:

			# Queue the file for download.
			CL_QueueHTTPDownload(path, False)


	else:

		# Check if the file is already there and download it if not.
		cl_download.CL_CheckOrDownloadFile(path)

"""
 * Parses a filelist referenced in the memory
 * buffer in the given dlhandle_t.
"""
def CL_ParseFileList(dl: download_h.dlhandle_t): #dlhandle_t * (static)

	if not cl_http_filelists.value:

		return


	if dl.tempBuffer is None:
		return


	# char *list = dl->tempBuffer; Q2PORT: the C string, up to the first NUL
	list_ = bytes(dl.tempBuffer[:dl.position]).split(b"\0", 1)[0].decode("latin-1")

	while True:

		p = list_.find('\n') #char *p = strchr(list, '\n');

		if p != -1:

			#p[0] = 0;

			if list_[:p]:

				CL_CheckAndQueueDownload(list_[:p])


			list_ = list_[p + 1:]

		else:

			if list_:

				CL_CheckAndQueueDownload(list_)


			break



	dl.tempBuffer = None # free(dl->tempBuffer)

"""
 * A pak file was just downloaded. Go through the
 * download queue and check if we can cancel some
 * downloads.
"""
def CL_ReVerifyHTTPQueue (): #void (static)

	global pendingCount

	pendingCount = 0

	for q in list(cl_main.cls.downloadQueue): # Q2PORT: a copy, CL_RemoveFromQueue changes the list

		if q.state == download_h.dlq_state.DLQ_STATE_NOT_STARTED:

			if common_h.FS_FileExists(q.quakePath):

				CL_RemoveFromQueue(q)

			else:

				pendingCount += 1

def _CL_IsPak(path: str)->bool: # Q2PORT: the !strcmp(path + len - 4, ".pak") || ... tests

	return path[-4:] == ".pak" or path[-4:] == ".pk2" or path[-4:] == ".pk3" or path[-4:] == ".zip"

"""
 * Processesall finished downloads. React on
 * errors, if there're none process the file.
"""
def CL_FinishHTTPDownload(): #void (static)

	global pendingCount, handleCount, downloadingPak, abortDownloads

	"""
	CURL *curl;
	char tempName[MAX_OSPATH];
	dlhandle_t *dl = NULL;
	int	msgs_in_queue;
	qboolean isFile;
	size_t i;
	"""
	dl = None
	msgs_in_queue = c_int(0)

	while True: # do

		# Get a message from CURL.
		msg = qcurl.qcurl_multi_info_read(multi, ctypes.byref(msgs_in_queue))

		if not msg:

			return


		msg = msg.contents

		if msg.msg != qcurl_h.CURLMSG_DONE:

			if msgs_in_queue.value > 0: # Q2PORT: a continue in a do while tests the condition

				continue

			break


		# Find the download handle for the message.
		curl = msg.easy_handle

		for i in range(download_h.MAX_HTTP_HANDLES):

			if cl_main.cls.HTTPHandles[i].curl == curl:

				dl = cl_main.cls.HTTPHandles[i]
				break

		else:

			clientserver.Com_Error(shared.ERR_DROP, "CL_FinishHTTPDownload: Handle not found")


		# Some files aren't saved but read
		# into memory buffers. This is used
		# for filelists only.
		if dl.file:

			isFile = True

			# Mkay, it's a file. Let's
			# close it's handle.
			dl.file.close()
			dl.file = None

		else:

			isFile = False


		# All downloads might have been aborted.
		# This is the case if the backend (or the
		# whole client) shuts down.
		if pendingCount:

			pendingCount -= 1


		# The file finished downloading, it's
		# handle it's now empty and ready for
		# reuse.
		handleCount -= 1

		# Get the download result (success, some
		# error, etc.) from CURL and process it.
		result = msg.data.result #CURLcode
		responseCode = c_long(0)

		# Q2PORT: the switch; the 200/404 case falls through to the fatal one
		fallthrough = False

		if result == qcurl_h.CURLE_HTTP_RETURNED_ERROR or result == qcurl_h.CURLE_OK:

			qcurl.qcurl_easy_getinfo(curl, qcurl_h.CURLINFO_RESPONSE_CODE, ctypes.byref(responseCode))

			if responseCode.value == 404:

				clientserver.Com_Printf("HTTP download: %s - File Not Found\n", dl.queueEntry.quakePath)

				# We got a 404, reset pak downloading state...
				if _CL_IsPak(dl.queueEntry.quakePath):

					downloadingPak = False


				# ...remove the target file...
				if isFile:

					system.Sys_Remove(dl.filePath)


				# ...remove it from the CURL multihandle...
				qcurl.qcurl_multi_remove_handle(multi, dl.curl)
				CL_RemoveFromQueue(dl.queueEntry)
				dl.queueEntry = None

				# ...and communicate the error.
				if isFile:

					dlquirks.error = True
					isFile = False

			elif responseCode.value == 200:

				clientserver.Com_Printf("HTTP download: %s - OK\n", dl.queueEntry.quakePath)

				# This wasn't a file, so it must be a filelist.
				if not isFile and not abortDownloads:

					CL_ParseFileList(dl)
					CL_RemoveFromQueue(dl.queueEntry)
					dl.queueEntry = None

			else:

				# Everything that's not 200 and 404 is fatal, fall through.
				fallthrough = True


		# Q2PORT: and CURLE_UNSUPPORTED_PROTOCOL, a redirect to something other
		# than HTTP(S), which CURLOPT_REDIR_PROTOCOLS_STR refuses
		if fallthrough or result == qcurl_h.CURLE_COULDNT_RESOLVE_HOST or \
			result == qcurl_h.CURLE_COULDNT_CONNECT or result == qcurl_h.CURLE_COULDNT_RESOLVE_PROXY or \
			result == qcurl_h.CURLE_UNSUPPORTED_PROTOCOL:

			clientserver.Com_Printf("HTTP download: %s - Server broken, aborting\n", dl.queueEntry.quakePath)

			# The download failed. Reset pak downloading state...
			if _CL_IsPak(dl.queueEntry.quakePath):

				downloadingPak = False


			# remove the temporary file...
			if isFile:

				system.Sys_Remove(dl.filePath)
				isFile = False


			# ...and the handle from CURLs mutihandle.
			qcurl.qcurl_multi_remove_handle(multi, dl.curl)

			# Special case: We're already aborting HTTP downloading,
			# so we can't just kill everything. Otherwise we'll get
			# stuck.
			if abortDownloads:

				CL_RemoveFromQueue(dl.queueEntry)
				dl.queueEntry = None


			# Abort all HTTP downloads.
			CL_CancelHTTPDownloads (True)
			CL_RemoveFromQueue(dl.queueEntry)
			dl.queueEntry = None

		elif result != qcurl_h.CURLE_HTTP_RETURNED_ERROR and result != qcurl_h.CURLE_OK: # default:

			clientserver.Com_Printf ("HTTP download: cURL error - %s\n", qcurl.qcurl_easy_strerror(result).decode("latin-1"))

			# The download failed. Clear the Remove the temporary file...
			if isFile:

				system.Sys_Remove(dl.filePath)
				isFile = False


			# ...and the handle from CURLs mutihandle.
			qcurl.qcurl_multi_remove_handle (multi, dl.curl)
			CL_RemoveFromQueue(dl.queueEntry)
			dl.queueEntry = None


		if isFile:

			# Rename the temporary file to it's final location
			tempName = "{}/{}".format(filesystem.FS_Gamedir(), dl.queueEntry.quakePath)
			system.Sys_Rename(dl.filePath, tempName)

			# Pak files are special because they contain
			# other files that we may be downloading...
			# The list of file types must be consistent with fs_packtypes in filesystem.c.
			if _CL_IsPak(tempName):

				filesystem.FS_AddPAKFromGamedir(dl.queueEntry.quakePath)
				CL_ReVerifyHTTPQueue ()
				downloadingPak = False


			CL_RemoveFromQueue(dl.queueEntry)
			dl.queueEntry = None


		# Remove the file fo CURLs multihandle.
		qcurl.qcurl_multi_remove_handle (multi, dl.curl)

		if not (msgs_in_queue.value > 0): # while (msgs_in_queue > 0);

			break



	# No more downloads are in in flight, so...
	if handleCount == 0:

		if abortDownloads == http_abort_t.HTTPDL_ABORT_SOFT.value:

			# ...if we're soft aborting we're done.
			abortDownloads = http_abort_t.HTTPDL_ABORT_NONE.value

		elif abortDownloads == http_abort_t.HTTPDL_ABORT_HARD.value:

			# ...if we're hard aborting we need to prevent future downloads.
			cl_main.cls.downloadServerRetry = cl_main.cls.downloadServer
			cl_main.cls.downloadServer = ""



	# All downloads done. Let's check if we've got more files to
	# request. This can be the case if we've processed a filelist
	# or downloaded a BSP that references other assets.
	if cl_main.cls.state == client_h.connstate_t.ca_connected and not CL_PendingHTTPDownloads():

		cl_download.CL_RequestNextDownload()

"""
 * Returns a free download handle.
"""
def CL_GetFreeDLHandle()->download_h.dlhandle_t: #void (returns static dlhandle_t *)

	for i in range(download_h.MAX_HTTP_HANDLES):

		dl = cl_main.cls.HTTPHandles[i]

		if not dl.queueEntry:

			return dl



	return None

"""
 * Starts the next download.
"""
def CL_StartNextHTTPDownload(): #void (static)

	global downloadingPak

	for q in cl_main.cls.downloadQueue: #dlqueue_t *q = &cls.downloadQueue; while (q->next)

		if q.state == download_h.dlq_state.DLQ_STATE_NOT_STARTED:

			dl = CL_GetFreeDLHandle()

			if not dl:

				return


			CL_StartHTTPDownload(q, dl)

			if _CL_IsPak(q.quakePath):

				downloadingPak = True


			break

# --------

# Startup and shutdown
# --------------------

"""
 * Initializes CURL.
"""
def CL_InitHTTPDownloads (): #void

	# We're initializing the cURL backend here because
	# currently we're the only user. As soon as there
	# are other users this must be moved up into the
	# global client intialization.
	qcurl.qcurlInit()

"""
 * Resets the internal state and - in case
 * of full shutdown - shuts CURL down.
"""
def CL_HTTP_Cleanup(fullShutdown: bool): #qboolean

	global multi, httpDown

	if fullShutdown and httpDown:

		return


	# Cleanup all internal handles.
	for i in range(download_h.MAX_HTTP_HANDLES):

		dl = cl_main.cls.HTTPHandles[i]

		if dl.file:

			dl.file.close()
			system.Sys_Remove (dl.filePath)
			dl.file = None


		if dl.tempBuffer is not None:

			dl.tempBuffer = None # free(dl->tempBuffer)


		if dl.curl:

			if multi:

				qcurl.qcurl_multi_remove_handle(multi, dl.curl)


			qcurl.qcurl_easy_cleanup(dl.curl)
			dl.curl = None


		dl.queueEntry = None


	# Cleanup download queue.
	cl_main.cls.downloadQueue.clear() # the free() loop

	# Cleanup CURL multihandle.
	if multi:

		qcurl.qcurl_multi_cleanup(multi)
		multi = None


	# Shutdown CURL.
	if fullShutdown:

		# This must be moved up into the generic
		# client shutdown as soon as there're
		# other users of the cURL backend.
		qcurl.qcurlShutdown()
		httpDown = True

# --------

# Public functions
# ----------------

"""
 * The server hand us a new HTTP URL. Nuke
 * the internal state to start over.
"""
def CL_SetHTTPServer (URL: str): #const char *

	global abortDownloads, handleCount, pendingCount, multi

	# This code abuses the download server setting to
	# determine if HTTP downloads are possible. So if
	# we don't set a download server, no downloads are
	# queued and run. :)
	if not qcurl.qcurlInitialized:

		cl_main.cls.downloadServer = ""
		return


	CL_HTTP_Cleanup(False)

	# Q2PORT: fix, the server chooses the URL; anything but HTTP(S) is refused
	# (cURL would fail each download and the map wouldn't load), so the files
	# come over UDP
	if URL[:7].lower() != "http://" and URL[:8].lower() != "https://":

		clientserver.Com_Printf("HTTP download: Ignoring a download server that isn't http:// or https://: %s\n", URL)
		cl_main.cls.downloadServer = ""
		return


	# Cleanup download queues.
	cl_main.cls.downloadQueue.clear() # the free() loop and memset (&cls.downloadQueue, 0, sizeof(cls.downloadQueue));

	# Cleanup internal state.
	abortDownloads = http_abort_t.HTTPDL_ABORT_NONE.value
	handleCount = pendingCount = 0
	cl_main.cls.downloadServerRetry = ""
	dlquirks.error = False

	# Remove trailing / from URL if any.
	cleanURL = URL

	if cleanURL[-1:] == '/': # Q2PORT: the C reads before the string for an empty URL

		cleanURL = cleanURL[:-1]


	cl_main.cls.downloadServer = cleanURL[:512 - 2] # Q_strlcpy(cls.downloadServer, cleanURL, sizeof(cls.downloadServer) - 1);

	# Initializes a new multihandle.
	if multi:

		clientserver.Com_Error(shared.ERR_DROP, "HTTP download: Still have old handle?!")


	multi = qcurl.qcurl_multi_init()

"""
 * Cancels all downloads and clears the queue.
"""
def CL_CancelHTTPDownloads(permKill: bool): #qboolean

	global abortDownloads, pendingCount

	if permKill:

		cl_main.CL_ResetPrecacheCheck()
		abortDownloads = http_abort_t.HTTPDL_ABORT_HARD.value

	else:

		abortDownloads = http_abort_t.HTTPDL_ABORT_SOFT.value


	for q in list(cl_main.cls.downloadQueue): # Q2PORT: a copy, CL_RemoveFromQueue changes the list

		if q.state == download_h.dlq_state.DLQ_STATE_NOT_STARTED:

			CL_RemoveFromQueue(q)



	if not pendingCount and not handleCount and abortDownloads == http_abort_t.HTTPDL_ABORT_HARD.value:

		cl_main.cls.downloadServer = ""


	pendingCount = 0

"""
 * This function should be called from old UDP download code
 * during the precache phase to determine if HTTP downloads
 * for the requested files are possible. Queues the download
 * and returns true if yes, returns fales if not.
"""
def CL_QueueHTTPDownload(quakePath: str, gamedirForFilelist: bool)->bool: #const char *, qboolean (returns qboolean)

	global pendingCount

	# Not HTTP servers were send by the server, HTTP is disabled
	# or the client is shutting down and we're wrapping up.
	if not cl_main.cls.downloadServer or abortDownloads or not cl_http_downloads.value:

		return False


	# Mkay, now that the first download is queued we want
	# the generic(!) filelist.
	needList = False

	if dlquirks.filelist and cl_http_filelists.value:

		needList = True
		dlquirks.filelist = False


	# Queue the download.
	for q in cl_main.cls.downloadQueue:

		# The generic code may request the same
		# file more than one time. *sigh*
		if quakePath == q.quakePath:

			return True



	q = download_h.dlqueue_t() # q->next = malloc(sizeof(*q));
	cl_main.cls.downloadQueue.append(q)
	q.state = download_h.dlq_state.DLQ_STATE_NOT_STARTED
	q.quakePath = quakePath[:shared.MAX_QPATH - 2] # Q_strlcpy(q->quakePath, quakePath, sizeof(q->quakePath) - 1);

	# Let's download the generic filelist if necessary.
	if needList:

		if gamedirForFilelist:

			fileList = "/{}{}".format(dlquirks.gamedir, ".filelist") #char fileList[MAX_OSPATH];
			CL_QueueHTTPDownload(fileList, False)

		else:

			CL_QueueHTTPDownload("/.filelist", False)



	# If we just queued a .bsp file ask for it's map
	# filelist. I don't think that this is good idea.
	# Cause a filelist can specifiy a .bsp that again
	# specifies a filelist... But r1q2 chose this way,
	# others followed and we have no choice but doing
	# the same.
	length = len(quakePath) #size_t len

	if cl_http_filelists.value and length > 4 and quakePath[length - 4:].lower() == ".bsp":

		#char listPath[MAX_OSPATH];
		#char filePath[MAX_OSPATH];

		if dlquirks.gamedir == "":

			filePath = "/{}".format(quakePath)

		else:

			filePath = "/{}/{}".format(dlquirks.gamedir, quakePath)


		listPath = shared_c.COM_StripExtension(filePath)
		listPath += ".filelist"

		CL_QueueHTTPDownload(listPath, False)


	# If we're here CL_FinishHTTPDownload() is guaranteed to be called.
	pendingCount += 1

	clientserver.Com_Printf("HTTP download: %s - Queued\n", q.quakePath)

	return True

"""
 * Returns true if still downloads pending and false
 * if not. Used by the old UDP code during precache
 * phase to determine if it's necessary to wait for
 * outstanding download.
"""
def CL_PendingHTTPDownloads()->bool: #void (returns qboolean)

	if not cl_main.cls.downloadServer:

		return False


	return (pendingCount + handleCount) > 0

"""
 * Calls CURL to perform the actual downloads.
 * Must be called every frame, otherwise CURL
 * will starve.
"""
def CL_RunHTTPDownloads(): #void

	global handleCount

	#int	newHandleCount;
	#CURLMcode ret;
	newHandleCount = c_int(0)

	# No HTTP server given or not initialized.
	if not cl_main.cls.downloadServer:

		return


	# Kick CURL into action.
	while True: # do

		ret = qcurl.qcurl_multi_perform(multi, ctypes.byref(newHandleCount))

		if newHandleCount.value < handleCount:

			CL_FinishHTTPDownload()
			handleCount = newHandleCount.value


		if ret != qcurl_h.CURLM_CALL_MULTI_PERFORM:
			break


	# Somethings gone very wrong.
	if ret != qcurl_h.CURLM_OK:

		clientserver.Com_Printf("HTTP download: cURL error - %s\n", qcurl.qcurl_multi_strerror(ret).decode("latin-1"))
		CL_CancelHTTPDownloads(True)


	# Not enough downloads running, start some more.
	if pendingCount and abortDownloads == http_abort_t.HTTPDL_ABORT_NONE.value and \
			handleCount < cl_http_max_connections.value and \
			not downloadingPak:

		CL_StartNextHTTPDownload()

#endif /* USE_CURL */
