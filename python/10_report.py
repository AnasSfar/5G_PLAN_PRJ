"""Step 10 (week 2) - build the week-2 report (.docx, same layout as the week-1 report) and export it
to PDF with Microsoft Word if it is installed.

Numbers are read from json/week2/*.json so the text always matches the last simulation.
Output: reports/week2_report.docx and reports/week2_report.pdf
"""
import json
import subprocess
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
import config as cfg

OUT = cfg.ROOT / "reports"
OUT.mkdir(exist_ok=True)
F = cfg.FIGS
S = json.loads((cfg.RESULTS / "summary.json").read_text(encoding="utf-8"))
TR = json.loads((cfg.RESULTS / "rrh_traffic.json").read_text(encoding="utf-8"))
C = S["cases"]
N = C["normal"]
HB = S["balancing_hour"]
fig_no = [0]
tab_no = [0]


# ----------------------------------------------------------------------------- helpers
def g(v):            # Mbps -> "x.x" Gbps
    return f"{v / 1000:.1f}"


def setup(doc):
    st = doc.styles["Normal"]
    st.font.name = "Arial"; st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    st.paragraph_format.space_after = Pt(0); st.paragraph_format.line_spacing = 1.15
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(2.54))
    sec.header_distance = Cm(0.5); sec.footer_distance = Cm(1.0)
    hp = sec.header.paragraphs[0]; hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.add_run().add_picture(str(cfg.ROOT / "img" / "upc_logo.png"), width=Cm(5.5))
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = fp.add_run()
    for t, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if t:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), t); r._r.append(e)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt; r._r.append(e)


def title(doc, text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    for i, line in enumerate(text.split("\n")):
        r = p.add_run(line); r.bold = True; r.font.size = Pt(13)
        if i == 0:
            r.add_break()


def h1(doc, text):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(16); p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text); r.font.size = Pt(14)


def h2(doc, text):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(10); p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text); r.font.size = Pt(12); r.font.color.rgb = RGBColor(0x43, 0x43, 0x43)


def para(doc, text, after=8):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(after)
    # very small markup: **bold**
    parts = text.split("**")
    for i, t in enumerate(parts):
        r = p.add_run(t); r.bold = i % 2 == 1
    return p


def bullets(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet"); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        parts = it.split("**")
        for i, t in enumerate(parts):
            r = p.add_run(t); r.bold = i % 2 == 1
    doc.paragraphs[-1].paragraph_format.space_after = Pt(8)


def caption(doc, text, kind="Figure"):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    if kind == "Figure":
        fig_no[0] += 1; n = fig_no[0]
    else:
        tab_no[0] += 1; n = tab_no[0]
    r = p.add_run(f"{kind} {n}. {text}"); r.italic = True
    return n


def figure(doc, path, text, width=15.5):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True; p.paragraph_format.space_before = Pt(4)
    p.add_run().add_picture(str(path), width=Cm(width))
    return caption(doc, text)


def shade(cell, hexcol="D9D9D9"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcol); tcPr.append(shd)


def table(doc, rows, text, widths=None, size=10):
    """rows[0] is the header (grey background, as in the week-1 report). Caption goes below."""
    t = doc.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.text = ""
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = True          # never split a table across pages
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val)); r.font.size = Pt(size)
            if i == 0:
                shade(c)
            if widths:
                c.width = Cm(widths[j])
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return caption(doc, text, "Table")


# ----------------------------------------------------------------------------- content
def build():
    doc = Document(); setup(doc)
    title(doc, "5G PLAN : WEEK 2 REPORT\nAnas Sfar, Dean Solano, Diego Soler")

    cls = TR["classes"]; nr = S["n_rrh"]
    net = TR["network_load_mbps"]
    hmax = net.index(max(net)) + 1; hmin = net.index(min(net)) + 1
    kf, kn, km = (cfg.K_CASES[c] for c in ("few", "normal", "many"))
    ld = N["load_stats_balancing_hour"]; rc = N["rrh_count_stats"]; dk = N["distance_km"]
    ac = N["avg_capacity_stats"]; ch = N["changes_vs_balancing_hour"]
    lb = N["load_stats_by_hour"]["delay"]
    hb4 = N["homogeneous_stats"]["before"]; ha = N["homogeneous_stats"]["after"]
    hrs = [h for h in cfg.HOURS if h != HB]

    # 1 ---------------------------------------------------------------------
    h1(doc, "1. Introduction")
    para(doc, f"In this stage we use the {nr:,} core RRHs of week 1 [1] to balance the load of the BBU pools "
              "[3]. The pools are placed with a farthest-first k-center heuristic and each RRH is first "
              "connected to its nearest pool (delay only). We then compare two balancing algorithms, by "
              "traffic (A) and by number of RRHs (B), following the master thesis [2].")

    # 2 ---------------------------------------------------------------------
    h1(doc, "2. Scenario parameters")
    para(doc, f"**Delay.** With 2x10^8 m/s in the fibre and a round-trip budget of {cfg.MAX_RTT_US:.0f} µs, the "
              f"maximum RRH-pool distance is {cfg.D_MAX_KM:.0f} km [2, eq. 3.3]. The thesis uses 15 km, but our "
              f"scenario is only 30 km wide and with 15 km almost every RRH could reach every pool. The possible "
              f"pools of an RRH are those within {cfg.D_MAX_KM:.0f} km.")
    para(doc, f"**Number of pools.** At least 10 pools are needed to serve every RRH within {cfg.D_MAX_KM:.0f} km. "
              f"We study three cases: K = {kf} (few: {C['few']['unserved']} RRHs unserved and "
              f"{C['few']['single_option']:,} with a single possible pool), K = {kn} (normal: "
              f"{C['normal']['mean_options']:.1f} possible pools per RRH on average) and K = {km} (too many: "
              f"{C['many']['mean_options']:.1f}).")
    para(doc, "**Traffic profiles.** Each RRH receives one of the residential, office or mixed profiles of "
              f"[2, Fig. E.1] (Figure 1a), according to land use: office within {cfg.OFFICE_RADIUS_KM} km of the "
              "main business districts (AZCA, Cuatro Torres, Distrito Telefónica, Campo de las Naciones, etc.), "
              "mixed in the dense centre inside the M-30 and at the airport, residential elsewhere. This gives "
              f"{cls['residential']:,} residential ({cls['residential'] / nr:.0%}), {cls['office']} office "
              f"({cls['office'] / nr:.0%}) and {cls['mixed']} mixed ({cls['mixed'] / nr:.0%}) RRHs. The peak "
              f"traffic of an RRH is {cfg.PEAK_4G_MBPS:.0f} Mbps per 4G station plus {cfg.PEAK_5G_MBPS:.0f} Mbps "
              "per 5G station, and its traffic at each hour is this peak multiplied by its profile. The load is "
              "counted in Mbps; with no pool capacity limit, the number of processing cards is proportional to it.")
    para(doc, f"**Balancing hour.** The sum of the three profiles is maximum at {HB:02d}:00, so the balancing is "
              f"done at this hour [3]. Figure 1b shows the overall network load: since most RRHs are "
              f"residential, it peaks at {hmax:02d}:00 ({g(max(net))} Gbps) and is lowest at {hmin:02d}:00 "
              f"({g(min(net))} Gbps).")
    figure(doc, F / "profiles_and_load.png",
           "(a) Normalised 24 h profile of each type of cell [2, Fig. E.1]; (b) overall network load during "
           "the day (as [2, Fig. 4.21]).", width=16)

    # 3 ---------------------------------------------------------------------
    h1(doc, "3. Algorithms")
    para(doc, "**Delay only:** each RRH is connected to its nearest pool. Both balancing algorithms first "
              "connect the RRHs that have only one possible pool and compute the pool loads. Then:")
    bullets(doc, [
        f"**A (traffic):** the remaining RRHs are sorted by number of possible pools (ascending), then by "
        f"traffic at {HB:02d}:00 (descending), then by distance; each goes to its possible pool with the lowest "
        "traffic, and the load is updated.",
        "**B (number of RRHs):** the remaining RRHs are sorted by number of possible pools (ascending); each goes "
        "to its possible pool with the fewest RRHs.",
    ])
    para(doc, "Ties are broken by choosing the closest pool. The results below are for K = "
              f"{kn} unless stated otherwise.")

    # 4 ---------------------------------------------------------------------
    h1(doc, "4. Before balancing (delay only)")
    para(doc, f"Figure 2 shows the load per pool at 08:00, 15:00 and 21:00. Farthest-first places most pools "
              f"on the border and only pool 1 in the dense centre, so pool 1 carries "
              f"{lb['8']['max'] / lb['8']['mean']:.1f}, {lb['15']['max'] / lb['15']['mean']:.1f} and "
              f"{lb['21']['max'] / lb['21']['mean']:.1f} times the average load. The imbalance is largest at "
              f"15:00, when the office and mixed cells of the centre are near their peak.")
    figure(doc, F / "1a_load_3h_normal.png", f"Load per BBU pool with delay only at (a) 08:00, (b) 15:00 and "
                                             f"(c) 21:00, K = {kn}.", width=16)
    para(doc, f"In Figure 3, at {HB:02d}:00, all-office gives the highest load ({g(hb4['off']['mean'])} Gbps "
              f"per pool on average, against {g(hb4['res']['mean'])} for all-residential and "
              f"{g(hb4['real']['mean'])} for the real mix), because {HB:02d}:00 is the office peak. With a single "
              f"profile every RRH is scaled by the same factor, so both homogeneous cases have the same relative "
              f"distribution (coefficient of variation {hb4['res']['cv']:.0%}); the real mix is more unbalanced "
              f"({hb4['real']['cv']:.0%}).")
    figure(doc, F / "1b_homog_before_normal.png",
           f"Load per pool at {HB:02d}:00 (delay only): all residential, all office and real mix.", width=11.5)

    # 5 ---------------------------------------------------------------------
    h1(doc, "5. After balancing")
    para(doc, f"**RRHs per pool (Figure 4).** With delay only, the pools have between {rc['delay']['min']:.0f} "
              f"and {rc['delay']['max']:.0f} RRHs; A gives {rc['A']['min']:.0f}-{rc['A']['max']:.0f} and B "
              f"{rc['B']['min']:.0f}-{rc['B']['max']:.0f}. The traffic at {HB:02d}:00 is balanced as well: its "
              f"standard deviation drops from {g(ld['delay']['std'])} to {g(ld['A']['std'])} Gbps (A) and "
              f"{g(ld['B']['std'])} Gbps (B). The corner pools cannot reach more than a few dozen RRHs, so a "
              f"perfect balance is not possible.")
    figure(doc, F / "2a_rrh_per_pool_normal.png", f"Number of RRHs per BBU pool, K = {kn}.", width=11.5)
    para(doc, f"**Hour of balancing (Figure 5).** If algorithm A is run at another hour, between "
              f"{min(ch[str(h)] for h in hrs)} and {max(ch[str(h)] for h in hrs)} RRHs "
              f"({min(ch[str(h)] for h in hrs) / nr:.0%}-{max(ch[str(h)] for h in hrs) / nr:.0%}) end in another "
              f"pool than at {HB:02d}:00 ({ch['8']} at 08:00, {ch['15']} at 15:00, {ch['21']} at 21:00). The "
              f"fronthaul cannot be re-wired every hour, so the {HB:02d}:00 assignment is the one adopted.")
    figure(doc, F / "2b_changes_by_hour_normal.png",
           f"RRHs assigned to another pool when algorithm A balances another hour instead of {HB:02d}:00.",
           width=11)
    para(doc, f"**All residential or all office (Figure 6).** After algorithm A the coefficient of variation is "
              f"{ha['res']['cv']:.0%} in both homogeneous cases, against {ha['real']['cv']:.0%} for the real mix: "
              f"with one profile only the peak traffic of each RRH matters, and the result is the same at any hour.")
    figure(doc, F / "2c_homog_after_normal.png",
           f"Algorithm A with all residential, all office and real mix: load at {HB:02d}:00 (left) and number of "
           f"RRHs (right) per pool.", width=16)
    para(doc, f"**Fronthaul distance (Figure 7).** With delay only the mean distance is {dk['delay']['mean']:.1f} "
              f"km. Balancing uses the whole allowed distance: {dk['A']['mean']:.1f} km (A) and "
              f"{dk['B']['mean']:.1f} km (B), with about a quarter of the links between 9 and 10 km, as in "
              f"[2, Fig. 4.3].")
    figure(doc, F / "2d_distance_hist_normal.png",
           "Share of RRHs per fronthaul distance band for the three strategies (as [2, Fig. 4.3]).", width=11.5)
    para(doc, f"**Average capacity (Figure 8).** Over 24 h, pool 1 needs {g(ac['delay']['max'])} Gbps on average "
              f"with delay only. Both algorithms reduce the standard deviation between pools from "
              f"{g(ac['delay']['std'])} to {g(ac['A']['std'])} Gbps (A) and {g(ac['B']['std'])} Gbps (B).")
    figure(doc, F / "2e_avg_capacity_normal.png",
           "Average capacity (24 h mean) per BBU pool for the three strategies (as [2, Fig. 4.4]).", width=11.5)

    # 6 ---------------------------------------------------------------------
    h1(doc, "6. Number of pools")
    rows = [["Case", "Strategy", "Load CV at " + f"{HB:02d}:00", "RRHs per pool (min-max)", "Mean distance [km]"]]
    for c in ("few", "normal", "many"):
        r = C[c]
        for k, lab in (("delay", "Delay only"), ("A", "A"), ("B", "B")):
            l = r["load_stats_balancing_hour"][k]; n = r["rrh_count_stats"][k]
            rows.append([f"{c.capitalize()} (K={r['K']})" if k == "delay" else "", lab, f"{l['cv']:.0%}",
                         f"{n['min']:.0f}-{n['max']:.0f}", f"{r['distance_km'][k]['mean']:.2f}"])
    table(doc, rows, "Comparison of the three numbers of pools.", widths=[3, 2.4, 3, 4, 3.2], size=9.5)
    para(doc, f"With **few pools** most RRHs have one possible pool, so the first iteration fixes almost "
              f"everything: A and B give the same result and the coefficient of variation stays at "
              f"{C['few']['load_stats_balancing_hour']['A']['cv']:.0%}. In the **normal** case balancing divides "
              f"it by four. With **too many pools** the balance is the best, but some pools serve a single RRH "
              f"with delay only and the mean link grows from {C['many']['distance_km']['delay']['mean']:.1f} to "
              f"{C['many']['distance_km']['A']['mean']:.1f} km.")

    # 7 ---------------------------------------------------------------------
    h1(doc, "7. Conclusions")
    para(doc, f"With delay only, the centre pool processes {ld['delay']['max'] / ld['delay']['mean']:.1f} times the "
              f"average load. Both algorithms spread the RRHs over all pools within {cfg.D_MAX_KM:.0f} km: A "
              f"balances the traffic best at the chosen hour, B is almost as good and does not depend on the hour. "
              f"The cost is a fronthaul about twice as long. The number of pools matters as much as the algorithm. "
              f"Next week we will add synthetic RRHs and prepare the 5G link budget.")

    h1(doc, "References")
    for ref in ("[1] Ministerio para la Transformacion Digital y de la Funcion Publica, \"Infoantenas - Niveles "
                "de exposicion\", https://geoportal.minetur.gob.es/VCTEL/vcne.do.",
                "[2] Master thesis on Cloud-RAN planning (T. M., 2016).",
                "[3] Project review: load balancing, MASTEAM Wireless and Radio Communication, EETAC-UPC, 2026."):
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(2)
        r = p.add_run(ref); r.font.size = Pt(9)

    path = OUT / "week2_report.docx"
    doc.save(path)
    print("written", path, "| figures:", fig_no[0], "tables:", tab_no[0])
    return path


def to_pdf(docx_path):
    pdf = docx_path.with_suffix(".pdf")
    ps = (f"$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
          f"$d = $w.Documents.Open('{docx_path}'); $d.SaveAs([ref]'{pdf}', [ref]17); $d.Close(); $w.Quit()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=180)
        print("written", pdf)
    except Exception as e:                                   # Word missing: keep the .docx only
        print("PDF export skipped:", e, file=sys.stderr)


if __name__ == "__main__":
    to_pdf(build())
