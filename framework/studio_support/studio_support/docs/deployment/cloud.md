# Cloud deployment

The `deployer_support` plugin gives you one contract (`Deployer`) for several targets. This
page covers what each deployer generates, how to invoke it, and how to run Studio in the
cloud.

## Deploy from the CLI

```bash
machine deploy --target <docker|vercel|cloudflare|dokploy> [--port 8008] [--env KEY=VALUE ...]
```

The command resolves a deployer from the machine registry (falling back to built-ins),
builds a `DeployConfig`, and calls `deployer.deploy(None, config)`.

## Docker

```bash
machine deploy --target docker --port 8008 --env MODE=prod
docker compose up --build
```

Generates a `Dockerfile` and `docker-compose.yml`. Push the image to any registry and run it
on ECS, Fly, Render, a VPS, or Kubernetes. See
[Self-hosting](self-hosting.md#generate-docker-artifacts).

## Vercel

```bash
machine deploy --target vercel
```

Generates:

- `vercel.json` with a `@vercel/python` build of `api/index.py` and a catch-all route,
- `api/index.py`, which imports your entry machine and exposes
  `server_support.create_app(machine)` as the handler.

Then deploy with the Vercel CLI:

```bash
npm i -g vercel
vercel --prod
```

> **Note:** Serverless functions have size and duration limits. Long-running agents,
> background workflows, and SQLite files are a poor fit for Vercel — prefer a container.

## Cloudflare

```bash
machine deploy --target cloudflare
```

Generates a `wrangler.toml` with the project name, a `[vars]` block, and a Python build
command. You provide the Worker entry (`src/worker.py`). Deploy with:

```bash
npm i -g wrangler
wrangler deploy
```

Treat the generated config as a starting point; Workers run in a constrained runtime, so
check that your plugins (and any native dependencies) are compatible.

## Dokploy

The registry and README advertise a Dokploy deployer, and `deployer_support/dokploy.py`
implements one that calls the Dokploy API:

- `application.saveEnvironment` when `env_vars` are present,
- `application.deploy` to trigger a deployment,
- `application.stop` on teardown.

It requires `application_id` in `config.extra` and `api_url` / `api_token` on the instance.

> **Important:** The Dokploy deployer is **not registered** by `DeployerSupportPlugin`, and
> the CLI's `_get_builtin_deployer` fallback covers only `docker`, `vercel`, and
> `cloudflare`. So `machine deploy --target dokploy` does not work out of the box. To use it,
> register it yourself (for example in `when_ready`) with the required fields:

```python
from deployer_support.dokploy import DokployDeployer

@machine.when_ready
async def _register_deployers():
    machine.register("deployer", "dokploy", DokployDeployer(
        api_url="https://dokploy.example.com",
        api_token="...",
    ))
```

Then `machine deploy --target dokploy` resolves it from the registry (the CLI tries the
registry first).

## Running Studio in the cloud

Studio is a separate service. Create a second application/container that runs:

```bash
machine studio --host 0.0.0.0 --port 3177
```

or, without the CLI, a small module:

```python
from studio_support.app import create_studio_host_app
from src.main import machine

app = create_studio_host_app(machine)
```

```bash
uvicorn studio_app:app --host 0.0.0.0 --port 3177
```

Guidance:

- **Do not expose `/_studio/` unauthenticated.** Put it behind SSO, a VPN, or a reverse proxy
  with auth. Studio can inspect and operate your runtime.
- Set the same secrets/environment as the API service so the machine loads identically.
- Studio reads context (`tenants`/`projects`/`environments`) from `pyproject.toml`. In a
  container, make sure the file is present (it is part of the project).
- Give Studio a persistent volume if you want its context or state to survive restarts.

## Secrets in the cloud

Never bake secrets into images. Provide them via the platform's secret store or Infisical:

| Variable | Purpose |
|----------|---------|
| Provider keys (`DEEPSEEK_API_KEY`, `OLLAMA_HOST`, ...) | Model access. |
| `INFISICAL_CLIENT_ID` / `INFISICAL_CLIENT_SECRET` | Enable remote secret loading. |
| `INFISICAL_PROJECT_ID` / `INFISICAL_ENVIRONMENT` | Which project/environment. |
| `MACHINE_STUDIO_ENABLED=1` | Marks a Studio process. |

See [Secrets](../concepts/secrets.md).

## Production checklist

- [ ] Secrets come from the platform, not the repo.
- [ ] SQLite/data paths mount a persistent volume (or use a hosted store).
- [ ] Studio is authenticated and not public.
- [ ] `/health` is wired to the platform's health check.
- [ ] CORS is narrowed if the API is browser-facing.
- [ ] Image/serverless limits are compatible with your plugins.
- [ ] `uv sync --no-dev` (the Docker deployer does this).

---

**Read next:** [Self-hosting](self-hosting.md) · [Deployers](../guides/deployers.md)

**Source:** `community/deployer_support/`,
`framework/cli_support/cli_support/commands/deploy_cmd.py`, `framework/studio_support/`.
