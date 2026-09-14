from flask import Blueprint
from flask import Response
from flask import jsonify
from flask import render_template
from datetime import datetime
from services.agenda_service import agenda_service

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def index():
    print(f"[{datetime.now()}] Respondendo")
    return render_template(

        "index.html",

        dados=agenda_service.get_dados(),

        ultima=agenda_service.get_ultima_atualizacao(),

        quantidade=agenda_service.get_quantidade(),

        status=agenda_service.get_status()

    )

@web_bp.route("/api/cache")
def cache():
    return jsonify(
        agenda_service.get_cache()
    )

@web_bp.route("/health")
def health():

    return jsonify(
        {
            "status": agenda_service.get_status(),

            "ultima_atualizacao": agenda_service.get_ultima_atualizacao()

        }

    )

@web_bp.route("/robots.txt")
def robots():

    robots_txt = f"""
    User-agent: *
    Allow: /

    Disallow:
    
    Sitemap: https://seminovos-venda.enjin.app.br/sitemap.xml
    """

    return Response(
        robots_txt,
        mimetype="text/plain"
    )
    
@web_bp.route("/sitemap.xml")
def sitemap():

    ultima = agenda_service.get_ultima_atualizacao()

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>

    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">

        <url>

            <loc>https://seminovos-venda.enjin.app.br/</loc>

            <lastmod>{ultima}</lastmod>

            <changefreq>always</changefreq>

            <priority>1.0</priority>

        </url>

    </urlset>
    """

    return Response(
        sitemap,
        mimetype="application/xml"
    )