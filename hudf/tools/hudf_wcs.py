"""
hudf_wcs.py
Works out the sky coordinates of the ESA/Hubble press image of the Hubble Ultra Deep Field (heic0406a, 6200 x 6200 px).
The press image carries no coordinates, so we detect galaxies and stars in it, find the rotation, scale and shift that
lay them on top of the UVUDF catalog positions (Rafelski et al. 2015), then fit a full linear (TAN) solution plus a
small polynomial correction by least squares on the matched pairs.

Usage: python3 hudf_wcs.py SOURCES_DIR   (writes cache/wcs.json and cache/wcs_check.jpg)
"""
import json, math, sys, warnings
from pathlib import Path
import numpy as np, cv2
from scipy.spatial import cKDTree
from scipy.ndimage import label, find_objects
warnings.simplefilter("ignore")
from astropy.table import Table

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1])
(HERE / "cache").mkdir(exist_ok=True)

# ---- catalog: tangent-plane coordinates (arcsec) about the field center
cat = Table.read(SRC / "uvudf_cat.fits")
RA, DEC = np.array(cat["RA"], float), np.array(cat["DEC"], float)
MAG = np.array(cat["MAG_F775W"], float); MAG[~np.isfinite(MAG) | (MAG <= 0) | (MAG > 40)] = 99
RA0, DEC0 = float(np.median(RA)), float(np.median(DEC))
def tan(ra, dec, ra0=RA0, dec0=DEC0):
    a, d, a0, d0 = np.radians(ra), np.radians(dec), math.radians(ra0), math.radians(dec0)
    c = np.sin(d0) * np.sin(d) + np.cos(d0) * np.cos(d) * np.cos(a - a0)
    xi = np.cos(d) * np.sin(a - a0) / c
    eta = (np.cos(d0) * np.sin(d) - np.sin(d0) * np.cos(d) * np.cos(a - a0)) / c
    return np.degrees(xi) * 3600, np.degrees(eta) * 3600        # xi grows to the east
XI, ETA = tan(RA, DEC)

# ---- detections in the image
img = cv2.imread(str(SRC / "heic0406a_large.jpg"))
H, W = img.shape[:2]
L = img.astype(np.float32).mean(2)
bg = cv2.medianBlur(cv2.resize(L, (W // 8, H // 8), interpolation=cv2.INTER_AREA).astype(np.uint8), 15).astype(np.float32)
bg = cv2.resize(bg, (W, H))
D = cv2.GaussianBlur(L - bg, (0, 0), 1.2)
mask = D > 18
lab, n = label(mask)
objs = find_objects(lab)
det = []
for i, sl in enumerate(objs):
    if sl is None: continue
    sub = (lab[sl] == i + 1); w = D[sl] * sub
    area = sub.sum()
    if area < 6: continue
    yy, xx = np.mgrid[sl[0], sl[1]]
    f = w.sum(); det.append((float((xx * w).sum() / f), float((yy * w).sum() / f), float(f), int(area)))
det = np.array(det)
det = det[np.argsort(-det[:, 2])]
print(f"image {W}x{H}, {len(det)} detections, catalog {len(RA)} objects")

# ---- coarse search: rotation, scale and parity by FFT cross-correlation of point maps
def raster(x, y, wts, N, s):
    m = np.zeros((N, N), np.float32)
    ix, iy = np.round(x / s).astype(int) + N // 2, np.round(y / s).astype(int) + N // 2
    ok = (ix >= 0) & (ix < N) & (iy >= 0) & (iy < N)
    np.add.at(m, (iy[ok], ix[ok]), wts[ok])
    return cv2.GaussianBlur(m, (0, 0), 1.5)
NB = 500
dsel = det[:NB]
B = 16                                                   # image pixels per raster cell
N = 512
imgmap = raster(dsel[:, 0] - W / 2, dsel[:, 1] - H / 2, np.ones(len(dsel), np.float32), N, B)
FI = np.fft.rfft2(imgmap)
csel = np.argsort(MAG)[:int(NB * 1.3)]
best = (0,)
for parity in (1, -1):
    for scale in np.arange(0.026, 0.066, 0.002):        # arcsec per image pixel
        for rot in np.arange(0, 360, 1.0):
            c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            # sky (xi east, eta north) -> image (x right, y down), before the shift
            u = (parity * XI[csel] * c - ETA[csel] * s_) / scale
            v = (-(parity * XI[csel] * s_ + ETA[csel] * c)) / scale
            cm = raster(u, v, np.ones(len(csel), np.float32), N, B)
            cc = np.fft.irfft2(FI * np.conj(np.fft.rfft2(cm)), s=(N, N))
            k = np.argmax(cc); v0 = cc.flat[k]
            if v0 > best[0]:
                dy, dx = np.unravel_index(k, cc.shape); dy = dy - N if dy > N // 2 else dy; dx = dx - N if dx > N // 2 else dx
                best = (v0, parity, scale, rot, dx * B, dy * B)
    print("parity", parity, "best so far", [round(float(b), 4) for b in best])
_, parity, scale, rot, sx, sy = best
print("coarse:", dict(parity=parity, scale=scale, rot=rot, shift=(sx, sy)))

# ---- refine: iterate matching and least squares (linear, then cubic)
def model_terms(u, v, order):
    t = [np.ones_like(u)]
    for k in range(1, order + 1):
        for j in range(k + 1): t.append(u ** (k - j) * v ** j)
    return np.stack(t, 1)
c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
def first(xi, eta):
    return W / 2 + sx + (parity * xi * c - eta * s_) / scale, H / 2 + sy - (parity * xi * s_ + eta * c) / scale
px, py = first(XI, ETA)
tree = cKDTree(det[:, :2])
sel = MAG < 29
coef = None
for it, (order, tol, ndet) in enumerate([(1, 40, 800), (1, 15, 2000), (1, 8, 4000), (2, 5, 6000), (3, 4, 8000), (3, 3, 8000)]):
    tree = cKDTree(det[:ndet, :2])
    d, j = tree.query(np.stack([px, py], 1), distance_upper_bound=tol)
    ok = np.isfinite(d) & sel
    # one catalog object per detection: keep the nearest
    order_ = np.argsort(d[ok]); used = set(); keep = []
    idx = np.where(ok)[0][order_]
    for k in idx:
        if j[k] in used: continue
        used.add(j[k]); keep.append(k)
    keep = np.array(keep)
    T = model_terms(XI[keep] / 100, ETA[keep] / 100, order)
    ax, *_ = np.linalg.lstsq(T, det[j[keep], 0], rcond=None)
    ay, *_ = np.linalg.lstsq(T, det[j[keep], 1], rcond=None)
    T_all = model_terms(XI / 100, ETA / 100, order)
    px, py = T_all @ ax, T_all @ ay
    r = np.hypot(px[keep] - det[j[keep], 0], py[keep] - det[j[keep], 1])
    print(f"iteration {it}: order {order}, {len(keep)} matches, median residual {np.median(r):.2f} px, rms {np.sqrt(np.mean(r**2)):.2f} px")
    coef = (order, ax, ay)

# inverse: image pixel -> (xi, eta), fitted on a grid
order, ax, ay = coef
gx, gy = np.meshgrid(np.linspace(XI.min() - 20, XI.max() + 20, 80), np.linspace(ETA.min() - 20, ETA.max() + 20, 80))
T = model_terms(gx.ravel() / 100, gy.ravel() / 100, order)
qx, qy = T @ ax, T @ ay
Ti = model_terms((qx - W / 2) / 1000, (qy - H / 2) / 1000, 3)
bx, *_ = np.linalg.lstsq(Ti, gx.ravel(), rcond=None)
by, *_ = np.linalg.lstsq(Ti, gy.ravel(), rcond=None)
chk = np.hypot(Ti @ bx - gx.ravel(), Ti @ by - gy.ravel())
print("inverse fit error (arcsec): max", chk.max(), "median", np.median(chk))
# local pixel scale and north angle at the center
J = np.array([[ax[1], ax[2]], [ay[1], ay[2]]]) / 100      # pixels per arcsec
pscale = 1 / math.sqrt(abs(np.linalg.det(J)))
north = math.degrees(math.atan2(-J[0, 1], -J[1, 1]))      # direction of increasing eta, measured from image up, clockwise
print(f"pixel scale {pscale:.4f} arcsec, north is {north:.1f} deg clockwise from up, parity {parity}")
json.dump(dict(image="heic0406a", width=W, height=H, ra0=RA0, dec0=DEC0, fwd_order=order, fwd_scale=100, fx=ax.tolist(), fy=ay.tolist(),
               inv_order=3, inv_scale=1000, ix=bx.tolist(), iy=by.tolist(), pixscale=pscale, north_deg=north, parity=parity,
               matches=int(len(keep)), rms_px=float(np.sqrt(np.mean(r ** 2)))), open(HERE / "cache" / "wcs.json", "w"), indent=1)
out = img.copy()
for x, y in zip(px[MAG < 27], py[MAG < 27]):
    if 0 < x < W and 0 < y < H: cv2.circle(out, (int(x), int(y)), 14, (0, 255, 255), 2)
cv2.imwrite(str(HERE / "cache" / "wcs_check.jpg"), out[2400:3600, 2400:3600])
