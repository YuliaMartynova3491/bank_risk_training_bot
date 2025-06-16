"""
Основные настройки проекта AI-агента для обучения банковским рискам.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Основные настройки
    debug: bool = Field(default=False, env="DEBUG")
    testing: bool = Field(default=False, env="TESTING")
    secret_key: str = Field(env="SECRET_KEY")
    
    # Telegram Bot
    telegram_bot_token: str = Field(env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(default=None, env="TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: Optional[str] = Field(default=None, env="TELEGRAM_WEBHOOK_SECRET")
    
    # База данных
    database_url: str = Field(env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # LLM настройки
    llm_provider: str = Field(default="lm_studio", env="LLM_PROVIDER")
    
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=2048, env="OPENAI_MAX_TOKENS")
    
    # LM Studio (для локальных моделей)
    lm_studio_url: str = Field(default="http://localhost:1234/v1", env="LM_STUDIO_URL")
    lm_studio_model: str = Field(default="llama-2-7b-chat", env="LM_STUDIO_MODEL")
    lm_studio_api_key: str = Field(default="lm-studio", env="LM_STUDIO_API_KEY")
    
    # Ollama
    ollama_url: str = Field(default="http://localhost:11434", env="OLLAMA_URL")
    ollama_model: str = Field(default="llama2", env="OLLAMA_MODEL")
    ollama_temperature: float = Field(default=0.7, env="OLLAMA_TEMPERATURE")
    
    # Azure OpenAI
    azure_openai_api_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", env="AZURE_OPENAI_API_VERSION")
    azure_openai_deployment_name: Optional[str] = Field(default=None, env="AZURE_OPENAI_DEPLOYMENT_NAME")
    
    # RAG настройки
    vector_store_path: str = Field(default="./ai_agent/rag/data/vectorstore", env="VECTOR_STORE_PATH")
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    
    # Настройки обучения
    min_lesson_score: int = Field(default=80, env="MIN_LESSON_SCORE")
    reminder_interval_hours: int = Field(default=8, env="REMINDER_INTERVAL_HOURS")
    max_difficulty_level: int = Field(default=5, env="MAX_DIFFICULTY_LEVEL")
    questions_per_lesson: int = Field(default=5, env="QUESTIONS_PER_LESSON")  # Увеличено до 5
    
    # Логирование
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # Аналитика
    analytics_enabled: bool = Field(default=True, env="ANALYTICS_ENABLED")
    analytics_port: int = Field(default=8000, env="ANALYTICS_PORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Глобальный экземпляр настроек
settings = Settings()


# Константы стикеров
class Stickers:
    """Стикеры для различных ситуаций в боте."""
    
    # Приветствие (случайный выбор)
    WELCOME = [
        "CAACAgIAAxkBAAEOd6RoIsd8Z1Gz2JyvVPrxpwRugDF89wAC8EAAAgMdyUh6q-4BL3FQLzYE",
        "CAACAgIAAxkBAAEOd6xoIshSMujqTxf8Od_p7PLDGn7sUwACWToAAqePcUmYZialrHxKnTYE"
    ]
    
    # Правильные ответы
    FIRST_CORRECT = "CAACAgIAAxkBAAEOd6hoIsgIXelJD9h0RgVTxLtEz_ZgMgACky4AAgFM6UhFC9JlyfY5rzYE"
    SUBSEQUENT_CORRECT = "CAACAgIAAxkBAAEOd6poIsggr-5-2bwnZt7t_2pJP9HWwACyCoAAkj3cUng5lb0xkBC6DYE"
    
    # Успешное прохождение
    LESSON_COMPLETED = "CAACAgIAAxkBAAEOd65oIsiE9oHP2Cxsg9wkj1LXFi0L1AACR18AAuphSUoma5l9yrkFmjYE"
    TOPIC_COMPLETED = "CAACAgIAAxkBAAEOd7JoIspvfu0_4EUpFnUcpq6OUjVMEAACRFkAAnnRSUru1p89ZmyntTYE"
    
    # Неправильные ответы
    FIRST_INCORRECT = "CAACAgIAAxkBAAEOd6JoIsc8ZgvKw1T8QqL2CNIpNtLUzAAC_0gAApjKwEh4Jj7i8mL2AjYE"
    SUBSEQUENT_INCORRECT = "CAACAgIAAxkBAAEOd6ZoIsfmsGJP3o0KdTMiriW8U9sVvwACHEUAAvkKiEjOqMQN3AH2PTYE"
    
    # Недостаточный результат
    INSUFFICIENT_SCORE = "CAACAgIAAxkBAAEOd7BoIsok2pkQSuPXBxRVf26hil-35gACEywAArBkcEno5QGUqynBvzYE"


# Команды для запуска бота
START_COMMANDS = [
    "start", "старт", "Start", "Старт", "начать", "Начать", 
    "начнем", "Начнем", "go", "Go", "поехали", "Поехали",
    "запуск", "Запуск", "run", "Run", "давай", "Давай"
]


# Конфигурация трудности обучения
class DifficultyConfig:
    """Конфигурация уровней сложности."""
    
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4
    MASTER = 5
    
    LEVEL_NAMES = {
        1: "Начинающий",
        2: "Базовый", 
        3: "Продвинутый",
        4: "Эксперт",
        5: "Мастер"
    }


# Шаблоны сообщений
class MessageTemplates:
    """Шаблоны сообщений для бота."""
    
    WELCOME = """
🏦 Добро пожаловать в AI-агент обучения банковским рискам!

Я помогу вам изучить методики управления рисками непрерывности деятельности банка.

🎯 Особенности обучения:
• Адаптивные вопросы по вашему уровню
• Интерактивные сценарии катастроф
• Персональный прогресс
• Помощь AI-ассистента 24/7

Выберите действие в меню ниже 👇
    """
    
    HELP = """
📚 Инструкция по работе с ботом:

1️⃣ Начните обучение - пройдите адаптивный курс
2️⃣ Задайте вопрос - получите помощь от AI
3️⃣ Проверьте прогресс - узнайте свои достижения

💡 Советы:
• Отвечайте честно на вопросы
• Используйте функцию "Задать вопрос" для получения дополнительной информации
• Обучение сохраняется автоматически
• Получайте напоминания о продолжении курса

❓ Есть вопросы? Просто напишите мне!
    """