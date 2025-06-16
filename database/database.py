"""
Конфигурация и инициализация базы данных.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from config.settings import settings
from database.models import Base


class DatabaseManager:
    """Менеджер для работы с базой данных."""
    
    def __init__(self):
        # Создание асинхронного движка для SQLite
        # SQLite не поддерживает pool_size и max_overflow
        if "sqlite" in settings.database_url:
            self.engine = create_async_engine(
                settings.database_url,
                echo=settings.database_echo,
                # Для SQLite убираем настройки пула
            )
        else:
            # Для PostgreSQL и других БД
            self.engine = create_async_engine(
                settings.database_url,
                echo=settings.database_echo,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=10,
                max_overflow=20
            )
        
        # Создание фабрики сессий
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True
        )
    
    async def create_tables(self):
        """Создание всех таблиц в базе данных."""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logging.info("✅ Таблицы базы данных созданы")
        except Exception as e:
            logging.error(f"❌ Ошибка при создании таблиц: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Получение сессии базы данных с автоматическим закрытием."""
        async with self.SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()


async def init_database():
    """Инициализация базы данных."""
    try:
        logging.info("🔄 Инициализация базы данных...")
        await db_manager.create_tables()
        logging.info("✅ База данных инициализирована")
    except Exception as e:
        logging.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise


async def get_user_by_telegram_id(telegram_id: int):
    """Получение пользователя по Telegram ID."""
    from database.models import User
    from sqlalchemy import select
    
    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def create_or_update_user(telegram_id: int, username: str = None, 
                               first_name: str = None, last_name: str = None):
    """Создание или обновление пользователя."""
    from database.models import User
    from sqlalchemy import select
    from datetime import datetime
    
    async with db_manager.get_session() as session:
        # Попытка найти существующего пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Обновление существующего пользователя
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.last_activity = datetime.utcnow()
        else:
            # Создание нового пользователя
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
        
        await session.commit()
        await session.refresh(user)
        return user
