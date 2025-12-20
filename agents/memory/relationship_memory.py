"""
Conecta Plus - Relationship Memory
Memória de relacionamentos entre entidades

Funcionalidades:
- Armazenamento de relacionamentos bidirecionais
- Histórico de interações
- Força e qualidade de relacionamentos
- Grafos de conexões
- Análise de comunidades
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    """Tipos de relacionamento"""
    # Familiares/Pessoais
    FAMILY = "family"
    SPOUSE = "spouse"
    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    RELATIVE = "relative"

    # Residenciais
    RESIDENT_OF = "resident_of"  # Pessoa -> Unidade
    OWNER_OF = "owner_of"  # Pessoa -> Unidade
    TENANT_OF = "tenant_of"  # Pessoa -> Unidade
    NEIGHBOR = "neighbor"  # Pessoa <-> Pessoa

    # Profissionais
    EMPLOYEE_OF = "employee_of"
    MANAGER_OF = "manager_of"
    COLLEAGUE = "colleague"
    SUPPLIER = "supplier"
    CLIENT = "client"

    # Veículos
    OWNER_VEHICLE = "owner_vehicle"  # Pessoa -> Veículo
    DRIVER_OF = "driver_of"  # Pessoa -> Veículo

    # Visitantes
    VISITOR_OF = "visitor_of"  # Pessoa -> Pessoa/Unidade
    AUTHORIZED_BY = "authorized_by"  # Pessoa -> Pessoa

    # Responsabilidades
    RESPONSIBLE_FOR = "responsible_for"
    GUARDIAN_OF = "guardian_of"
    DEPENDENT_OF = "dependent_of"

    # Organizacional
    MEMBER_OF = "member_of"  # Pessoa -> Organização/Grupo
    REPRESENTS = "represents"  # Pessoa -> Entidade

    # Genéricos
    KNOWS = "knows"
    RELATED_TO = "related_to"
    ASSOCIATED_WITH = "associated_with"


class RelationshipStatus(Enum):
    """Status do relacionamento"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    BLOCKED = "blocked"
    EXPIRED = "expired"


class InteractionType(Enum):
    """Tipos de interação"""
    MESSAGE = "message"
    CALL = "call"
    VISIT = "visit"
    MEETING = "meeting"
    TRANSACTION = "transaction"
    ACCESS = "access"
    DELIVERY = "delivery"
    COMPLAINT = "complaint"
    REQUEST = "request"
    SUPPORT = "support"
    OTHER = "other"


@dataclass
class Interaction:
    """Uma interação entre entidades"""
    interaction_id: str
    interaction_type: InteractionType
    timestamp: datetime = field(default_factory=datetime.now)

    # Participantes
    initiator_id: str = ""
    receiver_id: str = ""

    # Conteúdo
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    # Resultado
    outcome: str = "neutral"  # positive, negative, neutral
    sentiment: float = 0.0  # -1.0 a 1.0

    # Contexto
    channel: str = "direct"  # direct, app, phone, email
    location: Optional[str] = None
    related_conversation_id: Optional[str] = None

    # Métricas
    duration_seconds: int = 0
    response_time_seconds: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "interaction_type": self.interaction_type.value,
            "timestamp": self.timestamp.isoformat(),
            "initiator_id": self.initiator_id,
            "receiver_id": self.receiver_id,
            "summary": self.summary,
            "outcome": self.outcome,
            "sentiment": self.sentiment,
            "channel": self.channel,
        }


@dataclass
class InteractionHistory:
    """Histórico de interações entre duas entidades"""
    entity1_id: str
    entity2_id: str
    interactions: List[Interaction] = field(default_factory=list)

    # Métricas agregadas
    total_interactions: int = 0
    positive_interactions: int = 0
    negative_interactions: int = 0
    avg_sentiment: float = 0.0
    last_interaction: Optional[datetime] = None
    first_interaction: Optional[datetime] = None

    # Frequência
    interactions_last_30_days: int = 0
    interactions_last_90_days: int = 0

    def add_interaction(self, interaction: Interaction):
        """Adiciona interação ao histórico"""
        self.interactions.append(interaction)
        self.total_interactions += 1

        if interaction.outcome == "positive":
            self.positive_interactions += 1
        elif interaction.outcome == "negative":
            self.negative_interactions += 1

        # Atualizar média de sentimento
        total_sentiment = sum(i.sentiment for i in self.interactions)
        self.avg_sentiment = total_sentiment / len(self.interactions)

        # Atualizar timestamps
        self.last_interaction = interaction.timestamp
        if self.first_interaction is None:
            self.first_interaction = interaction.timestamp

        # Atualizar contadores de frequência
        now = datetime.now()
        cutoff_30 = now - timedelta(days=30)
        cutoff_90 = now - timedelta(days=90)

        self.interactions_last_30_days = sum(
            1 for i in self.interactions if i.timestamp > cutoff_30
        )
        self.interactions_last_90_days = sum(
            1 for i in self.interactions if i.timestamp > cutoff_90
        )

    @property
    def relationship_health(self) -> float:
        """Calcula saúde do relacionamento (0-1)"""
        if self.total_interactions == 0:
            return 0.5

        positive_ratio = self.positive_interactions / self.total_interactions
        recency_bonus = 0.2 if self.interactions_last_30_days > 0 else 0
        sentiment_factor = (self.avg_sentiment + 1) / 2  # Normalizar para 0-1

        return min(1.0, (positive_ratio * 0.4) + (sentiment_factor * 0.4) + recency_bonus)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity1_id": self.entity1_id,
            "entity2_id": self.entity2_id,
            "total_interactions": self.total_interactions,
            "positive_interactions": self.positive_interactions,
            "negative_interactions": self.negative_interactions,
            "avg_sentiment": self.avg_sentiment,
            "relationship_health": self.relationship_health,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "interactions_last_30_days": self.interactions_last_30_days,
        }


@dataclass
class Relationship:
    """Relacionamento entre duas entidades"""
    relationship_id: str
    relationship_type: RelationshipType
    status: RelationshipStatus = RelationshipStatus.ACTIVE

    # Entidades
    source_id: str = ""
    target_id: str = ""

    # Bidirecional
    bidirectional: bool = False
    inverse_type: Optional[RelationshipType] = None

    # Força e qualidade
    strength: float = 0.5  # 0.0 a 1.0
    trust_level: float = 0.5  # 0.0 a 1.0
    importance: float = 0.5  # 0.0 a 1.0

    # Metadados
    label: str = ""
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    # Temporal
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # Verificação
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

    # Histórico
    interaction_history: Optional[InteractionHistory] = None

    def __post_init__(self):
        if self.interaction_history is None:
            self.interaction_history = InteractionHistory(
                entity1_id=self.source_id,
                entity2_id=self.target_id
            )

    @property
    def is_active(self) -> bool:
        if self.status != RelationshipStatus.ACTIVE:
            return False
        now = datetime.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def update_strength(self, delta: float):
        """Atualiza força do relacionamento"""
        self.strength = max(0.0, min(1.0, self.strength + delta))

    def add_interaction(self, interaction: Interaction):
        """Registra interação"""
        self.interaction_history.add_interaction(interaction)

        # Ajustar força baseado na interação
        if interaction.outcome == "positive":
            self.update_strength(0.05)
        elif interaction.outcome == "negative":
            self.update_strength(-0.05)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "relationship_type": self.relationship_type.value,
            "status": self.status.value,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "bidirectional": self.bidirectional,
            "strength": self.strength,
            "trust_level": self.trust_level,
            "importance": self.importance,
            "label": self.label,
            "started_at": self.started_at.isoformat(),
            "is_active": self.is_active,
            "interaction_summary": self.interaction_history.to_dict() if self.interaction_history else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        rel = cls(
            relationship_id=data["relationship_id"],
            relationship_type=RelationshipType(data["relationship_type"]),
            status=RelationshipStatus(data.get("status", "active")),
            source_id=data["source_id"],
            target_id=data["target_id"],
            bidirectional=data.get("bidirectional", False),
            strength=data.get("strength", 0.5),
            trust_level=data.get("trust_level", 0.5),
            importance=data.get("importance", 0.5),
            label=data.get("label", ""),
            description=data.get("description", ""),
            properties=data.get("properties", {}),
        )

        if data.get("started_at"):
            rel.started_at = datetime.fromisoformat(data["started_at"])

        return rel


class RelationshipMemory:
    """
    Sistema de memória para relacionamentos.
    Implementa um grafo de relacionamentos entre entidades.
    """

    def __init__(
        self,
        redis_client=None,
        entity_memory=None,
    ):
        self.redis = redis_client
        self.entity_memory = entity_memory

        # Grafo de relacionamentos
        self._relationships: Dict[str, Relationship] = {}

        # Índices para busca rápida
        self._outgoing: Dict[str, Set[str]] = defaultdict(set)  # source -> relationship_ids
        self._incoming: Dict[str, Set[str]] = defaultdict(set)  # target -> relationship_ids
        self._by_type: Dict[RelationshipType, Set[str]] = defaultdict(set)
        self._by_pair: Dict[str, str] = {}  # "source:target" -> relationship_id

    # ========================================================================
    # CRUD DE RELACIONAMENTOS
    # ========================================================================

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        bidirectional: bool = False,
        **kwargs
    ) -> Relationship:
        """Cria novo relacionamento"""
        # Verificar se já existe
        pair_key = f"{source_id}:{target_id}"
        if pair_key in self._by_pair:
            existing = self.get_relationship(self._by_pair[pair_key])
            if existing and existing.relationship_type == relationship_type:
                return existing

        relationship_id = self._generate_id(source_id, target_id, relationship_type)

        relationship = Relationship(
            relationship_id=relationship_id,
            relationship_type=relationship_type,
            source_id=source_id,
            target_id=target_id,
            bidirectional=bidirectional,
            **kwargs
        )

        self._store_relationship(relationship)

        # Se bidirecional, criar relacionamento inverso
        if bidirectional:
            inverse_type = kwargs.get("inverse_type", relationship_type)
            self._create_inverse(relationship, inverse_type)

        logger.info(
            f"Relacionamento criado: {source_id} -{relationship_type.value}-> {target_id}"
        )
        return relationship

    def _create_inverse(self, relationship: Relationship, inverse_type: RelationshipType):
        """Cria relacionamento inverso"""
        inverse_id = self._generate_id(
            relationship.target_id,
            relationship.source_id,
            inverse_type
        )

        inverse = Relationship(
            relationship_id=inverse_id,
            relationship_type=inverse_type,
            source_id=relationship.target_id,
            target_id=relationship.source_id,
            bidirectional=False,  # Evitar recursão
            strength=relationship.strength,
            trust_level=relationship.trust_level,
        )

        self._store_relationship(inverse)

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Recupera relacionamento"""
        if relationship_id in self._relationships:
            return self._relationships[relationship_id]
        return asyncio.get_event_loop().run_until_complete(
            self._load_relationship(relationship_id)
        )

    def get_relationship_between(
        self,
        source_id: str,
        target_id: str
    ) -> Optional[Relationship]:
        """Recupera relacionamento entre duas entidades"""
        pair_key = f"{source_id}:{target_id}"
        rel_id = self._by_pair.get(pair_key)
        if rel_id:
            return self.get_relationship(rel_id)
        return None

    def update_relationship(
        self,
        relationship_id: str,
        **kwargs
    ) -> Optional[Relationship]:
        """Atualiza relacionamento"""
        rel = self.get_relationship(relationship_id)
        if not rel:
            return None

        for key, value in kwargs.items():
            if hasattr(rel, key):
                setattr(rel, key, value)

        self._store_relationship(rel)
        return rel

    def end_relationship(
        self,
        relationship_id: str,
        reason: str = None
    ) -> bool:
        """Encerra relacionamento"""
        rel = self.get_relationship(relationship_id)
        if not rel:
            return False

        rel.status = RelationshipStatus.INACTIVE
        rel.ended_at = datetime.now()
        if reason:
            rel.properties["end_reason"] = reason

        self._store_relationship(rel)
        return True

    # ========================================================================
    # CONSULTAS
    # ========================================================================

    def get_relationships_of(
        self,
        entity_id: str,
        relationship_type: RelationshipType = None,
        direction: str = "both",  # outgoing, incoming, both
        active_only: bool = True
    ) -> List[Relationship]:
        """Lista relacionamentos de uma entidade"""
        rel_ids = set()

        if direction in ["outgoing", "both"]:
            rel_ids.update(self._outgoing.get(entity_id, set()))

        if direction in ["incoming", "both"]:
            rel_ids.update(self._incoming.get(entity_id, set()))

        relationships = []
        for rid in rel_ids:
            rel = self.get_relationship(rid)
            if not rel:
                continue
            if active_only and not rel.is_active:
                continue
            if relationship_type and rel.relationship_type != relationship_type:
                continue
            relationships.append(rel)

        return relationships

    def get_related_entities(
        self,
        entity_id: str,
        relationship_type: RelationshipType = None,
        direction: str = "both"
    ) -> List[str]:
        """Lista entidades relacionadas"""
        relationships = self.get_relationships_of(entity_id, relationship_type, direction)

        related = []
        for rel in relationships:
            if rel.source_id == entity_id:
                related.append(rel.target_id)
            else:
                related.append(rel.source_id)

        return list(set(related))

    def get_by_type(
        self,
        relationship_type: RelationshipType,
        active_only: bool = True
    ) -> List[Relationship]:
        """Lista relacionamentos por tipo"""
        rel_ids = self._by_type.get(relationship_type, set())
        relationships = []

        for rid in rel_ids:
            rel = self.get_relationship(rid)
            if rel and (not active_only or rel.is_active):
                relationships.append(rel)

        return relationships

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 4
    ) -> Optional[List[Relationship]]:
        """Encontra caminho entre duas entidades (BFS)"""
        if source_id == target_id:
            return []

        visited = {source_id}
        queue = [(source_id, [])]

        while queue:
            current_id, path = queue.pop(0)

            if len(path) >= max_depth:
                continue

            for rel in self.get_relationships_of(current_id, direction="outgoing"):
                next_id = rel.target_id

                if next_id == target_id:
                    return path + [rel]

                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [rel]))

        return None

    def get_mutual_connections(
        self,
        entity1_id: str,
        entity2_id: str
    ) -> List[str]:
        """Encontra conexões mútuas"""
        connections1 = set(self.get_related_entities(entity1_id))
        connections2 = set(self.get_related_entities(entity2_id))

        return list(connections1 & connections2)

    # ========================================================================
    # INTERAÇÕES
    # ========================================================================

    def record_interaction(
        self,
        source_id: str,
        target_id: str,
        interaction_type: InteractionType,
        outcome: str = "neutral",
        **kwargs
    ) -> Interaction:
        """Registra interação entre entidades"""
        interaction = Interaction(
            interaction_id=self._generate_interaction_id(source_id, target_id),
            interaction_type=interaction_type,
            initiator_id=source_id,
            receiver_id=target_id,
            outcome=outcome,
            **kwargs
        )

        # Encontrar ou criar relacionamento
        rel = self.get_relationship_between(source_id, target_id)
        if rel:
            rel.add_interaction(interaction)
            self._store_relationship(rel)
        else:
            # Criar relacionamento genérico baseado na interação
            rel = self.create_relationship(
                source_id,
                target_id,
                RelationshipType.KNOWS,
                bidirectional=True
            )
            rel.add_interaction(interaction)

        return interaction

    def get_interaction_history(
        self,
        entity1_id: str,
        entity2_id: str
    ) -> Optional[InteractionHistory]:
        """Retorna histórico de interações"""
        rel = self.get_relationship_between(entity1_id, entity2_id)
        if rel:
            return rel.interaction_history

        # Tentar direção inversa
        rel = self.get_relationship_between(entity2_id, entity1_id)
        if rel:
            return rel.interaction_history

        return None

    # ========================================================================
    # ANÁLISE DE GRAFOS
    # ========================================================================

    def get_network_stats(self, entity_id: str) -> Dict[str, Any]:
        """Estatísticas de rede de uma entidade"""
        outgoing = len(self._outgoing.get(entity_id, set()))
        incoming = len(self._incoming.get(entity_id, set()))

        relationships = self.get_relationships_of(entity_id)

        total_strength = sum(r.strength for r in relationships)
        avg_strength = total_strength / len(relationships) if relationships else 0

        by_type = defaultdict(int)
        for rel in relationships:
            by_type[rel.relationship_type.value] += 1

        return {
            "entity_id": entity_id,
            "outgoing_connections": outgoing,
            "incoming_connections": incoming,
            "total_connections": outgoing + incoming,
            "avg_relationship_strength": avg_strength,
            "connections_by_type": dict(by_type),
        }

    def find_clusters(
        self,
        min_connections: int = 3
    ) -> List[Set[str]]:
        """Identifica clusters/comunidades"""
        clusters = []
        visited = set()

        for entity_id in list(self._outgoing.keys()) + list(self._incoming.keys()):
            if entity_id in visited:
                continue

            # BFS para encontrar cluster
            cluster = set()
            queue = [entity_id]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue

                visited.add(current)

                connections = self.get_related_entities(current)
                if len(connections) >= min_connections:
                    cluster.add(current)
                    for conn in connections:
                        if conn not in visited:
                            queue.append(conn)

            if len(cluster) >= min_connections:
                clusters.append(cluster)

        return clusters

    def get_influential_entities(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Identifica entidades mais influentes (por conexões)"""
        influence_scores = {}

        for entity_id in set(self._outgoing.keys()) | set(self._incoming.keys()):
            stats = self.get_network_stats(entity_id)
            # Score baseado em conexões e força média
            score = (
                stats["total_connections"] * 0.5 +
                stats["avg_relationship_strength"] * 10
            )
            influence_scores[entity_id] = score

        sorted_entities = sorted(
            influence_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_entities[:limit]

    def suggest_connections(
        self,
        entity_id: str,
        limit: int = 5
    ) -> List[Tuple[str, float, str]]:
        """Sugere novas conexões baseado em conexões em comum"""
        current_connections = set(self.get_related_entities(entity_id))
        suggestions = []

        # Para cada conexão, ver conexões dela
        for conn_id in current_connections:
            second_degree = self.get_related_entities(conn_id)
            for potential in second_degree:
                if potential == entity_id or potential in current_connections:
                    continue

                # Calcular afinidade
                mutual = len(set(self.get_related_entities(potential)) & current_connections)
                if mutual > 0:
                    reason = f"{mutual} conexões em comum"
                    suggestions.append((potential, mutual, reason))

        # Ordenar por afinidade
        suggestions.sort(key=lambda x: x[1], reverse=True)

        # Remover duplicados mantendo maior score
        seen = set()
        unique = []
        for s in suggestions:
            if s[0] not in seen:
                seen.add(s[0])
                unique.append(s)

        return unique[:limit]

    # ========================================================================
    # PERSISTÊNCIA
    # ========================================================================

    def _store_relationship(self, relationship: Relationship):
        """Armazena relacionamento"""
        self._relationships[relationship.relationship_id] = relationship
        self._update_indices(relationship)
        asyncio.create_task(self._persist_relationship(relationship))

    async def _persist_relationship(self, relationship: Relationship):
        """Persiste relacionamento"""
        if self.redis:
            data = json.dumps(relationship.to_dict())
            await self.redis.set(f"relationship:{relationship.relationship_id}", data)

    async def _load_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Carrega relacionamento"""
        if self.redis:
            data = await self.redis.get(f"relationship:{relationship_id}")
            if data:
                rel = Relationship.from_dict(json.loads(data))
                self._relationships[relationship_id] = rel
                self._update_indices(rel)
                return rel
        return None

    def _update_indices(self, rel: Relationship):
        """Atualiza índices"""
        self._outgoing[rel.source_id].add(rel.relationship_id)
        self._incoming[rel.target_id].add(rel.relationship_id)
        self._by_type[rel.relationship_type].add(rel.relationship_id)
        self._by_pair[f"{rel.source_id}:{rel.target_id}"] = rel.relationship_id

    # ========================================================================
    # UTILITÁRIOS
    # ========================================================================

    def _generate_id(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType
    ) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return hashlib.sha256(
            f"{source_id}:{target_id}:{rel_type.value}:{timestamp}".encode()
        ).hexdigest()[:16]

    def _generate_interaction_id(self, source_id: str, target_id: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return hashlib.sha256(
            f"interaction:{source_id}:{target_id}:{timestamp}".encode()
        ).hexdigest()[:12]

    def get_stats(self) -> Dict[str, Any]:
        """Estatísticas gerais"""
        type_counts = defaultdict(int)
        status_counts = defaultdict(int)

        for rel in self._relationships.values():
            type_counts[rel.relationship_type.value] += 1
            status_counts[rel.status.value] += 1

        return {
            "total_relationships": len(self._relationships),
            "unique_entities": len(set(self._outgoing.keys()) | set(self._incoming.keys())),
            "by_type": dict(type_counts),
            "by_status": dict(status_counts),
            "active_relationships": status_counts.get("active", 0),
        }
