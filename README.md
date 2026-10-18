<!-- mcp-name: io.github.fieldnote-agents/company-check-mcp -->
# Company Check MCP server (LEI, ARES, KRS, VIES)

An MCP server (stdio) that lets AI agents look up companies and Legal Entity
Identifiers (LEIs) worldwide. It calls the
[Global Company Check](https://apify.com/fieldnoteagents/global-company-check)
actor on Apify, which reads GLEIF open data (CC0).

> Not affiliated with or endorsed by GLEIF, the Czech Ministry of Finance, the Polish Ministry of Justice or the European Commission. Data comes from their public sources (GLEIF CC0, ARES, KRS open API, VIES).

## Tools

| Tool | What it does |
|---|---|
| `lookup_company(name, country?)` | Best match for a legal name; add an ISO-2 country (e.g. `SE`) for better results |
| `lookup_lei(lei)` | Full record for one 20-character LEI |
| `bulk_lookup(queries)` | Up to 500 queries: LEIs or `"Legal name \| CC"` |
| `czech_company_check(queries, include_persons?)` | Czech ARES: IČO lookup or company name ([actor](https://apify.com/fieldnoteagents/czech-company-check-ares)) |
| `poland_krs_extract(krs_numbers, include_persons?, full_extract?)` | Poland KRS extract by KRS number only ([actor](https://apify.com/fieldnoteagents/poland-krs-company-check)) |
| `eu_vat_check(vat_numbers, leis?, match_lei?, requester_vat_number?)` | EU VAT number check in VIES + GLEIF LEI match ([actor](https://apify.com/fieldnoteagents/eu-company-vat-check)) |

The LEI tools take `include_parents` (default `true`) to add direct and ultimate parents.
All tools take up to 500 items per call. Built for KYB, supplier and counterparty checks, not lead lists.
`include_persons` returns personal data (board members): use only for a lawful purpose (GDPR).

## Pricing

Runs go to **your own Apify account** using your `APIFY_TOKEN`:
each actor: first 25 results free, then $0.03 per company found / counterparty checked. No result, no charge.

### Spending cap for agents
Every tool call is one Apify run. To cap what a single call can cost, set
`COMPANY_CHECK_MAX_CHARGE_USD` (e.g. `"0.50"`) in the server's `env`; it is sent as
Apify's `maxTotalChargeUsd` and the actor stops cleanly at the limit.
**The cap must be at least $0.05**: Apify refuses runs of these actors with a lower max charge.
Calling the actors directly through the Apify MCP server (`https://mcp.apify.com`, `call-actor`)?
The same $0.05 minimum applies to `maxTotalChargeUsd` in `callOptions`.

## Setup

1. Get an Apify API token: https://console.apify.com/settings/integrations
2. Install from GitHub (works today; the PyPI package is not published yet):
   `uvx --from git+https://github.com/fieldnote-agents/company-check-mcp company-check-mcp`
   or `pip install "git+https://github.com/fieldnote-agents/company-check-mcp"`
3. Add to your MCP client, e.g. Claude Desktop / Cursor:

```json
{
  "mcpServers": {
    "company-check": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/fieldnote-agents/company-check-mcp", "company-check-mcp"],
      "env": { "APIFY_TOKEN": "apify_api_..." }
    }
  }
}
```

From source: `pip install .` then run `company-check-mcp`.

Once on PyPI, the short form `uvx company-check-mcp` will also work.

## Related
- [EU company registers directory](https://fieldnote-agents.github.io/eu-company-registers/): free, open list of official registers with API, key, limits, terms and a live status check (MIT, same org).

## License

MIT. Made by Fieldnote Agents.
