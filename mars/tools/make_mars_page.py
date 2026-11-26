"""
make_mars_page.py
Builds mars/index.html from the Moon page (moon/index.html) by swapping in everything that is specific to Mars:
data files, map modes (Viking color, THEMIS infrared, MOLA elevation), feature categories, landing sites,
views and text. Run it after changing the Moon page so both globes keep the same features:
    python3 mars/tools/make_mars_page.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
s = (ROOT / "moon" / "index.html").read_text().replace("'../data/", "'data/")

def rep(a, b, count=1):
    global s
    if a not in s:
        raise SystemExit("make_mars_page: text not found, the Moon page has changed here:\n" + a[:200])
    s = s.replace(a, b, count)

# ---------------------------------------------------------------- titles and text
rep("<title>Lunar Globe Explorer</title>", "<title>Mars Globe Explorer</title>")
rep('<div class="t">Lunar Globe Explorer</div>', '<div class="t">Mars Globe Explorer</div>')
rep("Loading the Moon</div>", "Loading Mars</div>")
rep("<h1>Lunar Globe Explorer</h1>", "<h1>Mars Globe Explorer</h1>")
rep('<a class="xlink" href="../mars/">Explore Mars &rarr;</a> &middot; <a class="xlink" href="../sky/">Explore the sky &rarr;</a>', '<a class="xlink" href="../moon/">Explore the Moon &rarr;</a> &middot; <a class="xlink" href="../sky/">Explore the sky &rarr;</a>')
rep('.xlink{color:#ffb68a;', '.xlink{color:#9cc8ff;')
rep('placeholder="Find a crater, mare or landing site"', 'placeholder="Find a volcano, canyon, crater or lander"')
rep("'Move over the Moon to read coordinates'", "'Move over Mars to read coordinates'")
rep(">Move over the Moon to read coordinates<", ">Move over Mars to read coordinates<")
rep("'Could not load the Moon data: '", "'Could not load the Mars data: '")

# ---------------------------------------------------------------- colors and label styles
rep("--gold:#e2b45c; --mare:#9cc8ff; --crater:#f3f5fa; --mount:#e8c48f; --other:#9fe0b8; --sat:#b7bfcf; --l100:#ffd166; --land:#ff9a62;",
    "--gold:#e2b45c; --region:#ffd2b0; --volcano:#ff9b7a; --canyon:#9fe0b8; --crater:#f3f5fa; --other:#c9c2ff; --albedo:#e8d48f; --land:#ffe066;")
rep(""".k-mare{color:var(--mare);font-family:Spectral,serif;font-style:italic;font-size:15px;letter-spacing:.06em}
.k-crater{color:var(--crater);font-size:12px}
.k-mount{color:var(--mount);font-size:12px}
.k-other{color:var(--other);font-size:11.5px}
.k-satellite{color:var(--sat);font-size:10.5px;opacity:.9}
.k-l100{color:var(--l100);font-size:11.5px;font-weight:500}
.k-l100::before{content:"\\25C6";font-size:9px;margin-right:4px;vertical-align:1px}""",
""".k-region{color:var(--region);font-family:Spectral,serif;font-style:italic;font-size:15px;letter-spacing:.06em}
.k-volcano{color:var(--volcano);font-size:12.5px;font-weight:600}
.k-canyon{color:var(--canyon);font-size:12px}
.k-crater{color:var(--crater);font-size:12px}
.k-other{color:var(--other);font-size:11.5px}
.k-albedo{color:var(--albedo);font-family:Spectral,serif;font-style:italic;font-size:14px;letter-spacing:.04em;opacity:.95}""")

# ---------------------------------------------------------------- panel controls
rep("""<div class="seg" id="mode"><button data-v="0" class="on">Surface</button><button data-v="1">Elevation</button><button data-v="2">Blend</button></div>""",
    """<div class="seg" id="mode"><button data-v="0" class="on">Color</button><button data-v="1">Infrared</button><button data-v="2">Elevation</button><button data-v="3">Blend</button></div>
    <div class="note" id="modeNote">Viking orbiter color mosaic.</div>""")
rep("""    <label class="chk"><input type="checkbox" id="L-mare" checked><span class="sw" style="background:var(--mare)"></span>Maria, lakes &amp; bays</label>
    <label class="chk"><input type="checkbox" id="L-crater" checked><span class="sw" style="background:var(--crater)"></span>Craters</label>
    <label class="chk"><input type="checkbox" id="L-mount" checked><span class="sw" style="background:var(--mount)"></span>Mountains &amp; capes</label>
    <label class="chk"><input type="checkbox" id="L-other" checked><span class="sw" style="background:var(--other)"></span>Valleys, rilles &amp; ridges</label>
    <label class="chk"><input type="checkbox" id="L-satellite" checked><span class="sw" style="background:var(--sat)"></span>Satellite craters (A, B, C&hellip;) up close</label>
    <label class="chk"><input type="checkbox" id="L-l100" checked><span class="sw" style="background:var(--l100)"></span>Lunar 100 (Charles Wood)</label>
    <label class="chk"><input type="checkbox" id="L-land" checked><span class="sw" style="background:var(--land)"></span>Landing sites</label>""",
"""    <label class="chk"><input type="checkbox" id="L-land" checked><span class="sw" style="background:var(--land)"></span>Landers and rovers</label>
    <label class="chk"><input type="checkbox" id="L-volcano" checked><span class="sw" style="background:var(--volcano)"></span>Volcanoes</label>
    <label class="chk"><input type="checkbox" id="L-canyon" checked><span class="sw" style="background:var(--canyon)"></span>Canyons, valleys &amp; channels</label>
    <label class="chk"><input type="checkbox" id="L-region" checked><span class="sw" style="background:var(--region)"></span>Plains, plateaus &amp; highlands</label>
    <label class="chk"><input type="checkbox" id="L-crater" checked><span class="sw" style="background:var(--crater)"></span>Craters</label>
    <label class="chk"><input type="checkbox" id="L-other" checked><span class="sw" style="background:var(--other)"></span>Other landforms (mesas, chaos, dunes&hellip;)</label>
    <label class="chk"><input type="checkbox" id="L-albedo"><span class="sw" style="background:var(--albedo)"></span>Classical telescope names (albedo features)</label>""")
rep("""<div class="note">More names appear as you zoom in. Up close, every IAU-named feature is shown.</div>""",
    """<div class="note">More names appear as you zoom in. Up close, every IAU-named feature is shown.</div>""")
rep("""      <button class="btn" data-view="near">Near side</button><button class="btn" data-view="far">Far side</button>
      <button class="btn" data-view="north">North pole</button><button class="btn" data-view="south">South pole</button>
      <button class="btn" data-view="east">East limb</button><button class="btn" data-view="west">West limb</button>""",
"""      <button class="btn" data-view="tharsis">Tharsis volcanoes</button><button class="btn" data-view="valles">Valles Marineris</button>
      <button class="btn" data-view="hellas">Hellas basin</button><button class="btn" data-view="elysium">Elysium &amp; Gale</button>
      <button class="btn" data-view="north">North pole</button><button class="btn" data-view="south">South pole</button>""")
rep("""<div class="note" id="detNote">Sharp LROC images (about 100 m per pixel) fade in as you zoom into these regions.</div>""",
    """<div class="note" id="detNote">Sharp THEMIS infrared images (about 100 m per pixel) fade in as you zoom into these regions.</div>""")

# class feature list: Mars examples
rep("""Partial or misspelled names find the closest IAU name, so <b>Appenninus</b> finds Montes Apenninus and <b>Sea of Tranquility</b> finds Mare Tranquillitatis.""",
    """Partial or misspelled names find the closest IAU name, so <b>Olympus</b> finds Olympus Mons and <b>Marineris</b> finds Valles Marineris.""")
rep('placeholder="Maria Lopez, Copernicus&#10;Ken Sato, Apenninus&#10;Ava Chen, Apollo 15"', 'placeholder="Maria Lopez, Olympus Mons&#10;Ken Sato, Marineris&#10;Ava Chen, Curiosity"')
rep("""const TEMPLATE = ['student,feature', 'Student One,Copernicus', 'Student Two,Mare Tranquillitatis', 'Student Three,Apenninus', 'Student Four,Apollo 15', 'Student Five,Sea of Crises'];""",
    """const TEMPLATE = ['student,feature', 'Student One,Olympus Mons', 'Student Two,Valles Marineris', 'Student Three,Gale', 'Student Four,Curiosity', 'Student Five,Hellas'];""")

# about the data
i0 = s.index("      <p>Surface: LRO Camera"); i1 = s.index("      <p>Longitudes are east positive.")
s = s[:i0] + """      <p>Color: Viking Orbiter MDIM 2.1 colorized global mosaic (USGS / NASA Ames), about 232 m per pixel in the original.</p>
      <p>Infrared: Mars Odyssey THEMIS daytime infrared global mosaic (NASA/JPL/Arizona State University), about 100 m per pixel.
      Warm, sunlit slopes look bright, so it shows the shape of the land very clearly.</p>
      <p>Elevation: Mars Global Surveyor MOLA laser altimeter (NASA/GSFC), resampled to 8 pixels per degree. Heights are relative to
      the MOLA areoid, the Martian equivalent of sea level.</p>
      <p>Names: IAU <a href="https://planetarynames.wr.usgs.gov/" target="_blank" rel="noopener">Gazetteer of Planetary Nomenclature</a> (USGS).
      Maps and close-ups come from the NASA <a href="https://trek.nasa.gov/mars/" target="_blank" rel="noopener">Mars Trek</a> tile service.</p>
""" + s[i1:]
rep("<p>Longitudes are east positive. Lunar near side faces you at the start.</p>", "<p>Longitudes are east positive (planetocentric).</p>")
rep("""<div id="legend"><div>Elevation relative to 1737.4 km</div>""", """<div id="legend"><div>Elevation relative to the MOLA areoid</div>""")
rep("""<span>&minus;9 km</span><span>0</span><span>+10.7 km</span>""", """<span>&minus;8.2 km</span><span>0</span><span>+21.2 km</span>""")

# ---------------------------------------------------------------- constants, view, atmosphere
rep("const R_KM = 1737.4, HMIN = -9.0, HMAX = 10.7;", "const R_KM = 3389.5, HMIN = -8.2, HMAX = 21.2;")
rep("camera.position.set(0, 0, 4.2 * fitK());",
    """{ const v0 = new THREE.Vector3(Math.cos(5 * Math.PI / 180) * Math.sin(-80 * Math.PI / 180), Math.sin(5 * Math.PI / 180), Math.cos(5 * Math.PI / 180) * Math.cos(-80 * Math.PI / 180));
  camera.position.copy(v0.multiplyScalar(4.2 * fitK())); }""")
rep("""const VIEWS = { near: [0, 0, 4.2], far: [0, 180, 4.2], north: [89.4, 0, 3.6], south: [-89.4, 0, 3.6], east: [0, 90, 3.6], west: [0, -90, 3.6] };""",
    """const VIEWS = { tharsis: [5, -115, 2.4], valles: [-9, -68, 2.2], hellas: [-40, 68, 2.6], elysium: [12, 140, 2.6], north: [89.4, 0, 3.4], south: [-89.4, 0, 3.4] };""")
rep("function wholeMoon() {", "function wholeMoon() {  // whole planet")

# thin dusty atmosphere glow at the limb
rep("const material = new THREE.ShaderMaterial({ uniforms, vertexShader: vert, fragmentShader: frag });",
"""const material = new THREE.ShaderMaterial({ uniforms, vertexShader: vert, fragmentShader: frag });
{ // a thin, dusty atmosphere seen at the edge of the planet
  const atm = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, side: THREE.BackSide, blending: THREE.AdditiveBlending,
    vertexShader: `varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `varying vec3 vN; varying vec3 vV; void main(){ float d = abs(dot(vN, vV)); float f = pow(smoothstep(0.0, 0.17, d), 1.6) * (1.0 - smoothstep(0.17, 0.5, d)); gl_FragColor = vec4(vec3(1.0, 0.62, 0.42) * f * 0.42, 1.0); }` });
  scene.add(new THREE.Mesh(new THREE.SphereGeometry(1.014, 128, 64), atm));
}""")

# ---------------------------------------------------------------- shader: color + infrared + elevation
rep("uniform sampler2D albedoTex, heightTex;", "uniform sampler2D albedoTex, irTex, heightTex;")
rep("""  float alb = texture(albedoTex, vUv).r;
  alb = mix(alb, clamp(t1 * dg1.x + dg1.y, 0.0, 1.0), w1);
  alb = mix(alb, clamp(t0 * dg0.x + dg0.y, 0.0, 1.0), w0);""",
"""  vec3 colr = texture(albedoTex, vUv).rgb;
  float ir0 = texture(irTex, vUv).r;
  float alb = ir0;                                   // infrared, sharpened by any close-up patches
  alb = mix(alb, clamp(t1 * dg1.x + dg1.y, 0.0, 1.0), w1);
  alb = mix(alb, clamp(t0 * dg0.x + dg0.y, 0.0, 1.0), w0);
  // in the Color view, close-up detail is added to the Viking colors as a warm-tinted brightness change""")
rep("""  if (mode == 0) base = vec3(alb) * 1.15;
  else if (mode == 1) base = ramp((vH - ${HMIN.toFixed(1)}) / ${(HMAX - HMIN).toFixed(1)});
  else base = ramp((vH - ${HMIN.toFixed(1)}) / ${(HMAX - HMIN).toFixed(1)}) * (0.35 + 1.05 * alb);""",
"""  if (mode == 0) base = clamp(colr * 1.08 + (alb - ir0) * vec3(0.95, 0.78, 0.66) * 0.85 * dw, 0.0, 1.0);
  else if (mode == 1) base = vec3(alb) * 1.1;
  else if (mode == 2) base = ramp((vH - ${HMIN.toFixed(1)}) / ${(HMAX - HMIN).toFixed(1)});
  else base = ramp((vH - ${HMIN.toFixed(1)}) / ${(HMAX - HMIN).toFixed(1)}) * (0.3 + 1.0 * alb);""")
rep("const uniforms = {\n  albedoTex: { value: null },", "const uniforms = {\n  albedoTex: { value: null }, irTex: { value: null },")

# ---------------------------------------------------------------- loading: two maps, the active one upgraded to 8k
i0 = s.index("  setLoad(0.02, 'Loading surface map');"); i1 = s.index("  setLoad(0.33, 'Loading elevation (LOLA)');")
s = s[:i0] + """  setLoad(0.02, 'Loading the color map');
  const mkTex = bm => { const t = new THREE.Texture(bm); t.flipY = false; t.wrapS = THREE.RepeatWrapping; t.colorSpace = THREE.NoColorSpace;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy(); t.needsUpdate = true; return t; };
  const cBlob = await fetchBlob('data/mars_color_4k.jpg', f => setLoad(0.02 + f * 0.18));
  maps.color.t4 = mkTex(await bitmap(cBlob));
  setLoad(0.2, 'Loading the THEMIS infrared map');
  const irBlob = await fetchBlob('data/mars_ir_4k.jpg', f => setLoad(0.2 + f * 0.13)); detail.albBlob = irBlob;
  maps.ir.t4 = mkTex(await bitmap(irBlob));
  maps.mk = mkTex; useMaps();

""" + s[i1:]
rep("setLoad(0.33, 'Loading elevation (LOLA)');", "setLoad(0.33, 'Loading elevation (MOLA)');")
rep("const hBlob = await fetchBlob('data/moon_height.png'", "const hBlob = await fetchBlob('data/mars_height.png'")
i0 = s.index("  if (maxTex >= 8192) { // sharper surface map for zooming in"); i1 = s.index("\n}\n", i0)
s = s[:i0] + "  upgradeMaps();" + s[i1:]
rep("async function loadAll() {", """const maps = { color: { t4: null, t8: null, loading: false, file: 'data/mars_color_8k.jpg' },
               ir: { t4: null, t8: null, loading: false, file: 'data/mars_ir_8k.jpg' }, mk: null };
function useMaps() {
  uniforms.albedoTex.value = maps.color.t8 || maps.color.t4;
  uniforms.irTex.value = maps.ir.t8 || maps.ir.t4; dirty = true;
}
// Only the map being looked at is loaded at full 8k size, to spare the graphics memory of smaller computers.
async function upgradeMaps() {
  if (renderer.capabilities.maxTextureSize < 8192 || !maps.mk) return;
  const want = uniforms.mode.value === 0 ? 'color' : 'ir', other = want === 'color' ? 'ir' : 'color';
  if (maps[other].t8 && want === 'color') { maps[other].t8.dispose(); maps[other].t8 = null; useMaps(); }
  const m = maps[want]; if (m.t8 || m.loading) return;
  m.loading = true;
  try { m.t8 = maps.mk(await bitmap(await fetchBlob(m.file))); useMaps(); } catch (e) { console.warn('8k map not loaded', e); }
  m.loading = false;
}
async function loadAll() {""")

# ---------------------------------------------------------------- features
rep("""  for (const [name, lat, lon, diam, kind, id] of fj.features) items.push({ name, lat, lon, diam: diam || 1, kind, id });
  const byName = new Map(items.map(it => [it.name.toLowerCase(), it]));
  for (const [name, lat, lon, desc] of fj.lunar100) {
    const m = byName.get(name.toLowerCase());
    if (m) { m.desc = desc; m.l100 = true; }               // same feature as an IAU name: keep one label
    else items.push({ name, lat, lon, diam: 0, kind: 'l100', desc });
  }""",
"""  for (const [name, lat, lon, diam, kind, id, type, origin] of fj.features) items.push({ name, lat, lon, diam: diam || 1, kind, id, type, origin });""")
rep("""const KIND_TEXT = {""", """const TYPE_TEXT = { Mons: 'Volcano or mountain (mons)', Montes: 'Mountain range (montes)', Tholus: 'Small volcano (tholus)', Tholi: 'Small volcanoes (tholi)',
  Patera: 'Volcanic crater (patera)', Paterae: 'Volcanic craters (paterae)', Vallis: 'Valley (vallis)', Valles: 'Valley system (valles)',
  Chasma: 'Canyon (chasma)', Chasmata: 'Canyons (chasmata)', Fossa: 'Trough (fossa)', Fossae: 'Troughs (fossae)', Labyrinthus: 'Canyon maze (labyrinthus)',
  Catena: 'Crater chain (catena)', Catenae: 'Crater chains (catenae)', Sulci: 'Grooved terrain (sulci)', Sulcus: 'Grooved terrain (sulcus)',
  Cavus: 'Hollow (cavus)', Cavi: 'Hollows (cavi)', Planitia: 'Low plain (planitia)', Planum: 'High plain (planum)', Plana: 'High plains (plana)',
  Terra: 'Highland region (terra)', Terrae: 'Highland regions (terrae)', Vastitas: 'Lowland plains (vastitas)', Regio: 'Region (regio)',
  Crater: 'Crater', Craters: 'Craters', 'Albedo Feature': 'Classical albedo feature', Mensa: 'Mesa (mensa)', Mensae: 'Mesas (mensae)',
  Chaos: 'Chaotic terrain (chaos)', Colles: 'Hills (colles)', Collis: 'Hill (collis)', Dorsum: 'Ridge (dorsum)', Dorsa: 'Ridges (dorsa)',
  Rupes: 'Cliff (rupes)', Rupēs: 'Cliffs (rupes)', Scopulus: 'Lobate cliff (scopulus)', Scopuli: 'Lobate cliffs (scopuli)', Undae: 'Dune field (undae)',
  Unda: 'Dune field (unda)', Labes: 'Landslide (labes)', Lingula: 'Tongue-shaped plateau (lingula)', Palus: 'Plain (palus)',
  Serpens: 'Sinuous feature (serpens)', 'Landing site name': 'Landing site name', Fluctus: 'Lava flow field (fluctus)', Fluctūs: 'Lava flow fields (fluctus)',
  Tessera: 'Tile-like terrain (tessera)', Lacus: 'Lake-like plain (lacus)', Lacūs: 'Lake-like plains (lacus)' };
const KIND_TEXT = {""")
rep("""function kindText(it) {
  if (it.kind === 'det') return 'Close-up region';
  if (it.kind === 'land') return 'Landing site';
  if (it.kind === 'l100') return 'Lunar 100 feature';
  if (it.l100) return (KIND_TEXT[it.name.split(' ')[0]] || 'Crater') + ' \\u00B7 Lunar 100';
  if (it.kind === 'satellite') return 'Satellite crater';
  return KIND_TEXT[it.name.split(' ')[0]] || 'Crater';
}""", """function kindText(it) {
  if (it.kind === 'det') return 'Close-up region';
  if (it.kind === 'land') return 'Lander or rover';
  return TYPE_TEXT[it.type] || it.type || 'Named feature';
}""")
rep("""  if (it.desc) html += `<div class="desc">${esc(it.desc)}</div>`;""",
    """  if (it.desc) html += `<div class="desc">${esc(it.desc)}</div>`;
  if (it.origin) html += `<div class="desc" style="color:var(--muted);font-size:12px">Name: ${esc(it.origin)}</div>`;""")
rep("""  if (it.diam > 1 && it.kind !== 'l100' && it.kind !== 'land') html += `<tr><td>${/^(Rima|Rimae|Vallis|Valles|Catena|Dorsum|Dorsa|Rupes|Montes)\\b/.test(it.name) ? 'Length' : 'Diameter'}</td>""",
    """  if (it.diam > 1 && it.kind !== 'land') html += `<tr><td>${/^(Vallis|Valles|Chasma|Chasmata|Fossa|Fossae|Catena|Catenae|Dorsum|Dorsa|Rupes|Montes|Sulci|Scopulus|Labes)$/.test(it.type) ? 'Length' : 'Diameter'}</td>""")
rep("""  if (it.diam > 1 && it.kind !== 'l100' && it.kind !== 'land') html += `<tr><td>Angular size from Earth</td><td>${(it.diam / 384400 * 206265).toFixed(0)}&Prime;</td></tr>`;""",
    """  if (it.diam > 1 && it.kind !== 'land') html += `<tr><td>Size seen from Earth at closest approach</td><td>${(it.diam / 56e6 * 206265).toFixed(2)}&Prime;</td></tr>`;""")

# ---------------------------------------------------------------- label rules
rep("""const layer = { mare: true, crater: true, mount: true, other: true, satellite: true, l100: true, land: true, det: true };""",
    """const layer = { land: true, volcano: true, canyon: true, region: true, crater: true, other: true, albedo: false, det: true };""")
rep("""  const satOK = alt < 0.5;
""", "")
rep("""    const viaL100 = it.l100 && layer.l100;
    if (!layer[it.kind] && !viaL100) continue;""", """    if (!layer[it.kind]) continue;""")
rep("""    else if (it.kind === 'l100') { if (dist > 3.2) continue; pri = 5e5; }
    else if (it.kind === 'det') { if (dist > 3.4 || px > H * 0.4) continue; pri = 8e5; }
    else if (it.kind === 'mare') { if (px < 40) continue; pri = 9e5 + Math.min(px, 2000); }
    else if (it.kind === 'satellite') { if (!satOK || px < 30 * zf) continue; pri = px * 0.5; }
    else if (viaL100 && dist < 3.2) pri = 5e5 + px;
    else { if (!layer[it.kind] || px < (it.kind === 'crater' ? 26 : it.kind === 'mount' ? 34 : 55) * zf) continue; pri = it.kind === 'crater' ? px : px * 0.6; }""",
"""    else if (it.kind === 'det') { if (dist > 3.4 || px > H * 0.4) continue; pri = 8e5; }
    else if (it.kind === 'region') { if (px < 60 * zf || px > W * 3) continue; pri = 9e5 + Math.min(px, 2000); }
    else if (it.kind === 'albedo') { if (px < 60 * zf) continue; pri = 8.5e5 + Math.min(px, 2000); }
    else if (it.kind === 'volcano') { if (px < 22 * zf) continue; pri = 8.8e5 + px; }
    else { if (px < (it.kind === 'crater' ? 26 : it.kind === 'canyon' ? 45 : 40) * zf) continue; pri = it.kind === 'canyon' ? px * 1.2 : it.kind === 'crater' ? px : px * 0.7; }""")
rep("""    const fs = c.it.kind === 'mare' ? 15 : c.it.kind === 'satellite' ? 10.5 : 12;
    const w = c.it.name.length * fs * (c.it.kind === 'mare' ? 0.6 : 0.56) + (c.it.kind === 'l100' || c.it.kind === 'land' || c.it.kind === 'det' ? 14 : 4), h = fs + 4;
    const point = c.it.kind === 'l100' || c.it.kind === 'land' || c.it.kind === 'det';""",
"""    const fs = c.it.kind === 'region' ? 15 : c.it.kind === 'albedo' ? 14 : 12;
    const w = c.it.name.length * fs * (c.it.kind === 'region' || c.it.kind === 'albedo' ? 0.6 : 0.56) + (c.it.kind === 'land' || c.it.kind === 'det' ? 14 : 4), h = fs + 4;
    const point = c.it.kind === 'land' || c.it.kind === 'det';""")
rep("""el.className = 'lbl k-' + c.it.kind + (c.it.l100 && layer.l100 ? ' l100' : ''); }""", """el.className = 'lbl k-' + c.it.kind; }""")
rep("""    const rank = it => (it.lc === q ? 1e7 : 0) + (it.kind === 'land' || it.kind === 'l100' || it.l100 || it.kind === 'mare' ? 1e5 : 0) + (it.kind === 'satellite' ? -1e4 : 0) + it.diam;""",
    """    const rank = it => (it.lc === q ? 1e7 : 0) + (it.kind === 'land' || it.kind === 'det' || it.kind === 'volcano' || it.kind === 'region' ? 1e5 : 0) + (it.kind === 'albedo' ? -1e4 : 0) + it.diam;""")
rep("""function pick(i) { const it = sList[i]; if (!it) return; if (!layer[it.kind] && !(it.l100 && layer.l100)) {""",
    """function pick(i) { const it = sList[i]; if (!it) return; if (!layer[it.kind]) {""")
rep("""    if (it.kind === 'l100' || it.kind === 'land' || it.diam < 2) continue;
    if (!layer[it.kind] && it.kind !== 'crater') continue;""",
    """    if (it.kind === 'land' || it.kind === 'det' || it.kind === 'albedo' || it.diam < 2) continue;""")

# ---------------------------------------------------------------- map mode switch
rep("""seg('mode', v => { uniforms.mode.value = v; $('legend').style.display = v ? 'block' : 'none'; });""",
"""const MODE_NOTE = ['Viking orbiter color mosaic.', 'THEMIS daytime infrared: warm sunlit slopes look bright, so landforms stand out.',
  'MOLA laser altimeter elevation.', 'Elevation colors on top of the infrared map.'];
seg('mode', v => { uniforms.mode.value = v; $('legend').style.display = v >= 2 ? 'block' : 'none'; $('modeNote').textContent = MODE_NOTE[v]; upgradeMaps(); });""")

# ---------------------------------------------------------------- live close-ups and region text
rep("""    if (info.live_tiles) $('detNote').textContent = 'Sharp LROC images (about 100 m per pixel) fade in as you zoom into these regions. Live close-ups from NASA Moon Trek also load anywhere you zoom in.';""",
    """    if (info.live_tiles) $('detNote').textContent = 'Sharp THEMIS infrared images (about 100 m per pixel) fade in as you zoom into these regions. Live close-ups from NASA Mars Trek also load anywhere you zoom in.';""")
rep("""    <div class="desc">A sharp LROC Wide Angle Camera image of this area fades in as you zoom in. Keep zooming to see small craters, rilles and boulder-strewn slopes.</div>""",
    """    <div class="desc">A sharp THEMIS daytime infrared image of this area fades in as you zoom in. In the Color view its detail is laid over the Viking colors.</div>""")
rep("""name: 'Live LROC close-up'""", """name: 'Live THEMIS close-up'""")
rep("""  const needPpd = Math.min(303, innerHeight""", """  const needPpd = Math.min(593, innerHeight""")

# ---------------------------------------------------------------- Mars: lower relief exaggeration by default
rep("""<span class="val" id="exV">4&times;</span>""", """<span class="val" id="exV">3&times;</span>""")
rep("""<input type="range" id="ex" min="0" max="25" step="0.5" value="4">""", """<input type="range" id="ex" min="0" max="15" step="0.5" value="3">""")
rep("""  exag: { value: 4 },""", """  exag: { value: 3 },""")
rep("""controls.minDistance = 1.03 + 4 * 0.0065;""", """controls.minDistance = 1.03 + 3 * 0.0065;""")

(ROOT / "mars" / "index.html").write_text(s)
print("mars/index.html written")
