"""
Conecta Plus - Agente Conhecimento (Nível 7)
Base de conhecimento inteligente com RAG

Capacidades:
1. REATIVO: Responder perguntas, buscar informações
2. PROATIVO: Sugerir conteúdos, atualizar base
3. PREDITIVO: Prever dúvidas, antecipar necessidades
4. AUTÔNOMO: Atualizar conhecimento, criar FAQs
5. EVOLUTIVO: Aprender com interações, melhorar respostas
6. COLABORATIVO: Integrar todos os agentes como fonte
7. TRANSCENDENTE: Central de conhecimento completa
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.base_agent import (
    BaseAgent, EvolutionLevel, Priority, AgentCapability,
    AgentContext, AgentAction, AgentPrediction,
)
from ..core.memory_store import UnifiedMemorySystem
from ..core.llm_client import UnifiedLLMClient
from ..core.tools import ToolRegistry
from ..core.rag_system import RAGPipeline

logger = logging.getLogger(__name__)


class CategoriaConhecimento(Enum):
    REGULAMENTO = "regulamento"
    CONVENCAO = "convencao"
    PROCEDIMENTO = "procedimento"
    FAQ = "faq"
    SERVICO = "servico"
    CONTATO = "contato"
    TUTORIAL = "tutorial"
    POLITICA = "politica"
    FORMULARIO = "formulario"
    GERAL = "geral"


class TipoDocumento(Enum):
    PDF = "pdf"
    TEXTO = "texto"
    MARKDOWN = "markdown"
    HTML = "html"
    VIDEO = "video"


class StatusDocumento(Enum):
    ATIVO = "ativo"
    REVISAO = "revisao"
    ARQUIVADO = "arquivado"
    RASCUNHO = "rascunho"


@dataclass
class DocumentoConhecimento:
    id: str
    titulo: str
    categoria: CategoriaConhecimento
    tipo: TipoDocumento
    conteudo: str
    resumo: str
    tags: List[str]
    status: StatusDocumento
    data_criacao: datetime
    data_atualizacao: datetime
    autor: str
    versao: int = 1
    visualizacoes: int = 0
    utilidade_media: float = 0
    embeddings: Optional[List[float]] = None


@dataclass
class PerguntaFrequente:
    id: str
    pergunta: str
    resposta: str
    categoria: CategoriaConhecimento
    visualizacoes: int = 0
    util_sim: int = 0
    util_nao: int = 0
    data_criacao: datetime = field(default_factory=datetime.now)
    ativo: bool = True


@dataclass
class BuscaHistorico:
    id: str
    termo: str
    usuario_id: Optional[str]
    timestamp: datetime
    resultados_encontrados: int
    documento_acessado: Optional[str] = None


@dataclass
class FeedbackConhecimento:
    id: str
    documento_id: str
    usuario_id: str
    tipo: str  # util, nao_util, sugestao
    comentario: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class AgenteConhecimento(BaseAgent):
    """Agente Conhecimento - Base de Conhecimento Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        rag: RAGPipeline = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"conhecimento_{condominio_id}",
            agent_type="conhecimento",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self.rag = rag

        self._documentos: Dict[str, DocumentoConhecimento] = {}
        self._faqs: Dict[str, PerguntaFrequente] = {}
        self._historico_buscas: List[BuscaHistorico] = []
        self._feedbacks: List[FeedbackConhecimento] = []
        self._sinonimos: Dict[str, List[str]] = {}

        self.config = {
            "max_resultados_busca": 10,
            "score_minimo_relevancia": 0.5,
            "auto_sugerir_faq": True,
            "gerar_resumo_automatico": True,
        }

        self._inicializar_base()

    def _inicializar_base(self):
        """Inicializar base de conhecimento padrão"""
        # FAQs comuns
        faqs_padrao = [
            ("Como faço para reservar o salão de festas?",
             "Acesse o app Conecta Plus, vá em 'Reservas' > 'Salão de Festas', escolha a data desejada e confirme. Pagamento do caução pode ser feito via PIX.",
             "servico"),
            ("Qual o horário de funcionamento da piscina?",
             "A piscina funciona diariamente das 6h às 22h. Aos domingos e feriados, das 8h às 20h.",
             "servico"),
            ("Como cadastrar um visitante?",
             "No app, acesse 'Visitantes' > 'Pré-cadastrar'. Informe nome, documento e data da visita. O visitante receberá um QR Code para entrada.",
             "procedimento"),
            ("Como reportar um problema de manutenção?",
             "Use o app para abrir uma ocorrência em 'Manutenção' > 'Nova Solicitação'. Descreva o problema e anexe fotos se possível.",
             "procedimento"),
            ("Quando é a assembleia geral?",
             "A Assembleia Geral Ordinária ocorre anualmente no primeiro trimestre. Assembleias extraordinárias são convocadas conforme necessidade. Confira o calendário no app.",
             "geral"),
            ("Posso ter animais de estimação?",
             "Sim, desde que cadastrados junto à administração. Consulte o regulamento de pets para conhecer as regras de convivência.",
             "regulamento"),
            ("Como trocar a senha do WiFi das áreas comuns?",
             "A senha do WiFi é atualizada mensalmente. Confira a nova senha no app em 'Serviços' > 'WiFi' ou com a portaria.",
             "servico"),
            ("Qual o valor da taxa condominial?",
             "O valor varia conforme a fração ideal de cada unidade. Consulte seu boleto mensal ou acesse 'Financeiro' no app.",
             "faq"),
        ]

        for pergunta, resposta, categoria in faqs_padrao:
            faq = PerguntaFrequente(
                id=f"faq_{len(self._faqs)}",
                pergunta=pergunta,
                resposta=resposta,
                categoria=CategoriaConhecimento[categoria.upper()]
            )
            self._faqs[faq.id] = faq

        # Sinônimos para melhorar busca
        self._sinonimos = {
            "salao": ["salão", "festa", "eventos", "churrasqueira"],
            "piscina": ["natacao", "natação", "banho"],
            "estacionamento": ["garagem", "vaga", "carro"],
            "portaria": ["porteiro", "entrada", "recepção"],
            "manutencao": ["manutenção", "conserto", "reparo", "problema"],
            "taxa": ["condomínio", "boleto", "pagamento", "mensalidade"],
            "animal": ["pet", "cachorro", "gato", "bicho"],
            "visitante": ["visita", "convidado", "hóspede"],
        }

    def _register_capabilities(self) -> None:
        self._capabilities["buscar_conhecimento"] = AgentCapability(
            name="buscar_conhecimento", description="Buscar na base de conhecimento",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["responder_perguntas"] = AgentCapability(
            name="responder_perguntas", description="Responder perguntas usando RAG",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["gerenciar_documentos"] = AgentCapability(
            name="gerenciar_documentos", description="Gerenciar documentos da base",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["central_conhecimento"] = AgentCapability(
            name="central_conhecimento", description="Central de conhecimento completa",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Conhecimento do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

RESPONSABILIDADES:
- Responder perguntas dos moradores
- Manter base de conhecimento atualizada
- Gerenciar FAQs e documentos
- Facilitar onboarding de novos moradores
- Prover informações precisas sobre regras e procedimentos

COMPORTAMENTO:
- Respostas claras e objetivas
- Cite fontes quando apropriado
- Sugira documentos relacionados
- Aprenda com feedbacks
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "perguntar":
            return await self._perguntar(params, context)
        elif action == "buscar":
            return await self._buscar(params, context)
        elif action == "adicionar_documento":
            return await self._adicionar_documento(params, context)
        elif action == "atualizar_documento":
            return await self._atualizar_documento(params, context)
        elif action == "listar_documentos":
            return await self._listar_documentos(params, context)
        elif action == "adicionar_faq":
            return await self._adicionar_faq(params, context)
        elif action == "listar_faqs":
            return await self._listar_faqs(params, context)
        elif action == "registrar_feedback":
            return await self._registrar_feedback(params, context)
        elif action == "onboarding":
            return await self._onboarding(params, context)
        elif action == "sugerir_conteudo":
            return await self._sugerir_conteudo(params, context)
        elif action == "estatisticas":
            return await self._estatisticas(params, context)
        elif action == "perguntas_frequentes":
            return await self._perguntas_frequentes(params, context)
        elif action == "dashboard":
            return await self._dashboard(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    def _expandir_termos(self, termo: str) -> List[str]:
        """Expandir termo de busca com sinônimos"""
        termos = [termo.lower()]
        for chave, sinonimos in self._sinonimos.items():
            if termo.lower() in sinonimos or termo.lower() == chave:
                termos.extend(sinonimos)
                termos.append(chave)
        return list(set(termos))

    async def _perguntar(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Responder pergunta usando RAG"""
        pergunta = params.get("pergunta")
        usuario_id = params.get("usuario_id")

        # Primeiro, buscar nas FAQs
        termos = self._expandir_termos(pergunta)
        faq_match = None

        for faq in self._faqs.values():
            if faq.ativo:
                for termo in termos:
                    if termo in faq.pergunta.lower():
                        faq_match = faq
                        faq.visualizacoes += 1
                        break
                if faq_match:
                    break

        # Se encontrou FAQ exata
        if faq_match:
            return {
                "success": True,
                "tipo": "faq",
                "resposta": faq_match.resposta,
                "fonte": f"FAQ: {faq_match.pergunta}",
                "faq_id": faq_match.id
            }

        # Buscar em documentos usando RAG
        documentos_relevantes = []
        for doc in self._documentos.values():
            if doc.status == StatusDocumento.ATIVO:
                score = self._calcular_relevancia(pergunta, doc)
                if score >= self.config["score_minimo_relevancia"]:
                    documentos_relevantes.append((doc, score))

        documentos_relevantes.sort(key=lambda x: x[1], reverse=True)
        documentos_relevantes = documentos_relevantes[:3]

        # Gerar resposta com LLM
        if self.llm:
            contexto_docs = "\n\n".join([
                f"Documento: {doc.titulo}\n{doc.conteudo[:1000]}"
                for doc, _ in documentos_relevantes
            ])

            prompt = f"""Responda a pergunta usando o contexto fornecido.

PERGUNTA: {pergunta}

CONTEXTO:
{contexto_docs if contexto_docs else "Não há documentos específicos sobre este tema."}

Responda de forma clara e direta. Se não souber, diga que não tem essa informação na base de conhecimento.
"""
            resposta = await self.llm.generate(self.get_system_prompt(), prompt)

            # Registrar busca
            busca = BuscaHistorico(
                id=f"busca_{datetime.now().timestamp()}",
                termo=pergunta,
                usuario_id=usuario_id,
                timestamp=datetime.now(),
                resultados_encontrados=len(documentos_relevantes)
            )
            self._historico_buscas.append(busca)

            return {
                "success": True,
                "tipo": "rag",
                "resposta": resposta,
                "documentos_consultados": [
                    {"id": doc.id, "titulo": doc.titulo, "relevancia": round(score, 2)}
                    for doc, score in documentos_relevantes
                ],
                "busca_id": busca.id
            }

        return {"error": "LLM não configurado"}

    def _calcular_relevancia(self, pergunta: str, documento: DocumentoConhecimento) -> float:
        """Calcular relevância do documento para a pergunta"""
        termos = self._expandir_termos(pergunta)
        score = 0

        texto_doc = f"{documento.titulo} {documento.conteudo} {' '.join(documento.tags)}".lower()

        for termo in termos:
            if termo in texto_doc:
                score += 0.2
            if termo in documento.titulo.lower():
                score += 0.3
            if termo in documento.tags:
                score += 0.25

        return min(score, 1.0)

    async def _buscar(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Buscar na base de conhecimento"""
        termo = params.get("termo")
        categoria = params.get("categoria")
        limite = params.get("limite", self.config["max_resultados_busca"])

        resultados = []

        # Buscar em documentos
        for doc in self._documentos.values():
            if doc.status != StatusDocumento.ATIVO:
                continue
            if categoria and doc.categoria.value != categoria:
                continue

            score = self._calcular_relevancia(termo, doc)
            if score > 0:
                resultados.append({
                    "tipo": "documento",
                    "id": doc.id,
                    "titulo": doc.titulo,
                    "categoria": doc.categoria.value,
                    "resumo": doc.resumo,
                    "relevancia": round(score, 2)
                })

        # Buscar em FAQs
        for faq in self._faqs.values():
            if not faq.ativo:
                continue
            if categoria and faq.categoria.value != categoria:
                continue

            termos = self._expandir_termos(termo)
            match = any(t in faq.pergunta.lower() or t in faq.resposta.lower() for t in termos)

            if match:
                resultados.append({
                    "tipo": "faq",
                    "id": faq.id,
                    "titulo": faq.pergunta,
                    "categoria": faq.categoria.value,
                    "resumo": faq.resposta[:100],
                    "relevancia": 0.8
                })

        resultados.sort(key=lambda x: x["relevancia"], reverse=True)
        resultados = resultados[:limite]

        # Registrar busca
        busca = BuscaHistorico(
            id=f"busca_{datetime.now().timestamp()}",
            termo=termo,
            usuario_id=params.get("usuario_id"),
            timestamp=datetime.now(),
            resultados_encontrados=len(resultados)
        )
        self._historico_buscas.append(busca)

        return {
            "success": True,
            "termo": termo,
            "total": len(resultados),
            "resultados": resultados
        }

    async def _adicionar_documento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Adicionar documento à base"""
        titulo = params.get("titulo")
        categoria = params.get("categoria", "geral")
        conteudo = params.get("conteudo")
        tags = params.get("tags", [])
        autor = params.get("autor")
        tipo = params.get("tipo", "texto")

        # Gerar resumo automaticamente
        resumo = params.get("resumo", "")
        if not resumo and self.config["gerar_resumo_automatico"] and self.llm:
            prompt = f"Resuma em 2 frases o seguinte texto:\n\n{conteudo[:2000]}"
            resumo = await self.llm.generate(self.get_system_prompt(), prompt)

        documento = DocumentoConhecimento(
            id=f"doc_{datetime.now().timestamp()}",
            titulo=titulo,
            categoria=CategoriaConhecimento[categoria.upper()],
            tipo=TipoDocumento[tipo.upper()],
            conteudo=conteudo,
            resumo=resumo,
            tags=tags,
            status=StatusDocumento.ATIVO,
            data_criacao=datetime.now(),
            data_atualizacao=datetime.now(),
            autor=autor
        )
        self._documentos[documento.id] = documento

        return {
            "success": True,
            "documento_id": documento.id,
            "titulo": titulo,
            "categoria": categoria
        }

    async def _atualizar_documento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Atualizar documento"""
        documento_id = params.get("documento_id")

        if documento_id not in self._documentos:
            return {"error": "Documento não encontrado"}

        doc = self._documentos[documento_id]

        if "titulo" in params:
            doc.titulo = params["titulo"]
        if "conteudo" in params:
            doc.conteudo = params["conteudo"]
        if "tags" in params:
            doc.tags = params["tags"]
        if "status" in params:
            doc.status = StatusDocumento[params["status"].upper()]

        doc.versao += 1
        doc.data_atualizacao = datetime.now()

        return {
            "success": True,
            "documento_id": documento_id,
            "versao": doc.versao
        }

    async def _listar_documentos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar documentos"""
        categoria = params.get("categoria")
        status = params.get("status", "ativo")

        documentos = list(self._documentos.values())

        if categoria:
            documentos = [d for d in documentos if d.categoria.value == categoria]
        if status:
            documentos = [d for d in documentos if d.status.value == status]

        return {
            "success": True,
            "total": len(documentos),
            "documentos": [
                {
                    "id": d.id,
                    "titulo": d.titulo,
                    "categoria": d.categoria.value,
                    "tipo": d.tipo.value,
                    "resumo": d.resumo,
                    "tags": d.tags,
                    "visualizacoes": d.visualizacoes,
                    "data_atualizacao": d.data_atualizacao.isoformat()
                }
                for d in sorted(documentos, key=lambda x: x.data_atualizacao, reverse=True)
            ]
        }

    async def _adicionar_faq(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Adicionar FAQ"""
        pergunta = params.get("pergunta")
        resposta = params.get("resposta")
        categoria = params.get("categoria", "geral")

        faq = PerguntaFrequente(
            id=f"faq_{datetime.now().timestamp()}",
            pergunta=pergunta,
            resposta=resposta,
            categoria=CategoriaConhecimento[categoria.upper()]
        )
        self._faqs[faq.id] = faq

        return {
            "success": True,
            "faq_id": faq.id,
            "pergunta": pergunta
        }

    async def _listar_faqs(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar FAQs"""
        categoria = params.get("categoria")
        limite = params.get("limite", 20)

        faqs = [f for f in self._faqs.values() if f.ativo]

        if categoria:
            faqs = [f for f in faqs if f.categoria.value == categoria]

        # Ordenar por popularidade
        faqs = sorted(faqs, key=lambda x: x.visualizacoes, reverse=True)[:limite]

        return {
            "success": True,
            "total": len(faqs),
            "faqs": [
                {
                    "id": f.id,
                    "pergunta": f.pergunta,
                    "resposta": f.resposta,
                    "categoria": f.categoria.value,
                    "visualizacoes": f.visualizacoes,
                    "utilidade": round(f.util_sim / (f.util_sim + f.util_nao) * 100, 1) if (f.util_sim + f.util_nao) > 0 else 0
                }
                for f in faqs
            ]
        }

    async def _registrar_feedback(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar feedback sobre conteúdo"""
        documento_id = params.get("documento_id")
        faq_id = params.get("faq_id")
        usuario_id = params.get("usuario_id")
        util = params.get("util", True)
        comentario = params.get("comentario")

        if faq_id and faq_id in self._faqs:
            faq = self._faqs[faq_id]
            if util:
                faq.util_sim += 1
            else:
                faq.util_nao += 1

        if documento_id and documento_id in self._documentos:
            doc = self._documentos[documento_id]
            feedbacks_doc = [f for f in self._feedbacks if f.documento_id == documento_id]
            total = len(feedbacks_doc) + 1
            positivos = len([f for f in feedbacks_doc if f.tipo == "util"]) + (1 if util else 0)
            doc.utilidade_media = positivos / total

        feedback = FeedbackConhecimento(
            id=f"feedback_{datetime.now().timestamp()}",
            documento_id=documento_id or faq_id,
            usuario_id=usuario_id,
            tipo="util" if util else "nao_util",
            comentario=comentario
        )
        self._feedbacks.append(feedback)

        return {
            "success": True,
            "feedback_registrado": True
        }

    async def _onboarding(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Conteúdo de onboarding para novos moradores"""
        tipo_morador = params.get("tipo", "proprietario")  # proprietario, locatario

        conteudos = {
            "boas_vindas": "Bem-vindo ao condomínio! Este guia rápido vai ajudá-lo a conhecer nosso sistema.",
            "app": "Baixe o app Conecta Plus para acessar todos os serviços do condomínio.",
            "cadastros_importantes": [
                "Cadastro de moradores e dependentes",
                "Cadastro de veículos",
                "Cadastro de pets (se houver)",
                "Configuração de contatos de emergência"
            ],
            "servicos_disponiveis": [
                "Reserva de áreas comuns",
                "Abertura de chamados de manutenção",
                "Consulta de boletos e financeiro",
                "Pré-cadastro de visitantes",
                "Comunicados e assembleias"
            ],
            "regras_importantes": [
                "Horário de silêncio: 22h às 8h",
                "Uso de áreas comuns: consulte regulamento",
                "Coleta de lixo: horários específicos por andar",
                "Mudanças: agendar com antecedência"
            ],
            "contatos_uteis": {
                "portaria": "Ramal 9",
                "zelador": "Ramal 10",
                "administração": "contato@condominio.com.br",
                "emergência": "Botão de pânico no app"
            }
        }

        faqs_iniciantes = [f for f in self._faqs.values() if f.ativo][:5]

        return {
            "success": True,
            "tipo_morador": tipo_morador,
            "conteudo": conteudos,
            "faqs_frequentes": [
                {"pergunta": f.pergunta, "resposta": f.resposta}
                for f in faqs_iniciantes
            ],
            "documentos_essenciais": [
                d.titulo for d in self._documentos.values()
                if d.categoria in [CategoriaConhecimento.REGULAMENTO, CategoriaConhecimento.CONVENCAO]
                and d.status == StatusDocumento.ATIVO
            ]
        }

    async def _sugerir_conteudo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Sugerir conteúdo baseado em histórico"""
        usuario_id = params.get("usuario_id")

        # Analisar buscas recentes
        buscas_usuario = [b for b in self._historico_buscas if b.usuario_id == usuario_id][-10:]

        # Documentos mais visualizados
        docs_populares = sorted(
            self._documentos.values(),
            key=lambda x: x.visualizacoes,
            reverse=True
        )[:5]

        # FAQs mais úteis
        faqs_uteis = sorted(
            [f for f in self._faqs.values() if f.ativo],
            key=lambda x: x.util_sim,
            reverse=True
        )[:5]

        return {
            "success": True,
            "baseado_em_buscas": len(buscas_usuario) > 0,
            "documentos_sugeridos": [
                {"id": d.id, "titulo": d.titulo, "categoria": d.categoria.value}
                for d in docs_populares
            ],
            "faqs_populares": [
                {"pergunta": f.pergunta, "visualizacoes": f.visualizacoes}
                for f in faqs_uteis
            ]
        }

    async def _estatisticas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Estatísticas da base de conhecimento"""
        periodo_dias = params.get("dias", 30)
        data_inicio = datetime.now() - timedelta(days=periodo_dias)

        buscas_periodo = [b for b in self._historico_buscas if b.timestamp >= data_inicio]

        # Termos mais buscados
        termos_contagem = {}
        for busca in buscas_periodo:
            termos_contagem[busca.termo] = termos_contagem.get(busca.termo, 0) + 1

        termos_top = sorted(termos_contagem.items(), key=lambda x: x[1], reverse=True)[:10]

        # Buscas sem resultado
        sem_resultado = [b for b in buscas_periodo if b.resultados_encontrados == 0]

        return {
            "success": True,
            "periodo_dias": periodo_dias,
            "total_buscas": len(buscas_periodo),
            "buscas_sem_resultado": len(sem_resultado),
            "termos_mais_buscados": [{"termo": t, "contagem": c} for t, c in termos_top],
            "total_documentos": len(self._documentos),
            "total_faqs": len(self._faqs),
            "feedbacks_recebidos": len([f for f in self._feedbacks if f.timestamp >= data_inicio])
        }

    async def _perguntas_frequentes(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Top perguntas frequentes"""
        limite = params.get("limite", 10)

        faqs = sorted(
            [f for f in self._faqs.values() if f.ativo],
            key=lambda x: x.visualizacoes,
            reverse=True
        )[:limite]

        return {
            "success": True,
            "faqs": [
                {
                    "pergunta": f.pergunta,
                    "resposta": f.resposta,
                    "categoria": f.categoria.value
                }
                for f in faqs
            ]
        }

    async def _dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Dashboard do conhecimento"""
        hoje = datetime.now().date()
        buscas_hoje = [b for b in self._historico_buscas if b.timestamp.date() == hoje]

        return {
            "success": True,
            "resumo": {
                "total_documentos": len([d for d in self._documentos.values() if d.status == StatusDocumento.ATIVO]),
                "total_faqs": len([f for f in self._faqs.values() if f.ativo]),
                "buscas_hoje": len(buscas_hoje),
                "feedbacks_pendentes": len([f for f in self._feedbacks if f.tipo == "sugestao"])
            },
            "por_categoria": {
                cat.value: len([d for d in self._documentos.values() if d.categoria == cat and d.status == StatusDocumento.ATIVO])
                for cat in CategoriaConhecimento
            },
            "documentos_recentes": [
                {"titulo": d.titulo, "data": d.data_atualizacao.isoformat()}
                for d in sorted(self._documentos.values(), key=lambda x: x.data_atualizacao, reverse=True)[:5]
            ]
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_knowledge_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    rag: RAGPipeline = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteConhecimento:
    """Factory function para criar agente de conhecimento"""
    return AgenteConhecimento(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        rag=rag,
        evolution_level=evolution_level
    )
