"""Smoke tests for app wiring."""


async def test_healthz(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "mbwira"}
