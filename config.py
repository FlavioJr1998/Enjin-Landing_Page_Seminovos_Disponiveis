import os

def retorna_api():

    return os.getenv(
        "API_INTERNA_URL",
        "http://172.16.201.130:8000/api/v1/oficina/agenda/todas"
    )


CACHE_TIMEOUT = 60