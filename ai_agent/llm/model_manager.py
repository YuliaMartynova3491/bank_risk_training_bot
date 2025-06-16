"""
Менеджер для работы с различными LLM провайдерами.
"""

import logging
from typing import Optional, Any
from config.settings import settings

class LLMManager:
    """Менеджер для инициализации и работы с LLM."""
    
    def __init__(self):
        self.llm = None
        self.provider = settings.llm_provider
    
    async def initialize(self) -> Optional[Any]:
        """Инициализация LLM в зависимости от провайдера."""
        try:
            if self.provider == "openai":
                self.llm = await self._init_openai()
            elif self.provider == "lm_studio":
                self.llm = await self._init_lm_studio()
            elif self.provider == "ollama":
                self.llm = await self._init_ollama()
            elif self.provider == "azure":
                self.llm = await self._init_azure_openai()
            else:
                logging.warning(f"⚠️ Неизвестный провайдер LLM: {self.provider}")
                return None
            
            logging.info(f"✅ LLM инициализирован: {self.provider}")
            return self.llm
            
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации LLM: {e}")
            return None
    
    async def _init_openai(self):
        """Инициализация OpenAI."""
        try:
            from langchain_openai import ChatOpenAI
            
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY не установлен")
            
            return ChatOpenAI(
                model=settings.openai_model,
                temperature=settings.openai_temperature,
                max_tokens=settings.openai_max_tokens,
                api_key=settings.openai_api_key
            )
        except ImportError:
            logging.error("❌ langchain-openai не установлен. Установите: pip install langchain-openai")
            return None
    
    async def _init_lm_studio(self):
        """Инициализация LM Studio с оптимизацией для Qwen2.5."""
        try:
            from langchain_openai import ChatOpenAI
            
            # Специальные настройки для Qwen2.5-14B-Instruct
            return ChatOpenAI(
                model=settings.lm_studio_model,
                temperature=0.3,  # Низкая температура для точных ответов
                max_tokens=4096,  # Qwen2.5 поддерживает длинные контексты
                base_url=settings.lm_studio_url,
                api_key=settings.lm_studio_api_key,
                # Дополнительные параметры для стабильности
                request_timeout=120,  # Увеличенный таймаут для 14B модели
                max_retries=2
            )
        except ImportError:
            logging.error("❌ langchain-openai не установлен для LM Studio")
            return None
    
    async def _init_ollama(self):
        """Инициализация Ollama."""
        try:
            from langchain_community.llms import Ollama
            
            return Ollama(
                model=settings.ollama_model,
                base_url=settings.ollama_url,
                temperature=settings.ollama_temperature
            )
        except ImportError:
            logging.error("❌ Ollama не доступен")
            return None
    
    async def _init_azure_openai(self):
        """Инициализация Azure OpenAI."""
        try:
            from langchain_openai import AzureChatOpenAI
            
            if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
                raise ValueError("Azure OpenAI настройки не установлены")
            
            return AzureChatOpenAI(
                deployment_name=settings.azure_openai_deployment_name,
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version
            )
        except ImportError:
            logging.error("❌ Azure OpenAI не доступен")
            return None
    
    def get_llm(self):
        """Получение инициализированного LLM."""
        return self.llm