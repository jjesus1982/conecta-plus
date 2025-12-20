"""
Conecta Plus - Serviço de WhatsApp
Envio de mensagens via WhatsApp (Evolution API / Twilio)
"""

import os
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConfiguracaoWhatsApp:
    """Configuração do serviço de WhatsApp"""
    # Evolution API (self-hosted)
    evolution_url: str = os.getenv('EVOLUTION_API_URL', 'http://localhost:8080')
    evolution_key: str = os.getenv('EVOLUTION_API_KEY', '')
    evolution_instance: str = os.getenv('EVOLUTION_INSTANCE', 'conecta-plus')

    # Twilio (alternativa)
    twilio_sid: str = os.getenv('TWILIO_SID', '')
    twilio_token: str = os.getenv('TWILIO_TOKEN', '')
    twilio_from: str = os.getenv('TWILIO_WHATSAPP_FROM', '')

    # Configurações gerais
    provider: str = os.getenv('WHATSAPP_PROVIDER', 'evolution')  # 'evolution' ou 'twilio'


class WhatsAppService:
    """Serviço de envio de WhatsApp"""

    # Templates de mensagens
    TEMPLATES = {
        'boleto': """
🏠 *{condominio_nome}*
━━━━━━━━━━━━━━━━━━

Olá, *{morador_nome}*! 👋

Seu boleto de condomínio está disponível:

📋 *Detalhes:*
• Competência: {competencia}
• Vencimento: {vencimento}
• Valor: *R$ {valor}*

💳 *Pague via PIX:*
Copie o código abaixo:
```
{pix_copia_cola}
```

📄 Ou acesse: {url_boleto}

━━━━━━━━━━━━━━━━━━
_Mensagem automática - Conecta Plus_
        """,

        'lembrete': """
⏰ *Lembrete de Vencimento*
━━━━━━━━━━━━━━━━━━

Olá, *{morador_nome}*!

Seu boleto vence {quando}:

📋 Competência: {competencia}
💰 Valor: *R$ {valor}*
📅 Vencimento: {vencimento}

💳 Pague via PIX (código abaixo):
```
{pix_copia_cola}
```

_Evite juros e multas, pague em dia!_ ✅
        """,

        'cobranca_leve': """
⚠️ *Aviso de Pendência*
━━━━━━━━━━━━━━━━━━

Olá, *{morador_nome}*.

Identificamos uma pendência em sua conta:

📋 Competência: {competencia}
💰 Valor: *R$ {valor}*
📅 Vencimento: {vencimento}
⏰ Dias em atraso: *{dias_atraso}*

Regularize sua situação para evitar encargos adicionais.

💳 PIX (código):
```
{pix_copia_cola}
```

Dúvidas? Fale com a administração.
        """,

        'cobranca_media': """
🔴 *PENDÊNCIA FINANCEIRA*
━━━━━━━━━━━━━━━━━━

Prezado(a) *{morador_nome}*,

Verificamos que existem pendências em seu nome há *{dias_atraso} dias*:

💰 Valor total: *R$ {valor_total}*

⚠️ Acréscimos aplicados:
• Multa: 2%
• Juros: 1% ao mês

📞 Entre em contato URGENTE com a administração para regularização ou proposta de acordo.

_Evite medidas de cobrança adicionais._
        """,

        'cobranca_grave': """
🚨 *NOTIFICAÇÃO URGENTE*
━━━━━━━━━━━━━━━━━━

*{morador_nome}*,

Sua situação financeira está CRÍTICA.

💰 Débito total: *R$ {valor_total}*
⏰ Dias em atraso: *{dias_atraso}*

⚠️ *ATENÇÃO:* Caso não seja regularizado em *5 dias úteis*, medidas de cobrança serão adotadas:
• Protesto em cartório
• Negativação SPC/Serasa
• Cobrança judicial

📞 Entre em contato IMEDIATAMENTE:
{telefone_administracao}

_Esta é uma notificação formal._
        """,

        'pagamento_confirmado': """
✅ *Pagamento Confirmado!*
━━━━━━━━━━━━━━━━━━

Olá, *{morador_nome}*! 🎉

Recebemos seu pagamento:

📋 Competência: {competencia}
💰 Valor: *R$ {valor}*
📅 Data: {data_pagamento}
💳 Forma: {forma_pagamento}

Obrigado por manter suas obrigações em dia! 👏

━━━━━━━━━━━━━━━━━━
_{condominio_nome}_
        """,

        'acordo_proposta': """
🤝 *Proposta de Acordo*
━━━━━━━━━━━━━━━━━━

Olá, *{morador_nome}*!

Preparamos uma proposta especial para você:

💰 Débito original: R$ {valor_original}
🎁 Desconto: {desconto}%
✨ Valor com desconto: *R$ {valor_final}*

📋 Condições:
• {parcelas}x de R$ {valor_parcela}
• Entrada: R$ {entrada}
• Dia de vencimento: {dia_vencimento}

Deseja aceitar? Responda:
*1* - Sim, aceito
*2* - Quero negociar
*3* - Não tenho interesse

_Proposta válida por 48 horas._
        """
    }

    def __init__(self, config: ConfiguracaoWhatsApp = None):
        self.config = config or ConfiguracaoWhatsApp()

    async def enviar_mensagem(
        self,
        telefone: str,
        mensagem: str,
        media_url: Optional[str] = None,
        media_type: str = 'image'
    ) -> Dict[str, Any]:
        """
        Envia mensagem de WhatsApp

        Args:
            telefone: Número do telefone (apenas números, com DDD)
            mensagem: Texto da mensagem
            media_url: URL da mídia (imagem, documento, etc)
            media_type: Tipo da mídia ('image', 'document', 'audio')

        Returns:
            Dict com resultado do envio
        """
        # Formata telefone
        telefone = self._formatar_telefone(telefone)

        # Modo mock se não houver configuração
        if not self.config.evolution_key and not self.config.twilio_sid:
            return await self._enviar_mock(telefone, mensagem)

        if self.config.provider == 'evolution':
            return await self._enviar_evolution(telefone, mensagem, media_url, media_type)
        else:
            return await self._enviar_twilio(telefone, mensagem, media_url)

    def _formatar_telefone(self, telefone: str) -> str:
        """Formata número de telefone para padrão internacional"""
        # Remove caracteres não numéricos
        telefone = ''.join(filter(str.isdigit, telefone))

        # Adiciona código do país se não tiver
        if len(telefone) == 11:  # DDD + número
            telefone = '55' + telefone
        elif len(telefone) == 10:  # DDD + número antigo
            telefone = '55' + telefone

        return telefone

    async def _enviar_mock(self, telefone: str, mensagem: str) -> Dict[str, Any]:
        """Simula envio de WhatsApp"""
        return {
            'sucesso': True,
            'modo': 'mock',
            'telefone': telefone,
            'mensagem': mensagem[:100] + '...' if len(mensagem) > 100 else mensagem,
            'timestamp': datetime.now().isoformat(),
            'id': f"mock_{datetime.now().timestamp()}"
        }

    async def _enviar_evolution(
        self,
        telefone: str,
        mensagem: str,
        media_url: Optional[str] = None,
        media_type: str = 'image'
    ) -> Dict[str, Any]:
        """Envia via Evolution API"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'apikey': self.config.evolution_key,
                    'Content-Type': 'application/json'
                }

                # Endpoint de envio de texto
                url = f"{self.config.evolution_url}/message/sendText/{self.config.evolution_instance}"

                payload = {
                    'number': telefone,
                    'text': mensagem
                }

                # Se tiver mídia, usa endpoint diferente
                if media_url:
                    url = f"{self.config.evolution_url}/message/sendMedia/{self.config.evolution_instance}"
                    payload = {
                        'number': telefone,
                        'mediatype': media_type,
                        'media': media_url,
                        'caption': mensagem
                    }

                response = await client.post(url, json=payload, headers=headers, timeout=30)

                if response.status_code == 200 or response.status_code == 201:
                    data = response.json()
                    return {
                        'sucesso': True,
                        'modo': 'evolution',
                        'telefone': telefone,
                        'id': data.get('key', {}).get('id', ''),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    return {
                        'sucesso': False,
                        'erro': response.text,
                        'status_code': response.status_code,
                        'telefone': telefone
                    }

        except Exception as e:
            return {
                'sucesso': False,
                'erro': str(e),
                'telefone': telefone
            }

    async def _enviar_twilio(
        self,
        telefone: str,
        mensagem: str,
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envia via Twilio"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.config.twilio_sid}/Messages.json"

                data = {
                    'From': f"whatsapp:{self.config.twilio_from}",
                    'To': f"whatsapp:+{telefone}",
                    'Body': mensagem
                }

                if media_url:
                    data['MediaUrl'] = media_url

                response = await client.post(
                    url,
                    data=data,
                    auth=(self.config.twilio_sid, self.config.twilio_token),
                    timeout=30
                )

                if response.status_code == 201:
                    result = response.json()
                    return {
                        'sucesso': True,
                        'modo': 'twilio',
                        'telefone': telefone,
                        'id': result.get('sid', ''),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    return {
                        'sucesso': False,
                        'erro': response.text,
                        'status_code': response.status_code,
                        'telefone': telefone
                    }

        except Exception as e:
            return {
                'sucesso': False,
                'erro': str(e),
                'telefone': telefone
            }

    async def enviar_boleto(
        self,
        telefone: str,
        boleto: Dict[str, Any],
        condominio: Dict[str, Any],
        qrcode_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envia boleto via WhatsApp"""
        valor = f"{boleto.get('valor', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        vencimento = boleto.get('vencimento', '')
        if isinstance(vencimento, str) and len(vencimento) >= 10:
            vencimento = datetime.strptime(vencimento[:10], '%Y-%m-%d').strftime('%d/%m/%Y')

        mensagem = self.TEMPLATES['boleto'].format(
            condominio_nome=condominio.get('nome', 'Condomínio'),
            morador_nome=boleto.get('morador', 'Morador'),
            competencia=boleto.get('competencia', ''),
            vencimento=vencimento,
            valor=valor,
            pix_copia_cola=boleto.get('pix_copia_cola', ''),
            url_boleto=f"/financeiro/boletos/{boleto.get('id')}"
        )

        return await self.enviar_mensagem(telefone, mensagem, qrcode_url)

    async def enviar_lembrete(
        self,
        telefone: str,
        boleto: Dict[str, Any],
        dias_para_vencer: int
    ) -> Dict[str, Any]:
        """Envia lembrete de vencimento"""
        valor = f"{boleto.get('valor', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        vencimento = boleto.get('vencimento', '')
        if isinstance(vencimento, str) and len(vencimento) >= 10:
            vencimento = datetime.strptime(vencimento[:10], '%Y-%m-%d').strftime('%d/%m/%Y')

        quando = "hoje" if dias_para_vencer == 0 else f"em {dias_para_vencer} dia(s)" if dias_para_vencer > 0 else "amanhã"

        mensagem = self.TEMPLATES['lembrete'].format(
            morador_nome=boleto.get('morador', 'Morador'),
            quando=quando,
            competencia=boleto.get('competencia', ''),
            valor=valor,
            vencimento=vencimento,
            pix_copia_cola=boleto.get('pix_copia_cola', '')
        )

        return await self.enviar_mensagem(telefone, mensagem)

    async def enviar_cobranca(
        self,
        telefone: str,
        boletos: List[Dict],
        morador: Dict[str, Any],
        condominio: Dict[str, Any],
        dias_atraso: int,
        nivel: str = 'leve'
    ) -> Dict[str, Any]:
        """Envia cobrança via WhatsApp"""
        valor_total = sum(b.get('valor', 0) for b in boletos)
        valor_fmt = f"{valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        # Seleciona template baseado no nível
        if nivel == 'leve' and dias_atraso <= 15:
            template_key = 'cobranca_leve'
            boleto = boletos[0] if boletos else {}
            valor = f"{boleto.get('valor', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            vencimento = boleto.get('vencimento', '')
            if isinstance(vencimento, str) and len(vencimento) >= 10:
                vencimento = datetime.strptime(vencimento[:10], '%Y-%m-%d').strftime('%d/%m/%Y')

            mensagem = self.TEMPLATES[template_key].format(
                morador_nome=morador.get('nome', 'Morador'),
                competencia=boleto.get('competencia', ''),
                valor=valor,
                vencimento=vencimento,
                dias_atraso=dias_atraso,
                pix_copia_cola=boleto.get('pix_copia_cola', '')
            )
        elif nivel == 'media' or dias_atraso <= 30:
            mensagem = self.TEMPLATES['cobranca_media'].format(
                morador_nome=morador.get('nome', 'Morador'),
                dias_atraso=dias_atraso,
                valor_total=valor_fmt
            )
        else:
            mensagem = self.TEMPLATES['cobranca_grave'].format(
                morador_nome=morador.get('nome', 'Morador'),
                dias_atraso=dias_atraso,
                valor_total=valor_fmt,
                telefone_administracao=condominio.get('telefone', '(11) 3456-7890')
            )

        return await self.enviar_mensagem(telefone, mensagem)

    async def enviar_confirmacao_pagamento(
        self,
        telefone: str,
        boleto: Dict[str, Any],
        condominio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Envia confirmação de pagamento"""
        valor = boleto.get('valor_pago', boleto.get('valor', 0))
        valor_fmt = f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        data_pagamento = boleto.get('data_pagamento', '')
        if isinstance(data_pagamento, str) and len(data_pagamento) >= 10:
            data_pagamento = datetime.strptime(data_pagamento[:10], '%Y-%m-%d').strftime('%d/%m/%Y')

        mensagem = self.TEMPLATES['pagamento_confirmado'].format(
            morador_nome=boleto.get('morador', 'Morador'),
            condominio_nome=condominio.get('nome', 'Condomínio'),
            competencia=boleto.get('competencia', ''),
            valor=valor_fmt,
            data_pagamento=data_pagamento,
            forma_pagamento=boleto.get('forma_pagamento', 'PIX').upper()
        )

        return await self.enviar_mensagem(telefone, mensagem)


# Instância global
whatsapp_service = WhatsAppService()
