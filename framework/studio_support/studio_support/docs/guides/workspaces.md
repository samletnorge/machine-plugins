# Workspaces

`workspace_support` gives agents an isolated place to work: a scoped filesystem, a sandbox
for running code, and a skills system for markdown-based specialization. It defines the
`sandbox` and `filesystem` categories and ships an `AgentWorkspace` that composes them.

## Enable it

```toml
plugins = ["workspace_support", "..."]
```

For Docker-backed sandboxes you also need Docker; without it, `sandbox_type="docker"` fails
loudly via `require_docker()`.

## The categories

| Category | Operations | Implementations |
|----------|-----------|-----------------|
| `sandbox` | `execute` (POST), `list` (GET) | `LocalSandbox`, `DockerSandbox` |
| `filesystem` | `read` (POST), `write` (POST), `list` (GET) | `LocalFileSystem` |

> **Note:** `WorkspaceSupportPlugin` registers the categories but no concrete sandbox or
> filesystem. Register your own (or use `AgentWorkspace`, which builds them for you).

## `LocalFileSystem`

`LocalFileSystem(root=...)` is root-scoped: paths are resolved inside `root` so an agent
cannot escape it.

```python
from workspace_support.filesystem import LocalFileSystem

fs = LocalFileSystem(root="./workspace")
await fs.write("notes/todo.md", b"# Todo\n")
data = await fs.read("notes/todo.md")
entries = await fs.list("notes")
await fs.delete("notes/todo.md")
```

`FileInfo` entries describe each listed path.

## Sandboxes

A sandbox executes code and supports file upload/download:

```python
from workspace_support.sandbox import LocalSandbox

sandbox = LocalSandbox(work_dir="./scratch")
result = await sandbox.execute("print(2 ** 10)", language="python", timeout=10)
print(result.exit_code, result.stdout)   # 0, "1024\n"
print(result.success)                    # True when exit_code == 0 and not timed out

await sandbox.upload("data.csv", b"a,b\n1,2\n")
blob = await sandbox.download("out.txt")
await sandbox.cleanup()
```

`ExecutionResult` has `exit_code`, `stdout`, `stderr`, `timed_out`, and a computed
`success`. `LocalSandbox` supports `python` and `bash` and kills the process on timeout.

`DockerSandbox` runs commands inside a container, giving strong isolation at the cost of
requiring Docker.

Both are async context managers.

## `AgentWorkspace`

`WorkspaceConfig` + `AgentWorkspace.create()` assemble everything:

```python
from workspace_support.workspace import AgentWorkspace, WorkspaceConfig

workspace = AgentWorkspace.create(WorkspaceConfig(
    root_dir="./agent-workspace",
    ephemeral=True,
    skills_dir="./skills",
    sandbox_type="local",          # or "docker"
))

async with workspace:
    await workspace.filesystem.write("main.py", b"print('hi')\n")
    result = await workspace.sandbox.execute("python main.py")
    print(result.stdout)
```

| `WorkspaceConfig` field | Default | Meaning |
|-------------------------|---------|---------|
| `root_dir` | required | Root for the filesystem and local sandbox. |
| `ephemeral` | `True` | Hint that the workspace is disposable. |
| `skills_dir` | `None` | If set, skills are discovered from here. |
| `sandbox_type` | `"local"` | `"local"` or `"docker"`. Unknown values fall back to local. |

`workspace.cleanup()` (called by the async context manager) releases the sandbox.

## Skills

A **skill** is a markdown file with a fixed structure. `SkillsManager` discovers files,
parses metadata, and loads full content on demand.

```python
from workspace_support.skills import SkillsManager

skills = SkillsManager("./skills")
skills.discover()
skills.list_names()
meta = skills.get_metadata("release-notes")
content = skills.load("release-notes")
```

Skill file format:

```markdown
# Skill: release-notes

## Description
Write concise release notes from a changelog.

## When to Use
- The user asks for release notes.
- A changelog file is present.
```

`SkillMetadata` exposes `name`, `description`, `when_to_use`, and `file_path`. A file
without a `# Skill: <name>` header is ignored.

## Registering workspace pieces

To expose a sandbox or filesystem over HTTP/Studio, register it:

```python
@machine.when_ready
async def _register_workspace():
    machine.register("filesystem", "default", LocalFileSystem(root="./workspace"))
    machine.register("sandbox", "local", LocalSandbox(work_dir="./scratch"))
```

Routes: `GET /api/filesystem`, `POST /api/filesystem/{name}/read|write`, `GET/POST
/api/sandbox/{name}/execute`.

## Tips

- Prefer `DockerSandbox` for untrusted code; `LocalSandbox` is not a security boundary.
- Keep `root_dir` per agent or per task to avoid cross-contamination.
- Skills pair well with coding agents: discover at startup, inject the matching skill into
  the system prompt.

---

**Read next:** [Browser](browser.md) · [Deployers](deployers.md)

**Source:** `community/workspace_support/`.
