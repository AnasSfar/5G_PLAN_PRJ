# How to run the project

Python 3.11 or newer. All commands are run from the `python/` folder.

## 1. Install

```bash
pip install -r requirements.txt
```

`contextily` (last line of `requirements.txt`) is only needed for the static basemap maps of step 12.

## 2. Phase 1 simulations (no internet needed)

The simulator reads `json/rrh_master.json`, which is already included, so you can start here.

```bash
cd python
python 07_scenario.py      # 200 RRHs, traffic patterns, 25 candidate pools
python 08_min_delay.py     # Minimise Delay algorithm and choice of K
python 09_figures.py       # figures fig01..fig12
python 10_robustness.py    # synthetic RRHs, full dataset, checks (fig13, fig14)
python 11_maps.py          # interactive maps map01..map05
```

The whole chain takes about 10 seconds. Results go to `phase1/`:

| Folder | Content |
|---|---|
| `phase1/data/` | `assignment_K19.csv` (pools per RRH), `pool_categories_K19.csv` (RRHs per pool and category), `k_analysis.csv`, `robustness.csv`, `results.json` |
| `phase1/figures/` | all PNG figures of the report |
| `phase1/maps/` | interactive maps: open the `.html` files in Chrome, Firefox or Edge |

Optional, needs internet: static maps over a real basemap, for the report or the poster.

```bash
python 12_basemap_figures.py                    # light grey basemap
python 12_basemap_figures.py --basemap osm      # or: satellite
```

## 2b. Phase 2 simulations (load balancing, no internet needed)

Run after the phase-1 steps 07 and 08 (it reads `phase1/data/scenario.json` and `k_analysis.csv`):

```bash
cd python
python 13_traffic.py       # 24 h profiles, traffic of every RRH, network load, balancing hour
python 14_balancing.py     # only distance vs traffic balancing vs RRH balancing, K = 19 / 8 / 25
python 15_p2_figures.py    # figures fig01..fig14
```

Results go to `phase2/data/` (CSV and `summary.json`) and `phase2/figures/`. Parameters are in the
phase-2 block at the end of `python/config.py` (`BALANCE_HOUR`, `K_CASES`, `PEAK_4G_MBPS`, `PEAK_5G_MBPS`,
`PROFILES`). See `week3.txt` for the decisions and the results.

## 3. Changing the scenario

Every parameter is in the phase-1 block at the end of `python/config.py`. Edit it, then run steps 07 to 11 again.

| Parameter | Default | Meaning |
|---|---|---|
| `N_RRH_REAL` | 200 | real RRHs drawn from the 2,085 sites (`None` = all) |
| `N_SYNTHETIC` | 0 | extra synthetic RRHs placed at random |
| `TRAFFIC_MODE` | `"geo"` | `"geo"` (Madrid districts) or `"random"` |
| `TRAFFIC_SHARES` | 50 / 30 / 20 % | mixed / office / residential shares for `"random"` |
| `MAX_RTT_US` | 200 | round-trip delay budget in µs (20 km) |
| `N_POOL_CANDIDATES` | 25 | candidate pool sites |
| `K_ACTIVE` | `"auto"` | number of active pools; `"auto"` picks 19, or give a number |

For a quick test without editing the file: `python 07_scenario.py --n-synth 100 --mode random`, then steps 08 to 11.

## 4. Week 1: rebuilding the dataset (optional)

Only needed if you change the band rules or the merge radius.

```bash
python -c "import zipfile; zipfile.ZipFile('../data/raw.zip').extractall('../data')"
python 03_process.py
python 04_map.py
```

Steps 01, 02 and 05 download data again from Infoantenas and OpenCelliD (see `README.md`).
