"""
Conecta Plus - Serviço de Auditoria
Sistema de Audit Trail para conformidade LGPD/SOX
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import asyncio
import uuid

from fastapi import Request


class TipoAcaoAuditoria(str, Enum):
    """Tipos de ação para auditoria"""
    # CRUD
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Financeiro específico
    BOLETO_CRIADO = "boleto_criado"
    BOLETO_PAGO = "boleto_pago"
    BOLETO_CANCELADO = "boleto_cancelado"
    BOLETO_EXPORTADO = "boleto_exportado"

    PAGAMENTO_REGISTRADO = "pagamento_registrado"
    PAGAMENTO_ESTORNADO = "pagamento_estornado"

    COBRANCA_ENVIADA = "cobranca_enviada"
    ACORDO_CRIADO = "acordo_criado"
    ACORDO_ACEITO = "acordo_aceito"
    ACORDO_QUEBRADO = "acordo_quebrado"

    # Relatórios
    RELATORIO_GERADO = "relatorio_gerado"
    DADOS_EXPORTADOS = "dados_exportados"

    # Acesso
    ACESSO_DADOS_SENSIVEIS = "acesso_dados_sensiveis"
    TENTATIVA_ACESSO_NEGADA = "tentativa_acesso_negada"

    # Configuração
    CONFIG_ALTERADA = "config_alterada"


@dataclass
class EntradaAuditoria:
    """Estrutura de uma entrada de auditoria"""
    id: str
    timestamp: str
    usuario_id: str
    usuario_email: str
    usuario_nome: Optional[str]
    usuario_ip: Optional[str]
    usuario_user_agent: Optional[str]

    acao: str
    descricao: str

    entidade_tipo: str
    entidade_id: str

    dados_anteriores: Optional[Dict[str, Any]]
    dados_novos: Optional[Dict[str, Any]]

    request_id: Optional[str]
    endpoint: Optional[str]
    metodo_http: Optional[str]

    condominio_id: Optional[str]

    # Hash para integridade
    hash_integridade: str


class AuditService:
    """
    Serviço de Auditoria

    Registra todas as operações financeiras para:
    - Conformidade LGPD
    - Conformidade SOX
    - Rastreabilidade
    - Segurança
    """

    def __init__(self, repository=None):
        """
        Args:
            repository: Repositório de audit logs (opcional)
        """
        self.repository = repository
        self._buffer: List[EntradaAuditoria] = []
        self._buffer_size = int(os.getenv('AUDIT_BUFFER_SIZE', '100'))

    def _gerar_hash(self, dados: Dict[str, Any]) -> str:
        """Gera hash de integridade para a entrada"""
        # Remove campos que mudam (timestamp, id)
        dados_para_hash = {k: v for k, v in dados.items()
                         if k not in ['id', 'timestamp', 'hash_integridade']}

        # Serializa de forma determinística
        dados_str = json.dumps(dados_para_hash, sort_keys=True, default=str)

        # Hash SHA-256
        return hashlib.sha256(dados_str.encode()).hexdigest()

    def _extrair_info_request(self, request: Optional[Request]) -> Dict[str, Any]:
        """Extrai informações da requisição"""
        if not request:
            return {}

        # IP do cliente
        ip = request.client.host if request.client else None

        # Tenta pegar IP real se estiver atrás de proxy
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            ip = forwarded_for.split(',')[0].strip()

        return {
            'ip': ip,
            'user_agent': request.headers.get('User-Agent', '')[:500],
            'request_id': request.headers.get('X-Request-ID', str(uuid.uuid4())),
            'endpoint': str(request.url.path),
            'method': request.method
        }

    def _sanitizar_dados(self, dados: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Remove dados sensíveis do log"""
        if not dados:
            return None

        # Campos sensíveis que devem ser mascarados
        campos_sensiveis = [
            'senha', 'password', 'token', 'api_key', 'secret',
            'cpf', 'cnpj', 'documento', 'cartao', 'cvv',
            'conta', 'agencia', 'chave_pix'
        ]

        dados_sanitizados = {}
        for chave, valor in dados.items():
            chave_lower = chave.lower()

            # Verifica se é campo sensível
            is_sensivel = any(s in chave_lower for s in campos_sensiveis)

            if is_sensivel and valor:
                if isinstance(valor, str):
                    # Mascara mantendo alguns caracteres
                    if len(valor) > 4:
                        dados_sanitizados[chave] = f"{valor[:2]}***{valor[-2:]}"
                    else:
                        dados_sanitizados[chave] = "***"
                else:
                    dados_sanitizados[chave] = "[REDACTED]"
            else:
                dados_sanitizados[chave] = valor

        return dados_sanitizados

    async def registrar(
        self,
        usuario_id: str,
        usuario_email: str,
        acao: TipoAcaoAuditoria,
        entidade_tipo: str,
        entidade_id: str,
        descricao: str,
        dados_anteriores: Optional[Dict[str, Any]] = None,
        dados_novos: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        condominio_id: Optional[str] = None,
        usuario_nome: Optional[str] = None
    ) -> EntradaAuditoria:
        """
        Registra uma entrada de auditoria

        Args:
            usuario_id: ID do usuário que realizou a ação
            usuario_email: Email do usuário
            acao: Tipo de ação
            entidade_tipo: Tipo da entidade (boleto, pagamento, etc)
            entidade_id: ID da entidade
            descricao: Descrição da ação
            dados_anteriores: Estado anterior (para updates)
            dados_novos: Novo estado
            request: Request HTTP (opcional)
            condominio_id: ID do condomínio
            usuario_nome: Nome do usuário

        Returns:
            EntradaAuditoria criada
        """
        # Extrai info da request
        request_info = self._extrair_info_request(request)

        # Sanitiza dados sensíveis
        dados_anteriores_safe = self._sanitizar_dados(dados_anteriores)
        dados_novos_safe = self._sanitizar_dados(dados_novos)

        # Monta entrada
        entrada_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'

        entrada_dict = {
            'id': entrada_id,
            'timestamp': timestamp,
            'usuario_id': usuario_id,
            'usuario_email': usuario_email,
            'usuario_nome': usuario_nome,
            'usuario_ip': request_info.get('ip'),
            'usuario_user_agent': request_info.get('user_agent'),
            'acao': acao.value,
            'descricao': descricao,
            'entidade_tipo': entidade_tipo,
            'entidade_id': str(entidade_id),
            'dados_anteriores': dados_anteriores_safe,
            'dados_novos': dados_novos_safe,
            'request_id': request_info.get('request_id'),
            'endpoint': request_info.get('endpoint'),
            'metodo_http': request_info.get('method'),
            'condominio_id': condominio_id,
            'hash_integridade': ''
        }

        # Gera hash de integridade
        entrada_dict['hash_integridade'] = self._gerar_hash(entrada_dict)

        entrada = EntradaAuditoria(**entrada_dict)

        # Salva no repositório se disponível
        if self.repository:
            try:
                from repositories.financeiro import get_session, AuditLogRepository
                from models.financeiro import TipoAuditoria as TipoAuditoriaDB

                # Mapeia ação para o enum do banco
                acao_db_map = {
                    'create': TipoAuditoriaDB.CREATE,
                    'read': TipoAuditoriaDB.ACCESS,
                    'update': TipoAuditoriaDB.UPDATE,
                    'delete': TipoAuditoriaDB.DELETE,
                }
                acao_db = acao_db_map.get(acao.value.split('_')[0], TipoAuditoriaDB.ACCESS)

                async with get_session() as session:
                    await AuditLogRepository.registrar(
                        session=session,
                        usuario_id=usuario_id,
                        usuario_email=usuario_email,
                        acao=acao_db,
                        entidade_tipo=entidade_tipo,
                        entidade_id=str(entidade_id),
                        descricao=descricao,
                        dados_anteriores=dados_anteriores_safe,
                        dados_novos=dados_novos_safe,
                        request_info=request_info
                    )
            except Exception as e:
                # Log error but don't fail the operation
                print(f"[AUDIT] Erro ao salvar no banco: {e}")

        # Adiciona ao buffer
        self._buffer.append(entrada)

        # Flush se buffer cheio
        if len(self._buffer) >= self._buffer_size:
            await self._flush_buffer()

        return entrada

    async def _flush_buffer(self):
        """Persiste buffer de logs"""
        if not self._buffer:
            return

        # Em produção, enviaria para:
        # - Elasticsearch
        # - CloudWatch Logs
        # - Splunk
        # - etc.

        # Por agora, apenas limpa o buffer
        self._buffer = []

    async def registrar_acesso_boleto(
        self,
        usuario_id: str,
        usuario_email: str,
        boleto_id: str,
        condominio_id: str,
        request: Optional[Request] = None
    ) -> EntradaAuditoria:
        """Atalho para registrar acesso a boleto"""
        return await self.registrar(
            usuario_id=usuario_id,
            usuario_email=usuario_email,
            acao=TipoAcaoAuditoria.READ,
            entidade_tipo='boleto',
            entidade_id=boleto_id,
            descricao=f"Acesso aos dados do boleto {boleto_id}",
            request=request,
            condominio_id=condominio_id
        )

    async def registrar_criacao_boleto(
        self,
        usuario_id: str,
        usuario_email: str,
        boleto_id: str,
        dados_boleto: Dict[str, Any],
        condominio_id: str,
        request: Optional[Request] = None
    ) -> EntradaAuditoria:
        """Atalho para registrar criação de boleto"""
        return await self.registrar(
            usuario_id=usuario_id,
            usuario_email=usuario_email,
            acao=TipoAcaoAuditoria.BOLETO_CRIADO,
            entidade_tipo='boleto',
            entidade_id=boleto_id,
            descricao=f"Boleto criado: {dados_boleto.get('competencia')} - R$ {dados_boleto.get('valor')}",
            dados_novos=dados_boleto,
            request=request,
            condominio_id=condominio_id
        )

    async def registrar_pagamento(
        self,
        usuario_id: str,
        usuario_email: str,
        pagamento_id: str,
        boleto_id: str,
        valor: float,
        condominio_id: str,
        request: Optional[Request] = None
    ) -> EntradaAuditoria:
        """Atalho para registrar pagamento"""
        return await self.registrar(
            usuario_id=usuario_id,
            usuario_email=usuario_email,
            acao=TipoAcaoAuditoria.PAGAMENTO_REGISTRADO,
            entidade_tipo='pagamento',
            entidade_id=pagamento_id,
            descricao=f"Pagamento de R$ {valor:.2f} registrado para boleto {boleto_id}",
            dados_novos={'boleto_id': boleto_id, 'valor': valor},
            request=request,
            condominio_id=condominio_id
        )

    async def registrar_cobranca(
        self,
        usuario_id: str,
        usuario_email: str,
        boleto_id: str,
        canal: str,
        condominio_id: str,
        request: Optional[Request] = None
    ) -> EntradaAuditoria:
        """Atalho para registrar envio de cobrança"""
        return await self.registrar(
            usuario_id=usuario_id,
            usuario_email=usuario_email,
            acao=TipoAcaoAuditoria.COBRANCA_ENVIADA,
            entidade_tipo='cobranca',
            entidade_id=boleto_id,
            descricao=f"Cobrança enviada via {canal} para boleto {boleto_id}",
            dados_novos={'canal': canal, 'boleto_id': boleto_id},
            request=request,
            condominio_id=condominio_id
        )

    async def registrar_exportacao(
        self,
        usuario_id: str,
        usuario_email: str,
        tipo_exportacao: str,
        quantidade_registros: int,
        condominio_id: str,
        request: Optional[Request] = None
    ) -> EntradaAuditoria:
        """Atalho para registrar exportação de dados"""
        return await self.registrar(
            usuario_id=usuario_id,
            usuario_email=usuario_email,
            acao=TipoAcaoAuditoria.DADOS_EXPORTADOS,
            entidade_tipo='exportacao',
            entidade_id=str(uuid.uuid4()),
            descricao=f"Exportação de {quantidade_registros} registros ({tipo_exportacao})",
            dados_novos={
                'tipo': tipo_exportacao,
                'quantidade': quantidade_registros
            },
            request=request,
            condominio_id=condominio_id
        )


# Instância global
audit_service = AuditService()


# ==================== DECORATOR PARA AUDITORIA ====================

def auditar(
    acao: TipoAcaoAuditoria,
    entidade_tipo: str,
    descricao_template: str = "{acao} em {entidade_tipo}"
):
    """
    Decorator para adicionar auditoria automática a endpoints

    Uso:
        @auditar(TipoAcaoAuditoria.BOLETO_CRIADO, 'boleto', 'Boleto criado')
        async def criar_boleto(request: Request, dados: BoletoCreate):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Executa função original
            result = await func(*args, **kwargs)

            # Tenta extrair request dos argumentos
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            # Tenta extrair usuário do request
            usuario_id = "system"
            usuario_email = "system@conectaplus.com.br"

            if request and hasattr(request, 'state'):
                if hasattr(request.state, 'user'):
                    usuario_id = getattr(request.state.user, 'id', usuario_id)
                    usuario_email = getattr(request.state.user, 'email', usuario_email)

            # Registra auditoria
            try:
                await audit_service.registrar(
                    usuario_id=usuario_id,
                    usuario_email=usuario_email,
                    acao=acao,
                    entidade_tipo=entidade_tipo,
                    entidade_id=str(getattr(result, 'id', 'unknown')),
                    descricao=descricao_template,
                    request=request
                )
            except Exception as e:
                # Não falha a operação se auditoria falhar
                print(f"[AUDIT] Erro no decorator: {e}")

            return result

        return wrapper
    return decorator
