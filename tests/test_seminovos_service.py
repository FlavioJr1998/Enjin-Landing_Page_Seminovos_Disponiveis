from datetime import datetime, timezone

from services.seminovos_service import SeminovosService


class FakeWorksheet:
    def __init__(self, values):
        self.values = values
        self.calls = 0

    def get_all_values(self):
        self.calls += 1
        return self.values


class FakeSpreadsheet:
    def __init__(self, worksheet):
        self._worksheet = worksheet

    def worksheet(self, name):
        assert name == "SEMINOVOS"
        return self._worksheet


class FakeClient:
    def __init__(self, worksheet):
        self._worksheet = worksheet

    def open_by_key(self, spreadsheet_id):
        assert spreadsheet_id == "sheet-id"
        return FakeSpreadsheet(self._worksheet)


def build_service(worksheet, clock):
    return SeminovosService(
        spreadsheet_id="sheet-id",
        tab_name="SEMINOVOS",
        credentials_file="credentials.json",
        cache_timeout=60,
        client_factory=lambda _: FakeClient(worksheet),
        monotonic=lambda: clock[0],
        now=lambda: datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
    )


def test_filters_columns_and_uses_cache():
    worksheet = FakeWorksheet(
        [
            ["Modelo", "Ano", "Quilometragem", "Valor de venda", "Chassi"],
            ["Civic", "2023", "18.000", "R$ 129.900", "nao-publicar"],
        ]
    )
    clock = [100.0]
    service = build_service(worksheet, clock)

    first = service.get_snapshot()
    second = service.get_snapshot()

    assert worksheet.calls == 1
    assert first["status"] == "online"
    assert first["dados"] == [
        {
            "modelo": "Civic",
            "ano": "2023",
            "km": "18.000",
            "valor_venda": "R$ 129.900",
        }
    ]
    assert second["dados"] == first["dados"]
    assert "Chassi" not in str(first)


def test_keeps_last_valid_cache_when_refresh_fails():
    worksheet = FakeWorksheet(
        [["Modelo", "Ano", "KM", "Valor"], ["HR-V", "2024", "9.500", "150000"]]
    )
    clock = [100.0]
    service = build_service(worksheet, clock)
    service.get_snapshot()

    def fail():
        raise ConnectionError("indisponível")

    worksheet.get_all_values = fail
    clock[0] = 200.0
    snapshot = service.get_snapshot()

    assert snapshot["status"] == "degradado"
    assert snapshot["quantidade"] == 1
    assert snapshot["dados"][0]["modelo"] == "HR-V"


def test_rejects_sheet_without_required_columns():
    worksheet = FakeWorksheet([["Modelo", "Ano"], ["City", "2025"]])
    service = build_service(worksheet, [100.0])

    snapshot = service.get_snapshot()

    assert snapshot["status"] == "indisponivel"
    assert snapshot["erro"] == "coluna_obrigatoria"
    assert snapshot["dados"] == []


def test_log_explains_missing_service_account_configuration(caplog):
    service = SeminovosService(
        spreadsheet_id="sheet-id",
        tab_name="SEMINOVOS",
        credentials_file="",
        cache_timeout=60,
    )

    with caplog.at_level("INFO", logger="Seminovos"):
        snapshot = service.get_snapshot()

    assert snapshot["erro"] == "configuracao_credenciais"
    assert "GOOGLE_SERVICE_ACCOUNT_FILE" in caplog.text
    assert "configuracao_credenciais" in caplog.text


def test_success_log_reports_connection_steps(caplog):
    worksheet = FakeWorksheet(
        [["Modelo", "Ano", "KM", "Valor"], ["City", "2025", "0", "R$ 120.000"]]
    )
    service = build_service(worksheet, [100.0])

    with caplog.at_level("INFO", logger="Seminovos"):
        service.get_snapshot()

    assert "Credenciais carregadas" in caplog.text
    assert "Planilha acessível" in caplog.text
    assert "atualizado com sucesso (1 veículo)" in caplog.text
