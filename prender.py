
"""Pure-Python figure renderer: fontTools glyph outlines + numpy scanline rasterizer + zlib PNG.
Used because every matplotlib/Pillow C extension is blocked by the host Application Control policy."""
import numpy as np, zlib, struct
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

FONTDIR = r"C:\Users\saisa\.claude-science\conda\envs\python\Lib\site-packages\matplotlib\mpl-data\fonts\ttf"
_FONTS = {}
def font(style="regular"):
    fn = {"regular":"DejaVuSans.ttf","bold":"DejaVuSans-Bold.ttf","italic":"DejaVuSans-Oblique.ttf"}[style]
    if style not in _FONTS:
        f = TTFont(FONTDIR+"\\"+fn); _FONTS[style] = (f, f.getGlyphSet(), f["head"].unitsPerEm,
                                                      f.getBestCmap(), f["hmtx"])
    return _FONTS[style]

def _flatten(pen_value, n=8):
    """RecordingPen output -> list of closed contours (lists of (x,y))."""
    contours, cur, start = [], [], (0,0)
    for op, args in pen_value:
        if op == "moveTo":
            if len(cur)>1: contours.append(cur)
            start = args[0]; cur = [start]
        elif op == "lineTo":
            cur.append(args[0])
        elif op == "qCurveTo":
            pts = list(args); on_end = pts[-1]
            if on_end is None: on_end = pts[0]; pts = pts[:-1]   # all-off-curve contour
            offs = pts[:-1] if pts[-1] is on_end else pts
            offs = pts[:-1]
            p0 = cur[-1]
            for i, c in enumerate(offs):
                p2 = on_end if i == len(offs)-1 else ((c[0]+offs[i+1][0])/2., (c[1]+offs[i+1][1])/2.)
                for t in np.linspace(0,1,n+1)[1:]:
                    x=(1-t)**2*p0[0]+2*(1-t)*t*c[0]+t*t*p2[0]; y=(1-t)**2*p0[1]+2*(1-t)*t*c[1]+t*t*p2[1]
                    cur.append((x,y))
                p0 = p2
        elif op == "curveTo":
            p0=cur[-1]; c1,c2,p3 = args
            for t in np.linspace(0,1,n+1)[1:]:
                x=(1-t)**3*p0[0]+3*(1-t)**2*t*c1[0]+3*(1-t)*t*t*c2[0]+t**3*p3[0]
                y=(1-t)**3*p0[1]+3*(1-t)**2*t*c1[1]+3*(1-t)*t*t*c2[1]+t**3*p3[1]
                cur.append((x,y))
        elif op == "closePath":
            if len(cur)>1: contours.append(cur)
            cur=[]
    if len(cur)>1: contours.append(cur)
    return contours

_GC = {}
def glyph_contours(ch, style):
    key=(ch,style)
    if key in _GC: return _GC[key]
    f, gs, upem, cmap, hmtx = font(style)
    name = cmap.get(ord(ch))
    if name is None: _GC[key]=([],0.0); return _GC[key]
    pen = RecordingPen(); gs[name].draw(pen)
    cont = [[(x/upem, y/upem) for x,y in c] for c in _flatten(pen.value)]
    adv = hmtx[name][0]/upem
    _GC[key]=(cont, adv); return _GC[key]

def text_width(s, size, style="regular"):
    return sum(glyph_contours(c, style)[1] for c in s)*size

class Canvas:
    def __init__(self, w_in, h_in, dpi=300, bg=(1,1,1)):
        self.dpi=dpi; self.W=int(round(w_in*dpi)); self.H=int(round(h_in*dpi))
        self.img=np.ones((self.H,self.W,3), np.float32)*np.array(bg, np.float32)
    # --- core rasterizer: nonzero-winding scanline, SS vertical subsamples, analytic x coverage
    def fill(self, contours, color, alpha=1.0, SS=4):
        edges=[]
        for c in contours:
            p=np.asarray(c,float)
            if len(p)<3: continue
            q=np.vstack([p,p[:1]])
            edges.append(np.column_stack([q[:-1,0],q[:-1,1],q[1:,0],q[1:,1]]))
        if not edges: return
        E=np.vstack(edges); E=E[E[:,1]!=E[:,3]]
        if len(E)==0: return
        y0=max(int(np.floor(min(E[:,1].min(),E[:,3].min()))),0)
        y1=min(int(np.ceil (max(E[:,1].max(),E[:,3].max())))+1,self.H)
        if y1<=y0: return
        ex0,ey0,ex1,ey1=E[:,0],E[:,1],E[:,2],E[:,3]
        ylo=np.minimum(ey0,ey1); yhi=np.maximum(ey0,ey1)
        dirn=np.where(ey1>ey0,1,-1); slope=(ex1-ex0)/(ey1-ey0)
        col=np.array(color,np.float32)
        for row in range(y0,y1):
            cov=np.zeros(self.W,np.float64); hit=False
            for s in range(SS):
                y=row+(s+0.5)/SS
                m=(ylo<=y)&(yhi>y)
                if not m.any(): continue
                xs=ex0[m]+(y-ey0[m])*slope[m]; dd=dirn[m]
                o=np.argsort(xs,kind="stable"); xs=xs[o]; dd=dd[o]
                wind=np.cumsum(dd)
                for i in range(len(xs)-1):
                    if wind[i]!=0 and xs[i+1]>xs[i]:
                        hit=True; self._span(cov,xs[i],xs[i+1],1.0/SS)
            if hit:
                np.clip(cov,0,1,out=cov)
                a=(cov*alpha).astype(np.float32)[:,None]
                self.img[row]=self.img[row]*(1-a)+col*a
    def _span(self,cov,xa,xb,w):
        xa=max(xa,0.0); xb=min(xb,float(self.W))
        if xb<=xa: return
        ia,ib=int(np.floor(xa)),int(np.floor(xb))
        if ia==ib: cov[ia]+=(xb-xa)*w; return
        cov[ia]+=(ia+1-xa)*w
        if ib>ia+1: cov[ia+1:ib]+=w
        if ib<self.W: cov[ib]+=(xb-ib)*w
    # --- primitives (device px, y down)
    def rect(self,x,y,w,h,color,alpha=1.0):
        if w<=0 or h<=0: return
        self.fill([[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]],color,alpha)
    def line(self,x0,y0,x1,y1,color,lw=1.0,alpha=1.0):
        dx,dy=x1-x0,y1-y0; L=(dx*dx+dy*dy)**.5
        if L==0: return
        nx,ny=-dy/L*lw/2,dx/L*lw/2
        self.fill([[(x0+nx,y0+ny),(x1+nx,y1+ny),(x1-nx,y1-ny),(x0-nx,y0-ny)]],color,alpha)
    def text(self,x,y,s,size,color=(0,0,0),style="regular",ha="left",va="baseline",rot=0.0,alpha=1.0):
        w=text_width(s,size,style)
        if ha=="center": x-=w/2
        elif ha=="right": x-=w
        if va=="middle": y+=size*0.36
        elif va=="top": y+=size*0.72
        ca,sa=np.cos(np.radians(rot)),np.sin(np.radians(rot))
        pen_x=0.0; out=[]
        for ch in s:
            cont,adv=glyph_contours(ch,style)
            for c in cont:
                p=np.asarray(c,float); gx=(p[:,0]+pen_x)*size; gy=-p[:,1]*size
                out.append(list(zip(x+gx*ca-gy*sa, y+gx*sa+gy*ca)))
            pen_x+=adv
        if out: self.fill(out,color,alpha)
        return w
    def save_png(self,path):
        a=np.clip(self.img,0,1); a=(a*255+0.5).astype(np.uint8)
        rows=b"".join(b"\x00"+a[r].tobytes() for r in range(self.H))
        def ch(t,d):
            c=t+d; return struct.pack(">I",len(d))+c+struct.pack(">I",zlib.crc32(c)&0xffffffff)
        ppm=int(round(self.dpi/0.0254))
        png=(b"\x89PNG\r\n\x1a\n"+ch(b"IHDR",struct.pack(">IIBBBBB",self.W,self.H,8,2,0,0,0))
             +ch(b"pHYs",struct.pack(">IIB",ppm,ppm,1))+ch(b"IDAT",zlib.compress(rows,9))+ch(b"IEND",b""))
        open(path,"wb").write(png); return self.W,self.H
