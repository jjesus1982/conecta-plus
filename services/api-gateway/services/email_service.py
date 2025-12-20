"""
Conecta Plus - Serviço de Email
Envio de emails transacionais (boletos, cobranças, notificações)
"""

import os
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib
from jinja2 import Template


@dataclass
class ConfiguracaoEmail:
    """Configuração do servidor de email"""
    smtp_host: str = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port: int = int(os.getenv('SMTP_PORT', '587'))
    smtp_user: str = os.getenv('SMTP_USER', '')
    smtp_pass: str = os.getenv('SMTP_PASS', '')
    smtp_tls: bool = True
    from_email: str = os.getenv('FROM_EMAIL', 'noreply@conectaplus.com.br')
    from_name: str = 'Conecta Plus'


class EmailService:
    """Serviço de envio de emails"""

    # Templates de email
    TEMPLATES = {
        'boleto': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }
        .valor { font-size: 28px; font-weight: bold; color: #2563eb; text-align: center; margin: 20px 0; }
        .info-box { background: white; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
        .btn { display: inline-block; background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 10px 5px; }
        .btn-pix { background: #00A868; }
        .pix-code { background: #f0f0f0; padding: 10px; border-radius: 4px; word-break: break-all; font-family: monospace; font-size: 12px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
        .qrcode { text-align: center; margin: 20px 0; }
        .qrcode img { max-width: 200px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ condominio_nome }}</h1>
            <p>Boleto de Condomínio</p>
        </div>
        <div class="content">
            <p>Olá <strong>{{ morador_nome }}</strong>,</p>
            <p>Segue o boleto referente à competência <strong>{{ competencia }}</strong>.</p>

            <div class="valor">R$ {{ valor }}</div>

            <div class="info-box">
                <div class="info-row">
                    <span>Unidade:</span>
                    <strong>{{ unidade }}</strong>
                </div>
                <div class="info-row">
                    <span>Competência:</span>
                    <strong>{{ competencia }}</strong>
                </div>
                <div class="info-row">
                    <span>Vencimento:</span>
                    <strong>{{ vencimento }}</strong>
                </div>
                <div class="info-row">
                    <span>Descrição:</span>
                    <strong>{{ descricao }}</strong>
                </div>
            </div>

            {% if pix_copia_cola %}
            <h3 style="color: #00A868;">Pague com PIX</h3>
            {% if qrcode_base64 %}
            <div class="qrcode">
                <img src="{{ qrcode_base64 }}" alt="QR Code PIX">
            </div>
            {% endif %}
            <p><strong>Código Copia e Cola:</strong></p>
            <div class="pix-code">{{ pix_copia_cola }}</div>
            {% endif %}

            <h3>Linha Digitável</h3>
            <div class="pix-code">{{ linha_digitavel }}</div>

            <div style="text-align: center; margin-top: 20px;">
                <a href="{{ url_boleto }}" class="btn">Baixar Boleto PDF</a>
            </div>
        </div>
        <div class="footer">
            <p>Este é um email automático, não responda.</p>
            <p>{{ condominio_nome }} - Gestão Conecta Plus</p>
        </div>
    </div>
</body>
</html>
        """,

        'cobranca': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc2626; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #fef2f2; padding: 20px; border: 1px solid #fecaca; }
        .valor { font-size: 28px; font-weight: bold; color: #dc2626; text-align: center; margin: 20px 0; }
        .info-box { background: white; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .btn { display: inline-block; background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Aviso de Cobrança</h1>
            <p>{{ condominio_nome }}</p>
        </div>
        <div class="content">
            <p>Prezado(a) <strong>{{ morador_nome }}</strong>,</p>

            <p>Identificamos que existe(m) pendência(s) financeira(s) em seu nome:</p>

            <div class="valor">R$ {{ valor_total }}</div>
            <p style="text-align: center; color: #dc2626;">{{ dias_atraso }} dia(s) em atraso</p>

            <div class="info-box">
                {% for boleto in boletos %}
                <div style="padding: 10px 0; border-bottom: 1px solid #eee;">
                    <strong>{{ boleto.competencia }}</strong> - R$ {{ boleto.valor }}
                    <br><small>Vencimento: {{ boleto.vencimento }}</small>
                </div>
                {% endfor %}
            </div>

            <p>Para regularizar sua situação, entre em contato com a administração ou efetue o pagamento.</p>

            {% if permite_acordo %}
            <p style="background: #dbeafe; padding: 15px; border-radius: 8px;">
                <strong>Proposta de Acordo:</strong><br>
                Você pode parcelar sua dívida em até {{ max_parcelas }}x com desconto de {{ desconto }}%.
            </p>
            {% endif %}

            <div style="text-align: center; margin-top: 20px;">
                <a href="{{ url_segunda_via }}" class="btn">Emitir Segunda Via</a>
            </div>
        </div>
        <div class="footer">
            <p>Este é um email automático do sistema de cobrança.</p>
            <p>{{ condominio_nome }}</p>
        </div>
    </div>
</body>
</html>
        """,

        'pagamento_confirmado': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #16a34a; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f0fdf4; padding: 20px; border: 1px solid #bbf7d0; }
        .valor { font-size: 28px; font-weight: bold; color: #16a34a; text-align: center; margin: 20px 0; }
        .check { font-size: 60px; text-align: center; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Pagamento Confirmado!</h1>
        </div>
        <div class="content">
            <div class="check">✓</div>
            <p style="text-align: center;">Olá <strong>{{ morador_nome }}</strong>,</p>
            <p style="text-align: center;">Recebemos seu pagamento com sucesso!</p>

            <div class="valor">R$ {{ valor }}</div>

            <div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <p><strong>Competência:</strong> {{ competencia }}</p>
                <p><strong>Data do Pagamento:</strong> {{ data_pagamento }}</p>
                <p><strong>Forma de Pagamento:</strong> {{ forma_pagamento }}</p>
            </div>

            <p style="text-align: center;">Obrigado por manter suas obrigações em dia!</p>
        </div>
        <div class="footer">
            <p>{{ condominio_nome }}</p>
        </div>
    </div>
</body>
</html>
        """
    }

    def __init__(self, config: ConfiguracaoEmail = None):
        self.config = config or ConfiguracaoEmail()

    async def enviar_email(
        self,
        para: str,
        assunto: str,
        corpo_html: str,
        anexos: List[Dict[str, Any]] = None,
        cc: List[str] = None,
        bcc: List[str] = None
    ) -> Dict[str, Any]:
        """
        Envia email

        Args:
            para: Email do destinatário
            assunto: Assunto do email
            corpo_html: Corpo do email em HTML
            anexos: Lista de anexos [{'nome': 'file.pdf', 'dados': bytes, 'tipo': 'application/pdf'}]
            cc: Lista de emails em cópia
            bcc: Lista de emails em cópia oculta

        Returns:
            Dict com resultado do envio
        """
        try:
            # Cria mensagem
            msg = MIMEMultipart()
            msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
            msg['To'] = para
            msg['Subject'] = assunto

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Corpo HTML
            msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))

            # Anexos
            if anexos:
                for anexo in anexos:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(anexo['dados'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f"attachment; filename={anexo['nome']}"
                    )
                    msg.attach(part)

            # Destinatários
            destinatarios = [para]
            if cc:
                destinatarios.extend(cc)
            if bcc:
                destinatarios.extend(bcc)

            # Envia (modo mock se não houver credenciais)
            if not self.config.smtp_user or not self.config.smtp_pass:
                return {
                    'sucesso': True,
                    'modo': 'mock',
                    'destinatario': para,
                    'assunto': assunto,
                    'mensagem': 'Email simulado (credenciais não configuradas)'
                }

            # Envia via SMTP
            await aiosmtplib.send(
                msg,
                hostname=self.config.smtp_host,
                port=self.config.smtp_port,
                username=self.config.smtp_user,
                password=self.config.smtp_pass,
                start_tls=self.config.smtp_tls
            )

            return {
                'sucesso': True,
                'modo': 'real',
                'destinatario': para,
                'assunto': assunto,
                'mensagem': 'Email enviado com sucesso'
            }

        except Exception as e:
            return {
                'sucesso': False,
                'erro': str(e),
                'destinatario': para
            }

    async def enviar_boleto(
        self,
        email: str,
        boleto: Dict[str, Any],
        condominio: Dict[str, Any],
        pdf_anexo: bytes = None,
        qrcode_base64: str = None
    ) -> Dict[str, Any]:
        """Envia email com boleto"""
        # Formata valor
        valor = boleto.get('valor', 0)
        valor_fmt = f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        # Formata vencimento
        vencimento = boleto.get('vencimento', '')
        if isinstance(vencimento, str) and len(vencimento) >= 10:
            from datetime import datetime
            vencimento = datetime.strptime(vencimento[:10], '%Y-%m-%d').strftime('%d/%m/%Y')

        # Renderiza template
        template = Template(self.TEMPLATES['boleto'])
        html = template.render(
            condominio_nome=condominio.get('nome', 'Condomínio'),
            morador_nome=boleto.get('morador', 'Morador'),
            unidade=boleto.get('unidade', ''),
            competencia=boleto.get('competencia', ''),
            vencimento=vencimento,
            valor=valor_fmt,
            descricao=boleto.get('descricao', 'Taxa de Condomínio'),
            linha_digitavel=boleto.get('linha_digitavel', ''),
            pix_copia_cola=boleto.get('pix_copia_cola', ''),
            qrcode_base64=qrcode_base64,
            url_boleto=f"/api/financeiro/boletos/{boleto.get('id')}/pdf"
        )

        # Anexos
        anexos = []
        if pdf_anexo:
            anexos.append({
                'nome': f"boleto_{boleto.get('competencia', '').replace('/', '_')}.pdf",
                'dados': pdf_anexo,
                'tipo': 'application/pdf'
            })

        return await self.enviar_email(
            para=email,
            assunto=f"Boleto {boleto.get('competencia', '')} - {condominio.get('nome', 'Condomínio')}",
            corpo_html=html,
            anexos=anexos
        )

    async def enviar_cobranca(
        self,
        email: str,
        boletos: List[Dict],
        morador: Dict[str, Any],
        condominio: Dict[str, Any],
        dias_atraso: int,
        permite_acordo: bool = True
    ) -> Dict[str, Any]:
        """Envia email de cobrança"""
        valor_total = sum(b.get('valor', 0) for b in boletos)
        valor_fmt = f"{valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        # Formata boletos
        boletos_fmt = []
        for b in boletos:
            vencimento = b.get('vencimento', '')
            if isinstance(vencimento, str) and len(vencimento) >= 10:
                from datetime import datetime
                vencimento = datetime.strptime(vencimento[:10], '%Y-%m-%d').strftime('%d/%m/%Y')

            valor = f"{b.get('valor', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            boletos_fmt.append({
                'competencia': b.get('competencia', ''),
                'vencimento': vencimento,
                'valor': valor
            })

        template = Template(self.TEMPLATES['cobranca'])
        html = template.render(
            condominio_nome=condominio.get('nome', 'Condomínio'),
            morador_nome=morador.get('nome', 'Morador'),
            valor_total=valor_fmt,
            dias_atraso=dias_atraso,
            boletos=boletos_fmt,
            permite_acordo=permite_acordo,
            max_parcelas=6,
            desconto=5,
            url_segunda_via='/financeiro'
        )

        return await self.enviar_email(
            para=email,
            assunto=f"AVISO: Pendência Financeira - {condominio.get('nome', 'Condomínio')}",
            corpo_html=html
        )

    async def enviar_confirmacao_pagamento(
        self,
        email: str,
        boleto: Dict[str, Any],
        condominio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Envia confirmação de pagamento"""
        valor = boleto.get('valor_pago', boleto.get('valor', 0))
        valor_fmt = f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        data_pagamento = boleto.get('data_pagamento', '')
        if isinstance(data_pagamento, str) and len(data_pagamento) >= 10:
            from datetime import datetime
            data_pagamento = datetime.strptime(data_pagamento[:10], '%Y-%m-%d').strftime('%d/%m/%Y')

        template = Template(self.TEMPLATES['pagamento_confirmado'])
        html = template.render(
            condominio_nome=condominio.get('nome', 'Condomínio'),
            morador_nome=boleto.get('morador', 'Morador'),
            valor=valor_fmt,
            competencia=boleto.get('competencia', ''),
            data_pagamento=data_pagamento,
            forma_pagamento=boleto.get('forma_pagamento', 'PIX').upper()
        )

        return await self.enviar_email(
            para=email,
            assunto=f"Pagamento Confirmado - {boleto.get('competencia', '')}",
            corpo_html=html
        )


# Instância global
email_service = EmailService()
