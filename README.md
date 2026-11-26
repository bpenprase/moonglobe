# Exploring Space: Interactive Apps for Models of Time and Space

A suite of browser apps for Astronomy 150, "Models of Time and Space," taught by Bryan Penprase at Soka University
of America. The course is based on the book *Models of Time and Space from Astrophysics and World Cultures* (Springer).

| Address | App |
|---|---|
| https://bpenprase.github.io/moonglobe/ | The landing page (`index.html`, images in `assets/`) |
| https://bpenprase.github.io/moonglobe/sky/ | Celestial Sphere Explorer (`sky/`) |
| https://bpenprase.github.io/moonglobe/horizon/ | Horizon Sky Explorer (`horizon/`, using the data in `sky/data/`) |
| https://bpenprase.github.io/moonglobe/blackhole/ | Galactic Center Black Hole viewer (`blackhole/`) |
| https://bpenprase.github.io/moonglobe/hudf/ | Hubble Ultra Deep Field Explorer (`hudf/`) |
| https://bpenprase.github.io/moonglobe/moon/ | Lunar Globe Explorer (`moon/`, with its data in `data/` and `tools/`) |
| https://bpenprase.github.io/moonglobe/mars/ | Mars Globe Explorer (`mars/`) |

The Moon globe used to live at the site's root address. Old links to it now open the landing page, one click away.

## Horizon Sky Explorer (the `horizon/` folder)

The celestial sphere seen from its center by an observer standing on a flat disk of Earth. It uses the Celestial
Sphere Explorer's data (stars, figures, boundaries, Flamsteed's plates, Messier objects and galaxies) and turns the
sphere for the observer's latitude and the local sidereal time.

- **Observer**: latitude and longitude sliders with preset places (the Soka campus, Stonehenge, Chaco Canyon, Giza, Mauna Kea,
  the Equator, the poles and others), and buttons to face N, E, S, W or look straight up. The default view faces south.
- **Date and time**: a time bar at the bottom of the screen with Play, Run backward and a speed menu (real time up to one
  day per second). "1 day/s" keeps the hour fixed, so the Sun drifts along the ecliptic and the Moon and planets wander
  among the stars. The panel adds a date box, a time-of-day slider, and a dial where the Sun can be dragged along the
  ecliptic to set the date; the Moon and planets show as dots on the dial.
- **Sidereal days**: speeds of 1, 10 or 60 sidereal days (23 h 56 m) per second. Each step is one turn of the sky, so
  the stars hold still while the Sun, Moon and planets move through the constellations. Choosing one turns off daylight
  and turns on planet trails, which show retrograde loops such as Mars in Leo in early 2027.
- **Moon and planets**: the Moon is a small globe with the real lunar map, lit by the Sun so its phase is right, and
  corrected for parallax from the observer's spot. The seven planets show with their colors and brightness. Their cards
  give phase, distance, magnitude, angle from the Sun, and rising and setting times. Positions come from
  `horizon/ephem.js` (Paul Schlyter's orbital formulas), which agree with astropy to within 2 arcminutes for the planets
  and about 5 for the Moon.
- **Measuring**: the horizon carries N, E, S, W labels and an azimuth scale. Clicking the sky marks a point and shows its
  altitude, azimuth, hour angle and rising, highest and setting times. "Show altitude scale" draws a graduated arc from
  the horizon up to the mark.
- **Daylight and the ground**: the sky brightens through twilight into day, and the ground can be solid, see-through or
  hidden. Looking down shows a compass rose at the observer's feet and the encircling ocean at the edge of the disk.
- Times are local mean solar time at the observer's longitude. The sphere is precessed from J2000 to the date shown.
  Refraction is not included.

## Galactic Center Black Hole viewer (the `blackhole/` folder)

The Keck/UCLA Galactic Center Group's orbit movie (`gc_orbits.mp4`, 1995.5 to 2025.3) with the positions of 19 stars
measured in every year step, so students can identify stars and measure their motions and orbits in arcseconds.

- **Movie controls**: play, pause, stop, loop, steps of 0.1 year, slower speeds and a year slider. Drag to pan, and
  scroll or use the + and − buttons to zoom.
- **Identify and trace**: clicking a star names it and traces its path up to the year shown, with a dot for each 0.1 year
  and labeled year marks. Several stars can be traced at once.
- **Motion between two dates**: "Mark start" and "Mark end" give the distance moved in arcseconds, the time elapsed and
  the speed across the sky (km/s at an adjustable distance, 8.0 kpc by default).
- **Orbit fit**: fits an ellipse or a circle to the traced points and reports how much of the curve the points cover.
  "Teacher view" shows the fitted axes and the orbit model's period, eccentricity and true semi-major axis.
- **Ruler**: measures between two clicks in arcseconds and snaps to traced points, fitted orbits and Sgr A*. Each line is
  tagged with its star and what it measures. "Save measurements (CSV)" writes every ruler line and start/end motion,
  with the student's name, for offline work with Kepler's third law. A small calculator does the same in the page.
- **Scale and orientation**: the movie's 0.1 arcsecond bar is 120 pixels, so 1 arcsec = 1200 movie pixels. North is up
  and east is to the left. Positions are offsets from Sgr A* (the white star symbol at pixel 989.1, 539.1).
- **How the positions were measured**: `blackhole/tools/track_stars.py` finds each star in each frame, links the
  detections from year to year, and fits a Kepler orbit with Sgr A* at the focus to each star. The fits match the movie
  to under 1 pixel for most stars (about 3 pixels for S0-2), and give S0-2 a period of 16.1 years and eccentricity
  0.888. `blackhole/tools/build_page.py` puts the results (`tools/stars.json`) into `index.html`. Edit
  `tools/page_template.html`, not `index.html`, then rebuild.
- **A note on the mass**: with the movie's scale bar, the best-measured orbits imply about 6 million solar masses at
  8 kpc, more than the published value of about 4 million. The orbits seen on the sky are also tilted, so the ellipse
  measured on the screen is smaller than the true orbit (for S0-2, 0.089 arcsec against 0.139 arcsec).

## Hubble Ultra Deep Field Explorer (the `hudf/` folder)

The 2004 Hubble Ultra Deep Field press image (ESA/Hubble heic0406a, 6200 x 6200 pixels at 0.030 arcsec per pixel,
CC BY 4.0) as zoomable tiles, with a catalog overlay.

- **Catalog**: 8,724 objects from the UVUDF catalog (Rafelski et al. 2015) with magnitudes in 11 filters and photometric
  redshifts, joined by position and brightness to the MUSE DR2 spectroscopic redshifts, stellar masses and star-formation
  rates (Bacon et al. 2023). 1,675 have spectroscopic redshifts. Outlines are colored by redshift; dashed outlines are
  photometric. Hover for a summary, click for a card with lookback time, age of the universe, size in kpc and a plot of
  brightness against wavelength. Filters by kind of redshift and brightness. Unchecking "All redshifts" gives "Show galaxies with redshifts between [min] and [max]", with quick ranges and a bar chart that can be dragged across to pick a range.
- **Coordinates**: the press image has none, so `hudf/tools/hudf_wcs.py` matches about 3,800 detected galaxies to the
  catalog and fits a polynomial solution (median error 0.37 px, about 0.01 arcsec). Every pixel then has an RA and Dec.
- **Marking**: Mark mode numbers clicked galaxies and records pixel position, RA, Dec, catalog number and redshift. Marks
  can be named, annotated, kept in the browser and saved as a CSV file.
- **Class galaxy list**: upload a CSV or Excel file, or paste a list, with a student name and a galaxy on each row
  (UVUDF number, MUSE or Coe number, RA and Dec, or a J-name). Matching is forgiving: extra words such as "galaxy" or
  "#" are ignored, a bare number is taken as a UVUDF number, and a name and galaxy typed on one line are split. "Show student names on the image" circles each galaxy and writes the
  names beside it, grouping students who share a galaxy. Rows that do not match are flagged. The list is kept in the
  browser. Excel files are read with SheetJS, loaded only when one is uploaded.
- The app opens with just the image: the catalog overlay starts off and "All redshifts" is checked. Hovering and clicking
  still identify galaxies with the overlay off.
- **Measuring**: Measure mode gives the separation of two points in pixels and arcseconds, and in kiloparsecs at the
  redshift of the galaxy the measurement starts on. Distances use a flat universe with H0 = 67.7 and Omega_m = 0.31.

To rebuild: run the **Fetch HUDF sources** workflow (it fills the `hudf-sources` branch), copy the image and catalog
files into a folder, then run `python3 hudf/tools/hudf_wcs.py FOLDER` and `python3 hudf/tools/build_hudf.py FOLDER`
(the UVUDF FITS catalog is saved there as `uvudf_cat.fits`).

# Lunar Globe Explorer

An interactive 3D globe of the Moon for Astronomy 150 (Models of Time and Space) at Soka University of America.
Students can rotate and zoom the globe, read latitude, longitude and elevation anywhere on the surface,
switch between the surface map and a color elevation map, light the Moon from any Sun angle to see phases and
relief, and turn feature names on or off.

## Getting around

- **Rotate**: drag the globe. **Zoom**: scroll, pinch, the **+** and **−** buttons at the lower right (hold a button
  to keep zooming), or the + and − keys. The circle button (or the 0 key) shows the whole Moon again.
  The number between the buttons is the height of your viewpoint above the surface.
- **Labels** follow the zoom: from far away only the maria and large craters are named; as you come closer,
  smaller craters, mountains, rilles and finally the lettered satellite craters (Copernicus A, B...) and the small
  names used by the Apollo crews appear. **Label density** (Fewer / Normal / More) changes how crowded this gets.
- **Click** the surface for latitude, longitude and elevation, or a label for details.

## What is in this folder

| Path | What it is |
|---|---|
| `moon/index.html` | The whole app (HTML, CSS and JavaScript in one file). It loads three.js from the jsDelivr CDN and its data from `data/`. |
| `data/moon_albedo_4k.jpg` | Greyscale LROC WAC surface map, 4096 x 2048 (loads first). |
| `data/moon_albedo_8k.jpg` | Greyscale LROC WAC surface map, 8192 x 4096 (loads second, about 1.3 km per pixel). |
| `data/moon_height.png` | LOLA elevation, 2880 x 1440, packed into 16 bits: elevation in meters = (red x 256 + green) x 8 - 10000. |
| `data/features.json` | About 9,000 IAU feature names, the Lunar 100 list and 20 landing sites. |
| `tools/prepare_moon_data.py` | The Python script that builds everything in `data/` from the original NASA and IAU files. |
| `tools/detail_regions.json` | The list of close-up regions. |
| `tools/fetch_detail_tiles.py` | Downloads and stitches the close-up images (run automatically by GitHub). |
| `data/detail/` | The close-up images and their index, `regions.json`. |

## Putting it on GitHub Pages

1. Create a repository (for example `moonglobe`) and upload every file in this folder, keeping the `data` and `tools` folders.
2. In the repository, open **Settings > Pages**, choose **Deploy from a branch**, pick `main` and `/ (root)`, and save.
3. After a minute the site is live at `https://<your-user-name>.github.io/moonglobe/`, with the Moon at `moon/`.

The `.nojekyll` file tells GitHub Pages to serve the files as they are.

To try it on your own computer, run `python3 -m http.server` in this folder and open `http://localhost:8000`.
(Opening `index.html` directly from the disk will not work, because browsers block loading the data files that way.)

## Rebuilding the data

`tools/prepare_moon_data.py` needs Python 3 with `numpy` and `Pillow` (`pip install numpy pillow`).
Put these files in `tools/raw/` and run `python3 prepare_moon_data.py`:

- `lroc_color_poles_8k.jpg` and `ldem_16_uint.tif` from the NASA SVS CGI Moon Kit: https://svs.gsfc.nasa.gov/4720
- `moon_iau_features.csv`: IAU Gazetteer of Planetary Nomenclature, Moon center points (https://planetarynames.wr.usgs.gov/), saved as CSV with the columns Feature_ID, Feature_Name, Diameter, Center_Latitude, Center_Longitude
- `lunar100.csv`: Charles Wood's Lunar 100 with columns name, description, x, y (pixel positions on a 5760 x 2880 map)

## Close-up regions (sharper images)

When you zoom into one of about 30 popular regions (the six Apollo sites, Copernicus, Tycho, Plato, the Alpine
Valley, the Straight Wall and others), a sharper LROC Wide Angle Camera image fades in. These images come
from NASA's Moon Trek tile service at about 100 m per pixel, roughly 13 times sharper than the global map.

- The list of regions is `tools/detail_regions.json`. Each entry has a name, a group, a size in km, and either
  an IAU feature name (`"feature": "Copernicus"`) or a latitude and longitude.
- `tools/fetch_detail_tiles.py` downloads the tiles for each region, stitches them, matches their overall
  brightness to the globe, and saves them in `data/detail/` with an index file `data/detail/regions.json`.
- You do not need to run it yourself. The GitHub Action in `.github/workflows/fetch-detail-tiles.yml` runs it
  automatically on GitHub whenever the region list or the script changes, then saves the new images to the
  repository. You can also start it by hand from the **Actions** tab (choose "Fetch close-up tiles", then "Run workflow").
- Each run writes `tools/detail_report.txt`, which shows how well the tiles lined up with the globe and how each region went.

To add a region, edit `tools/detail_regions.json` on GitHub (click the file, then the pencil icon), add a line such as
`{"name": "Hipparchus", "feature": "Hipparchus", "size_km": 250, "group": "Famous craters"},` and commit.
A few minutes later the new close-up is live.

If Moon Trek allows web pages on other sites to load its tiles (the report says "live tiles ... ALLOWED"),
the globe also loads live close-ups anywhere you zoom in, not just in the listed regions.

## Mars Globe Explorer (the `mars/` folder)

The same globe for Mars, at `https://bpenprase.github.io/moonglobe/mars/` (each globe links to the other).

- **Maps**: Color (Viking orbiter MDIM 2.1 colorized mosaic), Infrared (Mars Odyssey THEMIS daytime infrared, about
  100 m per pixel, with polar gaps filled from MOLA shaded relief), Elevation (MOLA laser altimeter), and Blend.
- **Layers**: landers and rovers (Viking 1 and 2 through Perseverance and Zhurong), volcanoes, canyons and channels,
  plains and highlands, craters, other landforms, and the classical telescope (albedo) names. About 2,000 IAU names in all,
  each with the origin of its name.
- **Close-ups**: 26 regions (landing sites, the Tharsis volcanoes, Valles Marineris, famous craters, Cydonia) with sharp
  THEMIS images, plus live THEMIS close-ups anywhere you zoom in.
- **How it is built**: `mars/tools/prepare_mars_data.py` downloads and processes the NASA and USGS data, and
  `tools/fetch_detail_tiles.py` makes the close-ups. Both run on GitHub through `.github/workflows/build-mars-data.yml`
  whenever the Mars scripts or `mars/tools/detail_regions.json` change. Reports are written to `mars/tools/*_report.txt`.
- **The page** `mars/index.html` is generated from the Moon page by `mars/tools/make_mars_page.py`, so improvements to
  the Moon globe can be carried over with one command: `python3 mars/tools/make_mars_page.py`.

## Celestial Sphere Explorer (the `sky/` folder)

The sky as a sphere, at `https://bpenprase.github.io/moonglobe/sky/`. Look out from the center as from Earth
(**Inside**), or turn it around as an antique celestial globe (**Outside**, mirror-reversed like the real globes).

- **Layers**: star names, constellation figures, IAU constellation boundaries and names, Flamsteed's *Atlas Coelestis*
  (1729), Messier objects, bright galaxies, other showpiece objects, the Milky Way, the RA/Dec grid, the ecliptic and
  the galactic equator. Click any star or object for a card with its data and a link to SIMBAD.
- **Flamsteed's plates**: all 25 constellation plates are placed on the sphere. Each plate was fitted to the
  Hipparcos catalog by matching its engraved star symbols (about 20 to 100 stars per plate, typically within a few
  arcminutes), precessing from the 1690 equinox Flamsteed used to J2000. The engraved coordinate grids are removed, and
  each piece of sky is drawn from one plate, so the figures join up across plate edges. **Engraving** shows the figures
  as light lines on the night sky; **Printed plate** shows them as dark ink on parchment. The images (about 14 MB)
  load the first time the layer is turned on.

| Path | What it is |
|---|---|
| `sky/index.html` | The app. |
| `sky/data/stars.json`, `sky/data/sky.json`, `sky/data/milkyway.jpg` | Stars to magnitude 6.5, names, constellations, deep-sky objects and the Milky Way, built by `sky/tools/prepare_sky_data.py` from d3-celestial (BSD license). |
| `sky/data/flamsteed/` | The 25 plate overlays (`plate_NNN.jpg`: red = engraving, green = mask) and `plates.json`, which ties points of each image to sky positions. |
| `sky/tools/flamsteed_plates.json` | Plate titles, constellations, rough centers and the measured map frames. |
| `sky/tools/flamsteed_fit.py` | Fits each plate's star symbols to the catalog (OpenCV, NumPy, SciPy). |
| `sky/tools/flamsteed_overlay.py` | Removes the grid, assigns sky to plates and writes `sky/data/flamsteed/`. |

The plate photographs come from Wikimedia Commons (RareMaps scans of the 1729 edition, public domain). They are kept on
the `flamsteed-sources` branch, which the **Fetch Flamsteed plates** workflow fills.

## Data credits

- Surface: LRO Camera (LROC) Wide Angle Camera mosaic, NASA/GSFC/Arizona State University, distributed in the NASA Scientific Visualization Studio CGI Moon Kit (Ernie Wright).
- Elevation: LRO Lunar Orbiter Laser Altimeter (LOLA), NASA/GSFC.
- Close-ups: LROC Wide Angle Camera global mosaic (303 pixels per degree), NASA/GSFC/Arizona State University, served by NASA Moon Trek (https://trek.nasa.gov/moon/).
- Names: IAU Working Group for Planetary System Nomenclature, Gazetteer of Planetary Nomenclature (USGS Astrogeology).
- Lunar 100: Charles A. Wood, *Sky & Telescope* (April 2004).
- 3D graphics: three.js (MIT license).

- Sky: star, constellation and deep-sky data from d3-celestial by Olaf Frohn (BSD license), based on Hipparcos, the IAU and the NGC/IC catalogs; plates from John Flamsteed, *Atlas Coelestis* (London, 1729), public domain.
- Mars: Viking MDIM 2.1 color mosaic (USGS / NASA Ames); THEMIS daytime infrared mosaic (NASA/JPL/Arizona State University); MOLA MEGDR topography (NASA/GSFC, PDS Geosciences Node); IAU Mars nomenclature (USGS); all served through NASA Mars Trek or the PDS.

- Galactic Center: orbit movie by the Keck/UCLA Galactic Center Group (UCLA), from W. M. Keck Observatory data.

NASA imagery and data are in the public domain. Please keep the credits above when you reuse the files.
