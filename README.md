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
| `index.html` | The whole app (HTML, CSS and JavaScript in one file). It loads three.js from the jsDelivr CDN. |
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
3. After a minute the globe is live at `https://<your-user-name>.github.io/moonglobe/`.

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

## Data credits

- Surface: LRO Camera (LROC) Wide Angle Camera mosaic, NASA/GSFC/Arizona State University, distributed in the NASA Scientific Visualization Studio CGI Moon Kit (Ernie Wright).
- Elevation: LRO Lunar Orbiter Laser Altimeter (LOLA), NASA/GSFC.
- Close-ups: LROC Wide Angle Camera global mosaic (303 pixels per degree), NASA/GSFC/Arizona State University, served by NASA Moon Trek (https://trek.nasa.gov/moon/).
- Names: IAU Working Group for Planetary System Nomenclature, Gazetteer of Planetary Nomenclature (USGS Astrogeology).
- Lunar 100: Charles A. Wood, *Sky & Telescope* (April 2004).
- 3D graphics: three.js (MIT license).

NASA imagery and data are in the public domain. Please keep the credits above when you reuse the files.
