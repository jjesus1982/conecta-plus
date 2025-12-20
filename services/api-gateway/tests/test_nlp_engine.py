"""
Testes Unitários para o NLP Engine.

Testa:
- Análise de Sentimento
- Geração de Mensagens
- Otimização de Comunicação
- Edge Cases
"""

import pytest
from datetime import date, datetime, timedelta
from typing import Dict, List

import sys
sys.path.insert(0, '/opt/conecta-plus/services/api-gateway')

from services.nlp_engine import (
    AnalisadorSentimento,
    GeradorMensagensIA,
    OtimizadorComunicacao,
    AnaliseSentimento,
    MensagemGerada,
    PerfilComunicacao,
    CanalComunicacao,
    TomMensagem
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def analisador() -> AnalisadorSentimento:
    """Instância do analisador de sentimento."""
    return AnalisadorSentimento()


@pytest.fixture
def gerador() -> GeradorMensagensIA:
    """Instância do gerador de mensagens."""
    return GeradorMensagensIA()


@pytest.fixture
def otimizador() -> OtimizadorComunicacao:
    """Instância do otimizador de comunicação."""
    return OtimizadorComunicacao()


@pytest.fixture
def dados_morador() -> Dict:
    """Dados de morador para geração de mensagem."""
    return {
        'nome': 'João Silva',
        'unidade': 'Apto 101',
        'bloco': 'A'
    }


@pytest.fixture
def dados_boleto() -> Dict:
    """Boleto de exemplo."""
    return {
        'id': 'bol_001',
        'valor': 500.00,
        'vencimento': (date.today() - timedelta(days=10)).isoformat(),
        'competencia': '12/2024',
        'dias_atraso': 10,
        'status': 'vencido',
        'link_pix': 'https://pix.example.com/123',
        'link_pagamento': 'https://pay.example.com/123'
    }


@pytest.fixture
def dados_condominio() -> Dict:
    """Dados do condomínio."""
    return {
        'nome': 'Residencial Teste',
        'portal_url': 'https://portal.example.com',
        'telefone': '(11) 99999-9999'
    }


# =============================================================================
# TESTES DE ANÁLISE DE SENTIMENTO
# =============================================================================

class TestAnalisadorSentimento:
    """Testes para análise de sentimento."""

    def test_sentimento_positivo(self, analisador):
        """Testa detecção de sentimento positivo."""
        texto = "Obrigado pelo contato, vou pagar amanhã com certeza!"

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)
        assert resultado.score > 0
        assert resultado.intencao_pagamento > 0.3

    def test_sentimento_negativo(self, analisador):
        """Testa detecção de sentimento negativo."""
        texto = "Estou desempregado e passando dificuldades, não tenho como pagar agora."

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)
        assert resultado.score < 0
        assert resultado.requer_atencao_especial == True

    def test_sentimento_neutro(self, analisador):
        """Testa detecção de sentimento neutro."""
        texto = "Recebi a cobrança e estou verificando."

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)

    def test_sentimento_hostil(self, analisador):
        """Testa detecção de sentimento hostil."""
        texto = "Isso é um absurdo! Vou processar vocês!"

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)
        assert resultado.score < 0
        assert resultado.requer_atencao_especial == True

    def test_texto_vazio(self, analisador):
        """Testa com texto vazio."""
        resultado = analisador.analisar("")

        assert isinstance(resultado, AnaliseSentimento)
        # Texto vazio deve retornar score neutro
        assert resultado.score == 0.0

    def test_texto_none(self, analisador):
        """Testa com texto None - deve lançar erro ou tratar graciosamente."""
        # A implementação atual não trata None, então esperamos AttributeError
        with pytest.raises(AttributeError):
            analisador.analisar(None)

    def test_texto_muito_curto(self, analisador):
        """Testa com texto muito curto."""
        resultado = analisador.analisar("ok")

        assert isinstance(resultado, AnaliseSentimento)
        # Confiança baixa para texto curto
        assert resultado.confianca <= 0.6

    def test_texto_muito_longo(self, analisador):
        """Testa com texto muito longo."""
        texto = "palavra " * 1000

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)
        # Confiança alta para texto longo
        assert resultado.confianca >= 0.8

    def test_emojis(self, analisador):
        """Testa texto com emojis."""
        texto = "Vou pagar!"

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)

    def test_caracteres_especiais(self, analisador):
        """Testa texto com caracteres especiais."""
        texto = "Olá! @#$%^&*() Vou pagar!!!"

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)

    def test_intencao_pagamento_alta(self, analisador):
        """Testa detecção de intenção de pagamento alta."""
        texto = "Vou pagar amanhã sem falta, pode contar comigo!"

        resultado = analisador.analisar(texto)

        assert resultado.intencao_pagamento >= 0.5

    def test_intencao_pagamento_baixa(self, analisador):
        """Testa detecção de intenção de pagamento baixa."""
        texto = "Não tenho dinheiro e não sei quando vou conseguir."

        resultado = analisador.analisar(texto)

        assert resultado.intencao_pagamento < 0.5


# =============================================================================
# TESTES DE GERAÇÃO DE MENSAGENS
# =============================================================================

class TestGeradorMensagens:
    """Testes para geração de mensagens."""

    def test_gerar_mensagem_whatsapp(self, gerador, dados_morador, dados_boleto, dados_condominio):
        """Testa geração de mensagem para WhatsApp."""
        resultado = gerador.gerar_mensagem(
            dados_boleto=dados_boleto,
            dados_morador=dados_morador,
            dados_condominio=dados_condominio,
            canal=CanalComunicacao.WHATSAPP,
            tom=TomMensagem.AMIGAVEL
        )

        assert isinstance(resultado, MensagemGerada)
        assert len(resultado.corpo) > 0
        assert resultado.canal == CanalComunicacao.WHATSAPP
        # WhatsApp não tem assunto
        assert resultado.assunto is None

    def test_gerar_mensagem_email(self, gerador, dados_morador, dados_boleto, dados_condominio):
        """Testa geração de mensagem para email."""
        resultado = gerador.gerar_mensagem(
            dados_boleto=dados_boleto,
            dados_morador=dados_morador,
            dados_condominio=dados_condominio,
            canal=CanalComunicacao.EMAIL,
            tom=TomMensagem.PROFISSIONAL
        )

        assert isinstance(resultado, MensagemGerada)
        assert len(resultado.corpo) > 0
        assert resultado.canal == CanalComunicacao.EMAIL
        assert resultado.assunto is not None
        assert len(resultado.assunto) > 0

    def test_gerar_mensagem_sms(self, gerador, dados_morador, dados_boleto, dados_condominio):
        """Testa geração de mensagem para SMS (usa mesmo template de email)."""
        resultado = gerador.gerar_mensagem(
            dados_boleto=dados_boleto,
            dados_morador=dados_morador,
            dados_condominio=dados_condominio,
            canal=CanalComunicacao.SMS,
            tom=TomMensagem.PROFISSIONAL
        )

        assert isinstance(resultado, MensagemGerada)
        assert resultado.canal == CanalComunicacao.SMS

    def test_tons_diferentes(self, gerador, dados_morador, dados_boleto, dados_condominio):
        """Testa diferentes tons de mensagem."""
        tons = [
            TomMensagem.AMIGAVEL,
            TomMensagem.PROFISSIONAL,
            TomMensagem.FIRME,
            TomMensagem.URGENTE,
            TomMensagem.FINAL
        ]

        for tom in tons:
            resultado = gerador.gerar_mensagem(
                dados_boleto=dados_boleto,
                dados_morador=dados_morador,
                dados_condominio=dados_condominio,
                canal=CanalComunicacao.EMAIL,
                tom=tom
            )

            assert isinstance(resultado, MensagemGerada)
            assert resultado.tom == tom

    def test_tom_automatico(self, gerador, dados_morador, dados_boleto, dados_condominio):
        """Testa determinação automática de tom baseado no atraso."""
        # Boleto com muitos dias de atraso deve ter tom mais firme
        boleto_atrasado = {**dados_boleto, 'dias_atraso': 45, 'status': 'vencido'}

        resultado = gerador.gerar_mensagem(
            dados_boleto=boleto_atrasado,
            dados_morador=dados_morador,
            dados_condominio=dados_condominio,
            canal=CanalComunicacao.EMAIL
            # tom não especificado, deve ser automático
        )

        assert resultado.tom in [TomMensagem.FIRME, TomMensagem.URGENTE]

    def test_dados_incompletos(self, gerador, dados_boleto, dados_condominio):
        """Testa com dados incompletos."""
        dados_minimos = {'nome': 'Cliente'}

        resultado = gerador.gerar_mensagem(
            dados_boleto=dados_boleto,
            dados_morador=dados_minimos,
            dados_condominio=dados_condominio,
            canal=CanalComunicacao.WHATSAPP,
            tom=TomMensagem.AMIGAVEL
        )

        assert isinstance(resultado, MensagemGerada)
        assert 'Cliente' in resultado.corpo

    def test_variantes_ab(self, gerador, dados_morador, dados_boleto, dados_condominio):
        """Testa variantes A/B."""
        resultado_a = gerador.gerar_mensagem(
            dados_boleto=dados_boleto,
            dados_morador=dados_morador,
            dados_condominio=dados_condominio,
            canal=CanalComunicacao.WHATSAPP,
            tom=TomMensagem.AMIGAVEL,
            variante="A"
        )

        resultado_b = gerador.gerar_mensagem(
            dados_boleto=dados_boleto,
            dados_morador=dados_morador,
            dados_condominio=dados_condominio,
            canal=CanalComunicacao.WHATSAPP,
            tom=TomMensagem.AMIGAVEL,
            variante="B"
        )

        assert resultado_a.variante == "A"
        assert resultado_b.variante == "B"

    def test_score_efetividade(self, gerador, dados_morador, dados_boleto, dados_condominio):
        """Testa que score de efetividade está no range válido."""
        resultado = gerador.gerar_mensagem(
            dados_boleto=dados_boleto,
            dados_morador=dados_morador,
            dados_condominio=dados_condominio,
            canal=CanalComunicacao.WHATSAPP,
            tom=TomMensagem.AMIGAVEL
        )

        assert 0 <= resultado.score_efetividade <= 1


# =============================================================================
# TESTES DE OTIMIZAÇÃO DE COMUNICAÇÃO
# =============================================================================

class TestOtimizadorComunicacao:
    """Testes para otimização de comunicação."""

    def test_obter_perfil(self, otimizador):
        """Testa obtenção de perfil de comunicação."""
        historico = [
            {'canal': 'whatsapp', 'hora_resposta': '10:00', 'dia_semana_resposta': 1, 'teve_resposta': True},
            {'canal': 'whatsapp', 'hora_resposta': '14:00', 'dia_semana_resposta': 2, 'teve_resposta': True},
            {'canal': 'email', 'hora_resposta': '09:00', 'dia_semana_resposta': 3, 'teve_resposta': False}
        ]

        resultado = otimizador.obter_perfil(
            unidade_id='unit_001',
            historico_interacoes=historico
        )

        assert isinstance(resultado, PerfilComunicacao)
        assert resultado.unidade_id == 'unit_001'

    def test_obter_perfil_sem_historico(self, otimizador):
        """Testa perfil sem histórico retorna padrões."""
        resultado = otimizador.obter_perfil(
            unidade_id='unit_001',
            historico_interacoes=[]
        )

        assert isinstance(resultado, PerfilComunicacao)
        # Deve retornar perfil padrão
        assert resultado.canal_preferido == CanalComunicacao.WHATSAPP
        assert resultado.tom_mais_efetivo == TomMensagem.PROFISSIONAL

    def test_cache_perfil(self, otimizador):
        """Testa que perfil é cacheado."""
        historico = [{'canal': 'whatsapp', 'teve_resposta': True}]

        perfil1 = otimizador.obter_perfil('unit_001', historico)
        perfil2 = otimizador.obter_perfil('unit_001', historico)

        # Deve retornar o mesmo objeto (cacheado)
        assert perfil1 is perfil2

    def test_sugerir_melhor_momento(self, otimizador):
        """Testa sugestão de melhor momento."""
        historico = [
            {'canal': 'whatsapp', 'hora_resposta': '10:00', 'dia_semana_resposta': 1, 'teve_resposta': True}
        ]
        perfil = otimizador.obter_perfil('unit_002', historico)

        sugestao = otimizador.sugerir_melhor_momento(perfil)

        assert 'canal' in sugestao
        assert 'horario' in sugestao
        assert 'data_sugerida' in sugestao
        assert 'tom_sugerido' in sugestao

    def test_taxa_resposta_calculada(self, otimizador):
        """Testa cálculo da taxa de resposta."""
        historico = [
            {'canal': 'whatsapp', 'teve_resposta': True},
            {'canal': 'whatsapp', 'teve_resposta': True},
            {'canal': 'whatsapp', 'teve_resposta': False},
            {'canal': 'whatsapp', 'teve_resposta': False}
        ]

        perfil = otimizador.obter_perfil('unit_003', historico)

        # 2 de 4 = 50%
        assert perfil.taxa_resposta == 0.5


# =============================================================================
# TESTES DE EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Testes de edge cases."""

    def test_unicode_text(self, analisador):
        """Testa texto com caracteres unicode."""
        texto = "Olá! Préço está çerto? Não vou pagar não!"

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)

    def test_mixed_language(self, analisador):
        """Testa texto com múltiplos idiomas."""
        texto = "Ok, I will pay tomorrow. Vou pagar amanhã!"

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)

    def test_numbers_in_text(self, analisador):
        """Testa texto com números."""
        texto = "Vou pagar R$ 500,00 dia 15/01/2025"

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)

    def test_only_numbers(self, analisador):
        """Testa texto apenas com números."""
        texto = "123456789"

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)

    def test_html_in_text(self, analisador):
        """Testa texto com HTML."""
        texto = "<p>Vou pagar <b>amanhã</b></p>"

        resultado = analisador.analisar(texto)

        assert isinstance(resultado, AnaliseSentimento)


# =============================================================================
# TESTES DE INTEGRAÇÃO
# =============================================================================

class TestIntegracao:
    """Testes de integração NLP."""

    def test_fluxo_analise_geracao(self, analisador, gerador, dados_morador, dados_boleto, dados_condominio):
        """Testa fluxo de análise -> geração."""
        # 1. Analisa resposta do cliente
        resposta_cliente = "Estou com dificuldades mas pretendo pagar na próxima semana"
        analise = analisador.analisar(resposta_cliente)

        # 2. Ajusta tom baseado na análise
        if analise.intencao_pagamento > 0.5:
            tom = TomMensagem.AMIGAVEL
        else:
            tom = TomMensagem.PROFISSIONAL

        # 3. Gera resposta
        mensagem = gerador.gerar_mensagem(
            dados_boleto=dados_boleto,
            dados_morador=dados_morador,
            dados_condominio=dados_condominio,
            canal=CanalComunicacao.WHATSAPP,
            tom=tom
        )

        assert analise is not None
        assert mensagem is not None

    def test_otimizacao_completa(self, analisador, gerador, otimizador, dados_morador, dados_boleto, dados_condominio):
        """Testa fluxo completo de otimização."""
        # 1. Determina perfil
        historico = [
            {'canal': 'whatsapp', 'hora_resposta': '10:00', 'teve_resposta': True}
        ]
        perfil = otimizador.obter_perfil('unit_001', historico)

        # 2. Gera mensagem para o canal preferido
        mensagem = gerador.gerar_mensagem(
            dados_boleto=dados_boleto,
            dados_morador=dados_morador,
            dados_condominio=dados_condominio,
            canal=perfil.canal_preferido,
            tom=perfil.tom_mais_efetivo
        )

        assert perfil is not None
        assert mensagem is not None
        assert mensagem.canal == perfil.canal_preferido


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
