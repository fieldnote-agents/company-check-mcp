"""MCP server (stdio) for the Global Company Check Apify actor.

Runs fieldnoteagents/global-company-check on the caller's own Apify account
(APIFY_TOKEN), so any usage is billed to that account.
Data comes from GLEIF open data (CC0). Not affiliated with or endorsed by GLEIF.
"""
from __future__ import annotations

import os
import re
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

ACTOR = os.environ.get("COMPANY_CHECK_ACTOR", "fieldnoteagents~global-company-check")
API = "https://api.apify.com/v2"
LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
MAX_BULK = 500

mcp = FastMCP("global-company-check")


def _token() -> str:
    tok = os.environ.get("APIFY_TOKEN", "").strip()
    if not tok:
        raise RuntimeError(
            "APIFY_TOKEN is not set. Create a token at https://console.apify.com/settings/integrations "
            "and pass it as the APIFY_TOKEN environment variable."
        )
    return tok


async def _run(actor_input: dict[str, Any]) -> list[dict[str, Any]]:
    timeout = float(os.environ.get("COMPANY_CHECK_TIMEOUT", "240"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            f"{API}/acts/{ACTOR}/run-sync-get-dataset-items",
            params={"format": "json", "clean": "true"},
            headers={"Authorization": f"Bearer {_token()}"},
            json=actor_input,
        )
    if r.status_code >= 400:
        try:
            msg = r.json().get("error", {}).get("message", r.text[:300])
        except Exception:
            msg = r.text[:300]
        raise RuntimeError(f"Apify returned HTTP {r.status_code}: {msg}")
    data = r.json()
    return data if isinstance(data, list) else [data]


@mcp.tool()
async def lookup_company(name: str, country: str | None = None, include_parents: bool = True) -> list[dict[str, Any]]:
    """Find a company by legal name in GLEIF open data. Optionally pass an ISO 3166-1
    alpha-2 country code (e.g. 'SE', 'DE', 'US') for a much better match. Returns the
    best match with LEI, legal name, addresses, status and (optionally) parent companies."""
    name = name.strip()
    if not name:
        raise ValueError("name is required")
    q = name
    if country:
        cc = country.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", cc):
            raise ValueError("country must be an ISO 3166-1 alpha-2 code, e.g. 'SE'")
        q = f"{name} | {cc}"
    return await _run({"queries": [q], "includeParents": include_parents})


@mcp.tool()
async def lookup_lei(lei: str, include_parents: bool = True) -> list[dict[str, Any]]:
    """Look up one 20-character Legal Entity Identifier (LEI) from any country in GLEIF
    open data. Returns legal name, addresses, registration status and parents."""
    lei = lei.strip().upper()
    if not LEI_RE.fullmatch(lei):
        raise ValueError("lei must be 20 characters: 18 letters/digits followed by 2 digits")
    return await _run({"queries": [lei], "includeParents": include_parents})


@mcp.tool()
async def bulk_lookup(queries: list[str], include_parents: bool = True) -> list[dict[str, Any]]:
    """Look up up to 500 companies in one run. Each query is either an LEI
    ('549300TTCXZOGZM2EY83') or 'Legal name | CC' with an optional ISO-2 country
    ('Spotify AB | SE'). One result per query."""
    qs = [q.strip() for q in queries if q and q.strip()]
    if not qs:
        raise ValueError("queries must contain at least one non-empty entry")
    if len(qs) > MAX_BULK:
        raise ValueError(f"at most {MAX_BULK} queries per call")
    return await _run({"queries": qs, "includeParents": include_parents})


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
