"""Measure the star positions in the Keck/UCLA Galactic Center orbit movie.

Run from the blackhole/ folder:
    python tools/track_stars.py          (takes about 3 minutes)
    python tools/build_page.py

Steps
1. Find every star in every frame. Stars are round blobs, so the program keeps
   the parts of each frame that are wider than the thin orbit lines and finds
   the center of each blob.
2. The movie shows one year step (0.1 yr) every 3 frames, from 1995.5 to 2025.3.
   One frame from each step is used.
3. Detections are linked from step to step into short, unambiguous segments.
4. The segments for each star are joined (the lists in CHAINS below were checked
   by eye against the orbits drawn in the movie), and a Kepler orbit is fitted
   to each star with Sgr A* at the focus. The fitted orbit gives a smooth
   position for every year step. Median misfit is under 1 movie pixel.
5. The results go to tools/stars.json, which build_page.py puts into index.html.

Scale: the movie's 0.1 arcsecond bar is 120 pixels long, so 1 arcsec = 1200 px.
Needs: numpy, scipy, opencv-python.
"""
import json
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import least_squares, linear_sum_assignment

HERE = Path(__file__).resolve().parent
MOVIE = HERE.parent / "gc_orbits.mp4"
PX_PER_ARCSEC = 1200.0
SGR_A = np.array([989.1, 539.1])     # the white star symbol, in movie pixels
N_STEPS = 299                        # 1995.5 ... 2025.3 in steps of 0.1 yr
YEARS = 1995.5 + 0.1 * np.arange(N_STEPS)


def frame_of_step(k):
    """Frames 0-59 show 1995.5 with labels, then 3 frames per 0.1 yr, then 2025.3 is held."""
    if k == 0:
        return 30
    if k == N_STEPS - 1:
        return 1000
    return 61 + 3 * (k - 1)


# ---------- 1. find the stars in each frame ----------
def find_blobs(frame):
    mx, mn = frame.max(2), frame.min(2)
    mask = ((mx > 25) & (mn < 200)).astype(np.uint8)     # colored pixels, not white text
    mask[150:225, 1560:1850] = 0                          # the year label
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, disk)   # removes thin orbit lines
    dist = cv2.GaussianBlur(cv2.distanceTransform(mask, cv2.DIST_L2, 5), (0, 0), 1.5)
    peaks = (dist == ndi.maximum_filter(dist, size=13)) & (dist > 11)
    out = []
    for y, x in zip(*np.nonzero(peaks)):
        y0, y1, x0, x1 = max(y - 3, 0), y + 4, max(x - 3, 0), x + 4
        w = dist[y0:y1, x0:x1] ** 4
        gy, gx = np.mgrid[y0:y0 + w.shape[0], x0:x0 + w.shape[1]]
        out.append(((w * gx).sum() / w.sum(), (w * gy).sum() / w.sum(), dist[y, x]))
    # merge peaks closer than 16 px (one star split by a line across it)
    out.sort(key=lambda p: -p[2])
    merged = []
    for x, y, v in out:
        if all(np.hypot(x - a, y - b) >= 16 for a, b in merged):
            merged.append((x, y))
    return np.array(merged) if merged else np.zeros((0, 2))


def detect_all():
    cap = cv2.VideoCapture(str(MOVIE))
    wanted = {frame_of_step(k): k for k in range(N_STEPS)}
    found, f = [None] * N_STEPS, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if f in wanted:
            found[wanted[f]] = find_blobs(frame)
        f += 1
    return found


# ---------- 3. link detections into segments ----------
def build_segments(found):
    segs, active = [], []
    for p in found[0]:
        segs.append({"k0": 0, "pts": [p]})
        active.append(len(segs) - 1)
    for k in range(1, N_STEPS):
        P, new_active, used = found[k], [], set()
        if active and len(P):
            pred = []
            for s in active:
                pts = segs[s]["pts"]
                pred.append(pts[-1] + (pts[-1] - pts[-2]) if len(pts) >= 2 else pts[-1])
            pred = np.array(pred)
            C = np.hypot(pred[:, None, 0] - P[None, :, 0], pred[:, None, 1] - P[None, :, 1])
            for a, b in zip(*linear_sum_assignment(np.where(C < 30, C, 1e6))):
                if C[a, b] >= 30:
                    continue
                row, col = np.sort(C[a]), np.sort(C[:, b])
                ambiguous = (len(row) > 1 and row[1] < max(1.6 * C[a, b], 12)) or \
                            (len(col) > 1 and col[1] < max(1.6 * C[a, b], 12))
                if ambiguous:
                    continue
                segs[active[a]]["pts"].append(P[b])
                new_active.append(active[a])
                used.add(b)
        for j, p in enumerate(P):
            if j not in used:
                segs.append({"k0": k, "pts": [p]})
                new_active.append(len(segs) - 1)
        active = new_active
    return [s for s in segs if len(s["pts"]) >= 4]


# Segment numbers for each star (from the numbered segment map).
CHAINS = {
    "S0-2": [0, 19, 27, 34, 36, 37, 38, 41, 42, 43, 45], "S0-1": [3], "S0-3": [2, 51],
    "S0-4": [1, 30, 33], "S0-5": [4], "S0-7": [6], "S0-8": [8], "S0-16": [7, 18, 22, 35],
    "S0-17": [10], "S0-19": [17, 20], "S0-20": [9, 31], "S0-26": [5], "S0-30": [11],
    "S0-37": [16, 25], "S0-38": [14, 21, 48], "S0-40": [13, 23, 50], "S0-49": [12],
    "S0-102": [15, 26, 32, 40], "Unlabeled": [28, 44, 46, 47, 49],
}
ORDER = ["S0-2", "S0-38", "S0-102", "S0-16", "S0-19", "S0-20", "S0-49", "S0-37", "S0-40",
         "S0-5", "S0-3", "S0-1", "S0-4", "S0-17", "S0-26", "S0-8", "S0-7", "S0-30", "Unlabeled"]


# ---------- 4. Kepler orbit fits (Thiele-Innes form, focus fixed at Sgr A*) ----------
def eccentric_anomaly(M, e):
    E = M.copy() if e < 0.8 else np.pi * np.sign(np.sin(M)) + 0 * M
    E = np.where(np.abs(np.sin(M)) < 1e-9, M, E)
    for _ in range(60):
        E = E - (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
    return E


def design(t, P, e, tp):
    M = np.mod(2 * np.pi * (t - tp) / P + np.pi, 2 * np.pi) - np.pi
    E = eccentric_anomaly(M, e)
    return np.stack([np.cos(E) - e, np.sqrt(1 - e * e) * np.sin(E)], 1)


def solve_linear(t, xy, P, e, tp):
    D = design(t, P, e, tp)
    cx = np.linalg.lstsq(D, xy[:, 0] - SGR_A[0], rcond=None)[0]
    cy = np.linalg.lstsq(D, xy[:, 1] - SGR_A[1], rcond=None)[0]
    return D, cx, cy


def residuals(q, t, xy):
    P, e, tp = np.exp(q[0]), 1 / (1 + np.exp(-q[1])), q[2]
    D, cx, cy = solve_linear(t, xy, P, e, tp)
    return np.concatenate([D @ cx + SGR_A[0] - xy[:, 0], D @ cy + SGR_A[1] - xy[:, 1]])


def fit_orbit(t, xy):
    best = None
    for P in np.exp(np.linspace(np.log(4), np.log(400), 40)):
        for e in (0.05, 0.3, 0.5, 0.7, 0.85, 0.95):
            for ph in np.linspace(0, 1, 12, endpoint=False):
                q = [np.log(P), np.log(e / (1 - e)), t[0] + ph * P]
                s = (residuals(q, t, xy) ** 2).sum()
                if best is None or s < best[0]:
                    best = (s, q)
    q = least_squares(residuals, best[1], args=(t, xy)).x
    P, e, tp = np.exp(q[0]), 1 / (1 + np.exp(-q[1])), q[2]
    _, cx, cy = solve_linear(t, xy, P, e, tp)
    return dict(P=P, e=e, tp=tp, cx=cx, cy=cy)


def orbit_xy(m, t):
    D = design(np.asarray(t, float), m["P"], m["e"], m["tp"])
    return np.stack([D @ m["cx"] + SGR_A[0], D @ m["cy"] + SGR_A[1]], 1)


def main():
    print("Finding stars in the movie frames ...")
    segs = build_segments(detect_all())
    stars = []
    for name in ORDER:
        k, p = [], []
        for i in CHAINS[name]:
            k += list(segs[i]["k0"] + np.arange(len(segs[i]["pts"])))
            p += list(segs[i]["pts"])
        k, p = np.array(k), np.array(p, float)
        m = fit_orbit(YEARS[k], p)
        for _ in range(2):          # drop points spoiled by crowding, then refit
            r = np.hypot(*(orbit_xy(m, YEARS[k]) - p).T)
            keep = r < max(3 * np.median(r), 4)
            m = fit_orbit(YEARS[k][keep], p[keep])
        r = np.hypot(*(orbit_xy(m, YEARS[k]) - p).T)
        A, F = m["cx"]; B, G = m["cy"]
        u, v = (A * A + B * B + F * F + G * G) / 2, A * G - B * F
        a = np.sqrt(u + np.sqrt(u * u - v * v)) / PX_PER_ARCSEC
        steps = np.arange(k.min(), k.max() + 1) if name != "Unlabeled" else np.arange(k.min(), N_STEPS)
        xy = np.round(orbit_xy(m, YEARS[steps]), 1)
        star = {"n": name, "k0": int(steps[0]), "xy": [float(c) for c in xy.ravel()]}
        if (len(steps) - 1) * 0.1 / m["P"] >= 0.45:     # only stars that show enough of their orbit
            star["m"] = {"P": round(m["P"], 1), "e": round(m["e"], 3), "a": round(a, 4)}
        stars.append(star)
        print(f"{name:9s} P={m['P']:7.1f} yr  e={m['e']:.3f}  a={a:.4f}\"  median misfit {np.median(r):.2f} px")
    (HERE / "stars.json").write_text(json.dumps(stars, separators=(",", ":")))
    print("Wrote", HERE / "stars.json")


if __name__ == "__main__":
    main()
