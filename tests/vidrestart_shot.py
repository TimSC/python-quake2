# Restart the video system while standing still, then screenshot and count world polygons drawn.
import os, sys, time
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import OpenGL.GL as GL
from PIL import Image
from linux import sys_linux, gl_glx
from client import cl_main
pass
from ref_gl import gl_rmain
from common import cmdparser
t0 = [None]; st = {"restart": False, "shot": False}
oe = gl_glx.GLimp_EndFrame
def EF():
	if cl_main.cls.state.name == "ca_active":
		if t0[0] is None: t0[0] = time.time()
		t = time.time() - t0[0]
		if t > 2 and not st["restart"]:
			cmdparser.Cbuf_AddText("vid_restart\n"); st["restart"] = True; t0[0] = time.time(); t = 0
			print("vr: vid_restart issued")
		elif st["restart"] and int(t) in (3, 6, 9, 12) and st.get("last") != int(t):
			st["last"] = int(t)
			vp = GL.glGetIntegerv(GL.GL_VIEWPORT); w, h = int(vp[2]), int(vp[3])
			GL.glReadBuffer(GL.GL_BACK)
			Image.frombytes("RGB", (w, h), GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)).transpose(Image.FLIP_TOP_BOTTOM).save(os.environ.get("SHOT", "/tmp/q2tests/vr_t%d.png") % int(t))
			from client import cl_scrn, console
			print("vr: t=%d polys %d viewcluster %s old %s key_dest %s con.current %.0f vid %dx%d refdef %dx%d" % (t, gl_rmain.c_brush_polys, gl_rmain.r_viewcluster, gl_rmain.r_oldviewcluster, cl_main.cls.key_dest.name, cl_scrn.scr_con_current, gl_rmain.vid.width, gl_rmain.vid.height, cl_main.cl.refdef.width, cl_main.cl.refdef.height))
			if int(t) == 12: sys.stdout.flush(); os._exit(0)
	return oe()
gl_glx.GLimp_EndFrame = EF
sys_linux.main()
