"""
Base agent class providing shared LLM invocation, logging, and retry logic.
Supports: Groq (free), Cerebras (free), Anthropic, OpenAI, Ollama.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings
from models.schemas import AgentType, AgentStatus, ResearchSession

logger = logging.getLogger(__name__)

_FAST_ROLES  = {AgentType.PLANNER, AgentType.RESEARCHER}
_SMART_ROLES = {AgentType.ANALYST, AgentType.WRITER}


def _resolve_model(agent_type: AgentType, model_override: Optional[str]) -> Optional[str]:
    if model_override and model_override != "auto":
        return model_override
    p = settings.LLM_PROVIDER
    use_smart = agent_type in _SMART_ROLES
    if p == "groq":
        return settings.GROQ_SMART_MODEL if use_smart else settings.GROQ_FAST_MODEL
    if p == "cerebras":
        return settings.CEREBRAS_SMART_MODEL if use_smart else settings.CEREBRAS_FAST_MODEL
    if p == "anthropic":
        return settings.ANTHROPIC_SMART_MODEL if use_smart else settings.ANTHROPIC_FAST_MODEL
    if p == "openai":
        return settings.OPENAI_MODEL
    return None


def get_llm(agent_type: AgentType, model_override: Optional[str] = None):
    """
    Factory returning a LangChain chat model for the configured provider.

    FREE options (no credit card needed):
      Groq     https://console.groq.com      — set LLM_PROVIDER=groq
      Cerebras https://cloud.cerebras.ai     — set LLM_PROVIDER=cerebras
      Ollama   (local)                       — set LLM_PROVIDER=ollama
    """
    provider = settings.LLM_PROVIDER
    model = _resolve_model(agent_type, model_override)

    if provider == "groq":
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set. Free key at https://console.groq.com")
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError("pip install langchain-groq")
        return ChatGroq(
            model=model,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0.3,
            max_tokens=4096,
        )

    if provider == "cerebras":
        if not settings.CEREBRAS_API_KEY:
            raise ValueError("CEREBRAS_API_KEY not set. Free key at https://cloud.cerebras.ai")
        try:
            from langchain_cerebras import ChatCerebras
        except ImportError:
            raise ImportError("pip install langchain-cerebras")
        return ChatCerebras(
            model=model,
            cerebras_api_key=settings.CEREBRAS_API_KEY,
            temperature=0.3,
            max_tokens=4096,
        )

    if provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set.")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            temperature=0.3,
            max_tokens=4096,
        )

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
            max_tokens=4096,
        )

    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=model or "llama3.1",
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.3,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")


class BaseAgent(ABC):
    def __init__(self, agent_type: AgentType, model_override: Optional[str] = None):
        self.agent_type = agent_type
        self.llm = get_llm(agent_type, model_override)
        self.logger = logging.getLogger(f"agent.{agent_type.value}")

    def log(self, session: ResearchSession, status: AgentStatus,
            message: str, details: Optional[Dict[str, Any]] = None):
        session.add_log(self.agent_type, status, message, details)
        self.logger.info(f"[{self.agent_type.value.upper()}] {message}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def invoke_llm(self, prompt: str, system: Optional[str] = None) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        response = await self.llm.ainvoke(messages)
        return response.content

    def parse_json_response(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        for fence in ("```json", "```"):
            if text.startswith(fence):
                text = text[len(fence):]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            import re
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass
            raise ValueError(f"Could not parse JSON: {text[:200]}")

    @abstractmethod
    async def run(self, session: "ResearchSession", **kwargs) -> Any:
        pass
