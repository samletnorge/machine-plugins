# Deployers

`deployer_support` defines the `deployer` category and ships deployers for several targets.
Each deployer takes a `DeployConfig` and returns a `DeployResult`, so projects and the
`machine deploy` CLI can target different platforms through one contract.

## Enable it

```toml
plugins = ["deployer_support", "..."]
```

## The contract

```python
class Deployer(BaseModel, ABC):
    name: str

    async def deploy(self, machine, config: DeployConfig) -> DeployResult: ...
    async def teardown(self, deploy_id: str) -> None: ...
```

```python
class DeployConfig(BaseModel):
    target: str                 # docker, dokploy, vercel, cloudflare
    env_vars: dict[str, str] = {}
    port: int = 8008
    region: str | None = None
    replicas: int = 1
    extra: dict[str, Any] = {}

class DeployResult(BaseModel):
    status: DeployStatus
    url: str | None = None
    message: str | None = None
    error: str | None = None
    deploy_id: str | None = None
    logs: list[str] = []
    metadata: dict[str, Any] = {}
```

`DeployStatus` is `pending`, `building`, `deploying`, `success`, or `failed`.

## Built-in deployers

`DeployerSupportPlugin` registers:

| Name | What it generates |
|------|-------------------|
| `deployer/docker` | A `Dockerfile` and `docker-compose.yml`. |
| `deployer/vercel` | `vercel.json` and `api/index.py`. |
| `deployer/cloudflare` | `wrangler.toml`. |

> **Note:** A `DokployDeployer` class exists in `deployer_support/dokploy.py` and the category
> advertises Dokploy, but it is **not registered** by the plugin and is **not** in the CLI's
> `_get_builtin_deployer` fallback map (which covers `docker`, `vercel`, `cloudflare`). As a
> result, `machine deploy --target dokploy` is not usable out of the box today despite the
> README and registry description. Register it yourself (with `api_url` / `api_token`) if you
> need it.

## The `machine deploy` command

```bash
machine deploy --target docker --port 8008
machine deploy --target vercel --env API_KEY=... --env MODE=prod
```

The command:

1. finds the project root and reads `entry`,
2. builds a `DeployConfig` with `extra = {"output_dir": <root>, "entry": <entry>}`,
3. tries to resolve a deployer from the machine registry (`machine.resolve("deployer", target)`),
4. falls back to `_get_builtin_deployer(target)`,
5. runs `await deployer.deploy(None, config)` and reports the result.

Errors are printed and the command exits non-zero on failure.

## What each deployer produces

### Docker

```python
from deployer_support.docker import DockerDeployer

result = await DockerDeployer().deploy(None, DeployConfig(
    target="docker", port=8008, env_vars={"MODE": "prod"},
    extra={"output_dir": ".", "entry": "src.main:machine"},
))
```

Writes a `Dockerfile` that copies `pyproject.toml`/`uv.lock`, runs `uv sync --no-dev`, and
starts `uvicorn <module>:<attr> --host 0.0.0.0 --port <port> --factory`, plus a
`docker-compose.yml`.

### Vercel

Writes `vercel.json` and `api/index.py`, where the handler imports your entry machine and
`server_support.create_app(machine)`.

### Cloudflare

Writes a `wrangler.toml` with a `[vars]` block and a Python build command. Treat it as a
starting config; you provide the Worker entry (`src/worker.py`).

### Dokploy (unregistered)

`DokployDeployer` has required `api_url` and `api_token` fields and calls the Dokploy API
(`application.deploy`, optionally `application.saveEnvironment`, then `application.stop` on
teardown). It needs `application_id` in `config.extra`.

## Deployers over HTTP

```
GET  /api/deployer
POST /api/deployer/{name}/deploy
POST /api/deployer/{name}/teardown
```

## Studio

Studio renders a **Deploy** domain backed by `/api/deploy/targets`. See
[Studio](studio.md#domains).

## Writing your own deployer

```python
from deployer_support.base import Deployer, DeployConfig, DeployResult, DeployStatus

class FlyDeployer(Deployer):
    name: str = "fly"

    async def deploy(self, machine, config: DeployConfig) -> DeployResult:
        # ... generate fly.toml, run `fly deploy`, etc.
        return DeployResult(status=DeployStatus.SUCCESS, url="https://app.fly.dev")

    async def teardown(self, deploy_id: str) -> None:
        ...
```

Register it from a thin plugin or your project with the `deployer:register` capability.

---

**Read next:** [Self-hosting](../deployment/self-hosting.md) ·
[Cloud](../deployment/cloud.md) · [CLI](../reference/cli.md)

**Source:** `community/deployer_support/`, `framework/cli_support/cli_support/commands/deploy_cmd.py`.
