"""
Conecta Plus - File Tools
Ferramentas para operações com arquivos
"""

import asyncio
import logging
import hashlib
import base64
import mimetypes
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .base_tool import (
    BaseTool, ToolContext, ToolResult, ToolMetadata,
    ToolCategory, ToolParameter, ParameterType, tool
)

logger = logging.getLogger(__name__)


# ============================================================
# File Read Tool
# ============================================================

@tool(
    name="file_read",
    version="1.0.0",
    category=ToolCategory.FILE,
    description="Leitura de arquivos",
    parameters=[
        ToolParameter("path", ParameterType.STRING, "Caminho do arquivo", required=True),
        ToolParameter("encoding", ParameterType.STRING, "Encoding do arquivo", required=False, default="utf-8"),
        ToolParameter("binary", ParameterType.BOOLEAN, "Leitura binária", required=False, default=False),
        ToolParameter("lines", ParameterType.INTEGER, "Número de linhas (0=todas)", required=False, default=0),
        ToolParameter("offset", ParameterType.INTEGER, "Offset em bytes", required=False, default=0),
    ],
    tags=["file", "read", "io"]
)
class FileReadTool(BaseTool):
    """
    Ferramenta para leitura de arquivos.
    Suporta texto e binário, com opções de paginação.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.allowed_paths = self.get_config("allowed_paths", ["/data", "/uploads", "/exports"])
        self.max_size = self.get_config("max_size", 10 * 1024 * 1024)  # 10MB

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Lê arquivo"""
        path = params.get("path")
        encoding = params.get("encoding", "utf-8")
        binary = params.get("binary", False)
        lines = params.get("lines", 0)
        offset = params.get("offset", 0)

        if not path:
            return ToolResult.fail("'path' é obrigatório")

        # Validar caminho (segurança)
        if not self._is_path_allowed(path):
            return ToolResult.fail("Caminho não permitido", error_code="PATH_NOT_ALLOWED")

        # Simular leitura (em produção, leria arquivo real)
        file_info = self._simulate_file_read(path, binary, encoding, lines, offset)

        return ToolResult.ok(file_info)

    def _is_path_allowed(self, path: str) -> bool:
        """Verifica se caminho é permitido"""
        # Em produção, verificaria contra lista de caminhos permitidos
        return not any(p in path for p in ["..", "~", "/etc", "/root", "/var"])

    def _simulate_file_read(
        self,
        path: str,
        binary: bool,
        encoding: str,
        lines: int,
        offset: int
    ) -> Dict[str, Any]:
        """Simula leitura de arquivo"""
        filename = Path(path).name
        ext = Path(path).suffix.lower()

        # Simular conteúdo baseado na extensão
        if binary:
            content = base64.b64encode(b"Binary content simulation").decode()
        elif ext == ".json":
            content = '{"example": "data", "items": [1, 2, 3]}'
        elif ext == ".csv":
            content = "nome,email,unidade\nJoão,joao@email.com,101A\nMaria,maria@email.com,102B"
        elif ext == ".txt":
            content = "Conteúdo do arquivo de texto.\nLinha 2.\nLinha 3."
        else:
            content = f"Conteúdo simulado do arquivo {filename}"

        if lines > 0 and not binary:
            content_lines = content.split("\n")
            content = "\n".join(content_lines[:lines])

        return {
            "path": path,
            "filename": filename,
            "content": content,
            "size": len(content),
            "encoding": encoding if not binary else "binary",
            "mime_type": mimetypes.guess_type(filename)[0] or "application/octet-stream",
            "lines_read": len(content.split("\n")) if not binary else None
        }


# ============================================================
# File Write Tool
# ============================================================

@tool(
    name="file_write",
    version="1.0.0",
    category=ToolCategory.FILE,
    description="Escrita de arquivos",
    parameters=[
        ToolParameter("path", ParameterType.STRING, "Caminho do arquivo", required=True),
        ToolParameter("content", ParameterType.STRING, "Conteúdo a escrever", required=True),
        ToolParameter("encoding", ParameterType.STRING, "Encoding", required=False, default="utf-8"),
        ToolParameter("mode", ParameterType.ENUM, "Modo de escrita",
                     required=False, default="write", enum_values=["write", "append"]),
        ToolParameter("create_dirs", ParameterType.BOOLEAN, "Criar diretórios", required=False, default=True),
    ],
    tags=["file", "write", "io"],
    required_permissions=["file_write"]
)
class FileWriteTool(BaseTool):
    """
    Ferramenta para escrita de arquivos.
    Suporta criação e append.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Escreve arquivo"""
        path = params.get("path")
        content = params.get("content")
        encoding = params.get("encoding", "utf-8")
        mode = params.get("mode", "write")
        create_dirs = params.get("create_dirs", True)

        if not path or content is None:
            return ToolResult.fail("'path' e 'content' são obrigatórios")

        # Validar caminho
        if not self._is_path_allowed(path):
            return ToolResult.fail("Caminho não permitido", error_code="PATH_NOT_ALLOWED")

        # Simular escrita
        bytes_written = len(content.encode(encoding))

        return ToolResult.ok({
            "path": path,
            "bytes_written": bytes_written,
            "mode": mode,
            "encoding": encoding,
            "created_at": datetime.now().isoformat()
        })

    def _is_path_allowed(self, path: str) -> bool:
        """Verifica se caminho é permitido"""
        return not any(p in path for p in ["..", "~", "/etc", "/root", "/var"])


# ============================================================
# File Upload Tool
# ============================================================

@dataclass
class UploadedFile:
    """Arquivo enviado"""
    file_id: str
    filename: str
    size: int
    mime_type: str
    path: str
    checksum: str
    uploaded_at: datetime = field(default_factory=datetime.now)


@tool(
    name="file_upload",
    version="1.0.0",
    category=ToolCategory.FILE,
    description="Upload de arquivos",
    parameters=[
        ToolParameter("filename", ParameterType.STRING, "Nome do arquivo", required=True),
        ToolParameter("content", ParameterType.STRING, "Conteúdo base64", required=True),
        ToolParameter("destination", ParameterType.STRING, "Diretório destino", required=False, default="/uploads"),
        ToolParameter("overwrite", ParameterType.BOOLEAN, "Sobrescrever se existir", required=False, default=False),
        ToolParameter("validate_type", ParameterType.BOOLEAN, "Validar tipo de arquivo", required=False, default=True),
    ],
    tags=["file", "upload", "storage"],
    required_permissions=["file_upload"]
)
class FileUploadTool(BaseTool):
    """
    Ferramenta para upload de arquivos.
    Suporta validação de tipo e checksum.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.max_size = self.get_config("max_upload_size", 50 * 1024 * 1024)  # 50MB
        self.allowed_types = self.get_config("allowed_types", [
            "image/jpeg", "image/png", "image/gif",
            "application/pdf",
            "text/plain", "text/csv",
            "application/json",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ])

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Faz upload de arquivo"""
        filename = params.get("filename")
        content = params.get("content")
        destination = params.get("destination", "/uploads")
        overwrite = params.get("overwrite", False)
        validate_type = params.get("validate_type", True)

        if not filename or not content:
            return ToolResult.fail("'filename' e 'content' são obrigatórios")

        # Decodificar conteúdo
        try:
            decoded = base64.b64decode(content)
        except Exception:
            return ToolResult.fail("Conteúdo base64 inválido", error_code="INVALID_CONTENT")

        # Verificar tamanho
        if len(decoded) > self.max_size:
            return ToolResult.fail(
                f"Arquivo muito grande (max: {self.max_size / 1024 / 1024}MB)",
                error_code="FILE_TOO_LARGE"
            )

        # Verificar tipo
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        if validate_type and mime_type not in self.allowed_types:
            return ToolResult.fail(
                f"Tipo de arquivo não permitido: {mime_type}",
                error_code="INVALID_FILE_TYPE"
            )

        # Gerar ID e checksum
        file_id = hashlib.md5(f"{filename}{datetime.now()}".encode()).hexdigest()[:16]
        checksum = hashlib.sha256(decoded).hexdigest()

        path = f"{destination}/{file_id}_{filename}"

        uploaded = UploadedFile(
            file_id=file_id,
            filename=filename,
            size=len(decoded),
            mime_type=mime_type,
            path=path,
            checksum=checksum
        )

        return ToolResult.ok({
            "file_id": uploaded.file_id,
            "filename": uploaded.filename,
            "path": uploaded.path,
            "size": uploaded.size,
            "mime_type": uploaded.mime_type,
            "checksum": uploaded.checksum,
            "uploaded_at": uploaded.uploaded_at.isoformat()
        })


# ============================================================
# File Conversion Tool
# ============================================================

class ConversionFormat(Enum):
    """Formatos de conversão"""
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    JSON = "json"
    HTML = "html"
    TXT = "txt"
    PNG = "png"
    JPEG = "jpeg"


@tool(
    name="file_conversion",
    version="1.0.0",
    category=ToolCategory.FILE,
    description="Conversão entre formatos de arquivo",
    parameters=[
        ToolParameter("source", ParameterType.STRING, "Arquivo fonte ou conteúdo base64", required=True),
        ToolParameter("source_format", ParameterType.ENUM, "Formato fonte",
                     required=True, enum_values=["pdf", "docx", "xlsx", "csv", "json", "html", "txt"]),
        ToolParameter("target_format", ParameterType.ENUM, "Formato destino",
                     required=True, enum_values=["pdf", "docx", "xlsx", "csv", "json", "html", "txt"]),
        ToolParameter("options", ParameterType.OBJECT, "Opções de conversão", required=False),
    ],
    tags=["file", "conversion", "transform"]
)
class FileConversionTool(BaseTool):
    """
    Ferramenta para conversão de formatos.
    Suporta documentos, planilhas e dados.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._supported_conversions = {
            ("csv", "json"): True,
            ("json", "csv"): True,
            ("xlsx", "csv"): True,
            ("csv", "xlsx"): True,
            ("docx", "pdf"): True,
            ("html", "pdf"): True,
            ("txt", "pdf"): True,
            ("json", "html"): True
        }

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Converte arquivo"""
        source = params.get("source")
        source_format = params.get("source_format")
        target_format = params.get("target_format")
        options = params.get("options", {})

        if not source or not source_format or not target_format:
            return ToolResult.fail("'source', 'source_format' e 'target_format' são obrigatórios")

        # Verificar se conversão é suportada
        if (source_format, target_format) not in self._supported_conversions:
            return ToolResult.fail(
                f"Conversão de {source_format} para {target_format} não suportada",
                error_code="UNSUPPORTED_CONVERSION"
            )

        # Simular conversão
        output_id = hashlib.md5(f"{source}{target_format}{datetime.now()}".encode()).hexdigest()[:12]

        return ToolResult.ok({
            "output_id": output_id,
            "output_path": f"/converted/{output_id}.{target_format}",
            "source_format": source_format,
            "target_format": target_format,
            "size": len(source) * 2,  # Simulado
            "converted_at": datetime.now().isoformat()
        })


# ============================================================
# Zip Tool
# ============================================================

@tool(
    name="zip",
    version="1.0.0",
    category=ToolCategory.FILE,
    description="Compactação e descompactação de arquivos",
    parameters=[
        ToolParameter("action", ParameterType.ENUM, "Ação",
                     required=True, enum_values=["compress", "decompress", "list"]),
        ToolParameter("files", ParameterType.ARRAY, "Arquivos para compactar", required=False),
        ToolParameter("archive", ParameterType.STRING, "Caminho do arquivo zip", required=False),
        ToolParameter("destination", ParameterType.STRING, "Destino para extração", required=False),
        ToolParameter("password", ParameterType.STRING, "Senha (opcional)", required=False),
        ToolParameter("compression", ParameterType.ENUM, "Nível de compressão",
                     required=False, default="normal", enum_values=["none", "fast", "normal", "best"]),
    ],
    tags=["file", "zip", "compress", "archive"]
)
class ZipTool(BaseTool):
    """
    Ferramenta para compactação.
    Suporta zip, tar.gz e outros formatos.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa operação de zip"""
        action = params.get("action")

        if action == "compress":
            return await self._compress(context, params)
        elif action == "decompress":
            return await self._decompress(context, params)
        elif action == "list":
            return await self._list_contents(context, params)
        else:
            return ToolResult.fail(f"Ação desconhecida: {action}")

    async def _compress(self, context: ToolContext, params: Dict) -> ToolResult:
        """Compacta arquivos"""
        files = params.get("files", [])
        destination = params.get("destination", "/archives")
        compression = params.get("compression", "normal")
        password = params.get("password")

        if not files:
            return ToolResult.fail("'files' é obrigatório para compactar")

        archive_id = hashlib.md5(f"{files}{datetime.now()}".encode()).hexdigest()[:12]
        archive_path = f"{destination}/archive_{archive_id}.zip"

        return ToolResult.ok({
            "archive_path": archive_path,
            "files_count": len(files),
            "compression": compression,
            "encrypted": password is not None,
            "size_original": len(files) * 10000,  # Simulado
            "size_compressed": len(files) * 5000,  # Simulado
            "compression_ratio": "50%",
            "created_at": datetime.now().isoformat()
        })

    async def _decompress(self, context: ToolContext, params: Dict) -> ToolResult:
        """Descompacta arquivo"""
        archive = params.get("archive")
        destination = params.get("destination", "/extracted")
        password = params.get("password")

        if not archive:
            return ToolResult.fail("'archive' é obrigatório para descompactar")

        return ToolResult.ok({
            "archive": archive,
            "destination": destination,
            "files_extracted": 5,  # Simulado
            "total_size": 50000,  # Simulado
            "extracted_at": datetime.now().isoformat()
        })

    async def _list_contents(self, context: ToolContext, params: Dict) -> ToolResult:
        """Lista conteúdo do arquivo"""
        archive = params.get("archive")

        if not archive:
            return ToolResult.fail("'archive' é obrigatório")

        # Simular lista de arquivos
        files = [
            {"name": "documento.pdf", "size": 15000, "compressed_size": 8000},
            {"name": "planilha.xlsx", "size": 25000, "compressed_size": 12000},
            {"name": "imagem.png", "size": 100000, "compressed_size": 95000}
        ]

        return ToolResult.ok({
            "archive": archive,
            "files": files,
            "total_files": len(files),
            "total_size": sum(f["size"] for f in files),
            "compressed_size": sum(f["compressed_size"] for f in files)
        })


def register_file_tools():
    """Registra todas as ferramentas de arquivo"""
    pass
