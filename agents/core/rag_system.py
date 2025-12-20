"""
Conecta Plus - RAG System
Sistema de Retrieval Augmented Generation para agentes

Componentes:
- DocumentProcessor: Processa e chunka documentos
- Retriever: Busca documentos relevantes
- RAGPipeline: Pipeline completo de RAG
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import json
import logging
import hashlib
import re

from .memory_store import VectorMemoryStore
from .llm_client import UnifiedLLMClient, LLMMessage

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Tipos de documentos suportados"""
    TEXT = "text"
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    CODE = "code"
    CONVERSATION = "conversation"


@dataclass
class Document:
    """Documento para indexação"""
    doc_id: str
    content: str
    doc_type: DocumentType
    title: str = ""
    source: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """Pedaço de documento"""
    chunk_id: str
    doc_id: str
    content: str
    index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Resultado de retrieval"""
    chunk: Chunk
    score: float
    document: Optional[Document] = None


@dataclass
class RAGResponse:
    """Resposta do sistema RAG"""
    answer: str
    sources: List[RetrievalResult]
    context_used: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentProcessor:
    """Processa e chunka documentos para indexação"""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def process(self, document: Document) -> List[Chunk]:
        """Processa documento e retorna chunks"""
        content = document.content

        # Pré-processar baseado no tipo
        if document.doc_type == DocumentType.HTML:
            content = self._strip_html(content)
        elif document.doc_type == DocumentType.CODE:
            return self._chunk_code(document)
        elif document.doc_type == DocumentType.CONVERSATION:
            return self._chunk_conversation(document)

        # Chunking padrão por sentenças
        return self._chunk_by_sentences(document, content)

    def _strip_html(self, html: str) -> str:
        """Remove tags HTML mantendo texto"""
        # Remover scripts e styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        # Remover tags
        html = re.sub(r'<[^>]+>', ' ', html)
        # Limpar espaços
        html = re.sub(r'\s+', ' ', html)
        return html.strip()

    def _chunk_by_sentences(self, document: Document, content: str) -> List[Chunk]:
        """Chunka por sentenças respeitando tamanho"""
        chunks = []

        # Dividir em sentenças
        sentences = re.split(r'(?<=[.!?])\s+', content)

        current_chunk = ""
        current_start = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence + " "
            else:
                # Salvar chunk atual
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(self._create_chunk(
                        document,
                        current_chunk.strip(),
                        len(chunks),
                        current_start
                    ))

                # Começar novo chunk com overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                current_start = current_start + len(current_chunk) - len(overlap_text)
                current_chunk = overlap_text + sentence + " "

        # Último chunk
        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(self._create_chunk(
                document,
                current_chunk.strip(),
                len(chunks),
                current_start
            ))

        return chunks

    def _chunk_code(self, document: Document) -> List[Chunk]:
        """Chunka código por funções/classes"""
        content = document.content
        chunks = []

        # Padrões para Python
        patterns = [
            r'(class\s+\w+.*?(?=\nclass|\ndef|\Z))',
            r'(def\s+\w+.*?(?=\ndef|\nclass|\Z))',
        ]

        code_blocks = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            code_blocks.extend(matches)

        if not code_blocks:
            # Fallback: chunking padrão
            return self._chunk_by_sentences(document, content)

        for i, block in enumerate(code_blocks):
            if len(block.strip()) >= self.min_chunk_size:
                start = content.find(block)
                chunks.append(self._create_chunk(
                    document,
                    block.strip(),
                    i,
                    start
                ))

        return chunks

    def _chunk_conversation(self, document: Document) -> List[Chunk]:
        """Chunka conversação mantendo contexto"""
        content = document.content
        chunks = []

        # Dividir por turnos
        turns = re.split(r'\n(?=(?:Usuário|User|Assistente|Assistant|Sistema|System):)', content)

        current_chunk = ""
        current_start = 0

        for turn in turns:
            if len(current_chunk) + len(turn) <= self.chunk_size:
                current_chunk += turn + "\n"
            else:
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(self._create_chunk(
                        document,
                        current_chunk.strip(),
                        len(chunks),
                        current_start
                    ))
                current_start = current_start + len(current_chunk)
                current_chunk = turn + "\n"

        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(self._create_chunk(
                document,
                current_chunk.strip(),
                len(chunks),
                current_start
            ))

        return chunks

    def _create_chunk(
        self,
        document: Document,
        content: str,
        index: int,
        start_char: int
    ) -> Chunk:
        """Cria objeto Chunk"""
        chunk_id = hashlib.sha256(
            f"{document.doc_id}:{index}:{content[:50]}".encode()
        ).hexdigest()[:16]

        return Chunk(
            chunk_id=chunk_id,
            doc_id=document.doc_id,
            content=content,
            index=index,
            start_char=start_char,
            end_char=start_char + len(content),
            metadata={
                "doc_title": document.title,
                "doc_source": document.source,
                "doc_type": document.doc_type.value,
                **document.metadata
            }
        )


class Retriever:
    """Busca documentos relevantes no vector store"""

    def __init__(
        self,
        vector_store: VectorMemoryStore,
        default_top_k: int = 5,
        min_score: float = 0.5
    ):
        self.vector_store = vector_store
        self.default_top_k = default_top_k
        self.min_score = min_score
        self._documents: Dict[str, Document] = {}
        self._chunks: Dict[str, Chunk] = {}

    async def index_document(self, document: Document, processor: DocumentProcessor = None) -> int:
        """Indexa documento no vector store"""
        processor = processor or DocumentProcessor()

        # Processar em chunks
        chunks = processor.process(document)

        # Armazenar documento
        self._documents[document.doc_id] = document

        # Indexar cada chunk
        indexed = 0
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

            success = await self.vector_store.store(
                agent_id="rag_system",
                content=chunk.content,
                metadata={
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "index": chunk.index,
                    **chunk.metadata
                },
                doc_id=chunk.chunk_id
            )

            if success:
                indexed += 1

        logger.info(f"Documento {document.doc_id} indexado: {indexed}/{len(chunks)} chunks")
        return indexed

    async def retrieve(
        self,
        query: str,
        top_k: int = None,
        filter_metadata: Dict[str, Any] = None
    ) -> List[RetrievalResult]:
        """Busca chunks relevantes para a query"""
        top_k = top_k or self.default_top_k

        # Buscar no vector store
        results = await self.vector_store.search(
            agent_id="rag_system",
            query=query,
            limit=top_k * 2,  # Buscar mais para filtrar
            filter_metadata=filter_metadata
        )

        # Converter para RetrievalResults
        retrieval_results = []
        for result in results:
            chunk_id = result.get("metadata", {}).get("chunk_id")
            doc_id = result.get("metadata", {}).get("doc_id")

            # Calcular score (1 - distance)
            distance = result.get("distance", 0)
            score = 1 - distance if distance else 0.8

            if score < self.min_score:
                continue

            # Criar chunk se não existir no cache
            chunk = self._chunks.get(chunk_id) or Chunk(
                chunk_id=chunk_id or "unknown",
                doc_id=doc_id or "unknown",
                content=result.get("content", ""),
                index=result.get("metadata", {}).get("index", 0),
                start_char=0,
                end_char=len(result.get("content", "")),
                metadata=result.get("metadata", {})
            )

            document = self._documents.get(doc_id)

            retrieval_results.append(RetrievalResult(
                chunk=chunk,
                score=score,
                document=document
            ))

        # Ordenar por score e limitar
        retrieval_results.sort(key=lambda x: x.score, reverse=True)
        return retrieval_results[:top_k]

    async def hybrid_retrieve(
        self,
        query: str,
        top_k: int = None,
        keyword_weight: float = 0.3
    ) -> List[RetrievalResult]:
        """
        Busca híbrida combinando semântica e keywords.
        Melhora resultados para termos específicos.
        """
        # Busca semântica
        semantic_results = await self.retrieve(query, top_k=top_k)

        # Extrair keywords da query
        keywords = self._extract_keywords(query)

        if not keywords:
            return semantic_results

        # Reranking baseado em keywords
        for result in semantic_results:
            keyword_score = self._calculate_keyword_score(result.chunk.content, keywords)
            # Combinar scores
            result.score = (1 - keyword_weight) * result.score + keyword_weight * keyword_score

        # Reordenar
        semantic_results.sort(key=lambda x: x.score, reverse=True)
        return semantic_results

    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai keywords importantes do texto"""
        # Remover stopwords comuns em português
        stopwords = {
            'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas',
            'de', 'da', 'do', 'das', 'dos', 'em', 'na', 'no', 'nas', 'nos',
            'por', 'para', 'com', 'sem', 'que', 'qual', 'quando', 'como',
            'e', 'ou', 'mas', 'se', 'não', 'sim', 'é', 'são', 'foi', 'ser'
        }

        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]

        return keywords

    def _calculate_keyword_score(self, content: str, keywords: List[str]) -> float:
        """Calcula score baseado em presença de keywords"""
        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)
        return matches / len(keywords) if keywords else 0


class RAGPipeline:
    """
    Pipeline completo de RAG (Retrieval Augmented Generation).
    Combina retriever e LLM para respostas contextualizadas.
    """

    def __init__(
        self,
        retriever: Retriever,
        llm_client: UnifiedLLMClient,
        max_context_tokens: int = 3000,
        include_sources: bool = True
    ):
        self.retriever = retriever
        self.llm = llm_client
        self.max_context_tokens = max_context_tokens
        self.include_sources = include_sources

    async def query(
        self,
        question: str,
        system_context: str = "",
        top_k: int = 5,
        temperature: float = 0.3,
        filter_metadata: Dict[str, Any] = None
    ) -> RAGResponse:
        """
        Executa query RAG completa.

        Args:
            question: Pergunta do usuário
            system_context: Contexto adicional do sistema
            top_k: Número de chunks a recuperar
            temperature: Temperatura para geração
            filter_metadata: Filtros para retrieval

        Returns:
            RAGResponse com resposta e fontes
        """
        # 1. Retrieval
        results = await self.retriever.hybrid_retrieve(
            query=question,
            top_k=top_k
        )

        if not results:
            return RAGResponse(
                answer="Não encontrei informações relevantes para responder sua pergunta.",
                sources=[],
                context_used="",
                confidence=0.0,
                metadata={"no_results": True}
            )

        # 2. Construir contexto
        context = self._build_context(results)

        # 3. Gerar resposta
        system_prompt = self._build_system_prompt(system_context)
        user_prompt = self._build_user_prompt(question, context)

        answer = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature
        )

        # 4. Calcular confiança
        confidence = self._calculate_confidence(results, answer)

        return RAGResponse(
            answer=answer,
            sources=results,
            context_used=context,
            confidence=confidence,
            metadata={
                "chunks_used": len(results),
                "avg_score": sum(r.score for r in results) / len(results)
            }
        )

    def _build_context(self, results: List[RetrievalResult]) -> str:
        """Constrói contexto a partir dos resultados"""
        context_parts = []
        total_chars = 0

        for i, result in enumerate(results, 1):
            chunk_text = f"[Fonte {i}]\n{result.chunk.content}"

            # Estimar tokens (aproximação: 4 chars = 1 token)
            estimated_tokens = len(chunk_text) / 4
            if total_chars / 4 + estimated_tokens > self.max_context_tokens:
                break

            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        return "\n\n".join(context_parts)

    def _build_system_prompt(self, additional_context: str = "") -> str:
        """Constrói system prompt para RAG"""
        base_prompt = """Você é um assistente especializado do sistema Conecta Plus para gestão condominial.

Sua tarefa é responder perguntas usando APENAS as informações fornecidas no contexto.

Regras:
1. Responda em português brasileiro
2. Use apenas informações do contexto fornecido
3. Se a informação não estiver no contexto, diga que não encontrou
4. Cite as fontes quando relevante (ex: "De acordo com a Fonte 1...")
5. Seja conciso e direto
6. Mantenha tom profissional

"""
        if additional_context:
            base_prompt += f"\nContexto adicional: {additional_context}\n"

        return base_prompt

    def _build_user_prompt(self, question: str, context: str) -> str:
        """Constrói prompt do usuário com contexto"""
        return f"""Contexto:
{context}

---

Pergunta: {question}

Responda baseado apenas no contexto acima:"""

    def _calculate_confidence(self, results: List[RetrievalResult], answer: str) -> float:
        """Calcula confiança da resposta"""
        if not results:
            return 0.0

        # Fatores de confiança
        avg_retrieval_score = sum(r.score for r in results) / len(results)

        # Verificar se resposta usa informações do contexto
        context_overlap = 0
        answer_words = set(answer.lower().split())
        for result in results:
            chunk_words = set(result.chunk.content.lower().split())
            overlap = len(answer_words & chunk_words) / max(len(answer_words), 1)
            context_overlap = max(context_overlap, overlap)

        # Combinar fatores
        confidence = (avg_retrieval_score * 0.5) + (context_overlap * 0.5)

        return min(confidence, 1.0)

    async def index_documents(
        self,
        documents: List[Document],
        processor: DocumentProcessor = None
    ) -> Dict[str, int]:
        """Indexa múltiplos documentos"""
        processor = processor or DocumentProcessor()
        results = {}

        for doc in documents:
            indexed = await self.retriever.index_document(doc, processor)
            results[doc.doc_id] = indexed

        return results


class ConversationalRAG(RAGPipeline):
    """
    RAG com memória de conversação.
    Mantém contexto entre perguntas.
    """

    def __init__(self, *args, max_history: int = 5, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_history = max_history
        self._history: Dict[str, List[Dict[str, str]]] = {}

    async def chat(
        self,
        session_id: str,
        question: str,
        **kwargs
    ) -> RAGResponse:
        """Chat com histórico"""
        # Obter histórico
        history = self._history.get(session_id, [])

        # Expandir query com contexto do histórico
        expanded_query = self._expand_query_with_history(question, history)

        # RAG normal
        response = await self.query(expanded_query, **kwargs)

        # Atualizar histórico
        if session_id not in self._history:
            self._history[session_id] = []

        self._history[session_id].append({
            "question": question,
            "answer": response.answer
        })

        # Manter apenas últimas N interações
        if len(self._history[session_id]) > self.max_history:
            self._history[session_id] = self._history[session_id][-self.max_history:]

        return response

    def _expand_query_with_history(
        self,
        question: str,
        history: List[Dict[str, str]]
    ) -> str:
        """Expande query incorporando histórico relevante"""
        if not history:
            return question

        # Verificar se pergunta faz referência a histórico
        reference_words = ['isso', 'esse', 'essa', 'ele', 'ela', 'anterior', 'último', 'aquilo']
        question_lower = question.lower()

        has_reference = any(word in question_lower for word in reference_words)

        if not has_reference:
            return question

        # Adicionar contexto do histórico
        recent = history[-2:] if len(history) >= 2 else history
        context = " ".join([h["question"] + " " + h["answer"][:100] for h in recent])

        return f"Contexto anterior: {context}\n\nPergunta atual: {question}"

    def clear_history(self, session_id: str) -> None:
        """Limpa histórico da sessão"""
        if session_id in self._history:
            del self._history[session_id]


# Factory functions
def create_rag_system(
    vector_store: VectorMemoryStore = None,
    llm_client: UnifiedLLMClient = None,
    conversational: bool = False
) -> RAGPipeline:
    """
    Cria sistema RAG configurado.

    Args:
        vector_store: Vector store para embeddings
        llm_client: Cliente LLM
        conversational: Se True, cria ConversationalRAG

    Returns:
        Sistema RAG configurado
    """
    vector_store = vector_store or VectorMemoryStore()
    llm_client = llm_client or UnifiedLLMClient()

    retriever = Retriever(vector_store)

    if conversational:
        return ConversationalRAG(retriever, llm_client)

    return RAGPipeline(retriever, llm_client)


async def quick_index(
    content: str,
    title: str = "",
    doc_type: DocumentType = DocumentType.TEXT,
    rag_system: RAGPipeline = None
) -> str:
    """Indexa conteúdo rapidamente"""
    doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    document = Document(
        doc_id=doc_id,
        content=content,
        doc_type=doc_type,
        title=title
    )

    rag = rag_system or create_rag_system()
    await rag.index_documents([document])

    return doc_id
