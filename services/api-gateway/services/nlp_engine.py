"""
Conecta Plus - NLP Engine
Motor de Processamento de Linguagem Natural para cobrança inteligente
"""

import os
import re
import json
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict
from enum import Enum


# ==================== CONFIGURAÇÃO ====================

class Sentimento(str, Enum):
    """Sentimentos detectados"""
    MUITO_POSITIVO = "muito_positivo"
    POSITIVO = "positivo"
    NEUTRO = "neutro"
    NEGATIVO = "negativo"
    MUITO_NEGATIVO = "muito_negativo"
    HOSTIL = "hostil"


class TomMensagem(str, Enum):
    """Tom da mensagem de cobrança"""
    AMIGAVEL = "amigavel"
    PROFISSIONAL = "profissional"
    FIRME = "firme"
    URGENTE = "urgente"
    FINAL = "final"


class CanalComunicacao(str, Enum):
    """Canais de comunicação"""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    TELEFONE = "telefone"
    CARTA = "carta"


@dataclass
class AnaliseSentimento:
    """Resultado da análise de sentimento"""
    sentimento: Sentimento
    score: float  # -1.0 a 1.0
    confianca: float
    emocoes_detectadas: List[str]
    intencao_pagamento: float  # 0-1
    requer_atencao_especial: bool
    sugestao_resposta: str


@dataclass
class MensagemGerada:
    """Mensagem gerada pelo sistema"""
    assunto: Optional[str]
    corpo: str
    tom: TomMensagem
    canal: CanalComunicacao
    personalizacoes: Dict[str, str]
    cta: str  # Call to Action
    score_efetividade: float
    variante: str  # A/B testing


@dataclass
class PerfilComunicacao:
    """Perfil de comunicação do cliente"""
    unidade_id: str
    canal_preferido: CanalComunicacao
    horario_preferido: str  # HH:MM
    dia_semana_preferido: int  # 0-6
    tom_mais_efetivo: TomMensagem
    responde_rapido: bool
    taxa_resposta: float
    historico_interacoes: int


# ==================== ANÁLISE DE SENTIMENTO ====================

class AnalisadorSentimento:
    """
    Analisa sentimento de mensagens recebidas dos moradores

    Usa análise baseada em léxico + padrões para ambiente sem dependências ML,
    com suporte a integração com APIs externas quando disponível.
    """

    # Léxico de palavras positivas
    PALAVRAS_POSITIVAS = {
        'obrigado': 0.5, 'obrigada': 0.5, 'agradeço': 0.5,
        'pagarei': 0.6, 'vou pagar': 0.6, 'pago': 0.4,
        'desculpa': 0.3, 'desculpe': 0.3, 'perdão': 0.3,
        'combinado': 0.5, 'acordo': 0.4, 'aceito': 0.5,
        'entendo': 0.3, 'compreendo': 0.3,
        'sim': 0.2, 'ok': 0.2, 'certo': 0.2,
        'amanhã': 0.4, 'segunda': 0.3, 'semana': 0.2,
        'gentileza': 0.3, 'por favor': 0.2,
        'transferi': 0.7, 'paguei': 0.8, 'quitei': 0.8,
        'regularizar': 0.5, 'resolver': 0.4
    }

    # Léxico de palavras negativas
    PALAVRAS_NEGATIVAS = {
        'não': -0.2, 'nunca': -0.4, 'jamais': -0.5,
        'absurdo': -0.6, 'abuso': -0.6, 'roubo': -0.7,
        'processo': -0.4, 'advogado': -0.3, 'justiça': -0.3,
        'impossível': -0.5, 'não tenho': -0.4, 'sem dinheiro': -0.5,
        'desemprego': -0.4, 'desempregado': -0.4,
        'doença': -0.3, 'hospital': -0.3, 'saúde': -0.2,
        'crise': -0.3, 'dificuldade': -0.3,
        'reclamar': -0.4, 'reclamação': -0.4,
        'pare': -0.5, 'chega': -0.4, 'basta': -0.4,
        'irritado': -0.5, 'raiva': -0.6, 'ódio': -0.8
    }

    # Padrões de intenção de pagamento
    PADROES_INTENCAO_PAGAR = [
        (r'vou pagar', 0.7),
        (r'pagarei', 0.7),
        (r'pago (amanhã|segunda|semana)', 0.6),
        (r'transferir?i?', 0.6),
        (r'pode parcelar', 0.5),
        (r'preciso de (prazo|tempo)', 0.4),
        (r'dia \d+ (eu )?pago', 0.6),
        (r'(até|antes) (do )?(dia|vencimento)', 0.5),
        (r'combinado', 0.6),
        (r'aceito', 0.6),
        (r'acordo', 0.5),
    ]

    # Padrões de hostilidade
    PADROES_HOSTILIDADE = [
        (r'(vai|vou) process', 0.7),
        (r'meu advogado', 0.6),
        (r'(procon|justiça|tribunal)', 0.5),
        (r'(para|pare) de (me )?ligar', 0.6),
        (r'(assédio|perseguição)', 0.8),
        (r'(não|nunca) (vou )?pag', 0.4),
        (r'(roubo|ladrões|ladrão)', 0.7),
    ]

    def analisar(self, texto: str, contexto: Optional[Dict] = None) -> AnaliseSentimento:
        """
        Analisa sentimento de uma mensagem

        Args:
            texto: Texto da mensagem
            contexto: Contexto adicional (histórico, perfil)

        Returns:
            AnaliseSentimento com detalhes
        """
        texto_lower = texto.lower()

        # Calcula score baseado em léxico
        score_lexico = self._calcular_score_lexico(texto_lower)

        # Detecta intenção de pagamento
        intencao_pag = self._detectar_intencao_pagamento(texto_lower)

        # Detecta hostilidade
        hostilidade = self._detectar_hostilidade(texto_lower)

        # Detecta emoções
        emocoes = self._detectar_emocoes(texto_lower)

        # Combina scores
        score_final = score_lexico * 0.6 + intencao_pag * 0.4

        # Ajusta por hostilidade
        if hostilidade > 0.5:
            score_final = min(score_final, -0.3)

        # Classifica sentimento
        if hostilidade > 0.6:
            sentimento = Sentimento.HOSTIL
        elif score_final > 0.5:
            sentimento = Sentimento.MUITO_POSITIVO
        elif score_final > 0.2:
            sentimento = Sentimento.POSITIVO
        elif score_final > -0.2:
            sentimento = Sentimento.NEUTRO
        elif score_final > -0.5:
            sentimento = Sentimento.NEGATIVO
        else:
            sentimento = Sentimento.MUITO_NEGATIVO

        # Gera sugestão de resposta
        sugestao = self._gerar_sugestao_resposta(sentimento, intencao_pag, emocoes)

        return AnaliseSentimento(
            sentimento=sentimento,
            score=round(score_final, 3),
            confianca=self._calcular_confianca(texto),
            emocoes_detectadas=emocoes,
            intencao_pagamento=round(intencao_pag, 3),
            requer_atencao_especial=hostilidade > 0.5 or 'doença' in emocoes or 'desemprego' in emocoes,
            sugestao_resposta=sugestao
        )

    def _calcular_score_lexico(self, texto: str) -> float:
        """Calcula score baseado em palavras-chave"""
        score = 0.0
        palavras_encontradas = 0

        for palavra, peso in self.PALAVRAS_POSITIVAS.items():
            if palavra in texto:
                score += peso
                palavras_encontradas += 1

        for palavra, peso in self.PALAVRAS_NEGATIVAS.items():
            if palavra in texto:
                score += peso  # já é negativo
                palavras_encontradas += 1

        # Normaliza
        if palavras_encontradas > 0:
            score = score / max(palavras_encontradas, 1)

        return max(-1.0, min(1.0, score))

    def _detectar_intencao_pagamento(self, texto: str) -> float:
        """Detecta intenção de pagamento"""
        max_score = 0.0

        for padrao, score in self.PADROES_INTENCAO_PAGAR:
            if re.search(padrao, texto):
                max_score = max(max_score, score)

        return max_score

    def _detectar_hostilidade(self, texto: str) -> float:
        """Detecta nível de hostilidade"""
        max_score = 0.0

        for padrao, score in self.PADROES_HOSTILIDADE:
            if re.search(padrao, texto):
                max_score = max(max_score, score)

        return max_score

    def _detectar_emocoes(self, texto: str) -> List[str]:
        """Detecta emoções específicas"""
        emocoes = []

        mapeamento = {
            'frustração': ['absurdo', 'não acredito', 'cansado', 'farto'],
            'preocupação': ['preocupado', 'medo', 'receio', 'ansioso'],
            'arrependimento': ['desculpa', 'perdão', 'erro', 'deveria'],
            'gratidão': ['obrigado', 'agradeço', 'gentileza'],
            'raiva': ['raiva', 'ódio', 'irritado', 'revoltado'],
            'tristeza': ['triste', 'difícil', 'problema', 'crise'],
            'esperança': ['espero', 'vou conseguir', 'vai melhorar'],
            'desemprego': ['desempregado', 'desemprego', 'perdi emprego', 'sem trabalho'],
            'doença': ['doente', 'doença', 'hospital', 'tratamento', 'saúde']
        }

        for emocao, palavras in mapeamento.items():
            for palavra in palavras:
                if palavra in texto:
                    if emocao not in emocoes:
                        emocoes.append(emocao)
                    break

        return emocoes

    def _calcular_confianca(self, texto: str) -> float:
        """Calcula confiança na análise"""
        # Mais texto = mais confiança
        palavras = len(texto.split())

        if palavras < 3:
            return 0.4
        elif palavras < 10:
            return 0.6
        elif palavras < 30:
            return 0.8
        else:
            return 0.9

    def _gerar_sugestao_resposta(
        self,
        sentimento: Sentimento,
        intencao_pag: float,
        emocoes: List[str]
    ) -> str:
        """Gera sugestão de como responder"""

        if sentimento == Sentimento.HOSTIL:
            return "Escalar para supervisor. Responder com calma, sem confronto. Oferecer canal de ouvidoria."

        if 'desemprego' in emocoes or 'doença' in emocoes:
            return "Demonstrar empatia. Oferecer condições especiais de negociação. Considerar carência."

        if sentimento in [Sentimento.MUITO_POSITIVO, Sentimento.POSITIVO]:
            if intencao_pag > 0.5:
                return "Confirmar acordo e facilitar processo de pagamento. Enviar PIX/boleto imediatamente."
            else:
                return "Agradecer pelo contato. Aproveitar momento positivo para propor acordo."

        if sentimento == Sentimento.NEUTRO:
            return "Manter tom profissional. Apresentar opções claras de regularização."

        if sentimento in [Sentimento.NEGATIVO, Sentimento.MUITO_NEGATIVO]:
            return "Manter calma. Ouvir reclamação. Buscar entender motivo real. Oferecer alternativas."

        return "Analisar caso individualmente."


# ==================== GERADOR DE MENSAGENS INTELIGENTE ====================

class GeradorMensagensIA:
    """
    Gera mensagens de cobrança personalizadas e otimizadas

    Usa templates inteligentes com variações para A/B testing,
    adaptando tom, canal e conteúdo ao perfil do cliente.
    """

    # Templates base por tom
    TEMPLATES = {
        TomMensagem.AMIGAVEL: {
            'email_assunto': [
                "Lembrete amigável: {competencia}",
                "{nome}, não esqueça do boleto de {competencia}",
                "Uma ajudinha para lembrar: boleto {competencia}"
            ],
            'corpo': [
                """Olá {nome}!

Esperamos que esteja tudo bem com você e sua família.

Passando para lembrar que o boleto de {competencia} no valor de R$ {valor} vence em {vencimento}.

Para sua comodidade, você pode pagar via PIX (mais rápido!) ou boleto bancário.

{cta}

Qualquer dúvida, estamos à disposição!

Atenciosamente,
{condominio}""",
                """Oi {nome}, tudo bem?

Só um lembrete carinhoso: seu boleto de {competencia} (R$ {valor}) vence dia {vencimento}.

{cta}

Abraços,
{condominio}"""
            ],
            'cta': [
                "Clique aqui para pagar via PIX: {link_pix}",
                "Pague agora pelo PIX e evite filas: {link_pix}",
                "Acesse: {link_portal}"
            ]
        },
        TomMensagem.PROFISSIONAL: {
            'email_assunto': [
                "Cobrança: Boleto {competencia} - {condominio}",
                "Aviso de vencimento: {competencia}",
                "Pendência financeira - Unidade {unidade}"
            ],
            'corpo': [
                """Prezado(a) {nome},

Informamos que consta em aberto o boleto referente a {competencia}, no valor de R$ {valor}, com vencimento em {vencimento}.

Solicitamos a regularização da pendência o mais breve possível.

{cta}

Em caso de dúvidas ou necessidade de negociação, entre em contato conosco.

Atenciosamente,
Administração {condominio}"""
            ],
            'cta': [
                "Para pagamento: {link_portal}",
                "Acesse o portal do condômino para segunda via: {link_portal}"
            ]
        },
        TomMensagem.FIRME: {
            'email_assunto': [
                "URGENTE: Débito em aberto - {competencia}",
                "Aviso importante: Regularize sua situação",
                "Pendência financeira requer atenção imediata"
            ],
            'corpo': [
                """Prezado(a) Sr(a). {nome},

Verificamos que o boleto de {competencia}, no valor de R$ {valor}, encontra-se vencido há {dias_atraso} dias.

Estão sendo aplicados juros e multa conforme convenção condominial.

Valor atualizado: R$ {valor_atualizado}

Solicitamos a regularização IMEDIATA para evitar medidas administrativas adicionais.

{cta}

Para negociação de parcelamento, entre em contato até {prazo_negociacao}.

Administração {condominio}"""
            ],
            'cta': [
                "Pague agora: {link_pagamento}",
                "Regularize já: {link_portal}"
            ]
        },
        TomMensagem.URGENTE: {
            'email_assunto': [
                "ÚLTIMO AVISO: Débito vencido - Ação necessária",
                "ATENÇÃO: Risco de restrição - Unidade {unidade}",
                "AVISO FINAL antes de medidas legais"
            ],
            'corpo': [
                """Sr(a). {nome},

AVISO FINAL

Apesar de nossas comunicações anteriores, identificamos que permanece em aberto o débito referente a {competencia}.

Valor total com encargos: R$ {valor_atualizado}
Dias em atraso: {dias_atraso}

Informamos que, não havendo regularização até {prazo_final}, seremos obrigados a:
- Incluir o débito em órgãos de proteção ao crédito (SPC/Serasa)
- Encaminhar para cobrança judicial

ESTA É A ÚLTIMA OPORTUNIDADE de regularização amigável.

{cta}

Para negociar condições especiais, ligue: {telefone}

Administração {condominio}"""
            ],
            'cta': [
                "PAGUE AGORA: {link_pagamento}",
                "Última chance: {link_portal}"
            ]
        },
        TomMensagem.FINAL: {
            'email_assunto': [
                "NOTIFICAÇÃO EXTRAJUDICIAL - Unidade {unidade}",
                "Cobrança judicial em andamento",
                "Comunicado formal: Medidas legais"
            ],
            'corpo': [
                """NOTIFICAÇÃO EXTRAJUDICIAL

Ao Sr(a). {nome}
Unidade: {unidade}

Pelo presente instrumento, NOTIFICAMOS V.Sa. de que:

1. Encontra-se em débito com o Condomínio {condominio} no valor de R$ {valor_atualizado}, referente a {competencia}.

2. Apesar de diversas tentativas de contato, não obtivemos retorno para negociação.

3. Concedemos o prazo IMPRORROGÁVEL de 5 (cinco) dias úteis para regularização.

4. Decorrido o prazo sem manifestação, o débito será encaminhado para:
   - Inclusão nos cadastros de inadimplentes (SPC/Serasa)
   - Cobrança judicial, com acréscimo de honorários advocatícios (20%)

Esta notificação tem caráter de INTERPELAÇÃO JUDICIAL, nos termos do Código Civil.

{cta}

Data: {data_hoje}
{condominio}"""
            ],
            'cta': [
                "Regularização: {link_portal}",
                "Contato urgente: {telefone}"
            ]
        }
    }

    # Templates para WhatsApp (mais curtos)
    TEMPLATES_WHATSAPP = {
        TomMensagem.AMIGAVEL: [
            "Oi {nome}! Tudo bem? Seu boleto de {competencia} (R$ {valor}) vence em {vencimento}. Pague fácil pelo PIX: {link_pix}",
            "Olá {nome}! Lembrete: boleto de {competencia} vence dia {vencimento}. Link PIX: {link_pix}"
        ],
        TomMensagem.PROFISSIONAL: [
            "{nome}, informamos que seu boleto de {competencia} (R$ {valor}) vence em {vencimento}. Acesse: {link_portal}",
            "Prezado(a) {nome}, pendência de {competencia} - R$ {valor}. Vencimento: {vencimento}. Portal: {link_portal}"
        ],
        TomMensagem.FIRME: [
            "AVISO: {nome}, seu boleto de {competencia} está vencido há {dias_atraso} dias. Total com juros: R$ {valor_atualizado}. Regularize: {link_portal}",
            "{nome}, URGENTE: Débito de R$ {valor_atualizado} vencido. Evite restrição de crédito. Pague: {link_pagamento}"
        ],
        TomMensagem.URGENTE: [
            "ÚLTIMO AVISO: {nome}, débito de R$ {valor_atualizado} ({dias_atraso} dias). Prazo final: {prazo_final}. Regularize AGORA: {link_pagamento}",
            "ATENÇÃO {nome}! Última oportunidade antes de medidas legais. Débito: R$ {valor_atualizado}. Contato: {telefone}"
        ]
    }

    def __init__(self):
        self.analisador_sentimento = AnalisadorSentimento()

    def gerar_mensagem(
        self,
        dados_boleto: Dict,
        dados_morador: Dict,
        dados_condominio: Dict,
        canal: CanalComunicacao,
        tom: Optional[TomMensagem] = None,
        historico_interacoes: Optional[List[Dict]] = None,
        variante: str = "A"
    ) -> MensagemGerada:
        """
        Gera mensagem personalizada de cobrança

        Args:
            dados_boleto: Dados do boleto (valor, vencimento, etc)
            dados_morador: Dados do morador (nome, unidade)
            dados_condominio: Dados do condomínio
            canal: Canal de comunicação
            tom: Tom da mensagem (auto se None)
            historico_interacoes: Histórico de mensagens anteriores
            variante: Variante para A/B testing

        Returns:
            MensagemGerada com conteúdo personalizado
        """
        # Determina tom automaticamente se não especificado
        if tom is None:
            tom = self._determinar_tom_automatico(dados_boleto, historico_interacoes)

        # Prepara variáveis de substituição
        variaveis = self._preparar_variaveis(dados_boleto, dados_morador, dados_condominio)

        # Seleciona template
        if canal == CanalComunicacao.WHATSAPP:
            corpo = self._selecionar_template_whatsapp(tom, variante)
            assunto = None
        else:
            templates = self.TEMPLATES.get(tom, self.TEMPLATES[TomMensagem.PROFISSIONAL])
            assunto = self._selecionar_e_preencher(templates['email_assunto'], variaveis, variante)
            corpo = self._selecionar_e_preencher(templates['corpo'], variaveis, variante)

        # Preenche variáveis
        corpo = self._preencher_template(corpo, variaveis)
        if assunto:
            assunto = self._preencher_template(assunto, variaveis)

        # Determina CTA
        cta = self._gerar_cta(canal, tom, variaveis)

        # Calcula score de efetividade esperado
        score_efetividade = self._calcular_score_efetividade(tom, canal, dados_boleto, historico_interacoes)

        return MensagemGerada(
            assunto=assunto,
            corpo=corpo,
            tom=tom,
            canal=canal,
            personalizacoes=variaveis,
            cta=cta,
            score_efetividade=score_efetividade,
            variante=variante
        )

    def _determinar_tom_automatico(
        self,
        dados_boleto: Dict,
        historico: Optional[List[Dict]]
    ) -> TomMensagem:
        """Determina tom baseado na situação"""

        status = dados_boleto.get('status', 'pendente')
        dias_atraso = dados_boleto.get('dias_atraso', 0)

        # Se tem histórico de resposta positiva recente
        if historico:
            ultima = historico[-1] if historico else None
            if ultima and ultima.get('resposta_positiva'):
                return TomMensagem.PROFISSIONAL

        # Baseado em dias de atraso
        if status == 'pendente' and dias_atraso <= 0:
            return TomMensagem.AMIGAVEL
        elif dias_atraso <= 15:
            return TomMensagem.PROFISSIONAL
        elif dias_atraso <= 30:
            return TomMensagem.FIRME
        elif dias_atraso <= 60:
            return TomMensagem.URGENTE
        else:
            return TomMensagem.FINAL

    def _preparar_variaveis(
        self,
        dados_boleto: Dict,
        dados_morador: Dict,
        dados_condominio: Dict
    ) -> Dict[str, str]:
        """Prepara variáveis para substituição"""

        # Calcula valores
        valor = dados_boleto.get('valor', 0)
        dias_atraso = dados_boleto.get('dias_atraso', 0)

        # Calcula valor atualizado (2% multa + 1% juros ao mês)
        if dias_atraso > 0:
            multa = valor * 0.02
            juros = valor * (0.01 / 30) * dias_atraso
            valor_atualizado = valor + multa + juros
        else:
            valor_atualizado = valor

        # Datas
        vencimento = dados_boleto.get('vencimento', '')
        if isinstance(vencimento, str) and len(vencimento) >= 10:
            vencimento_fmt = f"{vencimento[8:10]}/{vencimento[5:7]}/{vencimento[:4]}"
        else:
            vencimento_fmt = str(vencimento)

        prazo_final = (date.today() + timedelta(days=5)).strftime('%d/%m/%Y')
        prazo_negociacao = (date.today() + timedelta(days=3)).strftime('%d/%m/%Y')

        return {
            'nome': dados_morador.get('nome', dados_morador.get('morador', 'Morador')),
            'unidade': dados_morador.get('unidade', dados_morador.get('numero', 'N/A')),
            'competencia': dados_boleto.get('competencia', 'N/A'),
            'valor': f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            'valor_atualizado': f"{valor_atualizado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            'vencimento': vencimento_fmt,
            'dias_atraso': str(dias_atraso),
            'condominio': dados_condominio.get('nome', 'Condomínio'),
            'prazo_final': prazo_final,
            'prazo_negociacao': prazo_negociacao,
            'data_hoje': date.today().strftime('%d/%m/%Y'),
            'link_pix': dados_boleto.get('link_pix', dados_boleto.get('pix_copia_cola', '#')),
            'link_portal': dados_condominio.get('portal_url', '#'),
            'link_pagamento': dados_boleto.get('link_pagamento', '#'),
            'telefone': dados_condominio.get('telefone', '(11) 0000-0000')
        }

    def _selecionar_template_whatsapp(self, tom: TomMensagem, variante: str) -> str:
        """Seleciona template de WhatsApp"""
        templates = self.TEMPLATES_WHATSAPP.get(tom, self.TEMPLATES_WHATSAPP[TomMensagem.PROFISSIONAL])
        idx = 0 if variante == "A" else min(1, len(templates) - 1)
        return templates[idx]

    def _selecionar_e_preencher(self, templates: List[str], variaveis: Dict, variante: str) -> str:
        """Seleciona template baseado na variante"""
        idx = 0 if variante == "A" else min(1, len(templates) - 1)
        return templates[idx]

    def _preencher_template(self, template: str, variaveis: Dict) -> str:
        """Preenche template com variáveis"""
        resultado = template
        for chave, valor in variaveis.items():
            resultado = resultado.replace(f'{{{chave}}}', str(valor))
        return resultado

    def _gerar_cta(self, canal: CanalComunicacao, tom: TomMensagem, variaveis: Dict) -> str:
        """Gera call-to-action apropriado"""

        if canal == CanalComunicacao.WHATSAPP:
            return variaveis.get('link_pix', variaveis.get('link_portal', ''))

        ctas = self.TEMPLATES.get(tom, {}).get('cta', ["Acesse: {link_portal}"])
        cta = ctas[0]
        return self._preencher_template(cta, variaveis)

    def _calcular_score_efetividade(
        self,
        tom: TomMensagem,
        canal: CanalComunicacao,
        dados_boleto: Dict,
        historico: Optional[List[Dict]]
    ) -> float:
        """Calcula score de efetividade esperado"""

        # Base por tom
        base_tom = {
            TomMensagem.AMIGAVEL: 0.65,
            TomMensagem.PROFISSIONAL: 0.60,
            TomMensagem.FIRME: 0.55,
            TomMensagem.URGENTE: 0.50,
            TomMensagem.FINAL: 0.30
        }
        score = base_tom.get(tom, 0.50)

        # Ajuste por canal
        ajuste_canal = {
            CanalComunicacao.WHATSAPP: 1.15,  # Maior taxa de abertura
            CanalComunicacao.SMS: 1.10,
            CanalComunicacao.EMAIL: 1.0,
            CanalComunicacao.TELEFONE: 1.20,  # Contato direto
            CanalComunicacao.CARTA: 0.80
        }
        score *= ajuste_canal.get(canal, 1.0)

        # Ajuste por histórico
        if historico:
            respostas_positivas = sum(1 for h in historico if h.get('resposta_positiva'))
            if respostas_positivas > 0:
                score *= 1.1

        return min(1.0, round(score, 2))


# ==================== OTIMIZADOR DE COMUNICAÇÃO ====================

class OtimizadorComunicacao:
    """
    Otimiza estratégia de comunicação por morador

    Aprende com histórico para determinar melhor:
    - Canal de comunicação
    - Horário de envio
    - Tom da mensagem
    - Dia da semana
    """

    def __init__(self):
        self.perfis_cache: Dict[str, PerfilComunicacao] = {}

    def obter_perfil(
        self,
        unidade_id: str,
        historico_interacoes: List[Dict]
    ) -> PerfilComunicacao:
        """
        Obtém ou cria perfil de comunicação otimizado

        Args:
            unidade_id: ID da unidade
            historico_interacoes: Histórico de interações

        Returns:
            PerfilComunicacao otimizado
        """
        if unidade_id in self.perfis_cache:
            return self.perfis_cache[unidade_id]

        # Analisa histórico
        perfil = self._analisar_historico(unidade_id, historico_interacoes)
        self.perfis_cache[unidade_id] = perfil

        return perfil

    def _analisar_historico(
        self,
        unidade_id: str,
        historico: List[Dict]
    ) -> PerfilComunicacao:
        """Analisa histórico para criar perfil"""

        if not historico:
            # Perfil padrão
            return PerfilComunicacao(
                unidade_id=unidade_id,
                canal_preferido=CanalComunicacao.WHATSAPP,
                horario_preferido="10:00",
                dia_semana_preferido=1,  # Segunda
                tom_mais_efetivo=TomMensagem.PROFISSIONAL,
                responde_rapido=False,
                taxa_resposta=0.5,
                historico_interacoes=0
            )

        # Analisa canais com resposta
        canais_efetivos = {}
        horarios_resposta = []
        dias_resposta = []
        tons_efetivos = {}
        respostas_rapidas = 0

        for interacao in historico:
            canal = interacao.get('canal')
            teve_resposta = interacao.get('teve_resposta', False)

            if canal:
                if canal not in canais_efetivos:
                    canais_efetivos[canal] = {'enviados': 0, 'respondidos': 0}
                canais_efetivos[canal]['enviados'] += 1
                if teve_resposta:
                    canais_efetivos[canal]['respondidos'] += 1

            if teve_resposta:
                # Horário da resposta
                hora = interacao.get('hora_resposta')
                if hora:
                    horarios_resposta.append(hora)

                # Dia da semana
                dia = interacao.get('dia_semana_resposta')
                if dia is not None:
                    dias_resposta.append(dia)

                # Tom efetivo
                tom = interacao.get('tom')
                if tom:
                    if tom not in tons_efetivos:
                        tons_efetivos[tom] = 0
                    tons_efetivos[tom] += 1

                # Tempo de resposta
                tempo = interacao.get('tempo_resposta_horas', 48)
                if tempo < 4:
                    respostas_rapidas += 1

        # Determina canal preferido
        melhor_canal = CanalComunicacao.WHATSAPP
        melhor_taxa = 0
        for canal, stats in canais_efetivos.items():
            taxa = stats['respondidos'] / stats['enviados'] if stats['enviados'] > 0 else 0
            if taxa > melhor_taxa:
                melhor_taxa = taxa
                try:
                    melhor_canal = CanalComunicacao(canal)
                except:
                    pass

        # Determina horário preferido
        horario_pref = "10:00"
        if horarios_resposta:
            # Média dos horários
            horas = [int(h.split(':')[0]) for h in horarios_resposta if ':' in str(h)]
            if horas:
                media_hora = sum(horas) // len(horas)
                horario_pref = f"{media_hora:02d}:00"

        # Dia preferido
        dia_pref = 1  # Segunda por padrão
        if dias_resposta:
            # Moda
            dia_pref = max(set(dias_resposta), key=dias_resposta.count)

        # Tom mais efetivo
        tom_pref = TomMensagem.PROFISSIONAL
        if tons_efetivos:
            melhor_tom = max(tons_efetivos, key=tons_efetivos.get)
            try:
                tom_pref = TomMensagem(melhor_tom)
            except:
                pass

        # Taxa de resposta geral
        total_enviados = sum(s['enviados'] for s in canais_efetivos.values())
        total_respondidos = sum(s['respondidos'] for s in canais_efetivos.values())
        taxa_resposta = total_respondidos / total_enviados if total_enviados > 0 else 0.5

        return PerfilComunicacao(
            unidade_id=unidade_id,
            canal_preferido=melhor_canal,
            horario_preferido=horario_pref,
            dia_semana_preferido=dia_pref,
            tom_mais_efetivo=tom_pref,
            responde_rapido=respostas_rapidas > len(historico) * 0.3,
            taxa_resposta=round(taxa_resposta, 2),
            historico_interacoes=len(historico)
        )

    def sugerir_melhor_momento(
        self,
        perfil: PerfilComunicacao
    ) -> Dict[str, Any]:
        """
        Sugere melhor momento para contato

        Returns:
            Dict com canal, horário e dia sugeridos
        """
        hoje = date.today()
        dia_semana_hoje = hoje.weekday()

        # Calcula próximo dia preferido
        dias_ate_preferido = (perfil.dia_semana_preferido - dia_semana_hoje) % 7
        if dias_ate_preferido == 0:
            # Hoje é o dia preferido
            proximo_dia = hoje
        else:
            proximo_dia = hoje + timedelta(days=dias_ate_preferido)

        return {
            'canal': perfil.canal_preferido.value,
            'horario': perfil.horario_preferido,
            'data_sugerida': proximo_dia.isoformat(),
            'dia_semana': ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][perfil.dia_semana_preferido],
            'tom_sugerido': perfil.tom_mais_efetivo.value,
            'probabilidade_resposta': perfil.taxa_resposta,
            'responde_rapido': perfil.responde_rapido
        }


# ==================== INSTÂNCIAS GLOBAIS ====================

analisador_sentimento = AnalisadorSentimento()
gerador_mensagens = GeradorMensagensIA()
otimizador_comunicacao = OtimizadorComunicacao()
