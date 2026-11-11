# Render one fixed frame (early, static camera, frozen time) for regression diffing.
import os, sys, time
os.environ.setdefault("Q2PORT_NOMOUSE", "1")  # no mouse capture (tests)
sys.argv = ["main.py"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import OpenGL.GL as GL
import numpy as np
from PIL import Image
from backends.unix import system
from client.vid import glimp_sdl2
from client.refresh.gl1 import gl1_sdl, gl1_buffer # the gl1 frame swap (Yamagi's RI_EndFrame)
from client import cl_main
from client.refresh.gl1 import gl1_main
from client.refresh.gl1 import gl1_surf
frame=[0]; done=[False]; frozen=[None,None]
out=os.environ.get("SHOT","/tmp/refshot.png"); CAP=int(os.environ.get("CAPFRAME","12"))
Q2CONSOLE=os.environ.get("Q2CONSOLE")
if Q2CONSOLE:
    from client import cl_screen
orv=gl1_main.R_RenderView
def RV(fd):
    if done[0]:
        fd.vieworg[:] = frozen[0]; fd.viewangles[:] = frozen[1]
        fd.time = 0.0; fd.blend[:] = (0.0,0.0,0.0,0.0)
    return orv(fd)
gl1_main.R_RenderView=RV
oe=gl1_sdl.RI_EndFrame
def EF():
    if cl_main.cls.state.name=="ca_active" and not done[0]:
        frame[0]+=1
        if frame[0]==CAP:
            frozen[0]=np.array(gl1_main.r_newrefdef.vieworg,dtype=np.float32)
            frozen[1]=np.array(gl1_main.r_newrefdef.viewangles,dtype=np.float32)
            gl1_main.r_newrefdef.time=0.0; gl1_main.r_newrefdef.blend[:]=(0,0,0,0)
            if Q2CONSOLE:
                cl_screen.scr_conlines=0.75
            vp=GL.glGetIntegerv(GL.GL_VIEWPORT); w,h=int(vp[2]),int(vp[3])
            GL.glReadBuffer(GL.GL_BACK)
            gl1_buffer.R_ApplyGLBuffer() # draw the batched 2D first (RI_EndFrame does it before the swap)
            Image.frombytes("RGB",(w,h),GL.glReadPixels(0,0,w,h,GL.GL_RGB,GL.GL_UNSIGNED_BYTE)).transpose(Image.FLIP_TOP_BOTTOM).save(out)
            print("refshot %s -> %s" % (os.path.basename(out), out)); done[0]=True
            if os.environ.get("Q2LMDUMP"):
                base=gl1_main.gl_state.lightmap_textures
                for li in range(1,8):
                    GL.glBindTexture(GL.GL_TEXTURE_2D, base+li)
                    buf=GL.glGetTexImage(GL.GL_TEXTURE_2D,0,GL.GL_RGBA,GL.GL_UNSIGNED_BYTE)
                    a=np.frombuffer(buf,dtype=np.uint8).reshape(-1,4)[:,:3].astype(np.int32).mean()
                    print ("Q2LMDUMP lm%d mean=%.1f" % (li, a))
    return oe()
gl1_sdl.RI_EndFrame=EF
system.main()
