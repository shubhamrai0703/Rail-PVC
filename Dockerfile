FROM python:3.11-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY engine ./engine
COPY backend ./backend

WORKDIR /app/backend
RUN uv sync --locked --no-dev

EXPOSE 8000
CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
