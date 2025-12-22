"""
Conecta Plus - Testes dos Servicos
Testes para QR Code, PDF, Email, WhatsApp, Relatorios
"""

import pytest
import sys
import os

# Adiciona o diretorio ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestQRCodeGenerator:
    """Testes para o gerador de QR Code"""

    def test_gerar_qrcode_bytes(self):
        """Testa geracao de QR Code em bytes"""
        from services.qrcode_generator import qrcode_generator

        pix_code = "00020126580014br.gov.bcb.pix0136a1b2c3d4"
        qr_bytes = qrcode_generator.gerar_qrcode(pix_code)

        assert qr_bytes is not None
        assert len(qr_bytes) > 0
        # PNG magic bytes
        assert qr_bytes[:4] == b'\x89PNG'

    def test_gerar_qrcode_base64(self):
        """Testa geracao de QR Code em base64"""
        from services.qrcode_generator import qrcode_generator

        pix_code = "00020126580014br.gov.bcb.pix0136a1b2c3d4"
        qr_base64 = qrcode_generator.gerar_qrcode_base64(pix_code)

        assert qr_base64 is not None
        assert qr_base64.startswith("data:image/png;base64,")

    def test_gerar_qrcode_svg(self):
        """Testa geracao de QR Code em SVG"""
        from services.qrcode_generator import qrcode_generator

        pix_code = "00020126580014br.gov.bcb.pix0136a1b2c3d4"
        qr_svg = qrcode_generator.gerar_qrcode_svg(pix_code)

        assert qr_svg is not None
        assert "<svg" in qr_svg
        assert "</svg>" in qr_svg


class TestPDFGenerator:
    """Testes para o gerador de PDF"""

    def test_gerar_boleto_pdf(self):
        """Testa geracao de PDF de boleto"""
        from services.pdf_generator import pdf_generator

        boleto = {
            "id": "bol_test",
            "valor": 850.00,
            "vencimento": "2025-01-15",
            "competencia": "01/2025",
            "morador": "Teste Silva",
            "nosso_numero": "00000001",
            "codigo_barras": "12345678901234567890123456789012345678901234",
            "linha_digitavel": "12345.67890 12345.678901 12345.678901 1 12340000085000",
            "pix_copia_cola": "00020126580014br.gov.bcb.pix"
        }

        beneficiario = {
            "nome": "Condominio Teste",
            "documento": "12.345.678/0001-90",
            "conta": "12345678"
        }

        pdf_bytes = pdf_generator.gerar_boleto_pdf(boleto, beneficiario)

        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        # PDF magic bytes
        assert pdf_bytes[:4] == b'%PDF'

    def test_gerar_boleto_base64(self):
        """Testa geracao de PDF em base64"""
        from services.pdf_generator import pdf_generator

        boleto = {
            "id": "bol_test",
            "valor": 850.00,
            "vencimento": "2025-01-15",
            "competencia": "01/2025",
            "morador": "Teste Silva",
            "nosso_numero": "00000001"
        }

        beneficiario = {
            "nome": "Condominio Teste",
            "documento": "12.345.678/0001-90"
        }

        pdf_base64 = pdf_generator.gerar_boleto_base64(boleto, beneficiario)

        assert pdf_base64 is not None
        assert pdf_base64.startswith("data:application/pdf;base64,")


class TestEmailService:
    """Testes para o servico de email"""

    @pytest.mark.asyncio
    async def test_enviar_email_mock(self):
        """Testa envio de email (mock)"""
        from services.email_service import email_service

        resultado = await email_service.enviar_email(
            para="teste@email.com",
            assunto="Teste de Email",
            corpo_html="<h1>Teste</h1>"
        )

        assert resultado is not None
        assert resultado["sucesso"] is True
        assert resultado["modo"] == "mock"

    @pytest.mark.asyncio
    async def test_enviar_boleto_email(self):
        """Testa envio de boleto por email"""
        from services.email_service import email_service

        boleto = {
            "id": "bol_test",
            "valor": 850.00,
            "vencimento": "2025-01-15",
            "competencia": "01/2025",
            "morador": "Teste Silva",
            "pix_copia_cola": "00020126580014br.gov.bcb.pix"
        }

        condominio = {"nome": "Condominio Teste"}

        resultado = await email_service.enviar_boleto(
            email="teste@email.com",
            boleto=boleto,
            condominio=condominio
        )

        assert resultado is not None
        assert resultado["sucesso"] is True


class TestWhatsAppService:
    """Testes para o servico de WhatsApp"""

    @pytest.mark.asyncio
    async def test_enviar_mensagem_mock(self):
        """Testa envio de mensagem WhatsApp (mock)"""
        from services.whatsapp_service import whatsapp_service

        resultado = await whatsapp_service.enviar_mensagem(
            telefone="11999999999",
            mensagem="Teste de mensagem"
        )

        assert resultado is not None
        assert resultado["sucesso"] is True
        assert resultado["modo"] == "mock"

    @pytest.mark.asyncio
    async def test_formatar_telefone(self):
        """Testa formatacao de telefone"""
        from services.whatsapp_service import whatsapp_service

        # Telefone com 11 digitos (DDD + numero)
        assert whatsapp_service._formatar_telefone("11999999999") == "5511999999999"

        # Telefone com caracteres especiais
        assert whatsapp_service._formatar_telefone("(11) 99999-9999") == "5511999999999"

        # Telefone ja com codigo do pais
        assert whatsapp_service._formatar_telefone("5511999999999") == "5511999999999"


class TestRelatoriosAvancados:
    """Testes para relatorios avancados"""

    @pytest.mark.asyncio
    async def test_gerar_dre(self):
        """Testa geracao de DRE"""
        from services.relatorios_avancados import gerador_relatorios

        lancamentos = [
            {"tipo": "receita", "categoria": "REC001", "valor": 100000},
            {"tipo": "despesa", "categoria": "DES001", "valor": 20000},
        ]
        condominio = {"nome": "Condomínio Teste", "cnpj": "12.345.678/0001-90"}

        dre = gerador_relatorios.gerar_dre(lancamentos, 12, 2024, condominio)

        assert dre is not None
        assert isinstance(dre, bytes)  # Retorna PDF em bytes

    @pytest.mark.asyncio
    async def test_gerar_balancete(self):
        """Testa geracao de balancete"""
        from services.relatorios_avancados import gerador_relatorios

        lancamentos = [
            {"tipo": "receita", "categoria": "REC001", "valor": 10000},
            {"tipo": "despesa", "categoria": "DES001", "valor": 8000},
        ]
        saldo_anterior = 5000.0
        condominio = {"nome": "Condomínio Teste", "cnpj": "12.345.678/0001-90"}

        balancete = gerador_relatorios.gerar_balancete(lancamentos, saldo_anterior, 12, 2024, condominio)

        assert balancete is not None
        assert isinstance(balancete, bytes)  # Retorna PDF em bytes

    @pytest.mark.asyncio
    async def test_gerar_prestacao_contas(self):
        """Testa geracao de prestacao de contas"""
        from services.relatorios_avancados import gerador_relatorios
        from datetime import date

        lancamentos = [
            {"tipo": "receita", "categoria": "REC001", "valor": 95000},
            {"tipo": "despesa", "categoria": "DES001", "valor": 38000},
        ]
        boletos = [
            {"valor": 850.00, "status": "pago", "vencimento": "2024-12-10"},
        ]
        saldo_inicial = 50000.0
        periodo_inicio = date(2024, 12, 1)
        periodo_fim = date(2024, 12, 31)
        condominio = {"nome": "Condomínio Teste", "cnpj": "12.345.678/0001-90"}

        prestacao = gerador_relatorios.gerar_prestacao_contas(
            lancamentos, boletos, saldo_inicial, periodo_inicio, periodo_fim, condominio
        )

        assert prestacao is not None
        assert isinstance(prestacao, bytes)  # Retorna PDF em bytes


class TestWebSocketNotifier:
    """Testes para o notificador WebSocket"""

    def test_criar_notificacao(self):
        """Testa criacao de notificacao"""
        from services.websocket_notifier import Notificacao, TipoNotificacao

        notif = Notificacao(
            tipo=TipoNotificacao.PAGAMENTO_CONFIRMADO,
            titulo="Pagamento",
            mensagem="Pagamento confirmado",
            dados={"valor": 850}
        )

        assert notif.id is not None
        assert notif.timestamp is not None
        assert notif.lida is False

    def test_notificacao_to_dict(self):
        """Testa conversao de notificacao para dict"""
        from services.websocket_notifier import Notificacao, TipoNotificacao

        notif = Notificacao(
            tipo=TipoNotificacao.BOLETO_CRIADO,
            titulo="Boleto",
            mensagem="Novo boleto",
            dados={}
        )

        data = notif.to_dict()

        assert "id" in data
        assert "tipo" in data
        assert "titulo" in data
        assert data["tipo"] == "boleto_criado"

    def test_ws_manager_estatisticas(self):
        """Testa estatisticas do WebSocket manager"""
        from services.websocket_notifier import ws_manager

        stats = ws_manager.get_estatisticas()

        assert "total_conexoes" in stats
        assert "conexoes_admin" in stats
        assert "condominios_conectados" in stats
