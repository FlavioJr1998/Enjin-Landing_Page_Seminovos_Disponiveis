import io
import logging

import pytest

import config
from app import create_app
from utils.logger import configure_logging, logger


class FakeService:
    def get_snapshot(self, refresh=True):
        return {
            "status": "online",
            "erro": None,
            "ultima_atualizacao": "2026-09-16T12:00:00+00:00",
            "quantidade": 0,
            "dados": [],
        }


def test_writes_system_log_to_rotating_file(tmp_path):
    configure_logging(log_dir=tmp_path, level="INFO", retention_days=2)
    try:
        logger.info("acao-de-teste")
        for handler in logger.handlers:
            handler.flush()

        log_content = (tmp_path / "seminovos.log").read_text(encoding="utf-8")
        assert "acao-de-teste" in log_content
    finally:
        configure_logging(log_dir="logs", level="INFO", retention_days=30)


def test_logs_every_http_access():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    try:
        app = create_app(FakeService(), environment="homologation")
        app.config["TESTING"] = True
        response = app.test_client().get("/health")
    finally:
        logger.removeHandler(handler)

    assert response.status_code == 200
    assert "Acesso iniciado" in stream.getvalue()
    assert "Acesso concluído" in stream.getvalue()
    assert "rota=/health" in stream.getvalue()


def test_production_requires_external_configuration(monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_SHEETS_SPREADSHEET_ID", "")
    monkeypatch.setattr(config, "GOOGLE_SERVICE_ACCOUNT_FILE", "")
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "")

    with pytest.raises(RuntimeError, match="Configuração de produção incompleta"):
        config.validate_production_settings()


def test_app_accepts_production_when_configuration_exists(monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_SHEETS_SPREADSHEET_ID", "sheet-id")
    monkeypatch.setattr(config, "GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://example.test")

    app = create_app(FakeService(), environment="production")

    assert app.config["ENVIRONMENT"] == "production"
