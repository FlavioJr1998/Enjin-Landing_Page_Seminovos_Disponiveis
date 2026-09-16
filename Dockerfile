FROM python:3.14.7-slim AS builder

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN python -m venv "${VIRTUAL_ENV}"

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt


FROM python:3.14.7-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --no-create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appgroup /app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appgroup app.py config.py ./
COPY --chown=appuser:appgroup routes ./routes
COPY --chown=appuser:appgroup services ./services
COPY --chown=appuser:appgroup static ./static
COPY --chown=appuser:appgroup templates ./templates
COPY --chown=appuser:appgroup utils ./utils

USER 10001:10001

EXPOSE 5000

CMD ["python", "app.py", "--environment", "production", "--host", "0.0.0.0", "--port", "5000"]
