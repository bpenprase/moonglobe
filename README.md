# Lunar Globe Explorer

An interactive 3D globe of the Moon for Astronomy 150 (Models of Time and Space) at Soka University of America.
Students can rotate and zoom the globe, read latitude, longitude and elevation anywhere on the surface,
switch between the surface map and a color elevation map, light the Moon from any Sun angle to see phases and
relief, and turn feature names on or off.

## What is in this folder

| Path | What it is |
|---|---|
| `index.html` | The whole app (HTML, CSS and JavaScript in one file). It loads three.js from the jsDelivr CDN. |
| `data/moon_albedo_4k.jpg` | Greyscale LROC WAC surface map, 4096 x 2048 (loads first). |
| `data/moon_albedo_8k.jpg` | Greyscale LROC WAC surface map, 8192 x 4096 (loads second, about 1.3 km per pixel). |
| `data/moon_height.png` | LOLA elevation, 2880 x 1440, packed into 16 bits: elevation in meters = (red x 256 + green) x 8 - 10000. |
| `data/features.json` | About 9,000 IAU feature names, the Lunar 100 list and 20 landing sites. |
| `tools/prepare_moon_data.py` | The Python script that builds everything in `data/` from the original NASA and IAU files. |

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

## Data credits

- Surface: LRO Camera (LROC) Wide Angle Camera mosaic, NASA/GSFC/Arizona State University, distributed in the NASA Scientific Visualization Studio CGI Moon Kit (Ernie Wright).
- Elevation: LRO Lunar Orbiter Laser Altimeter (LOLA), NASA/GSFC.
- Names: IAU Working Group for Planetary System Nomenclature, Gazetteer of Planetary Nomenclature (USGS Astrogeology).
- Lunar 100: Charles A. Wood, *Sky & Telescope* (April 2004).
- 3D graphics: three.js (MIT license).

NASA imagery and data are in the public domain. Please keep the credits above when you reuse the files.
