"""Studio FastAPI sub-application and host app."""

from __future__ import annotations

from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from studio_support.dependencies import (
    StudioState,
    bind_studio_state,
    build_studio_state,
    reset_bound_studio_state,
)


def _machine_lifespan(machine: Any):
    """Start the Machine once, so plugins and when_ready callbacks run."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        categories = (
            machine.list_categories() if hasattr(machine, "list_categories") else []
        )
        if hasattr(machine, "start") and not categories:
            await machine.start()
        yield

    return lifespan


def _machine_favicon_svg() -> str:
    return """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48' fill='none'>
  <rect width='48' height='48' rx='12' fill='#07111B'/>
  <defs>
    <linearGradient id='favicon-machine-mark-gradient' x1='6' y1='6' x2='42' y2='42' gradientUnits='userSpaceOnUse'>
      <stop stop-color='#7DD3C7'/>
      <stop offset='1' stop-color='#67E8F9'/>
    </linearGradient>
  </defs>
  <path d='M9 38V10L24 27L39 10V38' stroke='url(#favicon-machine-mark-gradient)' stroke-width='7' stroke-linecap='round' stroke-linejoin='round'/>
  <circle cx='9' cy='10' r='3.2' fill='#07111B' stroke='url(#favicon-machine-mark-gradient)' stroke-width='2'/>
  <circle cx='24' cy='27' r='3.2' fill='#07111B' stroke='url(#favicon-machine-mark-gradient)' stroke-width='2'/>
  <circle cx='39' cy='10' r='3.2' fill='#07111B' stroke='url(#favicon-machine-mark-gradient)' stroke-width='2'/>
</svg>"""


def _landing_page_html(state: StudioState) -> str:
    catalog = state.catalog
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

    def _icon(path: str) -> str:
        return (
            "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            "stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round' "
            f"aria-hidden='true'>{path}</svg>"
        )

    build_items = [
        (
            "Agents",
            "Register user-facing agents with tools, memory, and their own run loop.",
            "<circle cx='12' cy='8' r='3.4'/><path d='M5.5 20a6.5 6.5 0 0 1 13 0'/>",
        ),
        (
            "Tools",
            "Define typed handlers and expose them over a stable runtime API.",
            "<path d='M14.7 6.3a4 4 0 0 0 3 5.5L10 19.5 4.5 14l7.7-7.7a4 4 0 0 0 2.5 0Z'/><path d='m13 3 8 8'/>",
        ),
        (
            "RAG",
            "Compose pipelines, chunkers, rerankers, and retrievers as plugins.",
            "<circle cx='11' cy='11' r='6'/><path d='m20 20-4.2-4.2'/>",
        ),
        (
            "Memory",
            "Thread history and working memory with a persistent storage backend.",
            "<path d='m12 4 8 4-8 4-8-4Z'/><path d='m4 12 8 4 8-4'/><path d='m4 16 8 4 8-4'/>",
        ),
        (
            "Workflows",
            "Model sequential and parallel steps as an inspectable graph.",
            "<rect x='4' y='4' width='6' height='6' rx='1.4'/><rect x='14' y='4' width='6' height='6' rx='1.4'/><rect x='9' y='14' width='6' height='6' rx='1.4'/><path d='M10 7h4'/><path d='M12 10v4'/>",
        ),
        (
            "Evals",
            "Score prompts and models with datasets, scorers, and run comparisons.",
            "<path d='M4 19h16'/><path d='M7 16V9'/><path d='M12 16V5'/><path d='M17 16v-7'/>",
        ),
        (
            "MCP",
            "Connect Model Context Protocol servers as first-class tool providers.",
            "<path d='M9 7V5a3 3 0 0 1 6 0v2'/><rect x='5' y='7' width='14' height='12' rx='2.4'/>",
        ),
        (
            "Studio",
            "One control plane to switch contexts, inspect the fleet, and operate.",
            "<rect x='3.5' y='4' width='17' height='4' rx='1.4'/><rect x='3.5' y='11' width='7' height='9' rx='1.4'/><rect x='13.5' y='11' width='7' height='9' rx='1.4'/>",
        ),
    ]

    build_cards = "".join(
        (
            "<article class='build-card reveal'>"
            f"<span class='build-icon'>{_icon(path)}</span>"
            f"<h3>{title}</h3>"
            f"<p>{copy}</p>"
            "</article>"
        )
        for title, copy, path in build_items
    )

    feature_items = [
        (
            "Project-scoped",
            "Everything is scoped to a project and environment, so growing to many projects never means starting over.",
        ),
        (
            "Composable plugins",
            "Add agents, tools, workflows, and storage as plugins instead of rewriting the core system.",
        ),
        (
            "Model gateway",
            "Put OpenAI, Anthropic, Google, Groq, and local models behind one provider contract.",
        ),
        (
            "Stable runtime API",
            "A generated /api/* data plane that stays consistent as your registry changes.",
        ),
        (
            "Operator control plane",
            "Studio inspects the fleet, switches contexts, and tests tools without leaving the browser.",
        ),
        (
            "Observable by default",
            "Traces, evaluations, and memory inspection live next to the code that produces them.",
        ),
    ]

    feature_cards = "".join(
        (
            "<article class='feature-card reveal'>"
            f"<span class='feature-index'>{index:02d}</span>"
            f"<h3>{title}</h3>"
            f"<p>{copy}</p>"
            "</article>"
        )
        for index, (title, copy) in enumerate(feature_items, start=1)
    )

    stats = [
        (len(tenants), "Tenants"),
        (len(projects), "Projects"),
        (len(environments), "Environments"),
        (len(build_items), "Capability areas"),
    ]
    stat_cells = "".join(
        f"<div class='stat'><strong>{value}</strong><span>{label}</span></div>"
        for value, label in stats
    )

    style = """
    * { box-sizing: border-box; }
    :root {
        color-scheme: dark;
        --bg: #060d16;
        --bg-soft: #0a1622;
        --panel: rgba(15, 27, 42, 0.68);
        --panel-strong: rgba(11, 21, 33, 0.92);
        --text: #eaf2fb;
        --muted: #93a7bd;
        --line: rgba(148, 172, 198, 0.16);
        --line-strong: rgba(148, 172, 198, 0.28);
        --teal: #7dd3c7;
        --cyan: #67e8f9;
        --violet: #a78bfa;
        --amber: #fbbf24;
        --grad: linear-gradient(135deg, #7dd3c7, #67e8f9);
        --radius: 18px;
        --shadow: 0 30px 90px rgba(2, 8, 23, 0.55);
        --font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
        --font-display: 'Sora', 'Inter', sans-serif;
    }
    html { scroll-behavior: smooth; }
    body {
        margin: 0;
        min-height: 100vh;
        font-family: var(--font-sans);
        color: var(--text);
        -webkit-font-smoothing: antialiased;
        background:
            radial-gradient(60rem 40rem at 12% -8%, rgba(125, 211, 199, 0.2), transparent 55%),
            radial-gradient(50rem 36rem at 92% 4%, rgba(103, 232, 249, 0.14), transparent 55%),
            radial-gradient(46rem 34rem at 50% 120%, rgba(167, 139, 250, 0.12), transparent 58%),
            linear-gradient(180deg, #08121d 0%, #060d16 46%, #04090f 100%);
        background-attachment: fixed;
    }
    a { color: inherit; text-decoration: none; }
    h1, h2, h3 { font-family: var(--font-display); letter-spacing: -0.035em; margin: 0; }
    p { margin: 0; }
    img, svg { display: block; }
    .container { width: min(1180px, calc(100% - 44px)); margin: 0 auto; }
    .nav {
        position: sticky;
        top: 0;
        z-index: 60;
        backdrop-filter: blur(18px);
        background: rgba(7, 15, 25, 0.72);
        border-bottom: 1px solid var(--line);
    }
    .nav-inner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        min-height: 68px;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-mark {
        width: 40px; height: 40px;
        display: inline-flex; align-items: center; justify-content: center;
        border-radius: 12px;
        background: linear-gradient(180deg, rgba(12, 24, 38, 0.96), rgba(9, 18, 29, 0.9));
        border: 1px solid rgba(125, 211, 199, 0.26);
        box-shadow: 0 14px 34px rgba(3, 10, 18, 0.4);
    }
    .brand-mark svg { width: 26px; height: 26px; }
    .brand-copy strong { font-family: var(--font-display); font-size: 1.02rem; letter-spacing: -0.02em; display: block; }
    .brand-copy small { color: var(--muted); font-size: 0.76rem; }
    .nav-links { display: flex; align-items: center; gap: 26px; }
    .nav-links a { color: var(--muted); font-size: 0.92rem; font-weight: 500; transition: color 160ms ease; }
    .nav-links a:hover { color: var(--text); }
    .nav-cta {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 10px 16px;
        border-radius: 999px;
        border: 1px solid rgba(125, 211, 199, 0.3);
        background: linear-gradient(135deg, rgba(125, 211, 199, 0.18), rgba(103, 232, 249, 0.1));
        font-size: 0.9rem; font-weight: 600;
        transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
    }
    .nav-cta:hover { transform: translateY(-1px); border-color: rgba(125, 211, 199, 0.5); }

    .hero { position: relative; padding: 96px 0 64px; text-align: center; overflow: hidden; }
    .hero::before {
        content: "";
        position: absolute; inset: -20% 10% auto 10%; height: 480px;
        background: radial-gradient(circle at center, rgba(125, 211, 199, 0.16), transparent 62%);
        pointer-events: none;
    }
    .badge {
        display: inline-flex; align-items: center; gap: 10px;
        padding: 8px 15px;
        border-radius: 999px;
        border: 1px solid var(--line-strong);
        background: rgba(9, 19, 31, 0.7);
        color: var(--muted);
        font-size: 0.82rem;
    }
    .badge .dot {
        width: 8px; height: 8px; border-radius: 999px;
        background: var(--grad);
        box-shadow: 0 0 16px rgba(125, 211, 199, 0.9);
    }
    .hero h1 {
        max-width: 17ch;
        margin: 22px auto 20px;
        font-size: clamp(2.7rem, 6.4vw, 4.7rem);
        line-height: 1.02;
        letter-spacing: -0.045em;
    }
    .hero h1 .grad {
        background: var(--grad);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }
    .hero-sub {
        max-width: 62ch;
        margin: 0 auto;
        color: var(--muted);
        font-size: clamp(1rem, 1.6vw, 1.16rem);
        line-height: 1.65;
    }
    .hero-actions { display: flex; flex-wrap: wrap; gap: 14px; justify-content: center; margin: 30px 0 8px; }
    .btn {
        display: inline-flex; align-items: center; justify-content: center; gap: 9px;
        padding: 14px 24px;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.98rem;
        transition: transform 160ms ease, filter 160ms ease, border-color 160ms ease;
    }
    .btn:hover { transform: translateY(-1px); }
    .btn-primary { background: var(--grad); color: #04202c; box-shadow: 0 16px 40px rgba(125, 211, 199, 0.28); }
    .btn-primary:hover { filter: brightness(1.04); }
    .btn-ghost { border: 1px solid var(--line-strong); background: rgba(8, 18, 29, 0.6); }
    .btn-ghost:hover { border-color: rgba(125, 211, 199, 0.44); }
    .hero-chips { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-top: 26px; }
    .chip {
        padding: 7px 13px;
        border-radius: 999px;
        border: 1px solid var(--line);
        background: rgba(9, 19, 31, 0.55);
        color: var(--muted);
        font-size: 0.8rem;
    }

    .install { padding: 18px 0 72px; }
    .terminal {
        position: relative;
        max-width: 860px;
        margin: 0 auto;
        border: 1px solid var(--line-strong);
        border-radius: var(--radius);
        background: linear-gradient(180deg, rgba(12, 24, 38, 0.92), rgba(7, 14, 23, 0.96));
        box-shadow: var(--shadow);
        overflow: hidden;
    }
    .terminal-bar {
        display: flex; align-items: center; gap: 8px;
        padding: 14px 18px;
        border-bottom: 1px solid var(--line);
        background: rgba(6, 12, 20, 0.7);
    }
    .terminal-bar .dot { width: 11px; height: 11px; border-radius: 999px; }
    .dot-red { background: #f87171; } .dot-amber { background: #fbbf24; } .dot-green { background: #34d399; }
    .terminal-title { margin-left: 10px; color: var(--muted); font-size: 0.82rem; }
    .terminal-body {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 14px;
        align-items: center;
        padding: 22px 20px;
    }
    .terminal-body code {
        display: block;
        text-align: left;
        font-family: 'SFMono-Regular', 'JetBrains Mono', 'Consolas', monospace;
        font-size: clamp(0.84rem, 1.3vw, 0.98rem);
        line-height: 1.7;
        color: #d8ecf5;
        word-break: break-word;
    }
    .terminal-body code .prompt { color: var(--teal); margin-right: 8px; user-select: none; }
    .copy-button {
        display: inline-flex; align-items: center; justify-content: center; gap: 8px;
        height: 46px;
        padding: 0 18px;
        border-radius: 12px;
        border: 1px solid rgba(125, 211, 199, 0.24);
        background: linear-gradient(135deg, rgba(125, 211, 199, 0.16), rgba(103, 232, 249, 0.1));
        color: var(--text);
        font: inherit; font-weight: 600; cursor: pointer;
        transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
    }
    .copy-button:hover { transform: translateY(-1px); border-color: rgba(125, 211, 199, 0.48); }
    .copy-button.copied { border-color: rgba(125, 211, 199, 0.6); box-shadow: 0 0 0 8px rgba(125, 211, 199, 0.08); }
    .terminal-caption { padding: 0 20px 20px; color: var(--muted); font-size: 0.9rem; }

    section.block { padding: 72px 0; }
    .section-head { max-width: 60ch; margin-bottom: 40px; }
    .eyebrow {
        display: inline-block;
        color: var(--cyan);
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-size: 0.74rem;
        font-weight: 600;
        margin-bottom: 14px;
    }
    .section-head h2 { font-size: clamp(1.9rem, 3.6vw, 2.8rem); line-height: 1.08; }
    .section-head p { margin-top: 14px; color: var(--muted); font-size: 1.04rem; line-height: 1.65; }

    .feature-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
    .feature-card {
        position: relative;
        padding: 26px 24px;
        border: 1px solid var(--line);
        border-radius: var(--radius);
        background: linear-gradient(180deg, rgba(13, 25, 39, 0.7), rgba(9, 18, 29, 0.82));
        overflow: hidden;
        transition: transform 180ms ease, border-color 180ms ease;
    }
    .feature-card:hover { transform: translateY(-3px); border-color: var(--line-strong); }
    .feature-card::after {
        content: "";
        position: absolute; inset: auto -30% -60% 30%; height: 180px;
        background: radial-gradient(circle, rgba(125, 211, 199, 0.14), transparent 65%);
        pointer-events: none;
    }
    .feature-index {
        display: inline-flex;
        font-family: var(--font-display);
        font-size: 0.82rem;
        color: var(--teal);
        letter-spacing: 0.08em;
        margin-bottom: 14px;
    }
    .feature-card h3 { font-size: 1.16rem; }
    .feature-card p { margin-top: 10px; color: var(--muted); font-size: 0.94rem; line-height: 1.6; }

    .build-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
    .build-card {
        display: grid;
        gap: 12px;
        padding: 22px;
        border: 1px solid var(--line);
        border-radius: var(--radius);
        background: linear-gradient(180deg, rgba(13, 25, 39, 0.66), rgba(8, 16, 26, 0.82));
        transition: transform 180ms ease, border-color 180ms ease;
    }
    .build-card:hover { transform: translateY(-3px); border-color: rgba(125, 211, 199, 0.4); }
    .build-icon {
        width: 46px; height: 46px;
        display: inline-flex; align-items: center; justify-content: center;
        border-radius: 13px;
        color: var(--teal);
        background: rgba(125, 211, 199, 0.12);
        border: 1px solid rgba(125, 211, 199, 0.22);
    }
    .build-icon svg { width: 24px; height: 24px; }
    .build-card h3 { font-size: 1.06rem; }
    .build-card p { color: var(--muted); font-size: 0.9rem; line-height: 1.58; }

    .stats-band {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1px;
        margin: 0 auto;
        padding: 1px;
        border-radius: var(--radius);
        overflow: hidden;
        background: var(--line);
    }
    .stat { padding: 26px 22px; background: linear-gradient(180deg, rgba(13, 25, 39, 0.9), rgba(8, 16, 26, 0.94)); }
    .stat strong { display: block; font-family: var(--font-display); font-size: 2.3rem; letter-spacing: -0.05em; }
    .stat span { display: block; margin-top: 6px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.72rem; }

    .context-strip {
        display: flex; flex-wrap: wrap; align-items: center; gap: 12px;
        margin-top: 26px;
        padding: 16px 20px;
        border: 1px solid var(--line);
        border-radius: var(--radius);
        background: rgba(9, 19, 31, 0.55);
        color: var(--muted);
        font-size: 0.92rem;
    }
    .context-strip .tag {
        padding: 5px 11px;
        border-radius: 999px;
        border: 1px solid rgba(125, 211, 199, 0.24);
        background: rgba(125, 211, 199, 0.1);
        color: var(--teal);
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .context-strip strong { color: var(--text); }

    .cta-band {
        margin: 24px 0 0;
        padding: 54px 40px;
        border: 1px solid rgba(125, 211, 199, 0.22);
        border-radius: calc(var(--radius) + 6px);
        text-align: center;
        background:
            radial-gradient(circle at 20% 20%, rgba(125, 211, 199, 0.16), transparent 42%),
            radial-gradient(circle at 84% 30%, rgba(167, 139, 250, 0.14), transparent 44%),
            linear-gradient(180deg, rgba(12, 24, 38, 0.9), rgba(7, 14, 23, 0.95));
        box-shadow: var(--shadow);
    }
    .cta-band h2 { font-size: clamp(1.8rem, 3.4vw, 2.6rem); }
    .cta-band p { margin: 14px auto 26px; max-width: 52ch; color: var(--muted); line-height: 1.6; }
    .cta-band .hero-actions { margin: 0; }

    .reveal { opacity: 1; transform: none; }
    html.js .reveal { opacity: 0; transform: translateY(22px); transition: opacity 520ms ease, transform 520ms ease; }
    html.js .reveal.reveal-visible { opacity: 1; transform: translateY(0); }

    footer.footer {
        margin-top: 72px;
        border-top: 1px solid var(--line);
        background: rgba(5, 11, 18, 0.7);
        padding: 52px 0 40px;
    }
    .footer-grid { display: grid; grid-template-columns: 1.6fr repeat(3, 1fr); gap: 32px; }
    .footer-brand p { margin-top: 14px; max-width: 34ch; color: var(--muted); font-size: 0.92rem; line-height: 1.6; }
    .footer-col h4 { margin: 0 0 14px; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }
    .footer-col a { display: block; margin-bottom: 10px; color: var(--text); font-size: 0.92rem; opacity: 0.86; transition: opacity 140ms ease, color 140ms ease; }
    .footer-col a:hover { opacity: 1; color: var(--teal); }
    .footer-bottom {
        display: flex; flex-wrap: wrap; justify-content: space-between; gap: 14px;
        margin-top: 42px; padding-top: 22px;
        border-top: 1px solid var(--line);
        color: var(--muted); font-size: 0.86rem;
    }

    @media (max-width: 980px) {
        .feature-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .build-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .footer-grid { grid-template-columns: 1fr 1fr; }
        .nav-links { display: none; }
    }
    @media (max-width: 640px) {
        .feature-grid, .build-grid, .stats-band, .footer-grid { grid-template-columns: 1fr; }
        .terminal-body { grid-template-columns: 1fr; }
        .copy-button { width: 100%; }
        .hero { padding: 72px 0 48px; }
        .cta-band { padding: 40px 22px; }
    }
    """

    script = """
    (() => {
        document.documentElement.classList.add('js');
        const button = document.getElementById('copy-install');
        const code = document.getElementById('install-command');
        if (button && code && navigator.clipboard) {
            button.addEventListener('click', async () => {
                try {
                    await navigator.clipboard.writeText(code.textContent || '');
                    button.classList.add('copied');
                    const label = button.querySelector('.copy-label');
                    if (label) label.textContent = 'Copied';
                    window.setTimeout(() => {
                        button.classList.remove('copied');
                        if (label) label.textContent = 'Copy';
                    }, 1600);
                } catch (_error) {
                    const label = button.querySelector('.copy-label');
                    if (label) label.textContent = 'Copy failed';
                    window.setTimeout(() => {
                        if (label) label.textContent = 'Copy';
                    }, 1600);
                }
            });
        }

        const revealables = document.querySelectorAll('.reveal');
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                for (const entry of entries) {
                    if (!entry.isIntersecting) continue;
                    entry.target.classList.add('reveal-visible');
                    observer.unobserve(entry.target);
                }
            }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
            revealables.forEach((node, index) => {
                node.style.transitionDelay = `${Math.min(index * 45, 240)}ms`;
                observer.observe(node);
            });
        } else {
            revealables.forEach((node) => node.classList.add('reveal-visible'));
        }
    })();
    """

    return f"""<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <meta name='description' content='Machine Core is the open control plane for building, running, and managing AI projects with agents, tools, RAG, memory, workflows, and evals.'>
  <title>Machine Core · Build, run, and manage AI projects</title>
  <link rel='icon' href='/favicon.ico' type='image/svg+xml'>
  <link rel='preconnect' href='https://fonts.googleapis.com'>
  <link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>
  <link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@500;600;700&display=swap'>
  <style>{style}</style>
</head>
<body>
  <header class='nav'>
    <div class='container nav-inner'>
      <a class='brand' href='/'>
        <span class='brand-mark' aria-hidden='true'>
          <svg viewBox='0 0 48 48' fill='none' xmlns='http://www.w3.org/2000/svg'>
            <defs>
              <linearGradient id='landing-machine-mark' x1='6' y1='6' x2='42' y2='42' gradientUnits='userSpaceOnUse'>
                <stop stop-color='#7DD3C7'/>
                <stop offset='1' stop-color='#67E8F9'/>
              </linearGradient>
            </defs>
            <path d='M9 38V10L24 27L39 10V38' stroke='url(#landing-machine-mark)' stroke-width='7' stroke-linecap='round' stroke-linejoin='round'/>
            <circle cx='9' cy='10' r='3.2' fill='#060d16' stroke='url(#landing-machine-mark)' stroke-width='2'/>
            <circle cx='24' cy='27' r='3.2' fill='#060d16' stroke='url(#landing-machine-mark)' stroke-width='2'/>
            <circle cx='39' cy='10' r='3.2' fill='#060d16' stroke='url(#landing-machine-mark)' stroke-width='2'/>
          </svg>
        </span>
        <span class='brand-copy'>
          <strong>Machine Core</strong>
          <small>One system for AI projects</small>
        </span>
      </a>
      <nav class='nav-links' aria-label='Primary'>
        <a href='#features'>Features</a>
        <a href='#build'>What you can build</a>
        <a href='#install-machine'>Install</a>
        <a href='/_studio/'>Studio</a>
      </nav>
      <a class='nav-cta' href='/_studio/'>Open Studio &rarr;</a>
    </div>
  </header>

  <main>
    <section class='hero'>
      <div class='container'>
        <span class='badge'><span class='dot'></span> Open-source control plane for AI projects</span>
        <h1>Build, run, and manage AI projects on <span class='grad'>one system</span>.</h1>
        <p class='hero-sub'>Start with a single project and keep shipping. Machine Core keeps the way you began working even when the project grows into many runtimes, contexts, and operators.</p>
        <div class='hero-actions'>
          <a class='btn btn-primary' href='#install-machine'>Install Machine</a>
          <a class='btn btn-ghost' href='/_studio/'>Open Studio</a>
        </div>
        <div class='hero-chips'>
          <span class='chip'>Agents</span>
          <span class='chip'>Tools</span>
          <span class='chip'>RAG</span>
          <span class='chip'>Memory</span>
          <span class='chip'>Workflows</span>
          <span class='chip'>Evals</span>
          <span class='chip'>MCP</span>
          <span class='chip'>Studio</span>
        </div>
      </div>
    </section>

    <section class='install' id='install-machine'>
      <div class='container'>
        <div class='terminal'>
          <div class='terminal-bar'>
            <span class='dot dot-red'></span>
            <span class='dot dot-amber'></span>
            <span class='dot dot-green'></span>
            <span class='terminal-title'>install.sh</span>
          </div>
          <div class='terminal-body'>
            <code id='install-command'><span class='prompt'>$</span>{escape(install_command)}</code>
            <button type='button' class='copy-button' id='copy-install' aria-label='Copy install command' title='Copy install command'>
              <span class='copy-label'>Copy</span>
              <span aria-hidden='true'>&#10697;</span>
            </button>
          </div>
          <p class='terminal-caption'>Paste this once. Machine Core wires up the runtime, the plugin system, and Studio.</p>
        </div>
      </div>
    </section>

    <section class='block' id='features'>
      <div class='container'>
        <div class='section-head'>
          <span class='eyebrow'>Why Machine Core</span>
          <h2>Start simple, then grow without starting over.</h2>
          <p>Every capability is a plugin with a stable contract, so the system you learn on day one is the system you run in production.</p>
        </div>
        <div class='feature-grid'>
          {feature_cards}
        </div>
      </div>
    </section>

    <section class='block' id='build'>
      <div class='container'>
        <div class='section-head'>
          <span class='eyebrow'>What you can build</span>
          <h2>Add capabilities instead of changing systems.</h2>
          <p>Compose the parts you need today, and attach the rest when the project asks for them.</p>
        </div>
        <div class='build-grid'>
          {build_cards}
        </div>
      </div>
    </section>

    <section class='block'>
      <div class='container'>
        <div class='stats-band'>
          {stat_cells}
        </div>
        <div class='context-strip'>
          <span class='tag'>Live context</span>
          <span>Currently inspecting <strong>{active_target}</strong></span>
          <span>Studio &middot; /_studio/</span>
        </div>
      </div>
    </section>

    <section class='block'>
      <div class='container'>
        <div class='cta-band'>
          <span class='eyebrow'>Ready when you are</span>
          <h2>Install once. Keep building.</h2>
          <p>Bring your own models, add your own tools, and operate everything from one control plane.</p>
          <div class='hero-actions'>
            <a class='btn btn-primary' href='#install-machine'>Install Machine</a>
            <a class='btn btn-ghost' href='/_studio/'>Open Studio</a>
          </div>
        </div>
      </div>
    </section>
  </main>

  <footer class='footer'>
    <div class='container'>
      <div class='footer-grid'>
        <div class='footer-brand'>
          <div class='brand'>
            <span class='brand-mark' aria-hidden='true'>
              <svg viewBox='0 0 48 48' fill='none' xmlns='http://www.w3.org/2000/svg'>
                <path d='M9 38V10L24 27L39 10V38' stroke='#7dd3c7' stroke-width='7' stroke-linecap='round' stroke-linejoin='round'/>
              </svg>
            </span>
            <span class='brand-copy'><strong>Machine Core</strong><small>One system for AI projects</small></span>
          </div>
          <p>The open control plane for agents, tools, RAG, memory, workflows, and evals.</p>
        </div>
        <div class='footer-col'>
          <h4>Product</h4>
          <a href='#features'>Features</a>
          <a href='#build'>What you can build</a>
          <a href='#install-machine'>Install</a>
        </div>
        <div class='footer-col'>
          <h4>Runtime</h4>
          <a href='/_studio/agents'>Agents</a>
          <a href='/_studio/tools'>Tools</a>
          <a href='/_studio/sections/rag'>RAG</a>
        </div>
        <div class='footer-col'>
          <h4>Operate</h4>
          <a href='/_studio/'>Studio</a>
          <a href='/_studio/docs'>Docs</a>
          <a href='/health'>Health</a>
        </div>
      </div>
      <div class='footer-bottom'>
        <span>Machine Core &middot; Studio is the control plane when you need a wider view.</span>
        <span>Built to run one project or many.</span>
      </div>
    </div>
  </footer>

  <script>{script}</script>
</body>
</html>
"""

def create_studio_host_app(machine: Any) -> FastAPI:
    """Create the top-level Studio host app with a landing page at /."""
    studio_state = build_studio_state(machine)
    app = FastAPI(title="Machine Core", lifespan=_machine_lifespan(machine))
    app.state.studio_state = studio_state

    studio = create_studio_app(machine, studio_state=studio_state)
    app.mount("/_studio", studio)

    @app.get("/", response_class=HTMLResponse)
    async def landing_page():
        return HTMLResponse(_landing_page_html(studio_state))

    @app.get("/health")
    async def health():
        return {"status": "healthy", "studio_mount": "/_studio"}

    @app.get("/favicon.ico")
    async def favicon() -> Response:
        return Response(content=_machine_favicon_svg(), media_type="image/svg+xml")

    return app


def create_studio_app(
    machine: Any, *, studio_state: StudioState | None = None
) -> FastAPI:
    """Create the Studio FastAPI sub-application."""
    if studio_state is None:
        studio_state = build_studio_state(machine)

    app = FastAPI(
        title="Machine Studio",
        docs_url=None,
        redoc_url=None,
        lifespan=_machine_lifespan(machine),
    )
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
