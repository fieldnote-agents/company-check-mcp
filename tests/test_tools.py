import asyncio, json, httpx, pytest
import company_check_mcp.server as S

CALLS = []
def fake(monkeypatch):
    CALLS.clear()
    monkeypatch.setenv("APIFY_TOKEN", "test-token")
    real = httpx.AsyncClient
    def handler(req):
        CALLS.append((str(req.url), json.loads(req.content)))
        return httpx.Response(200, json=[{"found": True}])
    monkeypatch.setattr(S.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))

def run(c): return asyncio.run(c)

def test_tools_registered():
    names = {t.name for t in run(S.mcp.list_tools())}
    assert {"lookup_company", "lookup_lei", "bulk_lookup", "czech_company_check", "poland_krs_extract", "eu_vat_check"} <= names

def test_ares(monkeypatch):
    fake(monkeypatch); run(S.czech_company_check(["27082440", " ", "Škoda Auto"], True))
    url, body = CALLS[0]
    assert "fieldnoteagents~czech-company-check-ares/run-sync-get-dataset-items" in url
    assert body == {"queries": ["27082440", "Škoda Auto"], "includePersons": True}

def test_krs(monkeypatch):
    fake(monkeypatch); run(S.poland_krs_extract(["0000019193"]))
    assert "poland-krs-company-check" in CALLS[0][0] and CALLS[0][1]["krsNumbers"] == ["0000019193"]
    with pytest.raises(ValueError): run(S.poland_krs_extract(["PKP SA"]))

def test_eu(monkeypatch):
    fake(monkeypatch); run(S.eu_vat_check(["IE6388047V", "BE0403170701"], ["", "t0yooobz"], requester_vat_number="ESB12345678"))
    url, body = CALLS[0]
    assert "eu-company-vat-check" in url
    assert body["counterparties"][0] == {"vatNumber": "IE6388047V", "lei": ""} and body["requesterVatNumber"] == "ESB12345678"

def test_limits(monkeypatch):
    fake(monkeypatch)
    with pytest.raises(ValueError): run(S.eu_vat_check([]))
    with pytest.raises(ValueError): run(S.czech_company_check(["1"] * 501))

def test_no_token(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    with pytest.raises(RuntimeError): run(S.czech_company_check(["27082440"]))
