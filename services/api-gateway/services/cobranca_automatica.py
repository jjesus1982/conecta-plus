"""
Conecta Plus - Sistema de Cobrança Automática Inteligente
Gerencia cobranças baseadas em regras e IA
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio


class CanalCobranca(Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    TELEFONE = "telefone"


class TipoMensagem(Enum):
    LEMBRETE_ANTES = "lembrete_antes"
    DIA_VENCIMENTO = "dia_vencimento"
    ATRASO_LEVE = "atraso_leve"       # 1-7 dias
    ATRASO_MEDIO = "atraso_medio"     # 8-30 dias
    ATRASO_GRAVE = "atraso_grave"     # 31-60 dias
    ATRASO_CRITICO = "atraso_critico" # 60+ dias
    NEGOCIACAO = "negociacao"
    ACORDO = "acordo"
    QUITACAO = "quitacao"


@dataclass
class ConfiguracaoCobranca:
    """Configuração de réguas de cobrança"""
    # Lembretes antes do vencimento
    dias_lembrete_antes: List[int] = None  # Ex: [7, 3, 1]

    # Cobranças após vencimento
    dias_cobranca_apos: List[int] = None   # Ex: [1, 3, 7, 15, 30]

    # Canais por fase
    canais_lembrete: List[CanalCobranca] = None
    canais_cobranca_inicial: List[CanalCobranca] = None
    canais_cobranca_avancada: List[CanalCobranca] = None

    # Horários permitidos
    horario_inicio: int = 8
    horario_fim: int = 20

    # Limites
    max_tentativas_dia: int = 2
    intervalo_minimo_horas: int = 4

    # IA
    usar_ia_personalizacao: bool = True
    usar_ia_horario_otimo: bool = True

    def __post_init__(self):
        self.dias_lembrete_antes = self.dias_lembrete_antes or [7, 3, 1]
        self.dias_cobranca_apos = self.dias_cobranca_apos or [1, 3, 7, 15, 30, 45, 60]
        self.canais_lembrete = self.canais_lembrete or [CanalCobranca.EMAIL]
        self.canais_cobranca_inicial = self.canais_cobranca_inicial or [
            CanalCobranca.EMAIL, CanalCobranca.WHATSAPP
        ]
        self.canais_cobranca_avancada = self.canais_cobranca_avancada or [
            CanalCobranca.WHATSAPP, CanalCobranca.SMS, CanalCobranca.TELEFONE
        ]


class TemplatesMensagem:
    """Templates de mensagens de cobrança"""

    TEMPLATES = {
        # Lembretes
        TipoMensagem.LEMBRETE_ANTES: {
            "email": {
                "assunto": "Lembrete: Boleto vence em {dias_para_vencer} dia(s)",
                "corpo": """
Olá {nome},

Este é um lembrete amigável sobre o boleto do seu condomínio.

📅 Vencimento: {data_vencimento}
💰 Valor: R$ {valor}
📝 Referência: {competencia}

{desconto_info}

Evite juros e multa pagando em dia!

Pague via PIX:
{pix_copia_cola}

Ou utilize o código de barras:
{linha_digitavel}

Atenciosamente,
{nome_condominio}
""",
            },
            "whatsapp": {
                "template": "reminder_before_due",
                "corpo": """📅 *Lembrete de Vencimento*

Olá {nome}! 👋

Seu boleto vence em *{dias_para_vencer} dia(s)*

💰 Valor: *R$ {valor}*
📅 Vencimento: *{data_vencimento}*

🔗 Pague agora via PIX:
```{pix_copia_cola}```

Evite juros e multa! ✅""",
            },
            "sms": {
                "corpo": "COND {nome_condominio}: Boleto R${valor} vence em {dias_para_vencer} dia(s). Evite juros! Pague via PIX ou acesse o app."
            }
        },

        # Dia do vencimento
        TipoMensagem.DIA_VENCIMENTO: {
            "email": {
                "assunto": "⚠️ Seu boleto vence HOJE",
                "corpo": """
Olá {nome},

Seu boleto vence HOJE! Pague agora para evitar juros e multa.

💰 Valor: R$ {valor}
📝 Referência: {competencia}

Pague instantaneamente via PIX:
{pix_copia_cola}

{nome_condominio}
""",
            },
            "whatsapp": {
                "corpo": """⚠️ *VENCE HOJE!*

Olá {nome}!

Seu boleto de *R$ {valor}* vence *hoje*!

Pague agora via PIX e evite juros:
```{pix_copia_cola}```

Dúvidas? Responda esta mensagem.""",
            }
        },

        # Atraso leve (1-7 dias)
        TipoMensagem.ATRASO_LEVE: {
            "email": {
                "assunto": "Boleto em atraso - Regularize sua situação",
                "corpo": """
Olá {nome},

Identificamos que seu boleto está em atraso.

📅 Vencimento: {data_vencimento}
⏰ Dias em atraso: {dias_atraso}
💰 Valor original: R$ {valor_original}
📈 Juros/Multa: R$ {valor_encargos}
💵 Valor atualizado: R$ {valor_total}

Regularize sua situação o quanto antes!

Pague via PIX (valor atualizado):
{pix_copia_cola}

Está com dificuldades? Entre em contato conosco para negociar.

{nome_condominio}
""",
            },
            "whatsapp": {
                "corpo": """🔔 *Boleto em Atraso*

Olá {nome},

Seu boleto está com *{dias_atraso} dia(s)* de atraso.

💰 Valor atualizado: *R$ {valor_total}*
(já com juros e multa)

Pague agora via PIX:
```{pix_copia_cola}```

💬 Precisa de ajuda? Responda esta mensagem.""",
            }
        },

        # Atraso médio (8-30 dias)
        TipoMensagem.ATRASO_MEDIO: {
            "whatsapp": {
                "corpo": """⚠️ *Atenção: Débito Pendente*

Olá {nome},

Seu débito com o condomínio está pendente há *{dias_atraso} dias*.

💰 Valor atual: *R$ {valor_total}*

🤝 *Podemos ajudar!*
Oferecemos condições especiais para regularização.

Responda:
1️⃣ Quero pagar agora
2️⃣ Preciso negociar
3️⃣ Já paguei""",
            },
            "email": {
                "assunto": "⚠️ Urgente: Débito pendente há {dias_atraso} dias",
                "corpo": """
Olá {nome},

Seu débito com o condomínio está pendente há {dias_atraso} dias.

💰 Valor atualizado: R$ {valor_total}

Estamos aqui para ajudar! Entre em contato para negociar condições especiais.

Atenciosamente,
{nome_condominio}
""",
            }
        },

        # Atraso grave (31-60 dias)
        TipoMensagem.ATRASO_GRAVE: {
            "whatsapp": {
                "corpo": """🚨 *Débito em Situação Crítica*

{nome}, seu débito está há mais de 30 dias sem pagamento.

💰 Valor: *R$ {valor_total}*
⚠️ Dias em atraso: *{dias_atraso}*

*Ação necessária:*
Sem regularização, medidas adicionais serão tomadas.

🤝 Oferecemos:
• Parcelamento em até 6x
• Desconto para pagamento à vista

Responda para negociar.""",
            }
        },

        # Atraso crítico (60+ dias)
        TipoMensagem.ATRASO_CRITICO: {
            "email": {
                "assunto": "🚨 URGENTE: Último aviso antes de medidas judiciais",
                "corpo": """
Prezado(a) {nome},

Apesar de nossos diversos contatos, seu débito permanece em aberto há mais de 60 dias.

Débito atual: R$ {valor_total}
Dias em atraso: {dias_atraso}

Informamos que, sem a regularização, seremos obrigados a adotar medidas legais cabíveis, incluindo:
- Negativação nos órgãos de proteção ao crédito
- Protesto do título
- Ação judicial de cobrança

Evite transtornos. Entre em contato imediatamente para regularizar sua situação.

Atenciosamente,
{nome_condominio}
""",
            },
            "whatsapp": {
                "corpo": """🚨 *ÚLTIMO AVISO*

{nome}, seu débito está crítico.

💰 Valor: R$ {valor_total}
⏰ Atraso: {dias_atraso} dias

Sem pagamento, medidas legais serão iniciadas:
• Negativação (SPC/Serasa)
• Protesto
• Cobrança judicial

*Esta é sua última chance de negociar.*

Responda AGORA para evitar estas medidas.""",
            }
        },

        # Negociação
        TipoMensagem.NEGOCIACAO: {
            "whatsapp": {
                "corpo": """🤝 *Proposta de Acordo*

Olá {nome}!

Preparamos uma proposta especial para você:

💳 *Opção 1 - À Vista:*
De R$ {valor_original} por *R$ {valor_avista}*
({desconto_percentual}% de desconto!)

📅 *Opção 2 - Parcelado:*
{parcelas}x de *R$ {valor_parcela}*
Entrada: R$ {entrada}

Responda com a opção desejada!""",
            }
        },

        # Confirmação de acordo
        TipoMensagem.ACORDO: {
            "whatsapp": {
                "corpo": """✅ *Acordo Confirmado!*

{nome}, seu acordo foi registrado com sucesso!

📋 *Resumo:*
• Valor total: R$ {valor_total}
• Parcelas: {parcelas}x de R$ {valor_parcela}
• Primeiro vencimento: {data_primeira_parcela}

Os boletos serão enviados por aqui.

Obrigado pela regularização! 🙏""",
            },
            "email": {
                "assunto": "✅ Acordo de Pagamento Confirmado",
                "corpo": """
Olá {nome},

Seu acordo de pagamento foi confirmado!

Resumo do acordo:
- Valor total: R$ {valor_total}
- Número de parcelas: {parcelas}
- Valor da parcela: R$ {valor_parcela}
- Primeiro vencimento: {data_primeira_parcela}

Os boletos serão enviados conforme o vencimento de cada parcela.

Agradecemos a regularização!

{nome_condominio}
""",
            }
        },

        # Quitação
        TipoMensagem.QUITACAO: {
            "whatsapp": {
                "corpo": """🎉 *Parabéns!*

{nome}, seu débito foi *QUITADO*!

✅ Valor pago: R$ {valor_pago}
📅 Data: {data_pagamento}

Obrigado por manter suas obrigações em dia!

Qualquer dúvida, estamos à disposição. 😊""",
            }
        }
    }

    @classmethod
    def get_template(
        cls,
        tipo: TipoMensagem,
        canal: CanalCobranca
    ) -> Optional[Dict]:
        """Retorna template para tipo e canal específicos"""
        templates_tipo = cls.TEMPLATES.get(tipo, {})
        return templates_tipo.get(canal.value)

    @classmethod
    def renderizar(
        cls,
        template: Dict,
        dados: Dict[str, Any]
    ) -> Dict[str, str]:
        """Renderiza template com dados"""
        resultado = {}
        for chave, valor in template.items():
            if isinstance(valor, str):
                resultado[chave] = valor.format(**dados)
            else:
                resultado[chave] = valor
        return resultado


class GeradorMensagemIA:
    """
    Gera mensagens personalizadas usando IA

    Adapta tom, conteúdo e abordagem baseado no perfil do devedor
    """

    @staticmethod
    def personalizar_mensagem(
        template: str,
        perfil_pagador: Dict,
        historico_interacoes: List[Dict]
    ) -> str:
        """
        Personaliza mensagem baseado no perfil

        Em produção, usaria LLM (GPT-4/Claude) para personalização
        """
        # Ajustes simples baseados no perfil
        tom = "formal"

        # Se já respondeu positivamente antes, tom mais amigável
        if any(i.get("sentimento") == "positivo" for i in historico_interacoes):
            tom = "amigavel"

        # Se nunca respondeu ou resposta negativa, mais direto
        if not historico_interacoes or \
           all(i.get("sentimento") == "negativo" for i in historico_interacoes):
            tom = "direto"

        # Aplica ajustes de tom (simplificado)
        if tom == "amigavel":
            template = template.replace("Prezado(a)", "Olá")
            template = template.replace("Informamos que", "Gostaríamos de lembrar que")

        elif tom == "direto":
            template = template.replace("Gostaríamos de", "Precisamos")
            template = template.replace("por gentileza", "urgentemente")

        return template

    @staticmethod
    def sugerir_melhor_horario(
        historico_aberturas: List[Dict]
    ) -> int:
        """
        Sugere melhor horário para envio baseado em histórico

        Returns:
            Hora ideal (0-23)
        """
        if not historico_aberturas:
            return 10  # Default: 10h

        # Conta aberturas por hora
        aberturas_por_hora = {}
        for abertura in historico_aberturas:
            hora = abertura.get("hora", 10)
            aberturas_por_hora[hora] = aberturas_por_hora.get(hora, 0) + 1

        # Retorna hora com mais aberturas
        melhor_hora = max(aberturas_por_hora, key=aberturas_por_hora.get)
        return melhor_hora


class MotorCobranca:
    """
    Motor principal de cobrança automática

    Gerencia toda a régua de cobrança de forma automatizada
    """

    def __init__(
        self,
        config: ConfiguracaoCobranca = None,
        boleto_repo=None,
        cobranca_repo=None
    ):
        self.config = config or ConfiguracaoCobranca()
        self.boleto_repo = boleto_repo
        self.cobranca_repo = cobranca_repo

    async def processar_cobrancas_pendentes(
        self,
        condominio_id: str
    ) -> Dict[str, Any]:
        """
        Processa todas as cobranças pendentes de um condomínio

        Returns:
            Estatísticas do processamento
        """
        hoje = date.today()
        estatisticas = {
            "lembretes_enviados": 0,
            "cobrancas_enviadas": 0,
            "erros": 0,
            "detalhes": []
        }

        # Busca boletos que precisam de ação
        # (implementação depende do repositório)

        # 1. Lembretes antes do vencimento
        for dias in self.config.dias_lembrete_antes:
            data_vencimento = hoje + timedelta(days=dias)
            # boletos = await self.boleto_repo.buscar_por_vencimento(data_vencimento)

            # Para cada boleto, verifica se já foi enviado lembrete hoje
            # Se não, envia

        # 2. Cobranças após vencimento
        for dias in self.config.dias_cobranca_apos:
            data_vencimento = hoje - timedelta(days=dias)
            # boletos = await self.boleto_repo.buscar_vencidos_em(data_vencimento)

            # Para cada boleto, envia cobrança apropriada

        return estatisticas

    async def enviar_cobranca(
        self,
        boleto: Dict,
        tipo: TipoMensagem,
        canais: List[CanalCobranca],
        morador: Dict
    ) -> List[Dict]:
        """
        Envia cobrança por múltiplos canais

        Returns:
            Lista de resultados de envio
        """
        resultados = []

        # Prepara dados para template
        dados = self._preparar_dados_template(boleto, morador)

        for canal in canais:
            template = TemplatesMensagem.get_template(tipo, canal)
            if not template:
                continue

            mensagem = TemplatesMensagem.renderizar(template, dados)

            try:
                # Envia pelo canal apropriado
                if canal == CanalCobranca.EMAIL:
                    resultado = await self._enviar_email(
                        morador.get("email"),
                        mensagem.get("assunto"),
                        mensagem.get("corpo")
                    )
                elif canal == CanalCobranca.WHATSAPP:
                    resultado = await self._enviar_whatsapp(
                        morador.get("telefone"),
                        mensagem.get("corpo")
                    )
                elif canal == CanalCobranca.SMS:
                    resultado = await self._enviar_sms(
                        morador.get("telefone"),
                        mensagem.get("corpo")
                    )
                else:
                    resultado = {"sucesso": False, "erro": "Canal não implementado"}

                resultados.append({
                    "canal": canal.value,
                    **resultado
                })

            except Exception as e:
                resultados.append({
                    "canal": canal.value,
                    "sucesso": False,
                    "erro": str(e)
                })

        return resultados

    def _preparar_dados_template(
        self,
        boleto: Dict,
        morador: Dict
    ) -> Dict[str, Any]:
        """Prepara dados para renderização do template"""
        hoje = date.today()
        vencimento = boleto.get("data_vencimento") or boleto.get("vencimento")

        if isinstance(vencimento, str):
            vencimento = datetime.strptime(vencimento[:10], "%Y-%m-%d").date()

        dias_atraso = (hoje - vencimento).days if hoje > vencimento else 0
        dias_para_vencer = (vencimento - hoje).days if vencimento > hoje else 0

        # Calcula encargos
        valor_original = boleto.get("valor", 0)
        valor_juros = boleto.get("valor_juros", 0)
        valor_multa = boleto.get("valor_multa", 0)
        valor_total = valor_original + valor_juros + valor_multa

        return {
            "nome": morador.get("nome", "Morador"),
            "nome_condominio": "Residencial Conecta Plus",
            "valor": f"{valor_original:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "valor_original": f"{valor_original:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "valor_encargos": f"{valor_juros + valor_multa:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "valor_total": f"{valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "data_vencimento": vencimento.strftime("%d/%m/%Y") if vencimento else "",
            "competencia": boleto.get("competencia", boleto.get("referencia", "")),
            "dias_atraso": dias_atraso,
            "dias_para_vencer": dias_para_vencer,
            "pix_copia_cola": boleto.get("pix_copia_cola", ""),
            "linha_digitavel": boleto.get("linha_digitavel", ""),
            "desconto_info": "💰 Pague até o vencimento e ganhe 5% de desconto!" if dias_para_vencer > 0 else ""
        }

    async def _enviar_email(
        self,
        destinatario: str,
        assunto: str,
        corpo: str
    ) -> Dict:
        """Envia email (mock)"""
        # Em produção, integraria com SendGrid, SES, etc.
        return {
            "sucesso": True,
            "provedor": "mock",
            "id": f"email_{datetime.now().timestamp()}"
        }

    async def _enviar_whatsapp(
        self,
        telefone: str,
        mensagem: str
    ) -> Dict:
        """Envia WhatsApp (mock)"""
        # Em produção, integraria com Evolution API, Twilio, etc.
        return {
            "sucesso": True,
            "provedor": "mock",
            "id": f"whatsapp_{datetime.now().timestamp()}"
        }

    async def _enviar_sms(
        self,
        telefone: str,
        mensagem: str
    ) -> Dict:
        """Envia SMS (mock)"""
        # Em produção, integraria com Twilio, Zenvia, etc.
        return {
            "sucesso": True,
            "provedor": "mock",
            "id": f"sms_{datetime.now().timestamp()}"
        }

    def determinar_tipo_cobranca(self, dias_atraso: int) -> TipoMensagem:
        """Determina tipo de mensagem baseado nos dias de atraso"""
        if dias_atraso < 0:
            return TipoMensagem.LEMBRETE_ANTES
        elif dias_atraso == 0:
            return TipoMensagem.DIA_VENCIMENTO
        elif dias_atraso <= 7:
            return TipoMensagem.ATRASO_LEVE
        elif dias_atraso <= 30:
            return TipoMensagem.ATRASO_MEDIO
        elif dias_atraso <= 60:
            return TipoMensagem.ATRASO_GRAVE
        else:
            return TipoMensagem.ATRASO_CRITICO

    def determinar_canais(self, tipo: TipoMensagem) -> List[CanalCobranca]:
        """Determina canais baseado no tipo de cobrança"""
        if tipo == TipoMensagem.LEMBRETE_ANTES:
            return self.config.canais_lembrete

        if tipo in [TipoMensagem.DIA_VENCIMENTO, TipoMensagem.ATRASO_LEVE]:
            return self.config.canais_cobranca_inicial

        return self.config.canais_cobranca_avancada
