from flask import Flask

from routes.web import web_bp
from services.agenda_service import agenda_service
from utils.logger import logger

def create_app():

    app = Flask(__name__)

    # Registra as rotas
    app.register_blueprint(web_bp)

    return app


app = create_app()

# -----------------------------------------------------------------------------
# Inicialização da aplicação
# -----------------------------------------------------------------------------

logger.info("Inicializando serviço de cache...")

agenda_service.iniciar()

# -----------------------------------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )