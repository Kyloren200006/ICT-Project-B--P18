"""Tiny local web server and static exporter for the WP3 dashboard (standard library only)."""
from __future__ import annotations

import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import data, render

CSP = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
       "img-src data:; base-uri 'none'; form-action 'self'")


class Config:
    def __init__(self, definitions, scored, calibration, label=""):
        self.label = label
        self.definitions = definitions
        self.scored = scored
        self.calibration = calibration

    def load(self):
        return data.build_context(self.definitions, self.scored, self.calibration, self.label)


def error_page(title, message):
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>%s</title>'
            '<body style="font:16px system-ui;max-width:48em;margin:3em auto;padding:0 1em">'
            '<h1>%s</h1><p>%s</p></body></html>' % (render.esc(title), render.esc(title), render.esc(message)))


def route(ctx, path, query):
    """Return (status, html). `path` like '/', '/metrics', '/metric/DM-001'."""
    router = render.Router("server")
    path = path.rstrip("/") or "/"
    filters = data.parse_filters(query, ctx.runs)
    if path == "/":
        return 200, render.page_overview(ctx, router, filters)
    if path == "/metrics":
        return 200, render.page_metrics(ctx, router)
    if path == "/distributions":
        return 200, render.page_distributions(ctx, router, filters)
    if path.startswith("/metric/"):
        html = render.page_metric(ctx, router, filters, path[len("/metric/"):])
        if html is None:
            return 404, error_page("Not found", "There is no metric with that ID.")
        return 200, html
    if path == "/runs":
        sort = (query.get("sort") or [""])[0]
        direction = "desc" if (query.get("dir") or ["asc"])[0] == "desc" else "asc"
        return 200, render.page_runs(ctx, router, filters, sort, direction)
    if path == "/calibration":
        return 200, render.page_calibration(ctx, router)
    if path == "/data":
        return 200, render.page_data(ctx, router)
    return 404, error_page("Not found", "That page does not exist.")


def make_handler(config):
    class Handler(BaseHTTPRequestHandler):
        server_version = "WP3Dashboard/1.0"

        def log_message(self, fmt, *args):      # quiet; the CLI prints the address once
            pass

        def _send(self, status, body, ctype="text/html; charset=utf-8", head=False):
            raw = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            if not head:
                self.wfile.write(raw)

        def _handle(self, head=False):
            url = urlparse(self.path)
            if url.path == "/healthz":
                return self._send(200, "ok", "text/plain; charset=utf-8", head)
            if url.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            try:
                ctx = config.load()                       # files are re-read on every request
                status, html = route(ctx, url.path, parse_qs(url.query))
            except FileNotFoundError as exc:
                status, html = 500, error_page("File not found", "%s. Check the --scored, --definitions and "
                                               "--calibration options." % exc)
            except Exception as exc:                       # show a readable message, keep serving
                status, html = 500, error_page("Could not build this page", "%s: %s" % (type(exc).__name__, exc))
            self._send(status, html, head=head)

        def do_GET(self):
            self._handle()

        def do_HEAD(self):
            self._handle(head=True)

    return Handler


def serve(config, host="127.0.0.1", port=8765):
    httpd = ThreadingHTTPServer((host, port), make_handler(config))
    return httpd


def export_site(config, outdir):
    """Write every page as a static HTML file (no filters, no sorting). Returns the file names."""
    ctx = config.load()
    router = render.Router("export")
    os.makedirs(outdir, exist_ok=True)
    filters = data.Filters()
    pages = {
        "index.html": render.page_overview(ctx, router, filters),
        "metrics.html": render.page_metrics(ctx, router),
        "distributions.html": render.page_distributions(ctx, router, filters),
        "runs.html": render.page_runs(ctx, router, filters),
        "calibration.html": render.page_calibration(ctx, router),
        "data.html": render.page_data(ctx, router),
    }
    for m in ctx.defs.metrics:
        pages["metric-%s.html" % m.id] = render.page_metric(ctx, router, filters, m.id)
    for name, html in pages.items():
        with open(os.path.join(outdir, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html)
    return sorted(pages)
