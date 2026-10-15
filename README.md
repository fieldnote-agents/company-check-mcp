<!-- mcp-name: io.github.fieldnote-agents/company-check-mcp -->
# Global Company Check MCP server

An MCP server (stdio) that lets AI agents look up companies and Legal Entity
Identifiers (LEIs) worldwide. It calls the
[Global Company Check](https://apify.com/fieldnoteagents/global-company-check)
actor on Apify, which reads GLEIF open data (CC0).

> Not affiliated with or endorsed by GLEIF. Data is from GLEIF's public LEI records.

## Tools

| Tool | What it does |
|---|---|
| `lookup_company(name, country?)` | Best match for a legal name; add an ISO-2 country (e.g. `SE`) for better results |
| `lookup_lei(lei)` | Full record for one 20-character LEI |
| `bulk_lookup(queries)` | Up to 500 queries: LEIs or `"Legal name \| CC"` |

All tools take `include_parents` (default `true`) to add direct and ultimate parents.

## Pricing

Runs go to **your own Apify account** using your `APIFY_TOKEN`:
first 25 companies found free, then $0.03 per company found. No result, no charge.

## Setup

1. Get an Apify API token: https://console.apify.com/settings/integrations
2. Install: `pip install company-check-mcp` (or `uvx company-check-mcp`)
3. Add to your MCP client, e.g. Claude Desktop / Cursor:

```json
{
  "mcpServers": {
    "company-check": {
      "command": "uvx",
      "args": ["company-check-mcp"],
      "env": { "APIFY_TOKEN": "apify_api_..." }
    }
  }
}
```

From source: `pip install .` then run `company-check-mcp`.

## License

MIT. Made by Fieldnote Agents.
