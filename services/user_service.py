"""
Сервис для управления пользователями AI-агента.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from database.database import db_manager
from database.models import User, LearningSession, UserProgress, ChatMessage, SystemNotification
from config.settings import DifficultyConfig


class UserService:
    """Сервис для работы с пользователями."""
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID."""
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                return result.scalar_one_or_none()
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения пользователя {telegram_id}: {e}")
            return None
    
    async def create_or_update_user(
        self, 
        telegram_id: int, 
        username: str = None,
        first_name: str = None, 
        last_name: str = None
    ) -> User:
        """Создание или обновление пользователя."""
        try:
            async with db_manager.get_session() as session:
                # Поиск существующего пользователя
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
                        last_name=last_name,
                        current_difficulty_level=1,
                        preferred_language="ru",
                        notifications_enabled=True
                    )
                    session.add(user)
                
                await session.commit()
                await session.refresh(user)
                
                logging.info(f"👤 Пользователь {telegram_id} {'обновлен' if result.scalar_one_or_none() else 'создан'}")
                return user
                
        except Exception as e:
            logging.error(f"❌ Ошибка создания/обновления пользователя: {e}")
            raise
    
    async def update_difficulty_level(self, telegram_id: int, difficulty_level: int) -> bool:
        """Обновление уровня сложности пользователя."""
        try:
            if difficulty_level < 1 or difficulty_level > 5:
                logging.warning(f"⚠️ Некорректный уровень сложности: {difficulty_level}")
                return False
            
            async with db_manager.get_session() as session:
                result = await session.execute(
                    update(User)
                    .where(User.telegram_id == telegram_id)
                    .values(
                        current_difficulty_level=difficulty_level,
                        updated_at=datetime.utcnow()
                    )
                )
                
                await session.commit()
                
                if result.rowcount > 0:
                    logging.info(f"🎯 Уровень сложности пользователя {telegram_id} изменен на {difficulty_level}")
                    return True
                else:
                    logging.warning(f"⚠️ Пользователь {telegram_id} не найден")
                    return False
                    
        except Exception as e:
            logging.error(f"❌ Ошибка обновления уровня сложности: {e}")
            return False
    
    async def update_notification_settings(self, telegram_id: int, enabled: bool) -> bool:
        """Обновление настроек уведомлений."""
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    update(User)
                    .where(User.telegram_id == telegram_id)
                    .values(
                        notifications_enabled=enabled,
                        updated_at=datetime.utcnow()
                    )
                )
                
                await session.commit()
                
                if result.rowcount > 0:
                    status = "включены" if enabled else "отключены"
                    logging.info(f"🔔 Уведомления для пользователя {telegram_id} {status}")
                    return True
                else:
                    return False
                    
        except Exception as e:
            logging.error(f"❌ Ошибка обновления настроек уведомлений: {e}")
            return False
    
    async def update_last_activity(self, telegram_id: int) -> bool:
        """Обновление времени последней активности."""
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    update(User)
                    .where(User.telegram_id == telegram_id)
                    .values(last_activity=datetime.utcnow())
                )
                
                await session.commit()
                return result.rowcount > 0
                
        except Exception as e:
            logging.error(f"❌ Ошибка обновления активности: {e}")
            return False
    
    async def get_user_sessions(self, user_id: int, limit: int = 10) -> List[LearningSession]:
        """Получение сессий обучения пользователя."""
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(LearningSession)
                    .where(LearningSession.user_id == user_id)
                    .order_by(LearningSession.started_at.desc())
                    .limit(limit)
                    .options(
                        selectinload(LearningSession.current_topic),
                        selectinload(LearningSession.current_lesson)
                    )
                )
                return result.scalars().all()
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения сессий пользователя: {e}")
            return []
    
    async def get_active_session(self, user_id: int) -> Optional[LearningSession]:
        """Получение активной сессии обучения."""
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(LearningSession)
                    .where(
                        LearningSession.user_id == user_id,
                        LearningSession.session_state == "active"
                    )
                    .order_by(LearningSession.started_at.desc())
                )
                return result.scalar_one_or_none()
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения активной сессии: {e}")
            return None
    
    async def create_learning_session(self, user_id: int, topic_id: int = None) -> LearningSession:
        """Создание новой сессии обучения."""
        try:
            async with db_manager.get_session() as session:
                # Завершение предыдущих активных сессий
                await session.execute(
                    update(LearningSession)
                    .where(
                        LearningSession.user_id == user_id,
                        LearningSession.session_state == "active"
                    )
                    .values(session_state="paused")
                )
                
                # Создание новой сессии
                new_session = LearningSession(
                    user_id=user_id,
                    current_topic_id=topic_id,
                    session_state="active",
                    agent_state={}
                )
                
                session.add(new_session)
                await session.commit()
                await session.refresh(new_session)
                
                logging.info(f"📚 Создана новая сессия обучения для пользователя {user_id}")
                return new_session
                
        except Exception as e:
            logging.error(f"❌ Ошибка создания сессии обучения: {e}")
            raise
    
    async def update_session_state(self, session_id: int, state: str, agent_state: Dict = None) -> bool:
        """Обновление состояния сессии обучения."""
        try:
            async with db_manager.get_session() as session:
                update_values = {
                    "session_state": state,
                    "last_activity_at": datetime.utcnow()
                }
                
                if agent_state is not None:
                    update_values["agent_state"] = agent_state
                
                if state == "completed":
                    update_values["completed_at"] = datetime.utcnow()
                
                result = await session.execute(
                    update(LearningSession)
                    .where(LearningSession.id == session_id)
                    .values(**update_values)
                )
                
                await session.commit()
                return result.rowcount > 0
                
        except Exception as e:
            logging.error(f"❌ Ошибка обновления состояния сессии: {e}")
            return False
    
    async def get_user_chat_history(self, user_id: int, limit: int = 20) -> List[ChatMessage]:
        """Получение истории чата пользователя с AI."""
        try:
            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.user_id == user_id)
                    .order_by(ChatMessage.created_at.desc())
                    .limit(limit)
                )
                return result.scalars().all()
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения истории чата: {e}")
            return []
    
    async def save_chat_message(
        self, 
        user_id: int, 
        message_type: str, 
        content: str,
        context_used: List[Dict] = None,
        confidence_score: float = None
    ) -> ChatMessage:
        """Сохранение сообщения в истории чата."""
        try:
            async with db_manager.get_session() as session:
                chat_message = ChatMessage(
                    user_id=user_id,
                    message_type=message_type,
                    content=content,
                    context_used=context_used or [],
                    confidence_score=confidence_score,
                    metadata={"timestamp": datetime.utcnow().isoformat()}
                )
                
                session.add(chat_message)
                await session.commit()
                await session.refresh(chat_message)
                
                return chat_message
                
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения сообщения: {e}")
            raise
    
    async def get_users_for_notifications(self, inactive_hours: int = 8) -> List[User]:
        """Получение пользователей для отправки напоминаний."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=inactive_hours)
            
            async with db_manager.get_session() as session:
                result = await session.execute(
                    select(User)
                    .where(
                        User.notifications_enabled == True,
                        User.last_activity < cutoff_time
                    )
                    .join(LearningSession, User.id == LearningSession.user_id)
                    .where(LearningSession.session_state.in_(["active", "paused"]))
                )
                return result.scalars().unique().all()
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения пользователей для уведомлений: {e}")
            return []
    
    async def create_notification(
        self, 
        user_id: int, 
        notification_type: str,
        title: str, 
        message: str,
        scheduled_for: datetime = None
    ) -> SystemNotification:
        """Создание системного уведомления."""
        try:
            async with db_manager.get_session() as session:
                notification = SystemNotification(
                    user_id=user_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    scheduled_for=scheduled_for or datetime.utcnow()
                )
                
                session.add(notification)
                await session.commit()
                await session.refresh(notification)
                
                return notification
                
        except Exception as e:
            logging.error(f"❌ Ошибка создания уведомления: {e}")
            raise
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя."""
        try:
            async with db_manager.get_session() as session:
                # Общее количество сессий
                sessions_result = await session.execute(
                    select(func.count(LearningSession.id))
                    .where(LearningSession.user_id == user_id)
                )
                total_sessions = sessions_result.scalar() or 0
                
                # Завершенные сессии
                completed_sessions_result = await session.execute(
                    select(func.count(LearningSession.id))
                    .where(
                        LearningSession.user_id == user_id,
                        LearningSession.session_state == "completed"
                    )
                )
                completed_sessions = completed_sessions_result.scalar() or 0
                
                # Время обучения (сумма времени сессий)
                time_result = await session.execute(
                    select(func.sum(
                        func.extract('epoch', LearningSession.last_activity_at - LearningSession.started_at) / 3600
                    ))
                    .where(LearningSession.user_id == user_id)
                )
                study_hours = time_result.scalar() or 0
                
                # Количество сообщений в чате
                messages_result = await session.execute(
                    select(func.count(ChatMessage.id))
                    .where(ChatMessage.user_id == user_id)
                )
                chat_messages = messages_result.scalar() or 0
                
                return {
                    "total_sessions": total_sessions,
                    "completed_sessions": completed_sessions,
                    "completion_rate": (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0,
                    "study_hours": round(float(study_hours), 2),
                    "chat_messages": chat_messages
                }
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения статистики пользователя: {e}")
            return {}
    
    async def delete_user_data(self, telegram_id: int) -> bool:
        """Удаление всех данных пользователя (GDPR)."""
        try:
            async with db_manager.get_session() as session:
                # Получение пользователя
                user_result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Удаление связанных данных будет выполнено автоматически
                # благодаря cascade="all, delete-orphan" в моделях
                await session.delete(user)
                await session.commit()
                
                logging.info(f"🗑️ Данные пользователя {telegram_id} удалены")
                return True
                
        except Exception as e:
            logging.error(f"❌ Ошибка удаления данных пользователя: {e}")
            return False