"""
Conecta Plus - Memory Store
Sistema de memória de longo prazo para agentes

Componentes:
- KeyValueMemory: Memória simples chave-valor (Redis)
- VectorMemory: Memória semântica com embeddings (ChromaDB/Qdrant)
- EpisodicMemory: Memória de episódios/eventos
- WorkingMemory: Memória de curto prazo para contexto
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio
import logging
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """Item de memória"""
    key: str
    value: Any
    agent_id: str
    memory_type: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: float = 0.5  # 0.0 - 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class Episode:
    """Episódio de memória (sequência de eventos)"""
    episode_id: str
    agent_id: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    outcome: str = ""  # success, failure, neutral
    lessons_learned: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseMemoryStore(ABC):
    """Interface base para memory stores"""

    @abstractmethod
    async def store(self, agent_id: str, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        pass

    @abstractmethod
    async def retrieve(self, agent_id: str, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def delete(self, agent_id: str, key: str) -> bool:
        pass

    @abstractmethod
    async def list_keys(self, agent_id: str, pattern: str = "*") -> List[str]:
        pass


class RedisMemoryStore(BaseMemoryStore):
    """
    Memory store usando Redis para armazenamento rápido.
    Ideal para memória de trabalho e cache.
    """

    def __init__(self, redis_url: str, prefix: str = "agent_memory"):
        self.redis_url = redis_url
        self.prefix = prefix
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import redis.asyncio as redis
            self._client = await redis.from_url(self.redis_url)
        return self._client

    def _make_key(self, agent_id: str, key: str) -> str:
        return f"{self.prefix}:{agent_id}:{key}"

    async def store(self, agent_id: str, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        try:
            client = await self._get_client()
            full_key = self._make_key(agent_id, key)

            item = MemoryItem(
                key=key,
                value=value,
                agent_id=agent_id,
                memory_type="redis",
                metadata=metadata or {}
            )

            data = json.dumps({
                "key": item.key,
                "value": item.value,
                "agent_id": item.agent_id,
                "memory_type": item.memory_type,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "access_count": item.access_count,
                "importance": item.importance,
                "metadata": item.metadata
            })

            await client.set(full_key, data)
            return True

        except Exception as e:
            logger.error(f"Erro ao armazenar memória: {e}")
            return False

    async def retrieve(self, agent_id: str, key: str) -> Optional[Any]:
        try:
            client = await self._get_client()
            full_key = self._make_key(agent_id, key)

            data = await client.get(full_key)
            if data:
                item = json.loads(data)
                # Incrementar contador de acesso
                item["access_count"] += 1
                await client.set(full_key, json.dumps(item))
                return item["value"]
            return None

        except Exception as e:
            logger.error(f"Erro ao recuperar memória: {e}")
            return None

    async def delete(self, agent_id: str, key: str) -> bool:
        try:
            client = await self._get_client()
            full_key = self._make_key(agent_id, key)
            await client.delete(full_key)
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar memória: {e}")
            return False

    async def list_keys(self, agent_id: str, pattern: str = "*") -> List[str]:
        try:
            client = await self._get_client()
            full_pattern = self._make_key(agent_id, pattern)
            keys = await client.keys(full_pattern)
            # Remover prefixo
            prefix_len = len(f"{self.prefix}:{agent_id}:")
            return [k.decode()[prefix_len:] for k in keys]
        except Exception as e:
            logger.error(f"Erro ao listar chaves: {e}")
            return []

    async def store_with_ttl(self, agent_id: str, key: str, value: Any, ttl_seconds: int) -> bool:
        """Armazena com tempo de expiração"""
        try:
            client = await self._get_client()
            full_key = self._make_key(agent_id, key)
            await client.setex(full_key, ttl_seconds, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Erro ao armazenar memória com TTL: {e}")
            return False


class VectorMemoryStore:
    """
    Memory store com suporte a busca semântica usando embeddings.
    Usa ChromaDB ou Qdrant como backend.
    """

    def __init__(
        self,
        collection_name: str = "agent_memories",
        embedding_model: str = "text-embedding-3-small",
        persist_directory: str = "./data/vector_db"
    ):
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.persist_directory = persist_directory
        self._client = None
        self._collection = None
        self._embedder = None

    async def _init_chroma(self):
        """Inicializa ChromaDB"""
        if self._client is None:
            import chromadb
            from chromadb.config import Settings

            self._client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.persist_directory,
                anonymized_telemetry=False
            ))

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

    async def _get_embedding(self, text: str) -> List[float]:
        """Gera embedding para texto usando OpenAI ou local"""
        try:
            # Tentar usar OpenAI
            import openai
            response = await openai.Embedding.acreate(
                input=text,
                model=self.embedding_model
            )
            return response['data'][0]['embedding']
        except:
            # Fallback: usar sentence-transformers local
            try:
                from sentence_transformers import SentenceTransformer
                if self._embedder is None:
                    self._embedder = SentenceTransformer('all-MiniLM-L6-v2')
                return self._embedder.encode(text).tolist()
            except:
                # Fallback final: hash simples (não recomendado para produção)
                logger.warning("Usando hash como embedding fallback")
                hash_val = hashlib.md5(text.encode()).hexdigest()
                return [float(int(c, 16)) / 16 for c in hash_val]

    async def store(
        self,
        agent_id: str,
        content: str,
        metadata: Dict[str, Any] = None,
        doc_id: str = None
    ) -> bool:
        """Armazena documento com embedding"""
        try:
            await self._init_chroma()

            # Gerar ID único se não fornecido
            if doc_id is None:
                doc_id = hashlib.sha256(
                    f"{agent_id}:{content}:{datetime.now().isoformat()}".encode()
                ).hexdigest()[:16]

            # Gerar embedding
            embedding = await self._get_embedding(content)

            # Preparar metadata
            meta = {
                "agent_id": agent_id,
                "created_at": datetime.now().isoformat(),
                **(metadata or {})
            }

            # Armazenar
            self._collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[meta]
            )

            return True

        except Exception as e:
            logger.error(f"Erro ao armazenar no vector store: {e}")
            return False

    async def search(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Busca semântica por similaridade"""
        try:
            await self._init_chroma()

            # Gerar embedding da query
            query_embedding = await self._get_embedding(query)

            # Filtro por agent_id
            where_filter = {"agent_id": agent_id}
            if filter_metadata:
                where_filter.update(filter_metadata)

            # Buscar
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter
            )

            # Formatar resultados
            items = []
            for i, doc_id in enumerate(results['ids'][0]):
                items.append({
                    "id": doc_id,
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })

            return items

        except Exception as e:
            logger.error(f"Erro na busca semântica: {e}")
            return []

    async def delete(self, doc_id: str) -> bool:
        """Remove documento por ID"""
        try:
            await self._init_chroma()
            self._collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar documento: {e}")
            return False

    async def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Recupera documento por ID"""
        try:
            await self._init_chroma()
            result = self._collection.get(ids=[doc_id])
            if result['ids']:
                return {
                    "id": result['ids'][0],
                    "content": result['documents'][0],
                    "metadata": result['metadatas'][0]
                }
            return None
        except Exception as e:
            logger.error(f"Erro ao recuperar documento: {e}")
            return None


class EpisodicMemory:
    """
    Memória episódica para armazenar sequências de eventos.
    Útil para aprender com experiências passadas.
    """

    def __init__(self, redis_store: RedisMemoryStore, vector_store: VectorMemoryStore):
        self.redis = redis_store
        self.vector = vector_store
        self._active_episodes: Dict[str, Episode] = {}

    def start_episode(self, agent_id: str, initial_context: Dict[str, Any] = None) -> Episode:
        """Inicia um novo episódio"""
        episode_id = hashlib.sha256(
            f"{agent_id}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        episode = Episode(
            episode_id=episode_id,
            agent_id=agent_id,
            metadata=initial_context or {}
        )

        self._active_episodes[episode_id] = episode
        return episode

    def add_event(self, episode_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """Adiciona evento ao episódio"""
        if episode_id not in self._active_episodes:
            logger.warning(f"Episódio {episode_id} não encontrado")
            return

        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        self._active_episodes[episode_id].events.append(event)

    async def end_episode(
        self,
        episode_id: str,
        outcome: str,
        summary: str,
        lessons: List[str] = None
    ) -> Episode:
        """Finaliza e persiste episódio"""
        if episode_id not in self._active_episodes:
            raise ValueError(f"Episódio {episode_id} não encontrado")

        episode = self._active_episodes[episode_id]
        episode.ended_at = datetime.now()
        episode.outcome = outcome
        episode.summary = summary
        episode.lessons_learned = lessons or []

        # Persistir no Redis
        await self.redis.store(
            agent_id=episode.agent_id,
            key=f"episode:{episode_id}",
            value={
                "episode_id": episode.episode_id,
                "events": episode.events,
                "summary": episode.summary,
                "outcome": episode.outcome,
                "lessons_learned": episode.lessons_learned,
                "started_at": episode.started_at.isoformat(),
                "ended_at": episode.ended_at.isoformat(),
                "metadata": episode.metadata
            }
        )

        # Indexar no Vector Store para busca semântica
        searchable_content = f"Episódio: {summary}. Resultado: {outcome}. Lições: {', '.join(lessons or [])}"
        await self.vector.store(
            agent_id=episode.agent_id,
            content=searchable_content,
            metadata={
                "type": "episode",
                "episode_id": episode_id,
                "outcome": outcome
            }
        )

        # Remover da memória ativa
        del self._active_episodes[episode_id]

        return episode

    async def get_similar_episodes(
        self,
        agent_id: str,
        situation_description: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Busca episódios similares à situação atual"""
        return await self.vector.search(
            agent_id=agent_id,
            query=situation_description,
            limit=limit,
            filter_metadata={"type": "episode"}
        )


class WorkingMemory:
    """
    Memória de trabalho (curto prazo) para contexto da conversa atual.
    Usa sliding window para manter últimas N interações.
    """

    def __init__(self, max_items: int = 20, ttl_seconds: int = 3600):
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._memory: Dict[str, List[Dict[str, Any]]] = {}

    def add(self, session_id: str, item_type: str, content: Any) -> None:
        """Adiciona item à memória de trabalho"""
        if session_id not in self._memory:
            self._memory[session_id] = []

        item = {
            "type": item_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        self._memory[session_id].append(item)

        # Manter apenas últimos N itens
        if len(self._memory[session_id]) > self.max_items:
            self._memory[session_id] = self._memory[session_id][-self.max_items:]

    def get_context(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Retorna contexto da sessão"""
        if session_id not in self._memory:
            return []

        items = self._memory[session_id]
        if limit:
            items = items[-limit:]
        return items

    def get_formatted_context(self, session_id: str, limit: int = 10) -> str:
        """Retorna contexto formatado para prompt"""
        items = self.get_context(session_id, limit)

        if not items:
            return "Sem contexto anterior."

        formatted = []
        for item in items:
            if item["type"] == "user_message":
                formatted.append(f"Usuário: {item['content']}")
            elif item["type"] == "assistant_message":
                formatted.append(f"Assistente: {item['content']}")
            elif item["type"] == "action":
                formatted.append(f"[Ação executada: {item['content']}]")
            elif item["type"] == "observation":
                formatted.append(f"[Observação: {item['content']}]")
            else:
                formatted.append(f"[{item['type']}: {item['content']}]")

        return "\n".join(formatted)

    def clear(self, session_id: str) -> None:
        """Limpa memória da sessão"""
        if session_id in self._memory:
            del self._memory[session_id]

    def summarize_and_compress(self, session_id: str) -> str:
        """Comprime memória mantendo informações essenciais"""
        items = self.get_context(session_id)

        if not items:
            return ""

        # Simplificação: pegar primeiros e últimos itens
        summary_items = []
        if len(items) > 6:
            summary_items = items[:3] + [{"type": "...", "content": f"[{len(items)-6} mensagens anteriores]"}] + items[-3:]
        else:
            summary_items = items

        return self.get_formatted_context(session_id)


class UnifiedMemorySystem:
    """
    Sistema unificado de memória que combina todos os tipos.
    Interface principal para agentes.
    """

    def __init__(
        self,
        redis_url: str = None,
        vector_persist_dir: str = "./data/vector_db"
    ):
        self.redis_store = RedisMemoryStore(redis_url) if redis_url else None
        self.vector_store = VectorMemoryStore(persist_directory=vector_persist_dir)
        self.episodic = EpisodicMemory(self.redis_store, self.vector_store) if self.redis_store else None
        self.working = WorkingMemory()

    # === Key-Value Memory ===
    async def store(self, agent_id: str, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Armazena na memória chave-valor"""
        if self.redis_store:
            return await self.redis_store.store(agent_id, key, value, metadata)
        return False

    async def retrieve(self, agent_id: str, key: str) -> Optional[Any]:
        """Recupera da memória chave-valor"""
        if self.redis_store:
            return await self.redis_store.retrieve(agent_id, key)
        return None

    # === Semantic Memory ===
    async def remember_semantic(self, agent_id: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Armazena na memória semântica"""
        return await self.vector_store.store(agent_id, content, metadata)

    async def search_semantic(self, agent_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca semântica"""
        return await self.vector_store.search(agent_id, query, limit)

    # === Episodic Memory ===
    def start_episode(self, agent_id: str, context: Dict[str, Any] = None) -> Episode:
        """Inicia episódio"""
        if self.episodic:
            return self.episodic.start_episode(agent_id, context)
        raise ValueError("Memória episódica não disponível")

    def add_episode_event(self, episode_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """Adiciona evento ao episódio"""
        if self.episodic:
            self.episodic.add_event(episode_id, event_type, data)

    async def end_episode(self, episode_id: str, outcome: str, summary: str, lessons: List[str] = None) -> Episode:
        """Finaliza episódio"""
        if self.episodic:
            return await self.episodic.end_episode(episode_id, outcome, summary, lessons)
        raise ValueError("Memória episódica não disponível")

    async def find_similar_episodes(self, agent_id: str, situation: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca episódios similares"""
        if self.episodic:
            return await self.episodic.get_similar_episodes(agent_id, situation, limit)
        return []

    # === Working Memory ===
    def add_to_context(self, session_id: str, item_type: str, content: Any) -> None:
        """Adiciona ao contexto da sessão"""
        self.working.add(session_id, item_type, content)

    def get_context(self, session_id: str, limit: int = 10) -> str:
        """Retorna contexto formatado"""
        return self.working.get_formatted_context(session_id, limit)

    def clear_context(self, session_id: str) -> None:
        """Limpa contexto da sessão"""
        self.working.clear(session_id)
