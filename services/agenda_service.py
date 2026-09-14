from datetime import datetime, timezone, timedelta
from config import CACHE_TIMEOUT, retorna_api
from utils.logger import logger
import requests
import threading
import time

class AgendaService:

    def __init__(self):

        self.api_url = retorna_api()

        self.session = requests.Session()

        self.lock = threading.Lock()

        self.cache = []

        self.ultima_atualizacao = None

        self.status = "Inicializando"

    def atualizar_cache(self):

        try:

            logger.info("Atualizando agenda...")

            response = self.session.get(
                self.api_url,
                timeout=(2,5)
            )

            response.raise_for_status()

            dados = response.json().get("dados", [])

            with self.lock:

                self.cache = dados
                self.ultima_atualizacao = datetime.now()
                self.status = "Online"

            logger.info(
                f"Cache atualizado ({len(dados)} registros)"
            )

        except requests.RequestException as e:

            self.status = "Offline"

            logger.error(e)

    def loop_cache(self):
        while True:

            self.atualizar_cache()

            time.sleep(CACHE_TIMEOUT)

    def iniciar(self):
        print(f"[{datetime.now()}] Respondendo")
        logger.info("Carregando cache inicial...")

        self.atualizar_cache()

        logger.info("Cache inicial carregado.")

        if hasattr(self, "_thread"):
            return

        self._thread = threading.Thread(
            target=self.loop_cache,
            daemon=True
        )

        self._thread.start()

        logger.info("Thread do cache iniciada.")

    def get_dados(self):

        with self.lock:

            return list(self.cache)

    def get_status(self):

        return self.status

    def get_quantidade(self):

        return len(self.cache)

    def get_ultima_atualizacao(self):
        if self.ultima_atualizacao:
            # Define o fuso horário de Brasília diretamente como UTC-3
            fuso_brasilia = timezone(timedelta(hours=-3))
            
            # Converte para o fuso local
            data_local = self.ultima_atualizacao.astimezone(fuso_brasilia)
            
            return data_local.strftime("%d/%m/%Y %H:%M:%S")
        return "Nunca"

    def get_cache(self):

        with self.lock:

            return {

                "status": self.status,

                "ultima_atualizacao": self.get_ultima_atualizacao(),

                "quantidade": len(self.cache),

                "dados": list(self.cache)

            }


agenda_service = AgendaService()