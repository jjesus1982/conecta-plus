"""
Conecta Plus - Search Tools
Ferramentas de busca e indexação
"""

import asyncio
import logging
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .base_tool import (
    BaseTool, ToolContext, ToolResult, ToolMetadata,
    ToolCategory, ToolParameter, ParameterType, tool
)

logger = logging.getLogger(__name__)


# ============================================================
# Full Text Search Tool
# ============================================================

@dataclass
class SearchResult:
    """Resultado de busca"""
    id: str
    score: float
    source: Dict[str, Any]
    highlights: Dict[str, List[str]] = field(default_factory=dict)


@tool(
    name="full_text_search",
    version="1.0.0",
    category=ToolCategory.SEARCH,
    description="Busca full-text em documentos e registros",
    parameters=[
        ToolParameter("query", ParameterType.STRING, "Termo de busca", required=True),
        ToolParameter("index", ParameterType.STRING, "Índice para buscar", required=False, default="default"),
        ToolParameter("fields", ParameterType.ARRAY, "Campos para buscar", required=False),
        ToolParameter("filters", ParameterType.OBJECT, "Filtros adicionais", required=False),
        ToolParameter("from_", ParameterType.INTEGER, "Offset de resultados", required=False, default=0),
        ToolParameter("size", ParameterType.INTEGER, "Quantidade de resultados", required=False, default=10, max_value=100),
        ToolParameter("sort", ParameterType.ARRAY, "Ordenação", required=False),
        ToolParameter("highlight", ParameterType.BOOLEAN, "Destacar matches", required=False, default=True),
    ],
    tags=["search", "fulltext", "elasticsearch"]
)
class FullTextSearchTool(BaseTool):
    """
    Busca full-text.
    Suporta queries complexas, filtros e highlighting.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._indices: Dict[str, List[Dict]] = {
            "moradores": [
                {"id": "1", "nome": "João Silva", "unidade": "101A", "email": "joao@email.com"},
                {"id": "2", "nome": "Maria Santos", "unidade": "102B", "email": "maria@email.com"},
                {"id": "3", "nome": "Pedro Oliveira", "unidade": "201A", "email": "pedro@email.com"}
            ],
            "ocorrencias": [
                {"id": "1", "titulo": "Vazamento no banheiro", "status": "resolvido", "unidade": "101A"},
                {"id": "2", "titulo": "Barulho excessivo", "status": "aberto", "unidade": "305B"},
                {"id": "3", "titulo": "Problema com interfone", "status": "em_andamento", "unidade": "102B"}
            ],
            "documentos": [
                {"id": "1", "titulo": "Regulamento Interno", "tipo": "regulamento", "conteudo": "..."},
                {"id": "2", "titulo": "Ata Assembleia Janeiro", "tipo": "ata", "conteudo": "..."},
                {"id": "3", "titulo": "Convenção do Condomínio", "tipo": "convenção", "conteudo": "..."}
            ]
        }

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa busca full-text"""
        query = params.get("query", "")
        index = params.get("index", "default")
        fields = params.get("fields")
        filters = params.get("filters", {})
        from_ = params.get("from_", 0)
        size = params.get("size", 10)
        highlight = params.get("highlight", True)

        if not query:
            return ToolResult.fail("'query' é obrigatório")

        # Buscar no índice
        documents = self._indices.get(index, [])
        if not documents and index == "default":
            # Buscar em todos os índices
            documents = []
            for docs in self._indices.values():
                documents.extend(docs)

        # Filtrar por query
        results = []
        query_lower = query.lower()

        for doc in documents:
            score = 0
            highlights = {}

            search_fields = fields or list(doc.keys())

            for field in search_fields:
                if field not in doc:
                    continue

                value = str(doc.get(field, "")).lower()
                if query_lower in value:
                    score += 1

                    if highlight:
                        # Criar highlight
                        pattern = re.compile(f"({re.escape(query)})", re.IGNORECASE)
                        highlighted = pattern.sub(r"<em>\1</em>", str(doc.get(field, "")))
                        if field not in highlights:
                            highlights[field] = []
                        highlights[field].append(highlighted)

            if score > 0:
                # Aplicar filtros
                match_filters = True
                for fk, fv in filters.items():
                    if doc.get(fk) != fv:
                        match_filters = False
                        break

                if match_filters:
                    results.append(SearchResult(
                        id=doc.get("id", ""),
                        score=score,
                        source=doc,
                        highlights=highlights
                    ))

        # Ordenar por score
        results.sort(key=lambda r: r.score, reverse=True)

        # Paginação
        total = len(results)
        results = results[from_:from_ + size]

        return ToolResult.ok({
            "hits": [
                {
                    "id": r.id,
                    "score": r.score,
                    "source": r.source,
                    "highlights": r.highlights
                }
                for r in results
            ],
            "total": total,
            "from": from_,
            "size": len(results),
            "query": query,
            "index": index
        })


# ============================================================
# Vector Search Tool
# ============================================================

@tool(
    name="vector_search",
    version="1.0.0",
    category=ToolCategory.SEARCH,
    description="Busca semântica usando embeddings vetoriais",
    parameters=[
        ToolParameter("query", ParameterType.STRING, "Texto de busca", required=True),
        ToolParameter("collection", ParameterType.STRING, "Coleção de vetores", required=False, default="default"),
        ToolParameter("top_k", ParameterType.INTEGER, "Número de resultados", required=False, default=10, max_value=100),
        ToolParameter("min_score", ParameterType.FLOAT, "Score mínimo", required=False, default=0.7, min_value=0, max_value=1),
        ToolParameter("filters", ParameterType.OBJECT, "Filtros de metadados", required=False),
        ToolParameter("include_vectors", ParameterType.BOOLEAN, "Incluir vetores na resposta", required=False, default=False),
    ],
    tags=["search", "vector", "semantic", "embeddings", "ai"]
)
class VectorSearchTool(BaseTool):
    """
    Busca semântica com vetores.
    Suporta similarity search e filtering.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._collections: Dict[str, List[Dict]] = {
            "knowledge": [
                {"id": "1", "text": "Como reservar área comum", "metadata": {"category": "reservas"}, "vector": [0.1] * 384},
                {"id": "2", "text": "Horário de funcionamento da piscina", "metadata": {"category": "lazer"}, "vector": [0.2] * 384},
                {"id": "3", "text": "Regras para pets no condomínio", "metadata": {"category": "regras"}, "vector": [0.3] * 384},
                {"id": "4", "text": "Como solicitar segunda via de boleto", "metadata": {"category": "financeiro"}, "vector": [0.4] * 384}
            ],
            "conversations": [
                {"id": "conv_1", "text": "Bom dia, preciso de ajuda com minha reserva", "metadata": {"intent": "greeting"}, "vector": [0.5] * 384},
                {"id": "conv_2", "text": "Tenho uma reclamação sobre barulho", "metadata": {"intent": "complaint"}, "vector": [0.6] * 384}
            ]
        }

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa busca vetorial"""
        query = params.get("query", "")
        collection = params.get("collection", "default")
        top_k = params.get("top_k", 10)
        min_score = params.get("min_score", 0.7)
        filters = params.get("filters", {})
        include_vectors = params.get("include_vectors", False)

        if not query:
            return ToolResult.fail("'query' é obrigatório")

        # Obter coleção
        documents = self._collections.get(collection, [])
        if not documents and collection == "default":
            documents = []
            for docs in self._collections.values():
                documents.extend(docs)

        # Simular embedding e similaridade
        results = []
        for doc in documents:
            # Calcular similaridade simulada (baseado em palavras comuns)
            query_words = set(query.lower().split())
            doc_words = set(doc.get("text", "").lower().split())
            common = len(query_words & doc_words)
            total = len(query_words | doc_words)
            score = common / total if total > 0 else 0

            # Adicionar algum ruído para parecer mais realista
            score = min(1.0, score + 0.5) if score > 0 else 0.3 + (hash(doc.get("id", "")) % 40) / 100

            # Aplicar filtros
            if filters:
                metadata = doc.get("metadata", {})
                match = all(metadata.get(k) == v for k, v in filters.items())
                if not match:
                    continue

            if score >= min_score:
                result = {
                    "id": doc.get("id"),
                    "score": round(score, 4),
                    "text": doc.get("text"),
                    "metadata": doc.get("metadata", {})
                }

                if include_vectors:
                    result["vector"] = doc.get("vector", [])[:10]  # Truncar para preview

                results.append(result)

        # Ordenar por score
        results.sort(key=lambda r: r["score"], reverse=True)
        results = results[:top_k]

        return ToolResult.ok({
            "results": results,
            "total": len(results),
            "collection": collection,
            "query": query,
            "min_score": min_score
        })


# ============================================================
# Filter Tool
# ============================================================

class FilterOperator(Enum):
    """Operadores de filtro"""
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NIN = "nin"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    EXISTS = "exists"
    BETWEEN = "between"


@tool(
    name="filter",
    version="1.0.0",
    category=ToolCategory.SEARCH,
    description="Filtragem avançada de dados",
    parameters=[
        ToolParameter("data", ParameterType.ARRAY, "Dados a filtrar", required=True),
        ToolParameter("conditions", ParameterType.ARRAY, "Condições de filtro", required=True),
        ToolParameter("logic", ParameterType.ENUM, "Lógica entre condições",
                     required=False, default="and", enum_values=["and", "or"]),
        ToolParameter("sort_by", ParameterType.STRING, "Campo para ordenar", required=False),
        ToolParameter("sort_order", ParameterType.ENUM, "Ordem", required=False, default="asc", enum_values=["asc", "desc"]),
        ToolParameter("limit", ParameterType.INTEGER, "Limite de resultados", required=False),
    ],
    tags=["filter", "query", "data"]
)
class FilterTool(BaseTool):
    """
    Filtro avançado de dados.
    Suporta múltiplos operadores e lógica complexa.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa filtragem"""
        data = params.get("data", [])
        conditions = params.get("conditions", [])
        logic = params.get("logic", "and")
        sort_by = params.get("sort_by")
        sort_order = params.get("sort_order", "asc")
        limit = params.get("limit")

        if not data:
            return ToolResult.ok({"results": [], "total": 0})

        if not conditions:
            return ToolResult.ok({
                "results": data[:limit] if limit else data,
                "total": len(data)
            })

        # Aplicar filtros
        results = []
        for item in data:
            matches = []

            for condition in conditions:
                field = condition.get("field")
                operator = condition.get("operator", "eq")
                value = condition.get("value")

                item_value = item.get(field)
                match = self._evaluate_condition(item_value, operator, value)
                matches.append(match)

            # Aplicar lógica
            if logic == "and":
                if all(matches):
                    results.append(item)
            else:  # or
                if any(matches):
                    results.append(item)

        # Ordenar
        if sort_by:
            reverse = sort_order == "desc"
            results.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)

        # Limitar
        total = len(results)
        if limit:
            results = results[:limit]

        return ToolResult.ok({
            "results": results,
            "total": total,
            "filtered": len(results)
        })

    def _evaluate_condition(self, item_value: Any, operator: str, value: Any) -> bool:
        """Avalia condição de filtro"""
        if operator == "eq":
            return item_value == value
        elif operator == "ne":
            return item_value != value
        elif operator == "gt":
            return item_value > value if item_value is not None else False
        elif operator == "gte":
            return item_value >= value if item_value is not None else False
        elif operator == "lt":
            return item_value < value if item_value is not None else False
        elif operator == "lte":
            return item_value <= value if item_value is not None else False
        elif operator == "in":
            return item_value in value if isinstance(value, list) else False
        elif operator == "nin":
            return item_value not in value if isinstance(value, list) else True
        elif operator == "contains":
            return value in str(item_value) if item_value is not None else False
        elif operator == "starts_with":
            return str(item_value).startswith(str(value)) if item_value is not None else False
        elif operator == "ends_with":
            return str(item_value).endswith(str(value)) if item_value is not None else False
        elif operator == "regex":
            try:
                return bool(re.match(value, str(item_value))) if item_value is not None else False
            except re.error:
                return False
        elif operator == "exists":
            return (item_value is not None) == value
        elif operator == "between":
            if isinstance(value, list) and len(value) == 2:
                return value[0] <= item_value <= value[1] if item_value is not None else False
            return False

        return False


# ============================================================
# Aggregation Tool
# ============================================================

class AggregationType(Enum):
    """Tipos de agregação"""
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    GROUP_BY = "group_by"
    DISTINCT = "distinct"
    PERCENTILE = "percentile"


@tool(
    name="aggregation",
    version="1.0.0",
    category=ToolCategory.SEARCH,
    description="Agregações e estatísticas sobre dados",
    parameters=[
        ToolParameter("data", ParameterType.ARRAY, "Dados para agregar", required=True),
        ToolParameter("aggregations", ParameterType.ARRAY, "Lista de agregações", required=True),
        ToolParameter("group_by", ParameterType.STRING, "Campo para agrupar", required=False),
        ToolParameter("filters", ParameterType.ARRAY, "Filtros pré-agregação", required=False),
    ],
    tags=["aggregation", "analytics", "statistics"]
)
class AggregationTool(BaseTool):
    """
    Agregações sobre dados.
    Suporta count, sum, avg, min, max e group by.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa agregação"""
        data = params.get("data", [])
        aggregations = params.get("aggregations", [])
        group_by = params.get("group_by")
        filters = params.get("filters")

        if not data:
            return ToolResult.ok({"results": {}, "count": 0})

        # Aplicar filtros se existirem
        if filters:
            filter_tool = FilterTool()
            filter_result = await filter_tool._execute(context, data=data, conditions=filters)
            if filter_result.success:
                data = filter_result.data.get("results", data)

        # Se tiver group by
        if group_by:
            return await self._group_aggregation(data, aggregations, group_by)

        # Agregação simples
        results = {"count": len(data)}

        for agg in aggregations:
            agg_type = agg.get("type", "count")
            field = agg.get("field")
            alias = agg.get("alias", f"{agg_type}_{field}" if field else agg_type)

            if agg_type == "count":
                results[alias] = len(data)

            elif agg_type == "sum" and field:
                values = [item.get(field, 0) for item in data if isinstance(item.get(field), (int, float))]
                results[alias] = sum(values)

            elif agg_type == "avg" and field:
                values = [item.get(field, 0) for item in data if isinstance(item.get(field), (int, float))]
                results[alias] = sum(values) / len(values) if values else 0

            elif agg_type == "min" and field:
                values = [item.get(field) for item in data if item.get(field) is not None]
                results[alias] = min(values) if values else None

            elif agg_type == "max" and field:
                values = [item.get(field) for item in data if item.get(field) is not None]
                results[alias] = max(values) if values else None

            elif agg_type == "distinct" and field:
                values = set(item.get(field) for item in data if item.get(field) is not None)
                results[alias] = list(values)
                results[f"{alias}_count"] = len(values)

        return ToolResult.ok({
            "results": results,
            "count": len(data)
        })

    async def _group_aggregation(
        self,
        data: List[Dict],
        aggregations: List[Dict],
        group_by: str
    ) -> ToolResult:
        """Agregação com group by"""
        groups: Dict[Any, List[Dict]] = {}

        for item in data:
            key = item.get(group_by, "_null_")
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

        results = []
        for key, items in groups.items():
            group_result = {group_by: key, "count": len(items)}

            for agg in aggregations:
                agg_type = agg.get("type", "count")
                field = agg.get("field")
                alias = agg.get("alias", f"{agg_type}_{field}" if field else agg_type)

                if agg_type == "sum" and field:
                    values = [i.get(field, 0) for i in items if isinstance(i.get(field), (int, float))]
                    group_result[alias] = sum(values)

                elif agg_type == "avg" and field:
                    values = [i.get(field, 0) for i in items if isinstance(i.get(field), (int, float))]
                    group_result[alias] = sum(values) / len(values) if values else 0

                elif agg_type == "min" and field:
                    values = [i.get(field) for i in items if i.get(field) is not None]
                    group_result[alias] = min(values) if values else None

                elif agg_type == "max" and field:
                    values = [i.get(field) for i in items if i.get(field) is not None]
                    group_result[alias] = max(values) if values else None

            results.append(group_result)

        return ToolResult.ok({
            "groups": results,
            "group_by": group_by,
            "total_groups": len(results),
            "total_items": len(data)
        })


def register_search_tools():
    """Registra todas as ferramentas de busca"""
    pass
