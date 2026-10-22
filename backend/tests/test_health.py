async def test_health_endpoint(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "AICTE FlowGuard API"
    assert data["database"] == "connected"
