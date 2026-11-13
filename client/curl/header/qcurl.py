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

#ifdef USE_CURL

#ifndef QCURL_H
#define QCURL_H

# --------

#include <curl/curl.h>
#include "../../../common/header/common.h"

# Q2PORT: the values of curl.h come from pycurl (pycurl.URL for CURLOPT_URL,
# pycurl.E_OK for CURLE_OK, ...). qcurlInitialized is in client/curl/qcurl.py;
# with pycurl there are no function pointers.

# --------

# True if cURL is initialized.
#extern qboolean qcurlInitialized;

# Loads and initialized cURL.
#qboolean qcurlInit(void);

# Shuts cURL down and unloads it.
#void qcurlShutdown(void);

# --------

#endif // QCURL_H
#endif // USE_CURL
