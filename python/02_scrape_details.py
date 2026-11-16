"""Step 2 - download the detail page of every site found in the tiles.

The GeoJSON has no technology field, only the detail page lists the assigned frequency bands,
which step 3 turns into a 4G/5G label. Raw HTML is saved untouched in data/raw/details/.
Resumable: pages already on disk are skipped.
"""
import json
import re
import time
import requests
import config as cfg


def safe_name(code: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", code)


def load_sites():
    """All distinct sites in the raw tiles, keyed by their unique code 'OPERATOR - ID'."""
    sites = {}
    for f in sorted(cfg.RAW_TILES.glob("tile_*.json")):
        text = f.read_bytes().decode("latin-1").strip()
        feats = json.loads(text or "{}").get("features", [])
        for ft in feats:
            p = ft["properties"]
            sites[p["Gis_Codigo"]] = p["Gis_ID"]
    return sites


def main():
    sites = load_sites()
    print(f"{len(sites)} distinct sites to fetch")
    session = requests.Session()
    session.headers["User-Agent"] = cfg.USER_AGENT
    for i, (code, gid) in enumerate(sorted(sites.items()), 1):
        out = cfg.RAW_DETAILS / (safe_name(code) + ".html")
        if out.exists():
            continue
        params = {"emplazamiento": gid, "codEmplazamiento": code}
        for attempt in range(1, cfg.RETRIES + 1):
            try:
                resp = session.get(cfg.DETAIL_URL, params=params, timeout=60)
                resp.raise_for_status()
                out.write_bytes(resp.content)
                if i % 25 == 0:
                    print(f"[{i}/{len(sites)}] last: {code}")
                break
            except requests.RequestException as exc:
                print(f"[{i}/{len(sites)}] {code} attempt {attempt} failed: {exc}")
                time.sleep(2 * attempt)
        else:
            print(f"!! {code} gave up, re-run to retry")
        time.sleep(cfg.SLEEP_S)
    print("details done")


if __name__ == "__main__":
    main()
