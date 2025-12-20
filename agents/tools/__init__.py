"""
Conecta Plus - Tools Module
Ferramentas para execução de ações pelos agentes

Tools são componentes que permitem aos agentes interagir com sistemas externos,
banco de dados e executar operações específicas.

Categorias:
- Database: Operações de banco de dados
- API: Chamadas a APIs externas
- Device: Controle de dispositivos
- Search: Busca e indexação
- File: Operações de arquivo
- Communication: Envio de mensagens
"""

from .base_tool import (
    BaseTool,
    ToolContext,
    ToolResult,
    ToolRegistry,
    tool,
    ToolParameter,
    ToolMetadata,
)

from .database_tools import (
    QueryTool,
    InsertTool,
    UpdateTool,
    DeleteTool,
    TransactionTool,
    MigrationTool,
)

from .api_tools import (
    HTTPClientTool,
    GraphQLTool,
    RESTfulTool,
    SOAPTool,
    WebSocketTool,
)

from .device_tools import (
    CameraTool,
    AccessControlTool,
    AlarmPanelTool,
    IntercomTool,
    SensorTool,
    GateTool,
)

from .search_tools import (
    FullTextSearchTool,
    VectorSearchTool,
    FilterTool,
    AggregationTool,
)

from .file_tools import (
    FileReadTool,
    FileWriteTool,
    FileUploadTool,
    FileConversionTool,
    ZipTool,
)

from .communication_tools import (
    SendNotificationTool,
    SendEmailTool,
    SendSMSTool,
    SendWhatsAppTool,
    BroadcastTool,
)

__all__ = [
    # Base
    "BaseTool",
    "ToolContext",
    "ToolResult",
    "ToolRegistry",
    "tool",
    "ToolParameter",
    "ToolMetadata",
    # Database
    "QueryTool",
    "InsertTool",
    "UpdateTool",
    "DeleteTool",
    "TransactionTool",
    "MigrationTool",
    # API
    "HTTPClientTool",
    "GraphQLTool",
    "RESTfulTool",
    "SOAPTool",
    "WebSocketTool",
    # Device
    "CameraTool",
    "AccessControlTool",
    "AlarmPanelTool",
    "IntercomTool",
    "SensorTool",
    "GateTool",
    # Search
    "FullTextSearchTool",
    "VectorSearchTool",
    "FilterTool",
    "AggregationTool",
    # File
    "FileReadTool",
    "FileWriteTool",
    "FileUploadTool",
    "FileConversionTool",
    "ZipTool",
    # Communication
    "SendNotificationTool",
    "SendEmailTool",
    "SendSMSTool",
    "SendWhatsAppTool",
    "BroadcastTool",
]
