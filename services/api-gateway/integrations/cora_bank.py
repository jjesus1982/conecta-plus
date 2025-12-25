"""
Conecta Plus - Integração com Cora Bank
API de cobranças e pagamentos do Banco Cora

Documentação oficial: https://developers.cora.com.br/
"""

import aiohttp
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, date, timedelta
from dataclasses import dataclass
import json
import hashlib
import hmac
import base64
import os


@dataclass
class CoraConfig:
    """Configuração da API Cora"""
    client_id: str
    client_secret: str
    ambiente: str = "sandbox"  # sandbox ou production
    api_version: str = "v2"  # v1 ou v2

    @property
    def base_url(self) -> str:
        base = "https://api.cora.com.br" if self.ambiente == "production" else "https://api.stage.cora.com.br"
        return f"{base}/{self.api_version}"

    @property
    def auth_url(self) -> str:
        if self.ambiente == "production":
            return "https://auth.cora.com.br"
        return "https://auth.stage.cora.com.br"


class CoraAuthError(Exception):
    """Erro de autenticação com a Cora"""
    pass


class CoraAPIError(Exception):
    """Erro genérico da API Cora"""
    def __init__(self, message: str, status_code: int = 0, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


class CoraBankClient:
    """
    Cliente para integração com Cora Bank

    Funcionalidades:
    - Autenticação OAuth2
    - Emissão de boletos
    - Cobrança PIX
    - Consulta de pagamentos
    - Webhooks
    """

    def __init__(self, config: CoraConfig):
        self.config = config
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Retorna sessão HTTP"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Fecha a sessão HTTP"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _authenticate(self) -> str:
        """Autentica na API e retorna access_token"""
        # Verifica se token ainda é válido
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token

        session = await self._get_session()

        auth_data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        try:
            async with session.post(
                f"{self.config.auth_url}/token",
                data=auth_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise CoraAuthError(f"Falha na autenticação: {response.status} - {text}")

                data = await response.json()
                self._access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)

                return self._access_token

        except aiohttp.ClientError as e:
            raise CoraAuthError(f"Erro de conexão: {str(e)}")

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Faz requisição autenticada para a API"""
        token = await self._authenticate()
        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.config.base_url}{endpoint}"

        try:
            async with session.request(
                method,
                url,
                json=data,
                params=params,
                headers=headers
            ) as response:
                response_data = await response.json() if response.content_length else {}

                if response.status >= 400:
                    raise CoraAPIError(
                        f"Erro na API: {response.status}",
                        status_code=response.status,
                        response=response_data
                    )

                return response_data

        except aiohttp.ClientError as e:
            raise CoraAPIError(f"Erro de conexão: {str(e)}")

    def _format_payer(self, pagador: Dict[str, Any]) -> Dict:
        """Formata dados do pagador para payload da API"""
        payer = {
            "name": pagador["nome"],
            "document": {
                "identity": pagador["documento"].replace(".", "").replace("-", "").replace("/", ""),
                "type": "CPF" if len(pagador["documento"].replace(".", "").replace("-", "")) == 11 else "CNPJ"
            }
        }

        if pagador.get("email"):
            payer["email"] = pagador["email"]

        if pagador.get("endereco"):
            end = pagador["endereco"]
            payer["address"] = {
                "street": end.get("logradouro", ""),
                "number": end.get("numero", "S/N"),
                "complement": end.get("complemento"),
                "district": end.get("bairro", ""),
                "city": end.get("cidade", ""),
                "state": end.get("uf", ""),
                "zip_code": end.get("cep", "").replace("-", "")
            }

        return payer

    # ==================== BOLETOS ====================

    async def criar_boleto(
        self,
        valor: float,
        vencimento: str,
        pagador: Dict[str, Any],
        descricao: str = "Cobrança",
        instrucoes: Optional[List[str]] = None,
        multa_percentual: float = 2.0,
        juros_mensal: float = 1.0,
        desconto: Optional[Dict] = None,
        numero_documento: Optional[str] = None,
    ) -> Dict:
        """
        Cria um novo boleto

        Args:
            valor: Valor do boleto em reais
            vencimento: Data de vencimento (YYYY-MM-DD)
            pagador: Dados do pagador {
                "nome": str,
                "documento": str (CPF/CNPJ),
                "email": str (opcional),
                "telefone": str (opcional),
                "endereco": {
                    "logradouro": str,
                    "numero": str,
                    "complemento": str (opcional),
                    "bairro": str,
                    "cidade": str,
                    "uf": str,
                    "cep": str
                }
            }
            descricao: Descrição da cobrança
            instrucoes: Lista de instruções no boleto
            multa_percentual: Percentual de multa após vencimento
            juros_mensal: Percentual de juros ao mês
            desconto: Desconto {
                "tipo": "PERCENTUAL" ou "VALOR_FIXO",
                "valor": float,
                "data_limite": "YYYY-MM-DD"
            }
            numero_documento: Número do documento/referência

        Returns:
            Dados do boleto criado incluindo código de barras e linha digitável
        """
        # Monta payload
        payload = {
            "amount": int(valor * 100),  # Valor em centavos
            "due_date": vencimento,
            "payer": self._format_payer(pagador),
            "payment_terms": {
                "fine": {
                    "type": "PERCENTAGE",
                    "value": int(multa_percentual * 100)  # Em centavos de percentual
                },
                "interest": {
                    "type": "MONTHLY_PERCENTAGE",
                    "value": int(juros_mensal * 100)
                }
            }
        }

        if descricao:
            payload["description"] = descricao

        if instrucoes:
            payload["instructions"] = instrucoes[:5]  # Máximo 5 instruções

        if desconto:
            payload["payment_terms"]["discount"] = {
                "type": desconto["tipo"],
                "value": int(desconto["valor"] * 100),
                "limit_date": desconto["data_limite"]
            }

        if numero_documento:
            payload["document_number"] = numero_documento

        response = await self._request("POST", "/invoices", data=payload)

        # Formata resposta
        return {
            "id": response.get("id"),
            "status": response.get("status"),
            "valor": valor,
            "vencimento": vencimento,
            "codigo_barras": response.get("payment", {}).get("bar_code"),
            "linha_digitavel": response.get("payment", {}).get("digitable_line"),
            "nosso_numero": response.get("our_number"),
            "url_pdf": response.get("pdf_url"),
            "pix": {
                "qrcode": response.get("pix", {}).get("qr_code"),
                "copia_cola": response.get("pix", {}).get("emv"),
                "txid": response.get("pix", {}).get("txid")
            },
            "response_original": response
        }

    async def consultar_boleto(self, boleto_id: str) -> Dict:
        """Consulta status de um boleto"""
        response = await self._request("GET", f"/invoices/{boleto_id}")

        status_map = {
            "OPEN": "pendente",
            "PAID": "pago",
            "OVERDUE": "vencido",
            "CANCELLED": "cancelado",
            "EXPIRED": "expirado",
        }

        return {
            "id": response.get("id"),
            "status": status_map.get(response.get("status"), response.get("status")),
            "valor": response.get("amount", 0) / 100,
            "valor_pago": response.get("paid_amount", 0) / 100 if response.get("paid_amount") else None,
            "data_pagamento": response.get("paid_at"),
            "vencimento": response.get("due_date"),
            "nosso_numero": response.get("our_number"),
            "response_original": response
        }

    async def listar_boletos(
        self,
        status: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict:
        """Lista boletos com filtros"""
        params = {
            "page": page,
            "per_page": limit
        }

        if status:
            status_map = {
                "pendente": "OPEN",
                "pago": "PAID",
                "vencido": "OVERDUE",
                "cancelado": "CANCELLED",
            }
            params["status"] = status_map.get(status, status)

        if data_inicio:
            params["start_date"] = data_inicio

        if data_fim:
            params["end_date"] = data_fim

        response = await self._request("GET", "/invoices", params=params)

        items = []
        for item in response.get("items", []):
            items.append({
                "id": item.get("id"),
                "status": item.get("status"),
                "valor": item.get("amount", 0) / 100,
                "vencimento": item.get("due_date"),
                "nosso_numero": item.get("our_number"),
            })

        return {
            "items": items,
            "total": response.get("total", 0),
            "page": page,
            "limit": limit
        }

    async def cancelar_boleto(self, boleto_id: str) -> bool:
        """Cancela um boleto"""
        try:
            await self._request("POST", f"/invoices/{boleto_id}/cancel")
            return True
        except CoraAPIError:
            return False

    # ==================== PIX ====================

    async def criar_cobranca_pix(
        self,
        valor: float,
        chave_pix: str,
        descricao: str = "Cobrança PIX",
        expiracao_segundos: int = 3600,
        pagador: Optional[Dict] = None,
        info_adicionais: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Cria uma cobrança PIX (QR Code dinâmico)

        Args:
            valor: Valor em reais
            chave_pix: Chave PIX do recebedor
            descricao: Descrição da cobrança
            expiracao_segundos: Tempo de expiração em segundos
            pagador: Dados do pagador (opcional)
            info_adicionais: Informações adicionais [{"nome": str, "valor": str}]

        Returns:
            Dados do PIX incluindo QR Code e copia-cola
        """
        payload = {
            "amount": int(valor * 100),
            "key": chave_pix,
            "description": descricao,
            "expiration": expiracao_segundos
        }

        if pagador:
            payload["payer"] = {
                "name": pagador.get("nome"),
                "document": pagador.get("documento", "").replace(".", "").replace("-", "").replace("/", "")
            }

        if info_adicionais:
            payload["additional_info"] = [
                {"name": i["nome"], "value": i["valor"]}
                for i in info_adicionais[:10]  # Máximo 10 infos
            ]

        response = await self._request("POST", "/pix/cob", data=payload)

        return {
            "txid": response.get("txid"),
            "status": response.get("status"),
            "valor": valor,
            "qrcode": response.get("qr_code"),
            "qrcode_base64": response.get("qr_code_base64"),
            "copia_cola": response.get("emv"),
            "expira_em": response.get("expiration"),
            "response_original": response
        }

    async def consultar_pix(self, txid: str) -> Dict:
        """Consulta status de uma cobrança PIX"""
        response = await self._request("GET", f"/pix/cob/{txid}")

        return {
            "txid": response.get("txid"),
            "status": response.get("status"),
            "valor": response.get("amount", 0) / 100,
            "valor_pago": response.get("paid_amount", 0) / 100 if response.get("paid_amount") else None,
            "data_pagamento": response.get("paid_at"),
            "end_to_end_id": response.get("end_to_end_id"),
            "response_original": response
        }

    # ==================== EXTRATO ====================

    async def consultar_extrato(
        self,
        data_inicio: str,
        data_fim: str,
        page: int = 1,
        limit: int = 100
    ) -> Dict:
        """
        Consulta extrato da conta

        Args:
            data_inicio: Data inicial (YYYY-MM-DD)
            data_fim: Data final (YYYY-MM-DD)
            page: Página
            limit: Itens por página

        Returns:
            Lista de transações
        """
        params = {
            "start_date": data_inicio,
            "end_date": data_fim,
            "page": page,
            "per_page": limit
        }

        response = await self._request("GET", "/statements", params=params)

        items = []
        for item in response.get("items", []):
            items.append({
                "id": item.get("id"),
                "data": item.get("date"),
                "tipo": "C" if item.get("type") == "CREDIT" else "D",
                "valor": item.get("amount", 0) / 100,
                "descricao": item.get("description"),
                "categoria": item.get("category"),
                "contrapartida": item.get("counterparty", {}).get("name"),
                "documento_contrapartida": item.get("counterparty", {}).get("document"),
                "referencia": item.get("reference"),
            })

        return {
            "items": items,
            "saldo_inicial": response.get("initial_balance", 0) / 100,
            "saldo_final": response.get("final_balance", 0) / 100,
            "total": response.get("total", 0),
            "page": page
        }

    async def consultar_saldo(self) -> Dict:
        """Consulta saldo atual da conta"""
        response = await self._request("GET", "/accounts/balance")

        return {
            "disponivel": response.get("available", 0) / 100,
            "bloqueado": response.get("blocked", 0) / 100,
            "total": response.get("total", 0) / 100,
            "atualizado_em": response.get("updated_at")
        }

    # ==================== API V2 - NOVOS RECURSOS ====================

    async def criar_carne(
        self,
        valor_total: float,
        numero_parcelas: int,
        data_primeiro_vencimento: str,
        pagador: Dict[str, Any],
        descricao: str = "Carnê",
        dia_vencimento: int = 10,
        multa_percentual: float = 2.0,
        juros_mensal: float = 1.0,
        **kwargs
    ) -> Dict:
        """
        Cria carnê com múltiplos boletos (API V2)

        Args:
            valor_total: Valor total do carnê
            numero_parcelas: Número de parcelas
            data_primeiro_vencimento: Data de vencimento da primeira parcela (YYYY-MM-DD)
            pagador: Dados do pagador (nome, documento, email, endereco)
            descricao: Descrição do carnê
            dia_vencimento: Dia do mês para vencimento das parcelas
            multa_percentual: Multa em percentual (padrão 2%)
            juros_mensal: Juros mensal em percentual (padrão 1%)

        Returns:
            Dados do carnê incluindo lista de boletos gerados

        Endpoint: POST /invoices/installments
        """
        payload = {
            "total_amount": int(valor_total * 100),
            "installments": numero_parcelas,
            "first_due_date": data_primeiro_vencimento,
            "due_day": dia_vencimento,
            "payer": self._format_payer(pagador),
            "description": descricao,
            "payment_terms": {
                "fine": {
                    "type": "PERCENTAGE",
                    "value": int(multa_percentual * 100)
                },
                "interest": {
                    "type": "MONTHLY_PERCENTAGE",
                    "value": int(juros_mensal * 100)
                }
            }
        }

        # Adiciona campos opcionais
        if kwargs.get("discount"):
            payload["discount"] = kwargs["discount"]

        response = await self._request("POST", "/invoices/installments", data=payload)

        return {
            "carne_id": response.get("id"),
            "boletos": [
                {
                    "id": b["id"],
                    "parcela": b["installment_number"],
                    "valor": b["amount"] / 100,
                    "vencimento": b["due_date"],
                    "codigo_barras": b["payment"]["bar_code"],
                    "linha_digitavel": b["payment"]["digitable_line"],
                    "nosso_numero": b.get("our_number"),
                    "status": b.get("status", "pending")
                }
                for b in response.get("invoices", [])
            ],
            "valor_total": valor_total,
            "numero_parcelas": numero_parcelas,
            "response_original": response
        }

    async def criar_transferencia(
        self,
        valor: float,
        beneficiario: Dict[str, Any],
        descricao: str = "Transferência",
        tipo: str = "TED"
    ) -> Dict:
        """
        Cria transferência bancária (API V2)

        Args:
            valor: Valor da transferência
            beneficiario: Dados do beneficiário:
                - tipo_conta: "CHECKING" | "SAVINGS"
                - banco: Código do banco (ex: "001")
                - agencia: Número da agência
                - conta: Número da conta
                - digito: Dígito verificador da conta
                - documento: CPF/CNPJ
                - nome: Nome do beneficiário
                - tipo_pessoa: "PF" | "PJ"
            descricao: Descrição da transferência
            tipo: Tipo de transferência ("TED", "TEF", "PIX")

        Returns:
            Dados da transferência criada

        Endpoint: POST /transfers
        """
        payload = {
            "amount": int(valor * 100),
            "description": descricao,
            "transfer_type": tipo,
            "beneficiary": {
                "account_type": beneficiario.get("tipo_conta", "CHECKING"),
                "bank_code": beneficiario["banco"],
                "branch": beneficiario["agencia"],
                "account": beneficiario["conta"],
                "account_digit": beneficiario.get("digito"),
                "document": {
                    "identity": beneficiario["documento"].replace(".", "").replace("-", "").replace("/", ""),
                    "type": beneficiario.get("tipo_pessoa", "PF")
                },
                "name": beneficiario["nome"]
            }
        }

        response = await self._request("POST", "/transfers", data=payload)

        return {
            "id": response.get("id"),
            "status": response.get("status"),
            "valor": valor,
            "tipo": tipo,
            "data_agendamento": response.get("scheduled_date"),
            "data_criacao": response.get("created_at"),
            "beneficiario": beneficiario["nome"],
            "response_original": response
        }

    async def listar_transferencias(
        self,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict:
        """
        Lista transferências (API V2)

        Args:
            data_inicio: Data inicial (YYYY-MM-DD)
            data_fim: Data final (YYYY-MM-DD)
            status: Filtrar por status
            page: Página
            limit: Limite por página

        Returns:
            Lista de transferências

        Endpoint: GET /transfers
        """
        params = {"page": page, "per_page": limit}

        if data_inicio:
            params["start_date"] = data_inicio
        if data_fim:
            params["end_date"] = data_fim
        if status:
            params["status"] = status

        response = await self._request("GET", "/transfers", params=params)

        return {
            "items": [
                {
                    "id": t["id"],
                    "valor": t["amount"] / 100,
                    "tipo": t["transfer_type"],
                    "status": t["status"],
                    "data": t["created_at"],
                    "data_agendamento": t.get("scheduled_date"),
                    "beneficiario": t["beneficiary"]["name"],
                    "descricao": t.get("description")
                }
                for t in response.get("items", [])
            ],
            "total": response.get("total", 0),
            "page": page,
            "per_page": limit
        }

    async def listar_bancos(self) -> List[Dict]:
        """
        Lista bancos disponíveis para transferência (API V2)

        Returns:
            Lista de bancos com código, nome e ISPB

        Endpoint: GET /banks
        """
        response = await self._request("GET", "/banks")

        return [
            {
                "codigo": b["code"],
                "nome": b["name"],
                "ispb": b.get("ispb")
            }
            for b in response.get("banks", [])
        ]

    async def pagar_darf(
        self,
        codigo_receita: str,
        periodo_apuracao: str,
        valor_principal: float,
        valor_multa: float = 0.0,
        valor_juros: float = 0.0,
        numero_referencia: Optional[str] = None
    ) -> Dict:
        """
        Paga DARF - Documento de Arrecadação de Receitas Federais (API V2)

        Args:
            codigo_receita: Código da receita federal
            periodo_apuracao: Período no formato "YYYY-MM"
            valor_principal: Valor principal do imposto
            valor_multa: Multa (se houver)
            valor_juros: Juros (se houver)
            numero_referencia: Número de referência (opcional)

        Returns:
            Dados do pagamento DARF

        Endpoint: POST /taxes/darf
        """
        payload = {
            "revenue_code": codigo_receita,
            "reference_period": periodo_apuracao,
            "principal_amount": int(valor_principal * 100),
            "fine_amount": int(valor_multa * 100),
            "interest_amount": int(valor_juros * 100)
        }

        if numero_referencia:
            payload["reference_number"] = numero_referencia

        response = await self._request("POST", "/taxes/darf", data=payload)

        return {
            "id": response.get("id"),
            "status": response.get("status"),
            "valor_total": (valor_principal + valor_multa + valor_juros),
            "valor_principal": valor_principal,
            "valor_multa": valor_multa,
            "valor_juros": valor_juros,
            "numero_autenticacao": response.get("authentication_number"),
            "data_pagamento": response.get("payment_date"),
            "response_original": response
        }

    async def pagar_gps(
        self,
        codigo_pagamento: str,
        competencia: str,
        identificador: str,
        valor: float
    ) -> Dict:
        """
        Paga GPS - Guia da Previdência Social (API V2)

        Args:
            codigo_pagamento: Código de pagamento GPS
            competencia: Competência no formato "YYYY-MM"
            identificador: CPF/CNPJ ou NIT
            valor: Valor a pagar

        Returns:
            Dados do pagamento GPS

        Endpoint: POST /taxes/gps
        """
        payload = {
            "payment_code": codigo_pagamento,
            "reference_month": competencia,
            "identifier": identificador.replace(".", "").replace("-", "").replace("/", ""),
            "amount": int(valor * 100)
        }

        response = await self._request("POST", "/taxes/gps", data=payload)

        return {
            "id": response.get("id"),
            "status": response.get("status"),
            "valor": valor,
            "competencia": competencia,
            "numero_autenticacao": response.get("authentication_number"),
            "data_pagamento": response.get("payment_date"),
            "response_original": response
        }

    async def consultar_dados_conta(self) -> Dict:
        """
        Consulta dados cadastrais da conta (API V2)

        Returns:
            Dados da conta bancária

        Endpoint: GET /account
        """
        response = await self._request("GET", "/account")

        return {
            "id": response.get("id"),
            "nome": response.get("name"),
            "documento": response.get("document"),
            "tipo_pessoa": response.get("document_type"),
            "agencia": response.get("branch"),
            "conta": response.get("account"),
            "digito": response.get("account_digit"),
            "banco": response.get("bank_code"),
            "status": response.get("status"),
            "data_criacao": response.get("created_at"),
            "response_original": response
        }

    # ==================== WEBHOOKS ====================

    @staticmethod
    def verificar_webhook(
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verifica assinatura do webhook

        Args:
            payload: Corpo da requisição (bytes)
            signature: Assinatura no header X-Cora-Signature
            secret: Webhook secret configurado

        Returns:
            True se assinatura válida
        """
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    @staticmethod
    def processar_webhook(body: Dict) -> Dict:
        """
        Processa payload do webhook

        Args:
            body: Corpo do webhook

        Returns:
            Dados processados do evento
        """
        event_type = body.get("type", "")
        data = body.get("data", {})

        # Mapeia tipos de evento
        if event_type == "invoice.paid":
            return {
                "tipo": "pagamento_boleto",
                "boleto_id": data.get("id"),
                "valor_pago": data.get("paid_amount", 0) / 100,
                "data_pagamento": data.get("paid_at"),
                "forma_pagamento": "boleto" if data.get("payment_method") == "BANK_SLIP" else "pix",
                "nosso_numero": data.get("our_number"),
            }

        elif event_type == "pix.received":
            return {
                "tipo": "pagamento_pix",
                "txid": data.get("txid"),
                "valor_pago": data.get("amount", 0) / 100,
                "data_pagamento": data.get("created_at"),
                "end_to_end_id": data.get("end_to_end_id"),
                "pagador_nome": data.get("payer", {}).get("name"),
                "pagador_documento": data.get("payer", {}).get("document"),
            }

        elif event_type == "invoice.overdue":
            return {
                "tipo": "boleto_vencido",
                "boleto_id": data.get("id"),
                "vencimento": data.get("due_date"),
                "valor": data.get("amount", 0) / 100,
            }

        elif event_type == "invoice.cancelled":
            return {
                "tipo": "boleto_cancelado",
                "boleto_id": data.get("id"),
            }

        # Eventos V2 - Pagamentos
        elif event_type == "payment.created":
            return {
                "tipo": "pagamento_criado",
                "payment_id": data.get("id"),
                "valor": data.get("amount", 0) / 100,
                "tipo_pagamento": data.get("payment_type"),
                "status": data.get("status"),
                "data_criacao": data.get("created_at")
            }

        elif event_type == "payment.failed":
            return {
                "tipo": "pagamento_falhou",
                "payment_id": data.get("id"),
                "motivo": data.get("failure_reason"),
                "erro_codigo": data.get("error_code"),
                "data_falha": data.get("failed_at")
            }

        # Eventos V2 - Transferências
        elif event_type == "transfer.completed":
            return {
                "tipo": "transferencia_concluida",
                "transfer_id": data.get("id"),
                "valor": data.get("amount", 0) / 100,
                "beneficiario": data.get("beneficiary", {}).get("name"),
                "tipo_transferencia": data.get("transfer_type"),
                "data_conclusao": data.get("completed_at")
            }

        elif event_type == "transfer.failed":
            return {
                "tipo": "transferencia_falhou",
                "transfer_id": data.get("id"),
                "motivo": data.get("failure_reason"),
                "erro_codigo": data.get("error_code"),
                "data_falha": data.get("failed_at")
            }

        # Eventos V2 - Carnês
        elif event_type == "installment.paid":
            return {
                "tipo": "parcela_paga",
                "installment_id": data.get("id"),
                "carne_id": data.get("installment_plan_id"),
                "numero_parcela": data.get("installment_number"),
                "valor_pago": data.get("paid_amount", 0) / 100,
                "data_pagamento": data.get("paid_at")
            }

        return {
            "tipo": event_type,
            "dados": data
        }


# ==================== FACTORY ====================

def criar_cliente_cora(
    client_id: str = None,
    client_secret: str = None,
    ambiente: str = "sandbox"
) -> CoraBankClient:
    """
    Factory para criar cliente Cora

    Se credenciais não fornecidas, usa variáveis de ambiente:
    - CORA_CLIENT_ID
    - CORA_CLIENT_SECRET
    - CORA_AMBIENTE
    """
    config = CoraConfig(
        client_id=client_id or os.getenv("CORA_CLIENT_ID", ""),
        client_secret=client_secret or os.getenv("CORA_CLIENT_SECRET", ""),
        ambiente=ambiente or os.getenv("CORA_AMBIENTE", "sandbox")
    )

    return CoraBankClient(config)


# ==================== MOCK CLIENT PARA TESTES ====================

class CoraBankMockClient:
    """
    Cliente mock para testes sem API real

    Simula comportamento da API Cora para desenvolvimento
    """

    def __init__(self):
        self._boletos = {}
        self._pix = {}
        self._contador = 1

    async def close(self):
        pass

    async def criar_boleto(
        self,
        valor: float,
        vencimento: str,
        pagador: Dict[str, Any],
        descricao: str = "Cobrança",
        **kwargs
    ) -> Dict:
        """Cria boleto mock"""
        import uuid

        boleto_id = str(uuid.uuid4())
        nosso_numero = f"{self._contador:08d}"
        self._contador += 1

        # Gera código de barras fake (47 dígitos)
        codigo_barras = f"23793.38128 60000.000003 {nosso_numero[:5]}.{nosso_numero[5:]} 1 9285{int(valor*100):010d}"

        # Gera linha digitável fake
        linha_digitavel = f"23793381286000000000300{nosso_numero}19285{int(valor):010d}"

        # Gera PIX EMV fake
        pix_emv = f"00020126580014br.gov.bcb.pix0136{uuid.uuid4()}5204000053039865406{valor:.2f}5802BR"

        boleto = {
            "id": boleto_id,
            "status": "pendente",
            "valor": valor,
            "vencimento": vencimento,
            "codigo_barras": codigo_barras,
            "linha_digitavel": linha_digitavel,
            "nosso_numero": nosso_numero,
            "url_pdf": f"https://mock.cora.com.br/boletos/{boleto_id}.pdf",
            "pix": {
                "qrcode": f"data:image/png;base64,mock_qrcode_{boleto_id[:8]}",
                "copia_cola": pix_emv,
                "txid": f"txid_{boleto_id[:16]}"
            },
            "pagador": pagador,
            "descricao": descricao,
            "created_at": datetime.now().isoformat()
        }

        self._boletos[boleto_id] = boleto
        return boleto

    async def consultar_boleto(self, boleto_id: str) -> Dict:
        """Consulta boleto mock"""
        if boleto_id in self._boletos:
            return self._boletos[boleto_id]
        raise CoraAPIError("Boleto não encontrado", status_code=404)

    async def listar_boletos(self, **kwargs) -> Dict:
        """Lista boletos mock"""
        items = list(self._boletos.values())
        return {
            "items": items,
            "total": len(items),
            "page": 1,
            "limit": 50
        }

    async def cancelar_boleto(self, boleto_id: str) -> bool:
        """Cancela boleto mock"""
        if boleto_id in self._boletos:
            self._boletos[boleto_id]["status"] = "cancelado"
            return True
        return False

    async def criar_cobranca_pix(
        self,
        valor: float,
        chave_pix: str,
        descricao: str = "Cobrança PIX",
        **kwargs
    ) -> Dict:
        """Cria PIX mock"""
        import uuid

        txid = f"pix_{uuid.uuid4().hex[:24]}"
        pix_emv = f"00020126580014br.gov.bcb.pix0136{uuid.uuid4()}5204000053039865406{valor:.2f}5802BR"

        pix = {
            "txid": txid,
            "status": "ATIVA",
            "valor": valor,
            "qrcode": f"data:image/png;base64,mock_qrcode_{txid[:8]}",
            "qrcode_base64": f"mock_base64_{txid[:8]}",
            "copia_cola": pix_emv,
            "expira_em": (datetime.now() + timedelta(hours=1)).isoformat(),
            "created_at": datetime.now().isoformat()
        }

        self._pix[txid] = pix
        return pix

    async def consultar_pix(self, txid: str) -> Dict:
        """Consulta PIX mock"""
        if txid in self._pix:
            return self._pix[txid]
        raise CoraAPIError("PIX não encontrado", status_code=404)

    async def consultar_saldo(self) -> Dict:
        """Retorna saldo mock"""
        return {
            "disponivel": 150000.00,
            "bloqueado": 5000.00,
            "total": 155000.00,
            "atualizado_em": datetime.now().isoformat()
        }

    async def consultar_extrato(
        self,
        data_inicio: str,
        data_fim: str,
        **kwargs
    ) -> Dict:
        """Retorna extrato mock"""
        return {
            "items": [
                {
                    "id": "trans_001",
                    "data": datetime.now().strftime("%Y-%m-%d"),
                    "tipo": "C",
                    "valor": 850.00,
                    "descricao": "Pagamento boleto - Apt 101",
                    "categoria": "INVOICE_PAYMENT",
                    "contrapartida": "Carlos Silva",
                    "referencia": "00000001"
                },
                {
                    "id": "trans_002",
                    "data": datetime.now().strftime("%Y-%m-%d"),
                    "tipo": "C",
                    "valor": 850.00,
                    "descricao": "PIX Recebido - Apt 102",
                    "categoria": "PIX_RECEIVED",
                    "contrapartida": "Maria Santos",
                    "referencia": "pix_abc123"
                }
            ],
            "saldo_inicial": 148300.00,
            "saldo_final": 150000.00,
            "total": 2,
            "page": 1
        }

    # ==================== MÉTODOS V2 - MOCK ====================

    async def criar_carne(
        self,
        valor_total: float,
        numero_parcelas: int,
        data_primeiro_vencimento: str,
        pagador: Dict[str, Any],
        descricao: str = "Carnê",
        **kwargs
    ) -> Dict:
        """Cria carnê mock com múltiplos boletos"""
        import uuid
        from dateutil.relativedelta import relativedelta

        carne_id = str(uuid.uuid4())
        valor_parcela = valor_total / numero_parcelas
        boletos = []

        # Gera boletos para cada parcela
        data_vencimento = datetime.fromisoformat(data_primeiro_vencimento)
        for i in range(1, numero_parcelas + 1):
            boleto_id = str(uuid.uuid4())
            nosso_numero = f"{self._contador:08d}"
            self._contador += 1

            boleto = {
                "id": boleto_id,
                "parcela": i,
                "valor": round(valor_parcela, 2),
                "vencimento": data_vencimento.strftime("%Y-%m-%d"),
                "codigo_barras": f"23793.38128 60000.000003 {nosso_numero[:5]}.{nosso_numero[5:]} 1 9285{int(valor_parcela*100):010d}",
                "linha_digitavel": f"23793381286000000000300{nosso_numero}19285{int(valor_parcela):010d}",
                "nosso_numero": nosso_numero,
                "status": "pending"
            }

            boletos.append(boleto)
            self._boletos[boleto_id] = boleto

            # Próximo mês
            data_vencimento = data_vencimento + relativedelta(months=1)

        return {
            "carne_id": carne_id,
            "boletos": boletos,
            "valor_total": valor_total,
            "numero_parcelas": numero_parcelas,
            "response_original": {
                "id": carne_id,
                "invoices": boletos
            }
        }

    async def criar_transferencia(
        self,
        valor: float,
        beneficiario: Dict[str, Any],
        descricao: str = "Transferência",
        tipo: str = "TED"
    ) -> Dict:
        """Cria transferência mock"""
        import uuid

        transfer_id = str(uuid.uuid4())

        return {
            "id": transfer_id,
            "status": "PROCESSING",
            "valor": valor,
            "tipo": tipo,
            "data_agendamento": datetime.now().strftime("%Y-%m-%d"),
            "data_criacao": datetime.now().isoformat(),
            "beneficiario": beneficiario["nome"],
            "response_original": {
                "id": transfer_id,
                "status": "PROCESSING",
                "amount": int(valor * 100),
                "transfer_type": tipo,
                "scheduled_date": datetime.now().strftime("%Y-%m-%d"),
                "created_at": datetime.now().isoformat(),
                "beneficiary": {"name": beneficiario["nome"]}
            }
        }

    async def listar_transferencias(
        self,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict:
        """Lista transferências mock"""
        return {
            "items": [
                {
                    "id": "transfer_001",
                    "valor": 5000.00,
                    "tipo": "TED",
                    "status": "COMPLETED",
                    "data": datetime.now().isoformat(),
                    "data_agendamento": datetime.now().strftime("%Y-%m-%d"),
                    "beneficiario": "Fornecedor XYZ Ltda",
                    "descricao": "Pagamento de serviços"
                },
                {
                    "id": "transfer_002",
                    "valor": 1500.00,
                    "tipo": "PIX",
                    "status": "COMPLETED",
                    "data": datetime.now().isoformat(),
                    "data_agendamento": datetime.now().strftime("%Y-%m-%d"),
                    "beneficiario": "João da Silva",
                    "descricao": "Reembolso"
                }
            ],
            "total": 2,
            "page": page,
            "per_page": limit
        }

    async def listar_bancos(self) -> List[Dict]:
        """Lista bancos mock"""
        return [
            {"codigo": "001", "nome": "Banco do Brasil S.A.", "ispb": "00000000"},
            {"codigo": "033", "nome": "Banco Santander (Brasil) S.A.", "ispb": "90400888"},
            {"codigo": "104", "nome": "Caixa Econômica Federal", "ispb": "00360305"},
            {"codigo": "237", "nome": "Banco Bradesco S.A.", "ispb": "60746948"},
            {"codigo": "341", "nome": "Itaú Unibanco S.A.", "ispb": "60701190"},
            {"codigo": "260", "nome": "Nu Pagamentos S.A. (Nubank)", "ispb": "18236120"},
            {"codigo": "077", "nome": "Banco Inter S.A.", "ispb": "00416968"}
        ]

    async def pagar_darf(
        self,
        codigo_receita: str,
        periodo_apuracao: str,
        valor_principal: float,
        valor_multa: float = 0.0,
        valor_juros: float = 0.0,
        numero_referencia: Optional[str] = None
    ) -> Dict:
        """Paga DARF mock"""
        import uuid

        payment_id = str(uuid.uuid4())
        valor_total = valor_principal + valor_multa + valor_juros

        return {
            "id": payment_id,
            "status": "PROCESSING",
            "valor_total": valor_total,
            "valor_principal": valor_principal,
            "valor_multa": valor_multa,
            "valor_juros": valor_juros,
            "numero_autenticacao": f"AUTH{self._contador:010d}",
            "data_pagamento": datetime.now().isoformat(),
            "response_original": {
                "id": payment_id,
                "status": "PROCESSING",
                "authentication_number": f"AUTH{self._contador:010d}",
                "payment_date": datetime.now().isoformat()
            }
        }

    async def pagar_gps(
        self,
        codigo_pagamento: str,
        competencia: str,
        identificador: str,
        valor: float
    ) -> Dict:
        """Paga GPS mock"""
        import uuid

        payment_id = str(uuid.uuid4())

        return {
            "id": payment_id,
            "status": "PROCESSING",
            "valor": valor,
            "competencia": competencia,
            "numero_autenticacao": f"GPS{self._contador:010d}",
            "data_pagamento": datetime.now().isoformat(),
            "response_original": {
                "id": payment_id,
                "status": "PROCESSING",
                "authentication_number": f"GPS{self._contador:010d}",
                "payment_date": datetime.now().isoformat()
            }
        }

    async def consultar_dados_conta(self) -> Dict:
        """Consulta dados da conta mock"""
        return {
            "id": "acc_mock_001",
            "nome": "Condomínio Teste Ltda",
            "documento": "12.345.678/0001-99",
            "tipo_pessoa": "PJ",
            "agencia": "0001",
            "conta": "123456",
            "digito": "7",
            "banco": "403",  # Código do Cora
            "status": "ACTIVE",
            "data_criacao": "2024-01-15T10:00:00Z",
            "response_original": {
                "id": "acc_mock_001",
                "name": "Condomínio Teste Ltda",
                "document": "12345678000199",
                "document_type": "CNPJ",
                "branch": "0001",
                "account": "123456",
                "account_digit": "7",
                "bank_code": "403",
                "status": "ACTIVE",
                "created_at": "2024-01-15T10:00:00Z"
            }
        }

    def simular_pagamento(self, boleto_id: str, valor_pago: Optional[float] = None):
        """Simula pagamento de um boleto (para testes)"""
        if boleto_id in self._boletos:
            boleto = self._boletos[boleto_id]
            boleto["status"] = "pago"
            boleto["valor_pago"] = valor_pago or boleto["valor"]
            boleto["data_pagamento"] = datetime.now().isoformat()
            return True
        return False


def criar_cliente_cora_mock() -> CoraBankMockClient:
    """Cria cliente mock para testes"""
    return CoraBankMockClient()
