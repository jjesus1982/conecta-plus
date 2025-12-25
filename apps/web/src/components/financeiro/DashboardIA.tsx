/**
 * Conecta Plus - Dashboard Inteligente de IA Financeira
 */

'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { useDashboardInteligente, useAlertasProativos } from '@/hooks/useFinanceiroIA';
import {
  Brain,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Lightbulb,
  Activity,
  DollarSign,
  AlertCircle,
  Info,
} from 'lucide-react';
import { formatCurrency } from '@/lib/utils';

export function DashboardIA() {
  const { data: dashboard, isLoading: dashboardLoading } = useDashboardInteligente();
  const { data: alertas, isLoading: alertasLoading } = useAlertasProativos();

  if (dashboardLoading || alertasLoading) {
    return <DashboardSkeleton />;
  }

  if (!dashboard || !alertas) {
    return null;
  }

  const getSaudeColor = (score: number) => {
    if (score >= 85) return 'text-green-600';
    if (score >= 70) return 'text-blue-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getSaudeVariant = (classificacao: string) => {
    if (classificacao === 'excelente') return 'default';
    if (classificacao === 'boa') return 'secondary';
    if (classificacao === 'regular') return 'outline';
    return 'destructive';
  };

  const getSeverityIcon = (severidade: string) => {
    switch (severidade) {
      case 'critical':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      default:
        return <Info className="h-4 w-4 text-blue-600" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header com Score de Saúde */}
      <Card className="border-2">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
                <Brain className="h-6 w-6 text-white" />
              </div>
              <div>
                <CardTitle>Saúde Financeira IA</CardTitle>
                <CardDescription>Análise inteligente em tempo real</CardDescription>
              </div>
            </div>
            <div className="text-right">
              <div className={`text-4xl font-bold ${getSaudeColor(dashboard.saude_financeira.score)}`}>
                {dashboard.saude_financeira.score}
              </div>
              <Badge variant={getSaudeVariant(dashboard.saude_financeira.classificacao)}>
                {dashboard.saude_financeira.classificacao.toUpperCase()}
              </Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Resumo Financeiro */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Receita</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {formatCurrency(dashboard.resumo.receita_mes)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Despesa</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {formatCurrency(dashboard.resumo.despesa_mes)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Saldo</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {formatCurrency(dashboard.resumo.saldo)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Inadimplência</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {dashboard.resumo.inadimplencia.toFixed(1)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Indicadores com Tendências */}
      {dashboard.indicadores && dashboard.indicadores.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Indicadores Chave
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {dashboard.indicadores.map((indicador, index) => (
                <div key={index} className="flex items-center justify-between p-4 rounded-lg border">
                  <div>
                    <p className="text-sm text-muted-foreground">{indicador.nome}</p>
                    <p className="text-2xl font-bold">{indicador.valor}</p>
                  </div>
                  <div>
                    {indicador.tendencia === 'up' ? (
                      <TrendingUp className="h-6 w-6 text-green-600" />
                    ) : (
                      <TrendingDown className="h-6 w-6 text-red-600" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Alertas Críticos */}
      {alertas.alertas && alertas.alertas.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Alertas do Sistema
              <Badge variant="outline" className="ml-2">
                {alertas.total_alertas} total
              </Badge>
              {alertas.criticos > 0 && (
                <Badge variant="destructive">{alertas.criticos} críticos</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {alertas.alertas.slice(0, 5).map((alerta, index) => (
              <Alert key={index} variant={alerta.severidade === 'critical' ? 'destructive' : 'default'}>
                <div className="flex items-start gap-3">
                  {getSeverityIcon(alerta.severidade)}
                  <div className="flex-1">
                    <AlertTitle>{alerta.titulo}</AlertTitle>
                    <AlertDescription>
                      {alerta.mensagem}
                      <div className="mt-2 text-xs">
                        <strong>Ação:</strong> {alerta.acao_recomendada}
                      </div>
                    </AlertDescription>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {(alerta.probabilidade * 100).toFixed(0)}%
                  </Badge>
                </div>
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Insights IA */}
      {dashboard.insights && dashboard.insights.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-yellow-500" />
              Insights IA
            </CardTitle>
            <CardDescription>Descobertas automáticas e recomendações</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboard.insights.map((insight, index) => (
              <div
                key={index}
                className="p-4 rounded-lg border bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950"
              >
                <div className="flex items-start gap-3">
                  <Lightbulb className="h-5 w-5 text-yellow-500 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="font-semibold">{insight.titulo}</h4>
                    <p className="text-sm text-muted-foreground mt-1">{insight.mensagem}</p>
                    <Badge variant="outline" className="mt-2">
                      {insight.prioridade}
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Ações Recomendadas */}
      {dashboard.acoes_recomendadas && dashboard.acoes_recomendadas.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Ações Recomendadas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {dashboard.acoes_recomendadas.map((acao, index) => (
                <li key={index} className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-blue-600" />
                  <span>{acao}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-32 w-full" />
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
}
