"""
Conecta Plus - Agente Sustentabilidade (Nível 7)
Gestor ambiental e de eficiência energética

Capacidades:
1. REATIVO: Monitorar consumo, registrar métricas
2. PROATIVO: Alertar desperdícios, sugerir economia
3. PREDITIVO: Prever consumo, identificar tendências
4. AUTÔNOMO: Otimizar sistemas, gerar relatórios ESG
5. EVOLUTIVO: Aprender padrões, melhorar eficiência
6. COLABORATIVO: Integrar Infraestrutura, Financeiro, Síndico
7. TRANSCENDENTE: Gestão ambiental inteligente total
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


class TipoRecurso(Enum):
    ENERGIA = "energia"
    AGUA = "agua"
    GAS = "gas"
    RESIDUO = "residuo"
    SOLAR = "solar"


class TipoResiduo(Enum):
    ORGANICO = "organico"
    RECICLAVEL = "reciclavel"
    REJEITO = "rejeito"
    ELETRONICO = "eletronico"
    OLEO = "oleo"
    PILHAS = "pilhas"


class StatusMeta(Enum):
    ATINGIDA = "atingida"
    EM_PROGRESSO = "em_progresso"
    NAO_ATINGIDA = "nao_atingida"
    SUPERADA = "superada"


class NivelEficiencia(Enum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"


@dataclass
class ConsumoRecurso:
    id: str
    tipo: TipoRecurso
    periodo: str  # YYYY-MM
    valor: float
    unidade: str  # kWh, m³, kg
    custo: float
    area_comum: bool = True
    comparativo_anterior: Optional[float] = None


@dataclass
class MetaSustentabilidade:
    id: str
    tipo: TipoRecurso
    descricao: str
    valor_meta: float
    valor_atual: float
    unidade: str
    prazo: datetime
    status: StatusMeta
    ano: int


@dataclass
class ColetaSeletiva:
    id: str
    data: datetime
    tipo_residuo: TipoResiduo
    quantidade_kg: float
    destino: str
    certificado: Optional[str] = None
    receita: float = 0


@dataclass
class SistemaFotovoltaico:
    id: str
    potencia_kwp: float
    data_instalacao: datetime
    paineis: int
    inversores: int
    geracao_mensal_media: float
    economia_mensal: float
    ativo: bool = True


@dataclass
class AlertaAmbiental:
    id: str
    tipo: str
    severidade: str
    descricao: str
    data: datetime
    resolvido: bool = False
    acoes_tomadas: List[str] = field(default_factory=list)


class AgenteSustentabilidade(BaseAgent):
    """Agente Sustentabilidade - Gestor Ambiental Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"sustentabilidade_{condominio_id}",
            agent_type="sustentabilidade",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools

        self._consumos: List[ConsumoRecurso] = []
        self._metas: Dict[str, MetaSustentabilidade] = {}
        self._coletas: List[ColetaSeletiva] = []
        self._sistema_solar: Optional[SistemaFotovoltaico] = None
        self._alertas: List[AlertaAmbiental] = []
        self._dicas_economia: List[Dict] = []

        self.config = {
            "meta_reducao_energia": 10,  # % de redução
            "meta_reducao_agua": 15,
            "meta_reciclagem": 50,  # % do lixo reciclado
            "alerta_consumo_anormal": 20,  # % acima da média
            "horario_pico_inicio": "18:00",
            "horario_pico_fim": "21:00",
        }

        self._inicializar_dicas()

    def _inicializar_dicas(self):
        """Dicas de economia e sustentabilidade"""
        self._dicas_economia = [
            {
                "tipo": "energia",
                "titulo": "Iluminação LED",
                "descricao": "Substituir lâmpadas por LED pode reduzir até 80% do consumo de iluminação",
                "economia_estimada": "30%",
                "investimento": "baixo"
            },
            {
                "tipo": "energia",
                "titulo": "Sensores de presença",
                "descricao": "Instalar sensores em áreas comuns evita luzes acesas sem necessidade",
                "economia_estimada": "20%",
                "investimento": "medio"
            },
            {
                "tipo": "energia",
                "titulo": "Horário de pico",
                "descricao": "Evitar uso de equipamentos de alto consumo entre 18h e 21h",
                "economia_estimada": "15%",
                "investimento": "zero"
            },
            {
                "tipo": "agua",
                "titulo": "Torneiras automáticas",
                "descricao": "Reduzem desperdício em áreas comuns",
                "economia_estimada": "25%",
                "investimento": "medio"
            },
            {
                "tipo": "agua",
                "titulo": "Captação de chuva",
                "descricao": "Sistema de captação para irrigação e limpeza",
                "economia_estimada": "40%",
                "investimento": "alto"
            },
            {
                "tipo": "agua",
                "titulo": "Vazamentos",
                "descricao": "Verificar e corrigir vazamentos pode economizar milhares de litros",
                "economia_estimada": "10%",
                "investimento": "baixo"
            },
            {
                "tipo": "residuo",
                "titulo": "Coleta seletiva",
                "descricao": "Separar recicláveis pode gerar receita e reduzir custos de coleta",
                "economia_estimada": "30%",
                "investimento": "baixo"
            },
            {
                "tipo": "solar",
                "titulo": "Energia solar",
                "descricao": "Sistema fotovoltaico pode eliminar até 100% da conta de luz das áreas comuns",
                "economia_estimada": "80%",
                "investimento": "alto"
            },
        ]

    def _register_capabilities(self) -> None:
        self._capabilities["monitorar_consumo"] = AgentCapability(
            name="monitorar_consumo", description="Monitorar consumo de recursos",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["alertar_desperdicio"] = AgentCapability(
            name="alertar_desperdicio", description="Alertar sobre desperdícios",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["prever_consumo"] = AgentCapability(
            name="prever_consumo", description="Prever consumo futuro",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["otimizar_recursos"] = AgentCapability(
            name="otimizar_recursos", description="Otimizar uso de recursos",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["gestao_ambiental_total"] = AgentCapability(
            name="gestao_ambiental_total", description="Gestão ambiental completa",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Sustentabilidade do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

RESPONSABILIDADES:
- Monitorar consumo de energia, água e gás
- Gerenciar coleta seletiva e reciclagem
- Controlar sistema fotovoltaico (se houver)
- Gerar relatórios ESG
- Sugerir melhorias de eficiência
- Acompanhar metas de sustentabilidade

COMPORTAMENTO:
- Priorize economia e eficiência
- Sugira investimentos sustentáveis
- Monitore padrões de consumo
- Alerte sobre desperdícios
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "registrar_consumo":
            return await self._registrar_consumo(params, context)
        elif action == "listar_consumos":
            return await self._listar_consumos(params, context)
        elif action == "comparar_periodos":
            return await self._comparar_periodos(params, context)
        elif action == "definir_meta":
            return await self._definir_meta(params, context)
        elif action == "verificar_metas":
            return await self._verificar_metas(params, context)
        elif action == "registrar_coleta":
            return await self._registrar_coleta(params, context)
        elif action == "relatorio_reciclagem":
            return await self._relatorio_reciclagem(params, context)
        elif action == "configurar_solar":
            return await self._configurar_solar(params, context)
        elif action == "geracao_solar":
            return await self._geracao_solar(params, context)
        elif action == "dicas_economia":
            return await self._dicas_economia_func(params, context)
        elif action == "calcular_pegada":
            return await self._calcular_pegada(params, context)
        elif action == "relatorio_esg":
            return await self._relatorio_esg(params, context)
        elif action == "alertas_ativos":
            return await self._alertas_ativos(params, context)
        elif action == "projecao_consumo":
            return await self._projecao_consumo(params, context)
        elif action == "dashboard":
            return await self._dashboard(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _registrar_consumo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar consumo de recurso"""
        tipo = params.get("tipo")
        periodo = params.get("periodo")  # YYYY-MM
        valor = params.get("valor", 0)
        custo = params.get("custo", 0)
        area_comum = params.get("area_comum", True)

        unidades = {
            "energia": "kWh",
            "agua": "m³",
            "gas": "m³",
            "residuo": "kg",
            "solar": "kWh"
        }

        # Buscar consumo anterior para comparativo
        consumos_anteriores = [
            c for c in self._consumos
            if c.tipo.value == tipo and c.area_comum == area_comum
        ]
        media_anterior = sum(c.valor for c in consumos_anteriores) / len(consumos_anteriores) if consumos_anteriores else None

        consumo = ConsumoRecurso(
            id=f"consumo_{datetime.now().timestamp()}",
            tipo=TipoRecurso[tipo.upper()],
            periodo=periodo,
            valor=valor,
            unidade=unidades.get(tipo, "un"),
            custo=custo,
            area_comum=area_comum,
            comparativo_anterior=((valor - media_anterior) / media_anterior * 100) if media_anterior else None
        )
        self._consumos.append(consumo)

        # Verificar se está acima do normal
        alerta = None
        if media_anterior and consumo.comparativo_anterior > self.config["alerta_consumo_anormal"]:
            alerta = AlertaAmbiental(
                id=f"alerta_{datetime.now().timestamp()}",
                tipo="consumo_alto",
                severidade="media",
                descricao=f"Consumo de {tipo} {consumo.comparativo_anterior:.1f}% acima da média",
                data=datetime.now()
            )
            self._alertas.append(alerta)

            # Notificar síndico
            if self.tools:
                await self.tools.execute(
                    "send_notification",
                    user_ids=["sindico"],
                    title=f"Alerta: Consumo de {tipo.capitalize()} Alto",
                    message=f"Consumo {consumo.comparativo_anterior:.1f}% acima da média em {periodo}",
                    channels=["push", "email"]
                )

        return {
            "success": True,
            "consumo_id": consumo.id,
            "tipo": tipo,
            "periodo": periodo,
            "valor": valor,
            "unidade": consumo.unidade,
            "custo": custo,
            "variacao_percentual": round(consumo.comparativo_anterior, 1) if consumo.comparativo_anterior else None,
            "alerta_gerado": alerta is not None
        }

    async def _listar_consumos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar consumos"""
        tipo = params.get("tipo")
        ano = params.get("ano")
        limite = params.get("limite", 12)

        consumos = self._consumos

        if tipo:
            consumos = [c for c in consumos if c.tipo.value == tipo]
        if ano:
            consumos = [c for c in consumos if c.periodo.startswith(str(ano))]

        consumos = sorted(consumos, key=lambda x: x.periodo, reverse=True)[:limite]

        return {
            "success": True,
            "total": len(consumos),
            "consumos": [
                {
                    "id": c.id,
                    "tipo": c.tipo.value,
                    "periodo": c.periodo,
                    "valor": c.valor,
                    "unidade": c.unidade,
                    "custo": c.custo,
                    "variacao": round(c.comparativo_anterior, 1) if c.comparativo_anterior else None
                }
                for c in consumos
            ]
        }

    async def _comparar_periodos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Comparar consumo entre períodos"""
        tipo = params.get("tipo")
        periodo1 = params.get("periodo1")
        periodo2 = params.get("periodo2")

        consumo1 = next((c for c in self._consumos if c.tipo.value == tipo and c.periodo == periodo1), None)
        consumo2 = next((c for c in self._consumos if c.tipo.value == tipo and c.periodo == periodo2), None)

        if not consumo1 or not consumo2:
            return {"error": "Períodos não encontrados"}

        variacao = ((consumo2.valor - consumo1.valor) / consumo1.valor) * 100

        return {
            "success": True,
            "tipo": tipo,
            "periodo1": {
                "periodo": periodo1,
                "valor": consumo1.valor,
                "custo": consumo1.custo
            },
            "periodo2": {
                "periodo": periodo2,
                "valor": consumo2.valor,
                "custo": consumo2.custo
            },
            "variacao_percentual": round(variacao, 1),
            "variacao_absoluta": round(consumo2.valor - consumo1.valor, 2),
            "economia_custo": round(consumo1.custo - consumo2.custo, 2)
        }

    async def _definir_meta(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Definir meta de sustentabilidade"""
        tipo = params.get("tipo")
        descricao = params.get("descricao")
        valor_meta = params.get("valor_meta")
        ano = params.get("ano", datetime.now().year)

        unidades = {
            "energia": "kWh",
            "agua": "m³",
            "residuo": "%",
            "solar": "kWh"
        }

        meta = MetaSustentabilidade(
            id=f"meta_{tipo}_{ano}",
            tipo=TipoRecurso[tipo.upper()],
            descricao=descricao,
            valor_meta=valor_meta,
            valor_atual=0,
            unidade=unidades.get(tipo, "un"),
            prazo=datetime(ano, 12, 31),
            status=StatusMeta.EM_PROGRESSO,
            ano=ano
        )
        self._metas[meta.id] = meta

        return {
            "success": True,
            "meta_id": meta.id,
            "tipo": tipo,
            "valor_meta": valor_meta,
            "ano": ano
        }

    async def _verificar_metas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Verificar progresso das metas"""
        ano = params.get("ano", datetime.now().year)

        metas_ano = [m for m in self._metas.values() if m.ano == ano]

        for meta in metas_ano:
            # Calcular valor atual
            consumos_ano = [
                c for c in self._consumos
                if c.tipo == meta.tipo and c.periodo.startswith(str(ano))
            ]

            if meta.tipo == TipoRecurso.RESIDUO:
                # Para resíduos, calcular % reciclado
                total_residuo = sum(c.valor for c in consumos_ano)
                reciclados = sum(
                    col.quantidade_kg for col in self._coletas
                    if col.data.year == ano and col.tipo_residuo in [TipoResiduo.RECICLAVEL]
                )
                meta.valor_atual = (reciclados / total_residuo * 100) if total_residuo else 0
            else:
                meta.valor_atual = sum(c.valor for c in consumos_ano)

            # Atualizar status
            if meta.valor_atual <= meta.valor_meta * 0.9:
                meta.status = StatusMeta.SUPERADA
            elif meta.valor_atual <= meta.valor_meta:
                meta.status = StatusMeta.ATINGIDA
            elif datetime.now() > meta.prazo:
                meta.status = StatusMeta.NAO_ATINGIDA
            else:
                meta.status = StatusMeta.EM_PROGRESSO

        return {
            "success": True,
            "ano": ano,
            "metas": [
                {
                    "id": m.id,
                    "tipo": m.tipo.value,
                    "descricao": m.descricao,
                    "meta": m.valor_meta,
                    "atual": round(m.valor_atual, 2),
                    "unidade": m.unidade,
                    "status": m.status.value,
                    "progresso": round((m.valor_atual / m.valor_meta * 100) if m.valor_meta else 0, 1)
                }
                for m in metas_ano
            ]
        }

    async def _registrar_coleta(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar coleta seletiva"""
        tipo_residuo = params.get("tipo_residuo")
        quantidade_kg = params.get("quantidade_kg", 0)
        destino = params.get("destino")
        receita = params.get("receita", 0)

        coleta = ColetaSeletiva(
            id=f"coleta_{datetime.now().timestamp()}",
            data=datetime.now(),
            tipo_residuo=TipoResiduo[tipo_residuo.upper()],
            quantidade_kg=quantidade_kg,
            destino=destino,
            receita=receita
        )
        self._coletas.append(coleta)

        return {
            "success": True,
            "coleta_id": coleta.id,
            "tipo": tipo_residuo,
            "quantidade_kg": quantidade_kg,
            "destino": destino,
            "receita": receita
        }

    async def _relatorio_reciclagem(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Relatório de reciclagem"""
        mes = params.get("mes")
        ano = params.get("ano", datetime.now().year)

        coletas = self._coletas
        if ano:
            coletas = [c for c in coletas if c.data.year == ano]
        if mes:
            coletas = [c for c in coletas if c.data.month == mes]

        por_tipo = {}
        for tipo in TipoResiduo:
            total = sum(c.quantidade_kg for c in coletas if c.tipo_residuo == tipo)
            receita = sum(c.receita for c in coletas if c.tipo_residuo == tipo)
            por_tipo[tipo.value] = {
                "quantidade_kg": round(total, 2),
                "receita": round(receita, 2)
            }

        total_kg = sum(c.quantidade_kg for c in coletas)
        total_receita = sum(c.receita for c in coletas)

        return {
            "success": True,
            "periodo": f"{mes}/{ano}" if mes else str(ano),
            "total_kg": round(total_kg, 2),
            "total_receita": round(total_receita, 2),
            "por_tipo": por_tipo,
            "coletas_realizadas": len(coletas)
        }

    async def _configurar_solar(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Configurar sistema fotovoltaico"""
        potencia_kwp = params.get("potencia_kwp")
        paineis = params.get("paineis")
        inversores = params.get("inversores")
        geracao_media = params.get("geracao_mensal_media")
        economia = params.get("economia_mensal")

        self._sistema_solar = SistemaFotovoltaico(
            id=f"solar_{self.condominio_id}",
            potencia_kwp=potencia_kwp,
            data_instalacao=datetime.now(),
            paineis=paineis,
            inversores=inversores,
            geracao_mensal_media=geracao_media,
            economia_mensal=economia
        )

        return {
            "success": True,
            "sistema_id": self._sistema_solar.id,
            "potencia_kwp": potencia_kwp,
            "paineis": paineis,
            "geracao_media": geracao_media
        }

    async def _geracao_solar(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Relatório de geração solar"""
        if not self._sistema_solar:
            return {"error": "Sistema solar não configurado"}

        # Buscar consumos de energia solar
        geracao = [c for c in self._consumos if c.tipo == TipoRecurso.SOLAR]

        total_gerado = sum(c.valor for c in geracao)
        economia_total = sum(c.custo for c in geracao)

        meses_operacao = (datetime.now() - self._sistema_solar.data_instalacao).days // 30

        return {
            "success": True,
            "sistema": {
                "potencia_kwp": self._sistema_solar.potencia_kwp,
                "paineis": self._sistema_solar.paineis,
                "data_instalacao": self._sistema_solar.data_instalacao.isoformat()
            },
            "geracao": {
                "total_kwh": round(total_gerado, 2),
                "media_mensal": round(total_gerado / meses_operacao, 2) if meses_operacao else 0,
                "economia_total": round(economia_total, 2),
                "meses_operacao": meses_operacao
            }
        }

    async def _dicas_economia_func(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar dicas de economia"""
        tipo = params.get("tipo")

        dicas = self._dicas_economia
        if tipo:
            dicas = [d for d in dicas if d["tipo"] == tipo]

        return {
            "success": True,
            "dicas": dicas
        }

    async def _calcular_pegada(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Calcular pegada de carbono"""
        ano = params.get("ano", datetime.now().year)

        # Fatores de emissão (kg CO2 por unidade)
        fatores = {
            "energia": 0.084,  # kg CO2 / kWh (média Brasil)
            "gas": 2.1,        # kg CO2 / m³
            "agua": 0.0003,    # kg CO2 / m³ (tratamento)
        }

        consumos_ano = [c for c in self._consumos if c.periodo.startswith(str(ano))]

        emissoes = {}
        total = 0

        for tipo, fator in fatores.items():
            consumo_total = sum(c.valor for c in consumos_ano if c.tipo.value == tipo)
            emissao = consumo_total * fator
            emissoes[tipo] = round(emissao, 2)
            total += emissao

        # Compensação solar
        geracao_solar = sum(c.valor for c in consumos_ano if c.tipo == TipoRecurso.SOLAR)
        compensacao = geracao_solar * fatores["energia"]

        pegada_liquida = total - compensacao

        return {
            "success": True,
            "ano": ano,
            "emissoes_kg_co2": emissoes,
            "total_bruto": round(total, 2),
            "compensacao_solar": round(compensacao, 2),
            "pegada_liquida": round(pegada_liquida, 2),
            "equivalente_arvores": round(pegada_liquida / 22, 1)  # ~22kg CO2/árvore/ano
        }

    async def _relatorio_esg(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gerar relatório ESG"""
        ano = params.get("ano", datetime.now().year)

        if not self.llm:
            return {"error": "LLM não configurado"}

        # Coletar dados
        consumos = [c for c in self._consumos if c.periodo.startswith(str(ano))]
        coletas = [c for c in self._coletas if c.data.year == ano]
        metas = [m for m in self._metas.values() if m.ano == ano]

        dados = {
            "energia_kwh": sum(c.valor for c in consumos if c.tipo == TipoRecurso.ENERGIA),
            "agua_m3": sum(c.valor for c in consumos if c.tipo == TipoRecurso.AGUA),
            "gas_m3": sum(c.valor for c in consumos if c.tipo == TipoRecurso.GAS),
            "residuos_reciclados_kg": sum(c.quantidade_kg for c in coletas if c.tipo_residuo == TipoResiduo.RECICLAVEL),
            "receita_reciclagem": sum(c.receita for c in coletas),
            "geracao_solar_kwh": sum(c.valor for c in consumos if c.tipo == TipoRecurso.SOLAR),
            "metas_atingidas": len([m for m in metas if m.status in [StatusMeta.ATINGIDA, StatusMeta.SUPERADA]])
        }

        prompt = f"""Gere um relatório ESG (Environmental, Social, Governance) para o condomínio com os seguintes dados de {ano}:

{json.dumps(dados, indent=2)}

Inclua:
1. Resumo executivo
2. Indicadores ambientais
3. Comparativo com benchmarks do setor
4. Iniciativas de sustentabilidade
5. Metas para o próximo ano
6. Recomendações de melhoria
"""

        relatorio = await self.llm.generate(self.get_system_prompt(), prompt)

        return {
            "success": True,
            "ano": ano,
            "dados": dados,
            "relatorio": relatorio
        }

    async def _alertas_ativos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar alertas ativos"""
        alertas = [a for a in self._alertas if not a.resolvido]

        return {
            "success": True,
            "total": len(alertas),
            "alertas": [
                {
                    "id": a.id,
                    "tipo": a.tipo,
                    "severidade": a.severidade,
                    "descricao": a.descricao,
                    "data": a.data.isoformat()
                }
                for a in sorted(alertas, key=lambda x: x.data, reverse=True)
            ]
        }

    async def _projecao_consumo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Projetar consumo futuro"""
        tipo = params.get("tipo")
        meses = params.get("meses", 6)

        consumos = [c for c in self._consumos if c.tipo.value == tipo]
        consumos = sorted(consumos, key=lambda x: x.periodo)[-12:]  # Últimos 12 meses

        if len(consumos) < 3:
            return {"error": "Dados insuficientes para projeção"}

        # Média móvel simples
        media = sum(c.valor for c in consumos) / len(consumos)
        tendencia = (consumos[-1].valor - consumos[0].valor) / len(consumos)

        projecoes = []
        ano_mes = datetime.now()
        for i in range(meses):
            ano_mes = ano_mes + timedelta(days=30)
            valor_projetado = media + (tendencia * (len(consumos) + i))
            projecoes.append({
                "periodo": ano_mes.strftime("%Y-%m"),
                "valor_projetado": round(max(0, valor_projetado), 2)
            })

        return {
            "success": True,
            "tipo": tipo,
            "media_historica": round(media, 2),
            "tendencia_mensal": round(tendencia, 2),
            "projecoes": projecoes
        }

    async def _dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Dashboard de sustentabilidade"""
        ano = datetime.now().year
        mes = datetime.now().month

        consumos_mes = [c for c in self._consumos if c.periodo == f"{ano}-{mes:02d}"]
        consumos_ano = [c for c in self._consumos if c.periodo.startswith(str(ano))]

        return {
            "success": True,
            "resumo_mes": {
                "energia_kwh": sum(c.valor for c in consumos_mes if c.tipo == TipoRecurso.ENERGIA),
                "agua_m3": sum(c.valor for c in consumos_mes if c.tipo == TipoRecurso.AGUA),
                "gas_m3": sum(c.valor for c in consumos_mes if c.tipo == TipoRecurso.GAS),
                "custo_total": sum(c.custo for c in consumos_mes)
            },
            "resumo_ano": {
                "energia_kwh": sum(c.valor for c in consumos_ano if c.tipo == TipoRecurso.ENERGIA),
                "agua_m3": sum(c.valor for c in consumos_ano if c.tipo == TipoRecurso.AGUA),
                "custo_total": sum(c.custo for c in consumos_ano)
            },
            "reciclagem": {
                "total_kg": sum(c.quantidade_kg for c in self._coletas if c.data.year == ano),
                "receita": sum(c.receita for c in self._coletas if c.data.year == ano)
            },
            "solar": {
                "ativo": self._sistema_solar is not None,
                "geracao_ano": sum(c.valor for c in consumos_ano if c.tipo == TipoRecurso.SOLAR)
            } if self._sistema_solar else None,
            "alertas_pendentes": len([a for a in self._alertas if not a.resolvido]),
            "metas": {
                "total": len([m for m in self._metas.values() if m.ano == ano]),
                "atingidas": len([m for m in self._metas.values() if m.ano == ano and m.status in [StatusMeta.ATINGIDA, StatusMeta.SUPERADA]])
            }
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_sustainability_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteSustentabilidade:
    """Factory function para criar agente de sustentabilidade"""
    return AgenteSustentabilidade(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        evolution_level=evolution_level
    )
