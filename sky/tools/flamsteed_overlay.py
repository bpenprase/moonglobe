"""
flamsteed_overlay.py
Turns the fitted Flamsteed plates into overlays for the celestial sphere.

For each plate (with a fit in cache/fits.json from flamsteed_fit.py):
  1. measure the engraving as "ink" (darkness relative to the local paper colour);
  2. find the map frame of the plate, so margins, scales and labels outside it are left out;
  3. erase the coordinate grid: ink that runs along the direction a parallel, hour line or ecliptic line
     takes at that spot, over a long straight stretch, is removed and the gap is painted over;
  4. keep only the plate's own constellations, using the IAU boundaries (moved back to 1690 and
     widened a little, with a soft edge), so neighbouring plates do not draw the same figure twice;
  5. write an image (red = ink, green = mask) and a mesh that ties points of the image to J2000 sky positions.

Output: ../data/flamsteed/plate_NNN.jpg and ../data/flamsteed/plates.json
Usage: python3 flamsteed_overlay.py PLATES_DIR [plate numbers...]
"""
import json, math, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image
from scipy.interpolate import griddata

sys.argv_saved = sys.argv; sys.argv = sys.argv[:1]
from flamsteed_fit import (HERE, EPOCH, precess, detect_stars, load_model, model_xy, sinus, polar)
sys.argv = sys.argv_saved

OUT = HERE.parent / "data" / "flamsteed"
SKY = json.load(open(HERE.parent / "data" / "sky.json"))
BOUNDS = {c["id"]: c["bounds"] for c in SKY["constellations"]}
SCALE = 0.5          # work at half the resolution of the photographs
EPS = math.radians(23.482)   # obliquity of the ecliptic in 1690


def precess_back(ra, dec, epoch=EPOCH):
    """epoch -> J2000: the inverse rotation of precess()."""
    t = (epoch - 2000.0) / 100.0
    zeta = math.radians((2306.2181 * t + 0.30188 * t * t + 0.017998 * t ** 3) / 3600)
    z = math.radians((2306.2181 * t + 1.09468 * t * t + 0.018203 * t ** 3) / 3600)
    th = math.radians((2004.3109 * t - 0.42665 * t * t - 0.041833 * t ** 3) / 3600)
    ra, dec = np.radians(ra) - z, np.radians(dec)
    A = np.cos(dec) * np.sin(ra)
    B = math.cos(th) * np.cos(dec) * np.cos(ra) + math.sin(th) * np.sin(dec)
    C = -math.sin(th) * np.cos(dec) * np.cos(ra) + math.cos(th) * np.sin(dec)
    return (np.degrees(np.arctan2(A, B)) - math.degrees(zeta)) % 360, np.degrees(np.arcsin(np.clip(C, -1, 1)))


def ecl2eq(lam, bet):
    l, b = np.radians(lam), np.radians(bet)
    x = np.cos(b) * np.cos(l)
    y = np.cos(b) * np.sin(l) * math.cos(EPS) - np.sin(b) * math.sin(EPS)
    z = np.cos(b) * np.sin(l) * math.sin(EPS) + np.sin(b) * math.cos(EPS)
    return np.degrees(np.arctan2(y, x)) % 360, np.degrees(np.arcsin(np.clip(z, -1, 1)))


def inverse_proj(d, X, Y):
    if d.get("proj") == "polar":
        r = np.hypot(X, Y)
        return np.degrees(np.arctan2(-Y, -X)) % 360, 90 - r
    dec = d["dec0"] - Y
    return (d["ra0"] - X / np.maximum(np.cos(np.radians(dec)), 1e-3)) % 360, dec


def ink_map(gray):
    g = gray.astype(np.float32)
    bg = cv2.GaussianBlur(g, (0, 0), 15)
    # the paper colour: a bright percentile in a moving window, so dense shading does not pull it down
    bg = np.maximum(bg, cv2.dilate(cv2.GaussianBlur(g, (0, 0), 2), np.ones((21, 21))) * 0.97)
    return np.clip(1 - g / np.maximum(bg, 1), 0, 1)


def grid_lines(d, w, shape, sc, s):
    """Candidate grid lines as dense pixel polylines: parallels every 1 degree, hour lines every 5 degrees,
    ecliptic parallels and meridians every 5 degrees (all for the equinox of 1690)."""
    H, W = shape
    px_per_deg = s * sc
    polar_plate = d.get("proj") == "polar"
    lines = []
    proj = (lambda r, dd: polar(r, dd)) if polar_plate else (lambda r, dd: sinus(r, dd, d["ra0"], d["dec0"]))
    def add(ra, dec, fam=2):
        x, y = w(ra % 360, dec)
        x, y = x * sc, y * sc
        PX, PY = proj(ra % 360, dec)
        ok = (x > -20) & (x < W + 20) & (y > -20) & (y < H + 20)
        # split into runs that stay on the image
        idx = np.where(ok)[0]
        if len(idx) < 30: return
        breaks = np.where(np.diff(idx) > 1)[0]
        for run in np.split(idx, breaks + 1):
            if len(run) >= 30: lines.append(np.stack([x[run], y[run], PX[run], PY[run], np.full(len(run), fam)], 1))
    t = np.linspace(0, 1, 4000)
    if polar_plate:
        for dec in np.arange(20, 89.5, 1.0): add(t * 360, np.full_like(t, dec), 0)
        for ra in np.arange(0, 360, 5.0): add(np.full_like(t, ra), 20 + t * 69.5, 1)
    else:
        lo, hi = max(-85, d["dec0"] - 45), min(85, d["dec0"] + 45)
        for dec in np.arange(math.ceil(lo), hi, 1.0):
            span = min(180, 80 / max(math.cos(math.radians(dec)), 0.1))
            add(d["ra0"] - span + t * 2 * span, np.full_like(t, dec), 0)
        r0 = 5 * round(d["ra0"] / 5)
        for ra in np.arange(r0 - 120, r0 + 120.1, 5.0): add(np.full_like(t, ra), lo + t * (hi - lo), 1)
    for lam in np.arange(0, 360, 5.0): add(*ecl2eq(np.full_like(t, lam), -85 + t * 170))
    for bet in np.arange(-80, 81, 5.0): add(*ecl2eq(t * 360, np.full_like(t, bet)))
    return lines


def snap_and_mark(ink, lines, search=9.0):
    """Move each candidate line sideways (by a smoothly varying offset) onto the engraved line it stands for,
    and mark the stretches where an engraved line really is there."""
    from scipy.ndimage import uniform_filter1d, median_filter
    H, W = ink.shape
    mark = np.zeros((H, W), np.uint8)
    found = []
    offs = np.arange(-search, search + 0.01, 0.5)
    for L in lines:
        # resample to about 2 px spacing
        seg = np.hypot(*np.diff(L[:, :2], axis=0).T); cum = np.concatenate([[0], np.cumsum(seg)])
        if cum[-1] < 60: continue
        q = np.arange(0, cum[-1], 2.0)
        P = np.stack([np.interp(q, cum, L[:, 0]), np.interp(q, cum, L[:, 1])], 1)
        PXY = np.stack([np.interp(q, cum, L[:, 2]), np.interp(q, cum, L[:, 3])], 1)
        T = np.gradient(P, axis=0); T /= np.maximum(np.hypot(*T.T), 1e-6)[:, None]
        N = np.stack([-T[:, 1], T[:, 0]], 1)
        X = (P[:, None, 0] + offs[None, :] * N[:, None, 0]).astype(np.float32)
        Y = (P[:, None, 1] + offs[None, :] * N[:, None, 1]).astype(np.float32)
        S = cv2.remap(ink, X, Y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        Ss = uniform_filter1d(S, 25, axis=0)                   # 50 px along the line
        best = median_filter(np.argmax(Ss, 1), size=41, mode="nearest")
        i = np.arange(len(P))
        val = Ss[i, best]
        bg = np.median(Ss, 1)
        good = (val - bg) > 0.09
        good = median_filter(good.astype(np.uint8), size=9) > 0
        Q = P + offs[best][:, None] * N
        inside = (Q[:, 0] >= 0) & (Q[:, 0] < W) & (Q[:, 1] >= 0) & (Q[:, 1] < H)
        good &= inside
        idx = np.where(good)[0]
        if len(idx) < 10: continue
        runs = [r for r in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1) if len(r) >= 15]
        if runs:
            # the stretch of this line where the engraving was found: start and end in projection
            # coordinates, mean Y, family, length in px, and the share of it that is covered
            a, b = runs[0][0], runs[-1][-1]
            allx = PXY[np.concatenate(runs), 0]
            found.append([allx.min(), allx.max(), PXY[a:b + 1, 1].mean(), L[0, 4], 2.0 * (b - a),
                          sum(len(r) for r in runs) / max(b - a, 1)])
        for run in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
            if len(run) < 10: continue
            cv2.polylines(mark, [np.round(Q[run] * 4).astype(np.int32)], False, 1, 3, cv2.LINE_8, 2)
    return mark, np.array(found).reshape(-1, 6)


def remove_grid(ink, mark, protect):
    remove = mark & (ink > 0.04).astype(np.uint8)
    remove[protect > 0] = 0
    keep = 1 - remove.astype(np.float32)
    num = cv2.GaussianBlur(ink * keep, (0, 0), 2.0); den = cv2.GaussianBlur(keep, (0, 0), 2.0)
    fill = num / np.maximum(den, 1e-3)
    clean = np.where(remove > 0, fill, ink).astype(np.float32)
    return clean, remove


def frame_mask(shape, sc, P, s):
    """The map area inside the plate frame: the measured corners, stepped in a little from the border."""
    H, W = shape
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(np.array(P["frame"], float) * sc).astype(np.int32)], 1)
    k = max(3, int(s * sc * 0.35))
    return cv2.erode(m, np.ones((k, k), np.uint8))


def constellation_mask(P, w, shape, sc, s):
    H, W = shape
    m = np.zeros((H, W), np.uint8)
    for con in P["cons"]:
        for poly in BOUNDS[con]:
            pts = []
            for (r0, d0), (r1, d1) in zip(poly, poly[1:] + poly[:1]):
                dr = ((r1 - r0 + 540) % 360) - 180
                k = max(2, int(max(abs(dr), abs(d1 - d0)) / 0.25))
                t = np.arange(k) / k
                pts.append(np.stack([r0 + dr * t, d0 + (d1 - d0) * t], 1))
            pts = np.concatenate(pts)
            r, dd = precess(pts[:, 0] % 360, pts[:, 1], EPOCH)
            px, py = w(r, dd)
            q = np.stack([px * sc, py * sc], 1)
            q = np.clip(q, -5 * W, 6 * W).astype(np.int32)
            cv2.fillPoly(m, [q], 1)
    grow = int(s * sc * 1.0)
    return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))


CON_IDS = [c["id"] for c in SKY["constellations"]]


def proj_xy(d, ra90, de90):
    return polar(ra90, de90) if d.get("proj") == "polar" else sinus(ra90, de90, d["ra0"], d["dec0"])


def plate_setup(P, src):
    """Model, frame and constellation labels of one plate, at the working resolution."""
    n = P["n"]
    fit = json.load(open(HERE / "cache" / "fits.json"))[n]
    d, s = fit["model"], fit["scale"]
    d["scale"] = s
    w = load_model(d)
    img = cv2.imread(str(src / f"Atlas_Coelestis_by_John_Flamsteed_(1729)_{n}.jpg"), cv2.IMREAD_GRAYSCALE)
    H, W = int(round(img.shape[0] * SCALE)), int(round(img.shape[1] * SCALE))
    frame = frame_mask((H, W), SCALE, P, s)
    depth = cv2.distanceTransform(frame, cv2.DIST_L2, 5)
    # label every pixel with the IAU constellation it shows (0 = none)
    lab = np.zeros((H, W), np.uint8)
    polar_plate = d.get("proj") == "polar"
    for k, con in enumerate(CON_IDS):
        if not polar_plate and con in ("UMi", "Oct"): continue      # around a pole: only the polar plate
        for poly in BOUNDS[con]:
            pts = []
            for (r0, d0), (r1, d1) in zip(poly, poly[1:] + poly[:1]):
                dr = ((r1 - r0 + 540) % 360) - 180
                m = max(2, int(max(abs(dr), abs(d1 - d0)) / 0.25))
                t = np.arange(m) / m
                pts.append(np.stack([r0 + dr * t, d0 + (d1 - d0) * t], 1))
            pts = np.concatenate(pts)
            r, dd = precess(pts[:, 0] % 360, pts[:, 1], EPOCH)
            X, Y = proj_xy(d, r, dd)
            if polar_plate:
                if dd.min() < -20: continue
            elif np.abs(X).max() > 80 or np.abs(Y).max() > 60:
                continue
            px, py = w(r, dd)
            cv2.fillPoly(lab, [np.stack([px * SCALE, py * SCALE], 1).astype(np.int32)], k + 1)
    prim = np.array([c in P["cons"] for c in CON_IDS])
    return dict(P=P, d=d, s=s, w=w, H=H, W=W, frame=frame, depth=depth, lab=lab, prim=prim, img=img, fit=fit)


def assign(setups, step=0.2):
    """Give each patch of sky to one plate: a plate that has the constellation among its own figures,
    and otherwise the plate on which the patch lies furthest inside the frame."""
    ra, de = np.meshgrid(np.arange(step / 2, 360, step), np.arange(-90 + step / 2, 90, step))
    ra, de = ra.ravel(), de.ravel()
    r90, d90 = precess(ra, de, EPOCH)
    best = np.full(ra.shape, -1.0); who = np.full(ra.shape, -1)
    hits = []
    for i, S in enumerate(setups):
        X, Y = proj_xy(S["d"], r90, d90)
        cand = np.where((d90 > 10) if S["d"].get("proj") == "polar" else ((np.abs(X) < 70) & (np.abs(Y) < 50)))[0]
        px, py = S["w"](r90[cand], d90[cand])
        px, py = np.round(px * SCALE).astype(int), np.round(py * SCALE).astype(int)
        ok = (px >= 0) & (px < S["W"]) & (py >= 0) & (py < S["H"])
        cand, px, py = cand[ok], px[ok], py[ok]
        inside = S["frame"][py, px] > 0
        cand, px, py = cand[inside], px[inside], py[inside]
        lab = S["lab"][py, px].astype(int)
        primary = (lab > 0) & S["prim"][np.maximum(lab - 1, 0)]
        score = S["depth"][py, px] + 1e6 * primary
        better = score > best[cand]
        best[cand[better]] = score[better]; who[cand[better]] = i
        hits.append((cand, px, py))
    masks = []
    for i, S in enumerate(setups):
        cand, px, py = hits[i]
        mine = who[cand] == i
        m = np.zeros((S["H"], S["W"]), np.uint8)
        m[py[mine], px[mine]] = 1
        # close the gaps between sampled points, then reach a little past the seam so neighbours overlap
        cell = int(math.ceil(step * S["s"] * SCALE)) + 2
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * cell + 1, 2 * cell + 1)))
        grow = int(S["s"] * SCALE * 0.35)
        m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))
        masks.append(m & S["frame"])
    return masks


def build(S, assigned):
    P, d, s, w, img, fit = S["P"], S["d"], S["s"], S["w"], S["img"], S["fit"]
    n = P["n"]
    stars = detect_stars(img)
    small = cv2.resize(img, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)
    H, W = small.shape
    ink = ink_map(small)
    lines = grid_lines(d, w, (H, W), SCALE, s)
    mark, found = snap_and_mark(ink, lines)
    frame = S["frame"]
    feather = s * SCALE * 0.3
    area = cv2.GaussianBlur(assigned.astype(np.float32), (0, 0), feather) * cv2.GaussianBlur(frame.astype(np.float32), (0, 0), feather / 2)
    area = np.clip(area * 1.15, 0, 1)
    protect = np.zeros((H, W), np.uint8)
    for x, y, a in stars:
        cv2.circle(protect, (int(x * SCALE), int(y * SCALE)), int(math.sqrt(a) * SCALE * 0.8) + 3, 1, -1)
    clean, removed = remove_grid(ink, mark, protect)
    # crop to where the overlay is visible
    ys, xs = np.where(area > 0.01)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    ink_c = np.clip((clean[y0:y1, x0:x1] - 0.04) / 0.32, 0, 1) ** 0.8
    rgb = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
    rgb[..., 0] = (ink_c * 255).astype(np.uint8)
    rgb[..., 1] = (area[y0:y1, x0:x1] * 255).astype(np.uint8)
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb).save(OUT / f"plate_{n}.jpg", quality=88, subsampling=0)
    # mesh: a regular grid in the plate's own projection, tied to J2000 positions
    Xg, Yg = np.meshgrid(np.arange(-90, 90.01, 0.5), np.arange(-60, 60.01, 0.5))
    if d.get("proj") == "polar":
        Xg, Yg = np.meshgrid(np.arange(-75, 75.01, 0.5), np.arange(-75, 75.01, 0.5))
    px, py = model_xy(w, Xg.ravel(), Yg.ravel())
    inside = (px * SCALE >= x0) & (px * SCALE <= x1) & (py * SCALE >= y0) & (py * SCALE <= y1)
    # far outside the plate the polynomial can fold back onto the image: keep to the plate's own span
    inside &= (np.abs(Xg.ravel()) <= 62) & (np.abs(Yg.ravel()) <= 42) if d.get("proj") != "polar" else inside
    Xs, Ys = Xg.ravel()[inside], Yg.ravel()[inside]
    step = 2.0
    gx = np.arange(Xs.min() - step, Xs.max() + 2 * step, step)
    gy = np.arange(Ys.min() - step, Ys.max() + 2 * step, step)
    MX, MY = np.meshgrid(gx, gy)
    qx, qy = model_xy(w, MX.ravel(), MY.ravel())
    u = (qx * SCALE - x0) / (x1 - x0); v = (qy * SCALE - y0) / (y1 - y0)
    ra90, de90 = inverse_proj(d, MX.ravel(), MY.ravel())
    ra, de = precess_back(ra90, de90)
    verts = []
    for a, b, c, e in zip(ra, de, u, v):
        if not (-0.3 < c < 1.3 and -0.3 < e < 1.3): c, e = -1, -1      # far off the image: never drawn
        verts += [round(float(a), 2), round(float(b), 2), round(float(c), 4), round(float(e), 4)]
    dbg = cv2.cvtColor(small, cv2.COLOR_GRAY2BGR)
    dbg[removed > 0] = (0, 0, 255)
    cv2.imwrite(str(HERE / "cache" / f"grid_{n}.jpg"), cv2.resize(dbg, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA))
    return dict(n=n, file=f"plate_{n}.jpg", title=P["title"], cons=P["cons"], nx=len(gx), ny=len(gy), v=verts,
                w=int(x1 - x0), h=int(y1 - y0), matched=fit["matched"])


if __name__ == "__main__":
    src = Path(sys.argv[1])
    want = set(sys.argv[2:])
    cfg = json.load(open(HERE / "flamsteed_plates.json"))["plates"]
    out = OUT / "plates.json"
    have = {p["n"]: p for p in json.load(open(out))["plates"]} if out.exists() else {}
    setups = [plate_setup(P, src) for P in cfg]          # every plate takes part in deciding who draws what
    masks = assign(setups)
    for S, m in zip(setups, masks):
        P = S["P"]
        if want and P["n"] not in want: continue
        r = build(S, m)
        have[P["n"]] = r
        print(P["n"], P["title"], f"{r['w']}x{r['h']}", f"mesh {r['nx']}x{r['ny']}", flush=True)
    json.dump(dict(source="John Flamsteed, Atlas Coelestis (London, 1729); photographs of the plates via Wikimedia Commons (RareMaps), public domain",
                   epoch=EPOCH, plates=[have[k] for k in sorted(have)]), open(out, "w"), separators=(",", ":"))
