"""
Conecta Plus - Relatórios Financeiros Avançados
DRE, Balancete, Prestação de Contas
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from decimal import Decimal
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


@dataclass
class CategoriaContabil:
    """Categoria contábil para DRE"""
    codigo: str
    nome: str
    tipo: str  # 'receita' ou 'despesa'
    grupo: str
    valor: float = 0.0


class GeradorRelatorios:
    """Gera relatórios financeiros avançados"""

    # Estrutura do DRE
    ESTRUTURA_DRE = {
        'receitas_operacionais': {
            'nome': 'RECEITAS OPERACIONAIS',
            'categorias': [
                ('REC001', 'Taxa de Condomínio Ordinária'),
                ('REC002', 'Taxa de Condomínio Extraordinária'),
                ('REC003', 'Fundo de Reserva'),
                ('REC004', 'Multas e Juros de Atraso'),
                ('REC005', 'Aluguel de Áreas Comuns'),
                ('REC006', 'Outras Receitas'),
            ]
        },
        'despesas_pessoal': {
            'nome': 'DESPESAS COM PESSOAL',
            'categorias': [
                ('DES001', 'Salários e Ordenados'),
                ('DES002', 'Encargos Sociais (INSS, FGTS)'),
                ('DES003', 'Férias e 13º Salário'),
                ('DES004', 'Vale Transporte e Alimentação'),
                ('DES005', 'Uniformes e EPIs'),
            ]
        },
        'despesas_manutencao': {
            'nome': 'DESPESAS DE MANUTENÇÃO',
            'categorias': [
                ('DES010', 'Manutenção Predial'),
                ('DES011', 'Manutenção de Elevadores'),
                ('DES012', 'Manutenção Hidráulica'),
                ('DES013', 'Manutenção Elétrica'),
                ('DES014', 'Jardinagem e Paisagismo'),
                ('DES015', 'Limpeza e Conservação'),
            ]
        },
        'despesas_consumo': {
            'nome': 'DESPESAS DE CONSUMO',
            'categorias': [
                ('DES020', 'Energia Elétrica'),
                ('DES021', 'Água e Esgoto'),
                ('DES022', 'Gás'),
                ('DES023', 'Telefone e Internet'),
                ('DES024', 'Material de Limpeza'),
                ('DES025', 'Material de Escritório'),
            ]
        },
        'despesas_servicos': {
            'nome': 'DESPESAS COM SERVIÇOS',
            'categorias': [
                ('DES030', 'Administração'),
                ('DES031', 'Segurança e Vigilância'),
                ('DES032', 'Seguros'),
                ('DES033', 'Assessoria Jurídica'),
                ('DES034', 'Assessoria Contábil'),
                ('DES035', 'Outros Serviços'),
            ]
        },
        'despesas_tributarias': {
            'nome': 'DESPESAS TRIBUTÁRIAS',
            'categorias': [
                ('DES040', 'IPTU'),
                ('DES041', 'Taxas Municipais'),
                ('DES042', 'Tributos Diversos'),
            ]
        }
    }

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Configura estilos de relatório"""
        self.styles.add(ParagraphStyle(
            name='TituloRelatorio',
            fontSize=16,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        self.styles.add(ParagraphStyle(
            name='SubtituloRelatorio',
            fontSize=12,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=10
        ))
        self.styles.add(ParagraphStyle(
            name='TextoNormal',
            fontSize=10,
            fontName='Helvetica',
            alignment=TA_LEFT
        ))
        self.styles.add(ParagraphStyle(
            name='ValorMonetario',
            fontSize=10,
            fontName='Helvetica',
            alignment=TA_RIGHT
        ))

    def gerar_dre(
        self,
        lancamentos: List[Dict],
        mes: int,
        ano: int,
        condominio: Dict[str, Any]
    ) -> bytes:
        """
        Gera DRE (Demonstrativo de Resultado do Exercício)

        Args:
            lancamentos: Lista de lançamentos do período
            mes: Mês de referência
            ano: Ano de referência
            condominio: Dados do condomínio

        Returns:
            bytes: PDF do DRE
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
        elements = []

        # Cabeçalho
        elements.append(Paragraph(condominio.get('nome', 'CONDOMÍNIO'), self.styles['TituloRelatorio']))
        elements.append(Paragraph(
            f"DEMONSTRATIVO DE RESULTADO DO EXERCÍCIO<br/>Período: {mes:02d}/{ano}",
            self.styles['SubtituloRelatorio']
        ))
        elements.append(Spacer(1, 10*mm))

        # Processa lançamentos
        totais_categoria = self._processar_lancamentos(lancamentos)

        # Monta tabela do DRE
        data = [['DESCRIÇÃO', 'VALOR (R$)']]

        total_receitas = 0
        total_despesas = 0

        # Receitas
        for grupo_key, grupo in self.ESTRUTURA_DRE.items():
            if 'receita' in grupo_key:
                data.append([grupo['nome'], ''])
                for codigo, nome in grupo['categorias']:
                    valor = totais_categoria.get(codigo, 0)
                    total_receitas += valor
                    valor_fmt = self._formatar_valor(valor) if valor else '-'
                    data.append([f"    {nome}", valor_fmt])
                data.append(['', ''])

        data.append(['TOTAL RECEITAS', self._formatar_valor(total_receitas)])
        data.append(['', ''])

        # Despesas
        for grupo_key, grupo in self.ESTRUTURA_DRE.items():
            if 'despesa' in grupo_key:
                data.append([grupo['nome'], ''])
                for codigo, nome in grupo['categorias']:
                    valor = totais_categoria.get(codigo, 0)
                    total_despesas += valor
                    valor_fmt = self._formatar_valor(valor) if valor else '-'
                    data.append([f"    {nome}", valor_fmt])
                data.append(['', ''])

        data.append(['TOTAL DESPESAS', self._formatar_valor(total_despesas)])
        data.append(['', ''])

        # Resultado
        resultado = total_receitas - total_despesas
        resultado_fmt = self._formatar_valor(resultado)
        status = 'SUPERÁVIT' if resultado >= 0 else 'DÉFICIT'
        data.append([f'RESULTADO DO PERÍODO ({status})', resultado_fmt])

        # Cria tabela
        table = Table(data, colWidths=[130*mm, 50*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dbeafe')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(table)

        # Rodapé
        elements.append(Spacer(1, 15*mm))
        elements.append(Paragraph(
            f"<i>Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>",
            self.styles['TextoNormal']
        ))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def gerar_balancete(
        self,
        lancamentos: List[Dict],
        saldo_anterior: float,
        mes: int,
        ano: int,
        condominio: Dict[str, Any]
    ) -> bytes:
        """
        Gera Balancete Mensal

        Args:
            lancamentos: Lista de lançamentos do período
            saldo_anterior: Saldo do mês anterior
            mes: Mês de referência
            ano: Ano de referência
            condominio: Dados do condomínio

        Returns:
            bytes: PDF do Balancete
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
        elements = []

        # Cabeçalho
        elements.append(Paragraph(condominio.get('nome', 'CONDOMÍNIO'), self.styles['TituloRelatorio']))
        elements.append(Paragraph(
            f"BALANCETE MENSAL<br/>Período: {mes:02d}/{ano}",
            self.styles['SubtituloRelatorio']
        ))
        elements.append(Spacer(1, 10*mm))

        # Resumo
        totais = self._processar_lancamentos(lancamentos)
        total_receitas = sum(v for k, v in totais.items() if k.startswith('REC'))
        total_despesas = sum(v for k, v in totais.items() if k.startswith('DES'))
        saldo_atual = saldo_anterior + total_receitas - total_despesas

        resumo_data = [
            ['RESUMO FINANCEIRO', 'VALOR (R$)'],
            ['Saldo Anterior', self._formatar_valor(saldo_anterior)],
            ['(+) Total de Receitas', self._formatar_valor(total_receitas)],
            ['(-) Total de Despesas', self._formatar_valor(total_despesas)],
            ['(=) Saldo Atual', self._formatar_valor(saldo_atual)],
        ]

        resumo_table = Table(resumo_data, colWidths=[130*mm, 50*mm])
        resumo_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a34a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dcfce7')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(resumo_table)
        elements.append(Spacer(1, 10*mm))

        # Detalhamento de Receitas
        elements.append(Paragraph('RECEITAS', self.styles['SubtituloRelatorio']))
        receitas_data = [['Código', 'Descrição', 'Valor (R$)']]

        for codigo, valor in sorted(totais.items()):
            if codigo.startswith('REC') and valor > 0:
                nome = self._get_nome_categoria(codigo)
                receitas_data.append([codigo, nome, self._formatar_valor(valor)])

        receitas_data.append(['', 'TOTAL RECEITAS', self._formatar_valor(total_receitas)])

        receitas_table = Table(receitas_data, colWidths=[25*mm, 115*mm, 40*mm])
        receitas_table.setStyle(self._get_table_style())
        elements.append(receitas_table)
        elements.append(Spacer(1, 10*mm))

        # Detalhamento de Despesas
        elements.append(Paragraph('DESPESAS', self.styles['SubtituloRelatorio']))
        despesas_data = [['Código', 'Descrição', 'Valor (R$)']]

        for codigo, valor in sorted(totais.items()):
            if codigo.startswith('DES') and valor > 0:
                nome = self._get_nome_categoria(codigo)
                despesas_data.append([codigo, nome, self._formatar_valor(valor)])

        despesas_data.append(['', 'TOTAL DESPESAS', self._formatar_valor(total_despesas)])

        despesas_table = Table(despesas_data, colWidths=[25*mm, 115*mm, 40*mm])
        despesas_table.setStyle(self._get_table_style())
        elements.append(despesas_table)

        # Rodapé
        elements.append(Spacer(1, 15*mm))
        elements.append(Paragraph(
            f"<i>Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>",
            self.styles['TextoNormal']
        ))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def gerar_prestacao_contas(
        self,
        lancamentos: List[Dict],
        boletos: List[Dict],
        saldo_inicial: float,
        periodo_inicio: date,
        periodo_fim: date,
        condominio: Dict[str, Any]
    ) -> bytes:
        """
        Gera Prestação de Contas para Assembleia

        Args:
            lancamentos: Lista de lançamentos do período
            boletos: Lista de boletos do período
            saldo_inicial: Saldo no início do período
            periodo_inicio: Data de início
            periodo_fim: Data de fim
            condominio: Dados do condomínio

        Returns:
            bytes: PDF da Prestação de Contas
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
        elements = []

        # Cabeçalho
        elements.append(Paragraph(condominio.get('nome', 'CONDOMÍNIO'), self.styles['TituloRelatorio']))
        elements.append(Paragraph(
            f"PRESTAÇÃO DE CONTAS<br/>"
            f"Período: {periodo_inicio.strftime('%d/%m/%Y')} a {periodo_fim.strftime('%d/%m/%Y')}",
            self.styles['SubtituloRelatorio']
        ))
        elements.append(Spacer(1, 10*mm))

        # Processa dados
        totais = self._processar_lancamentos(lancamentos)
        total_receitas = sum(v for k, v in totais.items() if k.startswith('REC'))
        total_despesas = sum(v for k, v in totais.items() if k.startswith('DES'))
        saldo_final = saldo_inicial + total_receitas - total_despesas

        # Estatísticas de boletos
        total_boletos = len(boletos)
        boletos_pagos = len([b for b in boletos if b.get('status') == 'pago'])
        boletos_vencidos = len([b for b in boletos if b.get('status') == 'vencido'])
        valor_arrecadado = sum(b.get('valor_pago', b.get('valor', 0)) for b in boletos if b.get('status') == 'pago')
        valor_inadimplente = sum(b.get('valor', 0) for b in boletos if b.get('status') == 'vencido')
        taxa_inadimplencia = (boletos_vencidos / total_boletos * 100) if total_boletos > 0 else 0

        # 1. Resumo Executivo
        elements.append(Paragraph('<b>1. RESUMO EXECUTIVO</b>', self.styles['SubtituloRelatorio']))
        elements.append(Spacer(1, 5*mm))

        resumo_texto = f"""
        Este documento apresenta a prestação de contas do <b>{condominio.get('nome', 'Condomínio')}</b>
        referente ao período de {periodo_inicio.strftime('%d/%m/%Y')} a {periodo_fim.strftime('%d/%m/%Y')}.

        Durante o período, foram arrecadados <b>{self._formatar_valor(total_receitas)}</b> em receitas
        e realizadas despesas no valor total de <b>{self._formatar_valor(total_despesas)}</b>,
        resultando em {'superávit' if saldo_final >= saldo_inicial else 'déficit'}
        de <b>{self._formatar_valor(abs(saldo_final - saldo_inicial))}</b>.

        A taxa de inadimplência no período foi de <b>{taxa_inadimplencia:.1f}%</b>,
        correspondendo a <b>{self._formatar_valor(valor_inadimplente)}</b> em valores não recebidos.
        """
        elements.append(Paragraph(resumo_texto, self.styles['TextoNormal']))
        elements.append(Spacer(1, 10*mm))

        # 2. Movimentação Financeira
        elements.append(Paragraph('<b>2. MOVIMENTAÇÃO FINANCEIRA</b>', self.styles['SubtituloRelatorio']))
        elements.append(Spacer(1, 5*mm))

        mov_data = [
            ['Descrição', 'Valor (R$)'],
            ['Saldo Inicial do Período', self._formatar_valor(saldo_inicial)],
            ['(+) Receitas Recebidas', self._formatar_valor(total_receitas)],
            ['(-) Despesas Realizadas', self._formatar_valor(total_despesas)],
            ['(=) Saldo Final do Período', self._formatar_valor(saldo_final)],
            ['', ''],
            ['Variação no Período', self._formatar_valor(saldo_final - saldo_inicial)],
        ]

        mov_table = Table(mov_data, colWidths=[130*mm, 50*mm])
        mov_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -4), 0.5, colors.grey),
            ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#dbeafe')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(mov_table)
        elements.append(Spacer(1, 10*mm))

        # 3. Arrecadação
        elements.append(Paragraph('<b>3. SITUAÇÃO DA ARRECADAÇÃO</b>', self.styles['SubtituloRelatorio']))
        elements.append(Spacer(1, 5*mm))

        arrec_data = [
            ['Indicador', 'Quantidade', 'Valor (R$)'],
            ['Total de Boletos Emitidos', str(total_boletos), '-'],
            ['Boletos Pagos', str(boletos_pagos), self._formatar_valor(valor_arrecadado)],
            ['Boletos em Aberto/Vencidos', str(boletos_vencidos), self._formatar_valor(valor_inadimplente)],
            ['Taxa de Adimplência', f'{100 - taxa_inadimplencia:.1f}%', '-'],
            ['Taxa de Inadimplência', f'{taxa_inadimplencia:.1f}%', '-'],
        ]

        arrec_table = Table(arrec_data, colWidths=[100*mm, 40*mm, 40*mm])
        arrec_table.setStyle(self._get_table_style())
        elements.append(arrec_table)
        elements.append(Spacer(1, 10*mm))

        # 4. Assinaturas
        elements.append(PageBreak())
        elements.append(Paragraph('<b>4. APROVAÇÃO</b>', self.styles['SubtituloRelatorio']))
        elements.append(Spacer(1, 20*mm))

        assinaturas = """
        Declaramos que as informações contidas neste documento são verdadeiras e
        correspondem fielmente às movimentações financeiras do condomínio no período indicado.


        Local e Data: _________________________________, _____ de _________________ de _______



        _________________________________________
        Síndico(a)
        Nome: ___________________________________



        _________________________________________
        Conselho Fiscal
        Nome: ___________________________________



        _________________________________________
        Conselho Fiscal
        Nome: ___________________________________
        """
        elements.append(Paragraph(assinaturas, self.styles['TextoNormal']))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def _processar_lancamentos(self, lancamentos: List[Dict]) -> Dict[str, float]:
        """Processa lançamentos e agrupa por categoria"""
        totais = {}
        for lanc in lancamentos:
            categoria = lanc.get('categoria_id', lanc.get('categoria', 'OUTROS'))
            valor = lanc.get('valor', 0)
            totais[categoria] = totais.get(categoria, 0) + valor
        return totais

    def _formatar_valor(self, valor: float) -> str:
        """Formata valor monetário"""
        if valor < 0:
            return f"({abs(valor):,.2f})".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    def _get_nome_categoria(self, codigo: str) -> str:
        """Retorna nome da categoria pelo código"""
        for grupo in self.ESTRUTURA_DRE.values():
            for cod, nome in grupo['categorias']:
                if cod == codigo:
                    return nome
        return codigo

    def _get_table_style(self) -> TableStyle:
        """Retorna estilo padrão de tabela"""
        return TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8fafc')]),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e5e7eb')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ])


# Instância global
gerador_relatorios = GeradorRelatorios()
