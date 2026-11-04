FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global @google/gemini-cli@0.66.0 \
    && npm cache clean --force
WORKDIR /app
COPY adapter.py server.py http_server.py ./
RUN mkdir -p /data/gemini && chown -R node:node /app /data/gemini && chmod 700 /data/gemini
USER node
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    GEMINI_CLI_PATH=/usr/local/bin/gemini GEMINI_MCP_STATE_DIR=/data/gemini \
    GEMINI_TELEMETRY_ENABLED=false PORT=8080 BIND_HOST=0.0.0.0
EXPOSE 8080
CMD ["python3", "http_server.py"]
