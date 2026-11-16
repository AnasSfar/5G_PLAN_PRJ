# Project context

Shared context for the team (and for any AI assistant working in this repo). Keep it up to date
when a decision changes or a week is finished.

## Course and assignment

- **Course:** MASTEAM, Wireless & Radio Communication (5G NR air interface, cellular planning), EETAC (UPC), 2026.
- **Professor:** Sílvia Ruiz.
- **Assignment, phase 1 (scenario + delay-based pool placement):** `docs/C-RAN work_instructions_v2.pdf` (text version in `docs/work_instructions_transcript.md`).
- **Assignment, phase 2 (load balancing):** `docs/Project review_phase2_RRH_balancing_and_load_balancing.pdf` (text version in `docs/phase2_transcript.md`).
- **Reference to reproduce:** `docs/Thesis_TiagoM_v20161114_vLC.pdf`, Tiago Monteiro's master thesis on C-RAN in small cells.
- **Team:** 3 students. Any programming language is allowed; we use Python.

## Goal

Design a C-RAN: choose the number K and the positions of the BBU pools, and assign every RRH to a pool, so that:
- the RRH-to-pool distance (fronthaul delay) stays below the maximum acceptable delay;
- load and traffic are balanced between pools.

Every RRH site is a candidate pool site. Pools are picked with a heuristic such as farthest-first
k-center, for several values of K, and the results are compared. The program must also be able to
inject synthetic RRHs (their number is a variable), clearly labelled, to test higher densities.

Extra deliverable: a **5G link budget in Excel**.

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

## Phase 2: load balancing (professor's review, not started)

Use the BBU pools to spread the RRHs evenly so the network is more resilient to faults.
- **Virtualised scenario:** the load is counted in Mbps or GOPS, which gives the number of processing cards per pool.
- **No limit on pool capacity:** there is no maximum number of cards per pool. The goal is to *balance* the load, not to minimise the number of cards.
- **Traffic profiles:** every RRH gets a profile (residential, office or mixed). Give the 24 h curve of each profile as a figure.
- **Analysis hour:** choose 8:00, 15:00 (peak) or 21:00. A good choice is the hour where the sum of the three profiles is highest, usually around noon.

**Algorithm A: balancing by traffic load**
1. Choose the hour.
2. First iteration: assign the RRHs that can reach only one pool (within the delay limit), then compute each pool's load.
3. Second iteration: order the remaining RRHs carefully, or the solution may not be physically possible. Take into account the number of possible pools, the distance to each and the current pool traffic.
4. After each assignment, update that pool's load. Continue until every RRH is assigned.

**Algorithm B: balancing by number of RRHs (for comparison)**
1. Same first iteration as A (RRHs with a single possible pool).
2. Sort the remaining RRHs by their number of possible pools, in ascending order.
3. Assign each one to the possible pool that has the fewest RRHs, update the counts and continue until every RRH is assigned.

**Outputs to simulate and plot**

Before balancing (pools assigned by delay only):
- [ ] Load per pool at 8:00, 15:00 and 21:00: three figures, x = pool id, y = total load (Mbps or GOPS).
- [ ] At least at peak hour: 3 bars per pool for all residential, all office and the real mix.
- [ ] Overall network load over 24 h (like fig. 4.21 of the thesis).

After balancing:
- [ ] Number of RRHs per pool for algorithm A (traffic) and algorithm B (number of RRHs), to compare with delay only.
- [ ] Figure or table of how many RRHs change pool depending on the hour. Re-wiring is not physically possible, so the peak-hour assignment is the one adopted.
- [ ] Balancing results when all RRHs are residential vs all office.
- [ ] Number of RRHs per distance band (0–1 km, 1–2 km, …) for the three cases: delay only, traffic balancing, RRH-count balancing (like fig. 4.3 of the thesis).
- [ ] Average capacity per pool for the same three cases (like fig. 4.4 of the thesis).
- [ ] Repeat the whole comparison for three values of K: normal, too few pools, too many pools.

## Next steps

Phase 1, still open:
- [ ] Check a few Madrid sites by eye on the Infoantenas portal against the dataset.
- [ ] Synthetic RRH injection (variable count, labelled).
- [ ] RRH-to-candidate distance matrix and conversion to fronthaul delay.
- [ ] Farthest-first k-center for several K, then RRH-to-pool assignment by delay (this is the baseline for phase 2).
- [ ] 5G link budget in Excel.

Phase 2:
- [ ] Define the 24 h traffic profiles (residential, office, mixed), the conversion to Mbps or GOPS, and how each RRH gets its profile.
- [ ] Build the list of possible pools for each RRH (within the delay limit).
- [ ] Implement algorithms A and B, then produce the figures listed above.

Every week:
- [ ] Weekly report, and `report.txt` updated.

## Working rules

- Never edit `data/raw/`. Changing a rule means editing `python/config.py` and re-running from step 03.
- Keep every scenario parameter in `python/config.py` only.
- Secrets (the OpenCelliD key) only in environment variables, never committed.
- `json/rrh_master.json` is the input of the simulator: do not change its fields without telling the team.
