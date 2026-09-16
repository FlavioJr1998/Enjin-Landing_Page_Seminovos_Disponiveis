import re
import threading
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from config import (
    CACHE_TIMEOUT_SECONDS,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_SHEETS_SPREADSHEET_ID,
    GOOGLE_SHEETS_TAB_NAME,
)
from utils.logger import logger


HEADER_ALIASES = {
    "modelo": {"modelo"},
    "ano": {"ano", "ano modelo", "ano fabricacao"},
    "km": {"km", "quilometragem", "kilometragem"},
    "valor_venda": {
        "valor",
        "valor venda",
        "valor de venda",
        "preco",
        "preco venda",
        "preco de venda",
    },
}


class CredentialsConfigurationError(RuntimeError):
    pass


class RequiredColumnError(ValueError):
    pass


def _normalize_header(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(
        character for character in value if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _default_client_factory(credentials_file):
    import gspread

    if not Path(credentials_file).is_file():
        raise CredentialsConfigurationError(
            "O arquivo configurado em GOOGLE_SERVICE_ACCOUNT_FILE não foi encontrado."
        )
    return gspread.service_account(filename=credentials_file)


class SeminovosService:
    def __init__(
        self,
        spreadsheet_id=GOOGLE_SHEETS_SPREADSHEET_ID,
        tab_name=GOOGLE_SHEETS_TAB_NAME,
        credentials_file=GOOGLE_SERVICE_ACCOUNT_FILE,
        cache_timeout=CACHE_TIMEOUT_SECONDS,
        client_factory=None,
        monotonic=None,
        now=None,
    ):
        self.spreadsheet_id = spreadsheet_id
        self.tab_name = tab_name
        self.credentials_file = credentials_file
        self.cache_timeout = max(1, cache_timeout)
        self.client_factory = client_factory or _default_client_factory
        self.monotonic = monotonic or time.monotonic
        self.now = now or (lambda: datetime.now(timezone.utc))

        self._lock = threading.RLock()
        self._cache = []
        self._expires_at = 0.0
        self._last_updated = None
        self._status = "inicializando"
        self._last_error_code = None

    def _read_sheet(self):
        if not self.credentials_file:
            raise CredentialsConfigurationError(
                "Defina GOOGLE_SERVICE_ACCOUNT_FILE ou GOOGLE_APPLICATION_CREDENTIALS."
            )

        logger.info("Carregando as credenciais da conta de serviço...")
        client = self.client_factory(self.credentials_file)
        logger.info(
            "Credenciais carregadas. Abrindo a planilha %s...",
            self.spreadsheet_id,
        )
        worksheet = client.open_by_key(self.spreadsheet_id).worksheet(self.tab_name)
        logger.info("Planilha acessível. Lendo a aba '%s'...", self.tab_name)
        values = worksheet.get_all_values()
        logger.info(
            "Leitura da aba '%s' concluída (%d linhas recebidas).",
            self.tab_name,
            len(values),
        )

        if not values:
            return []

        header_positions = self._header_positions(values[0])
        vehicles = []

        for row in values[1:]:
            vehicle = {
                field: self._cell(row, position)
                for field, position in header_positions.items()
            }
            if any(vehicle.values()):
                vehicles.append(vehicle)

        return vehicles

    @staticmethod
    def _cell(row, position):
        if position >= len(row):
            return ""
        return str(row[position]).strip()

    @staticmethod
    def _header_positions(headers):
        normalized_headers = [_normalize_header(header) for header in headers]
        positions = {}

        for field, aliases in HEADER_ALIASES.items():
            try:
                positions[field] = next(
                    index
                    for index, header in enumerate(normalized_headers)
                    if header in aliases
                )
            except StopIteration as exc:
                raise RequiredColumnError(
                    f"Coluna obrigatória ausente na aba: {field}"
                ) from exc

        return positions

    @staticmethod
    def _diagnose_error(exc):
        try:
            from google.auth.exceptions import GoogleAuthError
            from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
            from requests.exceptions import ConnectionError, Timeout
        except ImportError:
            GoogleAuthError = APIError = SpreadsheetNotFound = WorksheetNotFound = ()
            ConnectionError = Timeout = ()

        if isinstance(exc, CredentialsConfigurationError):
            return "configuracao_credenciais", str(exc)
        if isinstance(exc, SpreadsheetNotFound):
            return (
                "planilha_sem_acesso",
                "Planilha não encontrada ou sem permissão para a conta de serviço. "
                "Confira o ID e o compartilhamento da planilha.",
            )
        if isinstance(exc, WorksheetNotFound):
            return (
                "aba_nao_encontrada",
                "A aba configurada não foi encontrada na planilha.",
            )
        if isinstance(exc, GoogleAuthError):
            return (
                "autenticacao_conta_servico",
                "A autenticação da conta de serviço falhou. Confira o arquivo de credenciais.",
            )
        if isinstance(exc, APIError):
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            suffix = f" HTTP {status_code}." if status_code else "."
            return (
                "google_sheets_api",
                "A API do Google Sheets recusou a consulta" + suffix,
            )
        if isinstance(exc, (ConnectionError, Timeout)):
            return (
                "conexao_google",
                "Não foi possível estabelecer conexão com o Google Sheets.",
            )
        if isinstance(exc, RequiredColumnError):
            return "coluna_obrigatoria", str(exc)
        if isinstance(exc, (ValueError, TypeError)):
            return (
                "credenciais_invalidas",
                "O arquivo da conta de serviço não contém credenciais válidas.",
            )
        return (
            "erro_inesperado",
            f"Falha inesperada durante a consulta ({type(exc).__name__}).",
        )

    def _refresh_if_needed(self, force=False):
        with self._lock:
            if not force and self.monotonic() < self._expires_at:
                logger.debug("Cache de seminovos ainda válido; consulta não executada.")
                return

            logger.info(
                "Atualizando cache pelo Google Sheets (aba='%s')...",
                self.tab_name,
            )
            try:
                vehicles = self._read_sheet()
            except Exception as exc:
                error_code, error_message = self._diagnose_error(exc)
                self._status = "degradado" if self._last_updated else "indisponivel"
                self._last_error_code = error_code
                self._expires_at = self.monotonic() + min(30, self.cache_timeout)
                logger.error(
                    "Falha ao atualizar o cache [%s]: %s",
                    error_code,
                    error_message,
                )
                return

            self._cache = vehicles
            self._last_updated = self.now()
            self._expires_at = self.monotonic() + self.cache_timeout
            self._status = "online"
            self._last_error_code = None
            logger.info(
                "Cache de seminovos atualizado com sucesso (%d veículo%s).",
                len(vehicles),
                "s" if len(vehicles) != 1 else "",
            )

    def get_snapshot(self, refresh=True):
        if refresh:
            self._refresh_if_needed()

        with self._lock:
            return {
                "status": self._status,
                "erro": self._last_error_code,
                "ultima_atualizacao": (
                    self._last_updated.isoformat() if self._last_updated else None
                ),
                "quantidade": len(self._cache),
                "dados": [dict(vehicle) for vehicle in self._cache],
            }

    def force_refresh(self):
        self._refresh_if_needed(force=True)
        return self.get_snapshot(refresh=False)


seminovos_service = SeminovosService()
