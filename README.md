# C-RAN project: Madrid scenario

Team project for the MASTEAM *Wireless & Radio Communication* course (EETAC, UPC, 2026).
We design a Cloud Radio Access Network: choose how many BBU pools to build and where, so that every
RRH stays within the maximum fronthaul delay while load and traffic stay balanced. The method
follows the reference thesis in `docs/`.

The project has three phases:
1. **Scenario and delay:** build the real RRH dataset (done, week 1), then place K BBU pools and assign RRHs within the delay limit (done, week 2: 19 pools, see `week2.txt`).
2. **Load balancing:** rebalance the RRH-to-pool assignment using 24 h traffic profiles (residential, office, mixed), by traffic load and by number of RRHs, then compare with the delay-only assignment (done, week 3, see `week3.txt`).
   Instructions: `docs/Project review_phase2_RRH_balancing_and_load_balancing.pdf`.
3. **5G link budget:** an Excel 5G NR link budget with every parameter explained, `phase3/5G_link_budget.xlsx` (week 4, see `week4.txt`; due 30 November 2026).
   Instructions: `phase3/5G_link_budget.pdf`.

Scenario: a 30 × 30 km box over Madrid, centred on the Santiago Bernabéu stadium (40.4531 N, 3.6883 W).
The real base stations come from Infoantenas, the official Spanish government portal.

Read [context.md](context.md) first: it explains the project, the decisions taken so far and what comes next.

## Quick start

```bash
# 1. Install the dependencies (Python 3.11+)
pip install -r requirements.txt

# 2. Unzip the raw data (creates data/raw/; not stored in git because it has ~8,700 files)
python -c "import zipfile; zipfile.ZipFile('data/raw.zip').extractall('data')"

# 3. Rebuild the dataset and the map from the raw files (no internet needed)
cd python
python 03_process.py
python 04_map.py
```

Then open `maps/rrh_map.html` (RRH map) in a browser.

## Pipeline

Run the scripts from the `python/` folder, in order. All settings (area, tile size, merge radius,
band rules) are in `python/config.py`.

| Script | What it does | Output |
|---|---|---|
| `01_scrape_tiles.py` | Queries the Infoantenas GeoJSON API for 225 tiles of 2 × 2 km | `data/raw/tiles/` |
| `02_scrape_details.py` | Downloads the detail page (frequency bands) of each site | `data/raw/details/` |
| `03_process.py` | Labels sites 4G / 5G / ambiguous from their bands and merges towers within 50 m into one RRH | `json/rrh_master.json`, `data/rrh_master.csv` |
| `04_map.py` | Folium map and density figure | `maps/rrh_map.html`, `maps/density.png` |
| `05_spotcheck.py` | Spot check against OpenCelliD in 3 small areas | `data/spotcheck_opencellid.csv` |
| `06_checks.py` | Cap test, rule sensitivity, raw-data manifest | `data/raw/manifest.json` |
| `07_scenario.py` | Phase 1: 200 real RRHs + synthetic RRHs, traffic pattern, 25 candidate pools (farthest-first) | `phase1/data/scenario.json` |
| `08_min_delay.py` | Phase 1: Minimise Delay algorithm, pool reduction, choice of K, options and categories | `phase1/data/*.csv`, `results.json` |
| `09_figures.py` | Phase 1: figures (plain x/y km axes) | `phase1/figures/fig*.png` |
| `10_robustness.py` | Phase 1: synthetic RRHs, full dataset, consistency checks | `phase1/data/robustness.csv`, fig13-14 |
| `11_maps.py` | Phase 1: the map figures on a real street map, interactive. Open the HTML in a browser (Chrome / Firefox / Edge): Leaflet and the municipal boundaries are embedded, only the background tiles (Esri) need internet | `phase1/maps/map01..map05*.html` |
| `12_basemap_figures.py` | Phase 1: the map figures as static PNGs over a basemap, **needs internet** and `pip install contextily` | `phase1/figures/map_fig*.png` |
| `13_traffic.py` | Phase 2: 24 h profiles, traffic of every RRH, network load, peak hour | `phase2/data/rrh_traffic.csv`, `traffic.json`, fig01-02 |
| `14_balancing.py` | Phase 2: delay only vs traffic balancing vs RRH-count balancing, for K = 19 / 8 / 25 | `phase2/data/assignment_*.csv`, `pools_*.csv`, `summary.json` |
| `15_p2_figures.py` | Phase 2: figures fig03..fig10 | `phase2/figures/fig*.png` |

Phase 1 (about 10 s, no internet): `python 07_scenario.py && python 08_min_delay.py && python 09_figures.py && python 10_robustness.py && python 11_maps.py`.
Then, with internet, `python 12_basemap_figures.py` (options `--basemap grey|osm|satellite`) for static map PNGs.
Phase-1 settings (number of RRHs, synthetic RRHs, traffic shares, delay budget, number of candidate pools, K)
are in the phase-1 block of `python/config.py`.

Phase 2 (about 5 s, after 07 and 08): `python 13_traffic.py && python 14_balancing.py && python 15_p2_figures.py`.
Phase-2 settings (profiles, traffic per technology, balancing hour, K cases) are in the phase-2 block at the end of `python/config.py`.

Steps 01 and 02 only need to be run again to re-scrape (they resume where they stopped).
Unzipping `data/raw.zip` is enough for everything else.

**OpenCelliD key (step 05 only).** Each person uses their own key, stored in an environment variable
and never in a file:

```bash
setx OPENCELLID_KEY "your-key"        # Windows, then reopen the terminal
export OPENCELLID_KEY="your-key"      # macOS / Linux
```

## Folder layout

```
python/        code: config.py + numbered steps 01..15 (p1_lib.py, p2_lib.py, p2_style.py shared helpers)
data/          rrh_master.csv, spot check, raw.zip (raw API answers, never edited),
               municipalities_madrid.geojson (IGN municipal boundaries via es-atlas, MIT; offline map layer)
json/          rrh_master.json: the master dataset, source of truth for the simulator
maps/          rrh_map.html, density.png
phase1/        phase-1 outputs: data/ (CSV, JSON), figures/ (PNG), maps/ (interactive map)
phase2/        phase-2 outputs: data/ (CSV, JSON), figures/ (PNG)
phase3/        phase-3 instructions and the Excel 5G link budget
docs/          phase 1 and phase 2 instructions (PDF + transcripts), reference thesis
reports/       weekly reports (.docx)
archive/       earlier Barcelona scenario, kept for reference only
week1.txt      what was done in week 1 and why (one file per week; week2 = phase 1, week3 = phase 2, week4 = phase 3)
report.txt     running draft of the final report
```

## Conventions

- Raw data in `data/raw/` is never edited: any change of rule means re-running step 03.
- One `weekN.txt` per week explains what was done and why, and `report.txt` grows a section each week.
- Infoantenas is the source of truth. OpenCelliD is only used for spot checks.
