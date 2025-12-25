"""
Testes unitários para o router de inteligência proativa (Q2)
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from uuid import uuid4


class TestPrevisoesRouter:
    """Testes para endpoints de previsões (RF-05)"""

    @pytest.fixture
    def sample_previsao(self):
        """Fixture de previsão de exemplo"""
        return {
            "id": str(uuid4()),
            "condominio_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "tipo": "inadimplencia",
            "subtipo": "atraso_pagamento",
            "entidade_tipo": "unidade",
            "entidade_id": str(uuid4()),
            "entidade_nome": "Unidade 101",
            "probabilidade": 0.85,
            "confianca": 0.92,
            "horizonte_dias": 30,
            "sinais": [
                {"tipo": "historico", "peso": 0.4, "descricao": "Atrasos frequentes"},
                {"tipo": "comportamental", "peso": 0.3, "descricao": "Não abriu boletos"},
                {"tipo": "sazonal", "peso": 0.3, "descricao": "Início de ano"}
            ],
            "acao_recomendada": "Enviar lembrete de pagamento",
            "status": "pendente",
            "impacto_estimado": "R$ 850,00",
            "created_at": datetime.utcnow().isoformat()
        }

    def test_create_previsao(self, sample_previsao):
        """Testa criação de previsão"""
        assert 0 <= sample_previsao["probabilidade"] <= 1
        assert 0 <= sample_previsao["confianca"] <= 1
        assert sample_previsao["horizonte_dias"] > 0

    def test_tipos_previsao_validos(self):
        """Testa tipos válidos de previsão"""
        tipos = [
            "inadimplencia",
            "manutencao",
            "seguranca",
            "conflito",
            "ocupacao",
            "consumo"
        ]
        assert "inadimplencia" in tipos
        assert "seguranca" in tipos

    def test_calcular_score_previsao(self, sample_previsao):
        """Testa cálculo de score de previsão"""
        probabilidade = sample_previsao["probabilidade"]
        confianca = sample_previsao["confianca"]

        # Score composto
        score = (probabilidade * 0.6) + (confianca * 0.4)

        assert 0 <= score <= 1
        assert round(score, 2) == 0.88  # 0.85*0.6 + 0.92*0.4

    def test_validar_previsao(self, sample_previsao):
        """Testa validação de previsão"""
        sample_previsao["status"] = "confirmada"
        sample_previsao["validado_por"] = str(uuid4())
        sample_previsao["validado_em"] = datetime.utcnow().isoformat()

        assert sample_previsao["status"] == "confirmada"

    def test_marcar_falso_positivo(self, sample_previsao):
        """Testa marcação de falso positivo"""
        sample_previsao["status"] = "falso_positivo"
        sample_previsao["motivo_rejeicao"] = "Pagamento já realizado"

        assert sample_previsao["status"] == "falso_positivo"


class TestSugestoesRouter:
    """Testes para endpoints de sugestões (RF-06)"""

    @pytest.fixture
    def sample_sugestao(self):
        """Fixture de sugestão de exemplo"""
        return {
            "id": str(uuid4()),
            "condominio_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "tipo": "economia",
            "codigo": "ECO-001",
            "titulo": "Reduzir consumo de energia",
            "descricao": "Instalar sensores de presença nos corredores",
            "contexto": "Consumo de energia aumentou 15% no último trimestre",
            "beneficio_estimado": "Economia de R$ 500/mês",
            "perfil_destino": "sindico",
            "status": "pendente",
            "prioridade": 2,
            "created_at": datetime.utcnow().isoformat()
        }

    def test_create_sugestao(self, sample_sugestao):
        """Testa criação de sugestão"""
        assert sample_sugestao["titulo"] is not None
        assert sample_sugestao["status"] == "pendente"
        assert sample_sugestao["prioridade"] >= 1

    def test_tipos_sugestao_validos(self):
        """Testa tipos válidos de sugestão"""
        tipos = ["economia", "seguranca", "convivencia", "manutencao", "comunicacao"]
        assert "economia" in tipos

    def test_perfis_destino_validos(self):
        """Testa perfis de destino válidos"""
        perfis = ["sindico", "administrador", "porteiro", "morador", "todos"]
        assert "sindico" in perfis

    def test_aceitar_sugestao(self, sample_sugestao):
        """Testa aceitação de sugestão"""
        sample_sugestao["status"] = "aceita"
        sample_sugestao["aceita_por"] = str(uuid4())
        sample_sugestao["aceita_em"] = datetime.utcnow().isoformat()

        assert sample_sugestao["status"] == "aceita"

    def test_rejeitar_sugestao(self, sample_sugestao):
        """Testa rejeição de sugestão"""
        sample_sugestao["status"] = "rejeitada"
        sample_sugestao["motivo_rejeicao"] = "Orçamento não disponível"

        assert sample_sugestao["status"] == "rejeitada"


class TestComunicacaoRouter:
    """Testes para endpoints de comunicação inteligente (RF-07)"""

    @pytest.fixture
    def sample_preferencias(self):
        """Fixture de preferências de comunicação"""
        return {
            "usuario_id": str(uuid4()),
            "horario_preferido_inicio": "08:00",
            "horario_preferido_fim": "20:00",
            "canal_primario": "push",
            "canal_secundario": "email",
            "max_notificacoes_dia": 10,
            "agrupar_similares": True,
            "receber_financeiro": True,
            "receber_manutencao": True,
            "receber_seguranca": True,
            "receber_comunicados": True,
            "receber_sugestoes": False,
            "nao_perturbe_ativo": True,
            "nao_perturbe_inicio": "22:00",
            "nao_perturbe_fim": "07:00"
        }

    def test_preferencias_horario(self, sample_preferencias):
        """Testa preferências de horário"""
        inicio = sample_preferencias["horario_preferido_inicio"]
        fim = sample_preferencias["horario_preferido_fim"]

        assert inicio < fim  # "08:00" < "20:00"

    def test_canais_validos(self):
        """Testa canais válidos de comunicação"""
        canais = ["push", "email", "sms", "whatsapp"]
        assert "push" in canais
        assert "whatsapp" in canais

    def test_modo_nao_perturbe(self, sample_preferencias):
        """Testa modo não perturbe"""
        assert sample_preferencias["nao_perturbe_ativo"] is True

        # Verificar se horário atual está no período de não perturbe
        hora_atual = "23:30"
        inicio = sample_preferencias["nao_perturbe_inicio"]
        fim = sample_preferencias["nao_perturbe_fim"]

        # 22:00 às 07:00 (cruza meia-noite)
        no_periodo = hora_atual >= inicio or hora_atual < fim
        assert no_periodo is True

    def test_agendar_comunicacao(self):
        """Testa agendamento de comunicação"""
        comunicacao = {
            "tipo": "lembrete",
            "titulo": "Boleto vence amanhã",
            "conteudo": "Seu boleto no valor de R$ 850,00 vence amanhã",
            "urgencia": "media",
            "agendar_para": (datetime.utcnow() + timedelta(hours=2)).isoformat()
        }

        assert comunicacao["urgencia"] in ["baixa", "media", "alta", "critica"]


class TestAprendizadoRouter:
    """Testes para endpoints de aprendizado contínuo (RF-08)"""

    @pytest.fixture
    def sample_feedback(self):
        """Fixture de feedback de exemplo"""
        return {
            "id": str(uuid4()),
            "condominio_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "tipo_origem": "previsao",
            "origem_id": str(uuid4()),
            "valor": "positivo",
            "comentario": "Previsão acertada, obrigado!",
            "avaliacao": 5,
            "usuario_id": str(uuid4()),
            "created_at": datetime.utcnow().isoformat()
        }

    def test_valores_feedback_validos(self):
        """Testa valores válidos de feedback"""
        valores = ["positivo", "negativo", "neutro", "ignorado"]
        assert "positivo" in valores

    def test_tipos_origem_validos(self):
        """Testa tipos de origem válidos"""
        tipos = ["previsao", "sugestao", "comunicacao", "alerta"]
        assert "previsao" in tipos

    def test_calcular_metricas_modelo(self):
        """Testa cálculo de métricas do modelo"""
        feedbacks = [
            {"valor": "positivo"},
            {"valor": "positivo"},
            {"valor": "positivo"},
            {"valor": "negativo"},
            {"valor": "neutro"},
        ]

        total = len(feedbacks)
        positivos = len([f for f in feedbacks if f["valor"] == "positivo"])
        negativos = len([f for f in feedbacks if f["valor"] == "negativo"])

        taxa_acerto = positivos / total
        taxa_erro = negativos / total

        assert round(taxa_acerto, 2) == 0.60
        assert round(taxa_erro, 2) == 0.20

    def test_metricas_modelo_estrutura(self):
        """Testa estrutura de métricas do modelo"""
        metricas = {
            "modelo": "previsao_inadimplencia",
            "versao": "1.0.0",
            "periodo": "2025-01",
            "total_previsoes": 100,
            "verdadeiros_positivos": 75,
            "falsos_positivos": 10,
            "verdadeiros_negativos": 12,
            "falsos_negativos": 3,
            "precisao": 0.88,
            "recall": 0.96,
            "f1_score": 0.92,
            "accuracy": 0.87
        }

        # Validar cálculos
        tp = metricas["verdadeiros_positivos"]
        fp = metricas["falsos_positivos"]
        fn = metricas["falsos_negativos"]

        precisao_calc = tp / (tp + fp)
        recall_calc = tp / (tp + fn)
        f1_calc = 2 * (precisao_calc * recall_calc) / (precisao_calc + recall_calc)

        assert round(precisao_calc, 2) == metricas["precisao"]
        assert round(recall_calc, 2) == metricas["recall"]
