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

    install_command = (
        "curl -fsSL https://gist.githubusercontent.com/valiantlynx/"
        "c3eaf552adf9aecff7c0366a25ff1e99/raw/install.sh | bash"
    )
    active_target = " / ".join(
        [
            escape(active_tenant.name if active_tenant else "Unknown tenant"),
            escape(active_project.name if active_project else "Unknown project"),
            escape(active_environment.name if active_environment else "No environment"),
        ]
    )

    ecosystem_cards = "".join(
        [
            "<span class='ecosystem-pill'>Agents</span>",
            "<span class='ecosystem-pill'>Tools</span>",
            "<span class='ecosystem-pill'>Model providers</span>",
            "<span class='ecosystem-pill'>Workflows</span>",
            "<span class='ecosystem-pill'>RAG</span>",
            "<span class='ecosystem-pill'>Browser</span>",
            "<span class='ecosystem-pill'>Workspace</span>",
            "<span class='ecosystem-pill'>Deploy</span>",
        ]
    )

    studio_preview = f"""
      <article class='studio-preview-card'>
        <span class='card-label'>Studio</span>
        <strong>{len(projects)} projects across {len(environments)} environments</strong>
        <p>When one project becomes many, Studio gives you one place to switch between them.</p>
        <div class='studio-preview-strip'>
          <span>{active_target}</span>
          <span class='studio-preview-sep'></span>
          <span>/_studio/</span>
        </div>
      </article>
    """

    command_markup = (
        "<div class='command-stage'>"
        "<div class='command-orbit orbit-a'></div>"
        "<div class='command-orbit orbit-b'></div>"
        "<div class='command-core'>"
        "<span class='command-kicker'>Install Machine</span>"
        "<div class='command-shell'>"
        f"<code id='install-command'>{escape(install_command)}</code>"
        "<button type='button' class='copy-button icon-only' id='copy-install' aria-label='Copy install command' title='Copy install command'>"
        "<span class='copy-icon' aria-hidden='true'>⧉</span>"
        "</button>"
        "</div>"
        "<p class='command-caption'>Paste this once. Then start building.</p>"
        "</div>"
        "</div>"
    )

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
      --panel: rgba(10, 24, 39, 0.82);
      --panel-strong: rgba(8, 19, 31, 0.94);
      --text: #eff6ff;
      --muted: #9db2c8;
      --line: rgba(157, 178, 200, 0.2);
      --teal: #7dd3c7;
      --cyan: #67e8f9;
      --violet: #a78bfa;
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
    .shell {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
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
      width: 52px;
      height: 52px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 16px;
      background: linear-gradient(180deg, rgba(8, 18, 29, 0.96), rgba(12, 24, 37, 0.92));
      border: 1px solid rgba(125, 211, 199, 0.18);
      box-shadow: 0 18px 36px rgba(3, 10, 18, 0.28);
    }}
    .brand-mark svg {{
      display: block;
      width: 36px;
      height: 36px;
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
    .hero {{ display: grid; gap: 26px; padding: 46px 0 22px; justify-items: center; text-align: center; }}
    .hero-copy {{
      width: min(980px, 100%);
      padding: 24px 0 0;
      background: none;
      border: 0;
      box-shadow: none;
      position: relative;
      overflow: hidden;
    }}
    .eyebrow {{ text-transform: uppercase; letter-spacing: 0.16em; font-size: 12px; }}
    .hero-copy h1 {{ font-size: clamp(3.6rem, 8vw, 7rem); line-height: 0.88; margin: 16px auto 18px; max-width: 11ch; }}
    .hero-copy p {{ font-size: 1.08rem; max-width: 56ch; margin: 0 auto 18px; }}
    .hero-actions {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; margin: 14px 0 0; }}
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
    .hero-tagline {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      border: 1px solid rgba(125, 211, 199, 0.22);
      background: rgba(8, 18, 29, 0.56);
      color: var(--muted);
      font-size: 0.92rem;
      margin-bottom: 10px;
    }}
    .hero-tagline::before {{
      content: "";
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--teal), var(--cyan));
      box-shadow: 0 0 18px rgba(125, 211, 199, 0.9);
    }}
    .hero-subgrid {{ width: min(920px, 100%); margin-top: 6px; }}
    .command-stage {{
      position: relative;
      min-height: 332px;
      display: grid;
      place-items: center;
      overflow: hidden;
      border: 1px solid rgba(125, 211, 199, 0.14);
      background:
        radial-gradient(circle at 18% 24%, rgba(125, 211, 199, 0.14), transparent 26%),
        radial-gradient(circle at 80% 18%, rgba(167, 139, 250, 0.14), transparent 24%),
        linear-gradient(180deg, rgba(9, 20, 31, 0.9), rgba(5, 12, 20, 0.94));
      box-shadow: var(--shadow);
    }}
    .command-orbit {{
      position: absolute;
      border: 1px solid rgba(125, 211, 199, 0.14);
      border-radius: 999px;
      animation: drift 14s linear infinite;
    }}
    .orbit-a {{ width: 560px; height: 560px; opacity: 0.6; }}
    .orbit-b {{ width: 380px; height: 380px; animation-direction: reverse; animation-duration: 11s; opacity: 0.45; }}
    .command-core {{
      position: relative;
      z-index: 1;
      width: min(820px, calc(100% - 44px));
      padding: 34px 28px;
      background: linear-gradient(180deg, rgba(12, 25, 39, 0.88), rgba(8, 17, 27, 0.95));
      border: 1px solid rgba(125, 211, 199, 0.18);
      box-shadow: 0 28px 90px rgba(3, 10, 18, 0.48);
    }}
    .command-kicker {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 16px;
      color: var(--cyan);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.18em;
    }}
    .command-kicker::before {{
      content: "";
      width: 28px;
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--cyan));
    }}
    .command-shell {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: center;
      padding: 20px 22px;
      border: 1px solid rgba(125, 211, 199, 0.16);
      background: rgba(5, 12, 20, 0.9);
      margin-bottom: 18px;
    }}
    .command-shell code {{
      display: block;
      text-align: left;
      color: var(--text);
      font-size: clamp(0.92rem, 1.3vw, 1.08rem);
      line-height: 1.8;
      word-break: break-word;
    }}
    .copy-button {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 14px 16px;
      border: 1px solid rgba(125, 211, 199, 0.22);
      background: linear-gradient(135deg, rgba(125, 211, 199, 0.18), rgba(103, 232, 249, 0.12));
      color: var(--text);
      font: inherit;
      cursor: pointer;
      transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
    }}
    .copy-button.icon-only {{
      justify-content: center;
      width: 58px;
      height: 58px;
      padding: 0;
      border-radius: 999px;
    }}
    .copy-button:hover {{
      transform: translateY(-1px);
      border-color: rgba(125, 211, 199, 0.42);
      background: linear-gradient(135deg, rgba(125, 211, 199, 0.26), rgba(103, 232, 249, 0.18));
    }}
    .copy-button.copied {{
      border-color: rgba(125, 211, 199, 0.5);
      box-shadow: 0 0 0 10px rgba(125, 211, 199, 0.08);
    }}
    .copy-icon {{
      display: inline-grid;
      place-items: center;
      width: 34px;
      height: 34px;
      border-radius: 999px;
      background: rgba(125, 211, 199, 0.14);
      animation: pulse 2.6s ease-in-out infinite;
      font-size: 1rem;
    }}
    .command-caption {{ margin: 0; font-size: 0.98rem; color: var(--muted); }}
    .hero-grid {{ display: grid; gap: 18px; margin-top: 18px; }}
    .hero-card-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
    .info-card, .section-card, .studio-preview-card, .example-card {{
      padding: 20px;
      border: 1px solid var(--line);
      background: rgba(8, 18, 29, 0.56);
      box-shadow: var(--shadow);
    }}
    .info-card strong, .section-card strong, .studio-preview-card strong, .example-card strong {{
      display: block;
      margin: 8px 0 10px;
      font-size: 1.14rem;
      letter-spacing: -0.02em;
    }}
    .info-card p, .section-card p, .studio-preview-card p, .example-card p {{ margin: 0; color: var(--muted); }}
    .section-stack {{ display: grid; gap: 18px; padding-bottom: 34px; }}
    .section-shell {{
      padding: 26px;
      border: 1px solid var(--line);
      background: var(--panel-strong);
      box-shadow: var(--shadow);
    }}
    .section-shell h2 {{ margin: 8px 0 8px; font-size: 2rem; letter-spacing: -0.03em; }}
    .section-shell > p {{ margin: 0; color: var(--muted); max-width: 62ch; }}
    .triad {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 18px; }}
    .ecosystem-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }}
    .ecosystem-pill {{
      display: inline-flex;
      justify-content: center;
      align-items: center;
      padding: 16px 14px;
      border: 1px solid rgba(125, 211, 199, 0.2);
      background: rgba(8, 18, 29, 0.5);
      color: var(--text);
      font-weight: 600;
    }}
    .studio-preview-strip {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 14px;
      color: var(--text);
    }}
    .studio-preview-sep {{ width: 18px; height: 1px; background: linear-gradient(90deg, rgba(125, 211, 199, 0.4), transparent); }}
    .footer-bar {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
      padding: 20px 0 40px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .footer-links {{ display: flex; gap: 16px; flex-wrap: wrap; }}
    .footer-links a {{ color: var(--text); }}
    .panel {{
      padding: 22px;
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
    }}
    .card-label {{ color: var(--cyan); text-transform: uppercase; letter-spacing: 0.16em; font-size: 0.75rem; }}
    .footer-note {{ padding-top: 8px; font-size: 0.92rem; }}
    @keyframes pulse {{
      0%, 100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(125, 211, 199, 0.18); }}
      50% {{ transform: scale(1.08); box-shadow: 0 0 0 14px rgba(125, 211, 199, 0); }}
    }}
    @keyframes drift {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}
    @media (max-width: 980px) {{
      .hero-card-grid,
      .triad,
      .ecosystem-grid {{ grid-template-columns: 1fr; }}
      .command-shell {{ grid-template-columns: 1fr; }}
      .copy-button.icon-only {{ width: 58px; }}
    }}
  </style>
</head>
<body>
  <div class='shell'>
    <header class='topbar'>
      <div class='brand'>
        <div class='brand-mark' aria-hidden='true'>
          <svg viewBox='0 0 48 48' fill='none' xmlns='http://www.w3.org/2000/svg'>
            <defs>
              <linearGradient id='machine-mark-gradient' x1='6' y1='6' x2='42' y2='42' gradientUnits='userSpaceOnUse'>
                <stop stop-color='#7DD3C7'/>
                <stop offset='1' stop-color='#67E8F9'/>
              </linearGradient>
            </defs>
            <path d='M9 38V10L24 27L39 10V38' stroke='url(#machine-mark-gradient)' stroke-width='7' stroke-linecap='round' stroke-linejoin='round'/>
            <circle cx='9' cy='10' r='3.2' fill='#07111B' stroke='url(#machine-mark-gradient)' stroke-width='2'/>
            <circle cx='24' cy='27' r='3.2' fill='#07111B' stroke='url(#machine-mark-gradient)' stroke-width='2'/>
            <circle cx='39' cy='10' r='3.2' fill='#07111B' stroke='url(#machine-mark-gradient)' stroke-width='2'/>
          </svg>
        </div>
        <div class='brand-copy'>
          <strong>Machine Core</strong><br>
          <small>One system to build, run, and manage AI projects</small>
        </div>
      </div>
      <a class='studio-link' href='/_studio/'>Open Studio</a>
    </header>

    <section class='hero'>
      <div class='hero-copy'>
        <div class='hero-tagline'>From the first project to everything that comes after</div>
        <div class='eyebrow'>Machine Core</div>
        <h1>One system to build, run, and manage AI projects.</h1>
        <p>Start with one project, keep shipping, and grow into bigger setups without changing how the system works underneath you.</p>
        <div class='hero-actions'>
          <a class='hero-primary' href='/health'>Get started</a>
          <a class='hero-secondary' href='/_studio/'>Open Studio</a>
        </div>
      </div>

      <div class='hero-subgrid'>
        {command_markup}
      </div>
    </section>

    <section class='section-stack'>
      <section class='section-shell'>
        <div class='eyebrow'>What Machine Core is</div>
        <h2>Start simple, then grow without starting over.</h2>
        <p>Machine is built so the way you begin still makes sense when the project gets bigger.</p>
        <div class='hero-card-grid'>
          <article class='info-card'>
            <span class='card-label'>Projects</span>
            <strong>Create and work inside projects</strong>
            <p>Work inside real projects.</p>
          </article>
          <article class='info-card'>
            <span class='card-label'>Plugins</span>
            <strong>Compose behavior with plugins</strong>
            <p>Add capabilities without rebuilding everything.</p>
          </article>
          <article class='info-card'>
            <span class='card-label'>Scale</span>
            <strong>Run one project or many</strong>
            <p>Stay small or grow later.</p>
          </article>
        </div>
      </section>

      <section class='section-shell'>
        <div class='eyebrow'>Why Machine Core feels different</div>
        <h2>It does not force every project into the same shape.</h2>
        <p>The same system already supports small demo apps, scaffolded projects, and larger aggregate setups.</p>
        <div class='triad'>
          <article class='section-card'>
            <span class='card-label'>One kernel</span>
            <strong>Small core, bigger system</strong>
            <p>A small core with room to grow.</p>
          </article>
          <article class='section-card'>
            <span class='card-label'>Many plugins</span>
            <strong>Framework and community layers</strong>
            <p>Capabilities expand through plugins.</p>
          </article>
          <article class='section-card'>
            <span class='card-label'>Local to remote</span>
            <strong>One project or many runtimes</strong>
            <p>Start local, then stretch further when needed.</p>
          </article>
        </div>
      </section>

      <section class='section-shell'>
        <div class='eyebrow'>Studio</div>
        <h2>Studio shows up when one project becomes many.</h2>
        <p>Use Studio when you want one place to switch between projects and environments.</p>
        {studio_preview}
      </section>

      <section class='section-shell'>
        <div class='eyebrow'>Plugin ecosystem</div>
        <h2>Capabilities grow through the plugin ecosystem.</h2>
        <p>Grow by adding capabilities instead of switching products.</p>
        <div class='ecosystem-grid'>
          {ecosystem_cards}
        </div>
      </section>
    </section>

    <footer class='footer-bar'>
      <div>Machine Core is the main system. Studio is there when you need a bigger view.</div>
      <div class='footer-links'>
        <a href='/health'>Get started</a>
        <a href='/_studio/'>Open Studio</a>
      </div>
    </footer>
    <script>
      (() => {{
        const button = document.getElementById('copy-install');
        const code = document.getElementById('install-command');
        if (!button || !code || !navigator.clipboard) return;

        button.addEventListener('click', async () => {{
          try {{
            await navigator.clipboard.writeText(code.textContent || '');
            button.classList.add('copied');
            button.setAttribute('aria-label', 'Copied install command');
            button.setAttribute('title', 'Copied');
            window.setTimeout(() => {{
              button.classList.remove('copied');
              button.setAttribute('aria-label', 'Copy install command');
              button.setAttribute('title', 'Copy install command');
            }}, 1400);
          }} catch (_error) {{
            button.setAttribute('title', 'Copy failed');
            window.setTimeout(() => {{
              button.setAttribute('title', 'Copy install command');
            }}, 1400);
          }}
        }});
      }})();
    </script>
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
