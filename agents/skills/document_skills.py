"""
Conecta Plus - Document Skills
Habilidades de processamento de documentos
"""

import asyncio
import logging
import re
import io
import base64
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .base_skill import (
    BaseSkill, SkillContext, SkillResult, SkillMetadata,
    SkillCategory, skill
)

logger = logging.getLogger(__name__)


# ============================================================
# PDF Extraction Skill
# ============================================================

@dataclass
class PDFPage:
    """Página de PDF extraída"""
    page_number: int
    text: str
    images: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[List[List[str]]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PDFDocument:
    """Documento PDF processado"""
    filename: str
    page_count: int
    pages: List[PDFPage]
    metadata: Dict[str, Any]

    # Extração
    full_text: str = ""
    tables: List[List[List[str]]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)


@skill(
    name="pdf_extraction",
    version="1.0.0",
    category=SkillCategory.DOCUMENT,
    description="Extração de conteúdo de PDFs",
    tags=["pdf", "extraction", "document", "ocr"]
)
class PDFExtractionSkill(BaseSkill):
    """
    Skill para extração de conteúdo de arquivos PDF.
    Suporta extração de texto, tabelas e imagens.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.enable_ocr = self.get_config("enable_ocr", True)
        self.extract_images = self.get_config("extract_images", False)
        self.extract_tables = self.get_config("extract_tables", True)

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa extração de PDF"""
        action = params.get("action", "extract")

        if action == "extract":
            return await self._extract_pdf(context, params)
        elif action == "extract_text":
            return await self._extract_text(context, params)
        elif action == "extract_tables":
            return await self._extract_tables(context, params)
        elif action == "get_metadata":
            return await self._get_metadata(context, params)
        elif action == "split":
            return await self._split_pdf(context, params)
        elif action == "merge":
            return await self._merge_pdfs(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _extract_pdf(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Extrai conteúdo completo do PDF"""
        file_path = params.get("file_path")
        file_content = params.get("file_content")  # Base64

        if not file_path and not file_content:
            return SkillResult.fail("'file_path' ou 'file_content' é obrigatório")

        # Simular extração (em produção, usaria PyPDF2/pdfplumber)
        filename = file_path if file_path else "document.pdf"

        # Estrutura de exemplo
        pages = [
            PDFPage(
                page_number=1,
                text="Página 1 - Conteúdo extraído do PDF...",
                tables=[],
                images=[]
            ),
            PDFPage(
                page_number=2,
                text="Página 2 - Mais conteúdo...",
                tables=[
                    [["Coluna 1", "Coluna 2"], ["Valor 1", "Valor 2"]]
                ],
                images=[]
            )
        ]

        document = PDFDocument(
            filename=filename,
            page_count=len(pages),
            pages=pages,
            metadata={
                "title": "Documento Exemplo",
                "author": "Sistema",
                "created": datetime.now().isoformat(),
                "producer": "Conecta Plus"
            },
            full_text="\n\n".join(p.text for p in pages)
        )

        return SkillResult.ok({
            "filename": document.filename,
            "page_count": document.page_count,
            "full_text": document.full_text,
            "tables_found": sum(len(p.tables) for p in pages),
            "images_found": sum(len(p.images) for p in pages),
            "metadata": document.metadata,
            "pages": [
                {
                    "page_number": p.page_number,
                    "text_length": len(p.text),
                    "has_tables": len(p.tables) > 0,
                    "has_images": len(p.images) > 0
                }
                for p in pages
            ]
        })

    async def _extract_text(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Extrai apenas texto"""
        result = await self._extract_pdf(context, params)

        if not result.success:
            return result

        return SkillResult.ok({
            "text": result.data["full_text"],
            "page_count": result.data["page_count"]
        })

    async def _extract_tables(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Extrai tabelas do PDF"""
        file_path = params.get("file_path")

        if not file_path:
            return SkillResult.fail("'file_path' é obrigatório")

        # Simular extração de tabelas
        tables = [
            {
                "page": 1,
                "table_index": 0,
                "headers": ["Nome", "Unidade", "Valor"],
                "rows": [
                    ["João Silva", "101A", "R$ 500,00"],
                    ["Maria Santos", "102B", "R$ 450,00"]
                ]
            }
        ]

        return SkillResult.ok({
            "tables": tables,
            "count": len(tables)
        })

    async def _get_metadata(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém metadados do PDF"""
        file_path = params.get("file_path")

        if not file_path:
            return SkillResult.fail("'file_path' é obrigatório")

        return SkillResult.ok({
            "title": "Documento",
            "author": "Sistema",
            "subject": "",
            "creator": "Conecta Plus",
            "producer": "PyPDF2",
            "creation_date": datetime.now().isoformat(),
            "modification_date": datetime.now().isoformat(),
            "page_count": 5,
            "file_size": 102400,
            "encrypted": False
        })

    async def _split_pdf(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Divide PDF em páginas"""
        file_path = params.get("file_path")
        pages = params.get("pages")  # Lista de páginas ou ranges

        if not file_path:
            return SkillResult.fail("'file_path' é obrigatório")

        # Simular divisão
        output_files = []

        if pages:
            for page_range in pages:
                output_files.append({
                    "filename": f"split_{page_range}.pdf",
                    "pages": page_range
                })
        else:
            for i in range(1, 6):
                output_files.append({
                    "filename": f"page_{i}.pdf",
                    "pages": str(i)
                })

        return SkillResult.ok({
            "output_files": output_files,
            "count": len(output_files)
        })

    async def _merge_pdfs(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Mescla múltiplos PDFs"""
        files = params.get("files", [])
        output_path = params.get("output_path", "merged.pdf")

        if not files:
            return SkillResult.fail("'files' é obrigatório")

        return SkillResult.ok({
            "output_path": output_path,
            "merged_files": len(files),
            "total_pages": len(files) * 5  # Estimativa
        })


# ============================================================
# OCR Skill
# ============================================================

class OCREngine(Enum):
    """Motor de OCR"""
    TESSERACT = "tesseract"
    GOOGLE_VISION = "google_vision"
    AWS_TEXTRACT = "aws_textract"
    AZURE_COGNITIVE = "azure_cognitive"


@dataclass
class OCRResult:
    """Resultado de OCR"""
    text: str
    confidence: float
    language: str

    # Detalhes
    words: List[Dict[str, Any]] = field(default_factory=list)
    lines: List[Dict[str, Any]] = field(default_factory=list)
    blocks: List[Dict[str, Any]] = field(default_factory=list)


@skill(
    name="ocr",
    version="1.0.0",
    category=SkillCategory.DOCUMENT,
    description="Reconhecimento óptico de caracteres",
    tags=["ocr", "image", "text", "extraction"]
)
class OCRSkill(BaseSkill):
    """
    Skill para OCR de imagens e documentos.
    Suporta múltiplos engines e pós-processamento.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.engine = OCREngine(self.get_config("engine", "tesseract"))
        self.default_language = self.get_config("language", "por")
        self.preprocess = self.get_config("preprocess", True)

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa OCR"""
        action = params.get("action", "extract")

        if action == "extract":
            return await self._extract_text(context, params)
        elif action == "extract_structured":
            return await self._extract_structured(context, params)
        elif action == "detect_language":
            return await self._detect_language(context, params)
        elif action == "batch":
            return await self._batch_ocr(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _extract_text(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Extrai texto de imagem"""
        image_path = params.get("image_path")
        image_content = params.get("image_content")  # Base64
        language = params.get("language", self.default_language)

        if not image_path and not image_content:
            return SkillResult.fail("'image_path' ou 'image_content' é obrigatório")

        # Simular OCR (em produção, usaria pytesseract ou API)
        text = """BOLETO DE CONDOMÍNIO

Condomínio: Residencial Vista Verde
Unidade: 101A - Bloco A
Competência: Dezembro/2024
Valor: R$ 850,00
Vencimento: 10/12/2024

Taxa condominial: R$ 650,00
Fundo de reserva: R$ 100,00
Água/Gás: R$ 100,00"""

        return SkillResult.ok({
            "text": text,
            "confidence": 0.92,
            "language": language,
            "engine": self.engine.value,
            "word_count": len(text.split()),
            "line_count": len(text.split('\n'))
        })

    async def _extract_structured(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Extrai texto com estrutura (posição, confiança)"""
        result = await self._extract_text(context, params)

        if not result.success:
            return result

        text = result.data["text"]
        lines = text.split('\n')

        structured_lines = []
        y_position = 0

        for line in lines:
            if line.strip():
                structured_lines.append({
                    "text": line.strip(),
                    "confidence": 0.9 + (hash(line) % 10) / 100,
                    "bounding_box": {
                        "x": 50,
                        "y": y_position,
                        "width": len(line) * 8,
                        "height": 20
                    }
                })
            y_position += 25

        return SkillResult.ok({
            "lines": structured_lines,
            "full_text": text,
            "average_confidence": sum(l["confidence"] for l in structured_lines) / len(structured_lines) if structured_lines else 0
        })

    async def _detect_language(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Detecta idioma do texto na imagem"""
        result = await self._extract_text(context, {**params, "language": "auto"})

        if not result.success:
            return result

        text = result.data["text"].lower()

        # Heurística simples
        pt_words = ["de", "do", "da", "que", "em", "para", "com", "não", "uma", "os"]
        en_words = ["the", "is", "of", "and", "to", "in", "for", "that", "with", "as"]
        es_words = ["de", "el", "la", "que", "en", "y", "los", "del", "se", "las"]

        pt_count = sum(1 for w in pt_words if f" {w} " in f" {text} ")
        en_count = sum(1 for w in en_words if f" {w} " in f" {text} ")
        es_count = sum(1 for w in es_words if f" {w} " in f" {text} ")

        detected = "pt"
        if en_count > pt_count and en_count > es_count:
            detected = "en"
        elif es_count > pt_count:
            detected = "es"

        return SkillResult.ok({
            "detected_language": detected,
            "confidence": 0.85,
            "alternatives": [
                {"language": "pt", "confidence": pt_count / 10},
                {"language": "en", "confidence": en_count / 10},
                {"language": "es", "confidence": es_count / 10}
            ]
        })

    async def _batch_ocr(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Processa múltiplas imagens"""
        images = params.get("images", [])

        if not images:
            return SkillResult.fail("'images' é obrigatório")

        results = []

        for img in images:
            result = await self._extract_text(context, {"image_path": img})
            results.append({
                "image": img,
                "success": result.success,
                "text": result.data.get("text") if result.success else None,
                "error": result.error
            })

        success_count = sum(1 for r in results if r["success"])

        return SkillResult.ok({
            "results": results,
            "total": len(images),
            "success": success_count,
            "failed": len(images) - success_count
        })


# ============================================================
# Document Generation Skill
# ============================================================

class DocumentFormat(Enum):
    """Formatos de documento"""
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    TXT = "txt"
    XLSX = "xlsx"
    CSV = "csv"


@dataclass
class DocumentStyle:
    """Estilo de documento"""
    font_family: str = "Arial"
    font_size: int = 12
    line_spacing: float = 1.5
    margin_top: int = 72
    margin_bottom: int = 72
    margin_left: int = 72
    margin_right: int = 72
    header_font_size: int = 16
    header_bold: bool = True


@skill(
    name="document_generation",
    version="1.0.0",
    category=SkillCategory.DOCUMENT,
    description="Geração de documentos",
    tags=["document", "generation", "pdf", "report"]
)
class DocumentGenerationSkill(BaseSkill):
    """
    Skill para geração de documentos.
    Suporta múltiplos formatos e templates.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.default_format = DocumentFormat(self.get_config("format", "pdf"))
        self.templates_path = self.get_config("templates_path", "/templates")

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Gera documento"""
        action = params.get("action", "generate")

        if action == "generate":
            return await self._generate_document(context, params)
        elif action == "generate_report":
            return await self._generate_report(context, params)
        elif action == "generate_receipt":
            return await self._generate_receipt(context, params)
        elif action == "generate_letter":
            return await self._generate_letter(context, params)
        elif action == "convert":
            return await self._convert_format(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _generate_document(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Gera documento genérico"""
        title = params.get("title", "Documento")
        content = params.get("content", "")
        sections = params.get("sections", [])
        format_type = DocumentFormat(params.get("format", self.default_format.value))

        # Construir conteúdo
        full_content = f"# {title}\n\n{content}"

        for section in sections:
            full_content += f"\n\n## {section.get('title', '')}\n\n{section.get('content', '')}"

        # Simular geração
        doc_id = hashlib.md5(f"{title}{datetime.now()}".encode()).hexdigest()[:12]
        filename = f"{title.lower().replace(' ', '_')}_{doc_id}.{format_type.value}"

        return SkillResult.ok({
            "filename": filename,
            "format": format_type.value,
            "size_bytes": len(full_content) * 2,  # Estimativa
            "page_count": max(1, len(full_content) // 3000),
            "generated_at": datetime.now().isoformat(),
            "content_preview": full_content[:500]
        })

    async def _generate_report(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Gera relatório estruturado"""
        report_type = params.get("type", "generic")
        data = params.get("data", {})
        period = params.get("period", {})

        title = f"Relatório {report_type.title()}"

        if period:
            title += f" - {period.get('start', '')} a {period.get('end', '')}"

        sections = []

        if report_type == "financeiro":
            sections = [
                {
                    "title": "Resumo Financeiro",
                    "content": f"Receitas: R$ {data.get('receitas', 0):,.2f}\n"
                              f"Despesas: R$ {data.get('despesas', 0):,.2f}\n"
                              f"Saldo: R$ {data.get('saldo', 0):,.2f}"
                },
                {
                    "title": "Inadimplência",
                    "content": f"Taxa: {data.get('inadimplencia', 0):.1f}%\n"
                              f"Unidades: {data.get('unidades_inadimplentes', 0)}"
                }
            ]
        elif report_type == "ocorrencias":
            sections = [
                {
                    "title": "Resumo de Ocorrências",
                    "content": f"Total: {data.get('total', 0)}\n"
                              f"Resolvidas: {data.get('resolvidas', 0)}\n"
                              f"Pendentes: {data.get('pendentes', 0)}"
                }
            ]
        elif report_type == "acesso":
            sections = [
                {
                    "title": "Movimentação",
                    "content": f"Entradas: {data.get('entradas', 0)}\n"
                              f"Saídas: {data.get('saidas', 0)}\n"
                              f"Visitantes: {data.get('visitantes', 0)}"
                }
            ]

        return await self._generate_document(context, {
            "title": title,
            "content": f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "sections": sections,
            "format": params.get("format", "pdf")
        })

    async def _generate_receipt(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Gera recibo"""
        recipient = params.get("recipient", {})
        amount = params.get("amount", 0)
        description = params.get("description", "")

        receipt_number = f"REC-{datetime.now().strftime('%Y%m%d')}-{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6].upper()}"

        content = f"""
RECIBO Nº {receipt_number}

Recebi de: {recipient.get('name', '')}
CPF/CNPJ: {recipient.get('document', '')}

A importância de: R$ {amount:,.2f}
({self._number_to_words(amount)})

Referente a: {description}

Data: {datetime.now().strftime('%d/%m/%Y')}
Local: {params.get('location', 'São Paulo, SP')}

_______________________________
Assinatura
        """

        return SkillResult.ok({
            "receipt_number": receipt_number,
            "content": content.strip(),
            "amount": amount,
            "recipient": recipient.get('name'),
            "generated_at": datetime.now().isoformat()
        })

    async def _generate_letter(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Gera carta/comunicado"""
        letter_type = params.get("type", "comunicado")
        recipient = params.get("recipient", {})
        subject = params.get("subject", "")
        body = params.get("body", "")

        header = f"{params.get('sender_name', 'Administração')}\n"
        header += f"{params.get('sender_address', '')}\n"
        header += f"{datetime.now().strftime('%d de %B de %Y')}\n\n"

        greeting = f"Prezado(a) Sr(a). {recipient.get('name', '')},"

        if letter_type == "cobranca":
            greeting = f"Prezado(a) Condômino(a) - Unidade {recipient.get('unit', '')},"
        elif letter_type == "convocacao":
            greeting = "Prezados Condôminos,"

        closing = params.get("closing", "Atenciosamente,")
        signature = params.get("signature", "A Administração")

        full_letter = f"{header}{greeting}\n\n{subject}\n\n{body}\n\n{closing}\n{signature}"

        return await self._generate_document(context, {
            "title": subject or f"Carta - {letter_type.title()}",
            "content": full_letter,
            "format": params.get("format", "pdf")
        })

    async def _convert_format(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Converte entre formatos"""
        source = params.get("source")
        target_format = DocumentFormat(params.get("target_format", "pdf"))

        if not source:
            return SkillResult.fail("'source' é obrigatório")

        source_ext = source.split('.')[-1].lower() if '.' in source else ""
        target_file = source.rsplit('.', 1)[0] + f".{target_format.value}"

        return SkillResult.ok({
            "source": source,
            "target": target_file,
            "source_format": source_ext,
            "target_format": target_format.value,
            "converted_at": datetime.now().isoformat()
        })

    def _number_to_words(self, number: float) -> str:
        """Converte número para extenso (simplificado)"""
        units = ["", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
        teens = ["dez", "onze", "doze", "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
        tens = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
        hundreds = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]

        inteiro = int(number)
        centavos = int((number - inteiro) * 100)

        if inteiro == 0:
            return "zero reais"

        if inteiro == 100:
            result = "cem"
        elif inteiro < 10:
            result = units[inteiro]
        elif inteiro < 20:
            result = teens[inteiro - 10]
        elif inteiro < 100:
            d, u = divmod(inteiro, 10)
            result = tens[d] + (" e " + units[u] if u else "")
        elif inteiro < 1000:
            c, resto = divmod(inteiro, 100)
            if resto == 0:
                result = hundreds[c] if c > 1 else "cem"
            else:
                result = hundreds[c] + " e " + self._number_to_words(resto).replace(" reais", "")
        else:
            result = f"{inteiro:,}".replace(",", ".")

        result += " reais" if inteiro != 1 else " real"

        if centavos:
            result += f" e {centavos} centavos"

        return result


# ============================================================
# Template Skill
# ============================================================

@dataclass
class Template:
    """Template de documento"""
    name: str
    content: str
    variables: List[str]
    format: str = "text"
    category: str = "general"
    version: str = "1.0"


@skill(
    name="template",
    version="1.0.0",
    category=SkillCategory.DOCUMENT,
    description="Gerenciamento e renderização de templates",
    tags=["template", "render", "document"]
)
class TemplateSkill(BaseSkill):
    """
    Skill para gerenciamento de templates.
    Suporta variáveis, condicionais e loops simples.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._templates: Dict[str, Template] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """Carrega templates padrão"""
        defaults = {
            "comunicado_geral": Template(
                name="comunicado_geral",
                content="""COMUNICADO

{{titulo}}

Prezados Moradores,

{{corpo}}

{{#se_urgente}}
ATENÇÃO: Este comunicado é URGENTE e requer sua atenção imediata.
{{/se_urgente}}

Atenciosamente,
{{assinatura}}
{{data}}""",
                variables=["titulo", "corpo", "se_urgente", "assinatura", "data"],
                category="comunicacao"
            ),
            "aviso_cobranca": Template(
                name="aviso_cobranca",
                content="""AVISO DE COBRANÇA

Unidade: {{unidade}}
Morador: {{nome}}

Informamos que identificamos pendências financeiras em seu cadastro:

{{#parcelas}}
- Competência: {{competencia}} - Valor: R$ {{valor}}
{{/parcelas}}

Total em aberto: R$ {{total}}

Solicitamos a regularização até {{data_limite}}.

Dúvidas: {{contato}}""",
                variables=["unidade", "nome", "parcelas", "total", "data_limite", "contato"],
                category="financeiro"
            ),
            "convocacao_assembleia": Template(
                name="convocacao_assembleia",
                content="""EDITAL DE CONVOCAÇÃO
ASSEMBLEIA GERAL {{tipo}}

Ficam os senhores condôminos convocados para participar da Assembleia Geral {{tipo}} do {{condominio}}, a realizar-se:

Data: {{data}}
Horário: {{hora}} (1ª convocação) / {{hora_segunda}} (2ª convocação)
Local: {{local}}

PAUTA:
{{#itens_pauta}}
{{numero}}. {{descricao}}
{{/itens_pauta}}

{{cidade}}, {{data_convocacao}}

{{sindico}}
Síndico""",
                variables=["tipo", "condominio", "data", "hora", "hora_segunda", "local", "itens_pauta", "cidade", "data_convocacao", "sindico"],
                category="assembleia"
            ),
            "autorizacao_entrada": Template(
                name="autorizacao_entrada",
                content="""AUTORIZAÇÃO DE ENTRADA

Eu, {{nome_autorizador}}, morador(a) da unidade {{unidade}}, autorizo a entrada de:

Nome: {{nome_visitante}}
RG: {{rg_visitante}}
Motivo: {{motivo}}

Data: {{data}}
Período: {{periodo}}

{{#observacoes}}
Observações: {{observacoes}}
{{/observacoes}}

___________________________
Assinatura do Morador""",
                variables=["nome_autorizador", "unidade", "nome_visitante", "rg_visitante", "motivo", "data", "periodo", "observacoes"],
                category="acesso"
            )
        }

        self._templates.update(defaults)

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa ação de template"""
        action = params.get("action", "render")

        if action == "render":
            return await self._render_template(context, params)
        elif action == "list":
            return await self._list_templates(context, params)
        elif action == "get":
            return await self._get_template(context, params)
        elif action == "create":
            return await self._create_template(context, params)
        elif action == "validate":
            return await self._validate_variables(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _render_template(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Renderiza template com variáveis"""
        template_name = params.get("template_name")
        template_content = params.get("template_content")
        variables = params.get("variables", {})

        if not template_name and not template_content:
            return SkillResult.fail("'template_name' ou 'template_content' é obrigatório")

        # Obter template
        if template_name:
            template = self._templates.get(template_name)
            if not template:
                return SkillResult.fail(f"Template não encontrado: {template_name}")
            content = template.content
        else:
            content = template_content

        # Substituir variáveis simples
        rendered = content
        for key, value in variables.items():
            # Variável simples: {{var}}
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value) if value is not None else "")

        # Processar condicionais: {{#condicao}}...{{/condicao}}
        rendered = self._process_conditionals(rendered, variables)

        # Processar loops: {{#lista}}...{{/lista}}
        rendered = self._process_loops(rendered, variables)

        # Limpar variáveis não preenchidas
        rendered = re.sub(r'\{\{[^}]+\}\}', '', rendered)

        # Limpar linhas vazias extras
        rendered = re.sub(r'\n{3,}', '\n\n', rendered)

        return SkillResult.ok({
            "rendered": rendered.strip(),
            "template_name": template_name,
            "variables_used": list(variables.keys()),
            "length": len(rendered)
        })

    def _process_conditionals(self, content: str, variables: Dict) -> str:
        """Processa blocos condicionais"""
        pattern = r'\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}'

        def replace_conditional(match):
            var_name = match.group(1)
            block_content = match.group(2)

            # Verificar se a variável existe e é truthy
            value = variables.get(var_name)
            if value and value not in [False, 0, "", [], {}, None]:
                return block_content
            return ""

        return re.sub(pattern, replace_conditional, content, flags=re.DOTALL)

    def _process_loops(self, content: str, variables: Dict) -> str:
        """Processa loops"""
        pattern = r'\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}'

        def replace_loop(match):
            var_name = match.group(1)
            block_content = match.group(2)

            value = variables.get(var_name)

            # Se for uma lista, iterar
            if isinstance(value, list):
                results = []
                for item in value:
                    item_content = block_content
                    if isinstance(item, dict):
                        for k, v in item.items():
                            item_content = item_content.replace(f"{{{{{k}}}}}", str(v))
                    else:
                        item_content = item_content.replace("{{.}}", str(item))
                    results.append(item_content.strip())
                return "\n".join(results)

            # Se for boolean/truthy, já foi processado como condicional
            return match.group(0)

        return re.sub(pattern, replace_loop, content, flags=re.DOTALL)

    async def _list_templates(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Lista templates disponíveis"""
        category = params.get("category")

        templates = []
        for name, template in self._templates.items():
            if not category or template.category == category:
                templates.append({
                    "name": name,
                    "category": template.category,
                    "variables": template.variables,
                    "version": template.version
                })

        return SkillResult.ok({
            "templates": templates,
            "count": len(templates),
            "categories": list(set(t.category for t in self._templates.values()))
        })

    async def _get_template(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém template específico"""
        template_name = params.get("template_name")

        if not template_name:
            return SkillResult.fail("'template_name' é obrigatório")

        template = self._templates.get(template_name)
        if not template:
            return SkillResult.fail(f"Template não encontrado: {template_name}")

        return SkillResult.ok({
            "name": template.name,
            "content": template.content,
            "variables": template.variables,
            "category": template.category,
            "version": template.version
        })

    async def _create_template(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Cria novo template"""
        name = params.get("name")
        content = params.get("content")

        if not name or not content:
            return SkillResult.fail("'name' e 'content' são obrigatórios")

        # Extrair variáveis do conteúdo
        variables = list(set(re.findall(r'\{\{#?/?(\w+)\}\}', content)))

        template = Template(
            name=name,
            content=content,
            variables=variables,
            category=params.get("category", "custom"),
            version=params.get("version", "1.0")
        )

        self._templates[name] = template

        return SkillResult.ok({
            "name": name,
            "variables": variables,
            "category": template.category,
            "created": True
        })

    async def _validate_variables(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Valida se todas as variáveis foram fornecidas"""
        template_name = params.get("template_name")
        variables = params.get("variables", {})

        if not template_name:
            return SkillResult.fail("'template_name' é obrigatório")

        template = self._templates.get(template_name)
        if not template:
            return SkillResult.fail(f"Template não encontrado: {template_name}")

        missing = []
        provided = []
        extra = []

        for var in template.variables:
            if var in variables:
                provided.append(var)
            else:
                missing.append(var)

        for var in variables:
            if var not in template.variables:
                extra.append(var)

        return SkillResult.ok({
            "valid": len(missing) == 0,
            "required_variables": template.variables,
            "provided_variables": provided,
            "missing_variables": missing,
            "extra_variables": extra
        })


# Função de inicialização
def register_document_skills():
    """Registra todas as skills de documento"""
    pass
