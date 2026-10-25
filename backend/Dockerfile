# Backend for `make dev` (docker compose). Source is bind-mounted over /app in compose;
# the virtualenv lives in /opt/venv so the host's backend/.venv is never used.
FROM python:3.12.15-slim-bookworm

RUN pip install --no-cache-dir uv==0.13.0
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uvicorn", "--factory", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
