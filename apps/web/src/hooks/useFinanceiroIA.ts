/**
 * Conecta Plus - React Hooks para IA Financeira
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { financeiroIAService } from '@/services/financeiro-ia.service';
import { toast } from 'sonner';

/**
 * Hook para previsão de inadimplência
 */
export function usePrevisaoInadimplencia(unidadeId: string) {
  return useQuery({
    queryKey: ['previsao-inadimplencia', unidadeId],
    queryFn: () => financeiroIAService.preverInadimplencia(unidadeId),
    enabled: !!unidadeId,
    staleTime: 5 * 60 * 1000, // 5 minutos
  });
}

/**
 * Hook para alertas proativos
 */
export function useAlertasProativos() {
  return useQuery({
    queryKey: ['alertas-proativos'],
    queryFn: () => financeiroIAService.obterAlertasProativos(),
    refetchInterval: 30 * 1000, // Atualiza a cada 30s
  });
}

/**
 * Hook para priorização de cobranças
 */
export function usePriorizacaoCobrancas() {
  return useQuery({
    queryKey: ['priorizacao-cobrancas'],
    queryFn: () => financeiroIAService.priorizarCobrancas(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook para análise de sentimento
 */
export function useAnaliseSentimento() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mensagem: string) => financeiroIAService.analisarSentimento(mensagem),
    onSuccess: (data) => {
      if (data.analise.requer_atencao) {
        toast.warning('Atenção Especial Requerida', {
          description: data.sugestao_resposta,
        });
      }
    },
  });
}

/**
 * Hook para gerar mensagem de cobrança
 */
export function useGerarMensagemCobranca() {
  return useMutation({
    mutationFn: (params: {
      boleto_id: string;
      canal?: string;
      tom?: string;
      variante?: string;
    }) => financeiroIAService.gerarMensagemCobranca(params),
    onSuccess: () => {
      toast.success('Mensagem gerada com sucesso');
    },
  });
}

/**
 * Hook para melhor momento de contato
 */
export function useMelhorMomento(unidadeId: string) {
  return useQuery({
    queryKey: ['melhor-momento', unidadeId],
    queryFn: () => financeiroIAService.obterMelhorMomento(unidadeId),
    enabled: !!unidadeId,
    staleTime: 10 * 60 * 1000,
  });
}

/**
 * Hook para previsão de fluxo de caixa
 */
export function usePrevisaoFluxoCaixa(dias: number = 90) {
  return useQuery({
    queryKey: ['previsao-fluxo-caixa', dias],
    queryFn: () => financeiroIAService.preverFluxoCaixa(dias),
    staleTime: 15 * 60 * 1000,
  });
}

/**
 * Hook para dashboard inteligente
 */
export function useDashboardInteligente() {
  return useQuery({
    queryKey: ['dashboard-inteligente'],
    queryFn: () => financeiroIAService.obterDashboardInteligente(),
    refetchInterval: 60 * 1000, // Atualiza a cada 1min
  });
}

/**
 * Hook para score de inadimplência
 */
export function useScore(unidadeId: string) {
  return useQuery({
    queryKey: ['score', unidadeId],
    queryFn: () => financeiroIAService.obterScore(unidadeId),
    enabled: !!unidadeId,
    staleTime: 10 * 60 * 1000,
  });
}

/**
 * Hook agregado - todas as métricas de IA
 */
export function useFinanceiroIAMetrics() {
  const alertas = useAlertasProativos();
  const priorizacao = usePriorizacaoCobrancas();
  const dashboard = useDashboardInteligente();

  return {
    alertas: alertas.data,
    priorizacao: priorizacao.data,
    dashboard: dashboard.data,
    isLoading: alertas.isLoading || priorizacao.isLoading || dashboard.isLoading,
    isError: alertas.isError || priorizacao.isError || dashboard.isError,
  };
}
