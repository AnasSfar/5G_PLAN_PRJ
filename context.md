# Project context

Shared context for the team (and for any AI assistant working in this repo). Keep it up to date
when a decision changes or a week is finished.

## Course and assignment

- **Course:** MASTEAM, Wireless & Radio Communication (5G NR air interface, cellular planning), EETAC (UPC), 2026.
- **Professor:** Sílvia Ruiz.
- **Assignment, phase 1 (scenario + delay-based pool placement):** `docs/C-RAN work_instructions_v2.pdf` (text version in `docs/work_instructions_transcript.md`).
- **Assignment, phase 2 (load balancing):** `docs/Project review_phase2_RRH_balancing_and_load_balancing.pdf` (text version in `docs/phase2_transcript.md`).
- **Assignment, phase 3 (5G link budget in Excel, due 30 November 2026):** `phase3/5G_link_budget.pdf`. Build an Excel 5G link budget based on the example calculator https://5g-tools.com/4g-LTE-link-budget-calculator/, and understand and explain every parameter in the calculation.
- **Reference to reproduce:** `docs/Thesis_TiagoM_v20161114_vLC.pdf`, Tiago Monteiro's master thesis on C-RAN in small cells.
- **Team:** 3 students. Any programming language is allowed; we use Python.

## Goal

Design a C-RAN: choose the number K and the positions of the BBU pools, and assign every RRH to a pool, so that:
- the RRH-to-pool distance (fronthaul delay) stays below the maximum acceptable delay;
- load and traffic are balanced between pools.

Every RRH site is a candidate pool site. Pools are picked with a heuristic such as farthest-first
k-center, for several values of K, and the results are compared. The program must also be able to
inject synthetic RRHs (their number is a variable), clearly labelled, to test higher densities.

Extra deliverable (phase 3): a **5G link budget in Excel**.

## Assessment (no final exam)

- Weekly intermediate reports.
- Final report: the weekly reports + the last simulations, analysis and conclusions, with figures comparing the balancing techniques.
- Live demo of the software in class (inputs, variables, algorithms, results).
- Printed poster, presented in class, with questions from other teams and the professor.
- Quality of the work and motivation.

## Scenario and decisions (week 1, done)

- **Area:** Madrid, 30 × 30 km centred on the Santiago Bernabéu stadium (40.4531 N, 3.6883 W).
  Bounding box: west −3.866, south 40.318, east −3.511, north 40.588. It covers a dense core,
  large parks, the airport, suburbs and sparse outskirts. The pipeline was first built on Barcelona;
  that data is kept in `archive/`.
- **Source:** Infoantenas GeoJSON API (`/VCTEL/infoantenasGeoJSON.do`). The API gives only the site
  id, the operator and the position, so a second request per site reads the frequency bands
  (`/VCTEL/detalleEstacion.do`).
- **Technology labels** are inferred from bands:
  4G evidence 800 / 1800 / 2600 MHz; 5G evidence 3.5 GHz and 26 GHz;
  700 / 900 / 2100 MHz alone = "ambiguous" (kept but not counted as 4G or 5G).
- **Merging:** all stations within 50 m become one RRH, and its operator list is kept as an attribute.
- **Core RRHs** (`in_core = true`) are those with 4G or 5G evidence: the simulator uses these.
- **Synthetic RRHs:** none yet (`is_synthetic = false` everywhere). Planned settings: 10 / 25 / 50 % of the real count,
  at least 200 m from any other RRH, seed 42.

### Week 1 numbers

- 225 tiles, 4,789 distinct sites, 0 failures. The cap test shows the API does not truncate its answers.
- 2,304 RRHs after merging: **2,085 core** (1,124 "4G+5G", 951 "4G", 10 "5G") and 219 ambiguous.
- Operators in core RRHs: Movistar 1,432, Orange 1,067, Vodafone 1,012, DS Mobile Networks 241, MásMóvil/Yoigo 24.
- The OpenCelliD spot check in 3 areas of about 1 km² is consistent. Infoantenas stays the reference.

Full reasoning and limits: `week1.txt`.

## Phase 1: minimise delay (week 2, done)

Instructions: professor's review "Project review phase 1 - min delay" (200 us round trip, about 200
RRHs and 19 pools, capacity ignored). Code: `python/07_scenario.py` .. `12_basemap_figures.py` + `p1_lib.py` (11 = interactive maps, 12 = static maps over a basemap, needs internet);
parameters in the phase-1 block of `python/config.py`; outputs in `phase1/`. Full reasoning: `week2.txt`.

- **RRHs:** 200 of the 2,085 core RRHs, simple random sample (seed 42), keeps the real density. Synthetic
  RRHs: variable `N_SYNTHETIC` (0 in the reference), uniform, >= 200 m apart, ids `SYNxxx`.
- **Traffic pattern:** `TRAFFIC_MODE` "geo" (reference; business districts -> office, historic centre,
  airport and isolated sites -> mixed, rest -> residential: 120 / 30 / 50) or "random" (`TRAFFIC_SHARES`).
- **Delay:** d_max = v RTT / 2, v = 2e8 m/s, 200 us -> 20 km, straight lines (`ROUTE_FACTOR` = 1).
- **Pools:** 25 candidates by farthest-first k-center on real RRH sites (P01 = nearest the Bernabeu),
  fixed. Backward elimination (remove the pool that raises the mean delay least, never unserve an RRH)
  and K = smallest K within 10 % of the 25-pool mean delay -> **K = 19** (P06, P07, P10, P11, P24, P25 off).
- **Numbers:** K = 19: 0 unserved, mean RTT 19.9 us (std 11.2), max 68.2 us, mean 1.99 km. K = 25: 18.2 us.
  K = 1 still serves everything (71.3 us): 200 us is not binding in 30 x 30 km. Smallest K serving all:
  1 / 2 / 6 / 17 for 200 / 150 / 100 / 50 us. Every RRH reaches 10-19 pools (mean 16.8), so category 1
  ("only this pool") is empty at 200 us; at 50 us 50 RRHs have one option and 1 is unserved.
- **Baseline for phase 2:** `phase1/data/assignment_K19.csv`. Suggested K cases: 8 / 19 / 25.

## Phase 2: load balancing (week 3, done)

Instructions: professor's review "Project review phase 2 - RRH balancing and load balancing" (thesis
sections 3.2.4 and 3.3.4). Virtualised scenario, no pool capacity limit: the goal is to *balance* the
load, not to minimise cards. Code: `python/13_traffic.py`, `14_balancing.py`, `15_p2_figures.py` +
`p2_lib.py`, `p2_style.py`; parameters in the phase-2 block of `python/config.py`; outputs in `phase2/`.
Full reasoning: `week3.txt`. Report: `reports/week3_report_phase2.docx`.

- **Scenario:** the phase-1 reference (200 RRHs, geo traffic 120 residential / 30 office / 50 mixed,
  RTT <= 200 us). K cases: normal 19, few 8, many 25 (pool sets from the phase-1 backward elimination).
- **Profiles:** thesis fig. E.1 digitised (`PROFILES`), index h = hour ending at h:00.
- **Traffic per RRH:** per merged station 45 Mbps if 4G (3 x 20 MHz x 1.5 b/s/Hz, 50 % load) + 150 Mbps
  if 5G (3 x 100 MHz x 5 b/s/Hz, 10 % load), x stations at the site, converted to MBph (1 Mbps for 1 h =
  450 MB). 20,250 to 526,500 MBph per RRH. GOPS not used.
- **Balancing hour:** 16:00, max of the sum of the three profiles (`BALANCE_HOUR = "auto"`); this
  assignment is the adopted one. The network total peaks at 22:00 (60 % residential).
- **Algorithm A (traffic):** 1st iteration = single-option RRHs (none at 200 us); then order by fewest
  possible pools, highest traffic at 16:00, nearest pool; each RRH -> possible pool with lowest load, ties -> nearest.
- **Algorithm B (number of RRHs):** same 1st iteration; order by fewest possible pools, then nearest;
  each RRH -> possible pool with fewest RRHs, ties -> nearest.
- **Numbers (K = 19, 16:00):** load CV 1.11 (delay only) -> 0.04 (A) / 0.26 (B); RRHs per pool 2-33 ->
  7-15 / 10-11; mean distance 2.0 -> 10.3 / 7.5 km (mean RTT 19.9 -> 102.5 / 75.2 us); 182 / 157 of 200 RRHs
  move. Price of balancing: every pool is reachable from almost every RRH, so RRHs cross the city
  (51 % of links > 10 km with A). All residential / all office give the same assignment (CV 0.00 after).
  Balancing at another hour moves 124-174 RRHs; with the 16:00 assignment the CV stays 0.04-0.37 all day.
  Few pools (8) are easiest to balance (A: CV 0.00), many (25) hardest (A: 0.10, B: 0.40).
- **All review outputs produced:** fig01-fig10 in `phase2/figures/` (profiles, network load, load per
  pool at 8/15/21 h, single-profile bars, RRHs per pool, hour dependence, distance bands, average
  capacity, K comparison).

## Phase 3: 5G link budget in Excel (week 4, workbook done)

Instructions: `phase3/5G_link_budget.pdf`. Due **30 November 2026**. Branch `phase3-5G-link-budget`.
Deliverable: `phase3/5G_link_budget.xlsx`, one sheet, kept simple on purpose (weekly-report level).
Details: `week4.txt`.

- **Structure:** same steps as 5g-tools (EIRP, sensitivity, margins, path loss, PASS/FAIL at a distance),
  downlink and uplink in two columns, a short explanation per row, plus MAPL, maximum range and cell radius.
- **Values:** n78 3.5 GHz, 30 kHz SCS, 273 RB; gNB 53 dBm, 17 dBi, 2 dB cable; UE 23 dBm, 20 RB; NF 7 / 5 dB;
  SINR -6 dB, margins 7 / 2 / 1 dB (5g-tools values); UMa NLOS, gNB 25 m, outdoor.
- **Numbers:** MAPL DL 151.1 dB, UL 134.4 dB -> range 1,741 m / 653 m, cell radius 653 m (uplink-limited),
  about 1,084 sites for 900 km2 vs 1,134 real 5G sites.
- **Check:** with the 5g-tools NR example inputs the sheet gives the same margin (+3.77 dB).

## Next steps

Phase 1, still open:
- [ ] Check a few Madrid sites by eye on the Infoantenas portal against the dataset.
- [ ] Check the office / mixed zones of the geographic traffic rule on `phase1/maps/map02_traffic_patterns.html`.

Phase 3:
- [x] Study the example calculator and list every parameter.
- [x] Build the Excel workbook (uplink and downlink, NR parameters), with an explanation of each parameter.
- [x] Cross-check against the online calculator (5g-tools NR example).
- [x] `week4.txt`.
- [ ] Open the workbook in Excel once, check the layout and save it (stores computed values).
- [x] Week 4 report: `reports/week4_report_phase3.docx` (figure in `phase3/figures/`).
- [ ] Phase-2 and phase-3 sections of `report.txt`.

Every week:
- [ ] Weekly report, and `report.txt` updated (phase-2 section still missing in `report.txt`).

## Working rules

- Never edit `data/raw/`. Changing a rule means editing `python/config.py` and re-running from step 03.
- Keep every scenario parameter in `python/config.py` only.
- Secrets (the OpenCelliD key) only in environment variables, never committed.
- `json/rrh_master.json` is the input of the simulator: do not change its fields without telling the team.
