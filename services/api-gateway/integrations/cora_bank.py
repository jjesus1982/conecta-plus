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

    @property
    def base_url(self) -> str:
        if self.ambiente == "production":
            return "https://api.cora.com.br"
        return "https://api.stage.cora.com.br"

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
        # Formata dados do pagador
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

        # Monta payload
        payload = {
            "amount": int(valor * 100),  # Valor em centavos
            "due_date": vencimento,
            "payer": payer,
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

        response = await self._request("POST", "/v1/invoices", data=payload)

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
        response = await self._request("GET", f"/v1/invoices/{boleto_id}")

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

        response = await self._request("GET", "/v1/invoices", params=params)

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
            await self._request("POST", f"/v1/invoices/{boleto_id}/cancel")
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

        response = await self._request("POST", "/v1/pix/cob", data=payload)

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
        response = await self._request("GET", f"/v1/pix/cob/{txid}")

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

        response = await self._request("GET", "/v1/statements", params=params)

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
        response = await self._request("GET", "/v1/accounts/balance")

        return {
            "disponivel": response.get("available", 0) / 100,
            "bloqueado": response.get("blocked", 0) / 100,
            "total": response.get("total", 0) / 100,
            "atualizado_em": response.get("updated_at")
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
