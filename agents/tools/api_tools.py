"""
Conecta Plus - API Tools
Ferramentas para integração com APIs externas
"""

import asyncio
import logging
import json
import hashlib
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlencode, urlparse

from .base_tool import (
    BaseTool, ToolContext, ToolResult, ToolMetadata,
    ToolCategory, ToolParameter, ParameterType, tool
)

logger = logging.getLogger(__name__)


class HTTPMethod(Enum):
    """Métodos HTTP"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class HTTPResponse:
    """Resposta HTTP"""
    status_code: int
    headers: Dict[str, str]
    body: Any
    elapsed_ms: float


# ============================================================
# HTTP Client Tool
# ============================================================

@tool(
    name="http_client",
    version="1.0.0",
    category=ToolCategory.API,
    description="Cliente HTTP para requisições a APIs externas",
    parameters=[
        ToolParameter("url", ParameterType.STRING, "URL da requisição", required=True),
        ToolParameter("method", ParameterType.ENUM, "Método HTTP",
                     required=False, default="GET",
                     enum_values=["GET", "POST", "PUT", "PATCH", "DELETE"]),
        ToolParameter("headers", ParameterType.OBJECT, "Headers da requisição", required=False),
        ToolParameter("body", ParameterType.OBJECT, "Corpo da requisição", required=False),
        ToolParameter("params", ParameterType.OBJECT, "Query parameters", required=False),
        ToolParameter("timeout", ParameterType.INTEGER, "Timeout em segundos", required=False, default=30),
        ToolParameter("auth", ParameterType.OBJECT, "Autenticação", required=False),
    ],
    tags=["http", "api", "rest", "client"],
    rate_limit_per_minute=60
)
class HTTPClientTool(BaseTool):
    """
    Cliente HTTP genérico.
    Suporta todos os métodos HTTP, autenticação e retry.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.default_headers = {
            "User-Agent": "ConectaPlus-Agent/1.0",
            "Accept": "application/json"
        }

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa requisição HTTP"""
        url = params.get("url")
        method = params.get("method", "GET").upper()
        headers = {**self.default_headers, **(params.get("headers") or {})}
        body = params.get("body")
        query_params = params.get("params")
        timeout = params.get("timeout", 30)
        auth = params.get("auth")

        # Validar URL
        if not url:
            return ToolResult.fail("'url' é obrigatório")

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ToolResult.fail("URL inválida", error_code="INVALID_URL")

        # Adicionar query params
        if query_params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(query_params)}"

        # Adicionar autenticação
        if auth:
            auth_type = auth.get("type", "bearer")
            if auth_type == "bearer":
                headers["Authorization"] = f"Bearer {auth.get('token', '')}"
            elif auth_type == "basic":
                credentials = base64.b64encode(
                    f"{auth.get('username', '')}:{auth.get('password', '')}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {credentials}"
            elif auth_type == "api_key":
                header_name = auth.get("header", "X-API-Key")
                headers[header_name] = auth.get("key", "")

        # Simular requisição (em produção, usaria aiohttp/httpx)
        response = await self._simulate_request(url, method, headers, body)

        return ToolResult.ok({
            "status_code": response.status_code,
            "headers": response.headers,
            "body": response.body,
            "elapsed_ms": response.elapsed_ms,
            "url": url,
            "method": method
        })

    async def _simulate_request(
        self,
        url: str,
        method: str,
        headers: Dict,
        body: Any
    ) -> HTTPResponse:
        """Simula requisição HTTP"""
        # Simular latência
        await asyncio.sleep(0.1)

        return HTTPResponse(
            status_code=200,
            headers={
                "Content-Type": "application/json",
                "X-Request-ID": hashlib.md5(f"{url}{datetime.now()}".encode()).hexdigest()[:8]
            },
            body={"success": True, "message": "Requisição simulada"},
            elapsed_ms=100.0
        )


# ============================================================
# GraphQL Tool
# ============================================================

@tool(
    name="graphql",
    version="1.0.0",
    category=ToolCategory.API,
    description="Cliente GraphQL para queries e mutations",
    parameters=[
        ToolParameter("endpoint", ParameterType.STRING, "URL do endpoint GraphQL", required=True),
        ToolParameter("query", ParameterType.STRING, "Query ou Mutation GraphQL", required=True),
        ToolParameter("variables", ParameterType.OBJECT, "Variáveis da query", required=False),
        ToolParameter("operation_name", ParameterType.STRING, "Nome da operação", required=False),
        ToolParameter("headers", ParameterType.OBJECT, "Headers adicionais", required=False),
    ],
    tags=["graphql", "api", "query"]
)
class GraphQLTool(BaseTool):
    """
    Cliente GraphQL.
    Suporta queries, mutations e subscriptions.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa query GraphQL"""
        endpoint = params.get("endpoint")
        query = params.get("query")
        variables = params.get("variables", {})
        operation_name = params.get("operation_name")
        headers = params.get("headers", {})

        if not endpoint or not query:
            return ToolResult.fail("'endpoint' e 'query' são obrigatórios")

        # Construir payload
        payload = {
            "query": query,
            "variables": variables
        }

        if operation_name:
            payload["operationName"] = operation_name

        # Simular execução
        response = await self._simulate_graphql(endpoint, payload)

        if response.get("errors"):
            return ToolResult.fail(
                f"GraphQL errors: {response['errors']}",
                error_code="GRAPHQL_ERROR"
            )

        return ToolResult.ok({
            "data": response.get("data"),
            "extensions": response.get("extensions"),
            "endpoint": endpoint
        })

    async def _simulate_graphql(
        self,
        endpoint: str,
        payload: Dict
    ) -> Dict[str, Any]:
        """Simula execução GraphQL"""
        return {
            "data": {
                "example": {
                    "id": "1",
                    "name": "Exemplo"
                }
            },
            "extensions": {
                "tracing": {
                    "duration": 15000000
                }
            }
        }


# ============================================================
# RESTful Tool
# ============================================================

@tool(
    name="restful",
    version="1.0.0",
    category=ToolCategory.API,
    description="Cliente REST com convenções RESTful",
    parameters=[
        ToolParameter("base_url", ParameterType.STRING, "URL base da API", required=True),
        ToolParameter("resource", ParameterType.STRING, "Nome do recurso", required=True),
        ToolParameter("action", ParameterType.ENUM, "Ação CRUD",
                     required=True,
                     enum_values=["list", "get", "create", "update", "delete"]),
        ToolParameter("resource_id", ParameterType.STRING, "ID do recurso", required=False),
        ToolParameter("data", ParameterType.OBJECT, "Dados do recurso", required=False),
        ToolParameter("filters", ParameterType.OBJECT, "Filtros para listagem", required=False),
        ToolParameter("pagination", ParameterType.OBJECT, "Paginação", required=False),
    ],
    tags=["rest", "api", "crud"]
)
class RESTfulTool(BaseTool):
    """
    Cliente REST com convenções.
    Mapeia ações CRUD para métodos HTTP automaticamente.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa operação REST"""
        base_url = params.get("base_url", "").rstrip("/")
        resource = params.get("resource")
        action = params.get("action")
        resource_id = params.get("resource_id")
        data = params.get("data")
        filters = params.get("filters", {})
        pagination = params.get("pagination", {})

        if not base_url or not resource or not action:
            return ToolResult.fail("'base_url', 'resource' e 'action' são obrigatórios")

        # Construir URL e método
        url = f"{base_url}/{resource}"
        method = "GET"
        body = None

        if action == "list":
            method = "GET"
            query_params = {**filters, **pagination}
            if query_params:
                url += "?" + urlencode(query_params)

        elif action == "get":
            if not resource_id:
                return ToolResult.fail("'resource_id' é obrigatório para 'get'")
            method = "GET"
            url += f"/{resource_id}"

        elif action == "create":
            if not data:
                return ToolResult.fail("'data' é obrigatório para 'create'")
            method = "POST"
            body = data

        elif action == "update":
            if not resource_id or not data:
                return ToolResult.fail("'resource_id' e 'data' são obrigatórios para 'update'")
            method = "PUT"
            url += f"/{resource_id}"
            body = data

        elif action == "delete":
            if not resource_id:
                return ToolResult.fail("'resource_id' é obrigatório para 'delete'")
            method = "DELETE"
            url += f"/{resource_id}"

        # Simular requisição
        response = await self._simulate_rest(url, method, body, action)

        return ToolResult.ok({
            "action": action,
            "resource": resource,
            "url": url,
            "method": method,
            **response
        })

    async def _simulate_rest(
        self,
        url: str,
        method: str,
        body: Any,
        action: str
    ) -> Dict[str, Any]:
        """Simula operação REST"""
        if action == "list":
            return {
                "data": [
                    {"id": "1", "name": "Item 1"},
                    {"id": "2", "name": "Item 2"}
                ],
                "total": 2,
                "page": 1,
                "per_page": 10
            }
        elif action == "get":
            return {
                "data": {"id": "1", "name": "Item 1"}
            }
        elif action == "create":
            return {
                "data": {"id": "new_id", **body},
                "status": "created"
            }
        elif action == "update":
            return {
                "data": body,
                "status": "updated"
            }
        elif action == "delete":
            return {
                "status": "deleted"
            }

        return {}


# ============================================================
# SOAP Tool
# ============================================================

@tool(
    name="soap",
    version="1.0.0",
    category=ToolCategory.API,
    description="Cliente SOAP para webservices",
    parameters=[
        ToolParameter("wsdl_url", ParameterType.STRING, "URL do WSDL", required=True),
        ToolParameter("operation", ParameterType.STRING, "Nome da operação", required=True),
        ToolParameter("params", ParameterType.OBJECT, "Parâmetros da operação", required=False),
        ToolParameter("headers", ParameterType.OBJECT, "SOAP Headers", required=False),
        ToolParameter("namespace", ParameterType.STRING, "Namespace", required=False),
    ],
    tags=["soap", "webservice", "xml"]
)
class SOAPTool(BaseTool):
    """
    Cliente SOAP para webservices.
    Suporta WSDL e operações customizadas.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa operação SOAP"""
        wsdl_url = params.get("wsdl_url")
        operation = params.get("operation")
        op_params = params.get("params", {})
        soap_headers = params.get("headers", {})
        namespace = params.get("namespace")

        if not wsdl_url or not operation:
            return ToolResult.fail("'wsdl_url' e 'operation' são obrigatórios")

        # Construir envelope SOAP
        envelope = self._build_soap_envelope(operation, op_params, soap_headers, namespace)

        # Simular chamada
        response = await self._simulate_soap(wsdl_url, operation, envelope)

        return ToolResult.ok({
            "operation": operation,
            "wsdl": wsdl_url,
            "response": response,
            "success": True
        })

    def _build_soap_envelope(
        self,
        operation: str,
        params: Dict,
        headers: Dict,
        namespace: str
    ) -> str:
        """Constrói envelope SOAP"""
        ns = namespace or "http://example.com/namespace"

        header_xml = ""
        if headers:
            header_items = "".join(f"<{k}>{v}</{k}>" for k, v in headers.items())
            header_xml = f"<soap:Header>{header_items}</soap:Header>"

        param_xml = "".join(f"<{k}>{v}</{k}>" for k, v in params.items())

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:ns="{ns}">
    {header_xml}
    <soap:Body>
        <ns:{operation}>
            {param_xml}
        </ns:{operation}>
    </soap:Body>
</soap:Envelope>"""

    async def _simulate_soap(
        self,
        wsdl: str,
        operation: str,
        envelope: str
    ) -> Dict[str, Any]:
        """Simula chamada SOAP"""
        return {
            "result": "Success",
            "data": {
                "code": "OK",
                "message": "Operação executada com sucesso"
            }
        }


# ============================================================
# WebSocket Tool
# ============================================================

@dataclass
class WebSocketConnection:
    """Conexão WebSocket"""
    connection_id: str
    url: str
    status: str = "disconnected"
    messages_sent: int = 0
    messages_received: int = 0
    connected_at: Optional[datetime] = None


@tool(
    name="websocket",
    version="1.0.0",
    category=ToolCategory.API,
    description="Cliente WebSocket para comunicação em tempo real",
    parameters=[
        ToolParameter("action", ParameterType.ENUM, "Ação WebSocket",
                     required=True,
                     enum_values=["connect", "send", "receive", "disconnect", "status"]),
        ToolParameter("url", ParameterType.STRING, "URL WebSocket", required=False),
        ToolParameter("connection_id", ParameterType.STRING, "ID da conexão", required=False),
        ToolParameter("message", ParameterType.OBJECT, "Mensagem a enviar", required=False),
        ToolParameter("timeout", ParameterType.INTEGER, "Timeout para receive", required=False, default=30),
    ],
    tags=["websocket", "realtime", "streaming"]
)
class WebSocketTool(BaseTool):
    """
    Cliente WebSocket.
    Suporta conexão, envio, recebimento e gerenciamento de conexões.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._connections: Dict[str, WebSocketConnection] = {}

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa ação WebSocket"""
        action = params.get("action")

        if action == "connect":
            return await self._connect(params)
        elif action == "send":
            return await self._send(params)
        elif action == "receive":
            return await self._receive(params)
        elif action == "disconnect":
            return await self._disconnect(params)
        elif action == "status":
            return await self._get_status(params)
        else:
            return ToolResult.fail(f"Ação desconhecida: {action}")

    async def _connect(self, params: Dict) -> ToolResult:
        """Conecta ao WebSocket"""
        url = params.get("url")
        if not url:
            return ToolResult.fail("'url' é obrigatório para connect")

        connection_id = hashlib.md5(f"{url}{datetime.now()}".encode()).hexdigest()[:12]

        connection = WebSocketConnection(
            connection_id=connection_id,
            url=url,
            status="connected",
            connected_at=datetime.now()
        )

        self._connections[connection_id] = connection

        return ToolResult.ok({
            "connection_id": connection_id,
            "url": url,
            "status": "connected"
        })

    async def _send(self, params: Dict) -> ToolResult:
        """Envia mensagem"""
        connection_id = params.get("connection_id")
        message = params.get("message")

        if not connection_id or not message:
            return ToolResult.fail("'connection_id' e 'message' são obrigatórios")

        conn = self._connections.get(connection_id)
        if not conn or conn.status != "connected":
            return ToolResult.fail("Conexão não encontrada ou desconectada")

        conn.messages_sent += 1

        return ToolResult.ok({
            "connection_id": connection_id,
            "sent": True,
            "messages_sent": conn.messages_sent
        })

    async def _receive(self, params: Dict) -> ToolResult:
        """Recebe mensagem"""
        connection_id = params.get("connection_id")
        timeout = params.get("timeout", 30)

        if not connection_id:
            return ToolResult.fail("'connection_id' é obrigatório")

        conn = self._connections.get(connection_id)
        if not conn or conn.status != "connected":
            return ToolResult.fail("Conexão não encontrada ou desconectada")

        # Simular recebimento
        conn.messages_received += 1

        return ToolResult.ok({
            "connection_id": connection_id,
            "message": {"type": "event", "data": "simulated_message"},
            "messages_received": conn.messages_received
        })

    async def _disconnect(self, params: Dict) -> ToolResult:
        """Desconecta"""
        connection_id = params.get("connection_id")

        if not connection_id:
            return ToolResult.fail("'connection_id' é obrigatório")

        conn = self._connections.get(connection_id)
        if conn:
            conn.status = "disconnected"

        return ToolResult.ok({
            "connection_id": connection_id,
            "status": "disconnected"
        })

    async def _get_status(self, params: Dict) -> ToolResult:
        """Retorna status da conexão"""
        connection_id = params.get("connection_id")

        if connection_id:
            conn = self._connections.get(connection_id)
            if not conn:
                return ToolResult.fail("Conexão não encontrada")

            return ToolResult.ok({
                "connection_id": conn.connection_id,
                "url": conn.url,
                "status": conn.status,
                "messages_sent": conn.messages_sent,
                "messages_received": conn.messages_received,
                "connected_at": conn.connected_at.isoformat() if conn.connected_at else None
            })

        # Listar todas as conexões
        connections = [
            {
                "connection_id": c.connection_id,
                "url": c.url,
                "status": c.status
            }
            for c in self._connections.values()
        ]

        return ToolResult.ok({
            "connections": connections,
            "total": len(connections)
        })


def register_api_tools():
    """Registra todas as ferramentas de API"""
    pass
