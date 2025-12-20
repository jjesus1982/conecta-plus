"""
Conecta Plus - LLM Client
Cliente unificado para modelos de linguagem (Claude, GPT, Local)

Suporta:
- Claude (Anthropic) - Preferido
- GPT-4 (OpenAI) - Fallback
- Modelos locais via Ollama
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Provedores de LLM suportados"""
    CLAUDE = "claude"
    OPENAI = "openai"
    OLLAMA = "ollama"


@dataclass
class LLMMessage:
    """Mensagem para o LLM"""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Resposta do LLM"""
    content: str
    model: str
    provider: LLMProvider
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Tool:
    """Definição de ferramenta para function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema


class BaseLLMClient(ABC):
    """Interface base para clientes LLM"""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> str:
        """Gera resposta simples"""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """Chat com histórico de mensagens"""
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Tool],
        **kwargs
    ) -> LLMResponse:
        """Gera com suporte a function calling"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream de resposta"""
        pass


class ClaudeClient(BaseLLMClient):
    """
    Cliente para Claude (Anthropic).
    Modelo preferido para o sistema.
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> str:
        """Gera resposta simples"""
        try:
            client = await self._get_client()

            response = await client.messages.create(
                model=kwargs.get("model", self.model),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Erro ao gerar com Claude: {e}")
            raise

    async def chat(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """Chat com histórico"""
        try:
            client = await self._get_client()

            # Separar system prompt
            system_content = ""
            chat_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_content = msg.content
                else:
                    chat_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            response = await client.messages.create(
                model=kwargs.get("model", self.model),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                system=system_content,
                messages=chat_messages
            )

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                provider=LLMProvider.CLAUDE,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                finish_reason=response.stop_reason
            )

        except Exception as e:
            logger.error(f"Erro no chat com Claude: {e}")
            raise

    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Tool],
        **kwargs
    ) -> LLMResponse:
        """Gera com function calling"""
        try:
            client = await self._get_client()

            # Separar system prompt
            system_content = ""
            chat_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_content = msg.content
                else:
                    chat_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            # Converter tools para formato Anthropic
            anthropic_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters
                }
                for tool in tools
            ]

            response = await client.messages.create(
                model=kwargs.get("model", self.model),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                system=system_content,
                messages=chat_messages,
                tools=anthropic_tools
            )

            # Extrair tool calls
            tool_calls = []
            content = ""

            for block in response.content:
                if block.type == "text":
                    content = block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input
                    })

            return LLMResponse(
                content=content,
                model=response.model,
                provider=LLMProvider.CLAUDE,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                finish_reason=response.stop_reason,
                tool_calls=tool_calls
            )

        except Exception as e:
            logger.error(f"Erro com tools no Claude: {e}")
            raise

    async def stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream de resposta"""
        try:
            client = await self._get_client()

            system_content = ""
            chat_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_content = msg.content
                else:
                    chat_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            async with client.messages.stream(
                model=kwargs.get("model", self.model),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                system=system_content,
                messages=chat_messages
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Erro no stream Claude: {e}")
            raise


class OpenAIClient(BaseLLMClient):
    """
    Cliente para OpenAI GPT.
    Usado como fallback ou para tarefas específicas.
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4o",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> str:
        """Gera resposta simples"""
        try:
            client = await self._get_client()

            response = await client.chat.completions.create(
                model=kwargs.get("model", self.model),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Erro ao gerar com OpenAI: {e}")
            raise

    async def chat(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """Chat com histórico"""
        try:
            client = await self._get_client()

            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            response = await client.chat.completions.create(
                model=kwargs.get("model", self.model),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                messages=openai_messages
            )

            choice = response.choices[0]

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider=LLMProvider.OPENAI,
                usage={
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                },
                finish_reason=choice.finish_reason
            )

        except Exception as e:
            logger.error(f"Erro no chat com OpenAI: {e}")
            raise

    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Tool],
        **kwargs
    ) -> LLMResponse:
        """Gera com function calling"""
        try:
            client = await self._get_client()

            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            # Converter tools para formato OpenAI
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                }
                for tool in tools
            ]

            response = await client.chat.completions.create(
                model=kwargs.get("model", self.model),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                messages=openai_messages,
                tools=openai_tools,
                tool_choice="auto"
            )

            choice = response.choices[0]

            # Extrair tool calls
            tool_calls = []
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    })

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider=LLMProvider.OPENAI,
                usage={
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                },
                finish_reason=choice.finish_reason,
                tool_calls=tool_calls
            )

        except Exception as e:
            logger.error(f"Erro com tools no OpenAI: {e}")
            raise

    async def stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream de resposta"""
        try:
            client = await self._get_client()

            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            stream = await client.chat.completions.create(
                model=kwargs.get("model", self.model),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                messages=openai_messages,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Erro no stream OpenAI: {e}")
            raise


class OllamaClient(BaseLLMClient):
    """
    Cliente para modelos locais via Ollama.
    Útil para desenvolvimento e privacidade.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> str:
        """Gera resposta simples"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": kwargs.get("model", self.model),
                        "prompt": f"{system_prompt}\n\nUsuário: {user_prompt}",
                        "stream": False,
                        "options": {
                            "num_predict": kwargs.get("max_tokens", self.max_tokens),
                            "temperature": kwargs.get("temperature", self.temperature)
                        }
                    }
                ) as response:
                    result = await response.json()
                    return result.get("response", "")

        except Exception as e:
            logger.error(f"Erro ao gerar com Ollama: {e}")
            raise

    async def chat(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """Chat com histórico"""
        try:
            import aiohttp

            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": kwargs.get("model", self.model),
                        "messages": ollama_messages,
                        "stream": False,
                        "options": {
                            "num_predict": kwargs.get("max_tokens", self.max_tokens),
                            "temperature": kwargs.get("temperature", self.temperature)
                        }
                    }
                ) as response:
                    result = await response.json()

                    return LLMResponse(
                        content=result.get("message", {}).get("content", ""),
                        model=self.model,
                        provider=LLMProvider.OLLAMA,
                        usage={
                            "input_tokens": result.get("prompt_eval_count", 0),
                            "output_tokens": result.get("eval_count", 0)
                        }
                    )

        except Exception as e:
            logger.error(f"Erro no chat com Ollama: {e}")
            raise

    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Tool],
        **kwargs
    ) -> LLMResponse:
        """Ollama tem suporte limitado a tools - simular via prompt"""
        # Adicionar descrição das tools ao prompt
        tools_description = "Ferramentas disponíveis:\n"
        for tool in tools:
            tools_description += f"- {tool.name}: {tool.description}\n"
            tools_description += f"  Parâmetros: {json.dumps(tool.parameters, indent=2)}\n"

        tools_description += "\nPara usar uma ferramenta, responda no formato JSON: {\"tool\": \"nome\", \"arguments\": {...}}"

        # Adicionar ao system message
        enhanced_messages = []
        for msg in messages:
            if msg.role == "system":
                enhanced_messages.append(LLMMessage(
                    role="system",
                    content=f"{msg.content}\n\n{tools_description}"
                ))
            else:
                enhanced_messages.append(msg)

        response = await self.chat(enhanced_messages, **kwargs)

        # Tentar extrair tool call do JSON
        try:
            content = response.content
            if "{" in content and "}" in content:
                json_start = content.index("{")
                json_end = content.rindex("}") + 1
                tool_json = json.loads(content[json_start:json_end])

                if "tool" in tool_json:
                    response.tool_calls = [{
                        "id": "ollama_tool_call",
                        "name": tool_json["tool"],
                        "arguments": tool_json.get("arguments", {})
                    }]
        except:
            pass

        return response

    async def stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream de resposta"""
        try:
            import aiohttp

            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": kwargs.get("model", self.model),
                        "messages": ollama_messages,
                        "stream": True,
                        "options": {
                            "num_predict": kwargs.get("max_tokens", self.max_tokens),
                            "temperature": kwargs.get("temperature", self.temperature)
                        }
                    }
                ) as response:
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    yield data["message"]["content"]
                            except:
                                pass

        except Exception as e:
            logger.error(f"Erro no stream Ollama: {e}")
            raise


class UnifiedLLMClient:
    """
    Cliente unificado que gerencia múltiplos provedores.
    Suporta fallback automático e load balancing.
    """

    def __init__(
        self,
        primary_provider: LLMProvider = LLMProvider.CLAUDE,
        fallback_providers: List[LLMProvider] = None
    ):
        self.primary = primary_provider
        self.fallbacks = fallback_providers or [LLMProvider.OPENAI]
        self._clients: Dict[LLMProvider, BaseLLMClient] = {}
        self._init_clients()

    def _init_clients(self):
        """Inicializa clientes disponíveis"""
        # Claude
        if os.getenv("ANTHROPIC_API_KEY"):
            self._clients[LLMProvider.CLAUDE] = ClaudeClient()
            logger.info("Cliente Claude inicializado")

        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            self._clients[LLMProvider.OPENAI] = OpenAIClient()
            logger.info("Cliente OpenAI inicializado")

        # Ollama (verificar se está rodando)
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                self._clients[LLMProvider.OLLAMA] = OllamaClient()
                logger.info("Cliente Ollama inicializado")
        except:
            pass

    def _get_client(self, provider: LLMProvider = None) -> BaseLLMClient:
        """Obtém cliente para provider"""
        provider = provider or self.primary

        if provider in self._clients:
            return self._clients[provider]

        # Tentar fallbacks
        for fb in self.fallbacks:
            if fb in self._clients:
                logger.warning(f"Usando fallback {fb.value} ao invés de {provider.value}")
                return self._clients[fb]

        raise ValueError("Nenhum provedor LLM disponível")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        provider: LLMProvider = None,
        **kwargs
    ) -> str:
        """Gera resposta com fallback automático"""
        providers_to_try = [provider or self.primary] + self.fallbacks

        last_error = None
        for prov in providers_to_try:
            if prov not in self._clients:
                continue

            try:
                return await self._clients[prov].generate(system_prompt, user_prompt, **kwargs)
            except Exception as e:
                logger.warning(f"Erro com {prov.value}: {e}")
                last_error = e

        raise last_error or ValueError("Nenhum provedor disponível")

    async def chat(
        self,
        messages: List[LLMMessage],
        provider: LLMProvider = None,
        **kwargs
    ) -> LLMResponse:
        """Chat com fallback automático"""
        providers_to_try = [provider or self.primary] + self.fallbacks

        last_error = None
        for prov in providers_to_try:
            if prov not in self._clients:
                continue

            try:
                return await self._clients[prov].chat(messages, **kwargs)
            except Exception as e:
                logger.warning(f"Erro com {prov.value}: {e}")
                last_error = e

        raise last_error or ValueError("Nenhum provedor disponível")

    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Tool],
        provider: LLMProvider = None,
        **kwargs
    ) -> LLMResponse:
        """Gera com tools e fallback"""
        providers_to_try = [provider or self.primary] + self.fallbacks

        last_error = None
        for prov in providers_to_try:
            if prov not in self._clients:
                continue

            try:
                return await self._clients[prov].generate_with_tools(messages, tools, **kwargs)
            except Exception as e:
                logger.warning(f"Erro com {prov.value}: {e}")
                last_error = e

        raise last_error or ValueError("Nenhum provedor disponível")

    async def stream(
        self,
        messages: List[LLMMessage],
        provider: LLMProvider = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream com o provider especificado"""
        client = self._get_client(provider)
        async for chunk in client.stream(messages, **kwargs):
            yield chunk


# Factory function
def create_llm_client(
    provider: str = "auto",
    **kwargs
) -> BaseLLMClient:
    """
    Cria cliente LLM baseado no provider.

    Args:
        provider: "claude", "openai", "ollama", ou "auto"
        **kwargs: Argumentos específicos do provider

    Returns:
        Cliente LLM configurado
    """
    if provider == "auto":
        return UnifiedLLMClient(**kwargs)
    elif provider == "claude":
        return ClaudeClient(**kwargs)
    elif provider == "openai":
        return OpenAIClient(**kwargs)
    elif provider == "ollama":
        return OllamaClient(**kwargs)
    else:
        raise ValueError(f"Provider '{provider}' não suportado")
