"""
Conecta Plus - Analysis Skills
Habilidades analíticas para agentes

Skills:
- SentimentAnalysisSkill: Análise de sentimento
- EntityExtractionSkill: Extração de entidades
- IntentClassificationSkill: Classificação de intenções
- SummarizationSkill: Sumarização de textos
- TranslationSkill: Tradução
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .base_skill import (
    BaseSkill, SkillContext, SkillResult, SkillMetadata,
    SkillCategory, skill
)

logger = logging.getLogger(__name__)


class Sentiment(Enum):
    """Níveis de sentimento"""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


class Intent(Enum):
    """Intenções comuns"""
    GREETING = "greeting"
    FAREWELL = "farewell"
    QUESTION = "question"
    REQUEST = "request"
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    CONFIRMATION = "confirmation"
    NEGATION = "negation"
    EMERGENCY = "emergency"
    INFORMATION = "information"
    UNKNOWN = "unknown"


@dataclass
class ExtractedEntity:
    """Entidade extraída"""
    text: str
    entity_type: str
    start: int
    end: int
    confidence: float
    normalized_value: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@skill(
    name="sentiment_analysis",
    version="1.0.0",
    category=SkillCategory.ANALYSIS,
    description="Analisa sentimento em textos",
    tags=["sentiment", "analysis", "nlp"]
)
class SentimentAnalysisSkill(BaseSkill):
    """
    Skill para análise de sentimento.

    Detecta:
    - Polaridade (positivo/negativo/neutro)
    - Intensidade
    - Emoções específicas
    - Aspectos (o que causou o sentimento)
    """

    # Palavras indicativas de sentimento
    POSITIVE_WORDS = {
        "obrigado", "obrigada", "excelente", "ótimo", "ótima", "perfeito",
        "perfeita", "maravilhoso", "maravilhosa", "adorei", "amei", "parabéns",
        "bom", "boa", "legal", "bacana", "show", "top", "incrível", "fantástico",
        "satisfeito", "satisfeita", "feliz", "contente", "agradeço", "grato", "grata"
    }

    NEGATIVE_WORDS = {
        "péssimo", "péssima", "horrível", "terrível", "ruim", "absurdo",
        "inaceitável", "decepcionado", "decepcionada", "frustrado", "frustrada",
        "irritado", "irritada", "raiva", "ódio", "problema", "reclamação",
        "insatisfeito", "insatisfeita", "triste", "chateado", "chateada",
        "demora", "atraso", "quebrado", "estragado", "não funciona"
    }

    INTENSIFIERS = {"muito", "demais", "extremamente", "super", "totalmente", "completamente"}
    NEGATORS = {"não", "nunca", "jamais", "nem", "nenhum", "nenhuma"}

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="sentiment_analysis",
            version="1.0.0",
            category=SkillCategory.ANALYSIS,
            description="Analisa sentimento em textos",
            tags=["sentiment", "nlp"],
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """
        Analisa sentimento do texto.

        Params:
            text: Texto para análise
            detailed: Se deve retornar análise detalhada
            use_llm: Se deve usar LLM para análise mais precisa
        """
        text = params.get("text", "")
        detailed = params.get("detailed", False)
        use_llm = params.get("use_llm", False)

        if not text:
            return SkillResult.fail("Texto vazio")

        # Análise baseada em regras
        sentiment, score, details = self._analyze_rules_based(text)

        # Se LLM disponível e solicitado, refinar análise
        if use_llm and context.config.get("llm_client"):
            llm_result = await self._analyze_with_llm(text, context)
            if llm_result:
                # Combinar resultados
                sentiment = llm_result.get("sentiment", sentiment)
                score = (score + llm_result.get("score", score)) / 2

        result_data = {
            "sentiment": sentiment.name,
            "score": score,
            "confidence": details.get("confidence", 0.7),
        }

        if detailed:
            result_data["details"] = details

        return SkillResult.ok(result_data)

    def _analyze_rules_based(self, text: str) -> Tuple[Sentiment, float, Dict]:
        """Análise baseada em regras"""
        text_lower = text.lower()
        words = text_lower.split()

        positive_count = 0
        negative_count = 0
        has_intensifier = False
        has_negation = False
        found_words = {"positive": [], "negative": []}

        for i, word in enumerate(words):
            # Verificar negação
            if word in self.NEGATORS:
                has_negation = True

            # Verificar intensificadores
            if word in self.INTENSIFIERS:
                has_intensifier = True

            # Contar palavras
            if word in self.POSITIVE_WORDS:
                # Se precedido por negação, conta como negativo
                if has_negation:
                    negative_count += 1
                    found_words["negative"].append(word)
                else:
                    positive_count += 1
                    found_words["positive"].append(word)
                has_negation = False

            elif word in self.NEGATIVE_WORDS:
                if has_negation:
                    positive_count += 1
                    found_words["positive"].append(word)
                else:
                    negative_count += 1
                    found_words["negative"].append(word)
                has_negation = False

        # Calcular score
        total = positive_count + negative_count
        if total == 0:
            sentiment = Sentiment.NEUTRAL
            score = 0.0
        else:
            raw_score = (positive_count - negative_count) / total

            # Aplicar intensificador
            if has_intensifier:
                raw_score *= 1.5

            # Normalizar para -1 a 1
            score = max(-1, min(1, raw_score))

            # Determinar categoria
            if score > 0.5:
                sentiment = Sentiment.VERY_POSITIVE
            elif score > 0.1:
                sentiment = Sentiment.POSITIVE
            elif score < -0.5:
                sentiment = Sentiment.VERY_NEGATIVE
            elif score < -0.1:
                sentiment = Sentiment.NEGATIVE
            else:
                sentiment = Sentiment.NEUTRAL

        details = {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "positive_words": found_words["positive"],
            "negative_words": found_words["negative"],
            "has_intensifier": has_intensifier,
            "confidence": min(0.9, 0.5 + (total * 0.1)),
        }

        return sentiment, score, details

    async def _analyze_with_llm(self, text: str, context: SkillContext) -> Optional[Dict]:
        """Análise usando LLM"""
        # Implementação dependeria do LLM client
        return None


@skill(
    name="entity_extraction",
    version="1.0.0",
    category=SkillCategory.ANALYSIS,
    description="Extrai entidades de textos",
    tags=["ner", "entities", "extraction", "nlp"]
)
class EntityExtractionSkill(BaseSkill):
    """
    Skill para extração de entidades nomeadas.

    Extrai:
    - Pessoas
    - Unidades/apartamentos
    - Veículos (placas)
    - Datas e horários
    - Valores monetários
    - Telefones
    - CPF/CNPJ
    - Endereços
    """

    # Padrões regex para entidades
    PATTERNS = {
        "phone": r'(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}',
        "cpf": r'\d{3}\.?\d{3}\.?\d{3}[-.]?\d{2}',
        "cnpj": r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}[-.]?\d{2}',
        "plate": r'[A-Z]{3}[-\s]?\d{4}|[A-Z]{3}\d[A-Z]\d{2}',
        "email": r'[\w\.-]+@[\w\.-]+\.\w+',
        "date": r'\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',
        "time": r'\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?',
        "money": r'R\$\s*[\d.,]+|\d+(?:,\d{2})?\s*reais',
        "unit": r'(?:apt?o?\.?|unidade|apartamento|bloco|torre)\s*\d+[A-Z]?',
        "cep": r'\d{5}[-]?\d{3}',
    }

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="entity_extraction",
            version="1.0.0",
            category=SkillCategory.ANALYSIS,
            description="Extrai entidades de textos",
            tags=["ner", "entities", "nlp"],
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """
        Extrai entidades do texto.

        Params:
            text: Texto para análise
            entity_types: Lista de tipos a extrair (opcional)
            normalize: Se deve normalizar valores
        """
        text = params.get("text", "")
        entity_types = params.get("entity_types")
        normalize = params.get("normalize", True)

        if not text:
            return SkillResult.fail("Texto vazio")

        entities = []

        # Aplicar cada padrão
        for entity_type, pattern in self.PATTERNS.items():
            if entity_types and entity_type not in entity_types:
                continue

            for match in re.finditer(pattern, text, re.IGNORECASE):
                entity = ExtractedEntity(
                    text=match.group(),
                    entity_type=entity_type,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9,
                )

                if normalize:
                    entity.normalized_value = self._normalize_entity(
                        entity.text, entity_type
                    )

                entities.append(entity)

        return SkillResult.ok({
            "entities": [
                {
                    "text": e.text,
                    "type": e.entity_type,
                    "start": e.start,
                    "end": e.end,
                    "normalized": e.normalized_value,
                    "confidence": e.confidence,
                }
                for e in entities
            ],
            "entity_count": len(entities),
            "types_found": list(set(e.entity_type for e in entities)),
        })

    def _normalize_entity(self, text: str, entity_type: str) -> str:
        """Normaliza valor da entidade"""
        text = text.strip()

        if entity_type == "cpf":
            # Remover pontuação
            return re.sub(r'[^\d]', '', text)

        elif entity_type == "cnpj":
            return re.sub(r'[^\d]', '', text)

        elif entity_type == "phone":
            # Manter apenas dígitos
            digits = re.sub(r'[^\d]', '', text)
            if len(digits) == 11:
                return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
            return digits

        elif entity_type == "plate":
            # Formato padrão
            text = text.upper().replace('-', '').replace(' ', '')
            return text

        elif entity_type == "money":
            # Converter para float
            value = re.sub(r'[^\d,.]', '', text)
            value = value.replace(',', '.')
            return value

        return text


@skill(
    name="intent_classification",
    version="1.0.0",
    category=SkillCategory.ANALYSIS,
    description="Classifica intenções em mensagens",
    tags=["intent", "classification", "nlp"]
)
class IntentClassificationSkill(BaseSkill):
    """
    Skill para classificação de intenções.

    Detecta:
    - Perguntas
    - Pedidos/solicitações
    - Reclamações
    - Saudações
    - Emergências
    """

    # Indicadores de intenção
    INTENT_INDICATORS = {
        Intent.GREETING: ["olá", "oi", "bom dia", "boa tarde", "boa noite", "e aí", "opa"],
        Intent.FAREWELL: ["tchau", "até logo", "até mais", "adeus", "valeu", "falou"],
        Intent.QUESTION: ["?", "como", "quando", "onde", "qual", "quem", "por que", "o que"],
        Intent.REQUEST: ["preciso", "quero", "gostaria", "pode", "poderia", "por favor", "solicito"],
        Intent.COMPLAINT: ["reclamação", "problema", "não funciona", "péssimo", "insatisfeito", "absurdo"],
        Intent.EMERGENCY: ["urgente", "emergência", "socorro", "perigo", "incêndio", "invasão", "ajuda"],
        Intent.CONFIRMATION: ["sim", "correto", "isso", "exato", "confirmo", "ok", "certo"],
        Intent.NEGATION: ["não", "negativo", "errado", "incorreto", "negar"],
        Intent.FEEDBACK: ["sugestão", "elogio", "feedback", "opinião", "avaliar"],
    }

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="intent_classification",
            version="1.0.0",
            category=SkillCategory.ANALYSIS,
            description="Classifica intenções",
            tags=["intent", "classification"],
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """
        Classifica intenção da mensagem.

        Params:
            text: Texto para classificar
            return_all: Retornar todas as intenções detectadas
        """
        text = params.get("text", "")
        return_all = params.get("return_all", False)

        if not text:
            return SkillResult.fail("Texto vazio")

        text_lower = text.lower()
        detected = []

        for intent, indicators in self.INTENT_INDICATORS.items():
            score = sum(1 for ind in indicators if ind in text_lower)
            if score > 0:
                confidence = min(0.95, 0.5 + (score * 0.15))
                detected.append({
                    "intent": intent.value,
                    "confidence": confidence,
                    "indicators_found": score,
                })

        # Ordenar por confiança
        detected.sort(key=lambda x: x["confidence"], reverse=True)

        if not detected:
            detected.append({
                "intent": Intent.UNKNOWN.value,
                "confidence": 0.5,
            })

        result = {
            "primary_intent": detected[0]["intent"],
            "confidence": detected[0]["confidence"],
        }

        if return_all:
            result["all_intents"] = detected

        return SkillResult.ok(result)


@skill(
    name="summarization",
    version="1.0.0",
    category=SkillCategory.ANALYSIS,
    description="Sumariza textos longos",
    tags=["summarization", "nlp", "text"]
)
class SummarizationSkill(BaseSkill):
    """
    Skill para sumarização de textos.

    Modos:
    - Extractive: Extrai sentenças mais importantes
    - Abstractive: Gera novo resumo (requer LLM)
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="summarization",
            version="1.0.0",
            category=SkillCategory.ANALYSIS,
            description="Sumariza textos",
            tags=["summarization", "text"],
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """
        Sumariza texto.

        Params:
            text: Texto para sumarizar
            max_sentences: Máximo de sentenças no resumo
            max_length: Tamanho máximo do resumo
            mode: extractive ou abstractive
        """
        text = params.get("text", "")
        max_sentences = params.get("max_sentences", 3)
        max_length = params.get("max_length", 500)
        mode = params.get("mode", "extractive")

        if not text:
            return SkillResult.fail("Texto vazio")

        if mode == "extractive":
            summary = self._extractive_summary(text, max_sentences, max_length)
        else:
            # Abstractive requer LLM
            summary = await self._abstractive_summary(text, max_length, context)

        return SkillResult.ok({
            "summary": summary,
            "original_length": len(text),
            "summary_length": len(summary),
            "compression_ratio": len(summary) / len(text) if text else 0,
            "mode": mode,
        })

    def _extractive_summary(self, text: str, max_sentences: int, max_length: int) -> str:
        """Sumarização extractiva"""
        # Dividir em sentenças
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= max_sentences:
            return text

        # Pontuar sentenças (heurística simples)
        scored = []
        for i, sentence in enumerate(sentences):
            score = 0
            # Posição: primeiras e últimas sentenças são mais importantes
            if i < 2 or i >= len(sentences) - 2:
                score += 2
            # Tamanho: sentenças médias são melhores
            if 50 < len(sentence) < 200:
                score += 1
            # Palavras-chave
            keywords = ["importante", "conclusão", "resultado", "portanto", "assim"]
            score += sum(1 for kw in keywords if kw in sentence.lower())

            scored.append((sentence, score, i))

        # Selecionar melhores
        scored.sort(key=lambda x: x[1], reverse=True)
        selected = sorted(scored[:max_sentences], key=lambda x: x[2])

        summary = ". ".join(s[0] for s in selected) + "."

        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."

        return summary

    async def _abstractive_summary(self, text: str, max_length: int, context: SkillContext) -> str:
        """Sumarização abstractiva usando LLM"""
        # Fallback para extractive se LLM não disponível
        return self._extractive_summary(text, 3, max_length)


@skill(
    name="translation",
    version="1.0.0",
    category=SkillCategory.ANALYSIS,
    description="Traduz textos entre idiomas",
    tags=["translation", "language", "nlp"]
)
class TranslationSkill(BaseSkill):
    """
    Skill para tradução de textos.

    Suporta:
    - Detecção automática de idioma
    - Tradução bidirecional
    - Preservação de formatação
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="translation",
            version="1.0.0",
            category=SkillCategory.ANALYSIS,
            description="Traduz textos",
            tags=["translation", "language"],
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """
        Traduz texto.

        Params:
            text: Texto para traduzir
            source_lang: Idioma de origem (auto para detectar)
            target_lang: Idioma de destino
        """
        text = params.get("text", "")
        source_lang = params.get("source_lang", "auto")
        target_lang = params.get("target_lang", "pt")

        if not text:
            return SkillResult.fail("Texto vazio")

        # Detectar idioma se necessário
        if source_lang == "auto":
            source_lang = self._detect_language(text)

        # Traduzir (implementação simplificada - em produção usaria API)
        translated = await self._translate(text, source_lang, target_lang)

        return SkillResult.ok({
            "translated_text": translated,
            "source_language": source_lang,
            "target_language": target_lang,
            "original_length": len(text),
            "translated_length": len(translated),
        })

    def _detect_language(self, text: str) -> str:
        """Detecta idioma do texto"""
        text_lower = text.lower()

        # Heurística simples baseada em palavras comuns
        pt_words = ["de", "que", "não", "para", "com", "uma", "os", "no", "se"]
        en_words = ["the", "is", "are", "was", "have", "with", "this", "that"]
        es_words = ["que", "de", "no", "es", "la", "el", "en", "los", "del"]

        pt_count = sum(1 for w in pt_words if f" {w} " in f" {text_lower} ")
        en_count = sum(1 for w in en_words if f" {w} " in f" {text_lower} ")
        es_count = sum(1 for w in es_words if f" {w} " in f" {text_lower} ")

        if pt_count >= en_count and pt_count >= es_count:
            return "pt"
        elif en_count >= es_count:
            return "en"
        else:
            return "es"

    async def _translate(self, text: str, source: str, target: str) -> str:
        """Traduz texto (placeholder - usar API real)"""
        # Em produção, integraria com Google Translate, DeepL, etc.
        return f"[{target}] {text}"
