"""
Q2PORT: the SDL 2 calls the port uses, done with pyglet.

Yamagi's platform code (client/vid/glimp_sdl2.c, client/input/sdl2.c and the
renderers' *_sdl.c) talks to SDL 2. The port has no SDL; this module gives
those files the same calls, names and constants, made with pyglet (windows,
GL contexts, events, display modes) and X11 (gamma ramps), so that the ports
of the C files can stay line by line. Only what the port calls is here.

The differences from SDL that the callers see:
 - pyglet creates the GL context together with the window, so the GL
   attributes are read in SDL_CreateWindow and SDL_GL_CreateContext returns
   the window's context.
 - pyglet reports key symbols, not scancodes. The scancodes come from the
   symbol through a US layout table.
 - adaptive vsync (swap interval -1) isn't supported.
Sound is not here: it is OpenAL (client/sound/qal.py, openal.py).
"""
from __future__ import annotations

import ctypes

import pyglet

# pyglet's hidden shadow window would make an extra GL context, and its GL error
# checks would trip over errors left by the renderers' PyOpenGL calls
pyglet.options['shadow_window'] = False
pyglet.options['debug_gl'] = False

import pyglet.window
from pyglet.window import key as pyglet_key
from pyglet.window import mouse as pyglet_mouse

SDL_MAJOR_VERSION = 2 # the API this module follows

#
# SDL_Init
#
SDL_INIT_TIMER = 0x00000001
SDL_INIT_AUDIO = 0x00000010
SDL_INIT_VIDEO = 0x00000020
SDL_INIT_JOYSTICK = 0x00000200
SDL_INIT_HAPTIC = 0x00001000
SDL_INIT_GAMECONTROLLER = 0x00002000
SDL_INIT_EVENTS = 0x00004000
SDL_INIT_SENSOR = 0x00008000
SDL_INIT_EVERYTHING = (SDL_INIT_TIMER | SDL_INIT_AUDIO | SDL_INIT_VIDEO | SDL_INIT_EVENTS |
	SDL_INIT_JOYSTICK | SDL_INIT_HAPTIC | SDL_INIT_GAMECONTROLLER | SDL_INIT_SENSOR)

#
# SDL_video.h
#
SDL_WINDOW_FULLSCREEN = 0x00000001
SDL_WINDOW_OPENGL = 0x00000002
SDL_WINDOW_SHOWN = 0x00000004
SDL_WINDOW_FULLSCREEN_DESKTOP = (SDL_WINDOW_FULLSCREEN | 0x00001000)
SDL_WINDOW_ALLOW_HIGHDPI = 0x00002000

SDL_WINDOWPOS_UNDEFINED_MASK = 0x1FFF0000

def SDL_WINDOWPOS_UNDEFINED_DISPLAY(X: int)->int:
	return SDL_WINDOWPOS_UNDEFINED_MASK | X

SDL_WINDOWPOS_UNDEFINED = SDL_WINDOWPOS_UNDEFINED_DISPLAY(0)

def SDL_WINDOWPOS_ISUNDEFINED(X: int)->bool:
	return (X & 0xFFFF0000) == SDL_WINDOWPOS_UNDEFINED_MASK

SDL_HINT_VIDEO_MINIMIZE_ON_FOCUS_LOSS = "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS"

# SDL_GLattr
SDL_GL_RED_SIZE = 0
SDL_GL_GREEN_SIZE = 1
SDL_GL_BLUE_SIZE = 2
SDL_GL_ALPHA_SIZE = 3
SDL_GL_BUFFER_SIZE = 4
SDL_GL_DOUBLEBUFFER = 5
SDL_GL_DEPTH_SIZE = 6
SDL_GL_STENCIL_SIZE = 7
SDL_GL_STEREO = 12
SDL_GL_MULTISAMPLEBUFFERS = 13
SDL_GL_MULTISAMPLESAMPLES = 14
SDL_GL_ACCELERATED_VISUAL = 15
SDL_GL_CONTEXT_MAJOR_VERSION = 17
SDL_GL_CONTEXT_MINOR_VERSION = 18
SDL_GL_CONTEXT_FLAGS = 20
SDL_GL_CONTEXT_PROFILE_MASK = 21

# SDL_GLprofile
SDL_GL_CONTEXT_PROFILE_CORE = 0x0001
SDL_GL_CONTEXT_PROFILE_COMPATIBILITY = 0x0002
SDL_GL_CONTEXT_PROFILE_ES = 0x0004

# SDL_GLcontextFlag
SDL_GL_CONTEXT_DEBUG_FLAG = 0x0001
SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG = 0x0002

#
# SDL_events.h
#
SDL_QUIT = 0x100
SDL_WINDOWEVENT = 0x200
SDL_KEYDOWN = 0x300
SDL_KEYUP = 0x301
SDL_TEXTINPUT = 0x303
SDL_MOUSEMOTION = 0x400
SDL_MOUSEBUTTONDOWN = 0x401
SDL_MOUSEBUTTONUP = 0x402
SDL_MOUSEWHEEL = 0x403
SDL_FIRSTEVENT = 0
SDL_LASTEVENT = 0xFFFF

# SDL_WindowEventID
SDL_WINDOWEVENT_SHOWN = 1
SDL_WINDOWEVENT_HIDDEN = 2
SDL_WINDOWEVENT_EXPOSED = 3
SDL_WINDOWEVENT_MOVED = 4
SDL_WINDOWEVENT_RESIZED = 5
SDL_WINDOWEVENT_SIZE_CHANGED = 6
SDL_WINDOWEVENT_MINIMIZED = 7
SDL_WINDOWEVENT_MAXIMIZED = 8
SDL_WINDOWEVENT_RESTORED = 9
SDL_WINDOWEVENT_ENTER = 10
SDL_WINDOWEVENT_LEAVE = 11
SDL_WINDOWEVENT_FOCUS_GAINED = 12
SDL_WINDOWEVENT_FOCUS_LOST = 13
SDL_WINDOWEVENT_CLOSE = 14

# SDL_mouse.h
SDL_BUTTON_LEFT = 1
SDL_BUTTON_MIDDLE = 2
SDL_BUTTON_RIGHT = 3
SDL_BUTTON_X1 = 4
SDL_BUTTON_X2 = 5

#
# SDL_keycode.h: SDL_Keymod
#
KMOD_NONE = 0x0000
KMOD_LSHIFT = 0x0001
KMOD_RSHIFT = 0x0002
KMOD_LCTRL = 0x0040
KMOD_RCTRL = 0x0080
KMOD_LALT = 0x0100
KMOD_RALT = 0x0200
KMOD_LGUI = 0x0400
KMOD_RGUI = 0x0800
KMOD_NUM = 0x1000
KMOD_CAPS = 0x2000
KMOD_MODE = 0x4000
KMOD_SCROLL = 0x8000
KMOD_CTRL = KMOD_LCTRL | KMOD_RCTRL
KMOD_SHIFT = KMOD_LSHIFT | KMOD_RSHIFT
KMOD_ALT = KMOD_LALT | KMOD_RALT
KMOD_GUI = KMOD_LGUI | KMOD_RGUI

#
# SDL_scancode.h: SDL_Scancode
#
SDL_SCANCODE_UNKNOWN = 0
SDL_SCANCODE_A = 4
SDL_SCANCODE_B = 5
SDL_SCANCODE_C = 6
SDL_SCANCODE_D = 7
SDL_SCANCODE_E = 8
SDL_SCANCODE_F = 9
SDL_SCANCODE_G = 10
SDL_SCANCODE_H = 11
SDL_SCANCODE_I = 12
SDL_SCANCODE_J = 13
SDL_SCANCODE_K = 14
SDL_SCANCODE_L = 15
SDL_SCANCODE_M = 16
SDL_SCANCODE_N = 17
SDL_SCANCODE_O = 18
SDL_SCANCODE_P = 19
SDL_SCANCODE_Q = 20
SDL_SCANCODE_R = 21
SDL_SCANCODE_S = 22
SDL_SCANCODE_T = 23
SDL_SCANCODE_U = 24
SDL_SCANCODE_V = 25
SDL_SCANCODE_W = 26
SDL_SCANCODE_X = 27
SDL_SCANCODE_Y = 28
SDL_SCANCODE_Z = 29
SDL_SCANCODE_1 = 30
SDL_SCANCODE_2 = 31
SDL_SCANCODE_3 = 32
SDL_SCANCODE_4 = 33
SDL_SCANCODE_5 = 34
SDL_SCANCODE_6 = 35
SDL_SCANCODE_7 = 36
SDL_SCANCODE_8 = 37
SDL_SCANCODE_9 = 38
SDL_SCANCODE_0 = 39
SDL_SCANCODE_RETURN = 40
SDL_SCANCODE_ESCAPE = 41
SDL_SCANCODE_BACKSPACE = 42
SDL_SCANCODE_TAB = 43
SDL_SCANCODE_SPACE = 44
SDL_SCANCODE_MINUS = 45
SDL_SCANCODE_EQUALS = 46
SDL_SCANCODE_LEFTBRACKET = 47
SDL_SCANCODE_RIGHTBRACKET = 48
SDL_SCANCODE_BACKSLASH = 49
SDL_SCANCODE_NONUSHASH = 50
SDL_SCANCODE_SEMICOLON = 51
SDL_SCANCODE_APOSTROPHE = 52
SDL_SCANCODE_GRAVE = 53
SDL_SCANCODE_COMMA = 54
SDL_SCANCODE_PERIOD = 55
SDL_SCANCODE_SLASH = 56
SDL_SCANCODE_CAPSLOCK = 57
SDL_SCANCODE_F1 = 58
SDL_SCANCODE_F2 = 59
SDL_SCANCODE_F3 = 60
SDL_SCANCODE_F4 = 61
SDL_SCANCODE_F5 = 62
SDL_SCANCODE_F6 = 63
SDL_SCANCODE_F7 = 64
SDL_SCANCODE_F8 = 65
SDL_SCANCODE_F9 = 66
SDL_SCANCODE_F10 = 67
SDL_SCANCODE_F11 = 68
SDL_SCANCODE_F12 = 69
SDL_SCANCODE_PRINTSCREEN = 70
SDL_SCANCODE_SCROLLLOCK = 71
SDL_SCANCODE_PAUSE = 72
SDL_SCANCODE_INSERT = 73
SDL_SCANCODE_HOME = 74
SDL_SCANCODE_PAGEUP = 75
SDL_SCANCODE_DELETE = 76
SDL_SCANCODE_END = 77
SDL_SCANCODE_PAGEDOWN = 78
SDL_SCANCODE_RIGHT = 79
SDL_SCANCODE_LEFT = 80
SDL_SCANCODE_DOWN = 81
SDL_SCANCODE_UP = 82
SDL_SCANCODE_NUMLOCKCLEAR = 83
SDL_SCANCODE_KP_DIVIDE = 84
SDL_SCANCODE_KP_MULTIPLY = 85
SDL_SCANCODE_KP_MINUS = 86
SDL_SCANCODE_KP_PLUS = 87
SDL_SCANCODE_KP_ENTER = 88
SDL_SCANCODE_KP_1 = 89
SDL_SCANCODE_KP_2 = 90
SDL_SCANCODE_KP_3 = 91
SDL_SCANCODE_KP_4 = 92
SDL_SCANCODE_KP_5 = 93
SDL_SCANCODE_KP_6 = 94
SDL_SCANCODE_KP_7 = 95
SDL_SCANCODE_KP_8 = 96
SDL_SCANCODE_KP_9 = 97
SDL_SCANCODE_KP_0 = 98
SDL_SCANCODE_KP_PERIOD = 99
SDL_SCANCODE_NONUSBACKSLASH = 100
SDL_SCANCODE_APPLICATION = 101
SDL_SCANCODE_POWER = 102
SDL_SCANCODE_KP_EQUALS = 103
SDL_SCANCODE_F13 = 104
SDL_SCANCODE_F14 = 105
SDL_SCANCODE_F15 = 106
SDL_SCANCODE_HELP = 117
SDL_SCANCODE_MENU = 118
SDL_SCANCODE_UNDO = 122
SDL_SCANCODE_INTERNATIONAL1 = 135
SDL_SCANCODE_INTERNATIONAL2 = 136
SDL_SCANCODE_INTERNATIONAL3 = 137
SDL_SCANCODE_INTERNATIONAL4 = 138
SDL_SCANCODE_INTERNATIONAL5 = 139
SDL_SCANCODE_INTERNATIONAL6 = 140
SDL_SCANCODE_INTERNATIONAL7 = 141
SDL_SCANCODE_INTERNATIONAL8 = 142
SDL_SCANCODE_INTERNATIONAL9 = 143
SDL_SCANCODE_SYSREQ = 154
SDL_SCANCODE_THOUSANDSSEPARATOR = 178
SDL_SCANCODE_DECIMALSEPARATOR = 179
SDL_SCANCODE_CURRENCYUNIT = 180
SDL_SCANCODE_CURRENCYSUBUNIT = 181
SDL_SCANCODE_LCTRL = 224
SDL_SCANCODE_LSHIFT = 225
SDL_SCANCODE_LALT = 226
SDL_SCANCODE_LGUI = 227
SDL_SCANCODE_RCTRL = 228
SDL_SCANCODE_RSHIFT = 229
SDL_SCANCODE_RALT = 230
SDL_SCANCODE_RGUI = 231
SDL_SCANCODE_MODE = 257

#
# SDL_keycode.h: SDL_Keycode
#
SDLK_SCANCODE_MASK = (1 << 30)

def SDL_SCANCODE_TO_KEYCODE(X: int)->int:
	return X | SDLK_SCANCODE_MASK

SDLK_UNKNOWN = 0
SDLK_RETURN = ord('\r')
SDLK_ESCAPE = 27
SDLK_BACKSPACE = ord('\b')
SDLK_TAB = ord('\t')
SDLK_SPACE = ord(' ')
SDLK_QUOTE = ord('\'')
SDLK_QUOTEDBL = ord('"')
SDLK_DELETE = 127
SDLK_CAPSLOCK = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_CAPSLOCK)
SDLK_F1 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F1)
SDLK_F2 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F2)
SDLK_F3 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F3)
SDLK_F4 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F4)
SDLK_F5 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F5)
SDLK_F6 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F6)
SDLK_F7 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F7)
SDLK_F8 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F8)
SDLK_F9 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F9)
SDLK_F10 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F10)
SDLK_F11 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F11)
SDLK_F12 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F12)
SDLK_PRINTSCREEN = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_PRINTSCREEN)
SDLK_SCROLLLOCK = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_SCROLLLOCK)
SDLK_PAUSE = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_PAUSE)
SDLK_INSERT = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_INSERT)
SDLK_HOME = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_HOME)
SDLK_PAGEUP = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_PAGEUP)
SDLK_END = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_END)
SDLK_PAGEDOWN = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_PAGEDOWN)
SDLK_RIGHT = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_RIGHT)
SDLK_LEFT = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_LEFT)
SDLK_DOWN = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_DOWN)
SDLK_UP = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_UP)
SDLK_NUMLOCKCLEAR = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_NUMLOCKCLEAR)
SDLK_KP_DIVIDE = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_DIVIDE)
SDLK_KP_MULTIPLY = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_MULTIPLY)
SDLK_KP_MINUS = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_MINUS)
SDLK_KP_PLUS = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_PLUS)
SDLK_KP_ENTER = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_ENTER)
SDLK_KP_1 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_1)
SDLK_KP_2 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_2)
SDLK_KP_3 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_3)
SDLK_KP_4 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_4)
SDLK_KP_5 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_5)
SDLK_KP_6 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_6)
SDLK_KP_7 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_7)
SDLK_KP_8 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_8)
SDLK_KP_9 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_9)
SDLK_KP_0 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_0)
SDLK_KP_PERIOD = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_PERIOD)
SDLK_APPLICATION = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_APPLICATION)
SDLK_POWER = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_POWER)
SDLK_KP_EQUALS = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_KP_EQUALS)
SDLK_F13 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F13)
SDLK_F14 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F14)
SDLK_F15 = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_F15)
SDLK_HELP = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_HELP)
SDLK_MENU = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_MENU)
SDLK_UNDO = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_UNDO)
SDLK_SYSREQ = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_SYSREQ)
SDLK_LCTRL = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_LCTRL)
SDLK_LSHIFT = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_LSHIFT)
SDLK_LALT = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_LALT)
SDLK_LGUI = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_LGUI)
SDLK_RCTRL = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_RCTRL)
SDLK_RSHIFT = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_RSHIFT)
SDLK_RALT = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_RALT)
SDLK_RGUI = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_RGUI)
SDLK_MODE = SDL_SCANCODE_TO_KEYCODE(SDL_SCANCODE_MODE)

#
# the event structures (SDL_Event is a union in C, here every member is there)
#
class SDL_Keysym(object):

	def __init__(self):

		self.scancode = 0 #SDL_Scancode
		self.sym = 0 #SDL_Keycode
		self.mod = 0 #Uint16

class SDL_KeyboardEvent(object):

	def __init__(self):

		self.repeat = 0 #Uint8
		self.keysym = SDL_Keysym() #SDL_Keysym

class SDL_MouseMotionEvent(object):

	def __init__(self):

		self.x, self.y = 0, 0 #Sint32
		self.xrel, self.yrel = 0, 0 #Sint32

class SDL_MouseButtonEvent(object):

	def __init__(self):

		self.button = 0 #Uint8
		self.x, self.y = 0, 0 #Sint32

class SDL_MouseWheelEvent(object):

	def __init__(self):

		self.x, self.y = 0, 0 #Sint32
		self.preciseX, self.preciseY = 0.0, 0.0 #float

class SDL_TextInputEvent(object):

	def __init__(self):

		self.text = "" #char [SDL_TEXTINPUTEVENT_TEXT_SIZE]

class SDL_WindowEvent(object):

	def __init__(self):

		self.event = 0 #Uint8, SDL_WindowEventID
		self.data1, self.data2 = 0, 0 #Sint32

class SDL_Event(object):

	def __init__(self):

		self.type = 0 #Uint32
		self.key = SDL_KeyboardEvent()
		self.motion = SDL_MouseMotionEvent()
		self.button = SDL_MouseButtonEvent()
		self.wheel = SDL_MouseWheelEvent()
		self.text = SDL_TextInputEvent()
		self.window = SDL_WindowEvent()

class SDL_DisplayMode(object):

	def __init__(self, w: int = 0, h: int = 0, refresh_rate: int = 0):

		self.format = 0 #Uint32
		self.w = w #int
		self.h = h #int
		self.refresh_rate = refresh_rate #int
		self.driverdata = None #void *

	def __repr__(self):

		return "SDL_DisplayMode({}x{}@{})".format(self.w, self.h, self.refresh_rate)

#
# state
#
_error = "" # SDL_GetError
_init_flags = 0 # SDL_WasInit
_display = None # pyglet display
_gl_attributes = {} # SDL_GL_SetAttribute
_gl_window = None # the window whose context is current
_events = [] # the event queue (SDL_PollEvent)
_modstate = KMOD_NONE # SDL_GetModState
_show_cursor = 1 # SDL_ShowCursor
_relative_mouse = False # SDL_SetRelativeMouseMode
_windows = [] # the open windows

def SDL_SetError(fmt: str)->int:

	global _error
	_error = fmt
	return -1

def SDL_GetError()->str:

	return _error

def SDL_SetHint(name: str, value: str)->bool:

	# pyglet has no hints; the window manager decides
	return False

#
# SDL_Init
#
def SDL_Init(flags: int)->int:

	global _init_flags, _display

	if flags & SDL_INIT_VIDEO:

		if _display is None:

			try:
				_display = pyglet.display.get_display()
			except Exception as err: # no X display, or pyglet can't talk to it
				return SDL_SetError(str(err))

		flags |= SDL_INIT_EVENTS

	_init_flags |= flags
	return 0

def SDL_InitSubSystem(flags: int)->int:

	return SDL_Init(flags)

def SDL_WasInit(flags: int)->int:

	if flags == 0:
		flags = SDL_INIT_EVERYTHING
	return _init_flags & flags

def SDL_QuitSubSystem(flags: int):

	global _init_flags

	if flags & SDL_INIT_VIDEO:
		flags |= SDL_INIT_EVENTS
	_init_flags &= ~flags

def SDL_Quit():

	global _init_flags

	for window in list(_windows):
		SDL_DestroyWindow(window)
	_init_flags = 0

def SDL_GetVersion()->tuple:

	# the version of pyglet that stands in for SDL
	return tuple(int(x) for x in pyglet.version.split(".")[:3])

def SDL_GetCurrentVideoDriver()->str:

	if _display is None:
		return None
	return "x11" # pyglet's xlib display

#
# displays
#
def _screens()->list:

	if _display is None:
		return []
	return _display.get_screens()

def SDL_GetNumVideoDisplays()->int:

	screens = _screens()
	if not screens:
		return SDL_SetError("Video subsystem has not been initialized")
	return len(screens)

def _display_modes(displayIndex: int)->list:

	screens = _screens()
	if displayIndex < 0 or displayIndex >= len(screens):
		return None

	screen = screens[displayIndex]
	modes = []
	for mode in screen.get_modes():
		modes.append(SDL_DisplayMode(mode.width, mode.height, int(round(mode.rate))))

	if not modes:
		# pyglet found no modes (e.g. xrandr without mode lines), the desktop is the one mode
		modes.append(SDL_DisplayMode(screen.width, screen.height, 0))

	return modes

def SDL_GetNumDisplayModes(displayIndex: int)->int:

	modes = _display_modes(displayIndex)
	if modes is None:
		return SDL_SetError("displayIndex must be in the range 0 - {}".format(len(_screens()) - 1))
	return len(modes)

def SDL_GetDisplayMode(displayIndex: int, modeIndex: int)->tuple: # (returns int, SDL_DisplayMode)

	modes = _display_modes(displayIndex)
	if modes is None:
		return SDL_SetError("displayIndex must be in the range 0 - {}".format(len(_screens()) - 1)), None
	if modeIndex < 0 or modeIndex >= len(modes):
		return SDL_SetError("index must be in the range of 0 - {}".format(len(modes) - 1)), None
	return 0, modes[modeIndex]

def SDL_GetCurrentDisplayMode(displayIndex: int)->tuple: # (returns int, SDL_DisplayMode)

	screens = _screens()
	if displayIndex < 0 or displayIndex >= len(screens):
		return SDL_SetError("displayIndex must be in the range 0 - {}".format(len(screens) - 1)), None

	screen = screens[displayIndex]
	mode = screen.get_mode()
	if mode is None:
		return 0, SDL_DisplayMode(screen.width, screen.height, 0)
	return 0, SDL_DisplayMode(mode.width, mode.height, int(round(mode.rate)))

def SDL_GetDesktopDisplayMode(displayIndex: int)->tuple: # (returns int, SDL_DisplayMode)

	return SDL_GetCurrentDisplayMode(displayIndex)

def SDL_GetClosestDisplayMode(displayIndex: int, mode: SDL_DisplayMode)->SDL_DisplayMode:

	modes = _display_modes(displayIndex)
	if not modes:
		SDL_SetError("Couldn't find display mode match")
		return None

	closest = None
	for m in modes:

		if m.w < mode.w or m.h < mode.h:
			continue
		if closest is None or (m.w, m.h) < (closest.w, closest.h) or \
			((m.w, m.h) == (closest.w, closest.h) and abs(m.refresh_rate - mode.refresh_rate) < abs(closest.refresh_rate - mode.refresh_rate)):
			closest = m

	if closest is None:
		SDL_SetError("Couldn't find display mode match")
	return closest

#
# windows
#
class SDL_Window(pyglet.window.Window):

	# pyglet sets up its own shaders and projection for its drawing; the port draws
	# with its own GL (gl1 can be a compatibility context), so none of that is done
	def _create_projection(self):

		self._viewport = (0, 0) + tuple(self.get_framebuffer_size())

	def _on_internal_resize(self, width, height):

		self._viewport = (0, 0) + tuple(self.get_framebuffer_size())
		self.dispatch_event('on_resize', width, height)

	def _on_internal_scale(self, scale, dpi):

		pass

	# the event handlers queue SDL events (pyglet's defaults would close the
	# window on escape and set the viewport on resize)
	def on_key_press(self, symbol, modifiers):

		_key_event(SDL_KEYDOWN, symbol, modifiers)
		return pyglet.event.EVENT_HANDLED

	def on_key_release(self, symbol, modifiers):

		_key_event(SDL_KEYUP, symbol, modifiers)
		return pyglet.event.EVENT_HANDLED

	def on_text(self, text):

		event = SDL_Event()
		event.type = SDL_TEXTINPUT
		event.text.text = text
		_events.append(event)
		return pyglet.event.EVENT_HANDLED

	def on_mouse_motion(self, x, y, dx, dy):

		event = SDL_Event()
		event.type = SDL_MOUSEMOTION
		event.motion.x, event.motion.y = int(x), int(self.height - y)
		event.motion.xrel, event.motion.yrel = int(dx), int(-dy) # pyglet's y goes up, SDL's down
		_events.append(event)
		return pyglet.event.EVENT_HANDLED

	def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):

		return self.on_mouse_motion(x, y, dx, dy)

	def on_mouse_press(self, x, y, button, modifiers):

		_button_event(SDL_MOUSEBUTTONDOWN, x, self.height - y, button)
		return pyglet.event.EVENT_HANDLED

	def on_mouse_release(self, x, y, button, modifiers):

		_button_event(SDL_MOUSEBUTTONUP, x, self.height - y, button)
		return pyglet.event.EVENT_HANDLED

	def on_mouse_scroll(self, x, y, scroll_x, scroll_y):

		event = SDL_Event()
		event.type = SDL_MOUSEWHEEL
		event.wheel.preciseX, event.wheel.preciseY = float(scroll_x), float(scroll_y)
		event.wheel.x, event.wheel.y = int(scroll_x), int(scroll_y)
		_events.append(event)
		return pyglet.event.EVENT_HANDLED

	def on_activate(self):

		_window_event(SDL_WINDOWEVENT_FOCUS_GAINED)
		return pyglet.event.EVENT_HANDLED

	def on_deactivate(self):

		_window_event(SDL_WINDOWEVENT_FOCUS_LOST)
		return pyglet.event.EVENT_HANDLED

	def on_move(self, x, y):

		_window_event(SDL_WINDOWEVENT_MOVED, x, y)
		return pyglet.event.EVENT_HANDLED

	def on_show(self):

		_window_event(SDL_WINDOWEVENT_SHOWN)
		return pyglet.event.EVENT_HANDLED

	def on_hide(self):

		_window_event(SDL_WINDOWEVENT_HIDDEN)
		return pyglet.event.EVENT_HANDLED

	def on_resize(self, width, height):

		_window_event(SDL_WINDOWEVENT_SIZE_CHANGED, width, height)
		return pyglet.event.EVENT_HANDLED

	def on_close(self):

		event = SDL_Event()
		event.type = SDL_QUIT
		_events.append(event)
		return pyglet.event.EVENT_HANDLED

	def on_draw(self):

		return pyglet.event.EVENT_HANDLED

def _gl_config():

	# SDL_GL_SetAttribute's values as a pyglet Config
	attr = _gl_attributes
	profile = attr.get(SDL_GL_CONTEXT_PROFILE_MASK, 0)
	major = attr.get(SDL_GL_CONTEXT_MAJOR_VERSION, 2)
	minor = attr.get(SDL_GL_CONTEXT_MINOR_VERSION, 1)
	flags = attr.get(SDL_GL_CONTEXT_FLAGS, 0)

	kwargs = dict(
		red_size = attr.get(SDL_GL_RED_SIZE, 3),
		green_size = attr.get(SDL_GL_GREEN_SIZE, 3),
		blue_size = attr.get(SDL_GL_BLUE_SIZE, 2),
		alpha_size = attr.get(SDL_GL_ALPHA_SIZE, 0),
		double_buffer = bool(attr.get(SDL_GL_DOUBLEBUFFER, 1)),
		depth_size = attr.get(SDL_GL_DEPTH_SIZE, 16),
		stencil_size = attr.get(SDL_GL_STENCIL_SIZE, 0),
		sample_buffers = attr.get(SDL_GL_MULTISAMPLEBUFFERS, 0),
		samples = attr.get(SDL_GL_MULTISAMPLESAMPLES, 0),
		forward_compatible = bool(flags & SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG),
		debug = bool(flags & SDL_GL_CONTEXT_DEBUG_FLAG),
	)

	if profile == SDL_GL_CONTEXT_PROFILE_CORE:

		kwargs["major_version"] = major
		kwargs["minor_version"] = minor
		kwargs["opengl_api"] = "gl" # pyglet asks for a core profile context

	elif profile == SDL_GL_CONTEXT_PROFILE_ES:

		kwargs["major_version"] = major
		kwargs["minor_version"] = minor
		kwargs["opengl_api"] = "gles"

	else:

		# like SDL without a profile: no version or profile is asked for, so the
		# driver gives its compatibility context (pyglet asks for core with "gl")
		if major >= 3:
			kwargs["major_version"] = major
			kwargs["minor_version"] = minor
		kwargs["opengl_api"] = "compatibility"

	return pyglet.gl.Config(**kwargs)

def SDL_CreateWindow(title: str, x: int, y: int, w: int, h: int, flags: int)->SDL_Window:

	global _gl_window

	if _display is None:

		SDL_SetError("Video subsystem has not been initialized")
		return None

	screen = _display.get_default_screen()
	if SDL_WINDOWPOS_ISUNDEFINED(x) or SDL_WINDOWPOS_ISUNDEFINED(y):

		index = x & 0xFFFF if SDL_WINDOWPOS_ISUNDEFINED(x) else 0
		screens = _screens()
		if index < len(screens):
			screen = screens[index]

	kwargs = dict(caption=title, screen=screen, config=_gl_config(), vsync=False, visible=True)

	if (flags & SDL_WINDOW_FULLSCREEN_DESKTOP) == SDL_WINDOW_FULLSCREEN_DESKTOP:

		kwargs["fullscreen"] = True # at the desktop size, the mode isn't changed

	elif flags & SDL_WINDOW_FULLSCREEN:

		kwargs["fullscreen"] = True
		kwargs["width"], kwargs["height"] = w, h

	else:

		kwargs["width"], kwargs["height"] = w, h

	try:
		window = SDL_Window(**kwargs)
	except Exception as err: # pyglet raises its own exception types for missing configs and contexts
		SDL_SetError(str(err) or type(err).__name__)
		return None

	window.sdl_flags = flags | SDL_WINDOW_SHOWN
	window.sdl_gamma_saved = None # the X gamma ramp to restore when the window goes
	window.sdl_mouse_exclusive = False

	if not window.fullscreen and not SDL_WINDOWPOS_ISUNDEFINED(x) and not SDL_WINDOWPOS_ISUNDEFINED(y):

		window.set_location(x, y)

	window.set_mouse_visible(bool(_show_cursor))
	_windows.append(window)
	_gl_window = window

	return window

def SDL_DestroyWindow(window: SDL_Window):

	global _gl_window

	if window is None or window not in _windows:
		return

	_restore_gamma(window)
	if window.sdl_mouse_exclusive:
		window.set_exclusive_mouse(False)

	window.close()
	_windows.remove(window)
	if _gl_window is window:
		_gl_window = None

	# drop the events of the closed window
	_events.clear()

def SDL_GetWindowFlags(window: SDL_Window)->int:

	if window is None:
		return 0

	flags = window.sdl_flags & ~SDL_WINDOW_FULLSCREEN_DESKTOP
	if window.fullscreen:
		flags |= window.sdl_flags & SDL_WINDOW_FULLSCREEN_DESKTOP or SDL_WINDOW_FULLSCREEN
	return flags

def SDL_GetWindowDisplayIndex(window: SDL_Window)->int:

	screens = _screens()
	for i, screen in enumerate(screens):

		if screen is window.screen:
			return i

	# pyglet may hand out new screen objects; match by position
	for i, screen in enumerate(screens):

		if (screen.x, screen.y) == (window.screen.x, window.screen.y):
			return i

	return 0

def SDL_GetWindowPosition(window: SDL_Window)->tuple: # (returns int x, int y)

	return tuple(window.get_location())

def SDL_SetWindowSize(window: SDL_Window, w: int, h: int):

	if not window.fullscreen:
		window.set_size(w, h)

def SDL_GetWindowDisplayMode(window: SDL_Window)->tuple: # (returns int, SDL_DisplayMode)

	ret, mode = SDL_GetCurrentDisplayMode(SDL_GetWindowDisplayIndex(window))
	if ret != 0:
		return ret, None

	if window.fullscreen:
		return 0, SDL_DisplayMode(window.width, window.height, mode.refresh_rate)

	return 0, SDL_DisplayMode(window.width, window.height, mode.refresh_rate)

def SDL_SetWindowDisplayMode(window: SDL_Window, mode: SDL_DisplayMode)->int:

	if not window.fullscreen:
		return 0

	try:
		window.set_fullscreen(True, width=mode.w, height=mode.h)
	except Exception as err:
		return SDL_SetError(str(err))
	return 0

def SDL_SetWindowFullscreen(window: SDL_Window, flags: int)->int:

	try:
		if (flags & SDL_WINDOW_FULLSCREEN_DESKTOP) == SDL_WINDOW_FULLSCREEN_DESKTOP:
			window.set_fullscreen(True)
		elif flags & SDL_WINDOW_FULLSCREEN:
			window.set_fullscreen(True, width=window.width, height=window.height)
		else:
			window.set_fullscreen(False)
	except Exception as err:
		return SDL_SetError(str(err))

	window.sdl_flags = (window.sdl_flags & ~SDL_WINDOW_FULLSCREEN_DESKTOP) | flags
	return 0

def SDL_SetWindowTitle(window: SDL_Window, title: str):

	window.set_caption(title)

def SDL_SetWindowIcon(window: SDL_Window, icon):

	# icon is a pyglet image
	window.set_icon(icon)

def SDL_SetWindowGrab(window: SDL_Window, grabbed: bool):

	# pyglet confines the pointer only in exclusive (relative) mode, which
	# SDL_SetRelativeMouseMode does
	pass

def SDL_ShowCursor(toggle: int)->int:

	global _show_cursor

	if toggle >= 0:

		_show_cursor = toggle
		for window in _windows:
			window.set_mouse_visible(bool(toggle) and not window.sdl_mouse_exclusive)

	return _show_cursor

def SDL_SetRelativeMouseMode(enabled: bool)->int:

	global _relative_mouse

	enabled = bool(enabled)
	_relative_mouse = enabled
	for window in _windows:

		if window.sdl_mouse_exclusive != enabled:

			window.sdl_mouse_exclusive = enabled
			window.set_exclusive_mouse(enabled)

	return 0

def SDL_GetRelativeMouseMode()->bool:

	return _relative_mouse

#
# GL
#
def SDL_GL_SetAttribute(attr: int, value: int)->int:

	_gl_attributes[attr] = int(value)
	return 0

def SDL_GL_ResetAttributes():

	_gl_attributes.clear()

def SDL_GL_GetAttribute(attr: int)->tuple: # (returns int, int value)

	if _gl_window is None:
		return SDL_SetError("No current context"), 0

	config = _gl_window.config
	if attr == SDL_GL_RED_SIZE:
		return 0, config.red_size or 0
	elif attr == SDL_GL_GREEN_SIZE:
		return 0, config.green_size or 0
	elif attr == SDL_GL_BLUE_SIZE:
		return 0, config.blue_size or 0
	elif attr == SDL_GL_ALPHA_SIZE:
		return 0, config.alpha_size or 0
	elif attr == SDL_GL_DOUBLEBUFFER:
		return 0, int(bool(config.double_buffer))
	elif attr == SDL_GL_DEPTH_SIZE:
		return 0, config.depth_size or 0
	elif attr == SDL_GL_STENCIL_SIZE:
		return 0, config.stencil_size or 0
	elif attr == SDL_GL_MULTISAMPLEBUFFERS:
		return 0, config.sample_buffers or 0
	elif attr == SDL_GL_MULTISAMPLESAMPLES:
		return 0, config.samples or 0
	elif attr == SDL_GL_CONTEXT_MAJOR_VERSION:
		return 0, config.major_version or 0
	elif attr == SDL_GL_CONTEXT_MINOR_VERSION:
		return 0, config.minor_version or 0

	return SDL_SetError("Unknown OpenGL attribute"), 0

def SDL_GL_CreateContext(window: SDL_Window):

	global _gl_window

	# pyglet made the context with the window
	if window is None or window.context is None:
		SDL_SetError("The specified window isn't an OpenGL window")
		return None

	window.switch_to()
	_gl_window = window
	return window.context

def SDL_GL_MakeCurrent(window: SDL_Window, context)->int:

	global _gl_window

	if window is None:
		_gl_window = None
		return 0

	window.switch_to()
	_gl_window = window
	return 0

def SDL_GL_DeleteContext(context):

	# the context goes with its window (SDL_DestroyWindow)
	pass

def SDL_GL_SwapWindow(window: SDL_Window):

	window.flip()

def SDL_GL_GetDrawableSize(window: SDL_Window)->tuple: # (returns int w, int h)

	return tuple(window.get_framebuffer_size())

def SDL_GL_SetSwapInterval(interval: int)->int:

	if _gl_window is None:
		return SDL_SetError("No OpenGL context has been made current")

	if interval < 0:
		return SDL_SetError("Negative swap interval unsupported in this GL")

	_gl_window.set_vsync(interval != 0)
	return 0

def SDL_GL_GetSwapInterval()->int:

	if _gl_window is None:
		return 0
	return 1 if _gl_window.vsync else 0

#
# gamma (X11 XF86VidMode, as SDL's X11 video driver)
#
def SDL_CalculateGammaRamp(gamma: float, ramp: list):

	# 0.0 gamma is all black
	if gamma == 0.0:

		for i in range(256):
			ramp[i] = 0
		return

	elif gamma == 1.0:

		# 1.0 gamma is identity
		for i in range(256):
			ramp[i] = (i << 8) | i
		return

	else:

		# calculate a real gamma ramp
		gamma = 1.0 / gamma
		for i in range(256):

			value = int(((i / 256.0) ** gamma) * 65535.0 + 0.5)
			if value > 65535:
				value = 65535
			ramp[i] = value

def _xf86vmode():

	from pyglet.libs.x11 import xf86vmode
	return xf86vmode

def _get_gamma_ramp(window: SDL_Window)->tuple:

	xf86vmode = _xf86vmode()
	dpy = window._x_display
	scr = window._x_screen_id
	size = ctypes.c_int()
	if not xf86vmode.XF86VidModeGetGammaRampSize(dpy, scr, ctypes.byref(size)) or size.value <= 0:
		return None

	r = (ctypes.c_ushort * size.value)()
	g = (ctypes.c_ushort * size.value)()
	b = (ctypes.c_ushort * size.value)()
	if not xf86vmode.XF86VidModeGetGammaRamp(dpy, scr, size.value, r, g, b):
		return None
	return (size.value, r, g, b)

def _set_gamma_ramp(window: SDL_Window, size: int, r, g, b)->bool:

	xf86vmode = _xf86vmode()
	return bool(xf86vmode.XF86VidModeSetGammaRamp(window._x_display, window._x_screen_id, size, r, g, b))

def SDL_SetWindowGammaRamp(window: SDL_Window, red: list, green: list, blue: list)->int:

	try:
		if window.sdl_gamma_saved is None:

			window.sdl_gamma_saved = _get_gamma_ramp(window)
			if window.sdl_gamma_saved is None:
				return SDL_SetError("Couldn't get the gamma ramp")

		size = window.sdl_gamma_saved[0]
		r = (ctypes.c_ushort * size)()
		g = (ctypes.c_ushort * size)()
		b = (ctypes.c_ushort * size)()
		for i in range(size):

			j = i * 256 // size # the server's ramp may not have 256 entries
			r[i], g[i], b[i] = red[j], green[j], blue[j]

		if not _set_gamma_ramp(window, size, r, g, b):
			return SDL_SetError("Setting the gamma ramp failed")

	except (OSError, AttributeError, ImportError) as err: # no XF86VidMode
		return SDL_SetError(str(err))

	return 0

def _restore_gamma(window: SDL_Window):

	if window.sdl_gamma_saved is not None:

		try:
			_set_gamma_ramp(window, *window.sdl_gamma_saved)
		except (OSError, AttributeError, ImportError):
			pass
		window.sdl_gamma_saved = None

#
# events
#
# pyglet key symbol -> (SDL_Keycode, SDL_Scancode)
_us_scancodes = {
	'a': SDL_SCANCODE_A, 'b': SDL_SCANCODE_B, 'c': SDL_SCANCODE_C, 'd': SDL_SCANCODE_D,
	'e': SDL_SCANCODE_E, 'f': SDL_SCANCODE_F, 'g': SDL_SCANCODE_G, 'h': SDL_SCANCODE_H,
	'i': SDL_SCANCODE_I, 'j': SDL_SCANCODE_J, 'k': SDL_SCANCODE_K, 'l': SDL_SCANCODE_L,
	'm': SDL_SCANCODE_M, 'n': SDL_SCANCODE_N, 'o': SDL_SCANCODE_O, 'p': SDL_SCANCODE_P,
	'q': SDL_SCANCODE_Q, 'r': SDL_SCANCODE_R, 's': SDL_SCANCODE_S, 't': SDL_SCANCODE_T,
	'u': SDL_SCANCODE_U, 'v': SDL_SCANCODE_V, 'w': SDL_SCANCODE_W, 'x': SDL_SCANCODE_X,
	'y': SDL_SCANCODE_Y, 'z': SDL_SCANCODE_Z,
	'1': SDL_SCANCODE_1, '2': SDL_SCANCODE_2, '3': SDL_SCANCODE_3, '4': SDL_SCANCODE_4,
	'5': SDL_SCANCODE_5, '6': SDL_SCANCODE_6, '7': SDL_SCANCODE_7, '8': SDL_SCANCODE_8,
	'9': SDL_SCANCODE_9, '0': SDL_SCANCODE_0,
	' ': SDL_SCANCODE_SPACE, '-': SDL_SCANCODE_MINUS, '=': SDL_SCANCODE_EQUALS,
	'[': SDL_SCANCODE_LEFTBRACKET, ']': SDL_SCANCODE_RIGHTBRACKET, '\\': SDL_SCANCODE_BACKSLASH,
	';': SDL_SCANCODE_SEMICOLON, '\'': SDL_SCANCODE_APOSTROPHE, '`': SDL_SCANCODE_GRAVE,
	',': SDL_SCANCODE_COMMA, '.': SDL_SCANCODE_PERIOD, '/': SDL_SCANCODE_SLASH,
}

_special_keys = {
	pyglet_key.RETURN: (SDLK_RETURN, SDL_SCANCODE_RETURN),
	pyglet_key.ESCAPE: (SDLK_ESCAPE, SDL_SCANCODE_ESCAPE),
	pyglet_key.BACKSPACE: (SDLK_BACKSPACE, SDL_SCANCODE_BACKSPACE),
	pyglet_key.TAB: (SDLK_TAB, SDL_SCANCODE_TAB),
	pyglet_key.DELETE: (SDLK_DELETE, SDL_SCANCODE_DELETE),
	pyglet_key.CAPSLOCK: (SDLK_CAPSLOCK, SDL_SCANCODE_CAPSLOCK),
	pyglet_key.F1: (SDLK_F1, SDL_SCANCODE_F1),
	pyglet_key.F2: (SDLK_F2, SDL_SCANCODE_F2),
	pyglet_key.F3: (SDLK_F3, SDL_SCANCODE_F3),
	pyglet_key.F4: (SDLK_F4, SDL_SCANCODE_F4),
	pyglet_key.F5: (SDLK_F5, SDL_SCANCODE_F5),
	pyglet_key.F6: (SDLK_F6, SDL_SCANCODE_F6),
	pyglet_key.F7: (SDLK_F7, SDL_SCANCODE_F7),
	pyglet_key.F8: (SDLK_F8, SDL_SCANCODE_F8),
	pyglet_key.F9: (SDLK_F9, SDL_SCANCODE_F9),
	pyglet_key.F10: (SDLK_F10, SDL_SCANCODE_F10),
	pyglet_key.F11: (SDLK_F11, SDL_SCANCODE_F11),
	pyglet_key.F12: (SDLK_F12, SDL_SCANCODE_F12),
	pyglet_key.F13: (SDLK_F13, SDL_SCANCODE_F13),
	pyglet_key.F14: (SDLK_F14, SDL_SCANCODE_F14),
	pyglet_key.F15: (SDLK_F15, SDL_SCANCODE_F15),
	pyglet_key.PRINT: (SDLK_PRINTSCREEN, SDL_SCANCODE_PRINTSCREEN),
	pyglet_key.SCROLLLOCK: (SDLK_SCROLLLOCK, SDL_SCANCODE_SCROLLLOCK),
	pyglet_key.PAUSE: (SDLK_PAUSE, SDL_SCANCODE_PAUSE),
	pyglet_key.BREAK: (SDLK_PAUSE, SDL_SCANCODE_PAUSE),
	pyglet_key.INSERT: (SDLK_INSERT, SDL_SCANCODE_INSERT),
	pyglet_key.HOME: (SDLK_HOME, SDL_SCANCODE_HOME),
	pyglet_key.PAGEUP: (SDLK_PAGEUP, SDL_SCANCODE_PAGEUP),
	pyglet_key.END: (SDLK_END, SDL_SCANCODE_END),
	pyglet_key.PAGEDOWN: (SDLK_PAGEDOWN, SDL_SCANCODE_PAGEDOWN),
	pyglet_key.RIGHT: (SDLK_RIGHT, SDL_SCANCODE_RIGHT),
	pyglet_key.LEFT: (SDLK_LEFT, SDL_SCANCODE_LEFT),
	pyglet_key.DOWN: (SDLK_DOWN, SDL_SCANCODE_DOWN),
	pyglet_key.UP: (SDLK_UP, SDL_SCANCODE_UP),
	pyglet_key.NUMLOCK: (SDLK_NUMLOCKCLEAR, SDL_SCANCODE_NUMLOCKCLEAR),
	pyglet_key.NUM_DIVIDE: (SDLK_KP_DIVIDE, SDL_SCANCODE_KP_DIVIDE),
	pyglet_key.NUM_MULTIPLY: (SDLK_KP_MULTIPLY, SDL_SCANCODE_KP_MULTIPLY),
	pyglet_key.NUM_SUBTRACT: (SDLK_KP_MINUS, SDL_SCANCODE_KP_MINUS),
	pyglet_key.NUM_ADD: (SDLK_KP_PLUS, SDL_SCANCODE_KP_PLUS),
	pyglet_key.NUM_ENTER: (SDLK_KP_ENTER, SDL_SCANCODE_KP_ENTER),
	pyglet_key.NUM_EQUAL: (SDLK_KP_EQUALS, SDL_SCANCODE_KP_EQUALS),
	# the keypad with numlock on
	pyglet_key.NUM_1: (SDLK_KP_1, SDL_SCANCODE_KP_1),
	pyglet_key.NUM_2: (SDLK_KP_2, SDL_SCANCODE_KP_2),
	pyglet_key.NUM_3: (SDLK_KP_3, SDL_SCANCODE_KP_3),
	pyglet_key.NUM_4: (SDLK_KP_4, SDL_SCANCODE_KP_4),
	pyglet_key.NUM_5: (SDLK_KP_5, SDL_SCANCODE_KP_5),
	pyglet_key.NUM_6: (SDLK_KP_6, SDL_SCANCODE_KP_6),
	pyglet_key.NUM_7: (SDLK_KP_7, SDL_SCANCODE_KP_7),
	pyglet_key.NUM_8: (SDLK_KP_8, SDL_SCANCODE_KP_8),
	pyglet_key.NUM_9: (SDLK_KP_9, SDL_SCANCODE_KP_9),
	pyglet_key.NUM_0: (SDLK_KP_0, SDL_SCANCODE_KP_0),
	pyglet_key.NUM_DECIMAL: (SDLK_KP_PERIOD, SDL_SCANCODE_KP_PERIOD),
	# and with numlock off (SDL keeps the keypad keycodes)
	pyglet_key.NUM_END: (SDLK_KP_1, SDL_SCANCODE_KP_1),
	pyglet_key.NUM_DOWN: (SDLK_KP_2, SDL_SCANCODE_KP_2),
	pyglet_key.NUM_PAGE_DOWN: (SDLK_KP_3, SDL_SCANCODE_KP_3),
	pyglet_key.NUM_LEFT: (SDLK_KP_4, SDL_SCANCODE_KP_4),
	pyglet_key.NUM_BEGIN: (SDLK_KP_5, SDL_SCANCODE_KP_5),
	pyglet_key.NUM_RIGHT: (SDLK_KP_6, SDL_SCANCODE_KP_6),
	pyglet_key.NUM_HOME: (SDLK_KP_7, SDL_SCANCODE_KP_7),
	pyglet_key.NUM_UP: (SDLK_KP_8, SDL_SCANCODE_KP_8),
	pyglet_key.NUM_PAGE_UP: (SDLK_KP_9, SDL_SCANCODE_KP_9),
	pyglet_key.NUM_INSERT: (SDLK_KP_0, SDL_SCANCODE_KP_0),
	pyglet_key.NUM_DELETE: (SDLK_KP_PERIOD, SDL_SCANCODE_KP_PERIOD),
	pyglet_key.MENU: (SDLK_APPLICATION, SDL_SCANCODE_APPLICATION),
	pyglet_key.HELP: (SDLK_HELP, SDL_SCANCODE_HELP),
	pyglet_key.UNDO: (SDLK_UNDO, SDL_SCANCODE_UNDO),
	pyglet_key.SYSREQ: (SDLK_SYSREQ, SDL_SCANCODE_SYSREQ),
	pyglet_key.LCTRL: (SDLK_LCTRL, SDL_SCANCODE_LCTRL),
	pyglet_key.RCTRL: (SDLK_RCTRL, SDL_SCANCODE_RCTRL),
	pyglet_key.LSHIFT: (SDLK_LSHIFT, SDL_SCANCODE_LSHIFT),
	pyglet_key.RSHIFT: (SDLK_RSHIFT, SDL_SCANCODE_RSHIFT),
	pyglet_key.LALT: (SDLK_LALT, SDL_SCANCODE_LALT),
	pyglet_key.RALT: (SDLK_RALT, SDL_SCANCODE_RALT),
	0xfe03: (SDLK_RALT, SDL_SCANCODE_RALT), # ISO_Level3_Shift (AltGr)
	pyglet_key.LWINDOWS: (SDLK_LGUI, SDL_SCANCODE_LGUI),
	pyglet_key.RWINDOWS: (SDLK_RGUI, SDL_SCANCODE_RGUI),
	pyglet_key.LMETA: (SDLK_LGUI, SDL_SCANCODE_LGUI),
	pyglet_key.RMETA: (SDLK_RGUI, SDL_SCANCODE_RGUI),
	pyglet_key.MODESWITCH: (SDLK_MODE, SDL_SCANCODE_MODE),
}

_pyglet_mods = ( # pyglet modifier -> SDL_Keymod
	(pyglet_key.MOD_SHIFT, KMOD_LSHIFT),
	(pyglet_key.MOD_CTRL, KMOD_LCTRL),
	(pyglet_key.MOD_ALT, KMOD_LALT),
	(pyglet_key.MOD_WINDOWS, KMOD_LGUI),
	(pyglet_key.MOD_CAPSLOCK, KMOD_CAPS),
	(pyglet_key.MOD_NUMLOCK, KMOD_NUM),
	(pyglet_key.MOD_SCROLLLOCK, KMOD_SCROLL),
)

_mod_keys = { # SDL_Keycode of a modifier key -> SDL_Keymod
	SDLK_LSHIFT: KMOD_LSHIFT, SDLK_RSHIFT: KMOD_RSHIFT,
	SDLK_LCTRL: KMOD_LCTRL, SDLK_RCTRL: KMOD_RCTRL,
	SDLK_LALT: KMOD_LALT, SDLK_RALT: KMOD_RALT,
	SDLK_LGUI: KMOD_LGUI, SDLK_RGUI: KMOD_RGUI,
	SDLK_MODE: KMOD_MODE,
}

def _translate_key(symbol: int)->tuple: # (returns SDL_Keycode, SDL_Scancode)

	if symbol in _special_keys:
		return _special_keys[symbol]

	if 32 <= symbol < 127:
		c = chr(symbol).lower()
		return ord(c), _us_scancodes.get(c, SDL_SCANCODE_UNKNOWN)

	if 0xa0 <= symbol <= 0xff:
		# Latin-1 keysyms are their unicode code points, as SDL's keycodes
		return symbol, SDL_SCANCODE_UNKNOWN

	return SDLK_UNKNOWN, SDL_SCANCODE_UNKNOWN

def _key_event(type_: int, symbol: int, modifiers: int):

	global _modstate

	sym, scancode = _translate_key(symbol)

	# pyglet's modifiers are the state before this key
	mod = KMOD_NONE
	for pmod, smod in _pyglet_mods:
		if modifiers & pmod:
			mod |= smod
	if sym in _mod_keys:
		if type_ == SDL_KEYDOWN:
			mod |= _mod_keys[sym]
		else:
			mod &= ~_mod_keys[sym]
	_modstate = mod

	event = SDL_Event()
	event.type = type_
	event.key.keysym.sym = sym
	event.key.keysym.scancode = scancode
	event.key.keysym.mod = mod
	_events.append(event)

_pyglet_buttons = {
	pyglet_mouse.LEFT: SDL_BUTTON_LEFT,
	pyglet_mouse.MIDDLE: SDL_BUTTON_MIDDLE,
	pyglet_mouse.RIGHT: SDL_BUTTON_RIGHT,
	pyglet_mouse.MOUSE4: SDL_BUTTON_X1,
	pyglet_mouse.MOUSE5: SDL_BUTTON_X2,
}

def _button_event(type_: int, x: int, y: int, button: int):

	event = SDL_Event()
	event.type = type_
	event.button.button = _pyglet_buttons.get(button, 0)
	event.button.x, event.button.y = int(x), int(y)
	_events.append(event)

def _window_event(id_: int, data1: int = 0, data2: int = 0):

	event = SDL_Event()
	event.type = SDL_WINDOWEVENT
	event.window.event = id_
	event.window.data1, event.window.data2 = int(data1), int(data2)
	_events.append(event)

def SDL_PumpEvents():

	for window in list(_windows):
		window.dispatch_events()

def SDL_PollEvent(event: SDL_Event)->int:

	if not _events:
		SDL_PumpEvents()

	if not _events:
		return 0

	e = _events.pop(0)
	if event is not None:
		event.__dict__.update(e.__dict__)
	return 1

def SDL_FlushEvents(minType: int, maxType: int):

	SDL_PumpEvents()
	_events[:] = [e for e in _events if not (minType <= e.type <= maxType)]

def SDL_StartTextInput():

	# pyglet always sends text events
	pass

def SDL_StopTextInput():

	pass

def SDL_GetModState()->int:

	return _modstate

#
# clipboard
#
def SDL_GetClipboardText()->str:

	if not _windows:
		SDL_SetError("Video subsystem must be initialized to get clipboard text")
		return ""

	try:
		return _windows[-1].get_clipboard_text() or ""
	except (NotImplementedError, AttributeError) as err:
		SDL_SetError(str(err))
		return ""

def SDL_SetClipboardText(text: str)->int:

	if not _windows:
		return SDL_SetError("Video subsystem must be initialized to set clipboard text")

	try:
		_windows[-1].set_clipboard_text(text)
	except (NotImplementedError, AttributeError) as err:
		return SDL_SetError(str(err))
	return 0
