"""MCP server (stdio) for Fieldnote Agents company-check Apify actors:
Global Company Check (GLEIF LEI), Czech ARES and Poland KRS.
The former EU VAT (VIES) tool is disabled since 0.2.2; see legacy/eu_vat.py.

Runs fieldnoteagents/global-company-check on the caller's own Apify account
(APIFY_TOKEN), so any usage is billed to that account.
Data comes from GLEIF open data (CC0). Not affiliated with or endorsed by GLEIF.
"""
from __future__ import annotations

import os
import re
from typing import Any

import httpx
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

ACTOR = os.environ.get("COMPANY_CHECK_ACTOR", "fieldnoteagents~global-company-check")
ARES_ACTOR = os.environ.get("CZECH_CHECK_ACTOR", "fieldnoteagents~czech-company-check-ares")
KRS_ACTOR = os.environ.get("KRS_CHECK_ACTOR", "fieldnoteagents~poland-krs-company-check")
EU_ACTOR = os.environ.get("EU_VAT_CHECK_ACTOR", "fieldnoteagents~eu-company-vat-check")  # legacy, unused by default
API = "https://api.apify.com/v2"
LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
MAX_BULK = 500

mcp = FastMCP(
    "company-check-mcp",
    instructions=(
        "Read-only company checks from official public registers (GLEIF, ARES, KRS). "
        "Use for KYB, supplier onboarding and counterparty verification, not for lead lists. "
        "Each call runs an Apify actor billed to the caller's APIFY_TOKEN ($0.03 per result after 25 free). "
        "Prefer one batched call over many single calls."
    ),
)
RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)


def _token() -> str:
    tok = os.environ.get("APIFY_TOKEN", "").strip()
    if not tok:
        raise RuntimeError(
            "APIFY_TOKEN is not set. Create a token at https://console.apify.com/settings/integrations "
            "and pass it as the APIFY_TOKEN environment variable."
        )
    return tok


MIN_MAX_CHARGE_USD = 0.05  # Apify refuses runs of these actors with a lower max charge


def _run_params() -> dict[str, str]:
    params = {"format": "json", "clean": "true"}
    cap = os.environ.get("COMPANY_CHECK_MAX_CHARGE_USD", "").strip()
    if cap:
        try:
            value = float(cap)
        except ValueError:
            raise ValueError(f"COMPANY_CHECK_MAX_CHARGE_USD must be a number in USD, got {cap!r}") from None
        if value < MIN_MAX_CHARGE_USD:
            raise ValueError(
                f"COMPANY_CHECK_MAX_CHARGE_USD must be at least {MIN_MAX_CHARGE_USD:.2f}; "
                "Apify refuses runs of these actors with a lower max charge."
            )
        params["maxTotalChargeUsd"] = f"{value:.2f}"
    return params


async def _run(actor_input: dict[str, Any], actor: str | None = None) -> list[dict[str, Any]]:
    timeout = float(os.environ.get("COMPANY_CHECK_TIMEOUT", "240"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            f"{API}/acts/{actor or ACTOR}/run-sync-get-dataset-items",
            params=_run_params(),
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


@mcp.tool(annotations=RO)
async def lookup_company(
    name: Annotated[str, Field(description="Legal name, e.g. 'Spotify AB'. Trading names match poorly.")],
    country: Annotated[str | None, Field(description="Optional ISO 3166-1 alpha-2 country of the legal address, e.g. 'SE'.")] = None,
    include_parents: Annotated[bool, Field(description="Add direct and ultimate parent companies.")] = True,
) -> list[dict[str, Any]]:
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


@mcp.tool(annotations=RO)
async def lookup_lei(
    lei: Annotated[str, Field(description="20-character LEI, e.g. '549300TTCXZOGZM2EY83'.")],
    include_parents: Annotated[bool, Field(description="Add direct and ultimate parent companies.")] = True,
) -> list[dict[str, Any]]:
    """Look up one 20-character Legal Entity Identifier (LEI) from any country in GLEIF
    open data. Returns legal name, addresses, registration status and parents."""
    lei = lei.strip().upper()
    if not LEI_RE.fullmatch(lei):
        raise ValueError("lei must be 20 characters: 18 letters/digits followed by 2 digits")
    return await _run({"queries": [lei], "includeParents": include_parents})


@mcp.tool(annotations=RO)
async def bulk_lookup(
    queries: Annotated[list[str], Field(description="1-500 items; each an LEI or 'Legal name | CC'.", min_length=1, max_length=500)],
    include_parents: Annotated[bool, Field(description="Add direct and ultimate parent companies.")] = True,
) -> list[dict[str, Any]]:
    """Look up up to 500 companies in one run. Each query is either an LEI
    ('549300TTCXZOGZM2EY83') or 'Legal name | CC' with an optional ISO-2 country
    ('Spotify AB | SE'). One result per query."""
    qs = [q.strip() for q in queries if q and q.strip()]
    if not qs:
        raise ValueError("queries must contain at least one non-empty entry")
    if len(qs) > MAX_BULK:
        raise ValueError(f"at most {MAX_BULK} queries per call")
    return await _run({"queries": qs, "includeParents": include_parents})


def _clean(items: list[str], what: str) -> list[str]:
    qs = [str(q).strip() for q in items if q and str(q).strip()]
    if not qs:
        raise ValueError(f"{what} must contain at least one non-empty entry")
    if len(qs) > MAX_BULK:
        raise ValueError(f"at most {MAX_BULK} {what} per call")
    return qs


@mcp.tool(annotations=RO)
async def czech_company_check(
    queries: Annotated[list[str], Field(description="1-500 items; 8-digit IČO ('27082440') or Czech company name.", min_length=1, max_length=500)],
    include_persons: Annotated[bool, Field(description="Add statutory body members (personal data, GDPR). Leave false unless needed.")] = False,
) -> list[dict[str, Any]]:
    """Verify Czech companies in ARES (official Czech register). Each query is an 8-digit
    IČO ('27082440') or a company name ('Škoda Auto'). Returns legal name, IČO, DIČ, status,
    address, legal form, CZ-NACE and registry court. include_persons adds statutory body
    members (personal data: use only for KYB/due diligence)."""
    return await _run({"queries": _clean(queries, "queries"), "includePersons": include_persons}, ARES_ACTOR)


@mcp.tool(annotations=RO)
async def poland_krs_extract(
    krs_numbers: Annotated[list[str], Field(description="1-500 KRS numbers, digits only, up to 10 ('0000019193'). No name search.", min_length=1, max_length=500)],
    include_persons: Annotated[bool, Field(description="Add board, supervisory board and proxies (personal data, GDPR).")] = False,
    full_extract: Annotated[bool, Field(description="Full historical extract (odpis pełny) instead of current.")] = False,
) -> list[dict[str, Any]]:
    """Get the official KRS (Polish National Court Register) extract by KRS number
    (up to 10 digits, e.g. '0000019193'). KRS numbers only: the open KRS API has no name
    search. Returns name, NIP, REGON, legal form, address, share capital, representation;
    include_persons adds board, supervisory board and proxies."""
    nums = _clean(krs_numbers, "krs_numbers")
    bad = [n for n in nums if not re.fullmatch(r"\d{1,10}", n.replace(" ", ""))]
    if bad:
        raise ValueError(f"not KRS numbers (digits only, max 10): {bad[:5]}")
    return await _run({"krsNumbers": nums, "includePersons": include_persons, "fullExtract": full_extract}, KRS_ACTOR)


# Legacy EU VAT (VIES) tool: off unless COMPANY_CHECK_ENABLE_LEGACY_EU_VAT=1 (maintainers' testing only).
from .legacy import eu_vat as _legacy_eu_vat  # noqa: E402

if os.environ.get(_legacy_eu_vat.ENV_FLAG, "").strip() == "1":
    mcp.tool(annotations=RO)(_legacy_eu_vat.make_tool(_run, _clean, EU_ACTOR))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
