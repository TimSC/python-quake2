"""
 * Copyright (C) 1997-2001 Id Software, Inc.
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
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
 * USA.
 *
 * =======================================================================
 *
 * Header for the HTTP / cURL download stuff.
 *
 * =======================================================================
"""
from __future__ import annotations

from enum import Enum

#ifdef USE_CURL

#ifndef DOWNLOAD_H
#define DOWNLOAD_H

# Number of max. parallel downloads.
MAX_HTTP_HANDLES = 4

#include <curl/curl.h>
#include "../../../common/header/common.h"

class dlq_state(Enum):

	DLQ_STATE_NOT_STARTED = 0
	DLQ_STATE_RUNNING = 1

class dlqueue_t(object):

	def __init__(self):

		#struct dlqueue_s *next; (cls.downloadQueue is a list)
		self.quakePath = "" #char [MAX_QPATH]
		self.state = dlq_state.DLQ_STATE_NOT_STARTED #dlq_state

	def __repr__(self):

		return "dlqueue_t({!r}, {})".format(self.quakePath, self.state.name)

class dlhandle_t(object):

	def __init__(self):

		self.curl = None #CURL *
		self.filePath = "" #char [MAX_OSPATH]
		self.file = None #FILE *
		self.queueEntry = None #dlqueue_t *
		self.fileSize = 0 #size_t
		self.position = 0 #size_t
		self.fileDownloadedSize = 0 #size_t
		self.URL = "" #char [576]
		self.tempBuffer = None #char *, a bytearray

class dlquirks_t(object):

	def __init__(self):

		self.error = False #qboolean
		self.filelist = False #qboolean
		self.gamedir = "" #char [MAX_QPATH]

#extern dlquirks_t dlquirks;

#extern cvar_t *cl_http_downloads;
#extern cvar_t *cl_http_filelists;
#extern cvar_t *cl_http_verifypeer;
#extern cvar_t *cl_http_proxy;
#extern cvar_t *cl_http_max_connections;
#extern cvar_t *cl_http_show_dw_progress;
#extern cvar_t *cl_http_bw_limit_rate;
#extern cvar_t *cl_http_bw_limit_tmout;

#void CL_CancelHTTPDownloads(qboolean permKill);
#void CL_InitHTTPDownloads(void);
#qboolean CL_QueueHTTPDownload(const char *quakePath, qboolean gamedirForFilelist);
#void CL_RunHTTPDownloads(void);
#qboolean CL_PendingHTTPDownloads(void);
#void CL_SetHTTPServer(const char *URL);
#void CL_HTTP_Cleanup(qboolean fullShutdown);

#endif // DOWNLOAD_H
#endif // USE_CURL
