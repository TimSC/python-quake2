"""
Group 1 port step, run after the move (yq_move.py group1.py) and yq_alias.py:
 - common/header/shared.py: Yamagi's shared.h changes (limits, new defines, cvar_t.default_string),
   and the vec_t typedefs moved here from shared.c;
 - common/shared/shared.py: synced to Yamagi's shared.c order (yq_sync.py --head), with
   RotatePointAroundVector, R_ConcatRotations and VectorNormalize2 ported from Yamagi.
Each edit checks that its anchor text is there exactly once.
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)


def edit(path, pairs):
	s = open(path).read()
	for old, new in pairs:
		assert s.count(old) == 1, (path, old[:60], s.count(old))
		s = s.replace(old, new)
	open(path, "w").write(s)


# ---- header: shared.h
edit("common/shared/shared.py", [
	("vec_t = np.float32 #typedef float vec_t;\nvec3_t = np.ndarray # typedef vec_t vec3_t[3];\nvec5_t = np.ndarray # typedef vec_t [5];\n", ""),
])
edit("common/header/shared.py", [
	('\tMULTICAST_PVS_R = 5\n\n"""\ntypedef\tint\tfixed4_t;',
	 '\tMULTICAST_PVS_R = 5\n\nvec_t = np.float32 #typedef float vec_t;\nvec3_t = np.ndarray #typedef vec_t vec3_t[3];\nvec5_t = np.ndarray #typedef vec_t vec5_t[5];\n\n"""\ntypedef\tint\tfixed4_t;'),
	("#ifndef M_PI\n#define M_PI\t\t3.14159265358979323846\t// matches value in gcc v2 math.h\n#endif\n", ""),
	("MAX_STRING_CHARS = 1024\t# max length", "MAX_STRING_CHARS = 2048\t# max length"),
	("MAX_TOKEN_CHARS = 128\t\t# max length", "MAX_TOKEN_CHARS = 1024\t\t# max length"),
	("MAX_OSPATH\t\t\t= 128\t\t# max length of a filesystem pathname", """
# DG: For some stupid reason, SV_WriteServerFile() and SV_ReadeServerFile() used
# MAX_OSPATH as buffer length for CVAR_LATCH CVARS and saved the whole buffer
# into $game/save/current/server.ssv, so changing MAX_OSPATH breaks savegames...
# Unfortunately, for some other fucking reason MAX_OSPATH was 128 for non-Windows
# which is just horrible.. so I introduced LATCH_CVAR_SAVELENGTH with the stupid
# values so I could bump MAX_OSPATH.
# TODO: whenever you break savegame compatibility next, make
#       LATCH_CVAR_SAVELENGTH system-independent (or remove it and hardcode a
#       sensible value in the two functions)

# not Win32 (Linux, BSD, Mac, ..)
MAX_OSPATH = 4096            # max length of a filesystem pathname
LATCH_CVAR_SAVELENGTH = 128"""),
	("MAX_INFO_STRING\t\t= 512", "MAX_INFO_KEYVAL = ((MAX_INFO_KEY - 1) + (MAX_INFO_VALUE - 1) + 3) # 3 for 2 backslashes and null char\nMAX_INFO_STRING\t\t= 512"),
	("RF_SHELL_BLUE\t\t= 4096\n", "RF_SHELL_BLUE\t\t= 4096\nRF_NOSHADOW = 8192        # don't draw a shadow\n"),
	("CS_STATUSBAR\t\t= 5\t\t# display program string\n",
	 "CS_STATUSBAR\t\t= 5\t\t# display program string\nCS_STATUSBAR_END = 29\ndef CS_STATUSBAR_SPACE(i): return ((CS_STATUSBAR_END - (i)) * MAX_QPATH) #define CS_STATUSBAR_SPACE(i)\n"),
	("DF_NO_SPHERES\t\t= 0x00100000\n", "DF_NO_SPHERES\t\t= 0x00100000\n\nROGUE_VERSION_STRING = \"08/21/1998 Beta 2 for Ensemble\"\n"),
	("\t\tself.value = None #float\n",
	 "\t\tself.value = None #float\n\t\t#struct cvar_s *next;\n\n\t\t# Added by YQ2. Must be at the end to preserve ABI.\n\t\tself.default_string = None #char *\n"),
])
s = open("common/header/shared.py").read()
open("common/header/shared.py", "w").write(s.replace("shared_c.vec3_t", "vec3_t"))
# M_PI goes with the math defines, before vec3_origin's extern (as the #ifndef in shared.h)
edit("common/header/shared.py", [
	('vec5_t = np.ndarray #typedef vec_t vec5_t[5];\n', 'vec5_t = np.ndarray #typedef vec_t vec5_t[5];\n\nM_PI = 3.14159265358979323846 # matches value in gcc v2 math.h\n'),
])

# ---- shared.c
subprocess.check_call([sys.executable, "scripts/yq_sync.py", "common/shared/shared.py", "--head"])
import ast


def unit(src, name):
	t = ast.parse(src); L = src.splitlines(keepends=True)
	for st in t.body:
		if isinstance(st, ast.FunctionDef) and st.name == name:
			return "".join(L[st.lineno - 1:st.end_lineno])
	raise KeyError(name)


def cblock(src, fname):
	t = ast.parse(src); L = src.splitlines(keepends=True)
	for st in t.body:
		if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str) and ("\n" + fname + "(") in st.value.value:
			return "".join(L[st.lineno - 1:st.end_lineno])
	raise KeyError(fname)


NEW = {}
NEW["R_ConcatRotations"] = '''def R_ConcatRotations(in1, in2, out): #const float [3][3], const float [3][3], float [3][3]

	out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] + \\
				in1[0][2] * in2[2][0]
	out[0][1] = in1[0][0] * in2[0][1] + in1[0][1] * in2[1][1] + \\
				in1[0][2] * in2[2][1]
	out[0][2] = in1[0][0] * in2[0][2] + in1[0][1] * in2[1][2] + \\
				in1[0][2] * in2[2][2]
	out[1][0] = in1[1][0] * in2[0][0] + in1[1][1] * in2[1][0] + \\
				in1[1][2] * in2[2][0]
	out[1][1] = in1[1][0] * in2[0][1] + in1[1][1] * in2[1][1] + \\
				in1[1][2] * in2[2][1]
	out[1][2] = in1[1][0] * in2[0][2] + in1[1][1] * in2[1][2] + \\
				in1[1][2] * in2[2][2]
	out[2][0] = in1[2][0] * in2[0][0] + in1[2][1] * in2[1][0] + \\
				in1[2][2] * in2[2][0]
	out[2][1] = in1[2][0] * in2[0][1] + in1[2][1] * in2[1][1] + \\
				in1[2][2] * in2[2][1]
	out[2][2] = in1[2][0] * in2[0][2] + in1[2][1] * in2[1][2] + \\
				in1[2][2] * in2[2][2]
'''
NEW["RotatePointAroundVector"] = '''def RotatePointAroundVector(dst, dir, point, degrees): #vec3_t, const vec3_t, const vec3_t, float

	"""
	float m[3][3];
	float im[3][3];
	float zrot[3][3];
	float tmpmat[3][3];
	float rot[3][3];
	int i;
	vec3_t vr, vup, vf;
	"""
	m = np.zeros((3, 3), dtype=np.float32)
	zrot = np.zeros((3, 3), dtype=np.float32)
	tmpmat = np.zeros((3, 3), dtype=np.float32)
	rot = np.zeros((3, 3), dtype=np.float32)
	vr = np.zeros((3,), dtype=np.float32)
	vup = np.zeros((3,), dtype=np.float32)
	vf = np.zeros((3,), dtype=np.float32)

	vf[0] = dir[0]
	vf[1] = dir[1]
	vf[2] = dir[2]

	PerpendicularVector(vr, dir)
	CrossProduct(vr, vf, vup)

	m[0][0] = vr[0]
	m[1][0] = vr[1]
	m[2][0] = vr[2]

	m[0][1] = vup[0]
	m[1][1] = vup[1]
	m[2][1] = vup[2]

	m[0][2] = vf[0]
	m[1][2] = vf[1]
	m[2][2] = vf[2]

	im = m.copy() #memcpy(im, m, sizeof(im));

	im[0][1] = m[1][0]
	im[0][2] = m[2][0]
	im[1][0] = m[0][1]
	im[1][2] = m[2][1]
	im[2][0] = m[0][2]
	im[2][1] = m[1][2]

	#memset(zrot, 0, sizeof(zrot));
	zrot[2][2] = 1.0

	zrot[0][0] = math.cos(DEG2RAD(degrees))
	zrot[0][1] = math.sin(DEG2RAD(degrees))
	zrot[1][0] = -math.sin(DEG2RAD(degrees))
	zrot[1][1] = math.cos(DEG2RAD(degrees))

	R_ConcatRotations(m, zrot, tmpmat)
	R_ConcatRotations(tmpmat, im, rot)

	for i in range(3):

		dst[i] = rot[i][0] * point[0] + rot[i][1] * point[1] + rot[i][2] * \\
				 point[2]
'''
NEW["VectorNormalize2"] = '''def VectorNormalize2(v, out): #const vec3_t, vec3_t (returns vec_t)

	shared.VectorCopy(v, out)

	return VectorNormalize(out)
'''
p = "common/shared/shared.py"
s = open(p).read()
s = s.replace(unit(s, "RotatePointAroundVector"), NEW["RotatePointAroundVector"])
s = s.replace(unit(s, "VectorNormalize2"), NEW["VectorNormalize2"])
s = s.replace(cblock(s, "R_ConcatRotations"), NEW["R_ConcatRotations"])
inc = '#include "../header/shared.h"\n"""\n'
assert s.count(inc) == 1
assert s.count("vec3_origin = np.zeros((3,), dtype=np.float32)\n") == 1
s = s.replace("vec3_origin = np.zeros((3,), dtype=np.float32)\n", "")
s = s.replace(inc, inc + '''
def DEG2RAD(a): return (a * math.pi) / 180.0 #define DEG2RAD(a) (a * M_PI) / 180.0F

vec3_origin = np.zeros((3,), dtype=np.float32) #vec3_t, {0, 0, 0}

"""
/* ============================================================================ */
"""
''')
# id's text blocks with no Yamagi counterpart
for start in ['"""\n\n#define DEG2RAD( a )', '"""\n\n\tint\t\ti;\n\tvec3_t\tcorners[2];']:
	a = s.index(start); b = s.index('"""', a + 4) + 4
	s = s[:a] + s[b:].lstrip("\n")
open(p, "w").write(s)
print("group 1 port edits applied")
