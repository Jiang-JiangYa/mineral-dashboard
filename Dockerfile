# Build the Vue client, then ship it with the Python API in a single service.
FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src ./src
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    DATA_DIR=/app/data \
    PORT=8000 \
    DEPLOYMENT_MODE=public \
    BOOTSTRAP_REFERENCE=1
WORKDIR /app
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt \
    && groupadd --gid 10001 mineral \
    && useradd --uid 10001 --gid mineral --no-create-home mineral \
    && mkdir -p /app/data \
    && chown mineral:mineral /app/data
COPY pipeline ./pipeline
COPY serve ./serve
COPY eval ./eval
COPY --from=frontend /build/dist ./dist
USER mineral
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/api/health',timeout=4)"
CMD ["python", "-m", "serve"]
