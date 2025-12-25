/**
 * Conecta Plus - Componente de Priorização Inteligente de Cobranças
 */

'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { usePriorizacaoCobrancas, useGerarMensagemCobranca } from '@/hooks/useFinanceiroIA';
import {
  AlertCircle,
  TrendingUp,
  Phone,
  Mail,
  MessageCircle,
  ArrowRight,
} from 'lucide-react';
import { formatCurrency } from '@/lib/utils';
import { useState } from 'react';

export function PriorizacaoCobrancas() {
  const { data, isLoading } = usePriorizacaoCobrancas();
  const gerarMensagem = useGerarMensagemCobranca();
  const [selectedBoleto, setSelectedBoleto] = useState<string | null>(null);

  if (isLoading) {
    return <PriorizacaoSkeleton />;
  }

  if (!data || data.priorizados.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <TrendingUp className="h-12 w-12 text-green-600 mb-4" />
          <p className="text-lg font-semibold">Nenhuma cobrança pendente</p>
          <p className="text-sm text-muted-foreground">Todas as cobranças estão em dia!</p>
        </CardContent>
      </Card>
    );
  }

  const getRiscoColor = (risco: string) => {
    switch (risco) {
      case 'critico':
        return 'destructive';
      case 'alto':
        return 'default';
      case 'medio':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const getRiscoIcon = (risco: string) => {
    switch (risco) {
      case 'critico':
        return <AlertCircle className="h-4 w-4" />;
      case 'alto':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <TrendingUp className="h-4 w-4" />;
    }
  };

  const handleGerarMensagem = async (boletoId: string, canal: string) => {
    setSelectedBoleto(boletoId);
    try {
      await gerarMensagem.mutateAsync({ boleto_id: boletoId, canal });
    } finally {
      setSelectedBoleto(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card className="border-2 border-orange-200 dark:border-orange-900">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Priorização Inteligente de Cobranças</CardTitle>
              <CardDescription>
                IA ordenou {data.priorizados.length} cobrança(s) por urgência e probabilidade de sucesso
              </CardDescription>
            </div>
            <div className="text-right">
              <div className="text-sm text-muted-foreground">Total Vencido</div>
              <div className="text-2xl font-bold text-red-600">
                {formatCurrency(data.valor_total)}
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Lista Priorizada */}
      <div className="space-y-3">
        {data.priorizados.map((item) => (
          <Card
            key={item.boleto_id}
            className={`transition-all hover:shadow-lg ${
              item.posicao <= 3 ? 'border-2 border-orange-300 dark:border-orange-700' : ''
            }`}
          >
            <CardContent className="p-6">
              <div className="flex items-start justify-between gap-4">
                {/* Posição e Info Principal */}
                <div className="flex gap-4 flex-1">
                  <div className="flex flex-col items-center justify-center">
                    <div
                      className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-xl ${
                        item.posicao === 1
                          ? 'bg-red-600 text-white'
                          : item.posicao <= 3
                          ? 'bg-orange-500 text-white'
                          : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200'
                      }`}
                    >
                      {item.posicao}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">TOP {item.posicao}</div>
                  </div>

                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-lg">
                        {item.morador || 'Morador N/A'} - Apt {item.unidade}
                      </h3>
                      <Badge variant={getRiscoColor(item.classificacao_risco)} className="gap-1">
                        {getRiscoIcon(item.classificacao_risco)}
                        {item.classificacao_risco.toUpperCase()}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div>
                        <span className="text-muted-foreground">Valor:</span>
                        <div className="font-semibold">{formatCurrency(item.valor)}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Dias Atraso:</span>
                        <div className="font-semibold text-red-600">{item.dias_atraso} dias</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Score Prioridade:</span>
                        <div className="font-semibold text-orange-600">
                          {item.score_prioridade.toFixed(1)}/100
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Prob. Pagamento:</span>
                        <div className="font-semibold text-blue-600">
                          {(item.probabilidade_pagamento * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>

                    <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
                      <div className="flex items-start gap-2">
                        <TrendingUp className="h-4 w-4 text-blue-600 mt-0.5" />
                        <div className="flex-1">
                          <div className="text-xs font-semibold text-blue-900 dark:text-blue-100 mb-1">
                            Estratégia Recomendada
                          </div>
                          <div className="text-sm text-blue-800 dark:text-blue-200">
                            {item.estrategia}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Ações */}
                <div className="flex flex-col gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-2"
                    onClick={() => handleGerarMensagem(item.boleto_id, 'whatsapp')}
                    disabled={selectedBoleto === item.boleto_id}
                  >
                    <MessageCircle className="h-4 w-4" />
                    WhatsApp
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-2"
                    onClick={() => handleGerarMensagem(item.boleto_id, 'email')}
                    disabled={selectedBoleto === item.boleto_id}
                  >
                    <Mail className="h-4 w-4" />
                    Email
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-2"
                  >
                    <Phone className="h-4 w-4" />
                    Ligar
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function PriorizacaoSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-32" />
      {[...Array(3)].map((_, i) => (
        <Skeleton key={i} className="h-48" />
      ))}
    </div>
  );
}
