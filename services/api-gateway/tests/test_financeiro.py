"""
Conecta Plus - Testes do Modulo Financeiro
"""

import pytest
from httpx import AsyncClient


class TestBoletos:
    """Testes para endpoints de boletos"""

    @pytest.mark.asyncio
    async def test_listar_boletos(self, auth_client):
        """Testa listagem de boletos"""
        response = await auth_client.get("/api/financeiro/boletos")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_listar_boletos_com_filtro_status(self, auth_client):
        """Testa listagem de boletos filtrados por status"""
        response = await auth_client.get("/api/financeiro/boletos?status=pendente")

        assert response.status_code == 200
        data = response.json()

        # Todos os boletos devem ter status pendente
        for boleto in data["items"]:
            assert boleto["status"] == "pendente"

    @pytest.mark.asyncio
    async def test_criar_boleto(self, auth_client, sample_boleto):
        """Testa criacao de boleto"""
        response = await auth_client.post(
            "/api/financeiro/boletos",
            json=sample_boleto
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "boleto" in data
        assert data["boleto"]["valor"] == sample_boleto["valor"]
        assert data["boleto"]["status"] == "pendente"

    @pytest.mark.asyncio
    async def test_criar_boleto_unidade_invalida(self, auth_client):
        """Testa criacao de boleto com unidade invalida"""
        boleto = {
            "unidade_id": "invalida",
            "valor": 850.00,
            "vencimento": "2025-01-15"
        }

        response = await auth_client.post(
            "/api/financeiro/boletos",
            json=boleto
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_obter_boleto_existente(self, auth_client):
        """Testa obtencao de boleto existente"""
        response = await auth_client.get("/api/financeiro/boletos/bol_001")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "bol_001"
        assert "valor" in data
        assert "vencimento" in data

    @pytest.mark.asyncio
    async def test_obter_boleto_inexistente(self, auth_client):
        """Testa obtencao de boleto inexistente"""
        response = await auth_client.get("/api/financeiro/boletos/boleto_inexistente")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_atualizar_boleto(self, auth_client):
        """Testa atualizacao de boleto"""
        response = await auth_client.put(
            "/api/financeiro/boletos/bol_001",
            json={"valor": 900.00}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["boleto"]["valor"] == 900.00

    @pytest.mark.asyncio
    async def test_cancelar_boleto(self, auth_client):
        """Testa cancelamento de boleto"""
        response = await auth_client.delete("/api/financeiro/boletos/bol_002")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "cancelado" in data["message"].lower()


class TestPagamentos:
    """Testes para endpoints de pagamentos"""

    @pytest.mark.asyncio
    async def test_registrar_pagamento(self, auth_client, sample_pagamento):
        """Testa registro de pagamento"""
        response = await auth_client.post(
            "/api/financeiro/pagamentos",
            json=sample_pagamento
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["boleto"]["status"] == "pago"
        assert data["boleto"]["valor_pago"] == sample_pagamento["valor_pago"]

    @pytest.mark.asyncio
    async def test_registrar_pagamento_boleto_inexistente(self, auth_client):
        """Testa registro de pagamento em boleto inexistente"""
        pagamento = {
            "boleto_id": "boleto_inexistente",
            "valor_pago": 850.00,
            "data_pagamento": "2025-01-08",
            "forma_pagamento": "pix"
        }

        response = await auth_client.post(
            "/api/financeiro/pagamentos",
            json=pagamento
        )

        assert response.status_code == 404


class TestRelatorios:
    """Testes para endpoints de relatorios"""

    @pytest.mark.asyncio
    async def test_resumo_financeiro(self, auth_client):
        """Testa resumo financeiro"""
        response = await auth_client.get("/api/financeiro/resumo")

        assert response.status_code == 200
        data = response.json()

        assert "receitas" in data
        assert "despesas" in data
        assert "saldo" in data
        assert "boletos" in data
        assert "inadimplencia" in data

    @pytest.mark.asyncio
    async def test_relatorio_inadimplencia(self, auth_client):
        """Testa relatorio de inadimplencia"""
        response = await auth_client.get("/api/financeiro/relatorios/inadimplencia")

        assert response.status_code == 200
        data = response.json()

        assert "taxa" in data
        assert "valor_total" in data
        assert "por_tempo" in data

    @pytest.mark.asyncio
    async def test_fluxo_caixa(self, auth_client):
        """Testa relatorio de fluxo de caixa"""
        response = await auth_client.get("/api/financeiro/relatorios/fluxo-caixa")

        assert response.status_code == 200
        data = response.json()

        assert "entradas" in data
        assert "saidas" in data
        assert "saldo_atual" in data

    @pytest.mark.asyncio
    async def test_previsao_financeira(self, auth_client):
        """Testa previsao financeira"""
        response = await auth_client.get("/api/financeiro/relatorios/previsao?meses=3")

        assert response.status_code == 200
        data = response.json()

        assert "previsoes" in data
        assert len(data["previsoes"]) == 3


class TestCategorias:
    """Testes para endpoints de categorias"""

    @pytest.mark.asyncio
    async def test_listar_categorias(self, auth_client):
        """Testa listagem de categorias"""
        response = await auth_client.get("/api/financeiro/categorias")

        assert response.status_code == 200
        data = response.json()

        assert "receita" in data
        assert "despesa" in data
        assert len(data["receita"]) > 0
        assert len(data["despesa"]) > 0


class TestLancamentos:
    """Testes para endpoints de lancamentos"""

    @pytest.mark.asyncio
    async def test_listar_lancamentos(self, auth_client):
        """Testa listagem de lancamentos"""
        response = await auth_client.get("/api/financeiro/lancamentos")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_criar_lancamento(self, auth_client, sample_lancamento):
        """Testa criacao de lancamento"""
        response = await auth_client.post(
            "/api/financeiro/lancamentos",
            json=sample_lancamento
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "lancamento" in data


class TestBancos:
    """Testes para endpoints de integracao bancaria"""

    @pytest.mark.asyncio
    async def test_listar_bancos(self, auth_client):
        """Testa listagem de bancos"""
        response = await auth_client.get("/api/financeiro/bancos")

        assert response.status_code == 200
        data = response.json()

        assert "bancos" in data
        assert len(data["bancos"]) > 0

    @pytest.mark.asyncio
    async def test_testar_conexao_banco(self, auth_client):
        """Testa conexao com banco"""
        response = await auth_client.post("/api/financeiro/bancos/inter/testar")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True


class TestExportacao:
    """Testes para endpoints de exportacao"""

    @pytest.mark.asyncio
    async def test_exportar_boletos_xlsx(self, auth_client):
        """Testa exportacao de boletos em XLSX"""
        response = await auth_client.get("/api/financeiro/exportar?tipo=boletos&formato=xlsx")

        assert response.status_code == 200
        data = response.json()

        assert "url" in data
        assert "filename" in data
        assert data["filename"].endswith(".xlsx")

    @pytest.mark.asyncio
    async def test_exportar_boletos_csv(self, auth_client):
        """Testa exportacao de boletos em CSV"""
        response = await auth_client.get("/api/financeiro/exportar?tipo=boletos&formato=csv")

        assert response.status_code == 200
        data = response.json()

        assert data["filename"].endswith(".csv")

    @pytest.mark.asyncio
    async def test_exportar_boletos_pdf(self, auth_client):
        """Testa exportacao de boletos em PDF"""
        response = await auth_client.get("/api/financeiro/exportar?tipo=boletos&formato=pdf")

        assert response.status_code == 200
        data = response.json()

        assert data["filename"].endswith(".pdf")
