"""
Conecta Plus - WebSocket Notifier
Notificações em tempo real para o frontend
"""

import json
import asyncio
from typing import Dict, Any, Set, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from fastapi import WebSocket, WebSocketDisconnect


class TipoNotificacao(str, Enum):
    """Tipos de notificação"""
    PAGAMENTO_CONFIRMADO = "pagamento_confirmado"
    BOLETO_CRIADO = "boleto_criado"
    BOLETO_VENCIDO = "boleto_vencido"
    COBRANCA_ENVIADA = "cobranca_enviada"
    ACORDO_CRIADO = "acordo_criado"
    SINCRONIZACAO_BANCO = "sincronizacao_banco"
    ALERTA_INADIMPLENCIA = "alerta_inadimplencia"
    RELATORIO_GERADO = "relatorio_gerado"
    SISTEMA = "sistema"


@dataclass
class Notificacao:
    """Estrutura de notificação"""
    tipo: TipoNotificacao
    titulo: str
    mensagem: str
    dados: Dict[str, Any]
    timestamp: str = None
    lida: bool = False
    id: str = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.id:
            self.id = f"notif_{datetime.now().timestamp()}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tipo': self.tipo.value if isinstance(self.tipo, TipoNotificacao) else self.tipo,
            'titulo': self.titulo,
            'mensagem': self.mensagem,
            'dados': self.dados,
            'timestamp': self.timestamp,
            'lida': self.lida
        }


class WebSocketManager:
    """Gerenciador de conexões WebSocket"""

    def __init__(self):
        # Conexões por condomínio
        self.conexoes: Dict[str, Set[WebSocket]] = {}
        # Conexões globais (admin)
        self.conexoes_admin: Set[WebSocket] = set()
        # Histórico de notificações
        self.historico: Dict[str, List[Notificacao]] = {}
        # Lock para operações thread-safe
        self._lock = asyncio.Lock()

    async def conectar(
        self,
        websocket: WebSocket,
        condominio_id: str = None,
        is_admin: bool = False
    ):
        """
        Conecta um cliente WebSocket

        Args:
            websocket: Conexão WebSocket
            condominio_id: ID do condomínio (opcional)
            is_admin: Se é conexão de admin (recebe tudo)
        """
        await websocket.accept()

        async with self._lock:
            if is_admin:
                self.conexoes_admin.add(websocket)
            elif condominio_id:
                if condominio_id not in self.conexoes:
                    self.conexoes[condominio_id] = set()
                self.conexoes[condominio_id].add(websocket)

        # Envia notificações não lidas
        if condominio_id and condominio_id in self.historico:
            nao_lidas = [n for n in self.historico[condominio_id] if not n.lida]
            for notif in nao_lidas[-10:]:  # Últimas 10
                try:
                    await websocket.send_json(notif.to_dict())
                except Exception:
                    pass

    async def desconectar(
        self,
        websocket: WebSocket,
        condominio_id: str = None
    ):
        """Desconecta um cliente WebSocket"""
        async with self._lock:
            self.conexoes_admin.discard(websocket)

            if condominio_id and condominio_id in self.conexoes:
                self.conexoes[condominio_id].discard(websocket)

            # Remove conjuntos vazios
            for cond_id in list(self.conexoes.keys()):
                if not self.conexoes[cond_id]:
                    del self.conexoes[cond_id]

    async def enviar_notificacao(
        self,
        notificacao: Notificacao,
        condominio_id: str = None,
        broadcast: bool = False
    ):
        """
        Envia notificação para clientes conectados

        Args:
            notificacao: Notificação a enviar
            condominio_id: ID do condomínio destino
            broadcast: Se deve enviar para todos
        """
        mensagem = notificacao.to_dict()

        # Salva no histórico
        if condominio_id:
            if condominio_id not in self.historico:
                self.historico[condominio_id] = []
            self.historico[condominio_id].append(notificacao)
            # Mantém apenas últimas 100 notificações
            if len(self.historico[condominio_id]) > 100:
                self.historico[condominio_id] = self.historico[condominio_id][-100:]

        conexoes_enviar = set()

        # Coleta conexões destino
        if broadcast:
            conexoes_enviar.update(self.conexoes_admin)
            for conns in self.conexoes.values():
                conexoes_enviar.update(conns)
        else:
            conexoes_enviar.update(self.conexoes_admin)
            if condominio_id and condominio_id in self.conexoes:
                conexoes_enviar.update(self.conexoes[condominio_id])

        # Envia para cada conexão
        conexoes_mortas = set()
        for websocket in conexoes_enviar:
            try:
                await websocket.send_json(mensagem)
            except Exception:
                conexoes_mortas.add(websocket)

        # Remove conexões mortas
        for ws in conexoes_mortas:
            await self.desconectar(ws)

    async def notificar_pagamento(
        self,
        boleto: Dict[str, Any],
        condominio_id: str
    ):
        """Notifica pagamento confirmado"""
        valor = boleto.get('valor_pago', boleto.get('valor', 0))
        valor_fmt = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        notificacao = Notificacao(
            tipo=TipoNotificacao.PAGAMENTO_CONFIRMADO,
            titulo="Pagamento Confirmado",
            mensagem=f"Pagamento de {valor_fmt} recebido - {boleto.get('unidade', '')}",
            dados={
                'boleto_id': boleto.get('id'),
                'unidade': boleto.get('unidade'),
                'morador': boleto.get('morador'),
                'valor': valor,
                'competencia': boleto.get('competencia'),
                'forma_pagamento': boleto.get('forma_pagamento')
            }
        )

        await self.enviar_notificacao(notificacao, condominio_id)

    async def notificar_boleto_criado(
        self,
        boleto: Dict[str, Any],
        condominio_id: str
    ):
        """Notifica criação de boleto"""
        notificacao = Notificacao(
            tipo=TipoNotificacao.BOLETO_CRIADO,
            titulo="Novo Boleto Emitido",
            mensagem=f"Boleto {boleto.get('competencia', '')} criado para {boleto.get('unidade', '')}",
            dados={
                'boleto_id': boleto.get('id'),
                'unidade': boleto.get('unidade'),
                'valor': boleto.get('valor'),
                'vencimento': boleto.get('vencimento')
            }
        )

        await self.enviar_notificacao(notificacao, condominio_id)

    async def notificar_cobranca(
        self,
        boleto: Dict[str, Any],
        canal: str,
        condominio_id: str
    ):
        """Notifica envio de cobrança"""
        notificacao = Notificacao(
            tipo=TipoNotificacao.COBRANCA_ENVIADA,
            titulo="Cobrança Enviada",
            mensagem=f"Cobrança enviada via {canal.upper()} para {boleto.get('morador', '')}",
            dados={
                'boleto_id': boleto.get('id'),
                'canal': canal,
                'unidade': boleto.get('unidade')
            }
        )

        await self.enviar_notificacao(notificacao, condominio_id)

    async def notificar_sincronizacao(
        self,
        resultado: Dict[str, Any],
        condominio_id: str
    ):
        """Notifica resultado de sincronização bancária"""
        notificacao = Notificacao(
            tipo=TipoNotificacao.SINCRONIZACAO_BANCO,
            titulo="Sincronização Concluída",
            mensagem=f"{resultado.get('novos_pagamentos', 0)} novos pagamentos encontrados",
            dados=resultado
        )

        await self.enviar_notificacao(notificacao, condominio_id)

    async def notificar_alerta_inadimplencia(
        self,
        dados: Dict[str, Any],
        condominio_id: str
    ):
        """Notifica alerta de inadimplência"""
        notificacao = Notificacao(
            tipo=TipoNotificacao.ALERTA_INADIMPLENCIA,
            titulo="Alerta de Inadimplência",
            mensagem=f"Taxa de inadimplência: {dados.get('taxa', 0):.1f}%",
            dados=dados
        )

        await self.enviar_notificacao(notificacao, condominio_id)

    async def notificar_sistema(
        self,
        titulo: str,
        mensagem: str,
        condominio_id: str = None,
        broadcast: bool = False
    ):
        """Notifica mensagem do sistema"""
        notificacao = Notificacao(
            tipo=TipoNotificacao.SISTEMA,
            titulo=titulo,
            mensagem=mensagem,
            dados={}
        )

        await self.enviar_notificacao(notificacao, condominio_id, broadcast)

    def get_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas das conexões"""
        total_conexoes = sum(len(conns) for conns in self.conexoes.values())
        total_conexoes += len(self.conexoes_admin)

        return {
            'total_conexoes': total_conexoes,
            'conexoes_admin': len(self.conexoes_admin),
            'condominios_conectados': len(self.conexoes),
            'historico_total': sum(len(h) for h in self.historico.values())
        }


# Instância global
ws_manager = WebSocketManager()


# Handler para endpoint WebSocket
async def websocket_handler(
    websocket: WebSocket,
    condominio_id: str = None,
    token: str = None
):
    """
    Handler para conexões WebSocket

    Uso no FastAPI:
    @app.websocket("/ws/{condominio_id}")
    async def websocket_endpoint(websocket: WebSocket, condominio_id: str):
        await websocket_handler(websocket, condominio_id)
    """
    # TODO: Validar token
    is_admin = token == "admin_token"  # Simplificado

    await ws_manager.conectar(websocket, condominio_id, is_admin)

    try:
        while True:
            # Aguarda mensagens do cliente (ping/pong, etc)
            data = await websocket.receive_text()

            # Processa comandos do cliente
            try:
                msg = json.loads(data)
                cmd = msg.get('command')

                if cmd == 'ping':
                    await websocket.send_json({'type': 'pong', 'timestamp': datetime.now().isoformat()})
                elif cmd == 'marcar_lida':
                    notif_id = msg.get('notificacao_id')
                    if condominio_id and condominio_id in ws_manager.historico:
                        for n in ws_manager.historico[condominio_id]:
                            if n.id == notif_id:
                                n.lida = True
                                break
                elif cmd == 'get_historico':
                    if condominio_id and condominio_id in ws_manager.historico:
                        historico = [n.to_dict() for n in ws_manager.historico[condominio_id][-50:]]
                        await websocket.send_json({'type': 'historico', 'data': historico})

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        await ws_manager.desconectar(websocket, condominio_id)
    except Exception:
        await ws_manager.desconectar(websocket, condominio_id)
