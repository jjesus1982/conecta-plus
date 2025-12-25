/**
 * Conecta Plus - Serviço de IA Financeira
 * APIs inteligentes para gestão financeira com ML/NLP
 */

import { apiClient } from './api-client';

export interface PrevisaoInadimplencia {
  unidade_id: string;
  unidade: string;
  morador: string;
  previsao: {
    probabilidade: number;
    classificacao: 'baixo_risco' | 'medio_risco' | 'alto_risco';
    score: number;
    confianca: number;
  };
  fatores_risco: string[];
  recomendacao: string;
  modelo_versao: string;
}

export interface Alerta {
  tipo: string;
  severidade: 'info' | 'warning' | 'critical';
  titulo: string;
  mensagem: string;
  acao_recomendada: string;
  probabilidade: number;
  entidade: {
    tipo: string;
    id: string;
  };
  criado_em: string;
}

export interface CobrancaPriorizada {
  posicao: number;
  boleto_id: string;
  unidade: string;
  morador: string;
  valor: number;
  dias_atraso: number;
  score_prioridade: number;
  probabilidade_pagamento: number;
  classificacao_risco: string;
  estrategia: string;
  componentes_score: {
    dias: number;
    valor: number;
  };
}

export interface AnaliseSentimento {
  mensagem_original: string;
  analise: {
    sentimento: 'muito_positivo' | 'positivo' | 'neutro' | 'negativo' | 'muito_negativo' | 'hostil';
    score: number;
    confianca: number;
    intencao_pagamento: number;
    emocoes: string[];
    requer_atencao: boolean;
  };
  sugestao_resposta: string;
}

export interface MensagemCobranca {
  boleto_id: string;
  canal: string;
  mensagem: {
    assunto: string | null;
    corpo: string;
    tom: string;
    cta: string;
  };
  score_efetividade: number;
  variante: string;
}

export interface MelhorMomento {
  unidade_id: string;
  morador: string;
  perfil: {
    canal_preferido: string;
    responde_rapido: boolean;
    taxa_resposta: number;
  };
  sugestao: {
    canal: string;
    horario: string;
    data_sugerida: string;
    dia_semana: string;
    tom_sugerido: string;
    probabilidade_resposta: number;
    responde_rapido: boolean;
  };
}

export interface PrevisaoFluxoCaixa {
  periodo_dias: number;
  semanas: number;
  previsoes: Array<{
    data_inicio: string;
    receita_prevista: number;
    despesa_prevista: number;
    saldo_previsto: number;
    intervalo: {
      inferior: number;
      superior: number;
    };
    confianca: number;
    sazonalidade: number;
    tendencia: string;
  }>;
  resumo: {
    receita_total_prevista: number;
    despesa_total_prevista: number;
    saldo_periodo: number;
  };
}

export interface DashboardInteligente {
  periodo: string;
  resumo: {
    receita_mes: number;
    despesa_mes: number;
    saldo: number;
    inadimplencia: number;
  };
  indicadores: Array<{
    nome: string;
    valor: string;
    tendencia: string;
  }>;
  insights: Array<{
    tipo: string;
    titulo: string;
    mensagem: string;
    prioridade: string;
  }>;
  acoes_recomendadas: string[];
  saude_financeira: {
    score: number;
    classificacao: string;
  };
}

export interface Score {
  score: number;
  classificacao: string;
  probabilidade: number;
  fatores: string[];
}

class FinanceiroIAService {
  /**
   * Prevê probabilidade de inadimplência de uma unidade
   */
  async preverInadimplencia(unidadeId: string): Promise<PrevisaoInadimplencia> {
    const response = await apiClient.get(`/financeiro/ia/previsao-inadimplencia/${unidadeId}`);
    return response.data;
  }

  /**
   * Obtém alertas proativos gerados pelo sistema
   */
  async obterAlertasProativos(): Promise<{
    total_alertas: number;
    criticos: number;
    avisos: number;
    info: number;
    alertas: Alerta[];
  }> {
    const response = await apiClient.get('/financeiro/ia/alertas-proativos');
    return response.data;
  }

  /**
   * Prioriza cobranças de forma inteligente
   */
  async priorizarCobrancas(): Promise<{
    total_vencidos: number;
    valor_total: number;
    priorizados: CobrancaPriorizada[];
  }> {
    const response = await apiClient.get('/financeiro/ia/priorizar-cobranca');
    return response.data;
  }

  /**
   * Analisa sentimento de uma mensagem
   */
  async analisarSentimento(mensagem: string): Promise<AnaliseSentimento> {
    const response = await apiClient.post('/financeiro/ia/analisar-sentimento', { mensagem });
    return response.data;
  }

  /**
   * Gera mensagem de cobrança personalizada
   */
  async gerarMensagemCobranca(params: {
    boleto_id: string;
    canal?: string;
    tom?: string;
    variante?: string;
  }): Promise<MensagemCobranca> {
    const response = await apiClient.post('/financeiro/ia/gerar-mensagem-cobranca', null, { params });
    return response.data;
  }

  /**
   * Obtém melhor momento para contatar um morador
   */
  async obterMelhorMomento(unidadeId: string): Promise<MelhorMomento> {
    const response = await apiClient.get(`/financeiro/ia/melhor-momento/${unidadeId}`);
    return response.data;
  }

  /**
   * Prevê fluxo de caixa
   */
  async preverFluxoCaixa(dias: number = 90): Promise<PrevisaoFluxoCaixa> {
    const response = await apiClient.get('/financeiro/ia/previsao-fluxo-caixa', { params: { dias } });
    return response.data;
  }

  /**
   * Obtém dashboard inteligente com insights
   */
  async obterDashboardInteligente(): Promise<DashboardInteligente> {
    const response = await apiClient.get('/financeiro/ia/dashboard-inteligente');
    return response.data;
  }

  /**
   * Obtém score de inadimplência de uma unidade
   */
  async obterScore(unidadeId: string): Promise<Score> {
    const response = await apiClient.get(`/financeiro/ia/score/${unidadeId}`);
    return response.data;
  }
}

export const financeiroIAService = new FinanceiroIAService();
