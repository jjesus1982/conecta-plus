"""
Conecta Plus - Serviço de Conciliação Bancária Automática
Algoritmo inteligente para matching de transações Cora com boletos/pagamentos
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
import logging
from sqlalchemy.orm import Session
from uuid import UUID

from repositories.cora import (
    TransacaoCoraRepository,
    CobrancaCoraRepository
)
from repositories.boleto import BoletoRepository
from repositories.pagamento import PagamentoRepository
from models.cora import TipoTransacaoCora

logger = logging.getLogger("conciliacao_service")


class ConfiancaMatch:
    """Níveis de confiança para matching"""
    MUITO_ALTA = 0.95  # Auto-concilia
    ALTA = 0.85
    MEDIA = 0.70
    BAIXA = 0.50
    MUITO_BAIXA = 0.30


class ResultadoConciliacao:
    """Resultado de uma tentativa de conciliação"""

    def __init__(
        self,
        transacao_id: UUID,
        sucesso: bool,
        metodo: str,
        confianca: float = 0.0,
        boleto_id: Optional[UUID] = None,
        pagamento_id: Optional[UUID] = None,
        motivo: Optional[str] = None
    ):
        self.transacao_id = transacao_id
        self.sucesso = sucesso
        self.metodo = metodo
        self.confianca = confianca
        self.boleto_id = boleto_id
        self.pagamento_id = pagamento_id
        self.motivo = motivo

    def to_dict(self) -> Dict:
        return {
            "transacao_id": str(self.transacao_id),
            "sucesso": self.sucesso,
            "metodo": self.metodo,
            "confianca": self.confianca,
            "boleto_id": str(self.boleto_id) if self.boleto_id else None,
            "pagamento_id": str(self.pagamento_id) if self.pagamento_id else None,
            "motivo": self.motivo
        }


class ConciliacaoService:
    """
    Serviço de conciliação bancária automática

    Implementa algoritmos inteligentes para matching:
    1. PIX: end_to_end_id exato (100% confiança)
    2. PIX: txid exato (100% confiança)
    3. Valor exato + data ±3 dias + documento (95% confiança)
    4. Valor exato + data ±7 dias (70% confiança)
    5. Valor aproximado ±1% + data ±3 dias (60% confiança)
    """

    def __init__(self, db: Session):
        self.db = db
        self.transacao_repo = TransacaoCoraRepository(db)
        self.cobranca_repo = CobrancaCoraRepository(db)
        self.boleto_repo = BoletoRepository(db)
        self.pagamento_repo = PagamentoRepository(db)

    def executar_conciliacao_automatica(
        self,
        condominio_id: str,
        auto_conciliar: bool = True,
        min_confianca: float = ConfiancaMatch.MUITO_ALTA
    ) -> Dict[str, Any]:
        """
        Executa conciliação automática para todas as transações pendentes

        Args:
            condominio_id: ID do condomínio
            auto_conciliar: Se True, concilia automaticamente matches com alta confiança
            min_confianca: Confiança mínima para auto-conciliar (padrão: 0.95)

        Returns:
            Resumo da execução com estatísticas
        """
        logger.info(f"Iniciando conciliação automática para condomínio {condominio_id}")

        # Busca transações não conciliadas (apenas CRÉDITO)
        transacoes_pendentes = self.transacao_repo.get_nao_conciliadas(
            condominio_id=condominio_id,
            tipo=TipoTransacaoCora.CREDITO
        )

        logger.info(f"Encontradas {len(transacoes_pendentes)} transações pendentes")

        # Estatísticas
        stats = {
            "total_analisadas": len(transacoes_pendentes),
            "conciliadas_automaticamente": 0,
            "marcadas_para_revisao": 0,
            "sem_match": 0,
            "erros": 0,
            "detalhes": []
        }

        # Processa cada transação
        for transacao in transacoes_pendentes:
            try:
                resultado = self._processar_transacao(
                    transacao=transacao,
                    condominio_id=condominio_id,
                    auto_conciliar=auto_conciliar,
                    min_confianca=min_confianca
                )

                stats["detalhes"].append(resultado.to_dict())

                if resultado.sucesso:
                    stats["conciliadas_automaticamente"] += 1
                elif resultado.confianca >= ConfiancaMatch.MEDIA:
                    stats["marcadas_para_revisao"] += 1
                else:
                    stats["sem_match"] += 1

            except Exception as e:
                logger.error(f"Erro ao processar transação {transacao.id}: {str(e)}")
                stats["erros"] += 1
                stats["detalhes"].append({
                    "transacao_id": str(transacao.id),
                    "sucesso": False,
                    "motivo": f"Erro: {str(e)}"
                })

        logger.info(
            f"Conciliação concluída: {stats['conciliadas_automaticamente']} "
            f"conciliadas, {stats['marcadas_para_revisao']} para revisão, "
            f"{stats['sem_match']} sem match, {stats['erros']} erros"
        )

        return stats

    def _processar_transacao(
        self,
        transacao: Any,
        condominio_id: str,
        auto_conciliar: bool,
        min_confianca: float
    ) -> ResultadoConciliacao:
        """
        Processa uma transação tentando encontrar match

        Returns:
            ResultadoConciliacao com resultado do processamento
        """
        logger.debug(f"Processando transação {transacao.id} (R$ {transacao.valor})")

        # Estratégia 1: PIX end_to_end_id exato
        if transacao.end_to_end_id:
            resultado = self._match_por_end_to_end_id(transacao, condominio_id)
            if resultado and resultado.confianca >= min_confianca and auto_conciliar:
                self._conciliar(transacao, resultado.boleto_id, resultado.confianca)
                return resultado
            elif resultado:
                return resultado

        # Estratégia 2: PIX txid exato
        if transacao.pix_txid:
            resultado = self._match_por_pix_txid(transacao, condominio_id)
            if resultado and resultado.confianca >= min_confianca and auto_conciliar:
                self._conciliar(transacao, resultado.boleto_id, resultado.confianca)
                return resultado
            elif resultado:
                return resultado

        # Estratégia 3: Valor exato + data ±3 dias + documento
        resultado = self._match_por_valor_data_documento(
            transacao, condominio_id, dias_tolerancia=3
        )
        if resultado and resultado.confianca >= min_confianca and auto_conciliar:
            self._conciliar(transacao, resultado.boleto_id, resultado.confianca)
            return resultado
        elif resultado and resultado.confianca >= ConfiancaMatch.ALTA:
            return resultado

        # Estratégia 4: Valor exato + data ±7 dias
        resultado = self._match_por_valor_data(
            transacao, condominio_id, dias_tolerancia=7
        )
        if resultado and resultado.confianca >= min_confianca and auto_conciliar:
            self._conciliar(transacao, resultado.boleto_id, resultado.confianca)
            return resultado
        elif resultado:
            return resultado

        # Estratégia 5: Valor aproximado ±1% + data ±3 dias
        resultado = self._match_por_valor_aproximado(
            transacao, condominio_id, tolerancia_percentual=0.01, dias_tolerancia=3
        )
        if resultado and resultado.confianca >= min_confianca and auto_conciliar:
            self._conciliar(transacao, resultado.boleto_id, resultado.confianca)
            return resultado
        elif resultado:
            return resultado

        # Nenhum match encontrado
        return ResultadoConciliacao(
            transacao_id=transacao.id,
            sucesso=False,
            metodo="nenhum",
            motivo="Nenhum match encontrado com confiança suficiente"
        )

    def _match_por_end_to_end_id(
        self,
        transacao: Any,
        condominio_id: str
    ) -> Optional[ResultadoConciliacao]:
        """
        Match por end_to_end_id exato (PIX)
        Confiança: 100%
        """
        logger.debug(f"Tentando match por end_to_end_id: {transacao.end_to_end_id}")

        # Busca cobrança Cora com esse end_to_end_id
        # (quando PIX é pago, Cora envia end_to_end_id no webhook)
        cobranca = self.cobranca_repo.get_by_pix_txid(transacao.end_to_end_id)

        if cobranca and cobranca.boleto_id:
            logger.info(
                f"Match EXATO por end_to_end_id: transação {transacao.id} "
                f"→ boleto {cobranca.boleto_id}"
            )

            return ResultadoConciliacao(
                transacao_id=transacao.id,
                sucesso=True,
                metodo="end_to_end_id_exato",
                confianca=1.0,
                boleto_id=cobranca.boleto_id,
                motivo="Match exato por end_to_end_id do PIX"
            )

        return None

    def _match_por_pix_txid(
        self,
        transacao: Any,
        condominio_id: str
    ) -> Optional[ResultadoConciliacao]:
        """
        Match por txid do PIX
        Confiança: 100%
        """
        logger.debug(f"Tentando match por pix_txid: {transacao.pix_txid}")

        cobranca = self.cobranca_repo.get_by_pix_txid(transacao.pix_txid)

        if cobranca and cobranca.boleto_id:
            logger.info(
                f"Match EXATO por pix_txid: transação {transacao.id} "
                f"→ boleto {cobranca.boleto_id}"
            )

            return ResultadoConciliacao(
                transacao_id=transacao.id,
                sucesso=True,
                metodo="pix_txid_exato",
                confianca=1.0,
                boleto_id=cobranca.boleto_id,
                motivo="Match exato por txid do PIX"
            )

        return None

    def _match_por_valor_data_documento(
        self,
        transacao: Any,
        condominio_id: str,
        dias_tolerancia: int = 3
    ) -> Optional[ResultadoConciliacao]:
        """
        Match por valor exato + data ±N dias + documento
        Confiança: 95%
        """
        logger.debug(
            f"Tentando match por valor+data+documento: R$ {transacao.valor}, "
            f"data {transacao.data_transacao}"
        )

        # Calcula janela de datas
        data_min = transacao.data_transacao - timedelta(days=dias_tolerancia)
        data_max = transacao.data_transacao + timedelta(days=dias_tolerancia)

        # Busca boletos com valor exato e vencimento na janela
        boletos_candidatos = self.boleto_repo.buscar_por_valor_e_data(
            condominio_id=condominio_id,
            valor=transacao.valor,
            data_min=data_min,
            data_max=data_max,
            status="pendente"  # Apenas boletos não pagos
        )

        # Filtra por documento se disponível
        if transacao.contrapartida_documento:
            boletos_candidatos = [
                b for b in boletos_candidatos
                if self._documentos_match(
                    b.unidade.morador_documento,
                    transacao.contrapartida_documento
                )
            ]

        # Se encontrou exatamente 1 match: alta confiança
        if len(boletos_candidatos) == 1:
            boleto = boletos_candidatos[0]
            logger.info(
                f"Match por valor+data+documento: transação {transacao.id} "
                f"→ boleto {boleto.id}"
            )

            return ResultadoConciliacao(
                transacao_id=transacao.id,
                sucesso=True,
                metodo="valor_data_documento",
                confianca=ConfiancaMatch.MUITO_ALTA,
                boleto_id=boleto.id,
                motivo=f"Match único por valor exato, data ±{dias_tolerancia} dias e documento"
            )

        # Se encontrou múltiplos: confiança média (requer revisão manual)
        elif len(boletos_candidatos) > 1:
            logger.warning(
                f"Múltiplos matches para transação {transacao.id}: "
                f"{len(boletos_candidatos)} boletos candidatos"
            )

            return ResultadoConciliacao(
                transacao_id=transacao.id,
                sucesso=False,
                metodo="valor_data_documento",
                confianca=ConfiancaMatch.MEDIA,
                motivo=f"Múltiplos matches ({len(boletos_candidatos)}) - revisão manual necessária"
            )

        return None

    def _match_por_valor_data(
        self,
        transacao: Any,
        condominio_id: str,
        dias_tolerancia: int = 7
    ) -> Optional[ResultadoConciliacao]:
        """
        Match por valor exato + data ±N dias (sem documento)
        Confiança: 70%
        """
        logger.debug(f"Tentando match por valor+data: R$ {transacao.valor}")

        data_min = transacao.data_transacao - timedelta(days=dias_tolerancia)
        data_max = transacao.data_transacao + timedelta(days=dias_tolerancia)

        boletos_candidatos = self.boleto_repo.buscar_por_valor_e_data(
            condominio_id=condominio_id,
            valor=transacao.valor,
            data_min=data_min,
            data_max=data_max,
            status="pendente"
        )

        if len(boletos_candidatos) == 1:
            boleto = boletos_candidatos[0]
            logger.info(
                f"Match por valor+data: transação {transacao.id} → boleto {boleto.id}"
            )

            return ResultadoConciliacao(
                transacao_id=transacao.id,
                sucesso=True,
                metodo="valor_data",
                confianca=ConfiancaMatch.ALTA,
                boleto_id=boleto.id,
                motivo=f"Match único por valor exato e data ±{dias_tolerancia} dias"
            )

        elif len(boletos_candidatos) > 1:
            return ResultadoConciliacao(
                transacao_id=transacao.id,
                sucesso=False,
                metodo="valor_data",
                confianca=ConfiancaMatch.BAIXA,
                motivo=f"Múltiplos matches ({len(boletos_candidatos)}) - baixa confiança"
            )

        return None

    def _match_por_valor_aproximado(
        self,
        transacao: Any,
        condominio_id: str,
        tolerancia_percentual: float = 0.01,
        dias_tolerancia: int = 3
    ) -> Optional[ResultadoConciliacao]:
        """
        Match por valor aproximado ±X% + data ±N dias
        Confiança: 60%

        Útil para casos com juros/multa pequenos
        """
        logger.debug(
            f"Tentando match por valor aproximado: R$ {transacao.valor} "
            f"±{tolerancia_percentual*100}%"
        )

        valor_min = transacao.valor * Decimal(str(1 - tolerancia_percentual))
        valor_max = transacao.valor * Decimal(str(1 + tolerancia_percentual))

        data_min = transacao.data_transacao - timedelta(days=dias_tolerancia)
        data_max = transacao.data_transacao + timedelta(days=dias_tolerancia)

        boletos_candidatos = self.boleto_repo.buscar_por_range_valor_e_data(
            condominio_id=condominio_id,
            valor_min=valor_min,
            valor_max=valor_max,
            data_min=data_min,
            data_max=data_max,
            status="pendente"
        )

        if len(boletos_candidatos) == 1:
            boleto = boletos_candidatos[0]
            logger.info(
                f"Match por valor aproximado: transação {transacao.id} "
                f"→ boleto {boleto.id}"
            )

            return ResultadoConciliacao(
                transacao_id=transacao.id,
                sucesso=True,
                metodo="valor_aproximado",
                confianca=ConfiancaMatch.MEDIA,
                boleto_id=boleto.id,
                motivo=(
                    f"Match único por valor aproximado "
                    f"±{tolerancia_percentual*100}% e data ±{dias_tolerancia} dias"
                )
            )

        return None

    def _documentos_match(self, doc1: Optional[str], doc2: Optional[str]) -> bool:
        """
        Verifica se dois documentos (CPF/CNPJ) são iguais
        Remove pontuação e compara apenas números
        """
        if not doc1 or not doc2:
            return False

        # Remove tudo que não é número
        doc1_num = ''.join(c for c in str(doc1) if c.isdigit())
        doc2_num = ''.join(c for c in str(doc2) if c.isdigit())

        return doc1_num == doc2_num

    def _conciliar(
        self,
        transacao: Any,
        boleto_id: UUID,
        confianca: float
    ):
        """
        Marca transação como conciliada
        """
        logger.info(
            f"Conciliando automaticamente: transação {transacao.id} "
            f"→ boleto {boleto_id} (confiança: {confianca:.2%})"
        )

        self.transacao_repo.conciliar(
            transacao_id=transacao.id,
            boleto_id=boleto_id,
            confianca_match=confianca,
            manual=False
        )

        # TODO: Criar pagamento vinculado ao boleto
        # TODO: Atualizar status do boleto para "pago"
        # TODO: Registrar auditoria

    def sugerir_matches(
        self,
        transacao_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Retorna sugestões de matches para uma transação específica
        Útil para conciliação manual (UI)

        Returns:
            Lista de sugestões ordenadas por confiança
        """
        transacao = self.transacao_repo.get_by_id(transacao_id)

        if not transacao:
            return []

        # Busca todos os possíveis matches
        sugestoes = []

        # Tenta cada estratégia
        estrategias = [
            ("end_to_end_id", lambda: self._match_por_end_to_end_id(
                transacao, transacao.condominio_id
            )),
            ("pix_txid", lambda: self._match_por_pix_txid(
                transacao, transacao.condominio_id
            )),
            ("valor_data_documento", lambda: self._match_por_valor_data_documento(
                transacao, transacao.condominio_id, dias_tolerancia=3
            )),
            ("valor_data_7dias", lambda: self._match_por_valor_data(
                transacao, transacao.condominio_id, dias_tolerancia=7
            )),
            ("valor_aproximado", lambda: self._match_por_valor_aproximado(
                transacao, transacao.condominio_id
            ))
        ]

        for nome, estrategia_fn in estrategias:
            try:
                resultado = estrategia_fn()
                if resultado and resultado.boleto_id:
                    # Busca detalhes do boleto
                    boleto = self.boleto_repo.get_by_id(resultado.boleto_id)

                    sugestoes.append({
                        "boleto_id": str(resultado.boleto_id),
                        "confianca": resultado.confianca,
                        "metodo": resultado.metodo,
                        "motivo": resultado.motivo,
                        "boleto": {
                            "valor": float(boleto.valor),
                            "vencimento": boleto.vencimento.isoformat(),
                            "unidade": boleto.unidade.codigo if boleto.unidade else None,
                            "morador": boleto.unidade.morador_nome if boleto.unidade else None
                        }
                    })
            except Exception as e:
                logger.error(f"Erro ao executar estratégia {nome}: {str(e)}")

        # Ordena por confiança (maior primeiro)
        sugestoes.sort(key=lambda x: x["confianca"], reverse=True)

        return sugestoes


# Singleton
_conciliacao_service_instance = None


def get_conciliacao_service(db: Session) -> ConciliacaoService:
    """Obtém instância do serviço de conciliação"""
    global _conciliacao_service_instance

    if _conciliacao_service_instance is None:
        _conciliacao_service_instance = ConciliacaoService(db)

    return _conciliacao_service_instance
