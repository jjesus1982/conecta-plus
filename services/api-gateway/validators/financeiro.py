"""
Conecta Plus - Validadores Financeiros
Validações de CPF, CNPJ, PIX, Código de Barras FEBRABAN
"""

import re
from typing import Optional, Tuple, Dict, Any, List
from datetime import date, datetime
from dataclasses import dataclass
from enum import Enum


# ==================== CONSTANTES ====================

# Códigos de bancos válidos FEBRABAN (principais)
BANCOS_VALIDOS = {
    "001": "Banco do Brasil",
    "033": "Santander",
    "041": "Banrisul",
    "077": "Banco Inter",
    "104": "Caixa Econômica Federal",
    "212": "Banco Original",
    "237": "Bradesco",
    "260": "Nubank",
    "290": "PagSeguro",
    "318": "BMG",
    "336": "C6 Bank",
    "341": "Itaú",
    "389": "Mercantil do Brasil",
    "422": "Safra",
    "633": "Rendimento",
    "655": "Neon",
    "707": "Daycoval",
    "741": "BRP",
    "745": "Citibank",
    "756": "Sicoob",
}

# Limites de valor
VALOR_MINIMO_BOLETO = 1.00  # R$ 1,00
VALOR_MAXIMO_BOLETO = 9999999.99  # R$ 9.999.999,99

# Data base FEBRABAN
DATA_BASE_FEBRABAN = date(1997, 10, 7)
DATA_LIMITE_CICLO1 = date(2025, 2, 21)


class TipoChavePix(str, Enum):
    CPF = "cpf"
    CNPJ = "cnpj"
    EMAIL = "email"
    TELEFONE = "telefone"
    EVP = "evp"  # Chave aleatória


@dataclass
class ResultadoValidacao:
    """Resultado de uma validação"""
    valido: bool
    mensagem: str
    dados: Optional[Dict[str, Any]] = None
    erros: Optional[List[str]] = None


# ==================== VALIDADORES DE DOCUMENTOS ====================

class ValidadorCPF:
    """Validador de CPF"""

    @staticmethod
    def validar(cpf: str) -> ResultadoValidacao:
        """
        Valida CPF

        Args:
            cpf: CPF com ou sem formatação

        Returns:
            ResultadoValidacao com status e mensagem
        """
        # Remove formatação
        cpf = re.sub(r'[^\d]', '', cpf)

        # Verifica tamanho
        if len(cpf) != 11:
            return ResultadoValidacao(
                valido=False,
                mensagem="CPF deve ter 11 dígitos",
                erros=["tamanho_invalido"]
            )

        # Verifica se todos os dígitos são iguais
        if cpf == cpf[0] * 11:
            return ResultadoValidacao(
                valido=False,
                mensagem="CPF inválido (dígitos repetidos)",
                erros=["digitos_repetidos"]
            )

        # Calcula primeiro dígito verificador
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        resto = soma % 11
        dv1 = 0 if resto < 2 else 11 - resto

        if int(cpf[9]) != dv1:
            return ResultadoValidacao(
                valido=False,
                mensagem="CPF inválido (dígito verificador 1)",
                erros=["dv1_invalido"]
            )

        # Calcula segundo dígito verificador
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        resto = soma % 11
        dv2 = 0 if resto < 2 else 11 - resto

        if int(cpf[10]) != dv2:
            return ResultadoValidacao(
                valido=False,
                mensagem="CPF inválido (dígito verificador 2)",
                erros=["dv2_invalido"]
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="CPF válido",
            dados={"cpf_formatado": f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"}
        )

    @staticmethod
    def formatar(cpf: str) -> str:
        """Formata CPF"""
        cpf = re.sub(r'[^\d]', '', cpf)
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


class ValidadorCNPJ:
    """Validador de CNPJ"""

    @staticmethod
    def validar(cnpj: str) -> ResultadoValidacao:
        """
        Valida CNPJ

        Args:
            cnpj: CNPJ com ou sem formatação

        Returns:
            ResultadoValidacao com status e mensagem
        """
        # Remove formatação
        cnpj = re.sub(r'[^\d]', '', cnpj)

        # Verifica tamanho
        if len(cnpj) != 14:
            return ResultadoValidacao(
                valido=False,
                mensagem="CNPJ deve ter 14 dígitos",
                erros=["tamanho_invalido"]
            )

        # Verifica se todos os dígitos são iguais
        if cnpj == cnpj[0] * 14:
            return ResultadoValidacao(
                valido=False,
                mensagem="CNPJ inválido (dígitos repetidos)",
                erros=["digitos_repetidos"]
            )

        # Pesos para cálculo
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

        # Calcula primeiro dígito verificador
        soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
        resto = soma % 11
        dv1 = 0 if resto < 2 else 11 - resto

        if int(cnpj[12]) != dv1:
            return ResultadoValidacao(
                valido=False,
                mensagem="CNPJ inválido (dígito verificador 1)",
                erros=["dv1_invalido"]
            )

        # Calcula segundo dígito verificador
        soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
        resto = soma % 11
        dv2 = 0 if resto < 2 else 11 - resto

        if int(cnpj[13]) != dv2:
            return ResultadoValidacao(
                valido=False,
                mensagem="CNPJ inválido (dígito verificador 2)",
                erros=["dv2_invalido"]
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="CNPJ válido",
            dados={"cnpj_formatado": f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"}
        )

    @staticmethod
    def formatar(cnpj: str) -> str:
        """Formata CNPJ"""
        cnpj = re.sub(r'[^\d]', '', cnpj)
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


class ValidadorDocumento:
    """Validador genérico de CPF/CNPJ"""

    @staticmethod
    def validar(documento: str) -> ResultadoValidacao:
        """Valida CPF ou CNPJ automaticamente"""
        doc_limpo = re.sub(r'[^\d]', '', documento)

        if len(doc_limpo) == 11:
            return ValidadorCPF.validar(documento)
        elif len(doc_limpo) == 14:
            return ValidadorCNPJ.validar(documento)
        else:
            return ResultadoValidacao(
                valido=False,
                mensagem="Documento deve ser CPF (11 dígitos) ou CNPJ (14 dígitos)",
                erros=["tamanho_invalido"]
            )

    @staticmethod
    def formatar(documento: str) -> str:
        """Formata CPF ou CNPJ"""
        doc_limpo = re.sub(r'[^\d]', '', documento)
        if len(doc_limpo) == 11:
            return ValidadorCPF.formatar(documento)
        elif len(doc_limpo) == 14:
            return ValidadorCNPJ.formatar(documento)
        return documento


# ==================== VALIDADOR DE PIX ====================

class ValidadorPIX:
    """Validador de Chave PIX"""

    @staticmethod
    def identificar_tipo(chave: str) -> TipoChavePix:
        """Identifica o tipo da chave PIX"""
        chave_limpa = chave.strip()

        # CPF: 11 dígitos
        if re.match(r'^\d{11}$', re.sub(r'[^\d]', '', chave_limpa)):
            return TipoChavePix.CPF

        # CNPJ: 14 dígitos
        if re.match(r'^\d{14}$', re.sub(r'[^\d]', '', chave_limpa)):
            return TipoChavePix.CNPJ

        # Email
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', chave_limpa):
            return TipoChavePix.EMAIL

        # Telefone: +55 + DDD + número
        if re.match(r'^\+55\d{10,11}$', re.sub(r'[^\d+]', '', chave_limpa)):
            return TipoChavePix.TELEFONE

        # EVP: 32 caracteres alfanuméricos com hífens
        if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', chave_limpa.lower()):
            return TipoChavePix.EVP

        # Fallback para EVP se tiver formato de UUID
        if len(chave_limpa) == 36 and chave_limpa.count('-') == 4:
            return TipoChavePix.EVP

        return TipoChavePix.EVP  # Default

    @staticmethod
    def validar(chave: str, tipo_esperado: Optional[TipoChavePix] = None) -> ResultadoValidacao:
        """
        Valida chave PIX

        Args:
            chave: Chave PIX
            tipo_esperado: Tipo esperado (opcional)

        Returns:
            ResultadoValidacao
        """
        if not chave or not chave.strip():
            return ResultadoValidacao(
                valido=False,
                mensagem="Chave PIX não pode ser vazia",
                erros=["chave_vazia"]
            )

        tipo = ValidadorPIX.identificar_tipo(chave)

        if tipo_esperado and tipo != tipo_esperado:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Tipo de chave inválido. Esperado: {tipo_esperado.value}, Encontrado: {tipo.value}",
                erros=["tipo_invalido"]
            )

        erros = []

        if tipo == TipoChavePix.CPF:
            resultado_cpf = ValidadorCPF.validar(chave)
            if not resultado_cpf.valido:
                return resultado_cpf

        elif tipo == TipoChavePix.CNPJ:
            resultado_cnpj = ValidadorCNPJ.validar(chave)
            if not resultado_cnpj.valido:
                return resultado_cnpj

        elif tipo == TipoChavePix.EMAIL:
            if len(chave) > 77:
                erros.append("email_muito_longo")

        elif tipo == TipoChavePix.TELEFONE:
            telefone_limpo = re.sub(r'[^\d]', '', chave)
            if len(telefone_limpo) < 12 or len(telefone_limpo) > 13:
                erros.append("telefone_invalido")

        elif tipo == TipoChavePix.EVP:
            if not re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', chave.lower()):
                erros.append("evp_formato_invalido")

        if erros:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Chave PIX inválida: {', '.join(erros)}",
                erros=erros
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="Chave PIX válida",
            dados={"tipo": tipo.value, "chave_normalizada": chave.strip()}
        )


# ==================== VALIDADOR DE CÓDIGO DE BARRAS ====================

class ValidadorCodigoBarras:
    """Validador de Código de Barras FEBRABAN"""

    @staticmethod
    def validar_banco(codigo_banco: str) -> ResultadoValidacao:
        """Valida código do banco"""
        if codigo_banco not in BANCOS_VALIDOS:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Código de banco '{codigo_banco}' não reconhecido pela FEBRABAN",
                erros=["banco_invalido"],
                dados={"bancos_validos": list(BANCOS_VALIDOS.keys())}
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="Banco válido",
            dados={"banco_nome": BANCOS_VALIDOS[codigo_banco]}
        )

    @staticmethod
    def validar_agencia(agencia: str, banco_codigo: str) -> ResultadoValidacao:
        """Valida agência bancária"""
        agencia_limpa = re.sub(r'[^\d]', '', agencia)

        if not agencia_limpa:
            return ResultadoValidacao(
                valido=False,
                mensagem="Agência não pode ser vazia",
                erros=["agencia_vazia"]
            )

        if len(agencia_limpa) > 6:
            return ResultadoValidacao(
                valido=False,
                mensagem="Agência deve ter no máximo 6 dígitos",
                erros=["agencia_muito_longa"]
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="Agência válida",
            dados={"agencia_formatada": agencia_limpa.zfill(4)}
        )

    @staticmethod
    def validar_conta(conta: str, banco_codigo: str) -> ResultadoValidacao:
        """Valida conta bancária"""
        conta_limpa = re.sub(r'[^\dxX]', '', conta)

        if not conta_limpa:
            return ResultadoValidacao(
                valido=False,
                mensagem="Conta não pode ser vazia",
                erros=["conta_vazia"]
            )

        if len(conta_limpa) > 12:
            return ResultadoValidacao(
                valido=False,
                mensagem="Conta deve ter no máximo 12 dígitos",
                erros=["conta_muito_longa"]
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="Conta válida",
            dados={"conta_formatada": conta_limpa}
        )

    @staticmethod
    def validar_codigo_barras(codigo: str) -> ResultadoValidacao:
        """
        Valida código de barras completo (44 posições)
        """
        codigo_limpo = re.sub(r'[^\d]', '', codigo)

        if len(codigo_limpo) != 44:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Código de barras deve ter 44 dígitos (encontrado: {len(codigo_limpo)})",
                erros=["tamanho_invalido"]
            )

        # Extrai partes
        banco = codigo_limpo[0:3]
        moeda = codigo_limpo[3]
        dv = codigo_limpo[4]
        fator = codigo_limpo[5:9]
        valor = codigo_limpo[9:19]
        campo_livre = codigo_limpo[19:44]

        erros = []

        # Valida banco
        if banco not in BANCOS_VALIDOS:
            erros.append(f"banco_invalido:{banco}")

        # Valida moeda (deve ser 9 = Real)
        if moeda != '9':
            erros.append(f"moeda_invalida:{moeda}")

        # Valida DV
        codigo_sem_dv = codigo_limpo[:4] + codigo_limpo[5:]
        dv_calculado = ValidadorCodigoBarras._calcular_dv_mod11(codigo_sem_dv)
        if str(dv_calculado) != dv:
            erros.append(f"dv_invalido:esperado_{dv_calculado}_encontrado_{dv}")

        # Valida fator de vencimento
        try:
            fator_int = int(fator)
            if fator_int < 1000 or fator_int > 9999:
                erros.append(f"fator_vencimento_invalido:{fator}")
        except ValueError:
            erros.append("fator_nao_numerico")

        if erros:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Código de barras inválido: {', '.join(erros)}",
                erros=erros
            )

        # Calcula vencimento
        vencimento = ValidadorCodigoBarras._fator_para_data(int(fator))
        valor_decimal = int(valor) / 100

        return ResultadoValidacao(
            valido=True,
            mensagem="Código de barras válido",
            dados={
                "banco": banco,
                "banco_nome": BANCOS_VALIDOS.get(banco, "Desconhecido"),
                "vencimento": vencimento.isoformat() if vencimento else None,
                "valor": valor_decimal,
                "campo_livre": campo_livre
            }
        )

    @staticmethod
    def validar_linha_digitavel(linha: str) -> ResultadoValidacao:
        """Valida linha digitável (47 dígitos formatados)"""
        linha_limpa = re.sub(r'[^\d]', '', linha)

        if len(linha_limpa) != 47:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Linha digitável deve ter 47 dígitos (encontrado: {len(linha_limpa)})",
                erros=["tamanho_invalido"]
            )

        # Extrai campos
        campo1 = linha_limpa[0:9]
        dv1 = linha_limpa[9]
        campo2 = linha_limpa[10:20]
        dv2 = linha_limpa[20]
        campo3 = linha_limpa[21:31]
        dv3 = linha_limpa[31]
        dv_geral = linha_limpa[32]
        campo5 = linha_limpa[33:47]

        erros = []

        # Valida DVs dos campos (módulo 10)
        if str(ValidadorCodigoBarras._calcular_dv_mod10(campo1)) != dv1:
            erros.append("dv_campo1_invalido")

        if str(ValidadorCodigoBarras._calcular_dv_mod10(campo2)) != dv2:
            erros.append("dv_campo2_invalido")

        if str(ValidadorCodigoBarras._calcular_dv_mod10(campo3)) != dv3:
            erros.append("dv_campo3_invalido")

        if erros:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Linha digitável inválida: {', '.join(erros)}",
                erros=erros
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="Linha digitável válida"
        )

    @staticmethod
    def _calcular_dv_mod11(codigo: str) -> int:
        """Calcula DV usando módulo 11"""
        pesos = [2, 3, 4, 5, 6, 7, 8, 9]
        soma = 0
        peso_idx = 0

        for digito in reversed(codigo):
            if digito.isdigit():
                soma += int(digito) * pesos[peso_idx % 8]
                peso_idx += 1

        resto = soma % 11
        dv = 11 - resto

        if dv == 0 or dv == 10 or dv == 11:
            return 1
        return dv

    @staticmethod
    def _calcular_dv_mod10(bloco: str) -> int:
        """Calcula DV usando módulo 10"""
        soma = 0
        multiplicador = 2

        for digito in reversed(bloco):
            if digito.isdigit():
                resultado = int(digito) * multiplicador
                if resultado > 9:
                    resultado = (resultado // 10) + (resultado % 10)
                soma += resultado
                multiplicador = 3 - multiplicador

        resto = soma % 10
        return 0 if resto == 0 else 10 - resto

    @staticmethod
    def _fator_para_data(fator: int) -> Optional[date]:
        """Converte fator de vencimento para data"""
        try:
            if fator >= 1000:
                if fator <= 9999:
                    # Ciclo 1 (até 21/02/2025)
                    return DATA_BASE_FEBRABAN + __import__('datetime').timedelta(days=fator)
            return None
        except Exception:
            return None


# ==================== VALIDADOR DE BOLETO ====================

class ValidadorBoleto:
    """Validador completo de dados de boleto"""

    @staticmethod
    def validar_valor(valor: float) -> ResultadoValidacao:
        """Valida valor do boleto"""
        if valor is None:
            return ResultadoValidacao(
                valido=False,
                mensagem="Valor não pode ser nulo",
                erros=["valor_nulo"]
            )

        if valor < VALOR_MINIMO_BOLETO:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Valor mínimo é R$ {VALOR_MINIMO_BOLETO:.2f}",
                erros=["valor_muito_baixo"]
            )

        if valor > VALOR_MAXIMO_BOLETO:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Valor máximo é R$ {VALOR_MAXIMO_BOLETO:.2f}",
                erros=["valor_muito_alto"]
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="Valor válido",
            dados={"valor_centavos": int(valor * 100)}
        )

    @staticmethod
    def validar_vencimento(vencimento: date) -> ResultadoValidacao:
        """Valida data de vencimento"""
        if not vencimento:
            return ResultadoValidacao(
                valido=False,
                mensagem="Data de vencimento não pode ser nula",
                erros=["vencimento_nulo"]
            )

        hoje = date.today()

        # Não pode ser mais de 5 anos no passado
        limite_passado = date(hoje.year - 5, hoje.month, hoje.day)
        if vencimento < limite_passado:
            return ResultadoValidacao(
                valido=False,
                mensagem="Data de vencimento muito antiga (máximo 5 anos)",
                erros=["vencimento_muito_antigo"]
            )

        # Não pode ser mais de 2 anos no futuro
        limite_futuro = date(hoje.year + 2, hoje.month, hoje.day)
        if vencimento > limite_futuro:
            return ResultadoValidacao(
                valido=False,
                mensagem="Data de vencimento muito distante (máximo 2 anos)",
                erros=["vencimento_muito_futuro"]
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="Vencimento válido",
            dados={"vencimento_iso": vencimento.isoformat()}
        )

    @staticmethod
    def validar_competencia(competencia: str) -> ResultadoValidacao:
        """Valida competência (MM/YYYY)"""
        if not competencia:
            return ResultadoValidacao(
                valido=False,
                mensagem="Competência não pode ser vazia",
                erros=["competencia_vazia"]
            )

        # Aceita MM/YYYY ou MM-YYYY
        match = re.match(r'^(\d{2})[/-](\d{4})$', competencia)
        if not match:
            return ResultadoValidacao(
                valido=False,
                mensagem="Competência deve estar no formato MM/YYYY",
                erros=["formato_invalido"]
            )

        mes = int(match.group(1))
        ano = int(match.group(2))

        if mes < 1 or mes > 12:
            return ResultadoValidacao(
                valido=False,
                mensagem="Mês deve estar entre 01 e 12",
                erros=["mes_invalido"]
            )

        ano_atual = date.today().year
        if ano < ano_atual - 10 or ano > ano_atual + 2:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Ano deve estar entre {ano_atual - 10} e {ano_atual + 2}",
                erros=["ano_invalido"]
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="Competência válida",
            dados={"mes": mes, "ano": ano, "competencia_normalizada": f"{mes:02d}/{ano}"}
        )

    @staticmethod
    def validar_boleto_completo(
        valor: float,
        vencimento: date,
        competencia: str,
        pagador_documento: str,
        banco_codigo: str,
        agencia: str,
        conta: str
    ) -> ResultadoValidacao:
        """Valida todos os campos de um boleto"""
        erros = []
        dados = {}

        # Valor
        resultado_valor = ValidadorBoleto.validar_valor(valor)
        if not resultado_valor.valido:
            erros.extend(resultado_valor.erros or [])
        else:
            dados.update(resultado_valor.dados or {})

        # Vencimento
        resultado_venc = ValidadorBoleto.validar_vencimento(vencimento)
        if not resultado_venc.valido:
            erros.extend(resultado_venc.erros or [])
        else:
            dados.update(resultado_venc.dados or {})

        # Competência
        resultado_comp = ValidadorBoleto.validar_competencia(competencia)
        if not resultado_comp.valido:
            erros.extend(resultado_comp.erros or [])
        else:
            dados.update(resultado_comp.dados or {})

        # Documento
        resultado_doc = ValidadorDocumento.validar(pagador_documento)
        if not resultado_doc.valido:
            erros.extend([f"documento_{e}" for e in (resultado_doc.erros or [])])

        # Banco
        resultado_banco = ValidadorCodigoBarras.validar_banco(banco_codigo)
        if not resultado_banco.valido:
            erros.extend(resultado_banco.erros or [])
        else:
            dados.update(resultado_banco.dados or {})

        # Agência
        resultado_agencia = ValidadorCodigoBarras.validar_agencia(agencia, banco_codigo)
        if not resultado_agencia.valido:
            erros.extend(resultado_agencia.erros or [])

        # Conta
        resultado_conta = ValidadorCodigoBarras.validar_conta(conta, banco_codigo)
        if not resultado_conta.valido:
            erros.extend(resultado_conta.erros or [])

        if erros:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Boleto inválido: {len(erros)} erro(s) encontrado(s)",
                erros=erros
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="Boleto válido",
            dados=dados
        )


# ==================== VALIDADOR DE ACORDO ====================

class ValidadorAcordo:
    """Validador de Acordo de Pagamento"""

    # Limites legais
    MAX_PARCELAS = 24
    MIN_PARCELAS = 1
    JUROS_MAXIMO_MENSAL = 1.0  # 1% ao mês (limite legal para condomínio)
    VALOR_MINIMO_PARCELA = 50.00  # R$ 50,00

    @staticmethod
    def validar(
        valor_total: float,
        numero_parcelas: int,
        valor_entrada: float = 0,
        taxa_juros_mensal: float = 0
    ) -> ResultadoValidacao:
        """Valida parâmetros de acordo"""
        erros = []

        if numero_parcelas < ValidadorAcordo.MIN_PARCELAS:
            erros.append(f"minimo_{ValidadorAcordo.MIN_PARCELAS}_parcelas")

        if numero_parcelas > ValidadorAcordo.MAX_PARCELAS:
            erros.append(f"maximo_{ValidadorAcordo.MAX_PARCELAS}_parcelas")

        if taxa_juros_mensal > ValidadorAcordo.JUROS_MAXIMO_MENSAL:
            erros.append(f"juros_maximo_{ValidadorAcordo.JUROS_MAXIMO_MENSAL}%_ao_mes")

        valor_parcela = (valor_total - valor_entrada) / numero_parcelas if numero_parcelas > 0 else 0

        if valor_parcela < ValidadorAcordo.VALOR_MINIMO_PARCELA:
            erros.append(f"parcela_minima_R${ValidadorAcordo.VALOR_MINIMO_PARCELA}")

        if valor_entrada < 0:
            erros.append("entrada_negativa")

        if valor_entrada > valor_total:
            erros.append("entrada_maior_que_total")

        if erros:
            return ResultadoValidacao(
                valido=False,
                mensagem=f"Acordo inválido: {', '.join(erros)}",
                erros=erros
            )

        return ResultadoValidacao(
            valido=True,
            mensagem="Acordo válido",
            dados={
                "valor_parcela": round(valor_parcela, 2),
                "valor_total_com_juros": round(valor_total * (1 + taxa_juros_mensal/100 * numero_parcelas), 2)
            }
        )
