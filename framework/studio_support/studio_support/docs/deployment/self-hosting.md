# Self-hosting

This page runs a machine-core project and Studio on your own machine or server. Everything
here uses the real `server_support` and `studio_support` entry points.

## The pieces you host

A machine-core project is **two** processes at most:

1. **The API server** — `server_support.create_app(machine)`, served by uvicorn. This is your
   product's HTTP surface (`/api`, `/gateway`, `/health`).
2. **Studio** (optional) — `studio_support.create_studio_host_app(machine)`, a separate
   uvicorn process. Run it on an internal port or behind auth.

Both import the same `src.main:machine`, so they share plugin configuration.

## Generate Docker artifacts

```bash
machine deploy --target docker --port 8008
```

`DockerDeployer` writes:

- `Dockerfile` — `python:3.12-slim`, installs `uv`, copies `pyproject.toml`/`uv.lock`, runs
  `uv sync --no-dev`, copies the app, installs the server, and starts:
  `uvicorn src.main:machine --host 0.0.0.0 --port 8008 --factory`
- `docker-compose.yml` — one `app` service exposing `8008` with `restart: unless-stopped`
  and any `--env` values.

```bash
docker compose up --build
curl -s http://127.0.0.1:8008/health
```

> **Note:** The generated Dockerfile copies the whole project. Make sure secrets come from
> the runtime environment (or a secret manager), not from a committed `.env`.

## Run the API directly

```bash
uv sync
uv run uvicorn src.main:machine --host 0.0.0.0 --port 8008 --factory
```

Or use the dev server for a non-production run:

```bash
machine dev --host 0.0.0.0 --port 8008
```

`machine dev` adds `--reload`; do not use it in production.

## Run Studio

```bash
machine studio --host 0.0.0.0 --port 3177
```

Studio is a control plane — treat it as privileged. Put it behind authentication (a reverse
proxy with auth, or `server_support`'s gateway `api_keys` for the API side) and do not expose
`/_studio/` publicly without protection.

## Configuration and secrets

- Set `[tool.machine-core].plugin_configs` in `pyproject.toml` for non-secret settings.
- Provide secrets through the environment. `bootstrap_secrets()` loads them at startup:
  a container environment, a mounted `.env` (set `MACHINE_CORE_ROOT` to its directory), or
  Infisical (`INFISICAL_CLIENT_ID` / `INFISICAL_CLIENT_SECRET`). See
  [Secrets](../concepts/secrets.md).

```bash
docker run -e DEEPSEEK_API_KEY=... -e INFISICAL_CLIENT_ID=... -p 8008:8008 my-app
```

## Persistent data

The kernel writes runtime state under `~/.config/machine-core/`:

- `plugin-data/<name>.json` — plugin-owned runtime state,
- `plugins/<name>/manifest.json` — synced manifests,
- `plugins/<name>.json` — user config.

If you use SQLite memory, point it at a mounted volume:

```toml
[tool.machine-core.plugin_configs.memory_support]
sqlite_path = "/data/memory.db"
```

Mount `/data` as a volume so threads survive restarts.

## A systemd unit

```ini
# /etc/systemd/system/machine-api.service
[Unit]
Description=machine-core API
After=network.target

[Service]
WorkingDirectory=/srv/my-app
EnvironmentFile=/srv/my-app/.env
ExecStart=/srv/my-app/.venv/bin/uvicorn src.main:machine --host 0.0.0.0 --port 8008 --factory
Restart=always
User=machine

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now machine-api
```

## Reverse proxy

Terminate TLS at a reverse proxy (Caddy, nginx, Traefik) and forward to the uvicorn port.
Because the API sets CORS to `*` by default, tighten `cors_origins` in `create_app` if the
API is browser-facing:

```python
app = create_app(machine, cors_origins=["https://app.example.com"])
```

## Health checks

Use `/health`:

```bash
curl -fsS http://127.0.0.1:8008/health || exit 1
```

It returns `{"status": "healthy", "categories": {...}}`. A count of `0` for an expected
category means a plugin did not load — check `machine dev` logs and the manifest sync.

## Updating

```bash
git pull
uv sync
sudo systemctl restart machine-api
```

`bootstrap_secrets()` runs again and picks up rotated secrets.

---

**Read next:** [Cloud](cloud.md) · [Deployers](../guides/deployers.md)

**Source:** `community/deployer_support/deployer_support/docker.py`,
`framework/server_support/`, `framework/studio_support/`, `src/machine_core/secrets.py`.
