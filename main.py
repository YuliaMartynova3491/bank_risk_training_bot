"""
Главный файл для запуска AI-агента обучения банковским рискам.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Глобальная переменная для приложения
application = None

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения."""
    logger.info(f"👋 Получен сигнал {signum}, завершение работы...")
    if application:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(stop_application())
            loop.close()
        except Exception as e:
            logger.error(f"❌ Ошибка остановки: {e}")
    sys.exit(0)

async def stop_application():
    """Остановка приложения."""
    global application
    try:
        logger.info("🛑 Завершение работы AI-агента...")
        
        if application:
            if hasattr(application, 'updater') and application.updater and application.updater.running:
                await application.updater.stop()
                logger.info("✅ Updater остановлен")
            
            await application.stop()
            logger.info("✅ Application остановлено")
            
            await application.shutdown()
            logger.info("✅ Telegram приложение остановлено")
        
        logger.info("✅ AI-агент корректно завершил работу")
        
    except Exception as e:
        logger.error(f"❌ Ошибка остановки: {e}")

async def main():
    """Главная функция запуска."""
    global application
    
    try:
        logger.info("🚀 Запуск AI-агента для обучения банковским рискам...")
        
        # Настройка обработчиков сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Импорт компонентов
        from telegram.ext import Application
        
        # Загрузка настроек
        from config.settings import get_settings
        settings = get_settings()
        
        # Инициализация базы данных (если доступна)
        try:
            from database.database import initialize_database
            logger.info("🔄 Инициализация базы данных...")
            await initialize_database()
            logger.info("✅ База данных инициализирована")
        except ImportError:
            logger.warning("⚠️ База данных недоступна")
        
        # Создание Telegram приложения
        application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .build()
        )
        
        # Инициализация компонентов
        try:
            from ai_agent.llm.model_manager import ModelManager
            model_manager = ModelManager(settings)
            llm = await model_manager.get_llm()
            logger.info(f"✅ LLM инициализирован: {settings.llm_provider}")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка инициализации LLM: {e}")
            llm = None
        
        # Инициализация базы знаний RAG
        try:
            logger.info("�� Инициализация базы знаний RAG...")
            from ai_agent.rag.knowledge_base import KnowledgeBase
            knowledge_base = KnowledgeBase(
                model_name=settings.embedding_model,
                persist_directory=settings.vector_store_path
            )
            await knowledge_base.initialize()
            logger.info("✅ База знаний инициализирована")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка инициализации RAG: {e}")
            knowledge_base = None
        
        # Инициализация LangGraph агента
        if llm and knowledge_base:
            try:
                from ai_agent.graph.learning_graph import LearningGraph
                learning_graph = LearningGraph(
                    knowledge_base=knowledge_base,
                    llm=llm
                )
                await learning_graph.initialize()
                logger.info("✅ LangGraph агент инициализирован")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка инициализации LearningGraph: {e}")
                learning_graph = None
        else:
            learning_graph = None
        
        # Сохранение компонентов в bot_data
        application.bot_data['learning_graph'] = learning_graph
        application.bot_data['knowledge_base'] = knowledge_base
        
        try:
            from services.user_service import UserService
            application.bot_data['user_service'] = UserService()
        except ImportError:
            logger.warning("⚠️ UserService недоступен")
        
        # Регистрация обработчиков
        from bot.handlers.base_handler import register_base_handlers
        register_base_handlers(application)
        logger.info("✅ Базовые обработчики зарегистрированы")
        
        try:
            from bot.handlers.lesson_handler import register_lesson_handlers
            register_lesson_handlers(application)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка регистрации lesson_handlers: {e}")
        
        try:
            from bot.handlers.chat_handler import register_chat_handlers
            register_chat_handlers(application)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка регистрации chat_handlers: {e}")
        
        try:
            from bot.handlers.progress_handler import register_progress_handlers
            register_progress_handlers(application)
            logger.info("✅ Обработчики прогресса зарегистрированы")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка регистрации progress_handlers: {e}")
        
        logger.info("✅ Все обработчики зарегистрированы")
        
        # Запуск бота
        logger.info("🤖 AI-агент запущен в режиме polling...")
        logger.info(f"🔧 Режим отладки: {settings.debug}")
        logger.info("📱 Бот готов к работе!")
        
        await application.run_polling(
            allowed_updates=['message', 'callback_query'],
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал прерывания...")
        await stop_application()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        await stop_application()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
