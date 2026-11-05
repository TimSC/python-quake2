# Check the greyed menu items, the sound quality option and the texture quality option in the running game.
import os, sys, time
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
import OpenGL.GL as GL
from PIL import Image
from linux import sys_linux, gl_glx, vid_menu, vid_so, qgl_linux
from client import cl_main, menu, qmenu, snd_dma
pass
from ref_gl import gl_image
from common import cvar
OUT = os.environ.get("OUT", "/tmp/q2tests")
st = {"t0": None, "step": 0, "shots": []}

def shot(name):
	vp = GL.glGetIntegerv(GL.GL_VIEWPORT); w, h = int(vp[2]), int(vp[3])
	GL.glReadBuffer(GL.GL_BACK)
	Image.frombytes("RGB", (w, h), GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)).transpose(Image.FLIP_TOP_BOTTOM).save(os.path.join(OUT, name))

def slide(item, direc):
	before = item.curvalue
	if item.type == menu.MTYPE_SLIDER: qmenu.Slider_DoSlide(item, direc)
	else: qmenu.SpinControl_DoSlide(item, direc)
	return before, item.curvalue

def biggest_upload():
	return max((t.upload_width or 0) for t in gl_image.gltextures if t.name and t.name.startswith("textures/"))

oe = gl_glx.GLimp_EndFrame
def EF():
	if cl_main.cls.state.name == "ca_active":
		if st["t0"] is None: st["t0"] = time.time()
		t = time.time() - st["t0"]
		s = st["step"]
		if s == 0 and t > 1:
			menu.M_Menu_Options_f(); st["step"] = 1
		elif s == 1 and t > 2:
			shot("options.png")
			for it in (menu.s_options_cdvolume_box, menu.s_options_compatibility_list):
				print("ms: options %-20s greyed=%s slide %s -> %s" % (it.name, bool(it.flags & menu.QMF_GRAYED), *slide(it, 1)))
			print("ms: options sound quality shows %r (s_loadas8bit=%s)" % (menu.s_options_quality_list.itemnames[menu.s_options_quality_list.curvalue], cvar.Cvar_VariableValue("s_loadas8bit")))
			print("ms: mixer before:", pygame.mixer.get_init())
			# sound quality: high (the callback calls re.EndFrame, so move on to the next step first)
			st["step"] = 2; st["t1"] = t
			menu.s_options_quality_list.curvalue = 1; menu.UpdateSoundQualityFunc(None)
		elif s == 2 and t > st["t1"] + 1:
			print("ms: after 'high': s_khz=%s mixer=%s" % (cvar.Cvar_VariableValue("s_khz"), pygame.mixer.get_init()))
			snd_dma.S_StartLocalSound("misc/menu1.wav")
			st["step"] = 99
			menu.s_options_quality_list.curvalue = 0; menu.UpdateSoundQualityFunc(None)
			st["step"] = 2
			print("ms: after 'low': s_khz=%s mixer=%s" % (cvar.Cvar_VariableValue("s_khz"), pygame.mixer.get_init()))
			snd_dma.S_StartLocalSound("misc/menu2.wav")
			menu.M_ForceMenuOff()
			vid_menu.VID_MenuInit()
			print("ms: video 8-bit textures greyed=%s slide %s -> %s" % (bool(vid_menu.s_paletted_texture_box.flags & menu.QMF_GRAYED), *slide(vid_menu.s_paletted_texture_box, 1)))
			st["up0"] = biggest_upload()
			print("ms: texture quality slider %s, gl_picmip %s, largest world texture upload %d" % (vid_menu.s_tq_slider.curvalue, cvar.Cvar_VariableValue("gl_picmip"), st["up0"]))
			vid_menu.s_tq_slider.curvalue = 1	# gl_picmip 2
			vid_menu.ApplyChanges(None) if vid_menu.ApplyChanges.__code__.co_argcount else vid_menu.ApplyChanges()
			print("ms: after apply: gl_picmip %s, vid_ref.modified %s" % (cvar.Cvar_VariableValue("gl_picmip"), vid_so.vid_ref.modified))
			st["step"] = 3; st["t2"] = t
		elif s == 3 and t > st["t2"] + 8:
			print("ms: after renderer restart: largest world texture upload %d (was %d)" % (biggest_upload(), st["up0"]))
			shot("picmip2.png")
			cvar.Cvar_SetValue("gl_picmip", 0)
			sys.stdout.flush(); os._exit(0)
	return oe()
gl_glx.GLimp_EndFrame = EF
sys_linux.main()
