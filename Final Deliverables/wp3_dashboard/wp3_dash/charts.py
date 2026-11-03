"""Server-rendered SVG charts for the WP3 dashboard (no JavaScript, no external libraries).

Colours come from CSS custom properties (see CHART_CSS) so the same markup works in light
and dark mode. standalone() wraps a chart in an <svg> that carries its own style block, which
is how figures are exported as editable .svg files for the technical report.

Palette (dataviz skill, reference instance): blue = series 1, orange = series 2, status colours
for risk bands; text always uses the ink tokens, never a series colour.
"""
from __future__ import annotations

from html import escape

CHART_CSS_LIGHT = {
    "--surface": "#fcfcfb", "--ink": "#0b0b0b", "--ink2": "#52514e", "--muted": "#898781",
    "--grid": "#e1e0d9", "--axis": "#c3c2b7",
    "--s1": "#2a78d6", "--s2": "#eb6834",
    "--good": "#0ca30c", "--warn": "#fab219", "--serious": "#ec835a", "--critical": "#d03b3b",
    "--on-fill": "#ffffff", "--on-warn": "#0b0b0b",
}
CHART_CSS_DARK = {
    "--surface": "#1a1a19", "--ink": "#f0efec", "--ink2": "#c3c2b7", "--muted": "#898781",
    "--grid": "#2c2c2a", "--axis": "#383835",
    "--s1": "#3987e5", "--s2": "#d95926",
    "--good": "#0ca30c", "--warn": "#fab219", "--serious": "#ec835a", "--critical": "#d03b3b",
    "--on-fill": "#ffffff", "--on-warn": "#0b0b0b",
}
CHART_RULES = """
.ch{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:12px}
.ch .surface{fill:var(--surface)}
.ch text{fill:var(--ink2)} .ch .t-ink{fill:var(--ink)} .ch .t-muted{fill:var(--muted)}
.ch .t-strong{fill:var(--ink);font-weight:600}
.ch .grid{stroke:var(--grid);stroke-width:1} .ch .axis{stroke:var(--axis);stroke-width:1}
.ch .s1{fill:var(--s1)} .ch .s2{fill:var(--s2)} .ch .gray{fill:var(--axis)}
.ch .st-good{fill:var(--good)} .ch .st-warn{fill:var(--warn)}
.ch .st-serious{fill:var(--serious)} .ch .st-critical{fill:var(--critical)}
.ch .bad{fill:var(--critical)}
.ch .thr{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:4 3}
.ch .on-fill{fill:var(--on-fill)} .ch .on-warn{fill:var(--on-warn)}
.ch .mark{transition:opacity .1s} .ch .mark:hover{opacity:.78}
.ch .hit{fill:transparent}
"""


def _vars(d):
    return ";".join("%s:%s" % kv for kv in d.items())


def standalone(svg, theme="light"):
    """Return `svg` (a chart string from this module) as a self-contained .svg document."""
    css = CHART_CSS_DARK if theme == "dark" else CHART_CSS_LIGHT
    style = "<style>.ch{%s}%s</style>" % (_vars(css), CHART_RULES)
    head, rest = svg.split(">", 1)
    if 'xmlns=' not in head:
        head += ' xmlns="http://www.w3.org/2000/svg"'
    # the surface rect gives the exported file a background in either theme
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + head + ">" + style + rest + "\n"


def _f(v, digits=2):
    return ("%." + str(digits) + "f") % v


def _bar_path(x, y, w, h, r=4, side="right"):
    """Bar with a rounded data end only (right end for horizontal bars, top end for vertical)."""
    r = min(r, w / 2 if side == "top" else h / 2, w if side == "right" else h)
    if side == "right":
        if w <= r:
            return "M%s,%sh%sv%sh-%sz" % (_f(x), _f(y), _f(max(w, 0.5)), _f(h), _f(max(w, 0.5)))
        return ("M%s,%sh%sa%s,%s 0 0 1 %s,%sv%sa%s,%s 0 0 1 -%s,%sh-%sz" % (
            _f(x), _f(y), _f(w - r), _f(r), _f(r), _f(r), _f(r), _f(h - 2 * r),
            _f(r), _f(r), _f(r), _f(r), _f(w - r)))
    # top
    if h <= r:
        return "M%s,%sh%sv%sh-%sz" % (_f(x), _f(y), _f(w), _f(max(h, 0.5)), _f(w))
    return ("M%s,%sv%sa%s,%s 0 0 1 %s,-%sh%sa%s,%s 0 0 1 %s,%sv%sz" % (
        _f(x), _f(y + h), _f(-(h - r)), _f(r), _f(r), _f(r), _f(r), _f(w - 2 * r),
        _f(r), _f(r), _f(r), _f(r), _f(h - r)))


def _svg_open(w, h, label, desc=None):
    return ('<svg class="ch" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
            'aria-label="%s" preserveAspectRatio="xMidYMid meet">%s<rect class="surface" '
            'width="%d" height="%d"/>' % (w, h, w, h, escape(label, True),
                                          ("<desc>%s</desc>" % escape(desc)) if desc else "", w, h))


def hbar(rows, label, vmax=1.0, width=560, label_w=160, bar_h=18, gap=10, ref=None,
         ref_label=None, desc=None):
    """Horizontal bars. rows: dicts with label, value (None = not measured), text, title, cls."""
    pad_r, top = 96, 18 if ref is not None else 6
    plot_w = width - label_w - pad_r
    height = top + len(rows) * (bar_h + gap) + 8
    out = [_svg_open(width, height, label, desc)]
    x0 = label_w
    # recessive gridlines at 0, .5, 1 (of vmax)
    for frac in (0.0, 0.5, 1.0):
        gx = x0 + plot_w * frac
        out.append('<line class="%s" x1="%s" x2="%s" y1="%d" y2="%d"/>' % (
            "axis" if frac == 0 else "grid", _f(gx), _f(gx), top - 2, height - 6))
    y = top
    for r in rows:
        cy = y + bar_h / 2 + 4
        out.append('<text class="t-ink" x="%d" y="%s" text-anchor="end">%s</text>' % (
            label_w - 8, _f(cy), escape(r["label"])))
        v = r.get("value")
        title = escape(r.get("title") or "")
        if v is None:
            out.append('<text class="t-muted" x="%d" y="%s">%s</text>' % (
                x0 + 6, _f(cy), escape(r.get("text") or "not measured")))
        else:
            w = max(plot_w * min(v, vmax) / vmax, 0.0)
            out.append('<g class="mark"><title>%s</title><path class="%s" d="%s"/></g>' % (
                title, r.get("cls", "s1"), _bar_path(x0, y, w, bar_h)))
            out.append('<text class="t-ink" x="%s" y="%s">%s</text>' % (
                _f(x0 + w + 6), _f(cy), escape(r.get("text") or _f(v))))
        y += bar_h + gap
    if ref is not None:
        rx = x0 + plot_w * ref / vmax
        out.append('<line class="thr" x1="%s" x2="%s" y1="%d" y2="%d"/>' % (
            _f(rx), _f(rx), top - 2, height - 6))
        if ref_label:
            out.append('<text class="t-ink" x="%s" y="11" text-anchor="middle">%s</text>' % (
                _f(rx), escape(ref_label)))
    out.append("</svg>")
    return "".join(out)


def grouped_hbar(groups, series, label, vmax=1.0, width=560, label_w=160, bar_h=12, inner=3,
                 gap=14, desc=None):
    """groups: [{label, bars:[{value, text, title}]}] with one bar per series (s1, s2)."""
    pad_r, top = 120, 6
    plot_w = width - label_w - pad_r
    gh = len(series) * bar_h + (len(series) - 1) * inner
    height = top + len(groups) * (gh + gap) + 6
    out = [_svg_open(width, height, label, desc)]
    x0 = label_w
    for frac in (0.0, 0.5, 1.0):
        gx = x0 + plot_w * frac
        out.append('<line class="%s" x1="%s" x2="%s" y1="%d" y2="%d"/>' % (
            "axis" if frac == 0 else "grid", _f(gx), _f(gx), top - 2, height - 4))
    y = top
    for g in groups:
        out.append('<text class="t-ink" x="%d" y="%s" text-anchor="end">%s</text>' % (
            label_w - 8, _f(y + gh / 2 + 4), escape(g["label"])))
        for i, b in enumerate(g["bars"]):
            by = y + i * (bar_h + inner)
            cls = "s1" if i == 0 else "s2"
            cy = by + bar_h / 2 + 4
            if b.get("value") is None:
                out.append('<text class="t-muted" x="%d" y="%s">%s</text>' % (
                    x0 + 6, _f(cy), escape(b.get("text") or "n/a")))
            else:
                w = plot_w * min(b["value"], vmax) / vmax
                out.append('<g class="mark"><title>%s</title><path class="%s" d="%s"/></g>' % (
                    escape(b.get("title") or ""), cls, _bar_path(x0, by, w, bar_h, r=3)))
                out.append('<text class="t-ink" x="%s" y="%s">%s</text>' % (
                    _f(x0 + w + 6), _f(cy), escape(b.get("text") or _f(b["value"]))))
        y += gh + gap
    out.append("</svg>")
    return "".join(out)


def stacked_bar(segments, label, width=560, height=34, desc=None):
    """One horizontal stacked bar. segments: [{label, count, cls, text_cls, icon}] in order.
    A 2px surface gap separates segments; counts print inside when the segment is wide enough."""
    total = sum(s["count"] for s in segments)
    out = [_svg_open(width, height, label, desc)]
    if total <= 0:
        out.append('<text class="t-muted" x="0" y="%d">no runs</text></svg>' % (height // 2 + 4))
        return "".join(out)
    x = 0.0
    for s in segments:
        if s["count"] <= 0:
            continue
        w = width * s["count"] / total
        out.append('<g class="mark"><title>%s</title><rect class="%s" x="%s" y="2" width="%s" '
                   'height="%d" stroke="var(--surface)" stroke-width="2"/></g>' % (
                       escape("%s: %d of %d runs" % (s["label"], s["count"], total)),
                       s["cls"], _f(x), _f(w), height - 4))
        if w >= 26:
            out.append('<text class="%s" x="%s" y="%d" text-anchor="middle" '
                       'style="font-weight:600">%d</text>' % (
                           s.get("text_cls", "on-fill"), _f(x + w / 2), height // 2 + 4, s["count"]))
        x += w
    out.append("</svg>")
    return "".join(out)


def histogram(bins, metric_threshold, passing, label, width=300, height=150, labels=None,
              desc=None):
    """Score histogram. bins: counts for 21 bins (20 of width 0.05 + one for exactly 1.00).
    passing: list of bools, bin counts as meeting the threshold. Dashed line = threshold."""
    n = len(bins)
    L, R, T, B = 30, 8, 18, 32
    pw, ph = width - L - R, height - T - B
    bw = pw / n
    ymax = max(max(bins), 1)
    out = [_svg_open(width, height, label, desc)]
    for frac in (0.0, 0.5, 1.0):
        gy = T + ph * (1 - frac)
        out.append('<line class="%s" x1="%d" x2="%d" y1="%s" y2="%s"/>' % (
            "axis" if frac == 0 else "grid", L, width - R, _f(gy), _f(gy)))
    out.append('<text class="t-muted" x="%d" y="%s" text-anchor="end">%d</text>' % (
        L - 4, _f(T + 4), ymax))
    out.append('<text class="t-muted" x="%d" y="%s" text-anchor="end">0</text>' % (
        L - 4, _f(T + ph + 4)))
    for i, c in enumerate(bins):
        x = L + i * bw + 1
        w = bw - 2
        lab = (labels[i] if labels else str(i))
        if c > 0:
            h = ph * c / ymax
            cls = "s1" if passing[i] else "bad"
            out.append('<g class="mark"><title>%s</title><path class="%s" d="%s"/></g>' % (
                escape("%s: %d run%s%s" % (lab, c, "" if c == 1 else "s",
                                            "" if passing[i] else " (below threshold)")),
                cls, _bar_path(x, T + ph - h, w, h, r=3, side="top")))
        else:
            out.append('<title>%s: 0 runs</title>' % escape(lab))
    # threshold line sits on a bin boundary: bins are 0.05 wide and thresholds are multiples of it
    tx = L + round(metric_threshold * (n - 1)) * bw
    out.append('<line class="thr" x1="%s" x2="%s" y1="%d" y2="%d"/>' % (
        _f(tx), _f(tx), T - 6, T + ph))
    anchor = "end" if tx > width * 0.6 else "start"
    out.append('<text class="t-ink" x="%s" y="%d" text-anchor="%s">threshold %s</text>' % (
        _f(tx + (-4 if anchor == "end" else 4)), T - 8, anchor, _f(metric_threshold)))
    # x ticks: 0, 0.5, 1.0 (bin n-1 is exactly 1.0)
    for lab_, idx in (("0", 0), ("0.5", 10), ("1.0", n - 1)):
        tx2 = L + idx * bw + (bw / 2 if idx == n - 1 else 0)
        out.append('<text class="t-muted" x="%s" y="%d" text-anchor="middle">%s</text>' % (
            _f(tx2), height - 16, lab_))
    out.append('<text class="t-muted" x="%s" y="%d" text-anchor="middle">score</text>' % (
        _f(L + pw / 2), height - 1))
    out.append("</svg>")
    return "".join(out)
