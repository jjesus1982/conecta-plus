"""
Conecta Plus - Gerador de PDF de Boletos
Gera boletos bancários em PDF com código de barras
"""

import io
import base64
from datetime import date, datetime
from typing import Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.common import I2of5


class GeradorPDFBoleto:
    """Gera PDF de boletos bancários"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Configura estilos personalizados"""
        self.styles.add(ParagraphStyle(
            name='TituloBoleto',
            fontSize=14,
            fontName='Helvetica-Bold',
            spaceAfter=10
        ))
        self.styles.add(ParagraphStyle(
            name='CampoBoleto',
            fontSize=8,
            fontName='Helvetica',
            leading=10
        ))
        self.styles.add(ParagraphStyle(
            name='ValorBoleto',
            fontSize=12,
            fontName='Helvetica-Bold',
            alignment=2  # Right
        ))

    def gerar_boleto_pdf(
        self,
        boleto: Dict[str, Any],
        beneficiario: Dict[str, Any],
        qrcode_base64: Optional[str] = None
    ) -> bytes:
        """
        Gera PDF do boleto

        Args:
            boleto: Dados do boleto
            beneficiario: Dados do beneficiário (condomínio)
            qrcode_base64: QR Code PIX em base64 (opcional)

        Returns:
            bytes: PDF gerado
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )

        elements = []

        # Cabeçalho
        elements.append(self._criar_cabecalho(boleto, beneficiario))
        elements.append(Spacer(1, 5*mm))

        # Linha pontilhada (recibo do pagador)
        elements.append(self._criar_linha_pontilhada())
        elements.append(Spacer(1, 3*mm))

        # Recibo do Pagador
        elements.append(Paragraph("RECIBO DO PAGADOR", self.styles['TituloBoleto']))
        elements.append(self._criar_recibo_pagador(boleto, beneficiario))
        elements.append(Spacer(1, 5*mm))

        # Linha pontilhada
        elements.append(self._criar_linha_pontilhada())
        elements.append(Spacer(1, 3*mm))

        # Ficha de Compensação
        elements.append(Paragraph("FICHA DE COMPENSAÇÃO", self.styles['TituloBoleto']))
        elements.append(self._criar_ficha_compensacao(boleto, beneficiario))
        elements.append(Spacer(1, 5*mm))

        # Código de Barras
        if boleto.get('codigo_barras'):
            elements.append(self._criar_codigo_barras(boleto['codigo_barras']))
            elements.append(Spacer(1, 3*mm))

        # Linha Digitável
        if boleto.get('linha_digitavel'):
            elements.append(Paragraph(
                f"<b>Linha Digitável:</b> {boleto['linha_digitavel']}",
                self.styles['CampoBoleto']
            ))
        elements.append(Spacer(1, 5*mm))

        # QR Code PIX (se disponível)
        if qrcode_base64 and boleto.get('pix_copia_cola'):
            elements.append(self._criar_secao_pix(boleto, qrcode_base64))

        # Instruções
        elements.append(Spacer(1, 5*mm))
        elements.append(self._criar_instrucoes())

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def _criar_cabecalho(self, boleto: Dict, beneficiario: Dict) -> Table:
        """Cria cabeçalho do boleto"""
        banco_codigo = boleto.get('banco_codigo', '077')
        banco_nome = boleto.get('banco', 'Inter')

        data = [
            [
                Paragraph(f"<b>{banco_nome}</b>", self.styles['TituloBoleto']),
                Paragraph(f"<b>{banco_codigo}-5</b>", self.styles['TituloBoleto']),
                Paragraph(boleto.get('linha_digitavel', ''), self.styles['CampoBoleto'])
            ]
        ]

        table = Table(data, colWidths=[60*mm, 30*mm, 90*mm])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        return table

    def _criar_recibo_pagador(self, boleto: Dict, beneficiario: Dict) -> Table:
        """Cria seção do recibo do pagador"""
        vencimento = boleto.get('vencimento', '')
        if isinstance(vencimento, str) and len(vencimento) >= 10:
            vencimento = datetime.strptime(vencimento[:10], '%Y-%m-%d').strftime('%d/%m/%Y')

        valor = boleto.get('valor', 0)
        valor_formatado = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        data = [
            ['Beneficiário', beneficiario.get('nome', 'Condomínio'), 'Vencimento', vencimento],
            ['CNPJ', beneficiario.get('documento', ''), 'Valor', valor_formatado],
            ['Pagador', boleto.get('morador', ''), 'Nosso Número', boleto.get('nosso_numero', '')],
            ['Documento', boleto.get('pagador_documento', ''), 'Competência', boleto.get('competencia', '')],
        ]

        table = Table(data, colWidths=[25*mm, 70*mm, 25*mm, 60*mm])
        table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        return table

    def _criar_ficha_compensacao(self, boleto: Dict, beneficiario: Dict) -> Table:
        """Cria ficha de compensação"""
        vencimento = boleto.get('vencimento', '')
        if isinstance(vencimento, str) and len(vencimento) >= 10:
            vencimento = datetime.strptime(vencimento[:10], '%Y-%m-%d').strftime('%d/%m/%Y')

        valor = boleto.get('valor', 0)
        valor_formatado = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        descricao = boleto.get('descricao', 'Taxa de Condomínio')

        data = [
            ['Local de Pagamento', 'PAGÁVEL EM QUALQUER BANCO ATÉ O VENCIMENTO'],
            ['Beneficiário', f"{beneficiario.get('nome', '')} - CNPJ: {beneficiario.get('documento', '')}"],
            ['Data Documento', datetime.now().strftime('%d/%m/%Y')],
            ['Número Documento', boleto.get('id', '')],
            ['Espécie', 'R$'],
            ['Aceite', 'N'],
            ['Data Processamento', datetime.now().strftime('%d/%m/%Y')],
            ['Nosso Número', boleto.get('nosso_numero', '')],
            ['Uso do Banco', ''],
            ['Carteira', 'SR'],
            ['Moeda', 'Real'],
            ['Quantidade', ''],
            ['Valor Documento', valor_formatado],
            ['Vencimento', vencimento],
            ['Agência/Código', f"0001 / {beneficiario.get('conta', '12345678')}"],
        ]

        # Instruções
        instrucoes = [
            f"Descrição: {descricao}",
            f"Competência: {boleto.get('competencia', '')}",
            "Após vencimento cobrar multa de 2% + juros de 1% ao mês",
            "Não receber após 30 dias do vencimento",
        ]

        data.append(['Instruções', '\n'.join(instrucoes)])

        # Pagador
        pagador_info = f"{boleto.get('morador', '')} - {boleto.get('unidade', '')}"
        data.append(['Pagador', pagador_info])

        table = Table(data, colWidths=[35*mm, 145*mm])
        table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        return table

    def _criar_codigo_barras(self, codigo: str) -> Drawing:
        """Cria código de barras I2of5"""
        drawing = Drawing(180*mm, 15*mm)

        try:
            # Código de barras intercalado 2 de 5
            barcode = I2of5(
                codigo,
                barWidth=0.38*mm,
                barHeight=12*mm,
                humanReadable=False
            )
            # Posiciona o barcode
            barcode.x = 0
            barcode.y = 0
            drawing.add(barcode)
        except Exception as e:
            # Se falhar, cria um placeholder
            from reportlab.graphics.shapes import String
            text = String(10, 5, f"Código: {codigo[:20]}...")
            text.fontSize = 8
            drawing.add(text)

        return drawing

    def _criar_secao_pix(self, boleto: Dict, qrcode_base64: str) -> Table:
        """Cria seção do PIX com QR Code"""
        # Decodifica base64 para criar imagem
        if qrcode_base64.startswith('data:image'):
            qrcode_base64 = qrcode_base64.split(',')[1]

        qr_data = base64.b64decode(qrcode_base64)
        qr_buffer = io.BytesIO(qr_data)
        qr_image = Image(qr_buffer, width=40*mm, height=40*mm)

        pix_code = boleto.get('pix_copia_cola', '')[:50] + '...' if len(boleto.get('pix_copia_cola', '')) > 50 else boleto.get('pix_copia_cola', '')

        data = [
            [qr_image, Paragraph(
                f"<b>PIX COPIA E COLA</b><br/><br/>"
                f"Escaneie o QR Code ou copie o código abaixo:<br/><br/>"
                f"<font size='6'>{pix_code}</font>",
                self.styles['CampoBoleto']
            )]
        ]

        table = Table(data, colWidths=[50*mm, 130*mm])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0066CC')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0F8FF')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]))

        return table

    def _criar_linha_pontilhada(self) -> Paragraph:
        """Cria linha pontilhada para recorte"""
        return Paragraph(
            "- " * 95,
            ParagraphStyle(name='Pontilhado', fontSize=6, textColor=colors.grey)
        )

    def _criar_instrucoes(self) -> Table:
        """Cria seção de instruções"""
        instrucoes = [
            "INSTRUÇÕES:",
            "1. Este boleto pode ser pago em qualquer banco até a data de vencimento.",
            "2. Após o vencimento, será cobrado multa de 2% e juros de 1% ao mês.",
            "3. Em caso de dúvidas, entre em contato com a administração do condomínio.",
            "4. O pagamento via PIX é processado instantaneamente.",
        ]

        data = [[Paragraph('<br/>'.join(instrucoes), self.styles['CampoBoleto'])]]

        table = Table(data, colWidths=[180*mm])
        table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFAF0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]))

        return table

    def gerar_boleto_base64(
        self,
        boleto: Dict[str, Any],
        beneficiario: Dict[str, Any],
        qrcode_base64: Optional[str] = None
    ) -> str:
        """
        Gera PDF como string Base64

        Returns:
            str: PDF em formato data:application/pdf;base64,...
        """
        pdf_bytes = self.gerar_boleto_pdf(boleto, beneficiario, qrcode_base64)
        b64 = base64.b64encode(pdf_bytes).decode('utf-8')
        return f"data:application/pdf;base64,{b64}"


# Instância global
pdf_generator = GeradorPDFBoleto()


def gerar_pdf_boleto(
    boleto: Dict[str, Any],
    beneficiario: Dict[str, Any] = None,
    qrcode_base64: str = None
) -> bytes:
    """Função utilitária para gerar PDF de boleto"""
    if beneficiario is None:
        beneficiario = {
            'nome': 'Residencial Conecta Plus',
            'documento': '12.345.678/0001-90',
            'conta': '12345678'
        }
    return pdf_generator.gerar_boleto_pdf(boleto, beneficiario, qrcode_base64)
