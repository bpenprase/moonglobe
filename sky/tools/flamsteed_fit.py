"""
flamsteed_fit.py
Fits each plate of Flamsteed's Atlas Coelestis (1729) to the real sky, so the engraved figures can be laid
onto the celestial sphere.

For each plate:
  1. find the engraved star symbols (dark, compact blobs) on the photographed plate;
  2. move today's star positions (J2000) back to Flamsteed's epoch, 1690, by precession;
  3. search for the plate's center, scale and rotation in Flamsteed's sinusoidal projection
     (north up, east to the left), counting how many bright stars land on engraved symbols;
  4. refine with every matched star (to magnitude 6), using a smooth polynomial warp that absorbs the curve
     of the photographed page;
  5. write a check image (catalog stars drawn over the plate) and the fitted model.

Usage: python3 flamsteed_fit.py PLATES_DIR [plate numbers...]
"""
import json, math, sys
from pathlib import Path
import numpy as np, cv2
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
STARS = json.load(open(HERE.parent / "data" / "stars.json"))
CAT = np.array([[s[0], s[1], s[2]] for s in STARS if s[2] <= 6.3])
EPOCH = 1690.0

def precess(ra, dec, epoch):
    """J2000 -> epoch (IAU 1976 precession), degrees in and out."""
    t = (epoch - 2000.0) / 100.0
    zeta = math.radians((2306.2181 * t + 0.30188 * t * t + 0.017998 * t ** 3) / 3600)
    z = math.radians((2306.2181 * t + 1.09468 * t * t + 0.018203 * t ** 3) / 3600)
    th = math.radians((2004.3109 * t - 0.42665 * t * t - 0.041833 * t ** 3) / 3600)
    ra, dec = np.radians(ra), np.radians(dec)
    A = np.cos(dec) * np.sin(ra + zeta)
    B = math.cos(th) * np.cos(dec) * np.cos(ra + zeta) - math.sin(th) * np.sin(dec)
    C = math.sin(th) * np.cos(dec) * np.cos(ra + zeta) + math.cos(th) * np.sin(dec)
    return (np.degrees(np.arctan2(A, B) + z)) % 360, np.degrees(np.arcsin(np.clip(C, -1, 1)))

RA90, DEC90 = precess(CAT[:, 0], CAT[:, 1], EPOCH)
MAG = CAT[:, 2]

def sinus(ra, dec, ra0, dec0):
    """Flamsteed's sinusoidal projection, in degrees: x grows to the west (right), y grows to the south (down)."""
    dra = ((ra - ra0 + 540) % 360) - 180
    return -dra * np.cos(np.radians(dec)), dec0 - dec

def polar(ra, dec, ra0=0, dec0=90):
    """The polar plate: hour lines radiate from the pole (0h to the left, 6h up), parallels are circles."""
    r = 90 - dec
    return -r * np.cos(np.radians(ra)), -r * np.sin(np.radians(ra))

PROJ = {"sinus": sinus, "polar": polar}

def detect_stars(gray):
    """Centers of engraved star symbols: compact dark blobs that survive removing the thin engraved lines."""
    g = gray.astype(np.float32)
    bg = cv2.GaussianBlur(g, (0, 0), 30)
    ink = np.clip(1 - g / np.maximum(bg, 1), 0, 1)
    bw = (ink > 0.22).astype(np.uint8)
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    closed = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, k3)
    # bright stars are engraved as a white star inside a dark ring: fill small enclosed white areas
    # (but not the much larger cells of the coordinate grid)
    inv = (1 - closed).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv, 4)
    small = np.zeros(n, bool); small[1:] = (st[1:, cv2.CC_STAT_AREA] < 900) & (st[1:, cv2.CC_STAT_WIDTH] < 45) & (st[1:, cv2.CC_STAT_HEIGHT] < 45)
    filled = np.maximum(closed, small[lab].astype(np.uint8))
    k7 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    blobs = cv2.morphologyEx(filled, cv2.MORPH_OPEN, k7)                    # drop lines thinner than about 6 px
    n, lab, stats, cent = cv2.connectedComponentsWithStats(blobs, 8)
    keep = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if 60 <= a <= 3000 and 0.6 <= w / max(h, 1) <= 1.6 and a / (w * h) > 0.5:
            keep.append((cent[i][0], cent[i][1], a))
    return np.array(keep) if keep else np.zeros((0, 3))

def poly_terms(X, Y, order):
    cols = [np.ones_like(X)]
    for o in range(1, order + 1):
        for i in range(o + 1):
            cols.append(X ** (o - i) * Y ** i)
    return np.stack(cols, axis=1)

class Model:
    def __init__(self, ra0, dec0, order, cx, cy, proj="sinus"):
        self.ra0, self.dec0, self.order, self.cx, self.cy, self.proj = ra0, dec0, order, cx, cy, proj
    def xy(self, ra, dec):
        return PROJ[self.proj](ra, dec, self.ra0, self.dec0)
    def fit(self, ra, dec, px, py):
        X, Y = self.xy(ra, dec)
        T = poly_terms(X / 30, Y / 30, self.order)
        self.ax, *_ = np.linalg.lstsq(T, px, rcond=None)
        self.ay, *_ = np.linalg.lstsq(T, py, rcond=None)
        return self
    def __call__(self, ra, dec):
        X, Y = self.xy(ra, dec)
        T = poly_terms(X / 30, Y / 30, self.order)
        return T @ self.ax, T @ self.ay
    def to_json(self):
        return dict(proj=self.proj, ra0=self.ra0, dec0=self.dec0, order=self.order, ax=self.ax.tolist(), ay=self.ay.tolist(), epoch=EPOCH)

def score_xy(tree, W, H, X, Y, ox, oy, s, rot, mir, tol, keep=None):
    c, n = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    x = mir * X
    px, py = ox + s * (c * x - n * Y), oy + s * (n * x + c * Y)
    inside = (px > 0) & (px < W) & (py > 0) & (py < H)
    if keep is not None: inside &= keep
    if inside.sum() < 8: return 0.0
    d, _ = tree.query(np.stack([px[inside], py[inside]], 1), distance_upper_bound=tol)
    return np.isfinite(d).sum() / math.sqrt(inside.sum())

def distinct(cands, k, sep):
    out = []
    for c in cands:
        if all(abs(c[1] - o[1]) + abs(c[2] - o[2]) > sep or abs(c[3] / o[3] - 1) > 0.04 for o in out):
            out.append(c)
        if len(out) == k: break
    return out

def coarse_search(blobs, W, H, ra_c, dec_c, scales, span=16, step=0.5):
    """Sinusoidal plates. Stage 1: position and scale on a coarse grid with bright stars.
    Stage 2: finer position, scale and a small rotation around the best distinct candidates.
    Returns candidates as (score, ra0, dec0, scale, rotation, mirror), best first."""
    tree = cKDTree(blobs[:, :2])
    b = MAG <= 4.8
    cands = []
    for ddec in np.arange(-span * 0.75, span * 0.75 + 1e-6, step):
        dec0 = dec_c + ddec
        for dra in np.arange(-span, span + 1e-6, step):
            ra0 = (ra_c + dra / max(0.3, math.cos(math.radians(dec_c)))) % 360
            X, Y = sinus(RA90[b], DEC90[b], ra0, dec0)
            keep = np.abs(X) < 60
            for sc in scales:
                cands.append((score_xy(tree, W, H, X, Y, W / 2, H / 2, sc, 0, 1, sc * 0.3, keep), ra0, dec0, sc, 0.0, 1, W / 2))
    cands.sort(reverse=True)
    f5 = MAG <= 5.3
    out = []
    for sc0, ra0, dec0, s0, _, _, _ in distinct(cands, 6, 1.5):
        best = (0, ra0, dec0, s0, 0.0, 1, W / 2)
        cd = math.cos(math.radians(dec0))
        # the central meridian of the projection need not sit at the middle of the photo:
        # moving it by delta changes the shear of the grid while the pattern stays put on the row dec0
        for delta in np.arange(-10, 10.01, 2.0):
            for dra in (-0.5, 0, 0.5):
                for ddec in (-0.5, 0, 0.5):
                    ra1 = (ra0 + dra / max(0.3, cd)) % 360
                    X, Y = sinus(RA90[f5], DEC90[f5], (ra1 + delta) % 360, dec0 + ddec)
                    keep = np.abs(X) < 70
                    for f in np.arange(0.94, 1.0601, 0.02):
                        ox = W / 2 - s0 * f * delta * cd
                        for r in (-3, -1.5, 0, 1.5, 3):
                            v = score_xy(tree, W, H, X, Y, ox, H / 2, s0 * f, r, 1, s0 * f * 0.18, keep)
                            if v > best[0]: best = (v, (ra1 + delta) % 360, dec0 + ddec, s0 * f, r, 1, ox)
        out.append(best)
    return sorted(out, reverse=True)

def polar_search(blobs, W, H, pole, scales):
    """Polar plate: the pole pixel is known roughly. Search rotation, scale and handedness."""
    tree = cKDTree(blobs[:, :2])
    b = (MAG <= 5.0) & (DEC90 > 20)
    X, Y = polar(RA90[b], DEC90[b])
    cands = []
    for dx in (-60, -30, 0, 30, 60):
        for dy in (-60, -30, 0, 30, 60):
            for sc in scales:
                for rot in np.arange(0, 360, 2.0):
                    for mir in (1, -1):
                        cands.append((score_xy(tree, W, H, X, Y, pole[0] + dx, pole[1] + dy, sc, rot, mir, sc * 0.3), pole[0] + dx, pole[1] + dy, sc, rot, mir))
    cands.sort(reverse=True)
    return cands[:6]

def refine(blobs, W, H, ra0, dec0, s, rot=0.0, proj="sinus", origin=None, mir=1, aspect=1.0):
    tree = cKDTree(blobs[:, :2])
    m = Model(ra0, dec0, 1, W / 2, H / 2, proj)
    c, n = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    ox, oy = origin if origin else (W / 2, H / 2)
    m.ax = np.array([ox, s * aspect * 30 * c * mir, -s * aspect * 30 * n]); m.ay = np.array([oy, s * 30 * n * mir, s * 30 * c])
    for order, tol, maglim in [(1, s * 0.35, 5.0), (1, s * 0.25, 5.5), (2, s * 0.2, 6.0), (2, s * 0.15, 6.3), (3, s * 0.12, 6.3), (3, s * 0.1, 6.3)]:
        sel = MAG <= maglim
        px, py = m(RA90[sel], DEC90[sel])
        inside = (px > 0) & (px < W) & (py > 0) & (py < H)
        idx = np.where(sel)[0][inside]
        d, j = tree.query(np.stack([px[inside], py[inside]], 1), distance_upper_bound=tol)
        ok = np.isfinite(d)
        # one catalog star per blob: keep the closest
        pairs = {}
        for k in np.where(ok)[0]:
            if j[k] not in pairs or d[k] < pairs[j[k]][1]:
                pairs[j[k]] = (idx[k], d[k])
        if len(pairs) < 12:
            order = 1
        bi = np.array(list(pairs.keys())); ci = np.array([pairs[b][0] for b in bi])
        nm = Model(ra0, dec0, order, W / 2, H / 2, proj).fit(RA90[ci], DEC90[ci], blobs[bi, 0], blobs[bi, 1])
        # drop outliers and refit
        qx, qy = nm(RA90[ci], DEC90[ci]); r = np.hypot(qx - blobs[bi, 0], qy - blobs[bi, 1])
        good = r < max(3 * np.median(r), 4)
        m = Model(ra0, dec0, order, W / 2, H / 2, proj).fit(RA90[ci[good]], DEC90[ci[good]], blobs[bi[good], 0], blobs[bi[good], 1])
        qx, qy = m(RA90[ci[good]], DEC90[ci[good]])
        rms = float(np.sqrt(np.mean((qx - blobs[bi[good], 0]) ** 2 + (qy - blobs[bi[good], 1]) ** 2)))
    best = (int(good.sum()), rms, m)
    anchors = bright_anchors(blobs, m, W, H, s)
    # polish: keep re-matching with the cubic model while the number of matched stars grows
    for it in range(6):
        nm, n2, r2 = icp_step(tree, m, W, H, s * 0.14, 6.5, proj, ra0, dec0, anchors=anchors)
        if nm is None or n2 <= best[0]: break
        m = nm; best = (n2, r2, nm)
    # then let a smooth residual field take up what a polynomial cannot, such as the curl of the page at the gutter
    m = Warp(best[2], np.zeros((0, 2)), np.zeros((0, 2)), s)
    for it in range(8):
        nm, n2, r2 = warp_step(tree, m, W, H, s * 0.16, 6.5, proj, ra0, dec0, s, anchors)
        if nm is None or n2 <= best[0]: break
        m = nm; best = (n2, r2, nm)
    return best[2], best[0], best[1]

class Warp:
    """A polynomial model plus a smooth field of pixel offsets, interpolated from the residuals of matched stars."""
    def __init__(self, poly, nodes, offs, s):
        self.poly, self.nodes, self.offs, self.sig = poly, nodes, offs, 3.5 * s
    def field(self, px, py):
        if len(self.nodes) == 0: return 0 * px, 0 * py
        P = np.stack([px, py], 1)
        d2 = ((P[:, None, :] - self.nodes[None, :, :]) ** 2).sum(-1)
        w = np.exp(-d2 / (2 * self.sig ** 2))
        den = w.sum(1) + 0.6   # where few stars are near, the offset fades to zero
        return (w @ self.offs[:, 0]) / den, (w @ self.offs[:, 1]) / den
    def __call__(self, ra, dec):
        px, py = self.poly(ra, dec)
        fx, fy = self.field(px, py)
        return px + fx, py + fy
    def to_json(self):
        d = self.poly.to_json()
        d.update(sigma=self.sig, nodes=np.round(self.nodes, 1).tolist(), offsets=np.round(self.offs, 2).tolist())
        return d

def warp_step(tree, m, W, H, tol, maglim, proj, ra0, dec0, s, anchors=()):
    sel = MAG <= maglim
    px, py = m(RA90[sel], DEC90[sel])
    inside = (px > 0) & (px < W) & (py > 0) & (py < H)
    idx = np.where(sel)[0][inside]
    d, j = tree.query(np.stack([px[inside], py[inside]], 1), distance_upper_bound=tol)
    pairs = {}
    for k in np.where(np.isfinite(d))[0]:
        if j[k] not in pairs or d[k] < pairs[j[k]][1]:
            pairs[j[k]] = (idx[k], d[k])
    for ci_, bi_ in anchors:
        if bi_ not in pairs and ci_ not in [v[0] for v in pairs.values()]:
            pairs[bi_] = (ci_, 0.0)
    if len(pairs) < 20: return None, 0, 0
    bi = np.array(list(pairs.keys())); ci = np.array([pairs[b][0] for b in bi]); B = tree.data
    poly = Model(ra0, dec0, 3, W / 2, H / 2, proj).fit(RA90[ci], DEC90[ci], B[bi, 0], B[bi, 1])
    qx, qy = poly(RA90[ci], DEC90[ci])
    res = np.stack([B[bi, 0] - qx, B[bi, 1] - qy], 1)
    good = np.hypot(*res.T) < max(3 * np.median(np.hypot(*res.T)), 6)
    nm = Warp(poly, np.stack([qx, qy], 1)[good], res[good], s)
    # leave-in residuals are smoothed by the field, so report the rms after the warp
    fx, fy = nm.field(qx[good], qy[good])
    rms = float(np.sqrt(np.mean((qx[good] + fx - B[bi[good], 0]) ** 2 + (qy[good] + fy - B[bi[good], 1]) ** 2)))
    return nm, int(good.sum()), rms

def icp_step(tree, m, W, H, tol, maglim, proj, ra0, dec0, order=3, anchors=()):
    sel = MAG <= maglim
    px, py = m(RA90[sel], DEC90[sel])
    inside = (px > 0) & (px < W) & (py > 0) & (py < H)
    idx = np.where(sel)[0][inside]
    d, j = tree.query(np.stack([px[inside], py[inside]], 1), distance_upper_bound=tol)
    pairs = {}
    for k in np.where(np.isfinite(d))[0]:
        if j[k] not in pairs or d[k] < pairs[j[k]][1]:
            pairs[j[k]] = (idx[k], d[k])
    for ci_, bi_ in anchors:
        if bi_ not in pairs and ci_ not in [v[0] for v in pairs.values()]:
            pairs[bi_] = (ci_, 0.0)
    if len(pairs) < 20: return None, 0, 0
    bi = np.array(list(pairs.keys())); ci = np.array([pairs[b][0] for b in bi])
    B = tree.data
    nm = Model(ra0, dec0, order, W / 2, H / 2, proj).fit(RA90[ci], DEC90[ci], B[bi, 0], B[bi, 1])
    qx, qy = nm(RA90[ci], DEC90[ci]); r = np.hypot(qx - B[bi, 0], qy - B[bi, 1])
    good = r < max(3 * np.median(r), 4)
    nm = Model(ra0, dec0, order, W / 2, H / 2, proj).fit(RA90[ci[good]], DEC90[ci[good]], B[bi[good], 0], B[bi[good], 1])
    qx, qy = nm(RA90[ci[good]], DEC90[ci[good]])
    return nm, int(good.sum()), float(np.sqrt(np.mean((qx - B[bi[good], 0]) ** 2 + (qy - B[bi[good], 1]) ** 2)))

def bright_anchors(blobs, m, W, H, s, maglim=3.8):
    """Bright stars are drawn as large symbols. Pair each with the nearest large symbol within a wide radius,
    when that pairing is unambiguous, so that regions the first fit got wrong still pull the model."""
    big = np.where(blobs[:, 2] >= np.percentile(blobs[:, 2], 75))[0]
    if len(big) < 5: return []
    bt = cKDTree(blobs[big, :2])
    sel = np.where(MAG <= maglim)[0]
    px, py = m(RA90[sel], DEC90[sel])
    out, used = [], set()
    for k, x, y in zip(sel, px, py):
        if not (0 < x < W and 0 < y < H): continue
        d, j = bt.query([x, y], k=2)
        if d[0] < s * 1.6 and d[1] > 2 * d[0] and big[j[0]] not in used:
            out.append((k, big[j[0]])); used.add(big[j[0]])
    return out

def check_image(img, m, blobs, path, maglim=5.5):
    out = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    for x, y, a in blobs:
        cv2.circle(out, (int(x), int(y)), 4, (255, 160, 0), -1)
    sel = MAG <= maglim
    px, py = m(RA90[sel], DEC90[sel])
    H, W = img.shape
    for x, y, mg in zip(px, py, MAG[sel]):
        if 0 < x < W and 0 < y < H:
            cv2.circle(out, (int(x), int(y)), int(6 + (6 - mg) * 3), (0, 0, 255), 3)
    cv2.imwrite(str(path), cv2.resize(out, (W // 2, H // 2), interpolation=cv2.INTER_AREA))

if __name__ == "__main__":
    src = Path(sys.argv[1])
    cfg = json.load(open(HERE / "flamsteed_plates.json"))["plates"]
    want = set(a for a in sys.argv[2:] if not a.startswith("--"))
    results = {}
    for P in cfg:
        if want and P["n"] not in want: continue
        f = src / f"Atlas_Coelestis_by_John_Flamsteed_(1729)_{P['n']}.jpg"
        img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        H, W = img.shape
        blobs = detect_stars(img)
        tries = []
        if P.get("proj") == "polar":
            for sc, ox, oy, sx, rot, mir in polar_search(blobs, W, H, P["pole_px"], P.get("scales", [40, 43, 46, 49, 52])):
                m, n, rms = refine(blobs, W, H, 0.0, 90.0, sx, rot, "polar", (ox, oy), mir)
                tries.append((n, -rms, sc, 0.0, 90.0, sx, rot, mir, m))
        elif "start" in P:
            ra0, dec0, sx, ox = P["start"][:4]
            m, n, rms = refine(blobs, W, H, ra0, dec0, sx, 0.0, "sinus", (ox, H / 2), 1, P.get("aspect", 1.0))
            tries.append((n, -rms, 0, ra0, dec0, sx, 0.0, 1, m))
        else:
            ra_c, dec_c = precess(np.array([P["ra"]]), np.array([P["dec"]]), EPOCH)
            for sc, ra0, dec0, sx, rot, mir, ox in coarse_search(blobs, W, H, float(ra_c[0]), float(dec_c[0]), P.get("scales", [42, 45, 48, 51, 54])):
                m, n, rms = refine(blobs, W, H, ra0, dec0, sx, rot, "sinus", (ox, H / 2))
                tries.append((n, -rms, sc, ra0, dec0, sx, rot, mir, m))
        tries.sort(key=lambda t: (t[0], t[1]), reverse=True)
        n, rms, score, ra0, dec0, s, rot, mir, m = tries[0]; rms = -rms
        alts = ", ".join(str(t[0]) for t in tries)
        print(f"{P['n']} {P['title']}: {len(blobs)} symbols, search score {score:.1f} at RA {ra0:.1f} Dec {dec0:.1f} scale {s:.1f} rotation {rot:+.1f};"
              f" {n} stars matched (candidates {alts}), rms {rms:.1f} px ({rms / s * 60:.1f} arcmin)", flush=True)
        prev = json.load(open(HERE / "cache" / "fits.json")).get(P["n"]) if (HERE / "cache" / "fits.json").exists() else None
        if prev and prev["matched"] > n and "--fresh" not in sys.argv:
            print(f"   keeping the earlier fit with {prev['matched']} stars"); continue
        check_image(img, m, blobs, HERE / "cache" / f"check_{P['n']}.jpg")
        results[P["n"]] = dict(model=m.to_json(), matched=n, rms_px=rms, scale=s, W=W, H=H)
    out = HERE / "cache" / "fits.json"
    old = json.load(open(out)) if out.exists() else {}
    old.update(results); json.dump(old, open(out, "w"), indent=1)

def load_model(d, W=None, H=None):
    """Rebuild the fitted plate model (polynomial plus residual warp) from fits.json."""
    poly = Model(d["ra0"], d["dec0"], d["order"], 0, 0, d.get("proj", "sinus"))
    poly.ax, poly.ay = np.array(d["ax"]), np.array(d["ay"])
    w = Warp(poly, np.array(d.get("nodes", [])).reshape(-1, 2), np.array(d.get("offsets", [])).reshape(-1, 2), 1)
    w.sig = d.get("sigma", 150)
    return w

def model_xy(w, X, Y):
    """Pixel position of projection coordinates (X, Y) in degrees, through the polynomial and the residual warp."""
    T = poly_terms(np.asarray(X, float) / 30, np.asarray(Y, float) / 30, w.poly.order)
    px, py = T @ w.poly.ax, T @ w.poly.ay
    fx, fy = w.field(px, py)
    return px + fx, py + fy
