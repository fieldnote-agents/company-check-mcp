"""LEGACY / DISABLED: EU VAT (VIES) + LEI check tool.

Paused in 0.2.2. The eu-company-vat-check Apify actor is no longer offered in
Apify Store, and the VIES terms forbid re-using VIES data commercially, so this
tool is NOT registered by default.

It is only registered when COMPANY_CHECK_ENABLE_LEGACY_EU_VAT=1 is set
(for the maintainers' own testing). Do not enable it in public configs.
"""
from __future__ import annotations

from typing import Annotated, Any, Awaitable, Callable

from pydantic import Field

ENV_FLAG = "COMPANY_CHECK_ENABLE_LEGACY_EU_VAT"


def make_tool(run: Callable[..., Awaitable[list[dict[str, Any]]]], clean: Callable[[list[str], str], list[str]], actor: str):
    async def eu_vat_check(
        vat_numbers: Annotated[list[str], Field(description="1-500 EU VAT numbers with country prefix, e.g. 'IE6388047V'. Max one check per number per day (cached).", min_length=1, max_length=500)],
        leis: Annotated[list[str] | None, Field(description="Optional LEIs in the same order as vat_numbers, to pin the LEI match.")] = None,
        match_lei: Annotated[bool, Field(description="Find the GLEIF LEI record for each VAT number.")] = True,
        requester_vat_number: Annotated[str | None, Field(description="Your own EU VAT number; VIES then returns a consultation number as proof.")] = None,
    ) -> list[dict[str, Any]]:
        """LEGACY (disabled by default). Validate EU VAT numbers in VIES and match each to
        its GLEIF LEI record. VAT numbers need the country prefix ('IE6388047V')."""
        vats = clean(vat_numbers, "vat_numbers")
        leis = leis or []
        cps = [{"vatNumber": v, "lei": (leis[i].strip().upper() if i < len(leis) and leis[i] else "")} for i, v in enumerate(vats)]
        inp: dict[str, Any] = {"counterparties": cps, "matchLei": match_lei}
        if requester_vat_number:
            inp["requesterVatNumber"] = requester_vat_number.strip()
        return await run(inp, actor)

    return eu_vat_check
