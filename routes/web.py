from flask import Blueprint, Response, current_app, jsonify, render_template
from markupsafe import escape


web_bp = Blueprint("web", __name__)


def _service():
    return current_app.extensions["seminovos_service"]


@web_bp.get("/")
def index():
    snapshot = _service().get_snapshot()
    return render_template(
        "index.html",
        dados=snapshot["dados"],
        ultima=snapshot["ultima_atualizacao"],
        quantidade=snapshot["quantidade"],
        status=snapshot["status"],
        public_base_url=current_app.config["PUBLIC_BASE_URL"],
    )


@web_bp.get("/api/cache")
def cache():
    return jsonify(_service().get_snapshot())


@web_bp.get("/health")
def health():
    snapshot = _service().get_snapshot()
    source_status = snapshot["status"]
    has_valid_cache = snapshot["ultima_atualizacao"] is not None

    if source_status == "online":
        health_status = "ok"
        status_code = 200
    elif has_valid_cache:
        health_status = "degraded"
        status_code = 200
    else:
        health_status = "error"
        status_code = 503

    return (
        jsonify(
            {
                "status": health_status,
                "fonte": source_status,
                "erro": snapshot["erro"],
                "ultima_atualizacao": snapshot["ultima_atualizacao"],
                "quantidade": snapshot["quantidade"],
            }
        ),
        status_code,
    )


@web_bp.get("/robots.txt")
def robots():
    base_url = current_app.config["PUBLIC_BASE_URL"]
    robots_txt = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /health\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return Response(robots_txt, content_type="text/plain; charset=utf-8")


@web_bp.get("/sitemap.xml")
def sitemap():
    snapshot = _service().get_snapshot(refresh=False)
    base_url = escape(current_app.config["PUBLIC_BASE_URL"])
    last_modified = ""
    if snapshot["ultima_atualizacao"]:
        last_modified = f"<lastmod>{escape(snapshot['ultima_atualizacao'])}</lastmod>"

    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>{base_url}/</loc>\n"
        f"    {last_modified}\n"
        "    <changefreq>hourly</changefreq>\n"
        "    <priority>1.0</priority>\n"
        "  </url>\n"
        "</urlset>\n"
    )
    return Response(sitemap_xml, content_type="application/xml; charset=utf-8")
