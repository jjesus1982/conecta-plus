"""
Conecta Plus - Gerador de Boletos
Gera boletos no padrão FEBRABAN com código de barras válido
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
import math


@dataclass
class DadosBoleto:
    """Dados para geração do boleto"""
    valor: float
    vencimento: date
    beneficiario_nome: str
    beneficiario_documento: str  # CNPJ
    pagador_nome: str
    pagador_documento: str  # CPF ou CNPJ
    pagador_endereco: str
    nosso_numero: str
    numero_documento: Optional[str] = None
    descricao: Optional[str] = None
    instrucoes: Optional[list] = None

    # Dados bancários
    banco_codigo: str = "077"  # Inter por padrão
    agencia: str = "0001"
    conta: str = "12345678"
    carteira: str = "112"

    # Multa e juros
    multa_percentual: float = 2.0
    juros_mensal: float = 1.0

    # Desconto
    desconto_valor: float = 0.0
    desconto_data_limite: Optional[date] = None


class GeradorCodigoBarras:
    """
    Gera código de barras no padrão FEBRABAN

    Estrutura do código de barras (44 posições):
    - Posição 1-3: Código do banco
    - Posição 4: Código da moeda (9 = Real)
    - Posição 5: Dígito verificador geral
    - Posição 6-9: Fator de vencimento
    - Posição 10-19: Valor (10 posições, 8 inteiras + 2 decimais)
    - Posição 20-44: Campo livre (definido por cada banco)
    """

    # Data base para cálculo do fator de vencimento
    DATA_BASE = date(1997, 10, 7)

    # Módulo 11 - Pesos para cálculo
    PESOS_MODULO11 = [2, 3, 4, 5, 6, 7, 8, 9]

    @classmethod
    def gerar(cls, dados: DadosBoleto) -> Dict[str, str]:
        """
        Gera código de barras e linha digitável

        Returns:
            Dict com 'codigo_barras' e 'linha_digitavel'
        """
        # Calcula fator de vencimento
        fator_vencimento = cls._calcular_fator_vencimento(dados.vencimento)

        # Formata valor (10 posições sem pontos e vírgulas)
        valor_formatado = cls._formatar_valor(dados.valor)

        # Campo livre (posições 20-44) - específico por banco
        campo_livre = cls._gerar_campo_livre(dados)

        # Monta código sem dígito verificador
        codigo_sem_dv = (
            dados.banco_codigo +  # 3 posições
            "9" +                 # Moeda (Real)
            fator_vencimento +    # 4 posições
            valor_formatado +     # 10 posições
            campo_livre           # 25 posições
        )

        # Calcula dígito verificador geral
        dv_geral = cls._calcular_dv_mod11(codigo_sem_dv)

        # Monta código de barras completo (44 posições)
        codigo_barras = (
            codigo_sem_dv[:4] +   # Banco + Moeda
            str(dv_geral) +       # DV
            codigo_sem_dv[4:]     # Resto
        )

        # Gera linha digitável
        linha_digitavel = cls._gerar_linha_digitavel(codigo_barras)

        return {
            "codigo_barras": codigo_barras,
            "linha_digitavel": linha_digitavel,
            "codigo_barras_formatado": cls._formatar_codigo_barras(codigo_barras),
            "fator_vencimento": fator_vencimento,
            "nosso_numero_formatado": cls._formatar_nosso_numero(dados.nosso_numero, dados.banco_codigo)
        }

    @classmethod
    def _calcular_fator_vencimento(cls, vencimento: date) -> str:
        """
        Calcula fator de vencimento (dias desde 07/10/1997)

        Após 21/02/2025, o fator reseta e começa de 1000
        """
        # Data limite do primeiro ciclo
        data_limite_ciclo1 = date(2025, 2, 21)

        if vencimento <= data_limite_ciclo1:
            dias = (vencimento - cls.DATA_BASE).days
        else:
            # Novo ciclo a partir de 22/02/2025
            nova_base = date(2025, 2, 22)
            dias = 1000 + (vencimento - nova_base).days

        return str(dias).zfill(4)

    @classmethod
    def _formatar_valor(cls, valor: float) -> str:
        """Formata valor com 10 posições (8 inteiras + 2 decimais)"""
        # Remove pontos e vírgulas, converte para centavos
        centavos = int(round(valor * 100))
        return str(centavos).zfill(10)

    @classmethod
    def _gerar_campo_livre(cls, dados: DadosBoleto) -> str:
        """
        Gera campo livre (25 posições) - específico por banco

        Para Banco Inter (077) e outros bancos digitais:
        - Posições 20-23: Agência (4 dígitos)
        - Posições 24-25: Carteira (2 dígitos)
        - Posições 26-36: Nosso número (11 dígitos)
        - Posições 37-44: Conta (8 dígitos)
        """
        agencia = dados.agencia.zfill(4)[:4]
        carteira = dados.carteira.zfill(2)[:2]
        nosso_numero = dados.nosso_numero.zfill(11)[:11]
        conta = dados.conta.zfill(8)[:8]

        campo_livre = agencia + carteira + nosso_numero + conta

        # Garante 25 posições
        return campo_livre.ljust(25, '0')[:25]

    @classmethod
    def _calcular_dv_mod11(cls, codigo: str) -> int:
        """
        Calcula dígito verificador usando módulo 11

        Pesos de 2 a 9, da direita para esquerda
        """
        soma = 0
        peso_idx = 0

        for digito in reversed(codigo):
            if digito.isdigit():
                soma += int(digito) * cls.PESOS_MODULO11[peso_idx % 8]
                peso_idx += 1

        resto = soma % 11
        dv = 11 - resto

        # Regras especiais
        if dv == 0 or dv == 10 or dv == 11:
            return 1

        return dv

    @classmethod
    def _calcular_dv_mod10(cls, bloco: str) -> int:
        """
        Calcula dígito verificador usando módulo 10

        Usado para campos da linha digitável
        """
        soma = 0
        multiplicador = 2

        for digito in reversed(bloco):
            if digito.isdigit():
                resultado = int(digito) * multiplicador
                # Se resultado > 9, soma os dígitos
                if resultado > 9:
                    resultado = (resultado // 10) + (resultado % 10)
                soma += resultado
                multiplicador = 3 - multiplicador  # Alterna entre 2 e 1

        resto = soma % 10
        if resto == 0:
            return 0
        return 10 - resto

    @classmethod
    def _gerar_linha_digitavel(cls, codigo_barras: str) -> str:
        """
        Gera linha digitável a partir do código de barras

        Estrutura (47 posições em 5 campos):
        Campo 1: AAABC.CCCCX (11 dígitos)
        Campo 2: DDDDD.DDDDDX (12 dígitos)
        Campo 3: EEEEE.EEEEEEX (12 dígitos)
        Campo 4: F (1 dígito - DV geral)
        Campo 5: GGGGHHHHHHHHHHH (14 dígitos - fator + valor)
        """
        # Extrai partes do código de barras
        banco = codigo_barras[0:3]
        moeda = codigo_barras[3]
        dv_geral = codigo_barras[4]
        fator = codigo_barras[5:9]
        valor = codigo_barras[9:19]
        campo_livre = codigo_barras[19:44]

        # Campo 1: Banco + Moeda + 5 primeiros do campo livre
        campo1_base = banco + moeda + campo_livre[0:5]
        dv1 = cls._calcular_dv_mod10(campo1_base)
        campo1 = campo1_base[:5] + "." + campo1_base[5:] + str(dv1)

        # Campo 2: Posições 6-15 do campo livre
        campo2_base = campo_livre[5:15]
        dv2 = cls._calcular_dv_mod10(campo2_base)
        campo2 = campo2_base[:5] + "." + campo2_base[5:] + str(dv2)

        # Campo 3: Posições 16-25 do campo livre
        campo3_base = campo_livre[15:25]
        dv3 = cls._calcular_dv_mod10(campo3_base)
        campo3 = campo3_base[:5] + "." + campo3_base[5:] + str(dv3)

        # Campo 4: DV geral (já calculado)
        campo4 = dv_geral

        # Campo 5: Fator de vencimento + Valor
        campo5 = fator + valor

        return f"{campo1} {campo2} {campo3} {campo4} {campo5}"

    @classmethod
    def _formatar_codigo_barras(cls, codigo: str) -> str:
        """Formata código de barras para exibição"""
        # Agrupa em blocos de 5
        return ' '.join([codigo[i:i+5] for i in range(0, len(codigo), 5)])

    @classmethod
    def _formatar_nosso_numero(cls, nosso_numero: str, banco_codigo: str) -> str:
        """Formata nosso número conforme padrão do banco"""
        nn = nosso_numero.zfill(11)

        # Diferentes formatos por banco
        if banco_codigo in ["077", "212"]:  # Inter, Original
            return f"{nn[:3]}/{nn[3:]}"
        elif banco_codigo == "341":  # Itaú
            return f"{nn[:8]}-{nn[8]}"
        elif banco_codigo == "237":  # Bradesco
            return f"{nn[:11]}-{cls._calcular_dv_mod11(nn)}"
        else:
            return nn


class GeradorPIX:
    """
    Gera código PIX (EMV) para cobrança

    Segue padrão EMV QR Code definido pelo Banco Central
    """

    @classmethod
    def gerar_pix_cobranca(
        cls,
        chave_pix: str,
        valor: float,
        nome_beneficiario: str,
        cidade: str,
        txid: Optional[str] = None,
        descricao: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Gera código PIX copia e cola

        Args:
            chave_pix: Chave PIX do beneficiário
            valor: Valor da cobrança
            nome_beneficiario: Nome do beneficiário
            cidade: Cidade do beneficiário
            txid: ID da transação (opcional)
            descricao: Descrição da cobrança (opcional)

        Returns:
            Dict com 'emv' (copia e cola) e dados formatados
        """
        # Monta payload EMV
        payload_format_indicator = cls._campo("00", "01")  # Versão
        merchant_account = cls._gerar_merchant_account(chave_pix, descricao)
        merchant_category = cls._campo("52", "0000")  # Categoria genérica
        currency = cls._campo("53", "986")  # BRL
        valor_campo = cls._campo("54", f"{valor:.2f}")
        country = cls._campo("58", "BR")
        nome = cls._campo("59", cls._limpar_texto(nome_beneficiario)[:25])
        cidade_campo = cls._campo("60", cls._limpar_texto(cidade)[:15])
        additional_data = cls._gerar_additional_data(txid)

        # Monta EMV sem CRC
        emv_sem_crc = (
            payload_format_indicator +
            merchant_account +
            merchant_category +
            currency +
            valor_campo +
            country +
            nome +
            cidade_campo +
            additional_data +
            "6304"  # CRC placeholder
        )

        # Calcula CRC16
        crc = cls._calcular_crc16(emv_sem_crc)

        # EMV completo
        emv = emv_sem_crc + crc

        return {
            "emv": emv,
            "chave": chave_pix,
            "valor": valor,
            "txid": txid or ""
        }

    @classmethod
    def _campo(cls, id_campo: str, valor: str) -> str:
        """Formata um campo EMV (ID + Tamanho + Valor)"""
        tamanho = str(len(valor)).zfill(2)
        return f"{id_campo}{tamanho}{valor}"

    @classmethod
    def _gerar_merchant_account(cls, chave_pix: str, descricao: Optional[str]) -> str:
        """Gera campo 26 - Merchant Account Information"""
        gui = cls._campo("00", "br.gov.bcb.pix")
        chave = cls._campo("01", chave_pix)

        conteudo = gui + chave
        if descricao:
            desc_limpa = cls._limpar_texto(descricao)[:72]
            conteudo += cls._campo("02", desc_limpa)

        return cls._campo("26", conteudo)

    @classmethod
    def _gerar_additional_data(cls, txid: Optional[str]) -> str:
        """Gera campo 62 - Additional Data Field"""
        if not txid:
            txid = "***"  # Indica que TXID será gerado pelo PSP

        txid_limpo = cls._limpar_texto(txid)[:25]
        conteudo = cls._campo("05", txid_limpo)
        return cls._campo("62", conteudo)

    @classmethod
    def _limpar_texto(cls, texto: str) -> str:
        """Remove caracteres especiais do texto"""
        import unicodedata

        # Remove acentos
        texto = unicodedata.normalize('NFKD', texto)
        texto = texto.encode('ASCII', 'ignore').decode('ASCII')

        # Remove caracteres não permitidos
        permitidos = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ')
        texto = ''.join(c for c in texto if c in permitidos)

        return texto.strip()

    @classmethod
    def _calcular_crc16(cls, dados: str) -> str:
        """
        Calcula CRC16-CCITT-FALSE

        Polinômio: 0x1021
        Valor inicial: 0xFFFF
        """
        crc = 0xFFFF

        for char in dados:
            crc ^= ord(char) << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
                crc &= 0xFFFF

        return format(crc, '04X')


class GeradorBoleto:
    """
    Classe principal para geração de boletos completos
    """

    def __init__(
        self,
        banco_codigo: str = "077",
        agencia: str = "0001",
        conta: str = "12345678",
        beneficiario_nome: str = "Condomínio Residencial",
        beneficiario_documento: str = "12.345.678/0001-90",
        chave_pix: Optional[str] = None
    ):
        self.banco_codigo = banco_codigo
        self.agencia = agencia
        self.conta = conta
        self.beneficiario_nome = beneficiario_nome
        self.beneficiario_documento = beneficiario_documento
        self.chave_pix = chave_pix

        # Contador para nosso número
        self._contador = 1

    def gerar_nosso_numero(self) -> str:
        """Gera próximo nosso número"""
        nn = str(self._contador).zfill(11)
        self._contador += 1
        return nn

    def gerar(
        self,
        valor: float,
        vencimento: date,
        pagador_nome: str,
        pagador_documento: str,
        pagador_endereco: str = "",
        nosso_numero: Optional[str] = None,
        descricao: Optional[str] = None,
        instrucoes: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Gera boleto completo com código de barras e PIX

        Returns:
            Dict com todos os dados do boleto
        """
        # Gera nosso número se não fornecido
        if not nosso_numero:
            nosso_numero = self.gerar_nosso_numero()

        # Monta dados do boleto
        dados = DadosBoleto(
            valor=valor,
            vencimento=vencimento,
            beneficiario_nome=self.beneficiario_nome,
            beneficiario_documento=self.beneficiario_documento,
            pagador_nome=pagador_nome,
            pagador_documento=pagador_documento,
            pagador_endereco=pagador_endereco,
            nosso_numero=nosso_numero,
            descricao=descricao or f"Cobrança - {vencimento.strftime('%m/%Y')}",
            instrucoes=instrucoes,
            banco_codigo=self.banco_codigo,
            agencia=self.agencia,
            conta=self.conta
        )

        # Gera código de barras
        codigo_barras = GeradorCodigoBarras.gerar(dados)

        # Gera PIX se tiver chave
        pix = None
        if self.chave_pix:
            txid = f"COB{nosso_numero}"
            pix = GeradorPIX.gerar_pix_cobranca(
                chave_pix=self.chave_pix,
                valor=valor,
                nome_beneficiario=self.beneficiario_nome[:25],
                cidade="SAO PAULO",
                txid=txid,
                descricao=descricao
            )

        return {
            "nosso_numero": nosso_numero,
            "nosso_numero_formatado": codigo_barras["nosso_numero_formatado"],
            "codigo_barras": codigo_barras["codigo_barras"],
            "codigo_barras_formatado": codigo_barras["codigo_barras_formatado"],
            "linha_digitavel": codigo_barras["linha_digitavel"],
            "valor": valor,
            "vencimento": vencimento.isoformat(),
            "beneficiario": {
                "nome": self.beneficiario_nome,
                "documento": self.beneficiario_documento,
                "agencia": self.agencia,
                "conta": self.conta
            },
            "pagador": {
                "nome": pagador_nome,
                "documento": pagador_documento,
                "endereco": pagador_endereco
            },
            "pix": {
                "copia_cola": pix["emv"] if pix else None,
                "txid": pix["txid"] if pix else None
            } if pix else None,
            "descricao": dados.descricao,
            "instrucoes": instrucoes or []
        }
