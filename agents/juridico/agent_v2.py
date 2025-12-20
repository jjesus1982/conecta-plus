"""
Conecta Plus - Agente Jurídico (Nível 7)
Advogado virtual do condomínio com IA jurídica especializada

Capacidades:
1. REATIVO: Responder consultas jurídicas, buscar legislação
2. PROATIVO: Alertar sobre prazos, monitorar mudanças legais
3. PREDITIVO: Prever riscos jurídicos, antecipar conflitos
4. AUTÔNOMO: Gerar documentos, elaborar notificações
5. EVOLUTIVO: Aprender precedentes, melhorar argumentação
6. COLABORATIVO: Integrar Síndico, Compliance, Financeiro
7. TRANSCENDENTE: Assessoria jurídica completa 24/7
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

logger = logging.getLogger(__name__)


class TipoProcesso(Enum):
    COBRANCA = "cobranca"
    TRABALHISTA = "trabalhista"
    CIVEL = "civel"
    ADMINISTRATIVO = "administrativo"
    CONSUMIDOR = "consumidor"
    AMBIENTAL = "ambiental"
    CRIMINAL = "criminal"


class StatusProcesso(Enum):
    ATIVO = "ativo"
    SUSPENSO = "suspenso"
    ARQUIVADO = "arquivado"
    ENCERRADO = "encerrado"
    RECURSO = "recurso"


class TipoDocumento(Enum):
    NOTIFICACAO = "notificacao"
    CONTRATO = "contrato"
    PROCURACAO = "procuracao"
    ATA = "ata"
    PARECER = "parecer"
    REGULAMENTO = "regulamento"
    CONVENCAO = "convencao"
    ADVERTENCIA = "advertencia"
    MULTA = "multa"


class CategoriaConsulta(Enum):
    INADIMPLENCIA = "inadimplencia"
    CONVIVENCIA = "convivencia"
    OBRAS = "obras"
    ANIMAIS = "animais"
    BARULHO = "barulho"
    TRABALHISTA = "trabalhista"
    CONTRATUAL = "contratual"
    ASSEMBLEIA = "assembleia"
    REGULAMENTO = "regulamento"
    GERAL = "geral"


@dataclass
class ProcessoJuridico:
    id: str
    numero: str
    tipo: TipoProcesso
    status: StatusProcesso
    descricao: str
    partes: Dict[str, str]  # autor, reu, etc
    valor_causa: float
    data_abertura: datetime
    advogado_responsavel: Optional[str] = None
    vara: Optional[str] = None
    comarca: Optional[str] = None
    proxima_audiencia: Optional[datetime] = None
    historico: List[Dict] = field(default_factory=list)
    documentos: List[str] = field(default_factory=list)
    probabilidade_exito: Optional[float] = None


@dataclass
class DocumentoJuridico:
    id: str
    tipo: TipoDocumento
    titulo: str
    conteudo: str
    data_criacao: datetime
    criado_por: str
    destinatario: Optional[str] = None
    assinado: bool = False
    data_assinatura: Optional[datetime] = None
    hash_documento: Optional[str] = None
    versao: int = 1


@dataclass
class ConsultaJuridica:
    id: str
    categoria: CategoriaConsulta
    pergunta: str
    resposta: Optional[str] = None
    data_consulta: datetime = field(default_factory=datetime.now)
    consultante: Optional[str] = None
    referencias_legais: List[str] = field(default_factory=list)
    satisfacao: Optional[int] = None


@dataclass
class AlertaJuridico:
    id: str
    tipo: str  # prazo, vencimento, mudanca_legal, etc
    titulo: str
    descricao: str
    data_alerta: datetime
    data_prazo: Optional[datetime] = None
    prioridade: str = "normal"
    resolvido: bool = False
    processo_id: Optional[str] = None


class AgenteJuridico(BaseAgent):
    """Agente Jurídico - Advogado Virtual Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"juridico_{condominio_id}",
            agent_type="juridico",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools

        self._processos: Dict[str, ProcessoJuridico] = {}
        self._documentos: Dict[str, DocumentoJuridico] = {}
        self._consultas: List[ConsultaJuridica] = []
        self._alertas: List[AlertaJuridico] = []
        self._templates_documentos: Dict[str, str] = {}
        self._legislacao_cache: Dict[str, Dict] = {}

        self.config = {
            "dias_alerta_prazo": 7,
            "auto_gerar_cobranca": True,
            "notificar_mudancas_legais": True,
            "gravar_consultas": True,
        }

        self._inicializar_templates()
        self._inicializar_legislacao()

    def _inicializar_templates(self):
        """Templates de documentos jurídicos"""
        self._templates_documentos = {
            "notificacao_inadimplencia": """
NOTIFICAÇÃO EXTRAJUDICIAL

Ao Sr(a). {nome_devedor}
Unidade: {unidade}

Pelo presente instrumento, fica V.Sa. NOTIFICADO(A) de que se encontra
em débito com o Condomínio {nome_condominio}, referente às cotas
condominiais abaixo discriminadas:

{lista_debitos}

VALOR TOTAL: R$ {valor_total}

Fica concedido o prazo de {dias_prazo} dias corridos para regularização
do débito, sob pena de adoção das medidas judiciais cabíveis.

{cidade}, {data}

___________________________
{nome_sindico}
Síndico
""",
            "advertencia_conduta": """
ADVERTÊNCIA

Ao Sr(a). {nome_morador}
Unidade: {unidade}

Comunicamos que foi registrada ocorrência de infração ao Regulamento
Interno deste Condomínio, conforme descrito abaixo:

INFRAÇÃO: {descricao_infracao}
DATA: {data_ocorrencia}
ARTIGO VIOLADO: {artigo_regulamento}

Esta é uma ADVERTÊNCIA formal. A reincidência poderá resultar em
aplicação de multa conforme Art. {artigo_multa} do Regulamento Interno.

{cidade}, {data}

___________________________
{nome_sindico}
Síndico
""",
            "multa": """
NOTIFICAÇÃO DE MULTA

Ao Sr(a). {nome_morador}
Unidade: {unidade}

Em razão de reiteradas infrações ao Regulamento Interno, conforme
advertências anteriores, aplicamos a presente MULTA no valor de:

R$ {valor_multa} ({valor_extenso})

FUNDAMENTAÇÃO:
{fundamentacao}

O valor será acrescido à próxima cota condominial.

{cidade}, {data}

___________________________
{nome_sindico}
Síndico
""",
            "procuracao_assembleia": """
PROCURAÇÃO

Pelo presente instrumento particular, eu {nome_outorgante},
proprietário(a)/inquilino(a) da unidade {unidade} do Condomínio
{nome_condominio}, CPF {cpf_outorgante}, nomeio e constituo como
meu(minha) bastante procurador(a) o(a) Sr(a). {nome_outorgado},
CPF {cpf_outorgado}, para me representar na Assembleia Geral
{tipo_assembleia} a ser realizada em {data_assembleia}, podendo
votar em meu nome conforme sua consciência.

{cidade}, {data}

___________________________
{nome_outorgante}
Outorgante
""",
        }

    def _inicializar_legislacao(self):
        """Cache de legislação condominial"""
        self._legislacao_cache = {
            "codigo_civil_condominio": {
                "artigos": {
                    "1331": "Definição de condomínio edilício",
                    "1332": "Instituição do condomínio",
                    "1333": "Convenção de condomínio",
                    "1334": "Conteúdo da convenção",
                    "1335": "Direitos dos condôminos",
                    "1336": "Deveres dos condôminos",
                    "1337": "Penalidades ao condômino nocivo",
                    "1338": "Obras em partes comuns",
                    "1339": "Partes comuns e exclusivas",
                    "1340": "Despesas comuns",
                    "1341": "Obras voluptuárias e úteis",
                    "1342": "Seguro obrigatório",
                    "1343": "Administração provisória",
                    "1344": "Atribuições do síndico",
                    "1345": "Assembleia geral",
                    "1346": "Convocação de assembleia",
                    "1347": "Assembleia para destituição",
                    "1348": "Quorum de votação",
                    "1349": "Atos do síndico",
                    "1350": "Prestação de contas",
                    "1351": "Alteração da convenção",
                    "1352": "Regulamento interno",
                    "1353": "Ação de cobrança",
                    "1354": "Assembleia virtual",
                    "1355": "Extinção do condomínio",
                    "1356": "Reconstrução",
                    "1357": "Terreno remanescente",
                    "1358": "Desapropriação",
                },
            },
            "lei_4591_64": {
                "descricao": "Lei de Condomínios e Incorporações",
                "aplicacao": "Dispositivos não revogados pelo Código Civil",
            },
            "cdc": {
                "descricao": "Código de Defesa do Consumidor",
                "aplicacao": "Relações com prestadores de serviço",
            },
        }

    def _register_capabilities(self) -> None:
        self._capabilities["consulta_juridica"] = AgentCapability(
            name="consulta_juridica", description="Responder consultas jurídicas",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["gerar_documento"] = AgentCapability(
            name="gerar_documento", description="Gerar documentos jurídicos",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["analisar_processo"] = AgentCapability(
            name="analisar_processo", description="Analisar processos judiciais",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["gestao_processos"] = AgentCapability(
            name="gestao_processos", description="Gerenciar processos judiciais",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["assessoria_completa"] = AgentCapability(
            name="assessoria_completa", description="Assessoria jurídica completa",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente Jurídico do Conecta Plus - um advogado virtual especializado em direito condominial.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

ESPECIALIDADES:
- Direito Condominial (Lei 4.591/64, Código Civil Arts. 1.331-1.358)
- Cobrança de inadimplentes
- Elaboração de documentos (notificações, advertências, multas)
- Análise de convenção e regulamento interno
- Questões trabalhistas de funcionários do condomínio
- Contratos com prestadores de serviços
- Assembleias e quórum de votação

COMPORTAMENTO:
- Seja preciso nas citações legais
- Sempre indique a base legal das orientações
- Alerte sobre riscos jurídicos
- Sugira alternativas de resolução de conflitos
- Recomende advogado presencial para casos complexos
- Mantenha linguagem acessível mas tecnicamente correta
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "consulta":
            return await self._consulta_juridica(params, context)
        elif action == "gerar_notificacao":
            return await self._gerar_notificacao(params, context)
        elif action == "gerar_advertencia":
            return await self._gerar_advertencia(params, context)
        elif action == "gerar_multa":
            return await self._gerar_multa(params, context)
        elif action == "gerar_procuracao":
            return await self._gerar_procuracao(params, context)
        elif action == "registrar_processo":
            return await self._registrar_processo(params, context)
        elif action == "atualizar_processo":
            return await self._atualizar_processo(params, context)
        elif action == "listar_processos":
            return await self._listar_processos(params, context)
        elif action == "analisar_risco":
            return await self._analisar_risco(params, context)
        elif action == "buscar_legislacao":
            return await self._buscar_legislacao(params, context)
        elif action == "calcular_multa_atraso":
            return await self._calcular_multa_atraso(params, context)
        elif action == "verificar_quorum":
            return await self._verificar_quorum(params, context)
        elif action == "analisar_contrato":
            return await self._analisar_contrato(params, context)
        elif action == "historico_consultas":
            return await self._historico_consultas(params, context)
        elif action == "alertas_prazos":
            return await self._alertas_prazos(params, context)
        elif action == "dashboard":
            return await self._dashboard(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _consulta_juridica(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Responder consulta jurídica"""
        pergunta = params.get("pergunta")
        categoria = params.get("categoria", "geral")
        consultante = params.get("consultante")

        if not self.llm:
            return {"error": "LLM não configurado"}

        # Buscar legislação relevante
        legislacao_relevante = self._buscar_legislacao_relevante(categoria)

        prompt = f"""Responda a seguinte consulta jurídica sobre condomínio:

PERGUNTA: {pergunta}
CATEGORIA: {categoria}

LEGISLAÇÃO RELEVANTE:
{json.dumps(legislacao_relevante, indent=2, ensure_ascii=False)}

Forneça:
1. Resposta clara e objetiva
2. Base legal (artigos de lei)
3. Orientação prática
4. Riscos ou cuidados
5. Recomendação (se necessário consultar advogado presencial)
"""

        resposta = await self.llm.generate(self.get_system_prompt(), prompt)

        # Registrar consulta
        consulta = ConsultaJuridica(
            id=f"consulta_{datetime.now().timestamp()}",
            categoria=CategoriaConsulta[categoria.upper()] if categoria.upper() in CategoriaConsulta.__members__ else CategoriaConsulta.GERAL,
            pergunta=pergunta,
            resposta=resposta,
            consultante=consultante,
            referencias_legais=self._extrair_referencias(resposta)
        )
        self._consultas.append(consulta)

        return {
            "success": True,
            "consulta_id": consulta.id,
            "resposta": resposta,
            "categoria": categoria,
            "referencias": consulta.referencias_legais
        }

    def _buscar_legislacao_relevante(self, categoria: str) -> Dict:
        """Buscar legislação relevante para a categoria"""
        relevante = {}

        mapeamento = {
            "inadimplencia": ["1336", "1337", "1353"],
            "convivencia": ["1336", "1337", "1352"],
            "obras": ["1338", "1341", "1342"],
            "assembleia": ["1345", "1346", "1347", "1348", "1351"],
            "regulamento": ["1333", "1334", "1352"],
            "trabalhista": [],
            "contratual": [],
        }

        artigos_relevantes = mapeamento.get(categoria, [])

        for artigo in artigos_relevantes:
            if artigo in self._legislacao_cache["codigo_civil_condominio"]["artigos"]:
                relevante[f"Art. {artigo} CC"] = self._legislacao_cache["codigo_civil_condominio"]["artigos"][artigo]

        return relevante

    def _extrair_referencias(self, texto: str) -> List[str]:
        """Extrair referências legais do texto"""
        import re
        referencias = []

        # Padrões de referência legal
        padroes = [
            r"Art\.?\s*\d+",
            r"artigo\s+\d+",
            r"Lei\s+\d+\.?\d*/\d+",
            r"Código Civil",
            r"CDC",
        ]

        for padrao in padroes:
            matches = re.findall(padrao, texto, re.IGNORECASE)
            referencias.extend(matches)

        return list(set(referencias))

    async def _gerar_notificacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gerar notificação de inadimplência"""
        nome_devedor = params.get("nome_devedor")
        unidade = params.get("unidade")
        lista_debitos = params.get("lista_debitos", [])
        valor_total = params.get("valor_total", 0)
        dias_prazo = params.get("dias_prazo", 10)
        nome_sindico = params.get("nome_sindico")
        nome_condominio = params.get("nome_condominio", self.condominio_id)

        # Formatar lista de débitos
        debitos_formatados = "\n".join([
            f"- {d.get('referencia')}: R$ {d.get('valor', 0):.2f}"
            for d in lista_debitos
        ])

        conteudo = self._templates_documentos["notificacao_inadimplencia"].format(
            nome_devedor=nome_devedor,
            unidade=unidade,
            nome_condominio=nome_condominio,
            lista_debitos=debitos_formatados,
            valor_total=f"{valor_total:.2f}",
            dias_prazo=dias_prazo,
            cidade="São Paulo",
            data=datetime.now().strftime("%d de %B de %Y"),
            nome_sindico=nome_sindico
        )

        doc = DocumentoJuridico(
            id=f"notif_{datetime.now().timestamp()}",
            tipo=TipoDocumento.NOTIFICACAO,
            titulo=f"Notificação de Inadimplência - {unidade}",
            conteudo=conteudo,
            data_criacao=datetime.now(),
            criado_por=self.agent_id,
            destinatario=nome_devedor
        )
        self._documentos[doc.id] = doc

        return {
            "success": True,
            "documento_id": doc.id,
            "tipo": "notificacao_inadimplencia",
            "conteudo": conteudo,
            "destinatario": nome_devedor,
            "unidade": unidade
        }

    async def _gerar_advertencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gerar advertência por infração"""
        nome_morador = params.get("nome_morador")
        unidade = params.get("unidade")
        descricao_infracao = params.get("descricao_infracao")
        data_ocorrencia = params.get("data_ocorrencia", datetime.now().strftime("%d/%m/%Y"))
        artigo_regulamento = params.get("artigo_regulamento", "N/A")
        artigo_multa = params.get("artigo_multa", "N/A")
        nome_sindico = params.get("nome_sindico")

        conteudo = self._templates_documentos["advertencia_conduta"].format(
            nome_morador=nome_morador,
            unidade=unidade,
            descricao_infracao=descricao_infracao,
            data_ocorrencia=data_ocorrencia,
            artigo_regulamento=artigo_regulamento,
            artigo_multa=artigo_multa,
            cidade="São Paulo",
            data=datetime.now().strftime("%d de %B de %Y"),
            nome_sindico=nome_sindico
        )

        doc = DocumentoJuridico(
            id=f"adv_{datetime.now().timestamp()}",
            tipo=TipoDocumento.ADVERTENCIA,
            titulo=f"Advertência - {unidade}",
            conteudo=conteudo,
            data_criacao=datetime.now(),
            criado_por=self.agent_id,
            destinatario=nome_morador
        )
        self._documentos[doc.id] = doc

        return {
            "success": True,
            "documento_id": doc.id,
            "tipo": "advertencia",
            "conteudo": conteudo
        }

    async def _gerar_multa(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gerar notificação de multa"""
        nome_morador = params.get("nome_morador")
        unidade = params.get("unidade")
        valor_multa = params.get("valor_multa", 0)
        fundamentacao = params.get("fundamentacao")
        nome_sindico = params.get("nome_sindico")

        # Valor por extenso (simplificado)
        valor_extenso = f"{valor_multa:.2f} reais"

        conteudo = self._templates_documentos["multa"].format(
            nome_morador=nome_morador,
            unidade=unidade,
            valor_multa=f"{valor_multa:.2f}",
            valor_extenso=valor_extenso,
            fundamentacao=fundamentacao,
            cidade="São Paulo",
            data=datetime.now().strftime("%d de %B de %Y"),
            nome_sindico=nome_sindico
        )

        doc = DocumentoJuridico(
            id=f"multa_{datetime.now().timestamp()}",
            tipo=TipoDocumento.MULTA,
            titulo=f"Multa - {unidade}",
            conteudo=conteudo,
            data_criacao=datetime.now(),
            criado_por=self.agent_id,
            destinatario=nome_morador
        )
        self._documentos[doc.id] = doc

        # Notificar financeiro
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                f"financeiro_{self.condominio_id}",
                {
                    "action": "registrar_multa",
                    "unidade": unidade,
                    "valor": valor_multa,
                    "documento_id": doc.id
                }
            )

        return {
            "success": True,
            "documento_id": doc.id,
            "tipo": "multa",
            "valor": valor_multa,
            "conteudo": conteudo
        }

    async def _gerar_procuracao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gerar procuração para assembleia"""
        nome_outorgante = params.get("nome_outorgante")
        cpf_outorgante = params.get("cpf_outorgante")
        unidade = params.get("unidade")
        nome_outorgado = params.get("nome_outorgado")
        cpf_outorgado = params.get("cpf_outorgado")
        data_assembleia = params.get("data_assembleia")
        tipo_assembleia = params.get("tipo_assembleia", "Ordinária")

        conteudo = self._templates_documentos["procuracao_assembleia"].format(
            nome_outorgante=nome_outorgante,
            cpf_outorgante=cpf_outorgante,
            unidade=unidade,
            nome_condominio=self.condominio_id,
            nome_outorgado=nome_outorgado,
            cpf_outorgado=cpf_outorgado,
            data_assembleia=data_assembleia,
            tipo_assembleia=tipo_assembleia,
            cidade="São Paulo",
            data=datetime.now().strftime("%d de %B de %Y")
        )

        doc = DocumentoJuridico(
            id=f"proc_{datetime.now().timestamp()}",
            tipo=TipoDocumento.PROCURACAO,
            titulo=f"Procuração Assembleia - {unidade}",
            conteudo=conteudo,
            data_criacao=datetime.now(),
            criado_por=self.agent_id
        )
        self._documentos[doc.id] = doc

        return {
            "success": True,
            "documento_id": doc.id,
            "tipo": "procuracao",
            "conteudo": conteudo
        }

    async def _registrar_processo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar novo processo judicial"""
        numero = params.get("numero")
        tipo = params.get("tipo", "civel")
        descricao = params.get("descricao")
        partes = params.get("partes", {})
        valor_causa = params.get("valor_causa", 0)
        advogado = params.get("advogado")
        vara = params.get("vara")
        comarca = params.get("comarca")

        processo = ProcessoJuridico(
            id=f"proc_{datetime.now().timestamp()}",
            numero=numero,
            tipo=TipoProcesso[tipo.upper()],
            status=StatusProcesso.ATIVO,
            descricao=descricao,
            partes=partes,
            valor_causa=valor_causa,
            data_abertura=datetime.now(),
            advogado_responsavel=advogado,
            vara=vara,
            comarca=comarca
        )
        self._processos[processo.id] = processo

        return {
            "success": True,
            "processo_id": processo.id,
            "numero": numero,
            "tipo": tipo,
            "status": "ativo"
        }

    async def _atualizar_processo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Atualizar processo judicial"""
        processo_id = params.get("processo_id")
        atualizacao = params.get("atualizacao")
        novo_status = params.get("status")
        proxima_audiencia = params.get("proxima_audiencia")

        if processo_id not in self._processos:
            return {"error": "Processo não encontrado"}

        processo = self._processos[processo_id]

        if atualizacao:
            processo.historico.append({
                "data": datetime.now().isoformat(),
                "atualizacao": atualizacao
            })

        if novo_status:
            processo.status = StatusProcesso[novo_status.upper()]

        if proxima_audiencia:
            processo.proxima_audiencia = datetime.fromisoformat(proxima_audiencia)

            # Criar alerta
            alerta = AlertaJuridico(
                id=f"alerta_{datetime.now().timestamp()}",
                tipo="audiencia",
                titulo=f"Audiência - Processo {processo.numero}",
                descricao=f"Audiência agendada para {proxima_audiencia}",
                data_alerta=datetime.now(),
                data_prazo=processo.proxima_audiencia,
                processo_id=processo_id,
                prioridade="alta"
            )
            self._alertas.append(alerta)

        return {
            "success": True,
            "processo_id": processo_id,
            "status": processo.status.value,
            "historico": len(processo.historico)
        }

    async def _listar_processos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar processos"""
        status = params.get("status")
        tipo = params.get("tipo")

        processos = list(self._processos.values())

        if status:
            processos = [p for p in processos if p.status.value == status]
        if tipo:
            processos = [p for p in processos if p.tipo.value == tipo]

        return {
            "success": True,
            "total": len(processos),
            "processos": [
                {
                    "id": p.id,
                    "numero": p.numero,
                    "tipo": p.tipo.value,
                    "status": p.status.value,
                    "descricao": p.descricao[:100],
                    "valor_causa": p.valor_causa,
                    "proxima_audiencia": p.proxima_audiencia.isoformat() if p.proxima_audiencia else None
                }
                for p in processos
            ]
        }

    async def _analisar_risco(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Analisar risco jurídico de situação"""
        situacao = params.get("situacao")
        tipo = params.get("tipo", "geral")

        if not self.llm:
            return {"error": "LLM não configurado"}

        prompt = f"""Analise o risco jurídico da seguinte situação condominial:

SITUAÇÃO: {situacao}
TIPO: {tipo}

Forneça:
1. Nível de risco (baixo, médio, alto, crítico)
2. Possíveis consequências jurídicas
3. Ações preventivas recomendadas
4. Prazos importantes
5. Estimativa de custos se judicializar
"""

        analise = await self.llm.generate(self.get_system_prompt(), prompt)

        return {
            "success": True,
            "situacao": situacao,
            "analise": analise
        }

    async def _buscar_legislacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Buscar legislação"""
        termo = params.get("termo")
        tipo = params.get("tipo", "codigo_civil")

        resultados = []

        if tipo == "codigo_civil" or tipo == "todos":
            for artigo, descricao in self._legislacao_cache["codigo_civil_condominio"]["artigos"].items():
                if termo.lower() in descricao.lower() or termo in artigo:
                    resultados.append({
                        "fonte": "Código Civil",
                        "artigo": artigo,
                        "descricao": descricao
                    })

        return {
            "success": True,
            "termo": termo,
            "resultados": resultados
        }

    async def _calcular_multa_atraso(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Calcular multa e juros por atraso"""
        valor_original = params.get("valor_original", 0)
        data_vencimento = params.get("data_vencimento")
        taxa_multa = params.get("taxa_multa", 2.0)  # 2% padrão
        taxa_juros_mensal = params.get("taxa_juros", 1.0)  # 1% ao mês

        vencimento = datetime.fromisoformat(data_vencimento)
        dias_atraso = (datetime.now() - vencimento).days

        if dias_atraso <= 0:
            return {
                "success": True,
                "valor_original": valor_original,
                "dias_atraso": 0,
                "multa": 0,
                "juros": 0,
                "valor_atualizado": valor_original
            }

        # Multa fixa de 2%
        multa = valor_original * (taxa_multa / 100)

        # Juros pro rata die
        meses_atraso = dias_atraso / 30
        juros = valor_original * (taxa_juros_mensal / 100) * meses_atraso

        valor_atualizado = valor_original + multa + juros

        return {
            "success": True,
            "valor_original": valor_original,
            "dias_atraso": dias_atraso,
            "multa": round(multa, 2),
            "juros": round(juros, 2),
            "valor_atualizado": round(valor_atualizado, 2),
            "base_legal": "Art. 1.336, §1º do Código Civil"
        }

    async def _verificar_quorum(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Verificar quórum necessário para deliberação"""
        tipo_deliberacao = params.get("tipo")
        total_unidades = params.get("total_unidades", 100)
        presentes = params.get("presentes", 0)

        quorums = {
            "primeira_convocacao": {
                "fracao": 0.5,
                "descricao": "Maioria absoluta (50% + 1)",
                "base_legal": "Art. 1.352 CC"
            },
            "segunda_convocacao": {
                "fracao": 0,
                "descricao": "Qualquer número",
                "base_legal": "Art. 1.353 CC"
            },
            "alteracao_convencao": {
                "fracao": 2/3,
                "descricao": "2/3 das frações ideais",
                "base_legal": "Art. 1.351 CC"
            },
            "alteracao_fachada": {
                "fracao": 1.0,
                "descricao": "Unanimidade",
                "base_legal": "Art. 1.336, III CC"
            },
            "destituicao_sindico": {
                "fracao": 0.5,
                "descricao": "Maioria absoluta",
                "base_legal": "Art. 1.349 CC"
            },
            "obras_uteis": {
                "fracao": 0.5,
                "descricao": "Maioria dos presentes",
                "base_legal": "Art. 1.341, I CC"
            },
            "obras_voluptuarias": {
                "fracao": 2/3,
                "descricao": "2/3 dos condôminos",
                "base_legal": "Art. 1.341, II CC"
            },
        }

        info = quorums.get(tipo_deliberacao, {
            "fracao": 0.5,
            "descricao": "Maioria simples",
            "base_legal": "Art. 1.352 CC"
        })

        necessario = int(total_unidades * info["fracao"]) + 1 if info["fracao"] > 0 else 1
        atingido = presentes >= necessario

        return {
            "success": True,
            "tipo_deliberacao": tipo_deliberacao,
            "quorum_necessario": necessario,
            "presentes": presentes,
            "atingido": atingido,
            "descricao": info["descricao"],
            "base_legal": info["base_legal"]
        }

    async def _analisar_contrato(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Analisar contrato"""
        tipo_contrato = params.get("tipo")
        conteudo = params.get("conteudo")
        pontos_atencao = params.get("pontos_atencao", [])

        if not self.llm:
            return {"error": "LLM não configurado"}

        prompt = f"""Analise o seguinte contrato para o condomínio:

TIPO: {tipo_contrato}
PONTOS DE ATENÇÃO: {pontos_atencao}

CONTEÚDO:
{conteudo[:3000]}

Forneça:
1. Cláusulas favoráveis ao condomínio
2. Cláusulas desfavoráveis ou de risco
3. Cláusulas ausentes recomendadas
4. Sugestões de alteração
5. Parecer geral (favorável, com ressalvas, desfavorável)
"""

        analise = await self.llm.generate(self.get_system_prompt(), prompt)

        return {
            "success": True,
            "tipo": tipo_contrato,
            "analise": analise
        }

    async def _historico_consultas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Histórico de consultas jurídicas"""
        limite = params.get("limite", 20)
        categoria = params.get("categoria")

        consultas = self._consultas
        if categoria:
            consultas = [c for c in consultas if c.categoria.value == categoria]

        consultas = sorted(consultas, key=lambda x: x.data_consulta, reverse=True)[:limite]

        return {
            "success": True,
            "total": len(consultas),
            "consultas": [
                {
                    "id": c.id,
                    "categoria": c.categoria.value,
                    "pergunta": c.pergunta[:100],
                    "data": c.data_consulta.isoformat(),
                    "referencias": c.referencias_legais
                }
                for c in consultas
            ]
        }

    async def _alertas_prazos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar alertas e prazos"""
        alertas_ativos = [a for a in self._alertas if not a.resolvido]
        alertas_ativos = sorted(alertas_ativos, key=lambda x: x.data_prazo or datetime.max)

        # Verificar processos com audiências próximas
        for processo in self._processos.values():
            if processo.proxima_audiencia:
                dias_para_audiencia = (processo.proxima_audiencia - datetime.now()).days
                if 0 < dias_para_audiencia <= self.config["dias_alerta_prazo"]:
                    existe = any(a.processo_id == processo.id and a.tipo == "audiencia" for a in alertas_ativos)
                    if not existe:
                        alertas_ativos.append(AlertaJuridico(
                            id=f"auto_alerta_{processo.id}",
                            tipo="audiencia",
                            titulo=f"Audiência Próxima - {processo.numero}",
                            descricao=f"Audiência em {dias_para_audiencia} dias",
                            data_alerta=datetime.now(),
                            data_prazo=processo.proxima_audiencia,
                            processo_id=processo.id,
                            prioridade="alta"
                        ))

        return {
            "success": True,
            "alertas": [
                {
                    "id": a.id,
                    "tipo": a.tipo,
                    "titulo": a.titulo,
                    "descricao": a.descricao,
                    "prazo": a.data_prazo.isoformat() if a.data_prazo else None,
                    "prioridade": a.prioridade
                }
                for a in alertas_ativos
            ]
        }

    async def _dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Dashboard jurídico"""
        processos_ativos = len([p for p in self._processos.values() if p.status == StatusProcesso.ATIVO])
        valor_total_causas = sum(p.valor_causa for p in self._processos.values() if p.status == StatusProcesso.ATIVO)
        alertas_pendentes = len([a for a in self._alertas if not a.resolvido])
        consultas_mes = len([c for c in self._consultas
                           if c.data_consulta.month == datetime.now().month])

        return {
            "success": True,
            "resumo": {
                "processos_ativos": processos_ativos,
                "valor_total_causas": valor_total_causas,
                "alertas_pendentes": alertas_pendentes,
                "consultas_mes": consultas_mes,
                "documentos_gerados": len(self._documentos)
            },
            "processos_por_tipo": {
                tipo.value: len([p for p in self._processos.values() if p.tipo == tipo])
                for tipo in TipoProcesso
            },
            "proximas_audiencias": [
                {
                    "processo": p.numero,
                    "data": p.proxima_audiencia.isoformat(),
                    "dias_restantes": (p.proxima_audiencia - datetime.now()).days
                }
                for p in self._processos.values()
                if p.proxima_audiencia and p.proxima_audiencia > datetime.now()
            ][:5]
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_legal_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteJuridico:
    """Factory function para criar agente jurídico"""
    return AgenteJuridico(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        evolution_level=evolution_level
    )
