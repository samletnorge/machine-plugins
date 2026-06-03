"""Studio FastAPI sub-application and host app."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from studio_support.dependencies import (
    StudioState,
    bind_studio_state,
    build_studio_state,
    reset_bound_studio_state,
)


def _landing_page_html(state: StudioState) -> str:
    catalog = state.catalog
    attachment = state.attachment_manager.attachment()
    tenants = catalog.tenants
    projects = catalog.projects
    environments = catalog.environments
    active_context = catalog.active_context

    tenants_by_id = {tenant.id: tenant for tenant in tenants}
    projects_by_id = {project.id: project for project in projects}
    environments_by_id = {environment.id: environment for environment in environments}

    active_tenant = tenants_by_id.get(active_context.tenant_id)
    active_project = projects_by_id.get(active_context.project_id)
    active_environment = environments_by_id.get(active_context.environment_id)
    status_class = "is-attached" if attachment.status == "attached" else "is-degraded"

    target_cards = "".join(
        (
            "<article class='target-card {active_class}'>"
            "<div class='eyebrow'>{tenant}</div>"
            "<strong>{project}</strong>"
            "<div class='target-meta'><span>{environment}</span><span>{kind}</span><span>{status}</span></div>"
            "</article>"
        ).format(
            active_class=(
                "is-active"
                if project.id == active_context.project_id
                and environment.id == active_context.environment_id
                else ""
            ),
            tenant=escape(
                tenants_by_id.get(project.tenant_id).name
                if tenants_by_id.get(project.tenant_id)
                else project.tenant_id
            ),
            project=escape(project.name),
            environment=escape(environment.name),
            kind=escape(environment.connection_kind),
            status=escape(environment.status),
        )
        for project in projects
        for environment in environments
        if environment.project_id == project.id
    )

    active_target = " / ".join(
        [
            escape(active_tenant.name if active_tenant else "Unknown tenant"),
            escape(active_project.name if active_project else "Unknown project"),
            escape(active_environment.name if active_environment else "No environment"),
        ]
    )
    attachment_text = escape(attachment.machine_name or "No runtime attached")
    if attachment.error:
        attachment_text += f" · {escape(attachment.error)}"

    return f"""
<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>Machine Studio</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #07111b;
      --panel: rgba(10, 24, 39, 0.78);
      --text: #eff6ff;
      --muted: #9db2c8;
      --line: rgba(157, 178, 200, 0.2);
      --teal: #7dd3c7;
      --cyan: #67e8f9;
      --amber: #fbbf24;
      --shadow: 0 30px 100px rgba(2, 8, 23, 0.45);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(125, 211, 199, 0.22), transparent 28%),
        radial-gradient(circle at 85% 15%, rgba(103, 232, 249, 0.16), transparent 24%),
        linear-gradient(180deg, #08121d 0%, #07111b 45%, #050c13 100%);
    }}
    a {{ color: inherit; text-decoration: none; }}
    .shell {{ max-width: 1260px; margin: 0 auto; padding: 24px; }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 16px 20px;
      border: 1px solid var(--line);
      background: rgba(7, 17, 27, 0.55);
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
    }}
    .brand {{ display: flex; align-items: center; gap: 14px; }}
    .brand-mark {{
      width: 42px;
      height: 42px;
      border-radius: 14px;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, rgba(125, 211, 199, 0.24), rgba(103, 232, 249, 0.16));
      border: 1px solid rgba(125, 211, 199, 0.28);
      color: var(--teal);
      font-weight: 700;
      letter-spacing: 0.08em;
    }}
    .brand-copy strong, .hero-copy h1, .panel h2, .metric strong {{ letter-spacing: -0.03em; }}
    .brand-copy small, .eyebrow, .metric span, .target-meta, .panel p, .command-card p, .footer-note {{ color: var(--muted); }}
    .studio-link {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 12px 18px;
      border: 1px solid rgba(125, 211, 199, 0.28);
      background: linear-gradient(135deg, rgba(125, 211, 199, 0.16), rgba(103, 232, 249, 0.08));
      color: var(--text);
      font-weight: 600;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.9fr);
      gap: 24px;
      padding: 28px 0 22px;
      align-items: stretch;
    }}
    .hero-copy {{
      padding: 34px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(8, 18, 29, 0.76), rgba(11, 26, 41, 0.88));
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }}
    .hero-copy::after {{
      content: "";
      position: absolute;
      inset: auto -6% -38% 45%;
      height: 280px;
      background: radial-gradient(circle, rgba(125, 211, 199, 0.2), transparent 62%);
      pointer-events: none;
    }}
    .eyebrow {{ text-transform: uppercase; letter-spacing: 0.16em; font-size: 12px; }}
    .hero-copy h1 {{ font-size: clamp(2.9rem, 7vw, 5.8rem); line-height: 0.94; margin: 12px 0 18px; max-width: 10ch; }}
    .hero-copy p {{ font-size: 1.05rem; max-width: 58ch; margin: 0 0 22px; }}
    .hero-actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 26px; }}
    .hero-primary {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 14px 22px;
      background: linear-gradient(135deg, rgba(125, 211, 199, 0.9), rgba(103, 232, 249, 0.82));
      color: #04202c;
      font-weight: 700;
    }}
    .hero-secondary {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 14px 22px;
      border: 1px solid var(--line);
      background: rgba(8, 18, 29, 0.58);
      font-weight: 600;
    }}
    .hero-footnote {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .hero-footnote span {{
      padding: 8px 12px;
      border: 1px solid var(--line);
      background: rgba(8, 18, 29, 0.48);
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .hero-side {{ display: grid; gap: 18px; }}
    .panel {{
      padding: 22px;
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
    }}
    .panel h2 {{ margin: 10px 0 10px; font-size: 1.6rem; }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      width: fit-content;
      padding: 8px 12px;
      border: 1px solid var(--line);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.72rem;
    }}
    .status-pill::before {{ content: ""; width: 9px; height: 9px; border-radius: 999px; background: var(--amber); }}
    .status-pill.is-attached::before {{ background: var(--teal); }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; margin: 8px 0 24px; }}
    .metric {{ padding: 18px; border: 1px solid var(--line); background: rgba(6, 15, 23, 0.45); }}
    .metric span {{ display: block; margin-bottom: 8px; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; }}
    .metric strong {{ font-size: 2rem; display: block; margin-bottom: 6px; }}
    .section-grid {{ display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(300px, 0.92fr); gap: 24px; padding-bottom: 28px; }}
    .command-grid, .target-grid {{ display: grid; gap: 14px; }}
    .command-card, .target-card {{ padding: 18px; border: 1px solid var(--line); background: rgba(8, 18, 29, 0.52); }}
    .command-card code {{ display: inline-block; margin-bottom: 10px; font-size: 1rem; color: var(--cyan); }}
    .target-card strong {{ display: block; margin: 6px 0; font-size: 1.05rem; }}
    .target-meta {{ display: flex; flex-wrap: wrap; gap: 10px; font-size: 0.9rem; }}
    .target-card.is-active {{ border-color: rgba(125, 211, 199, 0.32); background: rgba(10, 28, 37, 0.72); }}
    .footer-note {{ padding-top: 8px; font-size: 0.92rem; }}
    @media (max-width: 980px) {{
      .hero, .section-grid {{ grid-template-columns: 1fr; }}
      .metric-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class='shell'>
    <header class='topbar'>
      <div class='brand'>
        <div class='brand-mark'>MS</div>
        <div class='brand-copy'>
          <strong>Machine Studio</strong><br>
          <small>Aggregated control plane for Machine runtimes</small>
        </div>
      </div>
      <a class='studio-link' href='/_studio/'>Enter Studio</a>
    </header>

    <section class='hero'>
      <div class='hero-copy'>
        <div class='eyebrow'>Mission Control</div>
        <h1>Switch the whole fleet from one surface.</h1>
        <p>Machine Studio is the operator layer for all the runtimes you have declared across projects and environments. Keep each project running where it belongs, then use Studio to move between them, inspect live runtime surfaces, and operate the system from a single place.</p>
        <div class='hero-actions'>
          <a class='hero-primary' href='/_studio/'>Open Studio</a>
          <a class='hero-secondary' href='/health'>Check health</a>
        </div>
        <div class='hero-footnote'>
          <span>Run <code>machine dev --port ...</code> per project</span>
          <span>Run <code>machine studio --port ...</code> for the control plane</span>
        </div>
      </div>

      <div class='hero-side'>
        <section class='panel'>
          <div class='eyebrow'>Active target</div>
          <h2>{active_target}</h2>
          <div class='status-pill {status_class}'>{escape(attachment.status)}</div>
          <p>{attachment_text}</p>
        </section>

        <section class='panel'>
          <div class='eyebrow'>Studio shape</div>
          <h2>{len(projects)} projects across {len(tenants)} tenants.</h2>
          <p>{len(environments)} environments are available in this catalog. Studio keeps one active target selected at a time and uses that to drive the operational surface at <code>/_studio/</code>.</p>
        </section>
      </div>
    </section>

    <section class='metric-grid'>
      <article class='metric'>
        <span>Tenants</span>
        <strong>{len(tenants)}</strong>
        <div class='footer-note'>Organization-level Studio partitions.</div>
      </article>
      <article class='metric'>
        <span>Projects</span>
        <strong>{len(projects)}</strong>
        <div class='footer-note'>Distinct Machine runtimes in the catalog.</div>
      </article>
      <article class='metric'>
        <span>Environments</span>
        <strong>{len(environments)}</strong>
        <div class='footer-note'>Switchable runtime targets for the control plane.</div>
      </article>
    </section>

    <section class='section-grid'>
      <section class='panel'>
        <div class='eyebrow'>How to operate it</div>
        <h2>Three commands. Two layers. One control plane.</h2>
        <div class='command-grid'>
          <article class='command-card'>
            <code>machine</code>
            <p>Open the TUI for the current project perspective to inspect plugins, browse the store, check services, and inspect config.</p>
          </article>
          <article class='command-card'>
            <code>machine dev --port ...</code>
            <p>Run a project runtime server on its own port. This is the runtime layer that Studio later attaches to.</p>
          </article>
          <article class='command-card'>
            <code>machine studio --port ...</code>
            <p>Run the aggregated Studio control plane, then enter <code>/_studio/</code> to switch between configured targets.</p>
          </article>
        </div>
      </section>

      <section class='panel'>
        <div class='eyebrow'>Configured targets</div>
        <h2>Everything this Studio instance can see.</h2>
        <div class='target-grid'>
          {target_cards}
        </div>
      </section>
    </section>
  </div>
</body>
</html>
"""


def create_studio_host_app(machine: Any) -> FastAPI:
    """Create the top-level Studio host app with a landing page at /."""
    studio_state = build_studio_state(machine)
    app = FastAPI(title="Machine Studio")
    app.state.studio_state = studio_state

    studio = create_studio_app(machine, studio_state=studio_state)
    app.mount("/_studio", studio)

    @app.get("/", response_class=HTMLResponse)
    async def landing_page():
        return HTMLResponse(_landing_page_html(studio_state))

    @app.get("/health")
    async def health():
        return {"status": "healthy", "studio_mount": "/_studio"}

    return app


def create_studio_app(
    machine: Any, *, studio_state: StudioState | None = None
) -> FastAPI:
    """Create the Studio FastAPI sub-application."""
    if studio_state is None:
        studio_state = build_studio_state(machine)

    app = FastAPI(title="Machine Studio", docs_url=None, redoc_url=None)
    app.state.studio_state = studio_state

    @app.middleware("http")
    async def inject_studio_state(request, call_next):
        token = bind_studio_state(request.app.state.studio_state)
        try:
            return await call_next(request)
        finally:
            reset_bound_studio_state(token)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    from studio_support.routes import (
        chat,
        config,
        dashboard,
        registry,
        resources,
        services,
        tools as tool_routes,
    )
    from studio_support.control import auth as control_auth
    from studio_support.control import browser as control_browser
    from studio_support.control import config as control_config
    from studio_support.control import context as control_context
    from studio_support.control import deploy as control_deploy
    from studio_support.control import evals as control_evals
    from studio_support.control import memory as control_memory
    from studio_support.control import observe as control_observe
    from studio_support.control import pubsub as control_pubsub
    from studio_support.control import rag as control_rag
    from studio_support.control import registry as control_registry
    from studio_support.control import runtime as control_runtime
    from studio_support.control import services as control_services
    from studio_support.control import storage as control_storage
    from studio_support.control import voice as control_voice
    from studio_support.control import workspace as control_workspace

    app.include_router(dashboard.router)
    app.include_router(registry.router)
    app.include_router(config.router)
    app.include_router(services.router)
    app.include_router(resources.router)
    app.include_router(chat.router)
    app.include_router(tool_routes.router)
    app.include_router(control_services.router)
    app.include_router(control_registry.router)
    app.include_router(control_config.router)
    app.include_router(control_context.router)
    app.include_router(control_runtime.router)
    app.include_router(control_deploy.router)
    app.include_router(control_auth.router)
    app.include_router(control_observe.router)
    app.include_router(control_memory.router)
    app.include_router(control_rag.router)
    app.include_router(control_evals.router)
    app.include_router(control_pubsub.router)
    app.include_router(control_storage.router)
    app.include_router(control_workspace.router)
    app.include_router(control_browser.router)
    app.include_router(control_voice.router)

    return app
