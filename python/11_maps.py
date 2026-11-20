"""Step 11 (phase 1) - The map figures on a real street map (interactive Leaflet / Folium pages).

Same colours and content as the static figures of step 9, drawn over an OpenStreetMap / CARTO basemap.
The pages load the map tiles and Leaflet from the internet when they are opened in a browser.

  map01_scenario.html         fig01: RRHs by traffic pattern, 2,085 real sites, active / switched-off pools
  map02_traffic_patterns.html fig02: random shares (left) vs geographic rule with its zones (right), synced
  map03_assignment.html       fig03: one colour per pool, link RRH -> pool, one layer per pool, unserved RRHs
  map04_options_200us.html    fig11: number of reachable pools per RRH, RTT <= 200 us
  map05_options_50us.html     fig12c: the same at 50 us, 5 km reach of each pool, unserved RRH, links

Each page also carries, offline, the municipal boundaries of the area (data/municipalities_madrid.geojson, IGN
data via the es-atlas package, MIT), Leaflet itself (inlined, cached in python/web_cache/), and a notice that
appears when the background tiles cannot load. Only the tiles need the internet.

Output: phase1/maps/. Run after steps 7-8.
"""
import json

import folium
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from branca.element import MacroElement
from folium.plugins import DualMap
from jinja2 import Template

import config as cfg
import p1_lib as L

INK = "#0b0b0b"
# Basemaps (first = default). All Esri, no API key, and they accept pages opened from disk
# (tile.openstreetmap.org refuses requests without a web Referer, i.e. from a local file).
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/{}/MapServer/tile/{{z}}/{{y}}/{{x}}"
TILES = [
    (ESRI.format("Canvas/World_Light_Gray_Base"), "Light grey (Esri)",
     "Tiles &copy; Esri, HERE, Garmin, &copy; OpenStreetMap contributors"),
    (ESRI.format("World_Street_Map"), "Streets (Esri)",
     "Tiles &copy; Esri, HERE, Garmin, USGS, &copy; OpenStreetMap contributors"),
    (ESRI.format("World_Imagery"), "Satellite (Esri)", "Tiles &copy; Esri, Maxar, Earthstar Geographics"),
]
MUNI_FILE = cfg.DATA / "municipalities_madrid.geojson"   # IGN municipal boundaries (es-atlas, MIT), offline
WEB_CACHE = cfg.ROOT / "python" / "web_cache"
INLINE = ["https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js",
          "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css",
          "https://cdn.jsdelivr.net/gh/jieter/Leaflet.Sync/L.Map.Sync.min.js"]
DROP = ("bootstrap", "fontawesome", "awesome-markers", "awesome.rotate", "jquery")   # not used by these maps


def pool_colors(ids):
    cm = plt.get_cmap("tab20")
    return {pid: matplotlib.colors.to_hex(cm(i % 20)) for i, pid in enumerate(ids)}


class MetricScale(MacroElement):
    """Metric-only scale bar, bottom right (rendered inside the map's own script)."""
    _template = Template("""{% macro script(this, kwargs) %}
        L.control.scale({imperial: false, position: 'bottomright', maxWidth: 160}).addTo({{ this._parent.get_name() }});
    {% endmacro %}""")


class TileNotice(MacroElement):
    """Shows a notice on the map when the background tiles cannot load (offline, or a viewer that blocks images)."""
    _template = Template("""{% macro script(this, kwargs) %}
    (function (map) {
        var fails = 0, box = null;
        function show(on) {
            if (on && !box) {
                box = L.DomUtil.create('div', '', map.getContainer());
                box.style.cssText = 'position:absolute;top:48px;left:50%;transform:translateX(-50%);z-index:1000;' +
                    'background:#fff8e1;border:1px solid #e0b100;border-radius:6px;padding:6px 10px;' +
                    'font:12px Arial,sans-serif;color:#0b0b0b;max-width:460px;text-align:center';
                box.innerHTML = '<b>The background map cannot load here.</b> This viewer blocks map images, or ' +
                    'there is no internet. Download the file and open it in Chrome, Firefox or Edge. ' +
                    'Municipal boundaries are shown meanwhile.';
            }
            if (box) box.style.display = on ? 'block' : 'none';
        }
        function hook(l) {
            if (!(l instanceof L.TileLayer) || l._noticeHooked) return;
            l._noticeHooked = true;
            l.on('tileerror', function () { if (++fails >= 3) show(true); });
            l.on('tileload', function () { fails = 0; show(false); });
        }
        map.eachLayer(hook);
        map.on('layeradd', function (e) { hook(e.layer); });
    })({{ this._parent.get_name() }});
    {% endmacro %}""")


def add_municipalities(m):
    """Offline layer: municipal boundaries and names, visible even when no map tile can load."""
    if not MUNI_FILE.exists():
        return
    data = json.loads(MUNI_FILE.read_text(encoding="utf-8"))
    g = folium.FeatureGroup(name="Municipal boundaries (offline)", show=True)
    folium.GeoJson(data, style_function=lambda f: {"color": "#6b6a65", "weight": 1.2, "fill": True,
                                                   "fillColor": "#f4f3ef", "fillOpacity": 0.25},
                   tooltip=folium.GeoJsonTooltip(fields=["name"], labels=False)).add_to(g)
    w, s, e, n = cfg.BBOX
    for f in data["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        ring = np.array(max((p[0] for p in polys), key=len))
        lon, lat = ring[:, 0].mean(), ring[:, 1].mean()
        if w < lon < e and s < lat < n:
            folium.Marker([lat, lon], icon=folium.DivIcon(
                html=f"<div style='font:italic 11px Arial;color:#6b6a65;white-space:nowrap;"
                     f"text-shadow:0 0 3px #fff,0 0 3px #fff'>{f['properties']['name']}</div>",
                icon_size=(140, 14), icon_anchor=(40, 7))).add_to(g)
    g.add_to(m)


def cached(url):
    """Content of a library file: local cache first, else download once (needs internet)."""
    import urllib.request
    p = WEB_CACHE / "".join(ch if ch.isalnum() or ch in "@.-" else "_" for ch in url)
    if not p.exists():
        try:
            WEB_CACHE.mkdir(parents=True, exist_ok=True)
            p.write_bytes(urllib.request.urlopen(url, timeout=20).read())
        except Exception as exc:                      # offline: keep the CDN link
            print("  could not download", url, "->", exc)
            return None
    return p.read_text(encoding="utf-8")


def make_standalone(path):
    """Inline Leaflet (+ sync plugin) and drop unused CDN libraries, so a page needs the internet only for
    the background tiles."""
    import re
    html = path.read_text(encoding="utf-8")

    def repl(mt):
        tag, url = mt.group(0), mt.group(1)
        if any(k in url for k in DROP):
            return ""
        if url in INLINE:
            body = cached(url)
            if body is not None:
                return f"<style>{body}</style>" if url.endswith(".css") else f"<script>{body}</script>"
        return tag
    html = re.sub(r'<script src="([^"]+)"></script>', repl, html)
    html = re.sub(r'<link rel="stylesheet" href="([^"]+)"/>', repl, html)
    path.write_text(html, encoding="utf-8")


def base_map(m=None):
    """A map centred on the scenario with the two basemaps and the 30 x 30 km box."""
    if m is None:
        m = folium.Map(location=[cfg.CENTER_LAT, cfg.CENTER_LON], zoom_start=11, tiles=None, control_scale=False,
                       zoom_snap=0.25, zoom_delta=0.5)
    for i, (url, name, attr) in enumerate(TILES):
        folium.TileLayer(url, name=name, attr=attr, max_zoom=19, show=(i == 0)).add_to(m)
    w, s, e, n = cfg.BBOX
    folium.Rectangle([[s, w], [n, e]], color="#333", weight=2, fill=False, dash_array="6 4",
                     tooltip="30 x 30 km scenario").add_to(m)
    m.fit_bounds([[s, w], [n, e]], padding_top_left=(140, 10), padding_bottom_right=(10, 10))
    m.get_root().header.add_child(folium.Element(
        "<style>.leaflet-control-layers{font:11px/1.25 Arial,sans-serif}"
        ".leaflet-control-layers-list label{margin:0}</style>"))
    MetricScale().add_to(m)
    add_municipalities(m)
    TileNotice().add_to(m)
    return m


def legend(m, title, rows, pos="bottomleft"):
    """Fixed legend box: rows = [(html swatch, label), ...]."""
    v, h = ("bottom", "left") if pos == "bottomleft" else ("bottom", "right")
    items = "".join(f"<div style='display:flex;align-items:center;gap:6px;margin:2px 0'>{sw}<span>{lab}</span></div>"
                    for sw, lab in rows)
    html = (f"<div style='position:fixed;{v}:34px;{h}:12px;z-index:9999;background:rgba(255,255,255,.93);"
            f"padding:8px 10px;border:1px solid #bbb;border-radius:6px;font:12px/1.35 Arial,sans-serif;"
            f"color:{INK};max-width:225px'><b>{title}</b>{items}</div>")
    m.get_root().html.add_child(folium.Element(html))


def title_box(m, text):
    html = (f"<div style='position:fixed;top:10px;left:56px;z-index:9999;background:rgba(255,255,255,.93);"
            f"padding:6px 10px;border:1px solid #bbb;border-radius:6px;font:bold 13px Arial,sans-serif;"
            f"color:{INK}'>{text}</div>")
    m.get_root().html.add_child(folium.Element(html))


def dot(c, edge="#fff"):
    return f"<span style='display:inline-block;width:11px;height:11px;border-radius:50%;background:{c};border:1px solid {edge}'></span>"


def square(fill, edge=INK):
    return f"<span style='display:inline-block;width:11px;height:11px;background:{fill};border:2px solid {edge}'></span>"


def cross(c="#e34948"):
    return f"<span style='color:{c};font:bold 15px Arial;line-height:11px'>&#10005;</span>"


def add_pool(layer, p, fill, label, tip):
    html = (f"<div style='display:flex;align-items:center;gap:3px;white-space:nowrap'>"
            f"<div style='width:12px;height:12px;background:{fill};border:2px solid {INK}'></div>"
            f"<span style='font:bold 11px Arial;color:{INK};background:rgba(255,255,255,.85);padding:0 2px;"
            f"border-radius:2px'>{label}</span></div>")
    folium.Marker([p["lat"], p["lon"]], tooltip=tip,
                  icon=folium.DivIcon(html=html, icon_size=(90, 16), icon_anchor=(8, 8))).add_to(layer)


def add_cross(layer, lat, lon, tip, c="#e34948"):
    folium.Marker([lat, lon], tooltip=tip, icon=folium.DivIcon(
        html=f"<div style='color:{c};font:bold 18px Arial;text-shadow:0 0 2px #fff'>&#10005;</div>",
        icon_size=(18, 18), icon_anchor=(7, 11))).add_to(layer)


def rrh_tip(r, a=None):
    t = f"<b>{r['rrh_id']}</b>{' (synthetic)' if r['is_synthetic'] else ''}<br>{r['traffic']}: {r.get('traffic_reason', '')}"
    if a is not None:
        if a.served:
            t += (f"<br>best pool <b>{a.best_pool}</b>: {a.d_best_km:.2f} km, {a.rtt_best_us:.1f} us"
                  f"<br>{a.n_options} reachable pools: {a.options}")
        else:
            t += f"<br><b>UNSERVED</b>, nearest pool {a.nearest_pool_any} at {a.d_nearest_any_km:.2f} km"
    return t


def zone_shape(z):
    """Lat/lon outline of a circle (name, lat, lon, r) or a corridor (name, lat1, lon1, lat2, lon2, w)."""
    if len(z) == 4:
        z = (z[0], z[1], z[2], z[1], z[2], z[3])
    _, la1, lo1, la2, lo2, w = z
    (ax, ay), (bx, by) = [tuple(map(float, L.to_xy(la, lo))) for la, lo in ((la1, lo1), (la2, lo2))]
    ang = np.arctan2(by - ay, bx - ax)
    t1 = np.linspace(ang + np.pi / 2, ang + 3 * np.pi / 2, 24)      # cap around A
    t2 = np.linspace(ang - np.pi / 2, ang + np.pi / 2, 24)          # cap around B
    xs = np.r_[ax + w * np.cos(t1), bx + w * np.cos(t2)]
    ys = np.r_[ay + w * np.sin(t1), by + w * np.sin(t2)]
    lat, lon = L.to_latlon(xs, ys)
    return [[float(a), float(b)] for a, b in zip(lat, lon)]


def main():
    sc = json.loads((cfg.P1_DATA / "scenario.json").read_text(encoding="utf-8"))
    res = json.loads((cfg.P1_DATA / "results.json").read_text(encoding="utf-8"))
    rrhs, pools = sc["rrhs"], sc["pools"]
    K = res["k_selected"]; act_ids = res["active_pools"]
    act = [p for p in pools if p["pool_id"] in act_ids]
    pcol = pool_colors(act_ids)
    core = L.load_core()
    asg = pd.read_csv(cfg.P1_DATA / f"assignment_K{K}.csv").set_index("rrh_id")
    strict = min(cfg.RTT_SWEEP_US)
    asg_s = pd.read_csv(cfg.P1_DATA / f"assignment_K{K}_rtt{int(strict)}.csv").set_index("rrh_id")
    n_assigned = asg.best_pool.value_counts()
    out = cfg.P1_MAPS

    def pools_layer(m, show_off=True, counts=None, fill=None):
        g = folium.FeatureGroup(name="BBU pools")
        for p in pools:
            on = p["pool_id"] in act_ids
            if not on and not show_off:
                continue
            n = int(counts.get(p["pool_id"], 0)) if counts is not None and on else None
            lab = p["pool_id"] + (f" ({n})" if n is not None else "")
            tip = (f"<b>{p['pool_id']}</b> at site {p['site_rrh']}<br>"
                   + (f"active{f', {n} RRHs' if n is not None else ''}" if on else "candidate, switched off")
                   + f"<br>farthest-first order {p['ff_order']}")
            add_pool(g, p, (fill or {}).get(p["pool_id"], INK) if on else "#ffffff", lab, tip)
        g.add_to(m)

    # ------------------------------------------------------------------ map01 scenario
    m = base_map()
    g = folium.FeatureGroup(name=f"all {len(core)} real core RRHs", show=True)
    for c in core:
        folium.CircleMarker([c["lat"], c["lon"]], radius=1.5, color="#8d8c86", weight=0, fill=True,
                            fill_opacity=0.55).add_to(g)
    g.add_to(m)
    for t, col in cfg.TRAFFIC_COLORS.items():
        g = folium.FeatureGroup(name=f"{t} RRHs ({sum(r['traffic'] == t for r in rrhs)})")
        for r in rrhs:
            if r["traffic"] != t:
                continue
            if r["is_synthetic"]:
                folium.RegularPolygonMarker([r["lat"], r["lon"]], number_of_sides=3, radius=6, color=INK, weight=1,
                                            fill_color=col, fill_opacity=1, tooltip=rrh_tip(r)).add_to(g)
            else:
                folium.CircleMarker([r["lat"], r["lon"]], radius=5, color="#fff", weight=1, fill=True,
                                    fill_color=col, fill_opacity=0.95, tooltip=rrh_tip(r, asg.loc[r["rrh_id"]])).add_to(g)
        g.add_to(m)
    pools_layer(m)
    folium.LayerControl(collapsed=False).add_to(m)
    title_box(m, f"Madrid 30 x 30 km: {len(rrhs)} RRHs and {len(pools)} candidate BBU pools")
    rows = [(dot(c), f"{t} ({sum(r['traffic'] == t for r in rrhs)})") for t, c in cfg.TRAFFIC_COLORS.items()]
    rows += [(dot("#8d8c86", "#8d8c86"), f"all {len(core)} real core RRHs"),
             (square(INK), f"active pool ({len(act_ids)})"),
             (square("#fff"), f"candidate, switched off ({len(pools) - len(act_ids)})")]
    if any(r["is_synthetic"] for r in rrhs):
        rows.append(("&#9650;", f"synthetic RRH ({sum(r['is_synthetic'] for r in rrhs)})"))
    legend(m, "Traffic pattern / pools", rows)
    m.save(str(out / "map01_scenario.html"))

    # ------------------------------------------------------------------ map02 random vs geo (synced)
    dm = DualMap(location=[cfg.CENTER_LAT, cfg.CENTER_LON], zoom_start=10.5, tiles=None, zoom_snap=0.25)
    rnd = L.assign_traffic([dict(r) for r in rrhs], "random", cfg.TRAFFIC_SHARES, cfg.TRAFFIC_SEED)
    for mm, lst in ((dm.m1, rnd), (dm.m2, rrhs)):
        url, name, attr = TILES[0]
        folium.TileLayer(url, name=name, attr=attr, max_zoom=19).add_to(mm)
        add_municipalities(mm)
        TileNotice().add_to(mm)
        w, s, e, n = cfg.BBOX
        folium.Rectangle([[s, w], [n, e]], color="#333", weight=2, fill=False, dash_array="6 4").add_to(mm)
        for r in lst:
            folium.CircleMarker([r["lat"], r["lon"]], radius=5, color="#fff", weight=1, fill=True,
                                fill_color=cfg.TRAFFIC_COLORS[r["traffic"]], fill_opacity=0.95,
                                tooltip=f"<b>{r['rrh_id']}</b><br>{r['traffic']}: {r['traffic_reason']}").add_to(mm)
    for z in cfg.OFFICE_ZONES + cfg.MIXED_ZONES:
        kind = "office" if z in cfg.OFFICE_ZONES else "mixed"
        folium.Polygon(zone_shape(z), color=cfg.TRAFFIC_COLORS[kind], weight=2, dash_array="5 4", fill=True,
                       fill_opacity=0.10, tooltip=f"{kind} zone: {z[0]}").add_to(dm.m2)
    dm.m1.fit_bounds([[cfg.BBOX[1], cfg.BBOX[0]], [cfg.BBOX[3], cfg.BBOX[2]]])
    cnt = lambda lst, t: sum(r["traffic"] == t for r in lst)
    head = ("<div style='position:fixed;top:8px;z-index:9999;left:{l};background:rgba(255,255,255,.93);"
            "padding:6px 10px;border:1px solid #bbb;border-radius:6px;font:12px Arial;color:#0b0b0b'><b>{t}</b><br>{c}</div>")
    for left, lst, t in (("60px", rnd, "Random: " + ", ".join(f"{v:.0%} {k}" for k, v in cfg.TRAFFIC_SHARES.items())),
                         ("calc(50% + 60px)", rrhs, "Geographic rule (dashed: office / mixed zones)")):
        c = " &nbsp; ".join(f"{dot(col)} {k} ({cnt(lst, k)})" for k, col in cfg.TRAFFIC_COLORS.items())
        dm.get_root().html.add_child(folium.Element(head.format(l=left, t=t, c=c)))
    dm.save(str(out / "map02_traffic_patterns.html"))

    # ------------------------------------------------------------------ map03 assignment
    m = base_map()
    pos = {p["pool_id"]: p for p in pools}
    for pid in act_ids:
        g = folium.FeatureGroup(name=f"<span style='color:{pcol[pid]}'>&#9632;</span> {pid} ({int(n_assigned.get(pid, 0))} RRHs)")
        p = pos[pid]
        for r in rrhs:
            a = asg.loc[r["rrh_id"]]
            if a.best_pool != pid:
                continue
            folium.PolyLine([[r["lat"], r["lon"]], [p["lat"], p["lon"]]], color=pcol[pid], weight=2, opacity=0.85,
                            tooltip=f"{r['rrh_id']} -> {pid}: {a.d_best_km:.2f} km, {a.rtt_best_us:.1f} us").add_to(g)
            folium.CircleMarker([r["lat"], r["lon"]], radius=4.5, color="#fff", weight=1, fill=True,
                                fill_color=pcol[pid], fill_opacity=1, tooltip=rrh_tip(r, a)).add_to(g)
        g.add_to(m)
    gu = folium.FeatureGroup(name="unserved RRHs")
    for r in rrhs:
        a = asg.loc[r["rrh_id"]]
        if not a.served:
            add_cross(gu, r["lat"], r["lon"], rrh_tip(r, a))
    gu.add_to(m)
    pools_layer(m, show_off=False, counts=n_assigned, fill=pcol)
    folium.LayerControl(collapsed=False).add_to(m)
    title_box(m, f"Minimise Delay, K = {K} pools, RTT &le; {cfg.MAX_RTT_US:g} us (d &le; {cfg.d_max_km():g} km)")
    legend(m, "Assignment", [(square("#999"), "BBU pool (number of RRHs); colour = pool"),
                             ("<span style='display:inline-block;width:16px;border-top:2px solid #999'></span>",
                              "link RRH &rarr; nearest reachable pool"),
                             (cross(), f"unserved RRH ({int((~asg.served).sum())})")])
    m.save(str(out / "map03_assignment.html"))

    # ------------------------------------------------------------------ map04 / map05 options
    def options_map(a_df, rtt, name, circles, links):
        m = base_map()
        top = int(max(a_df.n_options.max(), 1))
        blues = plt.get_cmap("Blues", top + 1)
        colors = [matplotlib.colors.to_hex(blues(i)) for i in range(top + 1)]
        counts = a_df.n_options.value_counts()
        w_sw = max(6, min(18, 180 // top))
        step = 1 if top <= 10 else 3
        sw = "".join(f"<div style='text-align:center;font:9px Arial;width:{w_sw}px'><div title='{int(counts.get(i, 0))} RRHs' "
                     f"style='height:12px;background:{c};border:1px solid #52514e'></div>"
                     f"{i if (i == 1 or i == top or i % step == 0) else '&nbsp;'}</div>"
                     for i, c in enumerate(colors) if i > 0)
        scale_html = f"<div style='display:flex;gap:0;margin-top:3px'>{sw}</div>"
        dmax = cfg.d_max_km(rtt)
        if circles:
            gc = folium.FeatureGroup(name=f"{dmax:g} km reach of each pool")
            for p in act:
                folium.Circle([p["lat"], p["lon"]], radius=dmax * 1000, color="#52514e", weight=1, dash_array="3 4",
                              fill=False).add_to(gc)
            gc.add_to(m)
        if links:
            gl = folium.FeatureGroup(name="links RRH -> pool", show=True)
            for r in rrhs:
                a = a_df.loc[r["rrh_id"]]
                if a.served:
                    p = pos[a.best_pool]
                    folium.PolyLine([[r["lat"], r["lon"]], [p["lat"], p["lon"]]], color=pcol[a.best_pool],
                                    weight=1.5, opacity=0.7).add_to(gl)
            gl.add_to(m)
        g = folium.FeatureGroup(name="RRHs")
        for r in rrhs:
            a = a_df.loc[r["rrh_id"]]
            if a.n_options == 0:
                add_cross(g, r["lat"], r["lon"], rrh_tip(r, a))
            else:
                folium.CircleMarker([r["lat"], r["lon"]], radius=5.5, color="#52514e", weight=1, fill=True,
                                    fill_color=colors[int(a.n_options)], fill_opacity=1, tooltip=rrh_tip(r, a)).add_to(g)
        g.add_to(m)
        pools_layer(m, show_off=False, counts=a_df.best_pool.value_counts(), fill=pcol if links else None)
        folium.LayerControl(collapsed=False).add_to(m)
        n1 = int((a_df.n_options == 1).sum()); n0 = int((a_df.n_options == 0).sum())
        title_box(m, f"Reachable pools per RRH, K = {K}, RTT &le; {rtt:g} us (d &le; {dmax:g} km): "
                     f"mean {a_df.n_options.mean():.1f}, single option {n1}, unserved {n0}")
        legend(m, "Reachable pools per RRH", [(scale_html, ""),
                                              (square(INK if not links else "#999"), "active pool (number of RRHs)"
                                               + ("; links coloured by pool" if links else "")),
                                              (cross(), f"unserved RRH ({n0})")]
               + ([("<span style='display:inline-block;width:14px;height:14px;border-radius:50%;border:1px dashed #52514e'></span>",
                    f"{dmax:g} km reach of a pool")] if circles else []))
        m.save(str(out / name))

    options_map(asg, cfg.MAX_RTT_US, f"map04_options_{int(cfg.MAX_RTT_US)}us.html", circles=False, links=False)
    options_map(asg_s, strict, f"map05_options_{int(strict)}us.html", circles=True, links=True)
    for p in sorted(out.glob("map0*.html")):
        make_standalone(p)
    print("maps written to", out, ":", ", ".join(sorted(p.name for p in out.glob("map0*.html"))))


if __name__ == "__main__":
    main()
