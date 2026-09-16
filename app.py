import argparse
import time
from uuid import uuid4

from flask import Flask, g, request

from config import (
    APP_ENV,
    APP_HOST,
    APP_PORT,
    PUBLIC_BASE_URL,
    normalize_environment,
    validate_production_settings,
)
from routes.web import web_bp
from services.seminovos_service import seminovos_service
from utils.logger import logger


def create_app(service=None, environment=None):
    selected_environment = normalize_environment(environment or APP_ENV)
    if selected_environment == "production":
        validate_production_settings()

    app = Flask(__name__)
    app.config.update(
        ENVIRONMENT=selected_environment,
        PUBLIC_BASE_URL=PUBLIC_BASE_URL or "http://localhost:5000",
    )
    app.extensions["seminovos_service"] = service or seminovos_service
    app.register_blueprint(web_bp)
    register_request_logging(app)
    logger.info("Aplicação configurada ambiente=%s", selected_environment)
    return app


def register_request_logging(app):
    @app.before_request
    def start_request_log():
        g.request_id = uuid4().hex[:12]
        g.request_started_at = time.perf_counter()
        logger.info(
            "Acesso iniciado request_id=%s metodo=%s rota=%s ip=%s",
            g.request_id,
            request.method,
            request.path,
            request.remote_addr or "desconhecido",
        )

    @app.after_request
    def finish_request_log(response):
        elapsed_ms = (time.perf_counter() - g.request_started_at) * 1000
        logger.info(
            "Acesso concluído request_id=%s metodo=%s rota=%s status=%d duracao_ms=%.2f",
            g.request_id,
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.teardown_request
    def log_unhandled_error(error):
        if error is not None:
            logger.error(
                "Falha não tratada request_id=%s metodo=%s rota=%s tipo=%s",
                getattr(g, "request_id", "indisponivel"),
                request.method,
                request.path,
                type(error).__name__,
            )


def _command_line_arguments():
    parser = argparse.ArgumentParser(description="Landing page de veículos seminovos")
    parser.add_argument(
        "--environment",
        "--env",
        choices=("production", "homologation"),
        default=APP_ENV,
        help="Modo de execução (padrão: valor de APP_ENV).",
    )
    parser.add_argument("--host", default=APP_HOST)
    parser.add_argument("--port", type=int, default=APP_PORT)
    return parser.parse_args()


def run():
    args = _command_line_arguments()
    runtime_app = create_app(environment=args.environment)
    logger.info(
        "Iniciando aplicação ambiente=%s host=%s porta=%d",
        args.environment,
        args.host,
        args.port,
    )

    if args.environment == "production":
        from waitress import serve

        serve(runtime_app, host=args.host, port=args.port)
        return

    logger.warning("Modo de homologação ativo; depuração habilitada.")
    runtime_app.run(
        host=args.host,
        port=args.port,
        debug=True,
        use_reloader=False,
    )


app = create_app()


if __name__ == "__main__":
    run()
