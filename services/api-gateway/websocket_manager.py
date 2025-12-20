"""
WebSocket Manager para comunicação em tempo real
Gerencia conexões WebSocket para CFTV, alertas e notificações
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    """Gerenciador de conexões WebSocket"""

    def __init__(self):
        # Conexões ativas por tipo de canal
        self.active_connections: Dict[str, List[WebSocket]] = {
            "alerts": [],
            "cftv": [],
            "access": [],
            "notifications": [],
        }
        # Conexões por usuário
        self.user_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str, user_id: str = None):
        """Conecta um novo WebSocket"""
        await websocket.accept()

        if channel not in self.active_connections:
            self.active_connections[channel] = []

        self.active_connections[channel].append(websocket)

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

        print(f"[WS] Nova conexão: canal={channel}, user={user_id}")

    def disconnect(self, websocket: WebSocket, channel: str, user_id: str = None):
        """Desconecta um WebSocket"""
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)

        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)

        print(f"[WS] Desconexão: canal={channel}, user={user_id}")

    async def broadcast(self, channel: str, message: dict):
        """Envia mensagem para todos os clientes de um canal"""
        if channel not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Remove conexões mortas
        for conn in disconnected:
            self.active_connections[channel].remove(conn)

    async def send_to_user(self, user_id: str, message: dict):
        """Envia mensagem para um usuário específico"""
        if user_id not in self.user_connections:
            return

        disconnected = []
        for connection in self.user_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Remove conexões mortas
        for conn in disconnected:
            self.user_connections[user_id].remove(conn)

    async def send_alert(self, alert_type: str, message: str, priority: str = "media", data: dict = None):
        """Envia um alerta para todos os clientes conectados ao canal de alertas"""
        alert = {
            "type": "alert",
            "alert_type": alert_type,
            "message": message,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        }
        await self.broadcast("alerts", alert)

    async def send_camera_event(self, camera_id: str, event_type: str, data: dict = None):
        """Envia evento de câmera"""
        event = {
            "type": "camera_event",
            "camera_id": camera_id,
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        }
        await self.broadcast("cftv", event)

    async def send_access_event(self, access_type: str, person_name: str, location: str, authorized: bool):
        """Envia evento de acesso"""
        event = {
            "type": "access_event",
            "access_type": access_type,
            "person_name": person_name,
            "location": location,
            "authorized": authorized,
            "timestamp": datetime.now().isoformat(),
        }
        await self.broadcast("access", event)

    def get_stats(self) -> dict:
        """Retorna estatísticas das conexões"""
        return {
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "by_channel": {channel: len(conns) for channel, conns in self.active_connections.items()},
            "users_connected": len(self.user_connections),
        }


# Instância global do gerenciador
manager = ConnectionManager()


# Simulador de eventos para testes
async def simulate_events():
    """Simula eventos para testes (remover em produção)"""
    import random

    events = [
        lambda: manager.send_alert("camera_offline", "Câmera do estacionamento offline", "alta"),
        lambda: manager.send_alert("visitante_aguardando", "Novo visitante na portaria", "media"),
        lambda: manager.send_access_event("entrada", "Carlos Silva", "Portão Principal", True),
        lambda: manager.send_camera_event("1", "motion_detected", {"area": "entrada"}),
    ]

    while True:
        await asyncio.sleep(random.randint(10, 30))  # Evento a cada 10-30 segundos
        event = random.choice(events)
        await event()
