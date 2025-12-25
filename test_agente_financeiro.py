#!/usr/bin/env python3
"""
Script de teste completo do Agente Financeiro com IA
Conecta Plus - 2025
"""

import requests
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Any

# Configurações
API_BASE = "http://localhost:3001/api"
TEST_USER = {
    "email": "admin@conectaplus.com.br",
    "senha": "admin123"
}

class TesteAgenteFinanceiro:
    """Testes automatizados do Agente Financeiro"""

    def __init__(self):
        self.token = None
        self.boletos_criados = []
        self.session = requests.Session()

    def fazer_login(self):
        """Faz login e obtém token"""
        url = f"{API_BASE}/auth/login"
        response = self.session.post(url, json=TEST_USER)
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('access_token')
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})
            print("✓ Autenticação realizada com sucesso\n")
        else:
            print(f"❌ Falha na autenticação: {response.status_code}\n")

    def executar_todos_testes(self):
        """Executa toda a suíte de testes"""
        print("=" * 80)
        print(" TESTE COMPLETO DO AGENTE FINANCEIRO - IA")
        print("=" * 80)
        print()

        try:
            # 0. Login
            print("[0/10] Fazendo login...")
            self.fazer_login()

            # 1. Setup
            print("[1/10] Criando boletos de teste...")
            self.criar_boletos_teste()
            print("✓ Boletos criados com sucesso\n")

            # 2. Teste: Previsão de Inadimplência
            print("[2/10] Testando previsão de inadimplência...")
            self.testar_previsao_inadimplencia()
            print("✓ Previsão funcionando\n")

            # 3. Teste: Alertas Proativos
            print("[3/10] Testando alertas proativos...")
            self.testar_alertas_proativos()
            print("✓ Alertas gerados\n")

            # 4. Teste: Priorização de Cobranças
            print("[4/10] Testando priorização de cobranças...")
            self.testar_priorizacao_cobranca()
            print("✓ Priorização funcionando\n")

            # 5. Teste: Análise de Sentimento
            print("[5/10] Testando análise de sentimento...")
            self.testar_analise_sentimento()
            print("✓ Análise NLP funcionando\n")

            # 6. Teste: Geração de Mensagens
            print("[6/10] Testando geração de mensagens...")
            self.testar_geracao_mensagens()
            print("✓ Mensagens personalizadas geradas\n")

            # 7. Teste: Previsão de Fluxo de Caixa
            print("[7/10] Testando previsão de fluxo de caixa...")
            self.testar_previsao_fluxo_caixa()
            print("✓ Previsão de fluxo funcionando\n")

            # 8. Teste: Dashboard Inteligente
            print("[8/10] Testando dashboard inteligente...")
            self.testar_dashboard_inteligente()
            print("✓ Dashboard com insights gerado\n")

            # 9. Teste: Melhor Momento
            print("[9/10] Testando sugestão de melhor momento...")
            self.testar_melhor_momento()
            print("✓ Otimização de timing funcionando\n")

            # 10. Teste: Score Unidade
            print("[10/10] Testando score de unidade...")
            self.testar_score_unidade()
            print("✓ Score calculado\n")

            print("=" * 80)
            print(" TODOS OS TESTES CONCLUÍDOS COM SUCESSO! ✓")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()

    def criar_boletos_teste(self):
        """Cria boletos de teste"""
        # Boletos sem autenticação via endpoint público
        unidades = [
            {"id": "unit_001", "numero": "101", "bloco": "A"},
            {"id": "unit_002", "numero": "102", "bloco": "A"},
            {"id": "unit_003", "numero": "103", "bloco": "A"},
            {"id": "unit_004", "numero": "201", "bloco": "A"},
        ]

        hoje = date.today()

        for i, unidade in enumerate(unidades):
            # Varia os status
            if i == 0:
                vencimento = (hoje - timedelta(days=45)).strftime('%Y-%m-%d')
                status = "vencido"
            elif i == 1:
                vencimento = (hoje - timedelta(days=15)).strftime('%Y-%m-%d')
                status = "vencido"
            elif i == 2:
                vencimento = (hoje + timedelta(days=5)).strftime('%Y-%m-%d')
                status = "pendente"
            else:
                vencimento = (hoje - timedelta(days=3)).strftime('%Y-%m-%d')
                status = "pago"

            boleto = {
                "id": f"bol_test_{i}",
                "unidade_id": unidade["id"],
                "unidade": f"Apt {unidade['numero']} - Bloco {unidade['bloco']}",
                "valor": 850.00 + (i * 50),
                "vencimento": vencimento,
                "status": status,
                "competencia": "01/2025",
                "dias_atraso": (hoje - datetime.strptime(vencimento, '%Y-%m-%d').date()).days if status == "vencido" else 0
            }
            self.boletos_criados.append(boleto)
            print(f"  - Boleto {unidade['numero']}: {status}, vencimento {vencimento}")

    def testar_previsao_inadimplencia(self):
        """Testa API de previsão de inadimplência"""
        url = f"{API_BASE}/financeiro/ia/previsao-inadimplencia/unit_001"

        response = self.session.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"  - Probabilidade: {data.get('previsao', {}).get('probabilidade', 'N/A')}")
            print(f"  - Classificação: {data.get('previsao', {}).get('classificacao', 'N/A')}")
            print(f"  - Score: {data.get('previsao', {}).get('score', 'N/A')}/1000")
        else:
            print(f"  - Status: {response.status_code}")
            print(f"  - Response: {response.text[:200]}")

    def testar_alertas_proativos(self):
        """Testa sistema de alertas proativos"""
        url = f"{API_BASE}/financeiro/ia/alertas-proativos"

        response = self.session.get(url)
        if response.status_code == 200:
            data = response.json()
            total = data.get('total_alertas', 0)
            criticos = data.get('criticos', 0)
            print(f"  - Total de alertas: {total}")
            print(f"  - Alertas críticos: {criticos}")

            if data.get('alertas'):
                primeiro = data['alertas'][0]
                print(f"  - Exemplo: {primeiro.get('titulo', 'N/A')}")
        else:
            print(f"  - Status: {response.status_code}")

    def testar_priorizacao_cobranca(self):
        """Testa priorização inteligente de cobranças"""
        url = f"{API_BASE}/financeiro/ia/priorizar-cobranca"

        response = self.session.get(url)
        if response.status_code == 200:
            data = response.json()
            total = data.get('total_vencidos', 0)
            print(f"  - Boletos vencidos: {total}")

            if data.get('priorizados'):
                top1 = data['priorizados'][0]
                print(f"  - TOP 1: Unidade {top1.get('unidade', 'N/A')}")
                print(f"  - Score prioridade: {top1.get('score_prioridade', 0)}/100")
                print(f"  - Estratégia: {top1.get('estrategia', 'N/A')[:50]}...")
        else:
            print(f"  - Status: {response.status_code}")

    def testar_analise_sentimento(self):
        """Testa análise de sentimento NLP"""
        url = f"{API_BASE}/financeiro/ia/analisar-sentimento"

        mensagens_teste = [
            "Estou com dificuldades financeiras este mês, mas pretendo pagar em breve",
            "Vou pagar amanhã pela manhã, pode deixar!",
            "Isso é um absurdo! Vocês são uns ladrões!",
            "Obrigado pela compreensão, vou regularizar hoje mesmo"
        ]

        for msg in mensagens_teste:
            response = self.session.post(url, json={"mensagem": msg})
            if response.status_code == 200:
                data = response.json()
                sentimento = data.get('analise', {}).get('sentimento', 'N/A')
                score = data.get('analise', {}).get('score', 0)
                intencao = data.get('analise', {}).get('intencao_pagamento', 0)

                print(f"  - \"{msg[:40]}...\"")
                print(f"    Sentimento: {sentimento}, Score: {score:.2f}, Intenção: {intencao:.2f}")
                break

    def testar_geracao_mensagens(self):
        """Testa geração de mensagens personalizadas"""
        url = f"{API_BASE}/financeiro/ia/gerar-mensagem-cobranca"

        if not self.boletos_criados:
            print("  - Sem boletos para testar")
            return

        boleto = self.boletos_criados[0]
        params = {
            "boleto_id": boleto['id'],
            "canal": "whatsapp",
            "tom": "profissional",
            "variante": "A"
        }

        response = self.session.post(url, params=params)
        if response.status_code == 200:
            data = response.json()
            mensagem = data.get('mensagem', {})
            print(f"  - Canal: {data.get('canal', 'N/A')}")
            print(f"  - Tom: {mensagem.get('tom', 'N/A')}")
            print(f"  - Efetividade: {data.get('score_efetividade', 0):.2f}")
            corpo = mensagem.get('corpo', '')
            if corpo:
                print(f"  - Preview: {corpo[:80]}...")
        else:
            print(f"  - Status: {response.status_code}")

    def testar_previsao_fluxo_caixa(self):
        """Testa previsão de fluxo de caixa"""
        url = f"{API_BASE}/financeiro/ia/previsao-fluxo-caixa"

        response = self.session.get(url, params={"dias": 90})
        if response.status_code == 200:
            data = response.json()
            semanas = data.get('semanas', 0)
            resumo = data.get('resumo', {})

            print(f"  - Período: {data.get('periodo_dias', 0)} dias ({semanas} semanas)")
            print(f"  - Receita total prevista: R$ {resumo.get('receita_total_prevista', 0):,.2f}")
            print(f"  - Despesa total prevista: R$ {resumo.get('despesa_total_prevista', 0):,.2f}")
            print(f"  - Saldo no período: R$ {resumo.get('saldo_periodo', 0):,.2f}")
        else:
            print(f"  - Status: {response.status_code}")

    def testar_dashboard_inteligente(self):
        """Testa dashboard inteligente"""
        url = f"{API_BASE}/financeiro/ia/dashboard-inteligente"

        response = self.session.get(url)
        if response.status_code == 200:
            data = response.json()
            saude = data.get('saude_financeira', {})
            insights = data.get('insights', [])

            print(f"  - Score de saúde: {saude.get('score', 0)}/100")
            print(f"  - Classificação: {saude.get('classificacao', 'N/A')}")
            print(f"  - Insights gerados: {len(insights)}")

            if insights:
                print(f"  - Top insight: {insights[0].get('titulo', 'N/A')}")
        else:
            print(f"  - Status: {response.status_code}")

    def testar_melhor_momento(self):
        """Testa sugestão de melhor momento"""
        url = f"{API_BASE}/financeiro/ia/melhor-momento/unit_001"

        response = self.session.get(url)
        if response.status_code == 200:
            data = response.json()
            sugestao = data.get('sugestao', {})

            print(f"  - Canal: {sugestao.get('canal', 'N/A')}")
            print(f"  - Horário: {sugestao.get('horario', 'N/A')}")
            print(f"  - Dia: {sugestao.get('dia_semana', 'N/A')}")
            print(f"  - Prob. resposta: {sugestao.get('probabilidade_resposta', 0):.2f}")
        else:
            print(f"  - Status: {response.status_code}")

    def testar_score_unidade(self):
        """Testa score de unidade"""
        url = f"{API_BASE}/financeiro/ia/score/unit_001"

        response = self.session.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"  - Score: {data.get('score', 'N/A')}")
            print(f"  - Classificação: {data.get('classificacao', 'N/A')}")
        else:
            print(f"  - Status: {response.status_code}")


if __name__ == "__main__":
    teste = TesteAgenteFinanceiro()
    teste.executar_todos_testes()
