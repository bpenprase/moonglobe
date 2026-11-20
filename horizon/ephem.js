// ephem.js: positions of the Sun, Moon and planets for the Horizon Sky Explorer.
//
// Method: Paul Schlyter's "How to compute planetary positions" (orbital elements of date, a Kepler solution, and
// the main perturbations of the Moon, Jupiter, Saturn and Uranus). Accuracy is about 1 to 2 arcminutes for the
// planets and a few arcminutes for the Moon over several centuries around 2000, which is far better than the eye
// can tell on the sphere. Results are returned for the J2000 equinox, to match the star catalog.
//
// Time argument everywhere: dUT = days since 2000 January 1, 12:00 Universal Time (J2000.0).

const RAD = Math.PI / 180;
const sind = x => Math.sin(x * RAD), cosd = x => Math.cos(x * RAD);
const atan2d = (y, x) => Math.atan2(y, x) / RAD, asind = x => Math.asin(Math.max(-1, Math.min(1, x))) / RAD;
const rev = x => ((x % 360) + 360) % 360;

// orbital elements for Schlyter's day number d (0 at 2000 Jan 0.0 UT)
const ELEMENTS = {
  sun:     d => ({ N: 0, i: 0, w: 282.9404 + 4.70935e-5 * d, a: 1, e: 0.016709 - 1.151e-9 * d, M: 356.0470 + 0.9856002585 * d }),
  moon:    d => ({ N: 125.1228 - 0.0529538083 * d, i: 5.1454, w: 318.0634 + 0.1643573223 * d, a: 60.2666, e: 0.054900, M: 115.3654 + 13.0649929509 * d }),
  mercury: d => ({ N: 48.3313 + 3.24587e-5 * d, i: 7.0047 + 5.00e-8 * d, w: 29.1241 + 1.01444e-5 * d, a: 0.387098, e: 0.205635 + 5.59e-10 * d, M: 168.6562 + 4.0923344368 * d }),
  venus:   d => ({ N: 76.6799 + 2.46590e-5 * d, i: 3.3946 + 2.75e-8 * d, w: 54.8910 + 1.38374e-5 * d, a: 0.723330, e: 0.006773 - 1.302e-9 * d, M: 48.0052 + 1.6021302244 * d }),
  mars:    d => ({ N: 49.5574 + 2.11081e-5 * d, i: 1.8497 - 1.78e-8 * d, w: 286.5016 + 2.92961e-5 * d, a: 1.523688, e: 0.093405 + 2.516e-9 * d, M: 18.6021 + 0.5240207766 * d }),
  jupiter: d => ({ N: 100.4542 + 2.76854e-5 * d, i: 1.3030 - 1.557e-7 * d, w: 273.8777 + 1.64505e-5 * d, a: 5.20256, e: 0.048498 + 4.469e-9 * d, M: 19.8950 + 0.0830853001 * d }),
  saturn:  d => ({ N: 113.6634 + 2.38980e-5 * d, i: 2.4886 - 1.081e-7 * d, w: 339.3939 + 2.97661e-5 * d, a: 9.55475, e: 0.055546 - 9.499e-9 * d, M: 316.9670 + 0.0334442282 * d }),
  uranus:  d => ({ N: 74.0005 + 1.3978e-5 * d, i: 0.7733 + 1.9e-8 * d, w: 96.6612 + 3.0565e-5 * d, a: 19.18171 - 1.55e-8 * d, e: 0.047318 + 7.45e-9 * d, M: 142.5905 + 0.011725806 * d }),
  neptune: d => ({ N: 131.7806 + 3.0173e-5 * d, i: 1.7700 - 2.55e-7 * d, w: 272.8461 - 6.027e-6 * d, a: 30.05826 + 3.313e-8 * d, e: 0.008606 + 2.15e-9 * d, M: 260.2471 + 0.005995147 * d }),
};

function kepler(M, e) {                       // eccentric anomaly in degrees
  M = rev(M); let E = M + (e / RAD) * sind(M) * (1 + e * cosd(M));
  for (let k = 0; k < 8; k++) { const dE = (E - (e / RAD) * sind(E) - M) / (1 - e * cosd(E)); E -= dE; if (Math.abs(dE) < 1e-7) break; }
  return E;
}
// position in the orbit's own ecliptic frame (of date): longitude, latitude, distance
function orbit(el) {
  const E = kepler(el.M, el.e);
  const xv = el.a * (cosd(E) - el.e), yv = el.a * Math.sqrt(1 - el.e * el.e) * sind(E);
  const v = atan2d(yv, xv), r = Math.hypot(xv, yv), u = v + el.w;
  const x = r * (cosd(el.N) * cosd(u) - sind(el.N) * sind(u) * cosd(el.i));
  const y = r * (sind(el.N) * cosd(u) + cosd(el.N) * sind(u) * cosd(el.i));
  const z = r * sind(u) * sind(el.i);
  return { lon: rev(atan2d(y, x)), lat: atan2d(z, Math.hypot(x, y)), r };
}
const rect = (lon, lat, r) => [r * cosd(lon) * cosd(lat), r * sind(lon) * cosd(lat), r * sind(lat)];

const EPS2000 = 23.4392911;
// ecliptic of date -> J2000 ecliptic: undo the general precession in longitude since 2000
function toJ2000Ecl(lon, lat, d) { return { lon: rev(lon - 3.82394e-5 * d), lat }; }
function eclToEq(lon, lat) {                   // J2000 ecliptic -> J2000 right ascension and declination
  const x = cosd(lon) * cosd(lat), y = sind(lon) * cosd(lat), z = sind(lat), e = EPS2000;
  const ye = y * cosd(e) - z * sind(e), ze = y * sind(e) + z * cosd(e);
  return { ra: rev(atan2d(ye, x)), dec: asind(ze) };
}

export const BODIES = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune'];

// Everything at one instant. Geocentric, J2000. The Moon also carries its distance in Earth radii, so the caller
// can correct it for the observer's place on Earth (parallax, up to a degree).
export function compute(dUT) {
  const d = dUT + 1.5;                          // Schlyter's day number
  const out = {};
  // the Sun (Earth's orbit seen from the other side)
  const se = ELEMENTS.sun(d), sE = kepler(se.M, se.e);
  const sxv = cosd(sE) - se.e, syv = Math.sqrt(1 - se.e * se.e) * sind(sE);
  const sv = atan2d(syv, sxv), sr = Math.hypot(sxv, syv), slon = rev(sv + se.w);
  const [xs, ys] = [sr * cosd(slon), sr * sind(slon)];
  { const j = toJ2000Ecl(slon, 0, d); out.sun = { ...eclToEq(j.lon, j.lat), lon: j.lon, lat: 0, dist: sr, mag: -26.74 }; }

  // the Moon
  {
    const el = ELEMENTS.moon(d), o = orbit(el);
    const Ms = rev(se.M), Mm = rev(el.M), Ls = rev(se.M + se.w), Lm = rev(el.M + el.w + el.N);
    const D = Lm - Ls, F = Lm - el.N;
    const dlon = -1.274 * sind(Mm - 2 * D) + 0.658 * sind(2 * D) - 0.186 * sind(Ms) - 0.059 * sind(2 * Mm - 2 * D) - 0.057 * sind(Mm - 2 * D + Ms)
      + 0.053 * sind(Mm + 2 * D) + 0.046 * sind(2 * D - Ms) + 0.041 * sind(Mm - Ms) - 0.035 * sind(D) - 0.031 * sind(Mm + Ms)
      - 0.015 * sind(2 * F - 2 * D) + 0.011 * sind(Mm - 4 * D);
    const dlat = -0.173 * sind(F - 2 * D) - 0.055 * sind(Mm - F - 2 * D) - 0.046 * sind(Mm + F - 2 * D) + 0.033 * sind(F + 2 * D) + 0.017 * sind(2 * Mm + F);
    const dr = -0.58 * cosd(Mm - 2 * D) - 0.46 * cosd(2 * D);
    const lon = rev(o.lon + dlon), lat = o.lat + dlat, r = o.r + dr;
    const j = toJ2000Ecl(lon, lat, d);
    const elong = Math.acos(Math.max(-1, Math.min(1, cosd(lon - slon) * cosd(lat)))) / RAD;
    const phaseAngle = 180 - elong;              // close enough: the Moon is 400 times nearer than the Sun
    const k = (1 + cosd(phaseAngle)) / 2;          // illuminated fraction
    out.moon = { ...eclToEq(j.lon, j.lat), lon: j.lon, lat: j.lat, distER: r, distKm: r * 6378.14, elong, illum: k,
      waxing: rev(lon - slon) < 180, age: rev(lon - slon) / 360 * 29.530589,
      mag: -12.73 + 0.026 * Math.abs(phaseAngle) + 4e-9 * Math.pow(phaseAngle, 4) };
  }

  // the planets: heliocentric orbits, perturbed, then seen from Earth
  const M = name => rev(ELEMENTS[name](d).M);
  const Mj = M('jupiter'), Msat = M('saturn'), Mu = M('uranus');
  for (const name of BODIES) {
    const el = ELEMENTS[name](d), o = orbit(el);
    let { lon, lat, r } = o;
    if (name === 'jupiter') lon += -0.332 * sind(2 * Mj - 5 * Msat - 67.6) - 0.056 * sind(2 * Mj - 2 * Msat + 21) + 0.042 * sind(3 * Mj - 5 * Msat + 21)
      - 0.036 * sind(Mj - 2 * Msat) + 0.022 * cosd(Mj - Msat) + 0.023 * sind(2 * Mj - 3 * Msat + 52) - 0.016 * sind(Mj - 5 * Msat - 69);
    if (name === 'saturn') {
      lon += 0.812 * sind(2 * Mj - 5 * Msat - 67.6) - 0.229 * cosd(2 * Mj - 4 * Msat - 2) + 0.119 * sind(Mj - 2 * Msat - 3)
        + 0.046 * sind(2 * Mj - 6 * Msat - 69) + 0.014 * sind(Mj - 3 * Msat + 32);
      lat += -0.020 * cosd(2 * Mj - 4 * Msat - 2) + 0.018 * sind(2 * Mj - 6 * Msat - 49);
    }
    if (name === 'uranus') lon += 0.040 * sind(Msat - 2 * Mu + 6) + 0.035 * sind(Msat - 3 * Mu + 33) - 0.015 * sind(Mj - Mu + 20);
    const [xh, yh, zh] = rect(lon, lat, r);
    const xg = xh + xs, yg = yh + ys, zg = zh;
    const R = Math.hypot(xg, yg, zg), glon = rev(atan2d(yg, xg)), glat = atan2d(zg, Math.hypot(xg, yg));
    const FV = Math.acos(Math.max(-1, Math.min(1, (r * r + R * R - sr * sr) / (2 * r * R)))) / RAD;   // phase angle
    const l5 = 5 * Math.log10(r * R);
    let mag = { mercury: -0.36 + l5 + 0.027 * FV + 2.2e-13 * FV ** 6, venus: -4.34 + l5 + 0.013 * FV + 4.2e-7 * FV ** 3,
      mars: -1.51 + l5 + 0.016 * FV, jupiter: -9.25 + l5 + 0.014 * FV, saturn: -9.0 + l5 + 0.044 * FV,
      uranus: -7.15 + l5 + 0.001 * FV, neptune: -6.90 + l5 + 0.001 * FV }[name];
    let ringTilt = null;
    if (name === 'saturn') {
      const ir = 28.06, Nr = 169.51 + 3.82e-5 * d;
      ringTilt = asind(sind(glat) * cosd(ir) - cosd(glat) * sind(ir) * sind(glon - Nr));
      mag += -2.6 * Math.abs(sind(ringTilt)) + 1.2 * sind(ringTilt) ** 2;
    }
    const j = toJ2000Ecl(glon, glat, d);
    const elong = Math.acos(Math.max(-1, Math.min(1, cosd(glon - slon) * cosd(glat)))) / RAD;
    out[name] = { ...eclToEq(j.lon, j.lat), lon: j.lon, lat: j.lat, dist: R, rHelio: r, mag, phaseAngle: FV, elong,
      eastOfSun: rev(glon - slon) < 180, illum: (1 + cosd(FV)) / 2, ringTilt };
  }
  return out;
}

// apparent diameters in arcseconds at 1 AU (Schlyter), for the info cards
export const DIAM1AU = { mercury: 6.74, venus: 16.92, mars: 9.36, jupiter: 196.94, saturn: 165.6, uranus: 65.8, neptune: 62.2 };
