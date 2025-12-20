"""
Conecta Plus - Motor de Conciliação Bancária
Processa arquivos OFX, CNAB e faz match automático com boletos
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
import asyncio


class TipoArquivo(Enum):
    OFX = "ofx"
    CNAB240 = "cnab240"
    CNAB400 = "cnab400"
    CSV = "csv"


@dataclass
class TransacaoExtrato:
    """Representa uma transação do extrato bancário"""
    data: date
    tipo: str  # 'C' credito, 'D' debito
    valor: float
    descricao: str
    numero_documento: Optional[str] = None
    codigo_transacao: Optional[str] = None
    dados_originais: Optional[Dict] = None


@dataclass
class ResultadoMatch:
    """Resultado de uma tentativa de match"""
    encontrado: bool
    tipo: str  # 'boleto', 'lancamento', 'nenhum'
    id: Optional[str] = None
    confianca: float = 0.0
    motivo: str = ""
    sugestoes: List[Dict] = None


class ParserOFX:
    """Parser para arquivos OFX (Open Financial Exchange)"""

    @staticmethod
    def parse(conteudo: str) -> Tuple[Dict, List[TransacaoExtrato]]:
        """
        Parse de arquivo OFX

        Args:
            conteudo: Conteúdo do arquivo OFX

        Returns:
            Tuple com (metadados, lista de transações)
        """
        transacoes = []
        metadata = {}

        # Remove headers SGML se existirem
        if "OFXHEADER" in conteudo:
            idx = conteudo.find("<OFX>")
            if idx > 0:
                conteudo = conteudo[idx:]

        # Converte para XML válido (OFX usa tags sem fechamento)
        conteudo = ParserOFX._converter_para_xml(conteudo)

        try:
            root = ET.fromstring(conteudo)

            # Extrai informações da conta
            acct_info = root.find(".//BANKACCTFROM") or root.find(".//CCACCTFROM")
            if acct_info is not None:
                metadata["banco_id"] = ParserOFX._get_text(acct_info, "BANKID")
                metadata["agencia"] = ParserOFX._get_text(acct_info, "BRANCHID")
                metadata["conta"] = ParserOFX._get_text(acct_info, "ACCTID")
                metadata["tipo_conta"] = ParserOFX._get_text(acct_info, "ACCTTYPE")

            # Extrai período
            stmt = root.find(".//STMTRS") or root.find(".//CCSTMTRS")
            if stmt is not None:
                banktranlist = stmt.find("BANKTRANLIST")
                if banktranlist is not None:
                    metadata["data_inicio"] = ParserOFX._parse_data(
                        ParserOFX._get_text(banktranlist, "DTSTART")
                    )
                    metadata["data_fim"] = ParserOFX._parse_data(
                        ParserOFX._get_text(banktranlist, "DTEND")
                    )

                # Extrai saldos
                ledger_bal = stmt.find("LEDGERBAL")
                if ledger_bal is not None:
                    metadata["saldo_final"] = float(
                        ParserOFX._get_text(ledger_bal, "BALAMT") or 0
                    )

                avail_bal = stmt.find("AVAILBAL")
                if avail_bal is not None:
                    metadata["saldo_disponivel"] = float(
                        ParserOFX._get_text(avail_bal, "BALAMT") or 0
                    )

            # Extrai transações
            for stmttrn in root.findall(".//STMTTRN"):
                try:
                    tipo_transacao = ParserOFX._get_text(stmttrn, "TRNTYPE")
                    valor = float(ParserOFX._get_text(stmttrn, "TRNAMT") or 0)
                    data_str = ParserOFX._get_text(stmttrn, "DTPOSTED")

                    transacao = TransacaoExtrato(
                        data=ParserOFX._parse_data(data_str),
                        tipo="C" if valor > 0 else "D",
                        valor=abs(valor),
                        descricao=ParserOFX._get_text(stmttrn, "MEMO") or "",
                        numero_documento=ParserOFX._get_text(stmttrn, "FITID"),
                        codigo_transacao=tipo_transacao,
                        dados_originais={
                            "trntype": tipo_transacao,
                            "checknum": ParserOFX._get_text(stmttrn, "CHECKNUM"),
                            "refnum": ParserOFX._get_text(stmttrn, "REFNUM"),
                            "name": ParserOFX._get_text(stmttrn, "NAME"),
                        }
                    )
                    transacoes.append(transacao)
                except Exception:
                    continue

        except ET.ParseError:
            pass

        return metadata, transacoes

    @staticmethod
    def _converter_para_xml(conteudo: str) -> str:
        """Converte OFX SGML para XML válido"""
        # Remove tags de abertura sem fechamento
        # OFX usa <TAG>valor em vez de <TAG>valor</TAG>

        # Lista de tags que precisam de fechamento
        tags_simples = [
            'DTSERVER', 'LANGUAGE', 'DTSTART', 'DTEND', 'TRNTYPE',
            'DTPOSTED', 'TRNAMT', 'FITID', 'CHECKNUM', 'REFNUM',
            'NAME', 'MEMO', 'BANKID', 'BRANCHID', 'ACCTID', 'ACCTTYPE',
            'BALAMT', 'DTASOF', 'CURDEF', 'CODE', 'SEVERITY', 'MESSAGE'
        ]

        for tag in tags_simples:
            # Encontra <TAG>valor e substitui por <TAG>valor</TAG>
            pattern = rf'<{tag}>([^<\n]+)'
            conteudo = re.sub(pattern, rf'<{tag}>\1</{tag}>', conteudo)

        return conteudo

    @staticmethod
    def _get_text(element: ET.Element, tag: str) -> Optional[str]:
        """Extrai texto de um elemento"""
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else None

    @staticmethod
    def _parse_data(data_str: Optional[str]) -> date:
        """Parse de data no formato OFX (YYYYMMDDHHMMSS)"""
        if not data_str:
            return date.today()

        # Remove fuso horário se existir
        data_str = data_str.split("[")[0]

        try:
            if len(data_str) >= 8:
                return datetime.strptime(data_str[:8], "%Y%m%d").date()
        except ValueError:
            pass

        return date.today()


class ParserCNAB:
    """Parser para arquivos CNAB 240 e 400"""

    @staticmethod
    def parse_cnab240(conteudo: str) -> Tuple[Dict, List[TransacaoExtrato]]:
        """
        Parse de arquivo CNAB 240

        O CNAB 240 tem registros de 240 caracteres organizados em:
        - Header de arquivo (tipo 0)
        - Header de lote (tipo 1)
        - Detalhe (tipo 3)
        - Trailer de lote (tipo 5)
        - Trailer de arquivo (tipo 9)
        """
        transacoes = []
        metadata = {"formato": "CNAB240"}
        linhas = conteudo.strip().split("\n")

        for linha in linhas:
            linha = linha.ljust(240)  # Garante 240 caracteres

            tipo_registro = linha[7:8]

            # Header de arquivo
            if tipo_registro == "0":
                metadata["banco_codigo"] = linha[0:3].strip()
                metadata["empresa_nome"] = linha[72:102].strip()
                metadata["data_arquivo"] = ParserCNAB._parse_data_cnab(linha[143:151])

            # Detalhe
            elif tipo_registro == "3":
                segmento = linha[13:14]

                # Segmento E - Extrato
                if segmento == "E":
                    try:
                        data_str = linha[144:152]
                        valor_str = linha[152:170].strip()
                        natureza = linha[170:171]  # C ou D

                        valor = float(valor_str) / 100 if valor_str else 0

                        transacao = TransacaoExtrato(
                            data=ParserCNAB._parse_data_cnab(data_str),
                            tipo=natureza if natureza in ["C", "D"] else "C",
                            valor=valor,
                            descricao=linha[180:220].strip(),
                            numero_documento=linha[62:77].strip(),
                            dados_originais={"linha": linha}
                        )
                        transacoes.append(transacao)
                    except Exception:
                        continue

        return metadata, transacoes

    @staticmethod
    def parse_cnab400(conteudo: str) -> Tuple[Dict, List[TransacaoExtrato]]:
        """
        Parse de arquivo CNAB 400

        O CNAB 400 tem registros de 400 caracteres:
        - Tipo 0: Header
        - Tipo 1: Detalhe (transação)
        - Tipo 9: Trailer
        """
        transacoes = []
        metadata = {"formato": "CNAB400"}
        linhas = conteudo.strip().split("\n")

        for linha in linhas:
            linha = linha.ljust(400)

            tipo_registro = linha[0:1]

            # Header
            if tipo_registro == "0":
                metadata["banco_codigo"] = linha[76:79].strip()
                metadata["empresa_nome"] = linha[46:76].strip()
                metadata["data_arquivo"] = ParserCNAB._parse_data_cnab(linha[94:100], formato="%d%m%y")

            # Detalhe
            elif tipo_registro == "1":
                try:
                    data_str = linha[110:116]
                    valor_str = linha[152:165].strip()

                    valor = float(valor_str) / 100 if valor_str else 0

                    # Determina tipo pela posição do arquivo ou valor
                    tipo = "C"  # Crédito por padrão em retorno

                    transacao = TransacaoExtrato(
                        data=ParserCNAB._parse_data_cnab(data_str, formato="%d%m%y"),
                        tipo=tipo,
                        valor=valor,
                        descricao=linha[318:358].strip(),
                        numero_documento=linha[62:73].strip(),  # Nosso número
                        dados_originais={"linha": linha}
                    )
                    transacoes.append(transacao)
                except Exception:
                    continue

        return metadata, transacoes

    @staticmethod
    def _parse_data_cnab(data_str: str, formato: str = "%d%m%Y") -> date:
        """Parse de data CNAB"""
        try:
            data_str = data_str.strip()
            if len(data_str) == 6 and formato == "%d%m%y":
                return datetime.strptime(data_str, "%d%m%y").date()
            elif len(data_str) == 8:
                return datetime.strptime(data_str, "%d%m%Y").date()
        except ValueError:
            pass
        return date.today()


class MotorConciliacao:
    """
    Motor de conciliação bancária inteligente

    Faz match automático entre transações do extrato e:
    - Boletos
    - Lançamentos financeiros
    - Pagamentos registrados
    """

    def __init__(self, boleto_repository, pagamento_repository):
        """
        Args:
            boleto_repository: Repositório de boletos
            pagamento_repository: Repositório de pagamentos
        """
        self.boleto_repo = boleto_repository
        self.pagamento_repo = pagamento_repository

    async def processar_arquivo(
        self,
        conteudo: str,
        tipo_arquivo: TipoArquivo,
        condominio_id: str,
        conta_bancaria_id: str
    ) -> Dict[str, Any]:
        """
        Processa arquivo de extrato e tenta conciliar

        Returns:
            Resultado do processamento com estatísticas
        """
        # Parse do arquivo
        if tipo_arquivo == TipoArquivo.OFX:
            metadata, transacoes = ParserOFX.parse(conteudo)
        elif tipo_arquivo == TipoArquivo.CNAB240:
            metadata, transacoes = ParserCNAB.parse_cnab240(conteudo)
        elif tipo_arquivo == TipoArquivo.CNAB400:
            metadata, transacoes = ParserCNAB.parse_cnab400(conteudo)
        else:
            raise ValueError(f"Tipo de arquivo não suportado: {tipo_arquivo}")

        # Estatísticas
        total = len(transacoes)
        conciliadas_auto = 0
        pendentes = 0
        resultados = []

        # Processa cada transação
        for transacao in transacoes:
            resultado = await self._tentar_conciliar(
                transacao, condominio_id
            )

            resultados.append({
                "transacao": {
                    "data": transacao.data.isoformat(),
                    "tipo": transacao.tipo,
                    "valor": transacao.valor,
                    "descricao": transacao.descricao,
                    "documento": transacao.numero_documento,
                },
                "match": {
                    "encontrado": resultado.encontrado,
                    "tipo": resultado.tipo,
                    "id": resultado.id,
                    "confianca": resultado.confianca,
                    "motivo": resultado.motivo,
                },
                "sugestoes": resultado.sugestoes or []
            })

            if resultado.encontrado and resultado.confianca >= 95:
                conciliadas_auto += 1
            else:
                pendentes += 1

        return {
            "metadata": metadata,
            "estatisticas": {
                "total_transacoes": total,
                "conciliadas_auto": conciliadas_auto,
                "pendentes": pendentes,
                "taxa_conciliacao": round(conciliadas_auto / total * 100, 1) if total > 0 else 0
            },
            "transacoes": resultados
        }

    async def _tentar_conciliar(
        self,
        transacao: TransacaoExtrato,
        condominio_id: str
    ) -> ResultadoMatch:
        """Tenta encontrar match para uma transação"""

        # Apenas processa créditos (pagamentos recebidos)
        if transacao.tipo != "C":
            return ResultadoMatch(
                encontrado=False,
                tipo="nenhum",
                motivo="Transação de débito (despesa)"
            )

        # 1. Tenta match exato por nosso número
        resultado = await self._match_por_nosso_numero(
            transacao, condominio_id
        )
        if resultado.encontrado:
            return resultado

        # 2. Tenta match por valor exato + descrição
        resultado = await self._match_por_valor_descricao(
            transacao, condominio_id
        )
        if resultado.encontrado:
            return resultado

        # 3. Tenta match por valor aproximado (com juros/multa)
        resultado = await self._match_por_valor_aproximado(
            transacao, condominio_id
        )
        if resultado.encontrado:
            return resultado

        # 4. Busca sugestões
        sugestoes = await self._buscar_sugestoes(
            transacao, condominio_id
        )

        return ResultadoMatch(
            encontrado=False,
            tipo="nenhum",
            motivo="Nenhum match encontrado",
            sugestoes=sugestoes
        )

    async def _match_por_nosso_numero(
        self,
        transacao: TransacaoExtrato,
        condominio_id: str
    ) -> ResultadoMatch:
        """Match por nosso número (identificador do boleto)"""

        if not transacao.numero_documento:
            return ResultadoMatch(encontrado=False, tipo="nenhum")

        # Busca boleto pelo nosso número
        # Simplificado - na implementação real usaria o repositório
        query = """
            SELECT id, valor, nosso_numero, status
            FROM conecta.boletos
            WHERE condominio_id = $1
            AND nosso_numero = $2
            AND status IN ('pendente', 'vencido')
        """
        # boleto = await self.boleto_repo.buscar_por_nosso_numero(...)

        # Mock para demonstração
        return ResultadoMatch(encontrado=False, tipo="nenhum")

    async def _match_por_valor_descricao(
        self,
        transacao: TransacaoExtrato,
        condominio_id: str
    ) -> ResultadoMatch:
        """Match por valor exato e similaridade de descrição"""

        # Busca boletos com mesmo valor e status pendente/vencido
        # boletos = await self.boleto_repo.buscar_por_valor(...)

        # Calcula similaridade da descrição
        # Extrai número de apartamento da descrição
        apt_pattern = r'(?:apt?\.?\s*|apartamento\s*)(\d+)'
        match = re.search(apt_pattern, transacao.descricao, re.IGNORECASE)

        if match:
            apt_numero = match.group(1)
            # Busca boleto do apartamento com mesmo valor
            # ...

        return ResultadoMatch(encontrado=False, tipo="nenhum")

    async def _match_por_valor_aproximado(
        self,
        transacao: TransacaoExtrato,
        condominio_id: str
    ) -> ResultadoMatch:
        """Match por valor aproximado (considera juros/multa)"""

        # Define tolerância de 5% para variação de valor
        valor_min = transacao.valor * 0.95
        valor_max = transacao.valor * 1.10  # Até 10% a mais (juros+multa)

        # Busca boletos no range de valor
        # boletos = await self.boleto_repo.buscar_por_range_valor(...)

        return ResultadoMatch(encontrado=False, tipo="nenhum")

    async def _buscar_sugestoes(
        self,
        transacao: TransacaoExtrato,
        condominio_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """Busca sugestões de possíveis matches"""

        sugestoes = []

        # Busca boletos pendentes/vencidos com valor similar
        # boletos = await self.boleto_repo.buscar_pendentes(...)

        # Ordena por similaridade de valor e data
        # ...

        return sugestoes

    @staticmethod
    def calcular_similaridade(texto1: str, texto2: str) -> float:
        """Calcula similaridade entre dois textos (0-100)"""
        if not texto1 or not texto2:
            return 0.0

        texto1 = texto1.lower().strip()
        texto2 = texto2.lower().strip()

        ratio = SequenceMatcher(None, texto1, texto2).ratio()
        return round(ratio * 100, 2)


class ProcessadorRetornoCNAB:
    """
    Processador de arquivos de retorno CNAB

    Processa arquivos de retorno bancário para:
    - Atualizar status de boletos
    - Registrar pagamentos recebidos
    - Identificar rejeições
    """

    # Códigos de ocorrência comuns CNAB 240
    OCORRENCIAS_CNAB240 = {
        "02": "Entrada confirmada",
        "03": "Entrada rejeitada",
        "06": "Liquidação normal",
        "09": "Baixa",
        "17": "Liquidação após baixa",
        "19": "Confirmação de recebimento de instrução de protesto",
    }

    # Códigos de ocorrência comuns CNAB 400
    OCORRENCIAS_CNAB400 = {
        "02": "Confirmação de entrada",
        "03": "Comando recusado",
        "06": "Liquidação normal",
        "09": "Baixado automaticamente",
        "10": "Baixado conforme instruções",
        "15": "Liquidação em cartório",
    }

    @staticmethod
    def processar_retorno_240(conteudo: str) -> List[Dict]:
        """
        Processa arquivo de retorno CNAB 240

        Returns:
            Lista de ocorrências processadas
        """
        ocorrencias = []
        linhas = conteudo.strip().split("\n")

        for linha in linhas:
            linha = linha.ljust(240)

            tipo_registro = linha[7:8]

            # Detalhe - Segmento T (Título)
            if tipo_registro == "3" and linha[13:14] == "T":
                codigo_ocorrencia = linha[15:17]
                nosso_numero = linha[37:57].strip()
                valor = float(linha[81:96].strip() or 0) / 100
                data_vencimento = linha[73:81]

                ocorrencia = {
                    "nosso_numero": nosso_numero,
                    "codigo_ocorrencia": codigo_ocorrencia,
                    "descricao_ocorrencia": ProcessadorRetornoCNAB.OCORRENCIAS_CNAB240.get(
                        codigo_ocorrencia, "Desconhecido"
                    ),
                    "valor": valor,
                    "data_vencimento": data_vencimento,
                    "linha_original": linha
                }
                ocorrencias.append(ocorrencia)

        return ocorrencias

    @staticmethod
    def processar_retorno_400(conteudo: str) -> List[Dict]:
        """
        Processa arquivo de retorno CNAB 400

        Returns:
            Lista de ocorrências processadas
        """
        ocorrencias = []
        linhas = conteudo.strip().split("\n")

        for linha in linhas:
            linha = linha.ljust(400)

            tipo_registro = linha[0:1]

            # Detalhe
            if tipo_registro == "1":
                codigo_ocorrencia = linha[108:110]
                nosso_numero = linha[62:73].strip()
                valor = float(linha[152:165].strip() or 0) / 100
                data_credito = linha[110:116]

                ocorrencia = {
                    "nosso_numero": nosso_numero,
                    "codigo_ocorrencia": codigo_ocorrencia,
                    "descricao_ocorrencia": ProcessadorRetornoCNAB.OCORRENCIAS_CNAB400.get(
                        codigo_ocorrencia, "Desconhecido"
                    ),
                    "valor": valor,
                    "data_credito": data_credito,
                    "linha_original": linha
                }
                ocorrencias.append(ocorrencia)

        return ocorrencias
