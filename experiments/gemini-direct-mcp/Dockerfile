FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global @google/gemini-cli@0.66.0 \
    && npm cache clean --force
WORKDIR /app
COPY adapter.py server.py http_server.py ./
RUN python3 -c 'import json,pathlib; from adapter import CLI_SYSTEM_SETTINGS; p=pathlib.Path("/etc/gemini-cli/settings.json"); p.parent.mkdir(mode=0o755,parents=True,exist_ok=True); p.write_text(json.dumps(CLI_SYSTEM_SETTINGS)); p.chmod(0o644)'
RUN mkdir -p /data/gemini && chown -R node:node /app /data/gemini && chmod 700 /data/gemini
USER node
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    GEMINI_CLI_PATH=/usr/local/bin/gemini GEMINI_MCP_STATE_DIR=/data/gemini \
    GEMINI_CLI_SYSTEM_SETTINGS_PATH=/etc/gemini-cli/settings.json \
    GEMINI_TELEMETRY_ENABLED=false PORT=8080 BIND_HOST=0.0.0.0
EXPOSE 8080
CMD ["python3", "http_server.py"]
