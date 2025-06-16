"""
Главный файл AI-агента для обучения банковским рискам.
Запуск: python main.py
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

import coloredlogs
from telegram.ext import Application

from config.settings import settings
from bot.handlers.start_handler import register_start_handlers
from bot.handlers.menu_handler import register_menu_handlers
from bot.handlers.lesson_handler import register_lesson_handlers
from bot.handlers.chat_handler import register_chat_handlers


class BankRiskTrainingBot:
    """Основной класс AI-агента для обучения банковским рискам."""
    
    def __init__(self):
        self.application: Application = None
        
    async def initialize(self):
        """Инициализация всех компонентов бота."""
        try:
            # Настройка логирования
            coloredlogs.install(
                level=settings.log_level,
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            logging.info("🚀 Запуск AI-агента для обучения банковским рискам...")
            
            # Создание директорий
            self._create_directories()
            
            # Инициализация базы данных
            await self._init_database()
            logging.info("✅ База данных инициализирована")
            
            # Создание Telegram приложения
            self.application = (
                Application.builder()
                .token(settings.telegram_bot_token)
                .build()
            )
            
            # Регистрация обработчиков
            await self._register_handlers()
            logging.info("✅ Обработчики зарегистрированы")
            
            # Инициализация AI-агента
            await self._initialize_ai_agent()
            logging.info("✅ AI-агент инициализирован")
            
        except Exception as e:
            logging.error(f"❌ Ошибка при инициализации: {e}")
            sys.exit(1)
    
    def _create_directories(self):
        """Создание необходимых директорий."""
        directories = [
            "ai_agent/rag/data/vectorstore",
            "data/stickers",
            "data/templates", 
            "data/exports"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def _init_database(self):
        """Инициализация базы данных."""
        try:
            from database.database import init_database
            await init_database()
        except ImportError as e:
            logging.warning(f"⚠️ Не удалось импортировать модуль базы данных: {e}")
            logging.info("📝 Пропускаем инициализацию БД - будет использоваться упрощенное хранение")
    
    async def _register_handlers(self):
        """Регистрация всех обработчиков команд и сообщений."""
        try:
            from bot.handlers.start_handler import register_start_handlers
            from bot.handlers.menu_handler import register_menu_handlers
            
            register_start_handlers(self.application)
            register_menu_handlers(self.application)
            logging.info("✅ Базовые обработчики зарегистрированы")
            
            # Попытка зарегистрировать дополнительные обработчики
            try:
                from bot.handlers.lesson_handler import register_lesson_handlers
                from bot.handlers.chat_handler import register_chat_handlers
                
                register_lesson_handlers(self.application)
                register_chat_handlers(self.application)
                logging.info("✅ Все обработчики зарегистрированы")
                
            except ImportError as e:
                logging.warning(f"⚠️ Не удалось импортировать дополнительные обработчики: {e}")
                
        except ImportError as e:
            logging.warning(f"⚠️ Не удалось импортировать некоторые обработчики: {e}")
            # Регистрируем только базовые обработчики
            try:
                from bot.handlers.start_handler import register_start_handlers
                register_start_handlers(self.application)
            except ImportError:
                logging.error("❌ Не удалось импортировать даже базовые обработчики")
                raise
    
    async def _initialize_ai_agent(self):
        """Инициализация AI-агента на базе LangGraph."""
        try:
            from ai_agent.graph.learning_graph import LearningGraph
            from ai_agent.rag.knowledge_base import KnowledgeBase
            from ai_agent.llm.model_manager import LLMManager
            
            # Инициализация LLM
            llm_manager = LLMManager()
            llm = await llm_manager.initialize()
            
            # Инициализация базы знаний RAG
            knowledge_base = KnowledgeBase()
            await knowledge_base.initialize()
            
            # Инициализация графа обучения с LLM
            learning_graph = LearningGraph(knowledge_base, llm)
            await learning_graph.initialize()
            
            # Сохранение в глобальном состоянии
            self.application.bot_data['knowledge_base'] = knowledge_base
            self.application.bot_data['learning_graph'] = learning_graph
            self.application.bot_data['llm'] = llm
            
        except ImportError as e:
            logging.warning(f"⚠️ Не удалось импортировать AI компоненты: {e}")
            logging.info("📝 AI функции будут ограничены")
        except Exception as e:
            logging.warning(f"⚠️ AI компоненты частично недоступны: {e}")
            logging.info("📝 Бот будет работать в базовом режиме")
    
    async def start_polling(self):
        """Запуск бота в режиме polling."""
        try:
            logging.info("🤖 AI-агент запущен в режиме polling...")
            logging.info(f"🔧 Режим отладки: {settings.debug}")
            logging.info("📱 Бот готов к работе!")
            
            # Запуск polling
            await self.application.run_polling(
                allowed_updates=["message", "callback_query", "inline_query"],
                drop_pending_updates=True
            )
            
        except Exception as e:
            logging.error(f"❌ Ошибка при запуске polling: {e}")
            await self.shutdown()
    
    async def start_webhook(self):
        """Запуск бота в режиме webhook."""
        if not settings.telegram_webhook_url:
            raise ValueError("Для webhook режима необходимо указать TELEGRAM_WEBHOOK_URL")
        
        try:
            logging.info("🌐 Бот запущен в режиме webhook...")
            logging.info(f"🔗 Webhook URL: {settings.telegram_webhook_url}")
            
            # Установка webhook
            await self.application.bot.set_webhook(
                url=settings.telegram_webhook_url,
                secret_token=settings.telegram_webhook_secret
            )
            
            # Запуск webhook сервера
            await self.application.run_webhook(
                listen="0.0.0.0",
                port=8443,
                webhook_url=settings.telegram_webhook_url,
                secret_token=settings.telegram_webhook_secret
            )
            
        except Exception as e:
            logging.error(f"❌ Ошибка при запуске webhook: {e}")
            await self.shutdown()
    
    async def shutdown(self):
        """Корректное завершение работы бота."""
        logging.info("🛑 Завершение работы AI-агента...")
        
        try:
            # Остановка приложения
            if self.application:
                await self.application.shutdown()
                logging.info("✅ Telegram приложение остановлено")
            
            logging.info("✅ AI-агент корректно завершил работу")
            
        except Exception as e:
            logging.error(f"❌ Ошибка при завершении работы: {e}")


async def main():
    """Главная функция запуска."""
    # Проверка наличия .env файла
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("📝 Создайте файл .env на основе .env.example")
        print("💡 Минимальный .env должен содержать:")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token")
        print("   DATABASE_URL=sqlite+aiosqlite:///./bank_training.db")
        sys.exit(1)
    
    # Создание экземпляра бота
    bot = BankRiskTrainingBot()
    
    try:
        # Инициализация
        await bot.initialize()
        
        # Запуск в зависимости от конфигурации
        if hasattr(settings, 'telegram_webhook_url') and settings.telegram_webhook_url:
            await bot.start_webhook()
        else:
            await bot.start_polling()
            
    except KeyboardInterrupt:
        logging.info("👋 Получен сигнал завершения...")
    except Exception as e:
        logging.error(f"❌ Критическая ошибка: {e}")
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    # Проверка версии Python
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)
    
    # Запуск приложения
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Работа завершена пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)