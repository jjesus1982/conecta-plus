import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/auth/login", json={
            "email": "nonexistent@test.com",
            "senha": "wrong"
        })
    assert response.status_code == 401
    assert "Credenciais inválidas" in response.json()["detail"]

@pytest.mark.asyncio
async def test_verify_invalid_token():
    """Test token verification with invalid token"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/auth/verify?token=invalid_token")
    assert response.status_code == 401
