"""HTML pages for the WP3 dashboard. Server-rendered, no JavaScript beyond a theme toggle."""
from __future__ import annotations

from html import escape
from urllib.parse import urlencode

from . import charts, data
from .data import to_float

TITLE = "WP3 Trust Metrics Dashboard"

PAGES = [  # (key, label)
    ("overview", "Overview"),
    ("metrics", "Metric definitions"),
    ("distributions", "Score distributions"),
    ("runs", "Runs"),
    ("calibration", "Calibration"),
    ("data", "Data and checks"),
]
FILTERED_PAGES = {"overview", "distributions", "metric", "runs"}

BAND_STYLE = [  # status class, icon, in-fill text class
    ("good", "✓", "on-fill"),
    ("warn", "▲", "on-warn"),
    ("serious", "◆", "on-warn"),
    ("critical", "✕", "on-fill"),
]


class Raw(str):
    """Marks a string as already-safe HTML."""


def esc(v):
    return v if isinstance(v, Raw) else escape("" if v is None else str(v), quote=True)


def fmt(v, d=2, dash="—"):
    return dash if v is None else ("%." + str(d) + "f") % v


def pct(v, d=0):
    return "—" if v is None else ("%." + str(d) + "f%%") % (v * 100)


# ----------------------------------------------------------------------------------------
# routing helpers
# ----------------------------------------------------------------------------------------
class Router:
    """Builds links. mode 'server' -> /path?query ; mode 'export' -> static file names."""

    def __init__(self, mode="server"):
        self.mode = mode

    def href(self, page, filters=None, **extra):
        q = {}
        if self.mode == "server":
            if filters:
                q.update(filters.active())
            q.update({k: v for k, v in extra.items() if v not in (None, "")})
        if page == "metric":
            mid = extra.pop("id")
            q.pop("id", None)
            if self.mode == "export":
                return "metric-%s.html" % mid
            path = "/metric/%s" % mid
        elif self.mode == "export":
            path = "index.html" if page == "overview" else "%s.html" % page
        else:
            path = "/" if page == "overview" else "/%s" % page
        if self.mode == "server" and q:
            return path + "?" + urlencode(q)
        return path


# ----------------------------------------------------------------------------------------
# style
# ----------------------------------------------------------------------------------------
def _css():
    light = charts._vars(charts.CHART_CSS_LIGHT)
    dark = charts._vars(charts.CHART_CSS_DARK)
    css = """
:root{%(light)s;--page:#f9f9f7;--border:rgba(11,11,11,.10);--heat-lo:#cde2fb;--heat-hi:#1c5cab;
 --good-ink:#006300;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){%(dark)s;--page:#0d0d0d;
 --border:rgba(255,255,255,.10);--heat-lo:#0d366b;--heat-hi:#5598e7;--good-ink:#0ca30c;color-scheme:dark}}
:root[data-theme="dark"]{%(dark)s;--page:#0d0d0d;--border:rgba(255,255,255,.10);
 --heat-lo:#0d366b;--heat-hi:#5598e7;--good-ink:#0ca30c;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--s1)} a:focus-visible,button:focus-visible,select:focus-visible,summary:focus-visible{outline:2px solid var(--s1);outline-offset:2px}
header.top{background:var(--surface);border-bottom:1px solid var(--border);padding:14px 16px 0}
.wrap{max-width:1180px;margin:0 auto}
.brand{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 14px;justify-content:space-between}
.brand h1{font-size:19px;margin:0;font-weight:650}
.brand .sub{color:var(--ink2);font-size:13px}
nav.tabs{display:flex;flex-wrap:wrap;gap:2px;margin-top:10px}
nav.tabs a{padding:8px 12px;text-decoration:none;color:var(--ink2);border-bottom:2px solid transparent;font-size:14px}
nav.tabs a[aria-current="page"]{color:var(--ink);border-bottom-color:var(--s1);font-weight:600}
nav.tabs a:hover{color:var(--ink)}
main{padding:18px 16px 40px}
h2{font-size:17px;margin:26px 0 4px;font-weight:650} h3{font-size:15px;margin:0 0 4px;font-weight:650}
p.lead{color:var(--ink2);margin:2px 0 12px;max-width:80ch} .muted{color:var(--muted)} .ink2{color:var(--ink2)}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px;min-width:0}
.grid{display:grid;gap:14px} .g2{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(310px,1fr))} .g4{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.tile .label{color:var(--ink2);font-size:13px} .tile .value{font-size:30px;font-weight:650;line-height:1.15;margin:2px 0}
.tile .note{color:var(--ink2);font-size:13px}
.chart{overflow-x:auto} .chart svg{display:block;max-width:100%;height:auto}
.badge{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;padding:1px 8px 1px 6px;border-radius:99px;
 border:1px solid var(--border);white-space:nowrap}
.badge i{font-style:normal;display:inline-block;width:14px;height:14px;border-radius:50%;line-height:14px;text-align:center;font-size:9px;font-weight:700;color:#fff}
.i-good{background:var(--good)} .i-warn{background:var(--warn);color:#0b0b0b!important} .i-serious{background:var(--serious);color:#0b0b0b!important}
.i-critical{background:var(--critical)} .i-gray{background:var(--muted)}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin:8px 0 0;font-size:13px;color:var(--ink2)}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:baseline}
.sw.s1{background:var(--s1)} .sw.s2{background:var(--s2)} .sw.bad{background:var(--critical)}
form.filters{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:end;margin:0 0 14px;padding:10px 12px;background:var(--surface);
 border:1px solid var(--border);border-radius:10px}
form.filters label{display:flex;flex-direction:column;font-size:12.5px;color:var(--ink2);gap:2px}
select,button,.btn{font:inherit;font-size:14px;padding:5px 8px;border:1px solid var(--axis);border-radius:6px;background:var(--surface);color:var(--ink)}
button{cursor:pointer} .btn{text-decoration:none;display:inline-block}
.tablewrap{overflow-x:auto;border:1px solid var(--border);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid var(--grid);vertical-align:top}
th{font-weight:600;color:var(--ink2);background:var(--surface);position:sticky;top:0;white-space:nowrap}
td a{white-space:nowrap}
th a{color:inherit;text-decoration:none} th a:hover{text-decoration:underline}
tr:last-child td{border-bottom:0} td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.mono,.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12.5px}
.heat{--v:0;background:color-mix(in srgb,var(--heat-hi) calc(var(--v)*100%),var(--heat-lo));color:var(--ink);text-align:right;font-variant-numeric:tabular-nums}
.heat.hot{color:#fff} .heat.na{background:transparent;color:var(--muted)}
.mk{font-weight:700;margin-left:4px;color:var(--critical)} .mk.ok{color:var(--good-ink)}
tr.differs td{background:color-mix(in srgb,var(--critical) 7%,transparent)}
.chip{display:inline-block;font-size:12px;padding:0 7px;border:1px solid var(--axis);border-radius:99px;margin:1px 3px 1px 0;white-space:nowrap}
.notice{border:1px solid var(--axis);border-left:4px solid var(--warn);background:var(--surface);padding:8px 12px;border-radius:6px;margin:0 0 14px;font-size:14px}
.notice.ok{border-left-color:var(--good)} .notice.err{border-left-color:var(--critical)}
dl.defs{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;margin:0} dl.defs dt{color:var(--ink2)} dl.defs dd{margin:0;min-width:0;overflow-wrap:anywhere}
ul.plain{margin:4px 0;padding-left:20px} details{margin-top:10px} summary{cursor:pointer;color:var(--ink2);font-size:14px}
.chipset .chip b{font-weight:600}
footer{color:var(--muted);font-size:12.5px;padding:0 16px 30px} .toggle{font-size:13px;padding:3px 9px}
@media (max-width:560px){.tile .value{font-size:26px} dl.defs{grid-template-columns:1fr}}
@media print{header.top nav,.toggle,form.filters{display:none}}
"""
    return css.replace("%(light)s", light).replace("%(dark)s", dark) + charts.CHART_RULES


THEME_JS = """
(function(){var r=document.documentElement,k='wp3-dash-theme';
try{var s=localStorage.getItem(k);if(s==='light'||s==='dark')r.setAttribute('data-theme',s);}catch(e){}
var b=document.getElementById('theme');if(!b)return;
b.addEventListener('click',function(){var cur=r.getAttribute('data-theme');
var dark=cur?cur==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;
var n=dark?'light':'dark';r.setAttribute('data-theme',n);try{localStorage.setItem(k,n);}catch(e){}});})();
"""


# ----------------------------------------------------------------------------------------
# small components
# ----------------------------------------------------------------------------------------
def band_style(ctx, level):
    names = ctx.defs.band_names
    if level in names:
        i = names.index(level)
        if i < len(BAND_STYLE) and len(names) <= len(BAND_STYLE):
            return BAND_STYLE[i]
    return ("gray", "–", "on-fill")


def badge(ctx, level):
    cls, icon, _ = band_style(ctx, level)
    return Raw('<span class="badge"><i class="i-%s" aria-hidden="true">%s</i>%s</span>' % (
        cls, icon, esc(level)))


def table(headers, rows, num_cols=(), wrap=True, cls=""):
    """headers: list of str; rows: list of lists of (str | Raw). num_cols: indexes right-aligned."""
    h = "".join('<th%s>%s</th>' % (' class="num"' if i in num_cols else "", esc(c))
                for i, c in enumerate(headers))
    body = []
    for row in rows:
        tr_cls = ""
        if isinstance(row, tuple) and len(row) == 2 and isinstance(row[0], str) and isinstance(row[1], list):
            tr_cls, row = row
        cells = "".join('<td%s>%s</td>' % (
            ' class="num"' if i in num_cols else (' style="white-space:nowrap"' if (
                not isinstance(c, Raw) and len(str(c)) <= 14) else ""), esc(c))
            for i, c in enumerate(row))
        body.append('<tr%s>%s</tr>' % (' class="%s"' % tr_cls if tr_cls else "", cells))
    t = '<table%s><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (
        ' class="%s"' % cls if cls else "", h, "".join(body))
    return Raw('<div class="tablewrap">%s</div>' % t if wrap else t)


def heat_cell(v, title=""):
    if v is None:
        return Raw('<td class="heat na" title="not measured">—</td>')
    hot = " hot" if v > 0.55 else ""
    return Raw('<td class="heat%s" style="--v:%.3f" title="%s">%s</td>' % (
        hot, max(0.0, min(1.0, v)), esc(title), fmt(v)))


def tile(label, value, note="", extra=""):
    return Raw('<div class="panel tile"><div class="label">%s</div><div class="value">%s</div>'
               '<div class="note">%s</div>%s</div>' % (esc(label), esc(value), esc(note), extra))


def chart_panel(title, subtitle, svg, legend="", extra=""):
    return Raw('<div class="panel"><h3>%s</h3><div class="ink2" style="font-size:13px">%s</div>'
               '<div class="chart" style="margin-top:8px">%s</div>%s%s</div>' % (
                   esc(title), esc(subtitle), svg, legend, extra))


def risk_chips(ids):
    return Raw("".join('<span class="chip" title="%s">%s</span>' % (
        esc(data.RISK_NAMES.get(i, "")), esc(i)) for i in ids))


def filters_form(ctx, router, page, filters, **hidden):
    if router.mode == "export":
        return ""
    opts = data.filter_options(ctx.runs)

    def sel(name, key, current, label):
        o = "".join('<option value="%s"%s>%s</option>' % (
            esc(v), " selected" if v == current else "", esc(v)) for v in opts[key])
        return '<label>%s<select name="%s" onchange="this.form.submit()"><option value="">All</option>%s</select></label>' % (
            label, name, o)
    hid = "".join('<input type="hidden" name="%s" value="%s">' % (esc(k), esc(v)) for k, v in hidden.items())
    action = router.href("metric", id=hidden.get("id")) if page == "metric" else router.href(page)
    action = action.split("?")[0]
    return Raw('<form class="filters" method="get" action="%s" aria-label="Filters">%s%s%s%s'
               '<button type="submit">Apply</button><a class="btn" href="%s">Reset</a></form>' % (
                   esc(action), hid, sel("agent", "agent", filters.agent, "Agent"),
                   sel("workflow", "workflow", filters.workflow, "Workflow"),
                   sel("type", "type", filters.scenario_type, "Scenario type"), esc(action)))


# ----------------------------------------------------------------------------------------
# layout
# ----------------------------------------------------------------------------------------
def layout(ctx, router, active, title, body, filters=None):
    defs = ctx.defs
    nav = []
    for key, label in PAGES:
        cur = ' aria-current="page"' if key == active else ""
        nav.append('<a href="%s"%s>%s</a>' % (
            esc(router.href(key, filters if key in FILTERED_PAGES else None)), cur, esc(label)))
    notices = ""
    if ctx.warnings:
        notices += '<div class="notice err">%s</div>' % "<br>".join(esc(w) for w in ctx.warnings)
    ck = ctx.checks
    if ck.get("score_cells_mismatch") or ck.get("overall_mismatch"):
        notices += ('<div class="notice err"><b>Data check failed.</b> %d score cell(s) and %d overall score(s) in '
                    'the scored file differ from a recomputation using the definitions file. '
                    'See <a href="%s">Data and checks</a>.</div>') % (
            ck["score_cells_mismatch"], ck["overall_mismatch"], esc(router.href("data")))
    if getattr(ctx, "label", ""):
        notices = '<div class="notice"><b>Data shown:</b> %s</div>' % esc(ctx.label) + notices
    sub = "Metric definitions v%s (%s) · %d scored run%s" % (
        defs.version, defs.status, len(ctx.runs), "" if len(ctx.runs) == 1 else "s")
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s · %s</title><style>%s</style></head><body>'
            '<header class="top"><div class="wrap"><div class="brand"><h1>%s</h1>'
            '<span class="sub">%s <button id="theme" class="toggle" type="button" '
            'aria-label="Switch light or dark theme">Theme</button></span></div>'
            '<nav class="tabs" aria-label="Pages">%s</nav></div></header>'
            '<main><div class="wrap">%s%s</div></main>'
            '<footer><div class="wrap">Reads %s, the scored runs file and the calibration results. '
            'Scores are read as written by the scoring engine; this dashboard does not rescore.</div></footer>'
            '<script>%s</script></body></html>') % (
        esc(title), TITLE, _css(), TITLE, esc(sub), "".join(nav), notices, body,
        esc(_basename(defs.path)), THEME_JS)


def _basename(p):
    import os
    return os.path.basename(p or "")


# ----------------------------------------------------------------------------------------
# pages
# ----------------------------------------------------------------------------------------
def page_overview(ctx, router, filters):
    defs = ctx.defs
    runs = data.apply_filters(ctx.runs, filters)
    f_form = filters_form(ctx, router, "overview", filters)
    if not runs:
        return layout(ctx, router, "overview", "Overview",
                      f_form + '<div class="notice">No runs match these filters.</div>', filters)
    overall = [r.overall for r in runs]
    m_overall = data.mean(overall)
    lows = [r for r in runs if r.overall is not None]
    low = min(lows, key=lambda r: r.overall) if lows else None
    cells = fails = 0
    for m in defs.metrics:
        for r in runs:
            s = r.scores.get(m.id)
            if s is not None:
                cells += 1
                if not data.passes(m, s):
                    fails += 1
    agents = sorted({r.agent for r in runs})
    tiles = [
        tile("Scored runs", str(len(runs)), "%d agent configuration%s" % (len(agents), "" if len(agents) == 1 else "s")),
        tile("Mean overall trust score", fmt(m_overall, 3), "", extra=str(badge(ctx, defs.band_for(m_overall)))),
        tile("Lowest run", fmt(low.overall, 3) if low else "—",
             ("%s · %s" % (low.run_id, low.scenario_id)) if low else ""),
        tile("Metric results below threshold", "%d of %d" % (fails, cells),
             "measured metric results only; not-measured results are left out"),
    ]
    # band distribution
    lc = data.level_counts(runs, defs)
    segs = []
    for name, n in lc:
        cls, icon, txt = band_style(ctx, name)
        segs.append({"label": name, "count": n, "cls": "st-" + cls, "text_cls": txt})
    legend = '<div class="legend">%s</div>' % "".join(
        "<span>%s <b>%d</b></span>" % (badge(ctx, n), c) for n, c in lc)
    band_panel = chart_panel(
        "Runs by risk band", "Band of each run's overall trust score",
        charts.stacked_bar(segs, "Runs by risk band"), legend)

    def means_chart(title, sub, groups):
        rows = [{"label": k, "value": m, "text": "%s  (n=%d)" % (fmt(m), n),
                 "title": "%s: mean overall %s over %d run%s" % (k, fmt(m, 3), n, "" if n == 1 else "s")}
                for k, m, n in groups]
        return chart_panel(title, sub, charts.hbar(rows, title))

    ag = data.group_means(runs, "agent")
    ag_panel = means_chart("Mean overall trust score by agent", "0 = lowest, 1 = highest", ag)
    wf_panel = means_chart("By workflow", "Mean overall trust score", data.group_means(runs, "workflow"))
    ty_panel = means_chart("By scenario type", "Mean overall trust score", data.group_means(runs, "scenario_type"))
    # pass rate per metric
    rows = []
    for m in defs.metrics:
        st = data.metric_stats(m, runs)
        if st.pass_rate is None:
            rows.append({"label": m.id, "value": None, "text": "not measured in any run"})
        else:
            rows.append({"label": "%s %s" % (m.id, m.name.split()[0]), "value": st.pass_rate,
                         "text": "%s  (%d of %d)" % (pct(st.pass_rate), st.n_pass, st.n_measured),
                         "title": "%s: %d of %d measured runs meet the threshold (%s)" % (
                             m.id, st.n_pass, st.n_measured, m.threshold_rule)})
    pr_panel = chart_panel("Share of runs meeting each metric's threshold",
                           "Only runs where the metric was measured", charts.hbar(rows, "Pass rate per metric", width=600, label_w=190))
    # agent table (heat cells are real <td>s, so the table is built by hand)
    hdr = ["Agent", "Runs", "Mean overall", "Band"] + [m.id for m in defs.metrics]
    th = "".join("<th%s>%s</th>" % (' class="num"' if i in (1, 2) or i >= 4 else "", esc(h)) for i, h in enumerate(hdr))
    body_rows = []
    for a in data.agent_summary(runs, defs):
        tds = ("<td>%s</td><td class=\"num\">%d</td><td class=\"num\">%s</td><td>%s</td>" % (
            esc(a["agent"]), a["n"], fmt(a["mean"], 3), badge(ctx, a["level"])))
        tds += "".join(str(heat_cell(a["metric_means"][m.id],
                                     "%s: mean %s over %d measured run(s)" % (
                                         m.id, fmt(a["metric_means"][m.id], 3), a["metric_counts"][m.id])))
                       for m in defs.metrics)
        body_rows.append("<tr>%s</tr>" % tds)
    agent_table = Raw('<div class="tablewrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (
        th, "".join(body_rows)))
    body = (f_form +
            '<div class="grid g4">%s</div>' % "".join(str(t) for t in tiles) +
            '<div class="grid g2" style="margin-top:14px">%s%s</div>' % (band_panel, ag_panel) +
            '<div class="grid g2" style="margin-top:14px">%s%s</div>' % (wf_panel, ty_panel) +
            '<div style="margin-top:14px">%s</div>' % pr_panel +
            '<h2>Agent summary</h2><p class="lead">Mean metric score per agent. Darker = higher (safer). '
            '— means the metric was not measured in any of that agent\'s runs.</p>' + str(agent_table))
    return layout(ctx, router, "overview", "Overview", body, filters)


def page_metrics(ctx, router):
    defs = ctx.defs
    rows = []
    for m in defs.metrics:
        rows.append([
            Raw('<a href="%s"><b>%s</b></a>' % (esc(router.href("metric", id=m.id)), esc(m.id))),
            m.name, fmt(m.weight), Raw("%s<br><span class=\"muted\">%s</span>" % (esc(fmt(m.threshold)), esc(m.threshold_rule))),
            Raw('<span class="mono">%s</span>' % esc(m.formula)), risk_chips(m.risk_ids)])
    wrows = [{"label": "%s %s" % (m.id, m.name.split()[0]), "value": m.weight, "text": fmt(m.weight),
              "title": "%s weight %s" % (m.id, fmt(m.weight))} for m in defs.metrics]
    wchart = charts.hbar(wrows, "Metric weights in the overall score", vmax=max(0.3, max(m.weight for m in defs.metrics)),
                         label_w=190)
    brow = [[badge(ctx, b["name"]), fmt(b["min"]), fmt(b["max"])] for b in defs.bands]
    risk_rows = []
    for rid, name in data.RISK_NAMES.items():
        linked = [m.id for m in defs.metrics if rid in m.risk_ids]
        risk_rows.append([rid, name, Raw(" ".join('<span class="chip">%s</span>' % esc(i) for i in linked)
                                         or '<span class="muted">none</span>')])
    body = (
        '<h2 style="margin-top:0">Metric definitions</h2>'
        '<p class="lead">Read from <span class="mono">%s</span> (version %s, %s). Weights, thresholds, bands, formulas and '
        'linked risks all come from that file; change a value there and this page and the scoring engine follow.</p>' % (
            esc(_basename(defs.path)), esc(defs.version), esc(defs.status)) +
        str(table(["ID", "Metric", "Weight", "Threshold", "Formula", "Linked risks (WP1)"], rows, num_cols=(2,))) +
        '<div class="grid g2" style="margin-top:14px">' +
        str(chart_panel("Weights in the overall score", "Weights of the measured metrics are rescaled to sum to 1 for each run", wchart)) +
        '<div class="panel"><h3>Overall score</h3><p class="mono" style="margin:6px 0">%s</p>'
        '<p class="ink2" style="margin:6px 0"><b>No-data rule:</b> %s</p>'
        '<h3 style="margin-top:12px">Risk bands</h3>%s'
        '<p class="muted" style="font-size:13px;margin:6px 0 0">%s</p></div></div>' % (
            esc(defs.overall_formula), esc(defs.no_data_behaviour),
            table(["Band", "From", "To"], brow, num_cols=(1, 2)), esc(defs.band_status)) +
        '<h2>Linked WP1 threats</h2><p class="lead">Which metrics speak to each WP1 threat category.</p>' +
        str(table(["ID", "Threat", "Metrics"], risk_rows)))
    if defs.change_control:
        body += '<h2>Change control</h2><ul class="plain">%s</ul>' % "".join(
            "<li>%s</li>" % esc(c) for c in defs.change_control)
    return layout(ctx, router, "metrics", "Metric definitions", body)


def _hist_svg(m, st, width=300, height=150):
    passing = [data.bin_passes(m, i) for i in range(len(st.bins))]
    labels = [data.bin_label(i) for i in range(len(st.bins))]
    return charts.histogram(st.bins, m.threshold, passing,
                            "Score distribution of %s %s" % (m.id, m.name), width, height, labels)


HIST_LEGEND = ('<div class="legend"><span><span class="sw s1"></span>meets threshold</span>'
               '<span><span class="sw bad"></span>below threshold (✕)</span>'
               '<span>dashed line = threshold</span></div>')


def page_distributions(ctx, router, filters):
    defs = ctx.defs
    runs = data.apply_filters(ctx.runs, filters)
    f_form = filters_form(ctx, router, "distributions", filters)
    if not runs:
        return layout(ctx, router, "distributions", "Score distributions",
                      f_form + '<div class="notice">No runs match these filters.</div>', filters)
    cards, tab_rows = [], []
    stats = {m.id: data.metric_stats(m, runs) for m in defs.metrics}
    for m in defs.metrics:
        st = stats[m.id]
        meta = ('<div class="ink2" style="font-size:13px;margin-top:6px">%d measured · %d not measured · '
                'mean %s · median %s · %s meet threshold</div>' % (
                    st.n_measured, st.n_not_measured, fmt(st.mean), fmt(st.median), pct(st.pass_rate)))
        if st.n_measured:
            svg = _hist_svg(m, st)
        else:
            svg = '<p class="muted" style="margin:30px 0">Not measured in any of these runs.</p>'
        link = '<div style="margin-top:6px;font-size:13px"><a href="%s">Details for %s →</a></div>' % (
            esc(router.href("metric", filters, id=m.id)), esc(m.id))
        cards.append(chart_panel("%s · %s" % (m.id, m.name),
                                 "weight %s · threshold %s" % (fmt(m.weight), m.threshold_rule or fmt(m.threshold)),
                                 svg, "", meta + link))
    # heat table agent x metric
    th = "<th>Agent</th><th class=\"num\">Runs</th>" + "".join('<th class="num">%s</th>' % esc(m.id) for m in defs.metrics)
    trs = []
    for a in data.agent_summary(runs, defs):
        tds = "<td>%s</td><td class=\"num\">%d</td>" % (esc(a["agent"]), a["n"])
        tds += "".join(str(heat_cell(a["metric_means"][m.id], "%s mean over %d run(s)" % (m.id, a["metric_counts"][m.id])))
                       for m in defs.metrics)
        trs.append("<tr>%s</tr>" % tds)
    heat = '<div class="tablewrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, "".join(trs))
    # table view of the histograms
    trows = []
    for i in range(data.N_BINS + 1):
        trows.append([data.bin_label(i)] + [stats[m.id].bins[i] for m in defs.metrics])
    tv = table(["Score range"] + [m.id for m in defs.metrics], trows, num_cols=tuple(range(1, len(defs.metrics) + 1)))
    body = (f_form + '<h2 style="margin-top:0">Score distributions per metric</h2>'
            '<p class="lead">Each bar counts runs whose score falls in a 0.05 band; the last bar is runs scoring exactly 1.00. '
            'Runs where a metric was not measured are not in the chart.</p>' + HIST_LEGEND +
            '<div class="grid g3" style="margin-top:10px">%s</div>' % "".join(str(c) for c in cards) +
            '<h2>Mean score per agent and metric</h2>' + heat +
            '<details><summary>Table view of the histograms</summary>%s</details>' % tv)
    return layout(ctx, router, "distributions", "Score distributions", body, filters)


def page_metric(ctx, router, filters, metric_id):
    defs = ctx.defs
    m = defs.metric(metric_id)
    if m is None:
        return None
    runs = data.apply_filters(ctx.runs, filters)
    f_form = filters_form(ctx, router, "metric", filters, id=m.id)
    st = data.metric_stats(m, runs)
    dl = [("Description", m.description), ("Formula", Raw('<span class="mono">%s</span>' % esc(m.formula))),
          ("Weight", fmt(m.weight)), ("Threshold", "%s (%s)" % (fmt(m.threshold), m.threshold_rule)),
          ("Scoring kind", "%s: numerator = %s ; denominator = %s" % (
              m.kind, " + ".join(m.numerator), m.denominator)),
          ("Linked WP1 risks", risk_chips(m.risk_ids)),
          ("Risk mapping note", m.risk_mapping_note)]
    deflist = "".join("<dt>%s</dt><dd>%s</dd>" % (esc(k), esc(v)) for k, v in dl if v not in ("", None))
    inputs = "".join("<li><span class=\"mono\">%s</span>: %s</li>" % (esc(k), esc(v)) for k, v in m.inputs.items())
    edge = "".join("<li>%s</li>" % esc(e) for e in m.edge_cases)
    srcs = "".join("<li>%s</li>" % esc(s) for s in m.run_log_sources)
    refs = "".join("<li>%s</li>" % esc(s) for s in m.references)
    left = ('<div class="panel"><h3>%s · %s</h3><dl class="defs" style="margin-top:8px">%s</dl>'
            '<h3 style="margin-top:14px">Inputs</h3><ul class="plain">%s</ul>'
            '<h3 style="margin-top:10px">Edge cases</h3><ul class="plain">%s</ul>'
            '<h3 style="margin-top:10px">Run-log sources</h3><ul class="plain">%s</ul>'
            '<h3 style="margin-top:10px">References</h3><ul class="plain">%s</ul></div>') % (
        esc(m.id), esc(m.name), deflist, inputs, edge, srcs, refs)
    if st.n_measured:
        svg = _hist_svg(m, st, 420, 190)
    else:
        svg = '<p class="muted">Not measured in any of these runs.</p>'
    right = str(chart_panel("Score distribution", "%d measured · %d not measured · mean %s · median %s · min %s · %s meet threshold" % (
        st.n_measured, st.n_not_measured, fmt(st.mean), fmt(st.median), fmt(st.minimum), pct(st.pass_rate)), svg, HIST_LEGEND))
    # per agent
    arows = []
    for agent in sorted({r.agent for r in runs}):
        s2 = data.metric_stats(m, [r for r in runs if r.agent == agent])
        arows.append([agent, s2.n_measured, s2.n_not_measured, fmt(s2.mean), pct(s2.pass_rate)])
    # per scenario
    srows = []
    for r in data.scenario_rows(m, runs):
        srows.append([r["scenario"], r["workflow"], r["type"], r["runs"], r["measured"], fmt(r["mean"]),
                      "%g / %g" % (r["numerator"], r["denominator"])])
    # runs below threshold
    below = [r for r in runs if r.scores.get(m.id) is not None and not data.passes(m, r.scores[m.id])]
    brows = [[r.run_id, r.scenario_id, r.agent, fmt(r.scores[m.id], 3)] +
             [("%g" % r.counts[f]) if r.counts.get(f) is not None else "—" for f in m.count_fields]
             for r in sorted(below, key=lambda r: r.scores[m.id])]
    others = [x for x in defs.metrics if x.id != m.id]
    switch = " ".join('<a class="chip" href="%s">%s</a>' % (esc(router.href("metric", filters, id=x.id)), esc(x.id))
                      for x in defs.metrics)
    body = (f_form + '<p style="margin:0 0 10px"><a href="%s">← Score distributions</a> &nbsp; Metrics: %s</p>' % (
        esc(router.href("distributions", filters)), switch) +
        '<div class="grid g2">%s<div>%s</div></div>' % (left, right) +
        '<h2>By agent</h2>' + str(table(["Agent", "Measured", "Not measured", "Mean score", "Meet threshold"],
                                        arows, num_cols=(1, 2, 3, 4))) +
        '<h2>By scenario</h2><p class="lead">The last column sums the counts behind the score: %s / %s over the runs of the scenario.</p>' % (
            esc(" + ".join(m.numerator)), esc(m.denominator)) +
        str(table(["Scenario", "Workflow", "Type", "Runs", "Measured", "Mean score", "Counts"], srows, num_cols=(3, 4, 5, 6))) +
        '<h2>Runs below threshold (%d)</h2>' % len(below) +
        (str(table(["Run", "Scenario", "Agent", "Score"] + m.count_fields, brows, num_cols=tuple(range(3, 4 + len(m.count_fields)))))
         if brows else '<p class="lead">No measured run is below the threshold.</p>'))
    return layout(ctx, router, "distributions", "%s %s" % (m.id, m.name), body, filters)


RUN_COLS = [("run_id", "Run"), ("scenario_id", "Scenario"), ("agent", "Agent"), ("workflow", "Workflow"),
            ("scenario_type", "Type")]


def page_runs(ctx, router, filters, sort="", direction="asc", limit=500):
    defs = ctx.defs
    runs = data.apply_filters(ctx.runs, filters)
    f_form = filters_form(ctx, router, "runs", filters)
    keys = {k for k, _ in RUN_COLS} | {"overall"} | set(defs.ids)
    if sort not in keys:
        sort = ""
    if sort:
        def keyf(r):
            if sort in defs.ids:
                v = r.scores.get(sort)
            elif sort == "overall":
                v = r.overall
            else:
                v = getattr(r, sort)
            return (v is None, v if v is not None else 0)
        runs = sorted(runs, key=keyf, reverse=(direction == "desc"))
        # keep not-measured at the end whichever way we sort
        runs = [r for r in runs if keyf(r)[0] is False] + [r for r in runs if keyf(r)[0] is True]

    def head(key, label, num=False):
        nd = "desc" if (sort == key and direction == "asc") else "asc"
        arrow = (" ▲" if direction == "asc" else " ▼") if sort == key else ""
        href = router.href("runs", filters, sort=key, dir=nd) if router.mode == "server" else ""
        inner = '<a href="%s">%s%s</a>' % (esc(href), esc(label), arrow) if href else esc(label)
        return '<th%s>%s</th>' % (' class="num"' if num else "", inner)
    th = "".join(head(k, l) for k, l in RUN_COLS) + "".join(head(m.id, m.id, True) for m in defs.metrics) + \
        head("overall", "Overall", True) + "<th>Band</th>"
    rows = []
    for r in runs[:limit]:
        tds = "".join("<td>%s</td>" % esc(getattr(r, k)) for k, _ in RUN_COLS)
        for m in defs.metrics:
            s = r.scores.get(m.id)
            if s is None:
                tds += '<td class="num muted" title="not measured">—</td>'
            elif data.passes(m, s):
                tds += '<td class="num">%s</td>' % fmt(s)
            else:
                tds += '<td class="num">%s<span class="mk" title="below threshold %s" aria-label="below threshold">✕</span></td>' % (
                    fmt(s), fmt(m.threshold))
        tds += '<td class="num"><b>%s</b></td><td>%s</td>' % (fmt(r.overall, 3), badge(ctx, r.level))
        rows.append("<tr>%s</tr>" % tds)
    more = ('<p class="muted">Showing the first %d of %d runs.</p>' % (limit, len(runs))) if len(runs) > limit else ""
    body = (f_form + '<h2 style="margin-top:0">Runs (%d)</h2><p class="lead">One row per scored run. ✕ marks a score below that '
            'metric\'s threshold; — means not measured. Click a column heading to sort.</p>' % len(runs) +
            '<div class="tablewrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>%s' % (
                th, "".join(rows), more))
    return layout(ctx, router, "runs", "Runs", body, filters)


# ----------------------------------------------------------------------------------------
# calibration
# ----------------------------------------------------------------------------------------
def page_calibration(ctx, router):
    cal = ctx.calibration
    defs = ctx.defs
    if not cal.get("found"):
        body = ('<h2 style="margin-top:0">Calibration results</h2><div class="notice">No calibration files were found in '
                '<span class="mono">%s</span>. Point the dashboard at the <span class="mono">results</span> folder of the '
                'calibration package with <span class="mono">--calibration</span>.</div>' % esc(cal.get("dir") or ""))
        return layout(ctx, router, "calibration", "Calibration", body)
    summ = data.cal_summary(cal)
    tiles = []
    if "pack" in summ:
        p = summ["pack"]
        tiles.append(tile("Test pack: results agreeing with hand labels", "%d of %d" % (p["agree"], p["cells"]),
                          "metric results where both sides measured; %d false alarms, %d misses" % (p["FP"], p["FN"])))
    if "probes" in summ:
        p = summ["probes"]
        tiles.append(tile("Probes: results agreeing with hand labels", "%d of %d" % (p["agree"], p["cells"]),
                          "%d false alarms, %d misses (probes aim at the weak points)" % (p["FP"], p["FN"])))
    if "agreement" in summ:
        a = summ["agreement"]
        tiles.append(tile("Overall band agrees with hand-computed band", "%d of %d" % (a["band_agree"], a["runs"]),
                          "test-pack runs; largest score difference %s" % fmt(a["max_abs_diff"], 3)))
    if "probes_table" in summ:
        p = summ["probes_table"]
        tiles.append(tile("Probe runs with the same trust decision", "%d of %d" % (p["decision_same"], p["n"]),
                          "%d of %d had exactly the same counts as the hand labels" % (p["counts_match"], p["n"])))
    body = ['<h2 style="margin-top:0">Calibration results</h2><p class="lead">How the scoring engine\'s output compares with hand-labelled '
            'ground truth on the test pack and on targeted probes. A "flag" means a metric score below its threshold. '
            'Read together with the calibration and validation report.</p>',
            '<div class="grid g4">%s</div>' % "".join(str(t) for t in tiles)]
    res = cal.get("results")
    if res:
        by = {}
        for r in res:
            by.setdefault(r["dataset"], {})[r["metric_id"]] = r
        order = [m.id for m in defs.metrics]

        def groups(field):
            gs = []
            for mid in order:
                bars = []
                for ds in ("pack", "probes"):
                    r = by.get(ds, {}).get(mid)
                    v = to_float(r.get(field)) if r else None
                    if r is None:
                        txt = "n/a"
                    elif v is None:
                        txt = "undefined (no flags)" if field == "precision" else "undefined"
                    else:
                        txt = fmt(v)
                    bars.append({"value": v, "text": txt, "title": "%s on %s: %s %s" % (mid, ds, field, txt)})
                gs.append({"label": mid, "bars": bars})
            return gs
        leg = ('<div class="legend"><span><span class="sw s1"></span>test pack</span>'
               '<span><span class="sw s2"></span>probes</span></div>')
        body.append('<div class="grid g2" style="margin-top:14px">%s%s</div>' % (
            chart_panel("Precision per metric", "Of the runs the engine flagged, the share that really should be flagged",
                        charts.grouped_hbar(groups("precision"), ["pack", "probes"], "Precision per metric", width=520, label_w=70), leg),
            chart_panel("Recall per metric", "Of the runs that should be flagged, the share the engine flagged",
                        charts.grouped_hbar(groups("recall"), ["pack", "probes"], "Recall per metric", width=520, label_w=70), leg)))
        rows = []
        for r in res:
            rows.append([r["dataset"], r["metric_id"], r["cells_both_measured"], r["TP"], r["FP"], r["FN"], r["TN"],
                         "%s / %s" % (r["engine_unmeasured_truth_flag"], r["engine_unmeasured_truth_pass"]),
                         r["engine_extra"], fmt(to_float(r["precision"])), fmt(to_float(r["recall"])),
                         fmt(to_float(r["mean_abs_score_error"]), 3), "%s of %s" % (r["count_fields_differing"], r["count_fields_compared"])])
        body.append('<h2>Confusion counts per metric</h2><p class="lead">TP = both flag, FP = engine flags only, FN = hand label flags only, '
                    'TN = neither. "Engine not measured" shows runs the engine left unmeasured where the hand label flags / passes. '
                    '"Engine extra" = engine measured where the hand label did not.</p>' +
                    str(table(["Data", "Metric", "Both measured", "TP", "FP", "FN", "TN", "Engine not measured (flag / pass)",
                               "Engine extra", "Precision", "Recall", "Mean abs score error", "Counts differing"],
                              rows, num_cols=tuple(range(2, 13)))))
    th_rows = cal.get("thresholds")
    if th_rows:
        by_metric = {}
        for r in th_rows:
            by_metric.setdefault(r["metric_id"], []).append(r)
        rows = []
        for mid in [m.id for m in defs.metrics if m.id in by_metric]:
            chips = []
            for r in sorted(by_metric[mid], key=lambda r: float(r["threshold_tested"])):
                chosen = r.get("is_chosen_threshold") == "yes"
                chips.append('<span class="chip%s" title="%s runs would change decision against the chosen threshold">'
                             '<b>%s</b>%s &rarr; %s pass</span>' % (
                                 "" if not chosen else '" style="border-color:var(--s1);border-width:2px',
                                 esc(r["runs_changing_decision_vs_chosen"]), esc("%.2f" % float(r["threshold_tested"])),
                                 " (chosen)" if chosen else "", pct(to_float(r["pass_rate"]))))
            rows.append([mid, Raw("".join(chips)), by_metric[mid][0]["runs_measured"],
                         max(int(r["runs_changing_decision_vs_chosen"]) for r in by_metric[mid])])
        body.append('<h2>Threshold sensitivity</h2><p class="lead">Share of measured test-pack runs passing at nearby thresholds. '
                    'The last column is the most runs whose pass/fail decision changes at any tested threshold.</p>' +
                    str(table(["Metric", "Threshold → share passing", "Runs measured", "Most decisions changed"], rows, num_cols=(2, 3))))
    bw = cal.get("bands")
    if bw:
        rows = [[r["kind"].replace("_", " "), r["parameter"], r["change"], r["runs_assessed"], r["runs_changing_band"],
                 r["ranking_of_agents_preserved"], r["note"]] for r in bw]
        body.append('<h2>Band edge and weight sensitivity</h2><p class="lead">Effect of shifting band edges and of scaling each weight, '
                    'on the test pack.</p>' + str(table(["Change type", "Parameter", "Change", "Runs", "Runs changing band",
                                                          "Agent ranking kept", "Note"], rows, num_cols=(3, 4))))
    pr = cal.get("probes")
    if pr:
        rows = []
        for r in pr:
            differs = r.get("trust_decision") == "differs"
            tag = Raw('<span class="mk">✕ differs</span>') if differs else Raw('<span class="mk ok">✓ same</span>')
            row = [r["probe_id"], r["targets"], r["description"], r.get("weak_point_probed") or "", r["counts_match_truth"], tag, r["outcomes"]]
            rows.append(("differs", row) if differs else row)
        body.append('<h2>Probe findings (known false positives and false negatives)</h2><p class="lead">Each probe is a run built to '
                    'exercise one weak point of the rule-based extraction. Rows marked ✕ are runs where the engine reaches a '
                    'different trust decision from the hand label.</p>' + str(table(
                        ["Probe", "Metric", "What was probed", "Weak point", "Counts match", "Trust decision", "Outcome"], rows)))
    pf = cal.get("platform")
    if pf:
        rows = [[r["case"], r["tool_name_in_log"], r["tool_name_in_label"], r["count_field"], r["linux_mac"], r["windows"], r["same_on_both"]] for r in pf]
        body.append('<h2>Operating-system check</h2><p class="lead">The same run scored under Linux/macOS rules and Windows rules. '
                    'Differences are reported in the validation report as known finding F-16.</p>' + str(table(
                        ["Case", "Tool in log", "Tool in label", "Count", "Linux / macOS", "Windows", "Same"], rows, num_cols=(4, 5))))
    mm = cal.get("mismatches")
    if mm:
        rows = [[r["dataset"], r["run_id"], r["scenario_id"], r["metric_id"], r["field"], r["truth"], r["engine"], r["weak_point"]] for r in mm]
        body.append('<h2>Count mismatches (engine vs hand label)</h2>' + str(table(
            ["Data", "Run", "Scenario", "Metric", "Count field", "Hand label", "Engine", "Weak point"], rows, num_cols=(5, 6))))
    ag = cal.get("agreement")
    if ag:
        rows = [[r["run_id"], r["scenario_id"], r["agent_config"], r["truth_overall"], r["engine_overall"], r["abs_difference"],
                 r["truth_band"], r["engine_band"], r["band_agrees"]] for r in ag]
        body.append('<details><summary>Overall score agreement, run by run (%d runs)</summary>%s</details>' % (
            len(ag), table(["Run", "Scenario", "Agent", "Hand label overall", "Engine overall", "Difference", "Hand band", "Engine band", "Agrees"], rows,
                           num_cols=(3, 4, 5))))
    if cal.get("missing"):
        body.append('<p class="muted" style="margin-top:14px">Not found in the calibration folder (sections hidden): %s</p>' % esc(", ".join(cal["missing"])))
    return layout(ctx, router, "calibration", "Calibration", "".join(str(b) for b in body))


# ----------------------------------------------------------------------------------------
# data page
# ----------------------------------------------------------------------------------------
def page_data(ctx, router):
    ck = ctx.checks
    rr = ctx.calibration.get("run_record") or {}
    ok = not (ck.get("score_cells_mismatch") or ck.get("overall_mismatch")) and not ctx.warnings
    status = ('<div class="notice ok"><b>Data checks passed.</b> Every score in the scored file matches a recomputation '
              'from its counts using the formulas in the definitions file.</div>' if ok and ck.get("counts_present") else
              '<div class="notice"><b>Count fields not present or checks incomplete.</b> See below.</div>' if ok else
              '<div class="notice err"><b>Data checks found differences.</b> %s</div>' % "<br>".join(esc(e) for e in ck["examples"]))
    rows = [
        ["Metric definitions file", Raw('<span class="mono">%s</span>' % esc(ctx.defs.path)),
         "version %s, %s; %d metrics, weights sum %s" % (ctx.defs.version, ctx.defs.status, len(ctx.defs.metrics),
                                                          fmt(sum(m.weight for m in ctx.defs.metrics)))],
        ["Scored runs file", Raw('<span class="mono">%s</span>' % esc(ctx.scored_path)),
         "%d row%s, %d scored (completed), %d excluded (status not completed)" % (
             ck["total_rows"], "" if ck["total_rows"] == 1 else "s", len(ctx.runs), ck["excluded"])],
        ["Calibration folder", Raw('<span class="mono">%s</span>' % esc(ctx.calibration.get("dir") or "")),
         "%d of %d files found" % (len(ctx.calibration["found"]), len(data.CAL_FILES))],
    ]
    if rr:
        rows.append(["Calibration run record", "run_record.json",
                     "calibration v%s, engine v%s, definitions v%s" % (
                         rr.get("calibration_version", "?"), rr.get("engine_version", "?"), rr.get("metric_definitions_version", "?"))])
    mism = ctx.defs.version != str(rr.get("metric_definitions_version", ctx.defs.version))
    checks = [
        ["Score cells recomputed from counts", "%d checked" % ck["score_cells_checked"], "%d differ" % ck["score_cells_mismatch"]],
        ["Cells left blank because the scenario has no label (label_source = heuristic)", "%d" % ck["score_cells_unlabelled"],
         "designed engine rule, not counted as a difference"],
        ["Overall scores recomputed (weighted mean, weights rescaled over measured metrics)", "%d checked" % ck["overall_checked"],
         "%d differ" % ck["overall_mismatch"]],
        ["Definitions version matches the calibration run record", "yes" if not mism else "no",
         "" if not mism else "calibration was run against definitions v%s" % rr.get("metric_definitions_version")],
    ]
    body = ('<h2 style="margin-top:0">Data and checks</h2><p class="lead">What this dashboard is showing, and whether the files agree with each other.</p>' + status +
            str(table(["Input", "Location", "Detail"], rows)) + '<h2>Checks</h2>' + str(table(["Check", "Result", "Note"], checks)) +
            '<h2>How to refresh</h2><p class="lead">Re-run the scoring engine, then restart this dashboard (or reload the page: files are read on every request). '
            'Pass other files with <span class="mono">--scored</span>, <span class="mono">--definitions</span> and <span class="mono">--calibration</span>.</p>')
    return layout(ctx, router, "data", "Data and checks", body)
