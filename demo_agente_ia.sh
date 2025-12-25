#!/bin/bash

# Demo do Agente Financeiro com IA - Conecta Plus
# Script de demonstração completa

API="http://localhost:3001/api"

echo "=========================================="
echo " DEMONSTRAÇÃO: AGENTE FINANCEIRO IA"
echo " Conecta Plus - 2025"
echo "=========================================="
echo ""

# Login
echo "1. Fazendo login..."
TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@conectaplus.com.br", "senha": "admin123"}' | jq -r '.access_token')

echo "   ✓ Autenticado com sucesso"
echo ""

# Previsão de Inadimplência
echo "2. Previsão de Inadimplência - Unidade 101"
curl -s "$API/financeiro/ia/previsao-inadimplencia/unit_001" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    unidade: .unidade,
    morador: .morador,
    probabilidade: .previsao.probabilidade,
    classificacao: .previsao.classificacao,
    score: .previsao.score,
    recomendacao: .recomendacao
  }'
echo ""

# Alertas Proativos
echo "3. Alertas Proativos do Sistema"
curl -s "$API/financeiro/ia/alertas-proativos" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    total: .total_alertas,
    criticos: .criticos,
    primeiros_3: .alertas[:3] | map({tipo, severidade, titulo})
  }'
echo ""

# Priorização de Cobranças
echo "4. Priorização Inteligente de Cobranças"
curl -s "$API/financeiro/ia/priorizar-cobranca" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    total_vencidos: .total_vencidos,
    valor_total: .valor_total,
    top_3: .priorizados[:3] | map({posicao, unidade, morador, score_prioridade, estrategia})
  }'
echo ""

# Análise de Sentimento
echo "5. Análise de Sentimento NLP"
curl -s -X POST "$API/financeiro/ia/analisar-sentimento" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "Vou pagar amanhã, obrigado pela compreensão"}' | jq '{
    sentimento: .analise.sentimento,
    score: .analise.score,
    intencao_pagamento: .analise.intencao_pagamento,
    sugestao: .sugestao_resposta
  }'
echo ""

# Fluxo de Caixa
echo "6. Previsão de Fluxo de Caixa (próximos 30 dias)"
curl -s "$API/financeiro/ia/previsao-fluxo-caixa?dias=30" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    periodo_dias: .periodo_dias,
    semanas: .semanas,
    resumo: .resumo
  }'
echo ""

# Dashboard Inteligente
echo "7. Dashboard Inteligente com Insights"
curl -s "$API/financeiro/ia/dashboard-inteligente" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    saude_financeira: .saude_financeira,
    insights: .insights | map(.titulo),
    acoes_recomendadas: .acoes_recomendadas
  }'
echo ""

# Melhor Momento
echo "8. Melhor Momento para Contato - Unidade 101"
curl -s "$API/financeiro/ia/melhor-momento/unit_001" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    morador: .morador,
    canal: .sugestao.canal,
    horario: .sugestao.horario,
    dia_semana: .sugestao.dia_semana,
    probabilidade_resposta: .sugestao.probabilidade_resposta
  }'
echo ""

# Score
echo "9. Score de Inadimplência - Unidade 101"
curl -s "$API/financeiro/ia/score/unit_001" \
  -H "Authorization: Bearer $TOKEN" | jq '{
    score: .score,
    classificacao: .classificacao,
    probabilidade: .probabilidade,
    fatores: .fatores
  }'
echo ""

echo "=========================================="
echo " ✓ DEMONSTRAÇÃO CONCLUÍDA!"
echo "=========================================="
