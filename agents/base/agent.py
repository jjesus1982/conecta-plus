"""
Base Agent - Classe base para todos os agentes do Conecta Plus
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI


class BaseAgent(ABC):
    """Classe base abstrata para agentes de IA"""

    def __init__(
        self,
        name: str,
        description: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.name = name
        self.description = description
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(f"agent.{name}")
        self.conversation_history: List[Dict] = []
        self.tools: List[Dict] = []
        self.mcps: List[str] = []

        # Inicializa LLM baseado no modelo
        if "claude" in model:
            self.llm = ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            self.llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Prompt do sistema específico do agente"""
        pass

    @abstractmethod
    def get_tools(self) -> List[Dict]:
        """Retorna lista de ferramentas disponíveis para o agente"""
        pass

    @abstractmethod
    def get_mcps(self) -> List[str]:
        """Retorna lista de MCPs utilizados pelo agente"""
        pass

    async def process_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Processa uma mensagem e retorna resposta"""

        self.logger.info(f"Processando mensagem: {message[:100]}...")

        # Adiciona contexto se fornecido
        enhanced_message = message
        if context:
            enhanced_message = f"Contexto: {json.dumps(context, ensure_ascii=False)}\n\nMensagem: {message}"

        # Prepara mensagens
        messages = [
            SystemMessage(content=self.system_prompt),
            *[
                HumanMessage(content=h["content"]) if h["role"] == "user"
                else AIMessage(content=h["content"])
                for h in self.conversation_history[-10:]  # Últimas 10 mensagens
            ],
            HumanMessage(content=enhanced_message),
        ]

        try:
            # Invoca LLM
            response = await self.llm.ainvoke(messages)

            # Registra na história
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response.content})

            return {
                "success": True,
                "response": response.content,
                "agent": self.name,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Erro ao processar mensagem: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name,
                "timestamp": datetime.now().isoformat(),
            }

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Executa uma ferramenta/MCP"""

        self.logger.info(f"Executando ferramenta: {tool_name}")

        # Aqui seria a integração real com MCPs
        # Por ora, retorna estrutura padrão
        return {
            "success": True,
            "tool": tool_name,
            "result": None,
            "timestamp": datetime.now().isoformat(),
        }

    def clear_history(self):
        """Limpa histórico de conversação"""
        self.conversation_history = []

    def get_status(self) -> Dict[str, Any]:
        """Retorna status do agente"""
        return {
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "tools_count": len(self.get_tools()),
            "mcps": self.get_mcps(),
            "history_length": len(self.conversation_history),
            "status": "active",
        }


class AgentRegistry:
    """Registro central de agentes"""

    _instance = None
    _agents: Dict[str, BaseAgent] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, agent: BaseAgent):
        """Registra um agente"""
        self._agents[agent.name] = agent

    def get(self, name: str) -> Optional[BaseAgent]:
        """Obtém agente pelo nome"""
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        """Lista nomes dos agentes registrados"""
        return list(self._agents.keys())

    def get_all_status(self) -> List[Dict]:
        """Retorna status de todos os agentes"""
        return [agent.get_status() for agent in self._agents.values()]
