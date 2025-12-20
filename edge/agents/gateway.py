"""
Conecta Plus Edge Gateway
API local com suporte a modo offline e sincronização cloud
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings


# Configurações
class EdgeSettings(BaseSettings):
    NODE_ID: str = "edge-001"
    NODE_NAME: str = "Edge Node"
    CLOUD_API_URL: str = "https://api.conectaplus.com.br"
    CLOUD_API_KEY: Optional[str] = None
    LOCAL_API_PORT: int = 8080
    REDIS_URL: str = "redis://localhost:6379"
    MQTT_BROKER: str = "mqtt://localhost:1883"
    SYNC_INTERVAL: int = 30
    OFFLINE_MODE_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"


settings = EdgeSettings()

# Logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("edge-gateway")


# Redis connection
redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = await redis.from_url(settings.REDIS_URL)
    return redis_client


# Estado do edge
class EdgeState:
    """Gerencia estado do edge node"""

    def __init__(self):
        self.online = False
        self.last_sync = None
        self.pending_events = 0
        self.cloud_latency_ms = None

    def to_dict(self):
        return {
            "node_id": settings.NODE_ID,
            "node_name": settings.NODE_NAME,
            "online": self.online,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "pending_events": self.pending_events,
            "cloud_latency_ms": self.cloud_latency_ms,
            "timestamp": datetime.utcnow().isoformat()
        }


edge_state = EdgeState()


# Models
class AccessEvent(BaseModel):
    type: str  # entry, exit, visitor
    person_id: Optional[str] = None
    unit_id: Optional[str] = None
    camera_id: Optional[str] = None
    plate: Optional[str] = None
    face_match: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class DetectionEvent(BaseModel):
    camera_id: str
    label: str  # person, car, etc
    confidence: float
    bbox: List[float]
    timestamp: float
    snapshot_path: Optional[str] = None


class SyncQueue:
    """Fila de sincronização com cloud"""

    QUEUE_KEY = "edge:sync:queue"
    PROCESSED_KEY = "edge:sync:processed"

    @staticmethod
    async def push(event_type: str, data: Dict[str, Any]):
        """Adiciona evento à fila de sync"""
        r = await get_redis()
        event = {
            "id": f"{settings.NODE_ID}:{datetime.utcnow().timestamp()}",
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "node_id": settings.NODE_ID
        }
        await r.rpush(SyncQueue.QUEUE_KEY, json.dumps(event))
        edge_state.pending_events = await r.llen(SyncQueue.QUEUE_KEY)

    @staticmethod
    async def pop_batch(batch_size: int = 100) -> List[Dict]:
        """Remove lote de eventos da fila"""
        r = await get_redis()
        events = []
        for _ in range(batch_size):
            event = await r.lpop(SyncQueue.QUEUE_KEY)
            if event:
                events.append(json.loads(event))
            else:
                break
        edge_state.pending_events = await r.llen(SyncQueue.QUEUE_KEY)
        return events

    @staticmethod
    async def requeue(events: List[Dict]):
        """Recoloca eventos na fila (em caso de falha)"""
        r = await get_redis()
        for event in events:
            await r.lpush(SyncQueue.QUEUE_KEY, json.dumps(event))
        edge_state.pending_events = await r.llen(SyncQueue.QUEUE_KEY)


class CloudSync:
    """Sincronização com cloud"""

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=settings.CLOUD_API_URL,
            headers={"Authorization": f"Bearer {settings.CLOUD_API_KEY}"},
            timeout=30.0
        )

    async def check_connectivity(self) -> bool:
        """Verifica conectividade com cloud"""
        try:
            start = datetime.utcnow()
            response = await self.client.get("/health")
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            edge_state.cloud_latency_ms = latency
            edge_state.online = response.status_code == 200
            return edge_state.online
        except Exception as e:
            logger.warning(f"Cloud connectivity check failed: {e}")
            edge_state.online = False
            edge_state.cloud_latency_ms = None
            return False

    async def sync_events(self) -> int:
        """Sincroniza eventos com cloud"""
        if not edge_state.online:
            return 0

        events = await SyncQueue.pop_batch()
        if not events:
            return 0

        try:
            response = await self.client.post(
                f"/edge/{settings.NODE_ID}/events",
                json={"events": events}
            )

            if response.status_code == 200:
                edge_state.last_sync = datetime.utcnow()
                logger.info(f"Synced {len(events)} events to cloud")
                return len(events)
            else:
                # Requeue on failure
                await SyncQueue.requeue(events)
                logger.error(f"Sync failed: {response.status_code}")
                return 0

        except Exception as e:
            logger.error(f"Sync error: {e}")
            await SyncQueue.requeue(events)
            return 0

    async def fetch_updates(self) -> Dict[str, Any]:
        """Busca atualizações do cloud"""
        if not edge_state.online:
            return {}

        try:
            response = await self.client.get(
                f"/edge/{settings.NODE_ID}/updates",
                params={"since": edge_state.last_sync.isoformat() if edge_state.last_sync else None}
            )

            if response.status_code == 200:
                return response.json()
            return {}

        except Exception as e:
            logger.error(f"Fetch updates error: {e}")
            return {}


cloud_sync = CloudSync()


# Background sync task
async def sync_loop():
    """Loop de sincronização em background"""
    while True:
        try:
            # Check connectivity
            await cloud_sync.check_connectivity()

            # Sync events
            if edge_state.online:
                await cloud_sync.sync_events()

        except Exception as e:
            logger.error(f"Sync loop error: {e}")

        await asyncio.sleep(settings.SYNC_INTERVAL)


# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting Edge Gateway: {settings.NODE_ID}")
    await get_redis()
    asyncio.create_task(sync_loop())
    yield
    # Shutdown
    if redis_client:
        await redis_client.close()


# FastAPI app
app = FastAPI(
    title="Conecta Plus Edge Gateway",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes
@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "node_id": settings.NODE_ID}


@app.get("/ready")
async def ready():
    """Readiness check"""
    try:
        r = await get_redis()
        await r.ping()
        return {"status": "ready", "redis": True, "cloud": edge_state.online}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/status")
async def status():
    """Edge node status"""
    return edge_state.to_dict()


@app.post("/access/register")
async def register_access(event: AccessEvent, background: BackgroundTasks):
    """Registra evento de acesso"""
    # Salvar localmente
    r = await get_redis()
    event_data = event.dict()
    event_data["timestamp"] = datetime.utcnow().isoformat()
    event_data["node_id"] = settings.NODE_ID

    # Cache local
    event_key = f"access:{datetime.utcnow().strftime('%Y%m%d')}:{event.type}"
    await r.rpush(event_key, json.dumps(event_data))
    await r.expire(event_key, 86400 * 7)  # 7 dias

    # Adicionar à fila de sync
    await SyncQueue.push("access", event_data)

    return {"success": True, "queued": True, "online": edge_state.online}


@app.post("/detection/register")
async def register_detection(event: DetectionEvent):
    """Registra evento de detecção de IA"""
    r = await get_redis()
    event_data = event.dict()
    event_data["node_id"] = settings.NODE_ID

    # Cache local
    event_key = f"detection:{event.camera_id}:{datetime.utcnow().strftime('%Y%m%d')}"
    await r.rpush(event_key, json.dumps(event_data))
    await r.expire(event_key, 86400 * 7)

    # Adicionar à fila de sync
    await SyncQueue.push("detection", event_data)

    return {"success": True}


@app.get("/access/today")
async def get_today_access():
    """Retorna acessos de hoje"""
    r = await get_redis()
    today = datetime.utcnow().strftime('%Y%m%d')

    entries = []
    for event_type in ["entry", "exit", "visitor"]:
        key = f"access:{today}:{event_type}"
        events = await r.lrange(key, 0, -1)
        for e in events:
            entries.append(json.loads(e))

    return {"date": today, "count": len(entries), "entries": entries}


@app.get("/cameras")
async def list_cameras():
    """Lista câmeras disponíveis"""
    # TODO: Integrar com device manager
    return {"cameras": []}


@app.post("/sync/force")
async def force_sync():
    """Força sincronização imediata"""
    online = await cloud_sync.check_connectivity()
    if online:
        count = await cloud_sync.sync_events()
        return {"success": True, "synced": count}
    return {"success": False, "reason": "offline"}


@app.get("/sync/queue")
async def get_sync_queue():
    """Retorna status da fila de sync"""
    r = await get_redis()
    count = await r.llen(SyncQueue.QUEUE_KEY)
    return {
        "pending": count,
        "last_sync": edge_state.last_sync.isoformat() if edge_state.last_sync else None,
        "online": edge_state.online
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.LOCAL_API_PORT)
