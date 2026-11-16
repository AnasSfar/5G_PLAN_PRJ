# C-RAN project: Madrid scenario

Team project for the MASTEAM *Wireless & Radio Communication* course (EETAC, UPC, 2026).
We design a Cloud Radio Access Network: choose how many BBU pools to build and where, so that every
RRH stays within the maximum fronthaul delay while load and traffic stay balanced. The method
follows the reference thesis in `docs/`.

The project has two phases:
1. **Scenario and delay:** build the real RRH dataset (done, week 1), then place K BBU pools and assign RRHs within the delay limit.
2. **Load balancing:** rebalance the RRH-to-pool assignment using 24 h traffic profiles (residential, office, mixed), by traffic load and by number of RRHs, then compare with the delay-only assignment.
   Instructions: `docs/Project review_phase2_RRH_balancing_and_load_balancing.pdf`.

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
python/        code: config.py + numbered steps 01..06
data/          rrh_master.csv, spot check, raw.zip (raw API answers, never edited)
json/          rrh_master.json: the master dataset, source of truth for the simulator
maps/          rrh_map.html, density.png
docs/          phase 1 and phase 2 instructions (PDF + transcripts), reference thesis
archive/       earlier Barcelona scenario, kept for reference only
week1.txt      what was done in week 1 and why (one file per week)
report.txt     running draft of the final report```

## Conventions

- Raw data in `data/raw/` is never edited: any change of rule means re-running step 03.
- One `weekN.txt` per week explains what was done and why, and `report.txt` grows a section each week.
- Infoantenas is the source of truth. OpenCelliD is only used for spot checks.
