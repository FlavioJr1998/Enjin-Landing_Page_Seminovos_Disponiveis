from app import create_app


class FakeService:
    def __init__(self, status="online", last_updated="2026-09-16T12:00:00+00:00"):
        self.status = status
        self.last_updated = last_updated

    def get_snapshot(self, refresh=True):
        return {
            "status": self.status,
            "erro": None if self.status == "online" else "erro_teste",
            "ultima_atualizacao": self.last_updated,
            "quantidade": 1 if self.last_updated else 0,
            "dados": (
                [
                    {
                        "modelo": "Civic",
                        "ano": "2023",
                        "km": "18.000",
                        "valor_venda": "R$ 129.900",
                    }
                ]
                if self.last_updated
                else []
            ),
        }


def make_client(service=None):
    app = create_app(service or FakeService())
    app.config.update(TESTING=True, PUBLIC_BASE_URL="https://example.test")
    return app.test_client()


def test_index_renders_only_public_vehicle_fields():
    response = make_client().get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Civic" in body
    assert "2023" in body
    assert "18.000" in body
    assert "R$ 129.900" in body
    assert "Chassi" not in body
    assert "<table>" in body
    assert "Escolha seu próximo veículo" not in body


def test_health_is_ok_with_fresh_cache():
    response = make_client().get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_cache_api_exposes_only_allowed_sheet_fields():
    response = make_client().get("/api/cache")
    vehicle = response.get_json()["dados"][0]

    assert response.status_code == 200
    assert set(vehicle) == {"modelo", "ano", "km", "valor_venda"}


def test_health_is_degraded_with_stale_valid_cache():
    response = make_client(FakeService("degradado")).get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "degraded"


def test_health_is_unavailable_without_valid_cache():
    response = make_client(FakeService("indisponivel", None)).get("/health")

    assert response.status_code == 503
    assert response.get_json()["status"] == "error"


def test_robots_and_sitemap_use_public_url():
    client = make_client()

    robots = client.get("/robots.txt")
    sitemap = client.get("/sitemap.xml")

    assert robots.status_code == 200
    assert "Sitemap: https://example.test/sitemap.xml" in robots.get_data(as_text=True)
    assert sitemap.status_code == 200
    assert "<loc>https://example.test/</loc>" in sitemap.get_data(as_text=True)
