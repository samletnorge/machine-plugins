"""Studio FastAPI sub-application and host app."""

from __future__ import annotations

from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, Response
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
            "stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round' "
            f"aria-hidden='true'>{path}</svg>"
        )

    capabilities = [
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

    feature_classes = {"Agents": "cell-wide", "Studio": "cell-feature"}
    capability_cells = "".join(
        (
            f"<article class='cell {feature_classes.get(title, '')} reveal' "
            f"style='--reveal-delay:{index * 40}ms'>"
            f"<span class='cell-index'>{index:02d}</span>"
            f"<span class='cell-icon'>{_icon(path)}</span>"
            f"<h3>{title}</h3>"
            f"<p>{copy}</p>"
            "</article>"
        )
        for index, (title, copy, path) in enumerate(capabilities, start=1)
    )

    headline_words = "Build, run, and manage AI projects on one system.".split()
    headline_html = " ".join(
        f"<span class='word' style='--d:{index * 40}ms'>{escape(word)}</span>"
        for index, word in enumerate(headline_words)
    )

    marquee_keywords = [
        "Agents",
        "Tools",
        "RAG",
        "Memory",
        "Workflows",
        "Evals",
        "MCP",
        "Studio",
    ]
    marquee_items = "".join(
        f"<span class='word'>{keyword}</span><span class='dot'>·</span>"
        for keyword in marquee_keywords
    )
    marquee_sets = (
        f"<div class='marquee-set'>{marquee_items}</div>"
        f"<div class='marquee-set' aria-hidden='true'>{marquee_items}</div>"
    )

    stats = [
        (len(tenants), "Tenants"),
        (len(projects), "Projects"),
        (len(environments), "Environments"),
        (len(capabilities), "Capability areas"),
    ]
    stat_cells = "".join(
        f"<div class='stat reveal' style='--reveal-delay:{index * 60}ms'>"
        f"<strong data-count='{value}'>{value}</strong>"
        f"<span>{label}</span></div>"
        for index, (value, label) in enumerate(stats)
    )

    style = """
    * { box-sizing: border-box; }
    :root {
        color-scheme: dark;
        --bg: #0B0B0C;
        --panel: #101012;
        --elevated: #151517;
        --text: #EDEDED;
        --muted: #9B9CA3;
        --line: rgba(255, 255, 255, 0.08);
        --line-strong: rgba(255, 255, 255, 0.16);
        --accent: #FF5C38;
        --accent-hover: #FF7355;
        --accent-contrast: #0B0B0C;
        --radius: 10px;
        --radius-sm: 8px;
        --font-sans: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
        --font-mono: 'JetBrains Mono', ui-monospace, 'SFMono-Regular', monospace;
    }
    html { scroll-behavior: smooth; }
    body {
        margin: 0;
        min-height: 100vh;
        background: var(--bg);
        color: var(--text);
        font-family: var(--font-sans);
        font-size: 14px;
        line-height: 1.55;
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
    }
    a { color: inherit; text-decoration: none; }
    h1, h2, h3 { margin: 0; font-weight: 650; letter-spacing: -0.02em; line-height: 1.15; }
    p { margin: 0; }
    svg { display: block; }
    .container { width: min(1120px, calc(100% - 48px)); margin: 0 auto; }
    .scroll-progress {
        position: fixed; top: 0; left: 0; z-index: 90;
        width: 100%; height: 2px;
        background: var(--accent);
        transform: scaleX(0); transform-origin: 0 50%;
        will-change: transform;
    }
    html.js .reveal { opacity: 0; transform: translateY(14px); }
    html.js .reveal.is-visible {
        animation: reveal-up 260ms cubic-bezier(0.22, 0.61, 0.36, 1) both;
        animation-delay: var(--reveal-delay, 0ms);
    }
    @keyframes reveal-up { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
    .nav {
        position: sticky;
        top: 0;
        z-index: 50;
        background: var(--bg);
        border-bottom: 1px solid var(--line);
    }
    .nav-inner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        min-height: 64px;
    }
    .brand { display: flex; align-items: center; gap: 10px; }
    .brand-mark {
        display: inline-flex; align-items: center; justify-content: center;
        width: 30px; height: 30px;
        color: var(--accent);
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
    }
    .brand-mark svg { width: 18px; height: 18px; }
    .brand-copy strong { display: block; font-size: 14px; font-weight: 650; letter-spacing: -0.02em; }
    .brand-copy small {
        display: block; margin-top: 1px;
        font-family: var(--font-mono); font-size: 10.5px;
        text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted);
    }
    .nav-links { display: flex; align-items: center; gap: 24px; }
    .nav-links a { font-size: 13px; color: var(--muted); transition: color 120ms ease; }
    .nav-links a:hover { color: var(--text); }
    .nav-cta {
        display: inline-flex; align-items: center; height: 34px; padding: 0 14px;
        border: 1px solid var(--line-strong); border-radius: 8px;
        font-size: 13px; font-weight: 550;
        transition: border-color 120ms ease, color 120ms ease;
    }
    .nav-cta:hover { border-color: var(--accent); color: var(--accent); }

    .hero { position: relative; isolation: isolate; padding: 68px 0 36px; }
    .hero::before {
        content: "";
        position: absolute;
        inset: 0;
        z-index: -1;
        pointer-events: none;
        opacity: 0.55;
        background-image:
            linear-gradient(to right, var(--line) 1px, transparent 1px),
            linear-gradient(to bottom, var(--line) 1px, transparent 1px);
        background-size: 68px 68px;
        background-position: center top;
    }
    .badge {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 5px 11px;
        border: 1px solid var(--line); border-radius: 999px;
        font-family: var(--font-mono); font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted);
    }
    .badge .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); }
    .hero h1 {
        max-width: 18ch;
        margin: 20px 0 16px;
        font-size: clamp(2.5rem, 6vw, 4.2rem);
        line-height: 1.02;
        letter-spacing: -0.035em;
    }
    .hero h1 .word { display: inline-block; }
    html.js .hero h1 .word {
        opacity: 0;
        transform: translateY(14px);
        animation: word-up 240ms cubic-bezier(0.22, 0.61, 0.36, 1) both;
        animation-delay: var(--d, 0ms);
    }
    @keyframes word-up { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
    .hero-sub { max-width: 52ch; color: var(--muted); font-size: clamp(1rem, 1.5vw, 1.12rem); line-height: 1.6; }
    .hero-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 28px; }
    .btn {
        display: inline-flex; align-items: center; justify-content: center;
        height: 42px; padding: 0 20px;
        border: 1px solid transparent; border-radius: 8px;
        font-size: 14px; font-weight: 550;
        transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
    }
    .btn-primary { background: var(--accent); border-color: var(--accent); color: var(--accent-contrast); }
    .btn-primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
    .btn-ghost { border-color: var(--line-strong); color: var(--text); }
    .btn-ghost:hover { background: var(--elevated); }

    .install { padding: 8px 0 44px; }
    .terminal {
        max-width: 860px;
        border: 1px solid var(--line); border-radius: var(--radius);
        background: var(--panel);
        overflow: hidden;
    }
    .terminal-bar {
        display: flex; align-items: center; justify-content: space-between; gap: 12px;
        padding: 10px 14px;
        border-bottom: 1px solid var(--line);
        background: var(--elevated);
    }
    .terminal-title {
        font-family: var(--font-mono); font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted);
    }
    .terminal-body { padding: 18px; }
    .terminal-body code {
        display: block;
        font-family: var(--font-mono);
        font-size: clamp(0.82rem, 1.3vw, 0.95rem);
        line-height: 1.7;
        color: var(--text);
        word-break: break-word;
    }
    .terminal-body code .prompt { color: var(--accent); margin-right: 8px; user-select: none; }
    .terminal-body code .cursor {
        display: inline-block;
        width: 8px; height: 1.02em;
        margin-left: 2px;
        vertical-align: text-bottom;
        background: var(--accent);
        animation: cursor-blink 1s steps(1, end) infinite;
    }
    .terminal-body code .cursor.cursor-done { animation: none; opacity: 1; }
    @keyframes cursor-blink { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }
    .copy-button {
        display: inline-flex; align-items: center; gap: 8px;
        height: 30px; padding: 0 12px;
        border: 1px solid var(--line); border-radius: 6px;
        background: transparent; color: var(--muted);
        font-family: var(--font-mono); font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.06em;
        cursor: pointer;
        transition: color 120ms ease, border-color 120ms ease;
    }
    .copy-button:hover { color: var(--text); border-color: var(--line-strong); }
    .copy-button.copied { color: var(--accent); border-color: var(--accent); }
    .terminal-caption { padding: 0 18px 18px; color: var(--muted); font-size: 12.5px; }

    section.block { padding: 48px 0; }
    .section-head { max-width: 56ch; margin-bottom: 26px; }
    .eyebrow {
        display: inline-block; margin-bottom: 12px;
        font-family: var(--font-mono); font-size: 11px; font-weight: 500;
        text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted);
    }
    .section-head h2 { font-size: clamp(1.7rem, 3.4vw, 2.5rem); }
    .cell-grid {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        grid-auto-rows: minmax(148px, auto);
        gap: 1px;
        background: var(--line);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        overflow: hidden;
    }
    .cell {
        position: relative;
        display: flex; flex-direction: column;
        min-width: 0;
        padding: 20px;
        background: var(--bg);
        overflow: hidden;
        transition: transform 200ms ease, background-color 200ms ease;
    }
    .cell::before {
        content: "";
        position: absolute; left: 0; top: 0; bottom: 0;
        width: 2px;
        background: var(--accent);
        transform: translateX(-100%);
        transition: transform 200ms ease;
    }
    .cell:hover { transform: translateY(-1px); background: var(--panel); }
    .cell:hover::before { transform: translateX(0); }
    .cell-wide { grid-column: 3 / span 2; grid-row: 1; }
    .cell-feature { grid-column: 1 / span 2; grid-row: 1 / span 2; }
    .cell-feature h3 { margin-top: auto; font-size: 20px; }
    .cell-feature .cell-icon { width: 34px; height: 34px; margin-top: 18px; }
    .cell-feature .cell-icon svg { width: 26px; height: 26px; }
    .cell-index { font-family: var(--font-mono); font-size: 11px; color: var(--accent); }
    .cell-icon {
        display: inline-flex; align-items: center; justify-content: center;
        width: 26px; height: 26px;
        margin: 14px 0 12px;
        color: var(--muted);
    }
    .cell-icon svg { width: 20px; height: 20px; }
    .cell h3 { font-size: 15px; }
    .cell p { margin-top: 8px; color: var(--muted); font-size: 13px; }

    .marquee {
        overflow: hidden;
        border-top: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
        background: var(--panel);
    }
    .marquee-track {
        display: flex;
        width: max-content;
        animation: marquee-scroll 46s linear infinite;
        will-change: transform;
    }
    .marquee:hover .marquee-track { animation-play-state: paused; }
    .marquee-set { display: flex; align-items: center; gap: 26px; padding: 13px 26px 13px 0; }
    .marquee-set span {
        font-family: var(--font-mono); font-size: 12px;
        text-transform: uppercase; letter-spacing: 0.16em;
        color: var(--muted); white-space: nowrap;
    }
    .marquee-set span.word { color: var(--text); }
    .marquee-set span.dot { color: var(--accent); }
    @keyframes marquee-scroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }

    .steps {
        position: relative;
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 28px;
        margin: 0; padding: 0;
        list-style: none;
    }
    .steps::before {
        content: "";
        position: absolute; left: 0; right: 0; top: 33px;
        height: 1px; background: var(--line);
    }
    .step { position: relative; display: grid; align-content: start; gap: 10px; padding-right: 14px; }
    .step-num {
        display: inline-flex; align-items: center; justify-content: center;
        width: 66px; height: 66px;
        background: var(--bg);
        border: 1px solid var(--line);
        border-radius: 50%;
        font-family: var(--font-mono); font-size: 22px; font-weight: 500;
        color: var(--accent);
    }
    .step h3 { font-size: 17px; }
    .step p { color: var(--muted); font-size: 13px; }

    .stats-band {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        border: 1px solid var(--line);
        border-radius: var(--radius);
        overflow: hidden;
    }
    .stat { padding: 22px; border-right: 1px solid var(--line); }
    .stat:last-child { border-right: 0; }
    .stat strong { display: block; font-size: 28px; font-weight: 650; letter-spacing: -0.02em; }
    .stat span {
        display: block; margin-top: 4px;
        font-family: var(--font-mono); font-size: 10.5px;
        text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted);
    }
    .context-strip {
        display: flex; flex-wrap: wrap; align-items: center; gap: 12px;
        margin-top: 14px; padding: 12px 16px;
        border: 1px solid var(--line); border-radius: var(--radius-sm);
        color: var(--muted); font-size: 12.5px;
    }
    .context-strip .tag {
        font-family: var(--font-mono); font-size: 10.5px;
        text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent);
    }
    .context-strip strong { color: var(--text); }

    footer.footer { margin-top: 48px; border-top: 1px solid var(--line); padding: 48px 0 32px; }
    .footer-inner { display: grid; grid-template-columns: 1.6fr repeat(3, 1fr); gap: 32px; }
    .footer-brand p { margin-top: 14px; max-width: 34ch; color: var(--muted); font-size: 13px; }
    .footer-col h4 {
        margin: 0 0 12px;
        font-family: var(--font-mono); font-size: 10.5px; font-weight: 500;
        text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted);
    }
    .footer-col a { display: block; margin-bottom: 9px; color: var(--text); font-size: 13px; transition: color 120ms ease; }
    .footer-col a:hover { color: var(--accent); }
    .footer-bottom {
        display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px;
        margin-top: 40px; padding-top: 20px;
        border-top: 1px solid var(--line);
        color: var(--muted); font-size: 12px;
    }

    @media (max-width: 900px) {
        .cell-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); grid-auto-rows: minmax(132px, auto); }
        .cell-wide, .cell-feature { grid-column: auto; grid-row: auto; }
        .steps { grid-template-columns: minmax(0, 1fr); gap: 22px; }
        .steps::before { display: none; }
        .footer-inner { grid-template-columns: 1fr 1fr; }
        .nav-links { display: none; }
    }
    @media (max-width: 640px) {
        .cell-grid, .stats-band, .footer-inner { grid-template-columns: minmax(0, 1fr); }
        .stat { border-right: 0; border-bottom: 1px solid var(--line); }
        .stat:last-child { border-bottom: 0; }
        .hero { padding: 52px 0 30px; }
    }
    @media (prefers-reduced-motion: reduce) {
        html.js .reveal,
        html.js .hero h1 .word {
            opacity: 1 !important;
            transform: none !important;
            animation: none !important;
        }
        .marquee-track { animation: none !important; }
        .terminal-body code .cursor { animation: none !important; opacity: 1 !important; }
        .cell, .cell::before { transition: none !important; }
        html { scroll-behavior: auto; }
    }
    """

    script = """
    (() => {
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        const progress = document.getElementById('scroll-progress');
        if (progress) {
            if (reduceMotion) {
                progress.style.display = 'none';
            } else {
                const updateProgress = () => {
                    const doc = document.documentElement;
                    const max = doc.scrollHeight - doc.clientHeight;
                    const ratio = max > 0 ? doc.scrollTop / max : 0;
                    progress.style.transform = `scaleX(${ratio})`;
                };
                window.addEventListener('scroll', updateProgress, { passive: true });
                window.addEventListener('resize', updateProgress, { passive: true });
                updateProgress();
            }
        }

        const revealTargets = document.querySelectorAll('.reveal');
        if (revealTargets.length) {
            if (!reduceMotion && 'IntersectionObserver' in window) {
                const revealObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach((entry) => {
                        if (entry.isIntersecting) {
                            entry.target.classList.add('is-visible');
                            observer.unobserve(entry.target);
                        }
                    });
                }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
                revealTargets.forEach((target) => revealObserver.observe(target));
            } else {
                revealTargets.forEach((target) => target.classList.add('is-visible'));
            }
        }

        const countTargets = document.querySelectorAll('[data-count]');
        const runCount = (element) => {
            const target = Number(element.dataset.count);
            if (!Number.isFinite(target)) return;
            if (reduceMotion) {
                element.textContent = String(target);
                return;
            }
            const duration = 720;
            const start = performance.now();
            const tick = (now) => {
                const ratio = Math.min(1, (now - start) / duration);
                const eased = 1 - Math.pow(1 - ratio, 3);
                element.textContent = String(Math.round(target * eased));
                if (ratio < 1) window.requestAnimationFrame(tick);
            };
            window.requestAnimationFrame(tick);
        };
        if (countTargets.length) {
            if (!reduceMotion && 'IntersectionObserver' in window) {
                const countObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach((entry) => {
                        if (entry.isIntersecting) {
                            runCount(entry.target);
                            observer.unobserve(entry.target);
                        }
                    });
                }, { threshold: 0.4 });
                countTargets.forEach((target) => countObserver.observe(target));
            } else {
                countTargets.forEach(runCount);
            }
        }

        const button = document.getElementById('copy-install');
        const code = document.getElementById('install-command');
        const typed = document.getElementById('install-typed');
        const cursor = document.getElementById('install-cursor');
        const command = code ? code.dataset.command || '' : '';
        if (typed && command) {
            if (reduceMotion) {
                typed.textContent = command;
            } else {
                typed.textContent = '';
                let index = 0;
                const typeNext = () => {
                    index += 1;
                    typed.textContent = command.slice(0, index);
                    if (index < command.length) {
                        window.setTimeout(typeNext, 16 + Math.random() * 24);
                    } else if (cursor) {
                        cursor.classList.add('cursor-done');
                    }
                };
                window.setTimeout(typeNext, 360);
            }
        }
        if (button && code && navigator.clipboard) {
            button.addEventListener('click', async () => {
                try {
                    await navigator.clipboard.writeText(command || code.textContent || '');
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
  <link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=JetBrains+Mono:wght@400;500;600&display=swap'>
  <script>document.documentElement.classList.add('js');</script>
  <style>{style}</style>
</head>
<body>
  <div class='scroll-progress' id='scroll-progress' aria-hidden='true'></div>
  <header class='nav'>
    <div class='container nav-inner'>
      <a class='brand' href='/'>
        <span class='brand-mark' aria-hidden='true'>
          <svg viewBox='0 0 48 48' fill='none' xmlns='http://www.w3.org/2000/svg'>
            <path d='M9 38V10L24 27L39 10V38' stroke='currentColor' stroke-width='6' stroke-linecap='round' stroke-linejoin='round'/>
            <circle cx='9' cy='10' r='3' fill='currentColor'/>
            <circle cx='24' cy='27' r='3' fill='currentColor'/>
            <circle cx='39' cy='10' r='3' fill='currentColor'/>
          </svg>
        </span>
        <span class='brand-copy'>
          <strong>Machine Core</strong>
          <small>One system for AI projects</small>
        </span>
      </a>
      <nav class='nav-links' aria-label='Primary'>
        <a href='#capabilities'>Capabilities</a>
        <a href='#install-machine'>Install</a>
        <a href='/_studio/app/'>Studio</a>
        <a href='/_studio/app/'>Docs</a>
      </nav>
      <a class='nav-cta' href='/_studio/app/'>Open Studio</a>
    </div>
  </header>

  <main>
    <section class='hero'>
      <div class='container'>
        <span class='badge reveal' style='--reveal-delay:0ms'><span class='dot'></span> Open-source control plane for AI projects</span>
        <h1>{headline_html}</h1>
        <p class='hero-sub reveal' style='--reveal-delay:{len(headline_words) * 40 + 60}ms'>One runtime for agents, tools, RAG, memory, workflows, and evals — with a control plane that keeps every project in view.</p>
        <div class='hero-actions reveal' style='--reveal-delay:{len(headline_words) * 40 + 120}ms'>
          <a class='btn btn-primary' href='#install-machine'>Install Machine</a>
          <a class='btn btn-ghost' href='/_studio/app/'>Open Studio</a>
        </div>
      </div>
    </section>

    <section class='install' id='install-machine'>
      <div class='container'>
        <div class='terminal'>
          <div class='terminal-bar'>
            <span class='terminal-title'>install.sh</span>
            <button type='button' class='copy-button' id='copy-install' aria-label='Copy install command' title='Copy install command'>
              <span class='copy-label'>Copy</span>
            </button>
          </div>
          <div class='terminal-body'>
            <code id='install-command' data-command='{escape(install_command)}'><span class='prompt'>$</span><span class='typed' id='install-typed'>{escape(install_command)}</span><span class='cursor' id='install-cursor' aria-hidden='true'></span></code>
          </div>
          <p class='terminal-caption'>Paste once. Machine Core wires up the runtime, the plugin system, and Studio.</p>
        </div>
      </div>
    </section>

    <section class='block' id='capabilities'>
      <div class='container'>
        <div class='section-head reveal' style='--reveal-delay:0ms'>
          <span class='eyebrow'>Capabilities</span>
          <h2>Add capabilities instead of changing systems.</h2>
        </div>
        <div class='cell-grid'>
          {capability_cells}
        </div>
      </div>
    </section>

    <div class='marquee' aria-hidden='true'>
      <div class='marquee-track'>
        {marquee_sets}
      </div>
    </div>

    <section class='block' id='how-it-works'>
      <div class='container'>
        <div class='section-head reveal' style='--reveal-delay:0ms'>
          <span class='eyebrow'>How it works</span>
          <h2>Install, declare, run.</h2>
        </div>
        <ol class='steps'>
          <li class='step reveal' style='--reveal-delay:0ms'>
            <span class='step-num'>01</span>
            <h3>Install</h3>
            <p>Run the installer once. Machine Core wires up the runtime, the plugin system, and Studio on your machine.</p>
          </li>
          <li class='step reveal' style='--reveal-delay:60ms'>
            <span class='step-num'>02</span>
            <h3>Declare</h3>
            <p>Describe agents, tools, RAG, memory, and workflows as plugins in your project configuration.</p>
          </li>
          <li class='step reveal' style='--reveal-delay:120ms'>
            <span class='step-num'>03</span>
            <h3>Run</h3>
            <p>Start the machine and operate every project from one control plane. Switch contexts without leaving the page.</p>
          </li>
        </ol>
      </div>
    </section>

    <section class='block'>
      <div class='container'>
        <div class='stats-band reveal' style='--reveal-delay:0ms'>
          {stat_cells}
        </div>
        <div class='context-strip'>
          <span class='tag'>Live context</span>
          <span>Inspecting <strong>{active_target}</strong></span>
        </div>
      </div>
    </section>
  </main>

  <footer class='footer'>
    <div class='container footer-inner'>
      <div class='footer-brand'>
        <div class='brand'>
          <span class='brand-mark' aria-hidden='true'>
            <svg viewBox='0 0 48 48' fill='none' xmlns='http://www.w3.org/2000/svg'>
              <path d='M9 38V10L24 27L39 10V38' stroke='currentColor' stroke-width='6' stroke-linecap='round' stroke-linejoin='round'/>
              <circle cx='9' cy='10' r='3' fill='currentColor'/>
              <circle cx='24' cy='27' r='3' fill='currentColor'/>
              <circle cx='39' cy='10' r='3' fill='currentColor'/>
            </svg>
          </span>
          <span class='brand-copy'><strong>Machine Core</strong><small>One system for AI projects</small></span>
        </div>
        <p>The open control plane for agents, tools, RAG, memory, workflows, and evals.</p>
      </div>
      <div class='footer-col'>
        <h4>Product</h4>
        <a href='#capabilities'>Capabilities</a>
        <a href='#install-machine'>Install</a>
        <a href='/_studio/app/'>Studio</a>
      </div>
      <div class='footer-col'>
        <h4>Runtime</h4>
        <a href='/_studio/app/runtime'>Agents</a>
        <a href='/_studio/app/runtime'>Tools</a>
        <a href='/_studio/app/domain/rag'>RAG</a>
      </div>
      <div class='footer-col'>
        <h4>Operate</h4>
        <a href='/_studio/app/'>Studio</a>
        <a href='/_studio/app/'>Docs</a>
        <a href='/health'>Health</a>
      </div>
    </div>
    <div class='container footer-bottom'>
      <span>Machine Core · Studio is the control plane when you need a wider view.</span>
      <span>Built to run one project or many.</span>
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

    from studio_support.routes import (
        auth as auth_routes,
        legacy as legacy_routes,
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
    from studio_support.control import overview as control_overview
    from studio_support.control import pubsub as control_pubsub
    from studio_support.control import rag as control_rag
    from studio_support.control import registry as control_registry
    from studio_support.control import runtime as control_runtime
    from studio_support.control import services as control_services
    from studio_support.control import storage as control_storage
    from studio_support.control import voice as control_voice
    from studio_support.control import workspace as control_workspace

    app.include_router(auth_routes.router)
    app.include_router(tool_routes.router)
    app.include_router(control_services.router)
    app.include_router(control_registry.router)
    app.include_router(control_config.router)
    app.include_router(control_context.router)
    app.include_router(control_runtime.router)
    app.include_router(control_deploy.router)
    app.include_router(control_auth.router)
    app.include_router(control_observe.router)
    app.include_router(control_overview.router)
    app.include_router(control_memory.router)
    app.include_router(control_rag.router)
    app.include_router(control_evals.router)
    app.include_router(control_pubsub.router)
    app.include_router(control_storage.router)
    app.include_router(control_workspace.router)
    app.include_router(control_browser.router)
    app.include_router(control_voice.router)

    # Legacy server-rendered pages now redirect into the SPA.
    app.include_router(legacy_routes.router)

    # New SvelteKit Studio build (static SPA) served under /_studio/app.
    studio_build = Path(__file__).parent / "web" / "build"
    if studio_build.is_dir():
        assets_dir = studio_build / "_app"
        if assets_dir.is_dir():
            app.mount(
                "/app/_app",
                StaticFiles(directory=str(assets_dir)),
                name="studio-app-assets",
            )

        build_root = studio_build.resolve()

        @app.get("/app")
        @app.get("/app/{path:path}")
        async def studio_spa(path: str = "") -> Response:
            if path:
                candidate = (studio_build / path).resolve()
                if candidate.is_file() and build_root in candidate.parents:
                    return FileResponse(candidate)
            return FileResponse(studio_build / "index.html")

    return app
