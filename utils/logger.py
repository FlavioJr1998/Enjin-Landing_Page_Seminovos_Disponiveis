import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


logger = logging.getLogger("Seminovos")


def _log_level(value):
    return getattr(logging, str(value).upper(), logging.INFO)


def configure_logging(log_dir=None, level=None, retention_days=None):
    directory = Path(log_dir or os.getenv("LOG_DIR", "logs"))
    configured_level = _log_level(level or os.getenv("LOG_LEVEL", "INFO"))
    retention = int(retention_days or os.getenv("LOG_RETENTION_DAYS", "30"))
    directory.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )

    for handler in list(logger.handlers):
        if getattr(handler, "_seminovos_managed", False):
            logger.removeHandler(handler)
            handler.close()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler._seminovos_managed = True

    file_handler = TimedRotatingFileHandler(
        directory / "seminovos.log",
        when="midnight",
        interval=1,
        backupCount=max(1, retention),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler._seminovos_managed = True

    logger.setLevel(configured_level)
    logger.propagate = False
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.info(
        "Logs configurados arquivo=%s nivel=%s retencao_dias=%d",
        directory / "seminovos.log",
        logging.getLevelName(configured_level),
        max(1, retention),
    )


configure_logging()
