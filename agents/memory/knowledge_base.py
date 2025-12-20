"""
Conecta Plus - Knowledge Base
Base de conhecimento persistente para agentes

Funcionalidades:
- Armazenamento de conhecimento estruturado
- Categorização hierárquica
- Versionamento de informações
- Busca semântica
- Validação de conhecimento
- Fontes e referências
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


class KnowledgeCategory(Enum):
    """Categorias de conhecimento"""
    # Regras e regulamentos
    RULES = "rules"
    REGULATIONS = "regulations"
    BYLAWS = "bylaws"  # Convenção do condomínio
    INTERNAL_RULES = "internal_rules"  # Regimento interno

    # Procedimentos
    PROCEDURES = "procedures"
    WORKFLOWS = "workflows"
    BEST_PRACTICES = "best_practices"

    # Informações
    FAQ = "faq"
    GENERAL_INFO = "general_info"
    CONTACT_INFO = "contact_info"
    SCHEDULE = "schedule"

    # Técnico
    TECHNICAL = "technical"
    TROUBLESHOOTING = "troubleshooting"
    MAINTENANCE = "maintenance"

    # Financeiro
    FINANCIAL = "financial"
    FEES = "fees"
    BUDGET = "budget"

    # Segurança
    SECURITY = "security"
    EMERGENCY = "emergency"
    ACCESS_CONTROL = "access_control"

    # Infraestrutura
    FACILITIES = "facilities"
    AMENITIES = "amenities"
    SERVICES = "services"

    # Histórico
    HISTORY = "history"
    DECISIONS = "decisions"
    MEETING_MINUTES = "meeting_minutes"

    # Outros
    OTHER = "other"


class KnowledgeSource(Enum):
    """Fontes de conhecimento"""
    OFFICIAL_DOCUMENT = "official_document"
    MEETING_MINUTES = "meeting_minutes"
    ADMIN_INPUT = "admin_input"
    USER_FEEDBACK = "user_feedback"
    SYSTEM_GENERATED = "system_generated"
    EXTERNAL_API = "external_api"
    INFERENCE = "inference"


class KnowledgeStatus(Enum):
    """Status do conhecimento"""
    DRAFT = "draft"
    ACTIVE = "active"
    REVIEW_PENDING = "review_pending"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ValidationStatus(Enum):
    """Status de validação"""
    NOT_VALIDATED = "not_validated"
    VALIDATED = "validated"
    NEEDS_UPDATE = "needs_update"
    DISPUTED = "disputed"


@dataclass
class KnowledgeVersion:
    """Versão de um item de conhecimento"""
    version_id: str
    version_number: int
    content: str
    changed_by: str
    changed_at: datetime
    change_reason: str = ""
    diff_from_previous: str = ""


@dataclass
class KnowledgeReference:
    """Referência/fonte de conhecimento"""
    reference_id: str
    source_type: KnowledgeSource
    source_name: str
    source_url: Optional[str] = None
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    retrieved_at: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeItem:
    """Item de conhecimento"""
    knowledge_id: str
    title: str
    content: str
    category: KnowledgeCategory
    subcategory: Optional[str] = None

    # Status
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    validation_status: ValidationStatus = ValidationStatus.NOT_VALIDATED

    # Metadados
    keywords: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    related_items: List[str] = field(default_factory=list)

    # Fontes
    sources: List[KnowledgeReference] = field(default_factory=list)

    # Versionamento
    version: int = 1
    versions: List[KnowledgeVersion] = field(default_factory=list)

    # Aplicabilidade
    applies_to: List[str] = field(default_factory=list)  # condomínios, tipos de usuário
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # Métricas
    access_count: int = 0
    usefulness_score: float = 0.0
    last_accessed: Optional[datetime] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    updated_by: str = "system"

    # Embedding
    embedding: Optional[List[float]] = None

    def update_content(self, new_content: str, changed_by: str, reason: str = ""):
        """Atualiza conteúdo mantendo histórico"""
        # Salvar versão anterior
        version = KnowledgeVersion(
            version_id=f"{self.knowledge_id}_v{self.version}",
            version_number=self.version,
            content=self.content,
            changed_by=changed_by,
            changed_at=datetime.now(),
            change_reason=reason
        )
        self.versions.append(version)

        # Atualizar
        self.content = new_content
        self.version += 1
        self.updated_at = datetime.now()
        self.updated_by = changed_by

    def add_reference(self, source: KnowledgeReference):
        """Adiciona referência/fonte"""
        self.sources.append(source)

    def is_valid(self) -> bool:
        """Verifica se conhecimento está válido"""
        now = datetime.now()

        if self.status != KnowledgeStatus.ACTIVE:
            return False

        if self.valid_from and now < self.valid_from:
            return False

        if self.valid_until and now > self.valid_until:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "title": self.title,
            "content": self.content,
            "category": self.category.value,
            "subcategory": self.subcategory,
            "status": self.status.value,
            "validation_status": self.validation_status.value,
            "keywords": self.keywords,
            "tags": self.tags,
            "related_items": self.related_items,
            "version": self.version,
            "applies_to": self.applies_to,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "access_count": self.access_count,
            "usefulness_score": self.usefulness_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeItem":
        """Cria item a partir de dict"""
        item = cls(
            knowledge_id=data["knowledge_id"],
            title=data["title"],
            content=data["content"],
            category=KnowledgeCategory(data["category"]),
            subcategory=data.get("subcategory"),
            status=KnowledgeStatus(data.get("status", "active")),
            validation_status=ValidationStatus(data.get("validation_status", "not_validated")),
            keywords=data.get("keywords", []),
            tags=data.get("tags", []),
            related_items=data.get("related_items", []),
            version=data.get("version", 1),
            applies_to=data.get("applies_to", []),
            access_count=data.get("access_count", 0),
            usefulness_score=data.get("usefulness_score", 0.0),
            created_by=data.get("created_by", "system"),
        )

        if data.get("valid_from"):
            item.valid_from = datetime.fromisoformat(data["valid_from"])
        if data.get("valid_until"):
            item.valid_until = datetime.fromisoformat(data["valid_until"])
        if data.get("created_at"):
            item.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            item.updated_at = datetime.fromisoformat(data["updated_at"])

        return item


class KnowledgeBase:
    """
    Base de conhecimento para agentes.
    Gerencia armazenamento, busca e manutenção de conhecimento.
    """

    def __init__(
        self,
        redis_client=None,
        vector_store=None,
        llm_client=None,
        condominio_id: str = None,
    ):
        self.redis = redis_client
        self.vector_store = vector_store
        self.llm = llm_client
        self.condominio_id = condominio_id

        # Cache em memória
        self._items: Dict[str, KnowledgeItem] = {}

        # Índices
        self._by_category: Dict[KnowledgeCategory, Set[str]] = defaultdict(set)
        self._by_keyword: Dict[str, Set[str]] = defaultdict(set)
        self._by_tag: Dict[str, Set[str]] = defaultdict(set)

    # ========================================================================
    # CRUD
    # ========================================================================

    def add_knowledge(
        self,
        title: str,
        content: str,
        category: KnowledgeCategory,
        keywords: List[str] = None,
        tags: List[str] = None,
        source: KnowledgeSource = KnowledgeSource.ADMIN_INPUT,
        created_by: str = "system",
        **kwargs
    ) -> KnowledgeItem:
        """Adiciona novo conhecimento"""
        knowledge_id = self._generate_id(title)

        # Extrair keywords automaticamente se não fornecidas
        if not keywords:
            keywords = self._extract_keywords(content)

        item = KnowledgeItem(
            knowledge_id=knowledge_id,
            title=title,
            content=content,
            category=category,
            keywords=keywords or [],
            tags=tags or [],
            created_by=created_by,
            updated_by=created_by,
            **kwargs
        )

        # Adicionar referência da fonte
        if source:
            ref = KnowledgeReference(
                reference_id=f"ref_{knowledge_id}",
                source_type=source,
                source_name=created_by
            )
            item.add_reference(ref)

        # Armazenar
        self._store_item(item)

        logger.info(f"Conhecimento adicionado: {knowledge_id} - {title}")
        return item

    def get_knowledge(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        """Recupera conhecimento por ID"""
        if knowledge_id in self._items:
            item = self._items[knowledge_id]
            item.access_count += 1
            item.last_accessed = datetime.now()
            return item

        # Tentar carregar do storage
        return asyncio.get_event_loop().run_until_complete(
            self._load_item(knowledge_id)
        )

    def update_knowledge(
        self,
        knowledge_id: str,
        content: str = None,
        title: str = None,
        updated_by: str = "system",
        reason: str = "",
        **kwargs
    ) -> Optional[KnowledgeItem]:
        """Atualiza conhecimento"""
        item = self.get_knowledge(knowledge_id)
        if not item:
            return None

        if content and content != item.content:
            item.update_content(content, updated_by, reason)

        if title:
            item.title = title

        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)

        item.updated_at = datetime.now()
        item.updated_by = updated_by

        self._store_item(item)
        return item

    def delete_knowledge(self, knowledge_id: str, soft: bool = True) -> bool:
        """Remove conhecimento"""
        item = self.get_knowledge(knowledge_id)
        if not item:
            return False

        if soft:
            item.status = KnowledgeStatus.ARCHIVED
            self._store_item(item)
        else:
            self._remove_from_indices(item)
            del self._items[knowledge_id]

        return True

    # ========================================================================
    # BUSCA
    # ========================================================================

    def search(
        self,
        query: str,
        category: KnowledgeCategory = None,
        tags: List[str] = None,
        limit: int = 10,
        active_only: bool = True
    ) -> List[KnowledgeItem]:
        """Busca conhecimento por texto"""
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for item in self._items.values():
            if active_only and not item.is_valid():
                continue
            if category and item.category != category:
                continue
            if tags and not any(t in item.tags for t in tags):
                continue

            # Calcular relevância
            score = 0

            # Match no título
            if query_lower in item.title.lower():
                score += 10
            elif any(w in item.title.lower() for w in query_words):
                score += 5

            # Match no conteúdo
            content_lower = item.content.lower()
            if query_lower in content_lower:
                score += 5
            else:
                word_matches = sum(1 for w in query_words if w in content_lower)
                score += word_matches

            # Match em keywords
            keyword_matches = sum(1 for k in item.keywords if k.lower() in query_lower)
            score += keyword_matches * 3

            if score > 0:
                results.append((item, score))

        # Ordenar por relevância
        results.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in results[:limit]]

    async def semantic_search(
        self,
        query: str,
        category: KnowledgeCategory = None,
        limit: int = 10
    ) -> List[Tuple[KnowledgeItem, float]]:
        """Busca semântica usando embeddings"""
        if not self.vector_store:
            # Fallback para busca por texto
            items = self.search(query, category, limit=limit)
            return [(item, 1.0) for item in items]

        filters = {"type": "knowledge"}
        if category:
            filters["category"] = category.value
        if self.condominio_id:
            filters["condominio_id"] = self.condominio_id

        results = await self.vector_store.search(
            agent_id="knowledge_base",
            query=query,
            limit=limit,
            filter_metadata=filters
        )

        items_with_scores = []
        for result in results:
            knowledge_id = result.get("metadata", {}).get("knowledge_id")
            if knowledge_id:
                item = self.get_knowledge(knowledge_id)
                if item and item.is_valid():
                    score = 1 - result.get("distance", 0)
                    items_with_scores.append((item, score))

        return items_with_scores

    def get_by_category(
        self,
        category: KnowledgeCategory,
        limit: int = 50
    ) -> List[KnowledgeItem]:
        """Lista conhecimento por categoria"""
        ids = self._by_category.get(category, set())
        items = []

        for kid in list(ids)[:limit]:
            item = self.get_knowledge(kid)
            if item and item.is_valid():
                items.append(item)

        return items

    def get_by_tag(self, tag: str) -> List[KnowledgeItem]:
        """Lista conhecimento por tag"""
        ids = self._by_tag.get(tag.lower(), set())
        return [
            self.get_knowledge(kid)
            for kid in ids
            if self.get_knowledge(kid) and self.get_knowledge(kid).is_valid()
        ]

    def get_related(self, knowledge_id: str, limit: int = 5) -> List[KnowledgeItem]:
        """Retorna conhecimentos relacionados"""
        item = self.get_knowledge(knowledge_id)
        if not item:
            return []

        related = []

        # Itens explicitamente relacionados
        for rel_id in item.related_items:
            rel_item = self.get_knowledge(rel_id)
            if rel_item and rel_item.is_valid():
                related.append(rel_item)

        # Buscar por keywords/tags similares
        if len(related) < limit:
            for keyword in item.keywords:
                for other_id in self._by_keyword.get(keyword.lower(), set()):
                    if other_id != knowledge_id and other_id not in [r.knowledge_id for r in related]:
                        other = self.get_knowledge(other_id)
                        if other and other.is_valid():
                            related.append(other)
                            if len(related) >= limit:
                                break
                if len(related) >= limit:
                    break

        return related[:limit]

    # ========================================================================
    # PERGUNTAS E RESPOSTAS
    # ========================================================================

    async def answer_question(
        self,
        question: str,
        category: KnowledgeCategory = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Responde uma pergunta usando a base de conhecimento.
        Combina busca + geração de resposta.
        """
        # Buscar conhecimento relevante
        relevant_items = await self.semantic_search(question, category, limit=5)

        if not relevant_items:
            return {
                "answer": None,
                "sources": [],
                "confidence": 0.0,
                "found_knowledge": False
            }

        # Preparar contexto
        knowledge_context = "\n\n".join([
            f"### {item.title}\n{item.content}"
            for item, _ in relevant_items
        ])

        # Gerar resposta com LLM
        if self.llm:
            prompt = f"""Com base no seguinte conhecimento, responda à pergunta do usuário.

CONHECIMENTO:
{knowledge_context}

PERGUNTA: {question}

CONTEXTO ADICIONAL: {json.dumps(context or {})}

Responda de forma clara e direta. Se a informação não estiver no conhecimento fornecido, diga que não tem essa informação."""

            try:
                response = await self.llm.generate(
                    system_prompt="Você é um assistente que responde perguntas baseado no conhecimento fornecido.",
                    user_message=prompt
                )

                return {
                    "answer": response,
                    "sources": [
                        {"id": item.knowledge_id, "title": item.title, "relevance": score}
                        for item, score in relevant_items
                    ],
                    "confidence": relevant_items[0][1] if relevant_items else 0.0,
                    "found_knowledge": True
                }

            except Exception as e:
                logger.error(f"Erro ao gerar resposta: {e}")

        # Fallback: retornar conhecimento mais relevante
        best_item, best_score = relevant_items[0]
        return {
            "answer": best_item.content,
            "sources": [{"id": best_item.knowledge_id, "title": best_item.title}],
            "confidence": best_score,
            "found_knowledge": True
        }

    # ========================================================================
    # VALIDAÇÃO E MANUTENÇÃO
    # ========================================================================

    def validate_knowledge(
        self,
        knowledge_id: str,
        validated_by: str,
        status: ValidationStatus = ValidationStatus.VALIDATED
    ) -> bool:
        """Marca conhecimento como validado"""
        item = self.get_knowledge(knowledge_id)
        if not item:
            return False

        item.validation_status = status
        item.updated_at = datetime.now()
        item.updated_by = validated_by

        self._store_item(item)
        return True

    def deprecate_knowledge(
        self,
        knowledge_id: str,
        reason: str,
        replacement_id: str = None
    ) -> bool:
        """Depreca conhecimento"""
        item = self.get_knowledge(knowledge_id)
        if not item:
            return False

        item.status = KnowledgeStatus.DEPRECATED
        item.tags.append("deprecated")

        if replacement_id:
            item.related_items.append(replacement_id)
            item.tags.append(f"replaced_by:{replacement_id}")

        self._store_item(item)
        return True

    def get_stale_knowledge(self, days: int = 90) -> List[KnowledgeItem]:
        """Lista conhecimento não atualizado há muito tempo"""
        cutoff = datetime.now() - timedelta(days=days)

        return [
            item for item in self._items.values()
            if item.status == KnowledgeStatus.ACTIVE
            and item.updated_at < cutoff
        ]

    def get_low_usefulness(self, threshold: float = 0.3) -> List[KnowledgeItem]:
        """Lista conhecimento com baixa utilidade"""
        return [
            item for item in self._items.values()
            if item.status == KnowledgeStatus.ACTIVE
            and item.access_count > 10
            and item.usefulness_score < threshold
        ]

    def record_feedback(
        self,
        knowledge_id: str,
        useful: bool,
        feedback_text: str = None
    ):
        """Registra feedback sobre conhecimento"""
        item = self.get_knowledge(knowledge_id)
        if not item:
            return

        # Atualizar score de utilidade (média móvel)
        weight = 0.1
        current_score = item.usefulness_score
        new_value = 1.0 if useful else 0.0
        item.usefulness_score = current_score * (1 - weight) + new_value * weight

        if not useful and feedback_text:
            item.validation_status = ValidationStatus.NEEDS_UPDATE
            item.tags.append("needs_review")

        self._store_item(item)

    # ========================================================================
    # IMPORTAÇÃO/EXPORTAÇÃO
    # ========================================================================

    def import_from_document(
        self,
        content: str,
        source_name: str,
        category: KnowledgeCategory,
        split_by: str = "\n\n"
    ) -> List[KnowledgeItem]:
        """Importa conhecimento de um documento"""
        items = []
        sections = content.split(split_by)

        for i, section in enumerate(sections):
            section = section.strip()
            if len(section) < 50:  # Ignorar seções muito pequenas
                continue

            # Extrair título (primeira linha ou gerar)
            lines = section.split("\n")
            title = lines[0][:100] if lines else f"Seção {i+1}"
            content = "\n".join(lines[1:]) if len(lines) > 1 else section

            item = self.add_knowledge(
                title=title,
                content=content,
                category=category,
                source=KnowledgeSource.OFFICIAL_DOCUMENT,
                created_by=source_name
            )
            items.append(item)

        return items

    def export_to_json(self, category: KnowledgeCategory = None) -> str:
        """Exporta conhecimento para JSON"""
        items = []

        for item in self._items.values():
            if category and item.category != category:
                continue
            if item.status == KnowledgeStatus.ACTIVE:
                items.append(item.to_dict())

        return json.dumps(items, indent=2, ensure_ascii=False)

    # ========================================================================
    # PERSISTÊNCIA
    # ========================================================================

    def _store_item(self, item: KnowledgeItem):
        """Armazena item no cache e índices"""
        self._items[item.knowledge_id] = item
        self._update_indices(item)

        # Persistir assincronamente
        asyncio.create_task(self._persist_item(item))

    async def _persist_item(self, item: KnowledgeItem):
        """Persiste item no storage"""
        if self.redis:
            data = json.dumps(item.to_dict())
            await self.redis.set(f"knowledge:{item.knowledge_id}", data)

        # Indexar no vector store
        if self.vector_store:
            searchable = f"{item.title} {item.content} {' '.join(item.keywords)}"

            await self.vector_store.store(
                agent_id="knowledge_base",
                content=searchable,
                metadata={
                    "type": "knowledge",
                    "knowledge_id": item.knowledge_id,
                    "category": item.category.value,
                    "title": item.title,
                    "condominio_id": self.condominio_id,
                }
            )

    async def _load_item(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        """Carrega item do storage"""
        if self.redis:
            data = await self.redis.get(f"knowledge:{knowledge_id}")
            if data:
                item = KnowledgeItem.from_dict(json.loads(data))
                self._items[knowledge_id] = item
                self._update_indices(item)
                return item
        return None

    def _update_indices(self, item: KnowledgeItem):
        """Atualiza índices"""
        self._by_category[item.category].add(item.knowledge_id)

        for keyword in item.keywords:
            self._by_keyword[keyword.lower()].add(item.knowledge_id)

        for tag in item.tags:
            self._by_tag[tag.lower()].add(item.knowledge_id)

    def _remove_from_indices(self, item: KnowledgeItem):
        """Remove item dos índices"""
        self._by_category[item.category].discard(item.knowledge_id)

        for keyword in item.keywords:
            self._by_keyword[keyword.lower()].discard(item.knowledge_id)

        for tag in item.tags:
            self._by_tag[tag.lower()].discard(item.knowledge_id)

    # ========================================================================
    # UTILITÁRIOS
    # ========================================================================

    def _generate_id(self, title: str) -> str:
        """Gera ID único"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        hash_input = f"{title}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """Extrai keywords do conteúdo"""
        # Lista de stopwords em português
        stopwords = {
            "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
            "um", "uma", "uns", "umas", "o", "a", "os", "as", "e", "ou",
            "para", "por", "com", "sem", "que", "se", "não", "mais", "muito",
            "como", "quando", "onde", "qual", "quais", "isso", "este", "esta",
            "esse", "essa", "aquele", "aquela", "ser", "estar", "ter", "haver",
            "fazer", "ir", "vir", "ver", "poder", "dever", "querer", "saber"
        }

        # Tokenizar e contar
        words = content.lower().split()
        word_count = defaultdict(int)

        for word in words:
            # Limpar pontuação
            word = ''.join(c for c in word if c.isalnum())
            if len(word) > 3 and word not in stopwords:
                word_count[word] += 1

        # Retornar mais frequentes
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_keywords]]

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas da base"""
        category_counts = defaultdict(int)
        status_counts = defaultdict(int)

        for item in self._items.values():
            category_counts[item.category.value] += 1
            status_counts[item.status.value] += 1

        return {
            "total_items": len(self._items),
            "active_items": status_counts.get("active", 0),
            "by_category": dict(category_counts),
            "by_status": dict(status_counts),
            "total_keywords": len(self._by_keyword),
            "total_tags": len(self._by_tag),
        }
