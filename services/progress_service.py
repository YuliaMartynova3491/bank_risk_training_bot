"""
Сервис для управления прогрессом обучения пользователей.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

try:
    from sqlalchemy import select, func, and_, desc, Integer
    from sqlalchemy.orm import selectinload
    from database.database import db_manager
    from database.models import UserProgress, QuestionAttempt, LearningSession, Lesson, Topic, User
    DATABASE_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ База данных недоступна для progress_service")
    DATABASE_AVAILABLE = False

from config.settings import DifficultyConfig


class ProgressService:
    """Сервис для работы с прогрессом обучения и адаптивным обучением."""
    
    def __init__(self):
        self.min_level = 1
        self.max_level = 5
        self.questions_per_level_check = 3
    
    async def calculate_next_difficulty(
        self, 
        user_id: int, 
        current_answer_correct: bool,
        current_difficulty: int,
        session_id: int = None
    ) -> tuple[int, str]:
        """Рассчитывает следующий уровень сложности на основе результатов."""
        try:
            if not DATABASE_AVAILABLE:
                # Простая логика без БД
                if current_answer_correct:
                    new_level = min(current_difficulty + 1, self.max_level)
                    reason = "✅ Правильный ответ - повышаем сложность"
                else:
                    new_level = max(current_difficulty - 1, self.min_level)
                    reason = "❌ Неправильный ответ - понижаем сложность"
                
                return new_level, reason
            
            async with db_manager.get_session() as session:
                # ИСПРАВЛЕНО: ищем по telegram_id
                user_result = await session.execute(
                    select(User).where(User.telegram_id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logging.warning(f"⚠️ Пользователь {user_id} не найден для расчета сложности")
                    return current_difficulty, "Пользователь не найден"
                
                # Получаем последние попытки в текущей сессии
                recent_attempts = await session.execute(
                    select(QuestionAttempt)
                    .where(
                        QuestionAttempt.user_id == user.id,  # Используем внутренний ID
                        QuestionAttempt.session_id == session_id
                    )
                    .order_by(desc(QuestionAttempt.created_at))
                    .limit(self.questions_per_level_check)
                )
                
                attempts = recent_attempts.scalars().all()
                
                # ИСПРАВЛЕНО: упрощенная логика адаптации
                if current_answer_correct:
                    if current_difficulty < self.max_level:
                        new_level = current_difficulty + 1
                        reason = f"✅ Правильный ответ - повышаем с {current_difficulty} до {new_level}"
                    else:
                        new_level = current_difficulty
                        reason = f"⭐ Максимальный уровень {current_difficulty}"
                else:
                    if current_difficulty > self.min_level:
                        new_level = current_difficulty - 1
                        reason = f"❌ Неправильный ответ - понижаем с {current_difficulty} до {new_level}"
                    else:
                        new_level = current_difficulty
                        reason = f"📚 Минимальный уровень {current_difficulty}"
                
                return new_level, reason
                
        except Exception as e:
            logging.error(f"❌ Ошибка расчета сложности: {e}")
            return current_difficulty, "Ошибка расчета - сохраняем текущий уровень"
    
    def _adapt_difficulty_by_performance(
        self, 
        current_level: int, 
        accuracy: float, 
        attempts_count: int,
        last_answer_correct: bool
    ) -> tuple[int, str]:
        """Адаптация сложности на основе производительности."""
        
        # Если мало попыток, адаптируем постепенно
        if attempts_count < self.questions_per_level_check:
            if last_answer_correct and current_level < self.max_level:
                return current_level + 1, f"✅ Правильный ответ - повышаем с {current_level} до {current_level + 1}"
            elif not last_answer_correct and current_level > self.min_level:
                return current_level - 1, f"❌ Неправильный ответ - понижаем с {current_level} до {current_level - 1}"
            else:
                return current_level, "Границы сложности достигнуты"
        
        # Адаптация на основе точности
        if accuracy >= 0.8:  # 80%+ правильных ответов
            if current_level < self.max_level:
                new_level = min(current_level + 1, self.max_level)
                return new_level, f"🚀 Высокая точность ({accuracy:.1%}) - повышаем до уровня {new_level}"
            else:
                return current_level, f"⭐ Максимальный уровень! Точность: {accuracy:.1%}"
                
        elif accuracy <= 0.4:  # 40% и менее
            if current_level > self.min_level:
                new_level = max(current_level - 1, self.min_level)
                return new_level, f"📉 Низкая точность ({accuracy:.1%}) - понижаем до уровня {new_level}"
            else:
                return current_level, f"📚 Минимальный уровень. Точность: {accuracy:.1%}"
                
        else:  # 40-80% - нормальная производительность
            return current_level, f"📊 Стабильная работа на уровне {current_level}. Точность: {accuracy:.1%}"
    
    async def update_user_difficulty_level(self, user_id: int, new_level: int, reason: str = "") -> bool:
        """Обновление уровня сложности пользователя."""
        try:
            if not DATABASE_AVAILABLE:
                logging.info(f"📊 Уровень пользователя {user_id}: {new_level} ({reason})")
                return True
            
            async with db_manager.get_session() as session:
                # ИСПРАВЛЕНО: ищем по telegram_id, а не по внутреннему id
                user_result = await session.execute(
                    select(User).where(User.telegram_id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user:
                    old_level = user.current_difficulty_level
                    user.current_difficulty_level = new_level
                    
                    # ИСПРАВЛЕНО: принудительно сохраняем изменения
                    await session.commit()
                    await session.refresh(user)  # Обновляем объект из БД
                    
                    logging.info(f"📊 Пользователь {user_id}: уровень {old_level} → {new_level} ({reason})")
                    return True
                else:
                    logging.warning(f"⚠️ Пользователь {user_id} не найден в БД для обновления уровня")
                
        except Exception as e:
            logging.error(f"❌ Ошибка обновления уровня пользователя: {e}")
            
        return False
    
    async def get_adaptive_feedback(
        self, 
        is_correct: bool, 
        old_level: int, 
        new_level: int,
        explanation: str = "",
        correct_answer: str = ""
    ) -> str:
        """Генерация адаптивной обратной связи."""
        
        if is_correct:
            if new_level > old_level:
                feedback = f"""
✅ <b>Отлично!</b> Правильный ответ!

🚀 <b>Уровень повышен:</b> {old_level} → {new_level}

💪 Вы демонстрируете хорошее понимание материала. Следующий вопрос будет сложнее.
                """
            else:
                feedback = f"""
✅ <b>Правильно!</b>

📊 <b>Уровень:</b> {old_level} (стабильный прогресс)

👍 Продолжайте в том же духе!
                """
        else:
            if new_level < old_level:
                feedback = f"""
❌ <b>Неправильно.</b>

📉 <b>Уровень понижен:</b> {old_level} → {new_level}

💡 <b>Не расстраивайтесь!</b> Следующий вопрос будет проще. Рекомендуем повторить материал.
                """
            else:
                feedback = f"""
❌ <b>Неправильно.</b>

📊 <b>Уровень:</b> {old_level} (без изменений)

🎯 Продолжайте изучение - вы на правильном пути!
                """
        
        # Добавляем правильный ответ и объяснение
        if not is_correct and correct_answer:
            feedback += f"\n\n🎯 <b>Правильный ответ:</b> {correct_answer}"
        
        if explanation:
            feedback += f"\n\n💡 <b>Пояснение:</b> {explanation}"
        
        return feedback
    
    async def get_personalized_question_params(self, user_id: int) -> dict:
        """Получение персонализированных параметров для генерации вопроса."""
        try:
            if not DATABASE_AVAILABLE:
                return {"difficulty": 1, "focus_topics": ["basic_concepts"]}
            
            async with db_manager.get_session() as session:
                # ИСПРАВЛЕНО: получаем пользователя по telegram_id
                user_result = await session.execute(
                    select(User).where(User.telegram_id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logging.warning(f"⚠️ Пользователь {user_id} не найден для получения параметров")
                    return {"difficulty": 1, "focus_topics": ["basic_concepts"]}
                
                current_level = user.current_difficulty_level
                
                # Определяем темы для уровня
                focus_topics = self._get_topics_for_level(current_level)
                
                logging.info(f"📊 Параметры для пользователя {user_id}: уровень {current_level}, темы {focus_topics}")
                
                return {
                    "difficulty": current_level,
                    "focus_topics": focus_topics,
                    "question_type": self._get_question_type_for_level(current_level)
                }
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения персонализированных параметров: {e}")
            return {"difficulty": 1, "focus_topics": ["basic_concepts"]}
    
    def _get_topics_for_level(self, level: int) -> list[str]:
        """Получение тем для уровня сложности."""
        level_topics = {
            1: ["basic_concepts", "definitions"],
            2: ["risk_identification", "threat_types"],
            3: ["risk_assessment", "impact_analysis"], 
            4: ["mitigation_strategies", "business_continuity"],
            5: ["advanced_planning", "regulatory_compliance"]
        }
        return level_topics.get(level, ["basic_concepts"])
    
    def _get_question_type_for_level(self, level: int) -> str:
        """Определение типа вопроса для уровня."""
        if level <= 2:
            return "multiple_choice"
        elif level <= 4:
            return "multiple_choice_complex"
        else:
            return "scenario_based"
    
    async def get_user_overall_progress(self, user_id: int) -> Dict[str, Any]:
        """Получение общего прогресса пользователя."""
        try:
            if not DATABASE_AVAILABLE:
                return {
                    "error": "База данных недоступна",
                    "completion_percentage": 0,
                    "completed_lessons": 0,
                    "total_lessons": 0,
                    "current_level": 1,
                    "level_name": "Начинающий",
                    "study_time_minutes": 0,
                    "study_time_hours": 0,
                    "total_attempts": 0,
                    "correct_attempts": 0,
                    "accuracy_percentage": 0
                }
            
            async with db_manager.get_session() as session:
                # Получение пользователя
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return {"error": "Пользователь не найден"}
                
                # Общее количество уроков
                total_lessons_result = await session.execute(
                    select(func.count(Lesson.id)).where(Lesson.is_active == True)
                )
                total_lessons = total_lessons_result.scalar() or 0
                
                # Завершенные уроки
                completed_lessons_result = await session.execute(
                    select(func.count(UserProgress.id))
                    .where(
                        UserProgress.user_id == user_id,
                        UserProgress.status == "completed"
                    )
                )
                completed_lessons = completed_lessons_result.scalar() or 0
                
                # Общий процент завершения
                completion_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
                
                # Текущий уровень сложности
                current_level = user.current_difficulty_level
                level_name = DifficultyConfig.LEVEL_NAMES.get(current_level, "Неизвестно")
                
                # Время обучения
                study_time_result = await session.execute(
                    select(func.sum(UserProgress.time_spent_minutes))
                    .where(UserProgress.user_id == user_id)
                )
                total_study_time = study_time_result.scalar() or 0
                
                # ИСПРАВЛЕНО: Статистика ответов с правильным приведением типов
                attempts_result = await session.execute(
                    select(
                        func.count(QuestionAttempt.id).label('total'),
                        func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label('correct')
                    )
                    .where(QuestionAttempt.user_id == user_id)
                )
                attempts_stats = attempts_result.first()
                
                total_attempts = attempts_stats.total or 0
                correct_attempts = attempts_stats.correct or 0
                accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
                
                return {
                    "user_id": user_id,
                    "completion_percentage": round(completion_percentage, 1),
                    "completed_lessons": completed_lessons,
                    "total_lessons": total_lessons,
                    "current_level": current_level,
                    "level_name": level_name,
                    "study_time_minutes": total_study_time,
                    "study_time_hours": round(total_study_time / 60, 1),
                    "total_attempts": total_attempts,
                    "correct_attempts": correct_attempts,
                    "accuracy_percentage": round(accuracy, 1),
                    "last_activity": user.last_activity
                }
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения общего прогресса: {e}")
            return {"error": str(e)}
    
    async def get_detailed_progress(self, user_id: int) -> Dict[str, Any]:
        """Получение детального прогресса по темам и урокам."""
        try:
            if not DATABASE_AVAILABLE:
                return {"error": "База данных недоступна"}
                
            # Получение общего прогресса
            overall_progress = await self.get_user_overall_progress(user_id)
            
            return {
                "overall": overall_progress,
                "topics": []  # Упрощенная версия без детального анализа
            }
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения детального прогресса: {e}")
            return {"error": str(e)}
    
    async def update_lesson_progress(
        self, 
        user_id: int, 
        lesson_id: int,
        completion_percentage: float = None,
        mastery_level: float = None,
        time_spent: int = None,
        status: str = None
    ) -> bool:
        """Обновление прогресса по уроку."""
        try:
            if not DATABASE_AVAILABLE:
                logging.warning("⚠️ База данных недоступна для обновления прогресса")
                return False
                
            async with db_manager.get_session() as session:
                # Поиск существующего прогресса
                progress_result = await session.execute(
                    select(UserProgress)
                    .where(
                        UserProgress.user_id == user_id,
                        UserProgress.lesson_id == lesson_id
                    )
                )
                progress = progress_result.scalar_one_or_none()
                
                now = datetime.utcnow()
                
                if progress:
                    # Обновление существующего прогресса
                    if completion_percentage is not None:
                        progress.completion_percentage = completion_percentage
                    if mastery_level is not None:
                        progress.mastery_level = mastery_level
                    if time_spent is not None:
                        progress.time_spent_minutes += time_spent
                    if status is not None:
                        progress.status = status
                        if status == "completed":
                            progress.completed_at = now
                    
                    progress.last_attempt_at = now
                else:
                    # Создание нового прогресса
                    progress = UserProgress(
                        user_id=user_id,
                        lesson_id=lesson_id,
                        status=status or "in_progress",
                        completion_percentage=completion_percentage or 0,
                        mastery_level=mastery_level or 0,
                        time_spent_minutes=time_spent or 0,
                        first_attempt_at=now,
                        last_attempt_at=now
                    )
                    
                    if status == "completed":
                        progress.completed_at = now
                    
                    session.add(progress)
                
                await session.commit()
                
                logging.info(f"📊 Прогресс урока {lesson_id} для пользователя {user_id} обновлен")
                return True
                
        except Exception as e:
            logging.error(f"❌ Ошибка обновления прогресса урока: {e}")
            return False
    
    async def record_question_attempt(
        self,
        user_id: int,
        question_id: int,
        user_answer: str,
        is_correct: bool,
        time_spent: int = None,
        session_id: int = None
    ) -> bool:
        """Запись попытки ответа на вопрос."""
        try:
            if not DATABASE_AVAILABLE:
                logging.warning("⚠️ База данных недоступна для записи попытки")
                return False
                
            async with db_manager.get_session() as session:
                attempt = QuestionAttempt(
                    user_id=user_id,
                    question_id=question_id,
                    session_id=session_id,
                    user_answer=user_answer,
                    is_correct=is_correct,
                    time_spent_seconds=time_spent
                )
                
                session.add(attempt)
                await session.commit()
                
                logging.info(f"📝 Записана попытка ответа пользователя {user_id}")
                return True
                
        except Exception as e:
            logging.error(f"❌ Ошибка записи попытки ответа: {e}")
            return False
    
    async def get_learning_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Получение аналитики обучения за период."""
        try:
            if not DATABASE_AVAILABLE:
                return {"error": "База данных недоступна"}
                
            return {
                "period_days": days,
                "daily_activity": [],
                "difficulty_progress": {},
                "study_time": []
            }
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения аналитики: {e}")
            return {"error": str(e)}
    
    async def get_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение достижений пользователя."""
        try:
            if not DATABASE_AVAILABLE:
                return []
                
            # Базовые достижения без БД
            achievements = [
                {
                    "id": "first_question",
                    "title": "Первый вопрос",
                    "description": "Задан первый вопрос AI-ассистенту",
                    "icon": "❓",
                    "earned_at": datetime.utcnow()
                }
            ]
            
            return achievements
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения достижений: {e}")
            return []
    
    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение таблицы лидеров."""
        try:
            if not DATABASE_AVAILABLE:
                return []
                
            return []
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения таблицы лидеров: {e}")
            return []
    
    async def export_user_progress(self, user_id: int) -> Dict[str, Any]:
        """Экспорт прогресса пользователя для отчета."""
        try:
            # Получение всех данных
            overall_progress = await self.get_user_overall_progress(user_id)
            detailed_progress = await self.get_detailed_progress(user_id)
            analytics = await self.get_learning_analytics(user_id, 30)
            achievements = await self.get_achievements(user_id)
            
            return {
                "export_date": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "overall_progress": overall_progress,
                "detailed_progress": detailed_progress,
                "analytics": analytics,
                "achievements": achievements
            }
            
        except Exception as e:
            logging.error(f"❌ Ошибка экспорта прогресса: {e}")
            return {"error": str(e)}