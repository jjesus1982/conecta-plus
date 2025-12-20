"""
Conecta Plus - Entity Memory
Memória especializada para entidades (pessoas, lugares, objetos, conceitos)

Funcionalidades:
- Armazenamento de entidades com atributos
- Rastreamento de menções e contextos
- Resolução de referências (ele, ela, isso)
- Merge de entidades duplicadas
- Histórico de mudanças
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


class EntityType(Enum):
    """Tipos de entidades"""
    # Pessoas
    PERSON = "person"
    RESIDENT = "resident"  # Morador
    VISITOR = "visitor"  # Visitante
    EMPLOYEE = "employee"  # Funcionário
    SERVICE_PROVIDER = "service_provider"  # Prestador de serviço

    # Lugares
    LOCATION = "location"
    UNIT = "unit"  # Unidade/apartamento
    COMMON_AREA = "common_area"  # Área comum
    BUILDING = "building"  # Bloco/torre
    PARKING = "parking"  # Vaga

    # Veículos
    VEHICLE = "vehicle"
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    BICYCLE = "bicycle"

    # Objetos
    OBJECT = "object"
    EQUIPMENT = "equipment"  # Equipamento
    PACKAGE = "package"  # Encomenda
    DOCUMENT = "document"  # Documento

    # Abstratos
    EVENT = "event"
    TICKET = "ticket"  # Chamado/ocorrência
    RESERVATION = "reservation"  # Reserva
    MEETING = "meeting"  # Assembleia/reunião

    # Organizações
    ORGANIZATION = "organization"
    COMPANY = "company"
    DEPARTMENT = "department"

    # Outros
    CONCEPT = "concept"
    UNKNOWN = "unknown"


class EntityStatus(Enum):
    """Status da entidade"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"
    MERGED = "merged"
    PENDING_VERIFICATION = "pending"


@dataclass
class EntityAttribute:
    """Atributo de uma entidade"""
    name: str
    value: Any
    confidence: float = 1.0  # 0.0 - 1.0
    source: str = "user"  # user, system, inference
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    history: List[Tuple[Any, datetime]] = field(default_factory=list)

    def update(self, new_value: Any, source: str = "user"):
        """Atualiza valor mantendo histórico"""
        if self.value != new_value:
            self.history.append((self.value, self.updated_at))
            self.value = new_value
            self.source = source
            self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class EntityMention:
    """Menção de uma entidade em uma conversa/contexto"""
    mention_id: str
    entity_id: str
    text: str  # Texto original da menção
    context: str  # Contexto ao redor
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    resolved_by: str = "direct"  # direct, coreference, inference

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mention_id": self.mention_id,
            "entity_id": self.entity_id,
            "text": self.text,
            "context": self.context,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "resolved_by": self.resolved_by,
        }


@dataclass
class Entity:
    """Representa uma entidade no sistema"""
    entity_id: str
    entity_type: EntityType
    name: str
    status: EntityStatus = EntityStatus.ACTIVE

    # Identificadores alternativos
    aliases: List[str] = field(default_factory=list)
    external_ids: Dict[str, str] = field(default_factory=dict)  # cpf, rg, placa, etc.

    # Atributos
    attributes: Dict[str, EntityAttribute] = field(default_factory=dict)

    # Relacionamentos
    relationships: Dict[str, List[str]] = field(default_factory=dict)  # tipo -> [entity_ids]

    # Menções
    mentions: List[EntityMention] = field(default_factory=list)
    mention_count: int = 0

    # Metadados
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Merge info
    merged_from: List[str] = field(default_factory=list)
    merged_into: Optional[str] = None

    def add_attribute(self, name: str, value: Any, **kwargs):
        """Adiciona ou atualiza atributo"""
        if name in self.attributes:
            self.attributes[name].update(value, kwargs.get("source", "user"))
        else:
            self.attributes[name] = EntityAttribute(name=name, value=value, **kwargs)
        self.updated_at = datetime.now()

    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Retorna valor de um atributo"""
        attr = self.attributes.get(name)
        return attr.value if attr else default

    def add_alias(self, alias: str):
        """Adiciona alias (nome alternativo)"""
        if alias and alias not in self.aliases and alias != self.name:
            self.aliases.append(alias)
            self.updated_at = datetime.now()

    def add_relationship(self, relation_type: str, target_entity_id: str):
        """Adiciona relacionamento com outra entidade"""
        if relation_type not in self.relationships:
            self.relationships[relation_type] = []
        if target_entity_id not in self.relationships[relation_type]:
            self.relationships[relation_type].append(target_entity_id)
            self.updated_at = datetime.now()

    def add_mention(self, mention: EntityMention):
        """Registra nova menção"""
        self.mentions.append(mention)
        self.mention_count += 1
        self.last_seen = mention.timestamp
        self.updated_at = datetime.now()

    def matches_name(self, query: str) -> bool:
        """Verifica se query corresponde ao nome ou aliases"""
        query_lower = query.lower().strip()
        if query_lower == self.name.lower():
            return True
        return any(alias.lower() == query_lower for alias in self.aliases)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "status": self.status.value,
            "aliases": self.aliases,
            "external_ids": self.external_ids,
            "attributes": {k: v.to_dict() for k, v in self.attributes.items()},
            "relationships": self.relationships,
            "mention_count": self.mention_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """Cria entidade a partir de dict"""
        entity = cls(
            entity_id=data["entity_id"],
            entity_type=EntityType(data["entity_type"]),
            name=data["name"],
            status=EntityStatus(data.get("status", "active")),
            aliases=data.get("aliases", []),
            external_ids=data.get("external_ids", {}),
            mention_count=data.get("mention_count", 0),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
        )

        # Reconstruir atributos
        for name, attr_data in data.get("attributes", {}).items():
            entity.attributes[name] = EntityAttribute(
                name=name,
                value=attr_data["value"],
                confidence=attr_data.get("confidence", 1.0),
                source=attr_data.get("source", "user"),
            )

        entity.relationships = data.get("relationships", {})

        # Timestamps
        if "created_at" in data:
            entity.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            entity.updated_at = datetime.fromisoformat(data["updated_at"])
        if "last_seen" in data:
            entity.last_seen = datetime.fromisoformat(data["last_seen"])

        return entity


class EntityMemory:
    """
    Sistema de memória para entidades.
    Gerencia armazenamento, busca, resolução e merge de entidades.
    """

    def __init__(
        self,
        redis_client=None,
        vector_store=None,
        llm_client=None,
    ):
        self.redis = redis_client
        self.vector_store = vector_store
        self.llm = llm_client

        # Cache em memória
        self._entities: Dict[str, Entity] = {}

        # Índices para busca rápida
        self._by_type: Dict[EntityType, Set[str]] = defaultdict(set)
        self._by_name: Dict[str, Set[str]] = defaultdict(set)  # name_lower -> entity_ids
        self._by_external_id: Dict[str, str] = {}  # external_id -> entity_id

        # Contexto de conversa para resolução de referências
        self._conversation_context: Dict[str, List[str]] = defaultdict(list)  # conv_id -> entity_ids mencionados

    # ========================================================================
    # CRUD DE ENTIDADES
    # ========================================================================

    def create_entity(
        self,
        entity_type: EntityType,
        name: str,
        attributes: Dict[str, Any] = None,
        external_ids: Dict[str, str] = None,
        **kwargs
    ) -> Entity:
        """Cria nova entidade"""
        # Verificar se já existe por external_id
        if external_ids:
            for ext_type, ext_id in external_ids.items():
                existing = self.find_by_external_id(ext_type, ext_id)
                if existing:
                    logger.info(f"Entidade já existe com {ext_type}={ext_id}")
                    return existing

        # Criar nova entidade
        entity_id = self._generate_entity_id(entity_type, name)

        entity = Entity(
            entity_id=entity_id,
            entity_type=entity_type,
            name=name,
            external_ids=external_ids or {},
            **kwargs
        )

        # Adicionar atributos
        if attributes:
            for attr_name, attr_value in attributes.items():
                entity.add_attribute(attr_name, attr_value)

        # Armazenar
        self._store_entity(entity)

        logger.info(f"Entidade criada: {entity_id} ({entity_type.value}: {name})")
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Recupera entidade por ID"""
        if entity_id in self._entities:
            return self._entities[entity_id]

        # Tentar carregar do storage
        return asyncio.get_event_loop().run_until_complete(
            self._load_entity(entity_id)
        )

    def update_entity(
        self,
        entity_id: str,
        attributes: Dict[str, Any] = None,
        **kwargs
    ) -> Optional[Entity]:
        """Atualiza entidade"""
        entity = self.get_entity(entity_id)
        if not entity:
            return None

        # Atualizar atributos
        if attributes:
            for name, value in attributes.items():
                entity.add_attribute(name, value)

        # Atualizar outros campos
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        entity.updated_at = datetime.now()
        self._store_entity(entity)

        return entity

    def delete_entity(self, entity_id: str, soft: bool = True) -> bool:
        """Remove entidade (soft delete por padrão)"""
        entity = self.get_entity(entity_id)
        if not entity:
            return False

        if soft:
            entity.status = EntityStatus.DELETED
            entity.updated_at = datetime.now()
            self._store_entity(entity)
        else:
            self._remove_from_indices(entity)
            del self._entities[entity_id]

        return True

    # ========================================================================
    # BUSCA DE ENTIDADES
    # ========================================================================

    def find_by_name(
        self,
        name: str,
        entity_type: EntityType = None,
        fuzzy: bool = False
    ) -> List[Entity]:
        """Busca entidades por nome"""
        name_lower = name.lower().strip()
        results = []

        # Busca exata
        if name_lower in self._by_name:
            for entity_id in self._by_name[name_lower]:
                entity = self.get_entity(entity_id)
                if entity and entity.status == EntityStatus.ACTIVE:
                    if entity_type is None or entity.entity_type == entity_type:
                        results.append(entity)

        # Busca fuzzy se não encontrou
        if fuzzy and not results:
            for entity in self._entities.values():
                if entity.status != EntityStatus.ACTIVE:
                    continue
                if entity_type and entity.entity_type != entity_type:
                    continue

                # Verificar nome e aliases
                if name_lower in entity.name.lower() or any(
                    name_lower in alias.lower() for alias in entity.aliases
                ):
                    results.append(entity)

        return results

    def find_by_type(
        self,
        entity_type: EntityType,
        limit: int = 100,
        active_only: bool = True
    ) -> List[Entity]:
        """Busca entidades por tipo"""
        entity_ids = self._by_type.get(entity_type, set())
        results = []

        for entity_id in list(entity_ids)[:limit]:
            entity = self.get_entity(entity_id)
            if entity:
                if not active_only or entity.status == EntityStatus.ACTIVE:
                    results.append(entity)

        return results

    def find_by_external_id(
        self,
        id_type: str,
        id_value: str
    ) -> Optional[Entity]:
        """Busca entidade por ID externo (CPF, placa, etc.)"""
        key = f"{id_type}:{id_value}"
        entity_id = self._by_external_id.get(key)

        if entity_id:
            return self.get_entity(entity_id)
        return None

    def find_by_attribute(
        self,
        attribute_name: str,
        attribute_value: Any,
        entity_type: EntityType = None
    ) -> List[Entity]:
        """Busca entidades por valor de atributo"""
        results = []

        for entity in self._entities.values():
            if entity.status != EntityStatus.ACTIVE:
                continue
            if entity_type and entity.entity_type != entity_type:
                continue

            attr = entity.attributes.get(attribute_name)
            if attr and attr.value == attribute_value:
                results.append(entity)

        return results

    async def semantic_search(
        self,
        query: str,
        entity_type: EntityType = None,
        limit: int = 10
    ) -> List[Tuple[Entity, float]]:
        """Busca semântica de entidades"""
        if not self.vector_store:
            return []

        filters = {"type": "entity"}
        if entity_type:
            filters["entity_type"] = entity_type.value

        results = await self.vector_store.search(
            agent_id="entity_memory",
            query=query,
            limit=limit,
            filter_metadata=filters
        )

        entities_with_scores = []
        for result in results:
            entity_id = result.get("metadata", {}).get("entity_id")
            if entity_id:
                entity = self.get_entity(entity_id)
                if entity:
                    score = 1 - result.get("distance", 0)
                    entities_with_scores.append((entity, score))

        return entities_with_scores

    # ========================================================================
    # RESOLUÇÃO DE REFERÊNCIAS
    # ========================================================================

    def resolve_reference(
        self,
        text: str,
        conversation_id: str = None,
        context: str = None
    ) -> Optional[Entity]:
        """
        Resolve referência textual para entidade.
        Lida com pronomes, apelidos, referências indiretas.
        """
        text_lower = text.lower().strip()

        # 1. Busca direta por nome
        entities = self.find_by_name(text)
        if len(entities) == 1:
            return entities[0]

        # 2. Verificar pronomes/referências contextuais
        if conversation_id and text_lower in ["ele", "ela", "isso", "este", "esta", "esse", "essa"]:
            recent_entities = self._conversation_context.get(conversation_id, [])
            if recent_entities:
                # Retornar última entidade mencionada do tipo apropriado
                for entity_id in reversed(recent_entities):
                    entity = self.get_entity(entity_id)
                    if entity:
                        # Filtrar por gênero se aplicável
                        if text_lower in ["ele"] and entity.entity_type == EntityType.PERSON:
                            gender = entity.get_attribute("gender")
                            if gender == "M":
                                return entity
                        elif text_lower in ["ela"] and entity.entity_type == EntityType.PERSON:
                            gender = entity.get_attribute("gender")
                            if gender == "F":
                                return entity
                        elif text_lower in ["isso", "este", "esta", "esse", "essa"]:
                            return entity

        # 3. Busca por external_id em contexto
        # Ex: "a placa ABC1234", "o apartamento 101"
        import re

        # Placa de veículo
        placa_match = re.search(r'[A-Z]{3}[-]?\d{4}|[A-Z]{3}\d[A-Z]\d{2}', text.upper())
        if placa_match:
            entity = self.find_by_external_id("placa", placa_match.group())
            if entity:
                return entity

        # Unidade/apartamento
        unidade_match = re.search(r'(?:apt?o?\.?|unidade|apartamento)\s*(\d+[A-Z]?)', text_lower)
        if unidade_match:
            entities = self.find_by_attribute("numero", unidade_match.group(1), EntityType.UNIT)
            if len(entities) == 1:
                return entities[0]

        # 4. Busca fuzzy
        if len(entities) == 0:
            entities = self.find_by_name(text, fuzzy=True)
            if len(entities) == 1:
                return entities[0]

        # 5. Usar LLM para desambiguação se houver múltiplos resultados
        if len(entities) > 1 and self.llm and context:
            return asyncio.get_event_loop().run_until_complete(
                self._llm_disambiguate(text, entities, context)
            )

        return entities[0] if len(entities) == 1 else None

    async def _llm_disambiguate(
        self,
        text: str,
        candidates: List[Entity],
        context: str
    ) -> Optional[Entity]:
        """Usa LLM para desambiguar entre múltiplas entidades"""
        candidates_desc = "\n".join([
            f"{i+1}. {e.name} ({e.entity_type.value}) - {e.get_attribute('description', 'N/A')}"
            for i, e in enumerate(candidates)
        ])

        prompt = f"""Dado o contexto abaixo, qual entidade está sendo referenciada por "{text}"?

Contexto: {context}

Candidatos:
{candidates_desc}

Responda apenas com o número da opção correta (1, 2, etc.) ou 0 se nenhum corresponder."""

        try:
            response = await self.llm.generate(
                system_prompt="Você ajuda a identificar entidades. Responda apenas com um número.",
                user_message=prompt
            )

            choice = int(response.strip())
            if 1 <= choice <= len(candidates):
                return candidates[choice - 1]

        except Exception as e:
            logger.debug(f"Desambiguação LLM falhou: {e}")

        return None

    def register_mention(
        self,
        entity_id: str,
        text: str,
        context: str,
        conversation_id: str = None,
        **kwargs
    ) -> Optional[EntityMention]:
        """Registra menção de entidade"""
        entity = self.get_entity(entity_id)
        if not entity:
            return None

        mention = EntityMention(
            mention_id=self._generate_mention_id(entity_id),
            entity_id=entity_id,
            text=text,
            context=context,
            conversation_id=conversation_id,
            **kwargs
        )

        entity.add_mention(mention)

        # Atualizar contexto de conversa
        if conversation_id:
            if entity_id not in self._conversation_context[conversation_id]:
                self._conversation_context[conversation_id].append(entity_id)
            # Manter apenas últimas 10 entidades
            self._conversation_context[conversation_id] = \
                self._conversation_context[conversation_id][-10:]

        self._store_entity(entity)
        return mention

    # ========================================================================
    # MERGE DE ENTIDADES
    # ========================================================================

    def merge_entities(
        self,
        primary_id: str,
        secondary_id: str,
        strategy: str = "primary_wins"
    ) -> Optional[Entity]:
        """
        Merge duas entidades em uma.
        Strategies: primary_wins, secondary_wins, newest_wins, merge_all
        """
        primary = self.get_entity(primary_id)
        secondary = self.get_entity(secondary_id)

        if not primary or not secondary:
            return None

        # Definir qual entidade prevalece para atributos conflitantes
        if strategy == "secondary_wins":
            primary, secondary = secondary, primary
        elif strategy == "newest_wins":
            if secondary.updated_at > primary.updated_at:
                primary, secondary = secondary, primary

        # Merge aliases
        for alias in secondary.aliases:
            primary.add_alias(alias)
        primary.add_alias(secondary.name)

        # Merge external_ids
        for id_type, id_value in secondary.external_ids.items():
            if id_type not in primary.external_ids:
                primary.external_ids[id_type] = id_value

        # Merge atributos (estratégia: manter do primário, adicionar novos)
        for attr_name, attr in secondary.attributes.items():
            if attr_name not in primary.attributes or strategy == "merge_all":
                primary.attributes[attr_name] = attr

        # Merge relacionamentos
        for rel_type, rel_ids in secondary.relationships.items():
            for rel_id in rel_ids:
                primary.add_relationship(rel_type, rel_id)

        # Merge menções
        primary.mentions.extend(secondary.mentions)
        primary.mention_count += secondary.mention_count

        # Registrar merge
        primary.merged_from.append(secondary_id)
        secondary.status = EntityStatus.MERGED
        secondary.merged_into = primary_id

        # Atualizar timestamps
        primary.updated_at = datetime.now()

        # Persistir
        self._store_entity(primary)
        self._store_entity(secondary)

        # Atualizar índices
        self._remove_from_indices(secondary)

        logger.info(f"Entidades merged: {secondary_id} -> {primary_id}")
        return primary

    def find_duplicates(
        self,
        entity_type: EntityType = None,
        threshold: float = 0.8
    ) -> List[Tuple[Entity, Entity, float]]:
        """Encontra possíveis entidades duplicadas"""
        duplicates = []
        entities = list(self._entities.values())

        for i, entity1 in enumerate(entities):
            if entity1.status != EntityStatus.ACTIVE:
                continue
            if entity_type and entity1.entity_type != entity_type:
                continue

            for entity2 in entities[i+1:]:
                if entity2.status != EntityStatus.ACTIVE:
                    continue
                if entity1.entity_type != entity2.entity_type:
                    continue

                score = self._calculate_similarity(entity1, entity2)
                if score >= threshold:
                    duplicates.append((entity1, entity2, score))

        return sorted(duplicates, key=lambda x: x[2], reverse=True)

    def _calculate_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """Calcula similaridade entre duas entidades"""
        score = 0.0
        weights_total = 0.0

        # Nome similar
        name_sim = self._string_similarity(entity1.name, entity2.name)
        score += name_sim * 3.0
        weights_total += 3.0

        # Aliases em comum
        aliases1 = set([entity1.name.lower()] + [a.lower() for a in entity1.aliases])
        aliases2 = set([entity2.name.lower()] + [a.lower() for a in entity2.aliases])
        if aliases1 & aliases2:
            score += 2.0
        weights_total += 2.0

        # External IDs em comum
        for id_type, id_value in entity1.external_ids.items():
            if entity2.external_ids.get(id_type) == id_value:
                score += 5.0  # IDs iguais são forte indicador
                weights_total += 5.0
                break
        else:
            weights_total += 1.0

        # Atributos similares
        common_attrs = set(entity1.attributes.keys()) & set(entity2.attributes.keys())
        for attr in common_attrs:
            if entity1.attributes[attr].value == entity2.attributes[attr].value:
                score += 1.0
            weights_total += 1.0

        return score / weights_total if weights_total > 0 else 0.0

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calcula similaridade entre strings (Jaccard básico)"""
        s1_lower = s1.lower()
        s2_lower = s2.lower()

        if s1_lower == s2_lower:
            return 1.0

        # Jaccard em palavras
        words1 = set(s1_lower.split())
        words2 = set(s2_lower.split())

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    # ========================================================================
    # PERSISTÊNCIA E ÍNDICES
    # ========================================================================

    def _store_entity(self, entity: Entity):
        """Armazena entidade no cache e índices"""
        self._entities[entity.entity_id] = entity
        self._update_indices(entity)

        # Persistir assincronamente
        asyncio.create_task(self._persist_entity(entity))

    async def _persist_entity(self, entity: Entity):
        """Persiste entidade no storage"""
        if self.redis:
            data = json.dumps(entity.to_dict())
            await self.redis.set(f"entity:{entity.entity_id}", data)

        # Indexar no vector store
        if self.vector_store:
            searchable = f"{entity.name} {' '.join(entity.aliases)} {entity.entity_type.value}"
            for attr in entity.attributes.values():
                if isinstance(attr.value, str):
                    searchable += f" {attr.value}"

            await self.vector_store.store(
                agent_id="entity_memory",
                content=searchable,
                metadata={
                    "type": "entity",
                    "entity_id": entity.entity_id,
                    "entity_type": entity.entity_type.value,
                    "name": entity.name,
                }
            )

    async def _load_entity(self, entity_id: str) -> Optional[Entity]:
        """Carrega entidade do storage"""
        if self.redis:
            data = await self.redis.get(f"entity:{entity_id}")
            if data:
                entity = Entity.from_dict(json.loads(data))
                self._entities[entity_id] = entity
                self._update_indices(entity)
                return entity
        return None

    def _update_indices(self, entity: Entity):
        """Atualiza índices de busca"""
        # Por tipo
        self._by_type[entity.entity_type].add(entity.entity_id)

        # Por nome
        self._by_name[entity.name.lower()].add(entity.entity_id)
        for alias in entity.aliases:
            self._by_name[alias.lower()].add(entity.entity_id)

        # Por external_id
        for id_type, id_value in entity.external_ids.items():
            self._by_external_id[f"{id_type}:{id_value}"] = entity.entity_id

    def _remove_from_indices(self, entity: Entity):
        """Remove entidade dos índices"""
        self._by_type[entity.entity_type].discard(entity.entity_id)
        self._by_name[entity.name.lower()].discard(entity.entity_id)
        for alias in entity.aliases:
            self._by_name[alias.lower()].discard(entity.entity_id)
        for id_type, id_value in entity.external_ids.items():
            key = f"{id_type}:{id_value}"
            if self._by_external_id.get(key) == entity.entity_id:
                del self._by_external_id[key]

    # ========================================================================
    # UTILITÁRIOS
    # ========================================================================

    def _generate_entity_id(self, entity_type: EntityType, name: str) -> str:
        """Gera ID único para entidade"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        hash_input = f"{entity_type.value}:{name}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _generate_mention_id(self, entity_id: str) -> str:
        """Gera ID único para menção"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return hashlib.sha256(f"{entity_id}:{timestamp}".encode()).hexdigest()[:12]

    def clear_conversation_context(self, conversation_id: str):
        """Limpa contexto de conversa"""
        if conversation_id in self._conversation_context:
            del self._conversation_context[conversation_id]

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas da memória"""
        type_counts = defaultdict(int)
        for entity in self._entities.values():
            if entity.status == EntityStatus.ACTIVE:
                type_counts[entity.entity_type.value] += 1

        return {
            "total_entities": len(self._entities),
            "active_entities": sum(
                1 for e in self._entities.values()
                if e.status == EntityStatus.ACTIVE
            ),
            "by_type": dict(type_counts),
            "total_mentions": sum(e.mention_count for e in self._entities.values()),
            "indexed_names": len(self._by_name),
            "indexed_external_ids": len(self._by_external_id),
        }
