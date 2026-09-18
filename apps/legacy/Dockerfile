FROM ghcr.io/astral-sh/uv:0.11.2 AS uv

FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/apps/legacy/src \
    PATH=/app/.venv/bin:$PATH

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen

COPY apps/legacy ./apps/legacy

EXPOSE 8000

CMD ["sh", "-c", "flask --app legacy_app:create_app db-init && exec gunicorn --bind 0.0.0.0:8000 'legacy_app:create_app()'"]
