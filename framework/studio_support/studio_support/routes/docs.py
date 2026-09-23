"""In-product documentation routes for Studio.

The markdown doc set is bundled inside the plugin (``studio_support/docs``) so
that every install ships with the same pages. Markdown is rendered server-side
with ``markdown-it-py``; tables, fenced code blocks, heading anchors, and a
per-page table of contents are all produced here.
"""

from __future__ import annotations

import html
import posixpath
import re
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from markdown_it import MarkdownIt
from markdown_it.token import Token

from studio_support.ui import render_template

router = APIRouter(tags=["docs"])

DOCS_ROOT = (Path(__file__).resolve().parent.parent / "docs").resolve()

# Directory sections, in the order they appear in the sidebar and card grid.
_SECTION_ORDER: list[tuple[str, str, str]] = [
    (
        "getting-started",
        "Getting started",
        "Install the CLI, scaffold a project, and run your first agent.",
    ),
    (
        "concepts",
        "Concepts",
        "The kernel, plugins, hooks, configuration, and secrets.",
    ),
    (
        "guides",
        "Guides",
        "Build agents, tools, RAG, memory, workflows, voice, and more.",
    ),
    (
        "reference",
        "Reference",
        "Every CLI command, manifest field, registry entry, and config type.",
    ),
    (
        "deployment",
        "Deployment",
        "Self-host a project or ship it to the cloud.",
    ),
]

# Explicit page ordering per directory (matches docs/README.md).
_PAGE_ORDER: dict[str, list[str]] = {
    "getting-started": ["installation.md", "quickstart.md", "project-anatomy.md"],
    "concepts": [
        "architecture.md",
        "plugins.md",
        "hooks-and-events.md",
        "configuration.md",
        "secrets.md",
    ],
    "guides": [
        "agents.md",
        "tools.md",
        "model-providers.md",
        "memory.md",
        "rag.md",
        "workflows.md",
        "mcp.md",
        "voice.md",
        "browser.md",
        "workspaces.md",
        "deployers.md",
        "studio.md",
        "http-api.md",
        "evals.md",
        "build-a-chatbot.md",
        "build-a-rag-assistant.md",
        "build-a-tool-using-agent.md",
        "write-a-plugin.md",
    ],
    "reference": ["cli.md", "manifest.md", "registry.md", "config-schema.md"],
    "deployment": ["self-hosting.md", "cloud.md"],
}

_DEEP_DIVES: list[str] = ["ARCHITECTURE.md", "GETTING_STARTED.md"]


def _render_fence(tokens, idx, options, env):
    """Render a fenced code block wrapped with a language label + copy button."""
    token = tokens[idx]
    info = (token.info or "").strip()
    lang = info.split()[0] if info else ""
    label = html.escape(lang) if lang else "code"
    data_lang = html.escape(lang) if lang else "text"
    escaped = html.escape(token.content)
    lang_attr = f' class="language-{html.escape(lang)}"' if lang else ""
    return (
        f'<div class="docs-code" data-lang="{data_lang}">'
        '<div class="docs-code-bar">'
        f'<span class="docs-code-lang">{label}</span>'
        '<button type="button" class="docs-code-copy" aria-label="Copy code">'
        '<svg class="docs-code-copy-icon docs-code-copy-icon-copy" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true" focusable="false">'
        '<rect x="9" y="9" width="11" height="11" rx="2.5"></rect>'
        '<path d="M5 15.5V6a2.5 2.5 0 0 1 2.5-2.5H16"></path>'
        "</svg>"
        '<svg class="docs-code-copy-icon docs-code-copy-icon-check" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true" focusable="false">'
        '<path d="M20 6.5 9.5 17 4 11.5"></path>'
        "</svg>"
        '<span class="docs-code-copy-label">Copy</span>'
        "</button>"
        "</div>"
        f"<pre><code{lang_attr}>{escaped}</code></pre>"
        "</div>"
    )


def _make_markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "typographer": False})
    md.enable("table")
    md.enable("strikethrough")
    md.renderer.rules["fence"] = _render_fence
    return md


MD = _make_markdown()


@lru_cache(maxsize=None)
def _page_title(rel_path: str) -> str:
    """Return the first level-1 heading of a doc, falling back to its filename."""
    try:
        text = (DOCS_ROOT / rel_path).read_text(encoding="utf-8")
    except OSError:
        text = ""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return Path(rel_path).stem.replace("-", " ").title()


def _doc_href(rel_md: str, root_path: str) -> str:
    """Map a markdown file path to its Studio docs URL."""
    rel = posixpath.normpath(rel_md)
    if rel == "README.md":
        return f"{root_path}/docs"
    if rel.endswith(".md"):
        rel = rel[: -len(".md")]
    return f"{root_path}/docs/{rel}"


def _nav_entry(rel_md: str, root_path: str) -> dict[str, str]:
    return {
        "title": _page_title(rel_md),
        "rel": rel_md,
        "href": _doc_href(rel_md, root_path),
    }


def _dir_pages(dirname: str) -> list[str]:
    directory = DOCS_ROOT / dirname
    files = sorted(p.name for p in directory.glob("*.md")) if directory.is_dir() else []
    order = _PAGE_ORDER.get(dirname, [])
    ordered = [name for name in order if name in files]
    extras = [name for name in files if name not in ordered]
    return [f"{dirname}/{name}" for name in ordered + extras]


def _build_nav(root_path: str) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = [
        {
            "title": None,
            "pages": [_nav_entry("introduction.md", root_path)],
        }
    ]
    for dirname, title, _description in _SECTION_ORDER:
        sections.append(
            {
                "title": title,
                "pages": [_nav_entry(rel, root_path) for rel in _dir_pages(dirname)],
            }
        )
    help_pages = [_nav_entry("faq.md", root_path), _nav_entry("troubleshooting.md", root_path)]
    sections.append({"title": "Help", "pages": help_pages})
    deep_dive_pages = [_nav_entry(rel, root_path) for rel in _DEEP_DIVES]
    sections.append({"title": "Deep dives", "pages": deep_dive_pages})
    return sections


def _card(title: str, description: str, href: str, meta: str) -> dict[str, str]:
    return {
        "title": title,
        "description": description,
        "href": href,
        "meta": meta,
        "search": f"{title} {description} {meta}".lower(),
    }


def _build_cards(root_path: str) -> list[dict[str, str]]:
    cards = [
        _card(
            "Introduction",
            "What machine-core is and the kernel + plugins mental model.",
            _doc_href("introduction.md", root_path),
            "Start here",
        )
    ]
    for dirname, title, description in _SECTION_ORDER:
        pages = _dir_pages(dirname)
        if not pages:
            continue
        cards.append(
            _card(
                title,
                description,
                _doc_href(pages[0], root_path),
                f"{len(pages)} pages",
            )
        )
    cards.append(
        _card(
            "FAQ & troubleshooting",
            "Answers to common questions and fixes for rough edges.",
            _doc_href("faq.md", root_path),
            "2 pages",
        )
    )
    return cards


def _flatten_nav(nav: list[dict[str, object]]) -> list[dict[str, str]]:
    pages: list[dict[str, str]] = []
    for section in nav:
        pages.extend(section["pages"])
    return pages


def _resolve_doc(rel: str) -> Path | None:
    """Resolve a URL path to a markdown file inside DOCS_ROOT, or None."""
    parts = [part for part in rel.strip("/").split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        return None
    if not parts:
        candidate = DOCS_ROOT / "README.md"
    else:
        candidate = DOCS_ROOT.joinpath(*parts)
        if candidate.suffix.lower() != ".md":
            if candidate.is_dir():
                candidate = candidate / "README.md"
            else:
                candidate = candidate.with_suffix(".md")
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if resolved == DOCS_ROOT or DOCS_ROOT not in resolved.parents:
        return None
    if not resolved.is_file():
        return None
    return resolved


def _rewrite_href(href: str, current_rel: str, root_path: str) -> str:
    """Rewrite a markdown link so it points at the mounted docs routes."""
    if not href:
        return href
    if href.startswith("#"):
        return href
    if href.startswith("//") or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href):
        return href
    if href.startswith("/"):
        return f"{root_path}{href}" if href.startswith("/docs") else href

    base, _, anchor = href.partition("#")
    if not base:
        return href
    target = posixpath.normpath(posixpath.join(posixpath.dirname(current_rel), base))
    if target.startswith(".."):
        target = posixpath.basename(target)
    if target.endswith(".md"):
        target_md = target
    elif (DOCS_ROOT / target).is_dir():
        target_md = posixpath.join(target, "README.md")
    else:
        target_md = f"{target}.md"

    url = _doc_href(target_md, root_path)
    return f"{url}#{anchor}" if anchor else url


def _slugify(text: str, used: dict[str, int]) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE).strip()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-") or "section"
    base = slug
    count = used.get(base, 0)
    used[base] = count + 1
    return base if count == 0 else f"{base}-{count}"


def _inline_text(inline) -> str:
    parts = [child.content for child in (inline.children or []) if child.type in ("text", "code_inline")]
    return "".join(parts).strip()


def _apply_anchors(tokens, toc: list[dict[str, object]]) -> None:
    used: dict[str, int] = {}
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        if index + 1 >= len(tokens) or tokens[index + 1].type != "inline":
            continue
        inline = tokens[index + 1]
        text = _inline_text(inline)
        if not text:
            continue
        slug = _slugify(text, used)
        token.attrSet("id", slug)
        if token.tag in ("h2", "h3"):
            toc.append({"level": int(token.tag[1]), "id": slug, "text": text})
        anchor = Token("html_inline", "", 0)
        anchor.content = (
            f'<a class="docs-heading-anchor" href="#{slug}" '
            f'aria-label="Link to this section">#</a>'
        )
        inline.children = (inline.children or []) + [anchor]


def _rewrite_links(tokens, current_rel: str, root_path: str) -> None:
    for token in tokens:
        if token.type == "link_open":
            href = token.attrGet("href") or ""
            token.attrSet("href", _rewrite_href(href, current_rel, root_path))
        if token.children:
            _rewrite_links(token.children, current_rel, root_path)


def render_markdown(
    text: str, current_rel: str, root_path: str
) -> tuple[str, list[dict[str, object]]]:
    """Render markdown to HTML and return it alongside a heading TOC."""
    tokens = MD.parse(text)
    toc: list[dict[str, object]] = []
    _rewrite_links(tokens, current_rel, root_path)
    _apply_anchors(tokens, toc)
    return MD.renderer.render(tokens, MD.options, {}), toc


def _read_doc(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _docs_home_context(root_path: str) -> dict[str, object]:
    nav = _build_nav(root_path)
    landing_path = DOCS_ROOT / "README.md"
    landing_html, _landing_toc = render_markdown(
        _read_doc(landing_path), "README.md", root_path
    )
    return {
        "cards": _build_cards(root_path),
        "landing_html": landing_html,
        "nav": nav,
        "root_path": root_path,
        "current_rel": "README.md",
    }


@router.get("/docs")
async def docs_home(request: Request):
    root_path = request.scope.get("root_path", "")
    context = _docs_home_context(root_path)
    return render_template(
        request,
        "docs.html",
        page_title="Documentation",
        active_nav="docs",
        **context,
    )


@router.get("/docs/{path:path}")
async def docs_page(request: Request, path: str):
    root_path = request.scope.get("root_path", "")
    resolved = _resolve_doc(path)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Documentation page not found")

    current_rel = resolved.relative_to(DOCS_ROOT).as_posix()
    if current_rel == "README.md":
        context = _docs_home_context(root_path)
        return render_template(
            request,
            "docs.html",
            page_title="Documentation",
            active_nav="docs",
            **context,
        )

    content_html, toc = render_markdown(_read_doc(resolved), current_rel, root_path)
    nav = _build_nav(root_path)
    flat = _flatten_nav(nav)
    index = next((i for i, page in enumerate(flat) if page["rel"] == current_rel), None)
    prev_page = flat[index - 1] if index not in (None, 0) else None
    next_page = flat[index + 1] if index is not None and index + 1 < len(flat) else None

    return render_template(
        request,
        "docs_page.html",
        page_title=_page_title(current_rel),
        active_nav="docs",
        nav=nav,
        content_html=content_html,
        toc=toc,
        current_rel=current_rel,
        prev_page=prev_page,
        next_page=next_page,
        root_path=root_path,
    )
