"""Step 1 - download the Infoantenas GeoJSON for the 15 x 15 grid of 2 km tiles.

Each answer is saved byte-for-byte in data/raw/tiles/. A tile already on disk is skipped,
so the script can be stopped and restarted without scraping twice.
"""
import time
import requests
import config as cfg


def main():
    session = requests.Session()
    session.headers["User-Agent"] = cfg.USER_AGENT
    total = cfg.N_TILES ** 2
    done = 0
    for r in range(cfg.N_TILES):
        for c in range(cfg.N_TILES):
            done += 1
            out = cfg.RAW_TILES / f"tile_{r:02d}_{c:02d}.json"
            if out.exists():
                continue
            w, s, e, n = cfg.tile_bbox(r, c)
            params = {"idCapa": "null", "bbox": f"{w:.6f},{s:.6f},{e:.6f},{n:.6f}", "zoom": cfg.GEOJSON_ZOOM}
            for attempt in range(1, cfg.RETRIES + 1):
                try:
                    resp = session.get(cfg.GEOJSON_URL, params=params, timeout=60)
                    resp.raise_for_status()
                    out.write_bytes(resp.content)       # raw bytes, untouched
                    print(f"[{done}/{total}] tile {r:02d}_{c:02d} ok ({len(resp.content)} bytes)")
                    break
                except requests.RequestException as exc:
                    print(f"[{done}/{total}] tile {r:02d}_{c:02d} attempt {attempt} failed: {exc}")
                    time.sleep(2 * attempt)
            else:
                print(f"!! tile {r:02d}_{c:02d} gave up, re-run the script to retry")
            time.sleep(cfg.SLEEP_S)


if __name__ == "__main__":
    main()
