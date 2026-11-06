# Open every menu in the running game and draw it, check that sliders and spin
# controls change their cvars, walk a menu with the keys, and press "apply" in
# the video menu (which restarts the renderer).
import os, sys, time
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import OpenGL.GL as GL
from PIL import Image
from linux import sys_linux, gl_glx
from client import cl_main
from client.header import keyboard as keyboard_h
from client.menu import menu, qmenu, videomenu
from client.menu.header import qmenu as qmenu_h
from common import cvar
OUT = os.environ.get("OUT", "/tmp/q2tests")
st = {"t0": None, "step": 0, "menus": None, "frames": 0}

MENUS = ["M_Menu_Main_f", "M_Menu_Game_f", "M_Menu_LoadGame_f", "M_Menu_SaveGame_f", "M_Menu_Multiplayer_f",
	"M_Menu_JoinServer_f", "M_Menu_AddressBook_f", "M_Menu_StartServer_f", "M_Menu_DMOptions_f",
	"M_Menu_PlayerConfig_f", "M_Menu_DownloadOptions_f", "M_Menu_Options_f", "M_Menu_Keys_f",
	"M_Menu_Multiplayer_Keys_f", "M_Menu_Joy_f", "M_Menu_Stick_f", "M_Menu_Gyro_f",
	"M_Menu_ControllerButtons_f", "M_Menu_ControllerAltButtons_f", "M_Menu_Credits_f", "M_Menu_Mods_f",
	"M_Menu_Quit_f"]

def shot(name):
	vp = GL.glGetIntegerv(GL.GL_VIEWPORT); w, h = int(vp[2]), int(vp[3])
	GL.glReadBuffer(GL.GL_BACK)
	Image.frombytes("RGB", (w, h), GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)).transpose(Image.FLIP_TOP_BOTTOM).save(os.path.join(OUT, name))

def slide(item, dir_):
	cv = item.cvar if item.type == qmenu_h.MTYPE_SLIDER else None
	before = cvar.Cvar_VariableValue(cv) if cv else item.curvalue
	if item.type == qmenu_h.MTYPE_SLIDER: qmenu.Slider_DoSlide(item, dir_)
	else: qmenu.SpinControl_DoSlide(item, dir_)
	return before, (cvar.Cvar_VariableValue(cv) if cv else item.curvalue)

oe = gl_glx.GLimp_EndFrame
def EF():
	if cl_main.cls.state.name == "ca_active":
		if st["t0"] is None: st["t0"] = time.time()
		t = time.time() - st["t0"]
		s = st["step"]
		if s == 0 and t > 1:
			st["menus"] = list(MENUS); st["step"] = 1
		elif s == 1:
			# one menu per frame, so each is drawn before the next opens
			if st["menus"]:
				name = st["menus"].pop(0)
				menu.M_ForceMenuOff()
				getattr(menu, name)()
				top = menu.M_GetActiveMenu()
				print("ms: opened %-30s items %d" % (name, top.nitems if top else -1))
				if name == "M_Menu_Options_f": shot("options.png")
			else:
				menu.M_ForceMenuOff()
				print("ms: all menus opened")
				st["step"] = 2
		elif s == 2:
			menu.M_Menu_Options_f()
			print("ms: options volume %s -> %s" % slide(menu.s_options_sfxvolume_slider, 1))
			print("ms: options always run %s -> %s (cl_run %s)" % (*slide(menu.s_options_alwaysrun_box, 1), cvar.Cvar_VariableValue("cl_run")))
			slide(menu.s_options_alwaysrun_box, -1)
			# walk the menu with the keys
			m = menu.M_GetActiveMenu(); c0 = m.cursor
			menu.M_Keydown(keyboard_h.K_DOWNARROW); menu.M_Keydown(keyboard_h.K_DOWNARROW)
			print("ms: options cursor %d -> %d after two down arrows" % (c0, m.cursor))
			menu.M_Keydown(keyboard_h.K_ESCAPE)
			print("ms: after escape the menu depth is %d" % menu.m_menudepth)
			menu.M_ForceMenuOff()
			videomenu.M_Menu_Video_f()
			print("ms: video fov %s -> %s" % slide(videomenu.s_fov_slider, 1))
			slide(videomenu.s_fov_slider, -1)
			shot("video.png")
			videomenu.ApplyChanges(None)
			st["step"] = 3; st["t2"] = t
		elif s == 3 and t > st["t2"] + 6:
			print("ms: after renderer restart: r_mode %s, key_dest %s" % (cvar.Cvar_VariableValue("r_mode"), cl_main.cls.key_dest.name))
			sys.stdout.flush(); os._exit(0)
	return oe()
gl_glx.GLimp_EndFrame = EF
sys_linux.main()
