"""
Integration tests for API Gateway
Tests the integration between API Gateway and backend services
"""
import pytest
import requests
import json
from typing import Dict, Any

# Base URL for API Gateway
API_GATEWAY_URL = "http://localhost:3001"

# Test credentials
TEST_CREDENTIALS = {
    "email": "admin@conectaplus.com.br",
    "senha": "admin123"
}


class TestAuthenticationIntegration:
    """Test authentication flow integration"""

    def test_login_returns_valid_token(self):
        """Test that login endpoint returns a valid JWT token"""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/auth/login",
            json=TEST_CREDENTIALS,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data or "token" in data
        assert "user" in data or "email" in data

        # Token should be a non-empty string
        token = data.get("access_token") or data.get("token")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_protected_route_requires_authentication(self):
        """Test that protected routes require authentication"""
        response = requests.get(
            f"{API_GATEWAY_URL}/api/dashboard/estatisticas",
            timeout=10
        )

        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403]

    def test_protected_route_with_valid_token(self):
        """Test that protected routes work with valid token"""
        # First login
        login_response = requests.post(
            f"{API_GATEWAY_URL}/api/auth/login",
            json=TEST_CREDENTIALS,
            timeout=10
        )

        assert login_response.status_code == 200
        token_data = login_response.json()
        token = token_data.get("access_token") or token_data.get("token")

        # Then access protected route
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_GATEWAY_URL}/api/dashboard/estatisticas",
            headers=headers,
            timeout=10
        )

        assert response.status_code == 200


class TestFinanceiroIAIntegration:
    """Test Financeiro IA endpoints integration"""

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Get authentication headers with valid token"""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/auth/login",
            json=TEST_CREDENTIALS,
            timeout=10
        )

        assert response.status_code == 200
        token_data = response.json()
        token = token_data.get("access_token") or token_data.get("token")

        return {"Authorization": f"Bearer {token}"}

    def test_score_prediction_endpoint(self, auth_headers):
        """Test score prediction endpoint"""
        response = requests.get(
            f"{API_GATEWAY_URL}/api/financeiro/ia/score/unit_001",
            headers=auth_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        assert "score" in data
        assert "categoria" in data
        assert "confidence" in data

        # Validate score range
        assert 0 <= data["score"] <= 100

    def test_tendencias_endpoint(self, auth_headers):
        """Test tendências endpoint"""
        response = requests.get(
            f"{API_GATEWAY_URL}/api/financeiro/ia/tendencias",
            headers=auth_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        assert "tendencias" in data or isinstance(data, list)

    def test_priorizacao_cobrancas_endpoint(self, auth_headers):
        """Test priorização de cobranças endpoint"""
        response = requests.get(
            f"{API_GATEWAY_URL}/api/financeiro/ia/priorizacao",
            headers=auth_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        assert "unidades" in data or isinstance(data, list)

        if isinstance(data, dict) and "unidades" in data:
            # Each unit should have priority fields
            for unit in data["unidades"][:5]:  # Check first 5
                assert "unidade_id" in unit or "id" in unit
                assert "prioridade" in unit or "priority" in unit

    def test_feedback_endpoint(self, auth_headers):
        """Test feedback endpoint for ML learning"""
        feedback_data = {
            "unidade_id": "unit_test_001",
            "prediction_type": "score",
            "predicted_value": 85.5,
            "actual_value": 82.0,
            "was_accurate": True
        }

        response = requests.post(
            f"{API_GATEWAY_URL}/api/financeiro/ia/feedback",
            headers=auth_headers,
            json=feedback_data,
            timeout=10
        )

        # Should accept feedback
        assert response.status_code in [200, 201, 204]


class TestDashboardIntegration:
    """Test dashboard endpoints integration"""

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/auth/login",
            json=TEST_CREDENTIALS,
            timeout=10
        )

        token_data = response.json()
        token = token_data.get("access_token") or token_data.get("token")

        return {"Authorization": f"Bearer {token}"}

    def test_dashboard_estatisticas(self, auth_headers):
        """Test dashboard statistics endpoint"""
        response = requests.get(
            f"{API_GATEWAY_URL}/api/dashboard/estatisticas",
            headers=auth_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Should have basic statistics
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_dashboard_alertas(self, auth_headers):
        """Test dashboard alerts endpoint"""
        response = requests.get(
            f"{API_GATEWAY_URL}/api/dashboard/alertas",
            headers=auth_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Alerts can be empty array or object with alerts
        assert isinstance(data, (list, dict))


class TestCondominiosIntegration:
    """Test condomínios endpoints integration"""

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/auth/login",
            json=TEST_CREDENTIALS,
            timeout=10
        )

        token_data = response.json()
        token = token_data.get("access_token") or token_data.get("token")

        return {"Authorization": f"Bearer {token}"}

    def test_list_condominios(self, auth_headers):
        """Test listing all condomínios"""
        response = requests.get(
            f"{API_GATEWAY_URL}/api/condominios",
            headers=auth_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Should have items and total
        assert "items" in data or isinstance(data, list)
        if isinstance(data, dict):
            assert "total" in data
            assert data["total"] >= 0

    def test_get_condominio_by_id(self, auth_headers):
        """Test getting specific condomínio"""
        # First get list
        list_response = requests.get(
            f"{API_GATEWAY_URL}/api/condominios",
            headers=auth_headers,
            timeout=10
        )

        assert list_response.status_code == 200
        list_data = list_response.json()

        # Get first condominio ID
        items = list_data.get("items", list_data)
        if items and len(items) > 0:
            condo_id = items[0].get("id") or items[0].get("_id")

            if condo_id:
                # Get specific condominio
                response = requests.get(
                    f"{API_GATEWAY_URL}/api/condominios/{condo_id}",
                    headers=auth_headers,
                    timeout=10
                )

                assert response.status_code == 200
                data = response.json()
                assert "id" in data or "_id" in data


class TestErrorHandling:
    """Test error handling across integrations"""

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/auth/login",
            json=TEST_CREDENTIALS,
            timeout=10
        )

        token_data = response.json()
        token = token_data.get("access_token") or token_data.get("token")

        return {"Authorization": f"Bearer {token}"}

    def test_invalid_endpoint_returns_404(self, auth_headers):
        """Test that invalid endpoints return 404"""
        response = requests.get(
            f"{API_GATEWAY_URL}/api/invalid-endpoint-xyz",
            headers=auth_headers,
            timeout=10
        )

        assert response.status_code == 404

    def test_invalid_json_returns_error(self, auth_headers):
        """Test that invalid JSON returns appropriate error"""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/financeiro/ia/feedback",
            headers={**auth_headers, "Content-Type": "application/json"},
            data="invalid json{",
            timeout=10
        )

        # Should return 400 Bad Request or 422 Unprocessable Entity
        assert response.status_code in [400, 422]

    def test_missing_required_fields_returns_error(self, auth_headers):
        """Test that missing required fields return validation error"""
        response = requests.post(
            f"{API_GATEWAY_URL}/api/financeiro/ia/feedback",
            headers=auth_headers,
            json={},  # Empty object, missing required fields
            timeout=10
        )

        # Should return validation error
        assert response.status_code in [400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
