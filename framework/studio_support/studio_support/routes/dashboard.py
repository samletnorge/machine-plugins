"""Dashboard and planned-section routes for Studio."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from studio_support.control._common import domain_payload
from studio_support.ui import SECTION_COPY, render_template

router = APIRouter(tags=["dashboard"])

# section key -> (domain, categories) for the control-plane domain pages
SECTION_DOMAINS: dict[str, tuple[str, list[str]]] = {
    "memory": ("memory", ["memory"]),
    "rag": ("rag", ["rag_pipeline", "chunker", "reranker", "metadata_extractor"]),
    "evals": ("evals", ["scorer", "dataset"]),
    "storage": ("storage", ["storage-backend"]),
    "deploy": ("deploy", ["deployer"]),
    "observe": ("observe", ["observability_exporter"]),
    "auth": ("auth", ["auth_provider"]),
    "workspace": ("workspace", ["sandbox", "filesystem"]),
    "browser": ("browser", ["browser"]),
    "voice": ("voice", ["voice_provider"]),
    "pubsub": ("pubsub", ["pubsub"]),
}

# domain -> control-plane JSON endpoint backing its Svelte island
DOMAIN_ENDPOINTS: dict[str, str] = {
    "memory": "/api/memory/threads",
    "rag": "/api/rag/pipelines",
    "evals": "/api/evals/runs",
    "storage": "/api/storage/files",
    "deploy": "/api/deploy/targets",
    "observe": "/api/observe/traces",
    "auth": "/api/auth/keys",
    "workspace": "/api/workspace/files",
    "browser": "/api/browser/sessions",
    "voice": "/api/voice/voices",
    "pubsub": "/api/pubsub/events",
}


@router.get("/")
async def dashboard(request: Request):
    return render_template(
        request,
        "dashboard.html",
        page_title="Mission Control",
        active_nav="dashboard",
    )


@router.get("/dashboard")
async def dashboard_alias(request: Request):
    return await dashboard(request)


@router.get("/account")
async def account_page(request: Request):
    return render_template(
        request,
        "section.html",
        page_title="Account",
        active_nav="account",
        section_title="Account",
        section_description="Personal preferences for Machine Studio live here, including theme selection.",
        account_page=True,
    )


@router.get("/sections/{section_key}")
async def planned_section(request: Request, section_key: str):
    title, description = SECTION_COPY.get(
        section_key,
        ("Section", "This Studio surface has been reserved but not wired yet."),
    )

    if section_key in SECTION_DOMAINS:
        domain, categories = SECTION_DOMAINS[section_key]
        return render_template(
            request,
            "domain.html",
            page_title=title,
            active_nav=section_key,
            section_title=title,
            section_description=description,
            payload=domain_payload(domain, categories),
        )

    return render_template(
        request,
        "section.html",
        page_title=title,
        active_nav=section_key,
        section_title=title,
        section_description=description,
    )


@router.get("/islands/{domain}")
async def domain_island(request: Request, domain: str):
    """Render the Svelte island page for a control-plane domain."""
    if domain not in DOMAIN_ENDPOINTS:
        raise HTTPException(status_code=404, detail=f"Unknown island domain: {domain}")

    title, description = SECTION_COPY.get(
        domain,
        (domain.replace("-", " ").title(), "Live control-plane data for this domain."),
    )
    return render_template(
        request,
        "islands/domain.html",
        page_title=title,
        active_nav=domain,
        section_title=title,
        section_description=description,
        island_domain=domain,
        island_endpoint=DOMAIN_ENDPOINTS[domain],
    )
