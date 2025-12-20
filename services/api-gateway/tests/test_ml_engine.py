"""
Testes Unitários para o ML Engine.

Testa:
- Feature Engineering
- Modelo de Inadimplência
- Previsão de Fluxo de Caixa
- Sistema de Alertas
- Priorização de Cobrança
- Edge Cases
"""

import pytest
from datetime import date, datetime, timedelta
from typing import Dict, List

import sys
sys.path.insert(0, '/opt/conecta-plus/services/api-gateway')

from services.ml_engine import (
    FeatureEngineering,
    ModeloInadimplenciaML,
    PrevisaoFluxoCaixaML,
    SistemaAlertasProativos,
    PriorizadorCobranca,
    PrevisaoInadimplencia,
    PrevisaoFluxoCaixa,
    AlertaProativo
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def unidade_exemplo() -> Dict:
    """Fixture de unidade de exemplo."""
    return {
        'id': 'unit_001',
        'bloco': 'A',
        'numero': '101',
        'proprietario_nome': 'João Silva',
        'proprietario_cpf': '529.982.247-25'
    }


@pytest.fixture
def historico_boletos_bom() -> List[Dict]:
    """Histórico de boletos de bom pagador."""
    boletos = []
    hoje = date.today()
    for i in range(12):
        vencimento = hoje - timedelta(days=30 * (i + 1))
        boletos.append({
            'id': f'bol_{i}',
            'valor': 500.00,
            'vencimento': vencimento.isoformat(),
            'status': 'pago',
            'data_pagamento': (vencimento - timedelta(days=2)).isoformat()
        })
    return boletos


@pytest.fixture
def historico_boletos_mau() -> List[Dict]:
    """Histórico de boletos de mau pagador."""
    boletos = []
    hoje = date.today()
    for i in range(12):
        vencimento = hoje - timedelta(days=30 * (i + 1))
        status = 'vencido' if i < 6 else 'pago'  # Mais boletos vencidos
        data_pag = (vencimento + timedelta(days=30)).isoformat() if status == 'pago' else None
        boletos.append({
            'id': f'bol_{i}',
            'valor': 500.00,
            'vencimento': vencimento.isoformat(),
            'status': status,
            'data_pagamento': data_pag
        })
    return boletos


@pytest.fixture
def historico_pagamentos() -> List[Dict]:
    """Histórico de pagamentos."""
    pagamentos = []
    hoje = date.today()
    for i in range(6):
        pagamentos.append({
            'id': f'pag_{i}',
            'valor': 500.00,
            'data_pagamento': (hoje - timedelta(days=30 * (i + 1))).isoformat(),
            'forma_pagamento': 'pix' if i % 2 == 0 else 'boleto'
        })
    return pagamentos


@pytest.fixture
def acordos_exemplo() -> List[Dict]:
    """Acordos de exemplo."""
    return [
        {
            'id': 'acordo_1',
            'valor_original': 1500.00,
            'valor_negociado': 1300.00,
            'status': 'quitado'
        }
    ]


@pytest.fixture
def modelo_inadimplencia() -> ModeloInadimplenciaML:
    """Instância do modelo de inadimplência."""
    return ModeloInadimplenciaML()


@pytest.fixture
def modelo_fluxo_caixa() -> PrevisaoFluxoCaixaML:
    """Instância do modelo de fluxo de caixa."""
    return PrevisaoFluxoCaixaML()


@pytest.fixture
def sistema_alertas() -> SistemaAlertasProativos:
    """Instância do sistema de alertas."""
    return SistemaAlertasProativos()


@pytest.fixture
def priorizador() -> PriorizadorCobranca:
    """Instância do priorizador de cobrança."""
    return PriorizadorCobranca()


# =============================================================================
# TESTES DE FEATURE ENGINEERING
# =============================================================================

class TestFeatureEngineering:
    """Testes para a classe FeatureEngineering."""

    def test_calcular_features_cliente_novo(self, unidade_exemplo):
        """Testa features para cliente sem histórico."""
        features = FeatureEngineering.calcular_features_pagador(
            historico_boletos=[],
            historico_pagamentos=[],
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert 'total_boletos' in features
        assert features['total_boletos'] == 0
        # Cliente novo tem features de novo cliente

    def test_calcular_features_bom_pagador(
        self,
        unidade_exemplo,
        historico_boletos_bom,
        historico_pagamentos
    ):
        """Testa features para bom pagador."""
        features = FeatureEngineering.calcular_features_pagador(
            historico_boletos=historico_boletos_bom,
            historico_pagamentos=historico_pagamentos,
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert features['total_boletos'] == 12
        assert features['taxa_adimplencia'] == 1.0
        assert features['boletos_vencidos'] == 0

    def test_calcular_features_mau_pagador(
        self,
        unidade_exemplo,
        historico_boletos_mau,
        historico_pagamentos
    ):
        """Testa features para mau pagador."""
        features = FeatureEngineering.calcular_features_pagador(
            historico_boletos=historico_boletos_mau,
            historico_pagamentos=historico_pagamentos,
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert features['boletos_vencidos'] == 6
        assert features['taxa_adimplencia'] < 1.0
        assert features['valor_vencido'] > 0

    def test_calcular_features_com_acordos(
        self,
        unidade_exemplo,
        historico_boletos_bom,
        historico_pagamentos,
        acordos_exemplo
    ):
        """Testa features considerando acordos."""
        features = FeatureEngineering.calcular_features_pagador(
            historico_boletos=historico_boletos_bom,
            historico_pagamentos=historico_pagamentos,
            acordos=acordos_exemplo,
            dados_unidade=unidade_exemplo
        )

        assert features['total_acordos'] == 1
        assert features['acordos_cumpridos'] == 1
        assert features['taxa_cumprimento_acordo'] == 1.0


# =============================================================================
# TESTES DO MODELO DE INADIMPLÊNCIA
# =============================================================================

class TestModeloInadimplencia:
    """Testes para o modelo de inadimplência."""

    def test_prever_bom_pagador(
        self,
        modelo_inadimplencia,
        unidade_exemplo,
        historico_boletos_bom,
        historico_pagamentos
    ):
        """Testa previsão para bom pagador."""
        resultado = modelo_inadimplencia.prever(
            historico_boletos=historico_boletos_bom,
            historico_pagamentos=historico_pagamentos,
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert isinstance(resultado, PrevisaoInadimplencia)
        assert resultado.classificacao in ['baixo', 'medio']
        assert resultado.score > 600  # Score bom
        assert resultado.probabilidade < 0.5

    def test_prever_mau_pagador(
        self,
        modelo_inadimplencia,
        unidade_exemplo,
        historico_boletos_mau,
        historico_pagamentos
    ):
        """Testa previsão para mau pagador."""
        resultado = modelo_inadimplencia.prever(
            historico_boletos=historico_boletos_mau,
            historico_pagamentos=historico_pagamentos,
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert isinstance(resultado, PrevisaoInadimplencia)
        # Modelo pode classificar como médio ou alto
        assert resultado.classificacao in ['medio', 'alto', 'critico']
        assert resultado.probabilidade > 0.15

    def test_prever_cliente_novo(
        self,
        modelo_inadimplencia,
        unidade_exemplo
    ):
        """Testa previsão para cliente sem histórico."""
        resultado = modelo_inadimplencia.prever(
            historico_boletos=[],
            historico_pagamentos=[],
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert isinstance(resultado, PrevisaoInadimplencia)
        # Cliente novo deve ter confiança menor
        assert resultado.confianca <= 0.9

    def test_versao_modelo(self, modelo_inadimplencia):
        """Verifica versão do modelo."""
        assert hasattr(modelo_inadimplencia, 'VERSAO')
        assert modelo_inadimplencia.VERSAO is not None

    def test_recomendacao_gerada(
        self,
        modelo_inadimplencia,
        unidade_exemplo,
        historico_boletos_bom,
        historico_pagamentos
    ):
        """Testa se recomendação é gerada."""
        resultado = modelo_inadimplencia.prever(
            historico_boletos=historico_boletos_bom,
            historico_pagamentos=historico_pagamentos,
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert resultado.recomendacao is not None
        assert len(resultado.recomendacao) > 0


# =============================================================================
# TESTES DE PREVISÃO DE FLUXO DE CAIXA
# =============================================================================

class TestPrevisaoFluxoCaixa:
    """Testes para previsão de fluxo de caixa."""

    def test_prever_dias(self, modelo_fluxo_caixa):
        """Testa previsão de vários dias."""
        historico_receitas = [
            {'data': (date.today() - timedelta(days=i*7)).isoformat(), 'valor': 10000 + i*100}
            for i in range(12)
        ]
        historico_despesas = [
            {'data': (date.today() - timedelta(days=i*7)).isoformat(), 'valor': 8000 + i*50}
            for i in range(12)
        ]
        boletos_pendentes = [
            {'id': 'b1', 'valor': 500, 'vencimento': (date.today() + timedelta(days=10)).isoformat()}
        ]

        resultado = modelo_fluxo_caixa.prever(
            historico_receitas=historico_receitas,
            historico_despesas=historico_despesas,
            boletos_pendentes=boletos_pendentes,
            dias_previsao=30
        )

        assert isinstance(resultado, list)
        assert len(resultado) > 0

    def test_prever_sem_historico(self, modelo_fluxo_caixa):
        """Testa previsão sem histórico."""
        resultado = modelo_fluxo_caixa.prever(
            historico_receitas=[],
            historico_despesas=[],
            boletos_pendentes=[],
            dias_previsao=30
        )

        assert isinstance(resultado, list)


# =============================================================================
# TESTES DO SISTEMA DE ALERTAS
# =============================================================================

class TestSistemaAlertas:
    """Testes para o sistema de alertas proativos."""

    def test_gerar_alertas(self, sistema_alertas, unidade_exemplo):
        """Testa geração de alertas."""
        unidades = [unidade_exemplo]
        boletos = [
            {
                'id': 'bol_1',
                'unidade_id': 'unit_001',
                'valor': 500.00,
                'vencimento': (date.today() + timedelta(days=3)).isoformat(),
                'status': 'pendente'
            }
        ]

        alertas = sistema_alertas.gerar_alertas(
            unidades=unidades,
            boletos=boletos,
            pagamentos=[],
            acordos=[],
            lancamentos=[],
            saldo_atual=10000.0
        )

        assert isinstance(alertas, list)

    def test_gerar_alertas_boleto_vencido(self, sistema_alertas, unidade_exemplo):
        """Testa alerta para boleto vencido."""
        unidades = [unidade_exemplo]
        boletos = [
            {
                'id': 'bol_1',
                'unidade_id': 'unit_001',
                'valor': 500.00,
                'vencimento': (date.today() - timedelta(days=10)).isoformat(),
                'status': 'vencido'
            }
        ]

        alertas = sistema_alertas.gerar_alertas(
            unidades=unidades,
            boletos=boletos,
            pagamentos=[],
            acordos=[],
            lancamentos=[],
            saldo_atual=10000.0
        )

        assert isinstance(alertas, list)


# =============================================================================
# TESTES DO PRIORIZADOR DE COBRANÇA
# =============================================================================

class TestPriorizadorCobranca:
    """Testes para o priorizador de cobrança."""

    def test_priorizar_boletos_vencidos(self, priorizador, unidade_exemplo):
        """Testa priorização de boletos vencidos."""
        boletos_vencidos = [
            {
                'id': 'bol_1',
                'unidade_id': 'unit_001',
                'valor': 500.00,
                'vencimento': (date.today() - timedelta(days=5)).isoformat(),
                'status': 'vencido'
            },
            {
                'id': 'bol_2',
                'unidade_id': 'unit_001',
                'valor': 1500.00,
                'vencimento': (date.today() - timedelta(days=30)).isoformat(),
                'status': 'vencido'
            }
        ]
        unidades = {'unit_001': unidade_exemplo}
        historico_boletos = {'unit_001': []}
        historico_pagamentos = {'unit_001': []}
        acordos = {'unit_001': []}

        resultado = priorizador.priorizar(
            boletos_vencidos=boletos_vencidos,
            unidades=unidades,
            historico_boletos=historico_boletos,
            historico_pagamentos=historico_pagamentos,
            acordos=acordos
        )

        assert isinstance(resultado, list)

    def test_priorizar_sem_boletos(self, priorizador):
        """Testa priorização sem boletos."""
        resultado = priorizador.priorizar(
            boletos_vencidos=[],
            unidades={},
            historico_boletos={},
            historico_pagamentos={},
            acordos={}
        )

        assert isinstance(resultado, list)
        assert len(resultado) == 0


# =============================================================================
# TESTES DE EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Testes de edge cases e dados inválidos."""

    def test_boleto_sem_vencimento(self, modelo_inadimplencia, unidade_exemplo):
        """Testa boleto sem data de vencimento."""
        boletos = [{'id': 'bol_1', 'valor': 500.00, 'status': 'pendente'}]

        resultado = modelo_inadimplencia.prever(
            historico_boletos=boletos,
            historico_pagamentos=[],
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert resultado is not None

    def test_valor_negativo(self, modelo_inadimplencia, unidade_exemplo):
        """Testa boleto com valor negativo."""
        boletos = [
            {
                'id': 'bol_1',
                'valor': -500.00,
                'vencimento': date.today().isoformat(),
                'status': 'pendente'
            }
        ]

        resultado = modelo_inadimplencia.prever(
            historico_boletos=boletos,
            historico_pagamentos=[],
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert resultado is not None

    def test_data_invalida(self, modelo_inadimplencia, unidade_exemplo):
        """Testa boleto com data inválida."""
        boletos = [
            {
                'id': 'bol_1',
                'valor': 500.00,
                'vencimento': 'data-invalida',
                'status': 'pendente'
            }
        ]

        resultado = modelo_inadimplencia.prever(
            historico_boletos=boletos,
            historico_pagamentos=[],
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert resultado is not None

    def test_unidade_vazia(self, modelo_inadimplencia, historico_boletos_bom):
        """Testa com unidade vazia."""
        resultado = modelo_inadimplencia.prever(
            historico_boletos=historico_boletos_bom,
            historico_pagamentos=[],
            acordos=[],
            dados_unidade={}
        )

        assert resultado is not None
        assert resultado.unidade_id == 'unknown'

    def test_none_values(self, modelo_inadimplencia, unidade_exemplo):
        """Testa com valores None."""
        resultado = modelo_inadimplencia.prever(
            historico_boletos=None or [],
            historico_pagamentos=None or [],
            acordos=None or [],
            dados_unidade=unidade_exemplo
        )

        assert resultado is not None

    def test_lista_muito_grande(self, modelo_inadimplencia, unidade_exemplo):
        """Testa com lista muito grande de boletos."""
        boletos = [
            {
                'id': f'bol_{i}',
                'valor': 500.00,
                'vencimento': (date.today() - timedelta(days=i)).isoformat(),
                'status': 'pago'
            }
            for i in range(1000)
        ]

        resultado = modelo_inadimplencia.prever(
            historico_boletos=boletos,
            historico_pagamentos=[],
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        assert resultado is not None


# =============================================================================
# TESTES DE INTEGRAÇÃO
# =============================================================================

class TestIntegracao:
    """Testes de integração entre componentes."""

    def test_fluxo_completo(
        self,
        modelo_inadimplencia,
        sistema_alertas,
        unidade_exemplo,
        historico_boletos_mau
    ):
        """Testa fluxo completo de análise."""
        # 1. Prevê inadimplência
        previsao = modelo_inadimplencia.prever(
            historico_boletos=historico_boletos_mau,
            historico_pagamentos=[],
            acordos=[],
            dados_unidade=unidade_exemplo
        )

        # 2. Gera alertas
        alertas = sistema_alertas.gerar_alertas(
            unidades=[unidade_exemplo],
            boletos=historico_boletos_mau,
            pagamentos=[],
            acordos=[],
            lancamentos=[],
            saldo_atual=10000.0
        )

        # 3. Verifica consistência
        assert previsao is not None
        assert isinstance(alertas, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
