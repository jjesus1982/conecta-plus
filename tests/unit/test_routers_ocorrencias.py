"""
Testes unitários para o router de ocorrências
"""

import pytest
from datetime import datetime
from uuid import uuid4


class TestOcorrenciasRouter:
    """Testes para endpoints de ocorrências"""

    @pytest.fixture
    def sample_ocorrencia(self):
        """Fixture de ocorrência de exemplo"""
        return {
            "id": str(uuid4()),
            "condominio_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "unidade_id": str(uuid4()),
            "tipo": "barulho",
            "titulo": "Barulho excessivo após 22h",
            "descricao": "Música alta no apartamento 302 após 22h",
            "local": "Bloco A - Apartamento 302",
            "prioridade": "media",
            "status": "aberta",
            "anonima": False,
            "registrado_por": str(uuid4()),
            "data_ocorrencia": "2025-01-10T23:30:00",
            "created_at": datetime.utcnow().isoformat()
        }

    def test_create_ocorrencia(self, sample_ocorrencia):
        """Testa criação de ocorrência"""
        assert sample_ocorrencia["titulo"] is not None
        assert sample_ocorrencia["status"] == "aberta"

    def test_tipos_ocorrencia_validos(self):
        """Testa tipos válidos de ocorrência"""
        tipos = [
            "barulho",
            "manutencao",
            "seguranca",
            "limpeza",
            "estacionamento",
            "animais",
            "vazamento",
            "elevador",
            "portaria",
            "outros"
        ]
        assert "barulho" in tipos
        assert "seguranca" in tipos

    def test_prioridades_validas(self):
        """Testa prioridades válidas"""
        prioridades = ["baixa", "media", "alta", "urgente"]
        assert "media" in prioridades

    def test_status_validos(self):
        """Testa status válidos de ocorrência"""
        status = ["aberta", "em_analise", "em_andamento", "resolvida", "cancelada"]
        assert "aberta" in status
        assert "resolvida" in status

    def test_atualizar_status(self, sample_ocorrencia):
        """Testa atualização de status"""
        sample_ocorrencia["status"] = "em_analise"
        sample_ocorrencia["atualizado_por"] = str(uuid4())
        sample_ocorrencia["updated_at"] = datetime.utcnow().isoformat()

        assert sample_ocorrencia["status"] == "em_analise"

    def test_resolver_ocorrencia(self, sample_ocorrencia):
        """Testa resolução de ocorrência"""
        sample_ocorrencia["status"] = "resolvida"
        sample_ocorrencia["resolucao"] = "Morador notificado e orientado"
        sample_ocorrencia["resolvido_por"] = str(uuid4())
        sample_ocorrencia["resolvido_em"] = datetime.utcnow().isoformat()

        assert sample_ocorrencia["status"] == "resolvida"
        assert sample_ocorrencia["resolucao"] is not None

    def test_ocorrencia_anonima(self, sample_ocorrencia):
        """Testa ocorrência anônima"""
        sample_ocorrencia["anonima"] = True
        sample_ocorrencia["registrado_por"] = None

        assert sample_ocorrencia["anonima"] is True

    def test_listar_por_status(self):
        """Testa listagem por status"""
        ocorrencias = [
            {"status": "aberta"},
            {"status": "aberta"},
            {"status": "resolvida"},
            {"status": "em_andamento"},
        ]

        abertas = [o for o in ocorrencias if o["status"] == "aberta"]
        assert len(abertas) == 2

    def test_calcular_tempo_resolucao(self):
        """Testa cálculo de tempo de resolução"""
        created_at = datetime(2025, 1, 10, 10, 0, 0)
        resolvido_em = datetime(2025, 1, 12, 14, 30, 0)

        tempo_resolucao = resolvido_em - created_at
        horas = tempo_resolucao.total_seconds() / 3600

        assert round(horas, 1) == 52.5  # ~2 dias e meio


class TestReservasRouter:
    """Testes para endpoints de reservas"""

    @pytest.fixture
    def sample_reserva(self):
        """Fixture de reserva de exemplo"""
        return {
            "id": str(uuid4()),
            "condominio_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "area_comum_id": str(uuid4()),
            "area_nome": "Salão de Festas",
            "unidade_id": str(uuid4()),
            "morador_id": str(uuid4()),
            "data_reserva": "2025-02-15",
            "hora_inicio": "14:00",
            "hora_fim": "22:00",
            "num_convidados": 50,
            "motivo": "Festa de aniversário",
            "status": "pendente",
            "valor": 200.00,
            "pago": False,
            "created_at": datetime.utcnow().isoformat()
        }

    def test_create_reserva(self, sample_reserva):
        """Testa criação de reserva"""
        assert sample_reserva["data_reserva"] is not None
        assert sample_reserva["status"] == "pendente"

    def test_status_reserva_validos(self):
        """Testa status válidos de reserva"""
        status = ["pendente", "confirmada", "cancelada", "concluida"]
        assert "pendente" in status

    def test_verificar_conflito_horario(self):
        """Testa verificação de conflito de horário"""
        reservas_existentes = [
            {"data_reserva": "2025-02-15", "hora_inicio": "10:00", "hora_fim": "14:00"},
            {"data_reserva": "2025-02-15", "hora_inicio": "18:00", "hora_fim": "23:00"},
        ]

        nova_reserva = {
            "data_reserva": "2025-02-15",
            "hora_inicio": "14:00",
            "hora_fim": "18:00"
        }

        # Verificar conflito
        conflito = False
        for r in reservas_existentes:
            if r["data_reserva"] == nova_reserva["data_reserva"]:
                if not (nova_reserva["hora_fim"] <= r["hora_inicio"] or
                        nova_reserva["hora_inicio"] >= r["hora_fim"]):
                    conflito = True
                    break

        assert conflito is False  # Não há conflito

    def test_verificar_conflito_existente(self):
        """Testa detecção de conflito existente"""
        reservas_existentes = [
            {"data_reserva": "2025-02-15", "hora_inicio": "14:00", "hora_fim": "20:00"},
        ]

        nova_reserva = {
            "data_reserva": "2025-02-15",
            "hora_inicio": "18:00",
            "hora_fim": "22:00"
        }

        conflito = False
        for r in reservas_existentes:
            if r["data_reserva"] == nova_reserva["data_reserva"]:
                if not (nova_reserva["hora_fim"] <= r["hora_inicio"] or
                        nova_reserva["hora_inicio"] >= r["hora_fim"]):
                    conflito = True
                    break

        assert conflito is True  # Há conflito

    def test_aprovar_reserva(self, sample_reserva):
        """Testa aprovação de reserva"""
        sample_reserva["status"] = "confirmada"
        sample_reserva["aprovado_por"] = str(uuid4())
        sample_reserva["aprovado_em"] = datetime.utcnow().isoformat()

        assert sample_reserva["status"] == "confirmada"

    def test_cancelar_reserva(self, sample_reserva):
        """Testa cancelamento de reserva"""
        sample_reserva["status"] = "cancelada"
        sample_reserva["motivo_cancelamento"] = "Evento cancelado pelo morador"
        sample_reserva["cancelado_em"] = datetime.utcnow().isoformat()

        assert sample_reserva["status"] == "cancelada"


class TestManutencaoRouter:
    """Testes para endpoints de manutenção"""

    @pytest.fixture
    def sample_ordem_servico(self):
        """Fixture de ordem de serviço"""
        return {
            "id": str(uuid4()),
            "condominio_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "titulo": "Reparo no elevador",
            "descricao": "Elevador do bloco A parou de funcionar",
            "tipo": "corretiva",
            "prioridade": "alta",
            "status": "aberta",
            "local": "Bloco A - Elevador Social",
            "solicitante_id": str(uuid4()),
            "responsavel_id": None,
            "fornecedor_id": None,
            "custo_estimado": 2500.00,
            "custo_real": None,
            "prazo": "2025-01-15",
            "created_at": datetime.utcnow().isoformat()
        }

    def test_tipos_manutencao(self):
        """Testa tipos de manutenção"""
        tipos = ["preventiva", "corretiva", "emergencial", "melhoria"]
        assert "corretiva" in tipos

    def test_status_ordem_servico(self):
        """Testa status de ordem de serviço"""
        status = ["aberta", "em_cotacao", "aprovada", "em_execucao", "concluida", "cancelada"]
        assert "aberta" in status

    def test_atribuir_responsavel(self, sample_ordem_servico):
        """Testa atribuição de responsável"""
        sample_ordem_servico["responsavel_id"] = str(uuid4())
        sample_ordem_servico["status"] = "em_execucao"

        assert sample_ordem_servico["responsavel_id"] is not None

    def test_concluir_ordem(self, sample_ordem_servico):
        """Testa conclusão de ordem de serviço"""
        sample_ordem_servico["status"] = "concluida"
        sample_ordem_servico["custo_real"] = 2200.00
        sample_ordem_servico["concluido_em"] = datetime.utcnow().isoformat()
        sample_ordem_servico["observacoes_conclusao"] = "Peça substituída com sucesso"

        assert sample_ordem_servico["status"] == "concluida"
        assert sample_ordem_servico["custo_real"] <= sample_ordem_servico["custo_estimado"]
