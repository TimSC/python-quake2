
from __future__ import annotations

pass
from client import cl_cin
from common import filesystem

filesystem.FS_InitFilesystem()

cl_cin.SCR_PlayCinematic("idlog.cin")

cl_cin.SCR_RunCinematic()

while cl_cin.cin.pic_pending:
	cl_cin.SCR_RunCinematic()

cl_cin.wavout.close()
cl_cin.wavout = None


