import os

from dotenv import load_dotenv


load_dotenv()


ENVIRONMENT_ALIASES = {
    "production": "production",
    "producao": "production",
    "homologation": "homologation",
    "homologacao": "homologation",
}


def normalize_environment(value):
    normalized = str(value or "").strip().casefold()
    try:
        return ENVIRONMENT_ALIASES[normalized]
    except KeyError as exc:
        raise ValueError(
            "APP_ENV deve ser 'production' ou 'homologation'."
        ) from exc


APP_ENV = normalize_environment(os.getenv("APP_ENV", "homologation"))
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "5000"))
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip()
GOOGLE_SHEETS_TAB_NAME = os.getenv("GOOGLE_SHEETS_TAB_NAME", "SEMINOVOS")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS", ""
)
CACHE_TIMEOUT_SECONDS = int(os.getenv("CACHE_TIMEOUT_SECONDS", "300"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")


def validate_production_settings():
    required_settings = {
        "GOOGLE_SHEETS_SPREADSHEET_ID": GOOGLE_SHEETS_SPREADSHEET_ID,
        "GOOGLE_SERVICE_ACCOUNT_FILE ou GOOGLE_APPLICATION_CREDENTIALS": (
            GOOGLE_SERVICE_ACCOUNT_FILE
        ),
        "PUBLIC_BASE_URL": PUBLIC_BASE_URL,
    }
    missing = [name for name, value in required_settings.items() if not value]
    if missing:
        raise RuntimeError(
            "Configuração de produção incompleta. Variáveis ausentes: "
            + ", ".join(missing)
        )
