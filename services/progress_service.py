"""
Сервис для управления прогрессом обучения пользователей.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from database.database import db_manager
from database.models import UserProgress, QuestionAttempt, LearningSession, Lesson, Topic, User
from config.settings import DifficultyConfig


class ProgressService:
    """Сервис для работы с прогрессом обучения."""
    
"""
Сервис для управления прогрессом обучения пользователей.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from database.database import db_manager
from database.models import UserProgress, QuestionAttempt, LearningSession, Lesson, Topic, User
from config.settings import DifficultyConfig


class ProgressService:
    """Сервис для работы с прогрессом обучения."""
    
    async def get_user_overall_progress(self, user_id: int) -> Dict[str, Any]:
        """Получение общего прогресса пользователя."""
        try:
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
                
                # Статистика ответов
                attempts_result = await session.execute(
                    select(
                        func.count(QuestionAttempt.id).label('total'),
                        func.sum(func.cast(QuestionAttempt.is_correct, func.Integer())).label('correct')
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
            async with db_manager.get_session() as session:
                # Прогресс по темам
                topics_result = await session.execute(
                    select(Topic)
                    .where(Topic.is_active == True)
                    .order_by(Topic.order_index)
                )
                topics = topics_result.scalars().all()
                
                topics_progress = []
                for topic in topics:
                    # Получаем уроки для каждой темы отдельным запросом
                    lessons_result = await session.execute(
                        select(Lesson)
                        .where(Lesson.topic_id == topic.id, Lesson.is_active == True)
                        .order_by(Lesson.order_index)
                    )
                    # Прогресс по урокам темы
                    lessons_progress = []
                    topic_completion = 0
                    topic_total_lessons = 0
                    
                    for lesson in lessons:
                        if not lesson.is_active:
                            continue
                            
                        topic_total_lessons += 1
                        
                        # Получение прогресса по уроку
                        progress_result = await session.execute(
                            select(UserProgress)
                            .where(
                                UserProgress.user_id == user_id,
                                UserProgress.lesson_id == lesson.id
                            )
                        )
                        progress = progress_result.scalar_one_or_none()
                        
                        lesson_data = {
                            "lesson_id": lesson.id,
                            "title": lesson.title,
                            "difficulty_level": lesson.difficulty_level,
                            "status": progress.status if progress else "not_started",
                            "completion_percentage": progress.completion_percentage if progress else 0,
                            "mastery_level": progress.mastery_level if progress else 0,
                            "attempts": progress.total_attempts if progress else 0,
                            "correct_attempts": progress.correct_attempts if progress else 0,
                            "last_attempt": progress.last_attempt_at if progress else None
                        }
                        
                        lessons_progress.append(lesson_data)
                        
                        if progress and progress.status == "completed":
                            topic_completion += 1
                    
                    topic_completion_percentage = (topic_completion / topic_total_lessons * 100) if topic_total_lessons > 0 else 0
                    
                    topics_progress.append({
                        "topic_id": topic.id,
                        "title": topic.title,
                        "difficulty_level": topic.difficulty_level,
                        "completion_percentage": round(topic_completion_percentage, 1),
                        "completed_lessons": topic_completion,
                        "total_lessons": topic_total_lessons,
                        "lessons": lessons_progress
                    })
                
                # Общая статистика
                overall_progress = await self.get_user_overall_progress(user_id)
                
                return {
                    "overall": overall_progress,
                    "topics": topics_progress
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
                
                # Обновление статистики урока
                if question_id:
                    await self._update_lesson_attempt_stats(user_id, question_id, is_correct, session)
                
                logging.info(f"📝 Записана попытка ответа пользователя {user_id}")
                return True
                
        except Exception as e:
            logging.error(f"❌ Ошибка записи попытки ответа: {e}")
            return False
    
    async def _update_lesson_attempt_stats(self, user_id: int, question_id: int, is_correct: bool, session):
        """Обновление статистики попыток по уроку."""
        try:
            # Получение урока через вопрос
            from database.models import Question
            
            question_result = await session.execute(
                select(Question).where(Question.id == question_id)
            )
            question = question_result.scalar_one_or_none()
            
            if not question:
                return
            
            # Обновление прогресса урока
            progress_result = await session.execute(
                select(UserProgress)
                .where(
                    UserProgress.user_id == user_id,
                    UserProgress.lesson_id == question.lesson_id
                )
            )
            progress = progress_result.scalar_one_or_none()
            
            if not progress:
                progress = UserProgress(
                    user_id=user_id,
                    lesson_id=question.lesson_id,
                    status="in_progress",
                    first_attempt_at=datetime.utcnow()
                )
                session.add(progress)
            
            progress.total_attempts += 1
            if is_correct:
                progress.correct_attempts += 1
            
            # Пересчет среднего балла
            progress.average_score = (progress.correct_attempts / progress.total_attempts) * 100
            
            await session.commit()
            
        except Exception as e:
            logging.error(f"❌ Ошибка обновления статистики урока: {e}")
    
    async def get_learning_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Получение аналитики обучения за период."""
        try:
            async with db_manager.get_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Активность по дням
                daily_activity = await session.execute(
                    select(
                        func.date(QuestionAttempt.created_at).label('date'),
                        func.count(QuestionAttempt.id).label('attempts'),
                        func.sum(func.cast(QuestionAttempt.is_correct, func.Integer())).label('correct')
                    )
                    .where(
                        QuestionAttempt.user_id == user_id,
                        QuestionAttempt.created_at >= cutoff_date
                    )
                    .group_by(func.date(QuestionAttempt.created_at))
                    .order_by(func.date(QuestionAttempt.created_at))
                )
                
                activity_data = []
                for row in daily_activity:
                    activity_data.append({
                        "date": row.date.isoformat(),
                        "attempts": row.attempts,
                        "correct": row.correct or 0,
                        "accuracy": (row.correct / row.attempts * 100) if row.attempts > 0 else 0
                    })
                
                # Прогресс по уровням сложности
                difficulty_progress = await session.execute(
                    select(
                        Question.difficulty_level,
                        func.count(QuestionAttempt.id).label('attempts'),
                        func.sum(func.cast(QuestionAttempt.is_correct, func.Integer())).label('correct')
                    )
                    .join(Question, QuestionAttempt.question_id == Question.id)
                    .where(
                        QuestionAttempt.user_id == user_id,
                        QuestionAttempt.created_at >= cutoff_date
                    )
                    .group_by(Question.difficulty_level)
                )
                
                difficulty_data = {}
                for row in difficulty_progress:
                    level_name = DifficultyConfig.LEVEL_NAMES.get(row.difficulty_level, "Неизвестно")
                    difficulty_data[level_name] = {
                        "attempts": row.attempts,
                        "correct": row.correct or 0,
                        "accuracy": (row.correct / row.attempts * 100) if row.attempts > 0 else 0
                    }
                
                # Время обучения по дням
                study_time = await session.execute(
                    select(
                        func.date(LearningSession.started_at).label('date'),
                        func.sum(
                            func.extract('epoch', 
                                func.coalesce(LearningSession.completed_at, LearningSession.last_activity_at) 
                                - LearningSession.started_at
                            ) / 60
                        ).label('minutes')
                    )
                    .where(
                        LearningSession.user_id == user_id,
                        LearningSession.started_at >= cutoff_date
                    )
                    .group_by(func.date(LearningSession.started_at))
                )
                
                study_time_data = []
                for row in study_time:
                    study_time_data.append({
                        "date": row.date.isoformat(),
                        "minutes": round(float(row.minutes or 0), 1)
                    })
                
                return {
                    "period_days": days,
                    "daily_activity": activity_data,
                    "difficulty_progress": difficulty_data,
                    "study_time": study_time_data
                }
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения аналитики: {e}")
            return {"error": str(e)}
    
    async def get_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение достижений пользователя."""
        try:
            async with db_manager.get_session() as session:
                # Получение статистики для расчета достижений
                overall_progress = await self.get_user_overall_progress(user_id)
                
                achievements = []
                
                # Достижения за завершение уроков
                completed_lessons = overall_progress.get("completed_lessons", 0)
                if completed_lessons >= 1:
                    achievements.append({
                        "id": "first_lesson",
                        "title": "Первые шаги",
                        "description": "Завершен первый урок",
                        "icon": "🎯",
                        "earned_at": await self._get_achievement_date(user_id, "first_lesson")
                    })
                
                if completed_lessons >= 5:
                    achievements.append({
                        "id": "five_lessons",
                        "title": "Настойчивость",
                        "description": "Завершено 5 уроков",
                        "icon": "🏆",
                        "earned_at": await self._get_achievement_date(user_id, "five_lessons")
                    })
                
                if completed_lessons >= 10:
                    achievements.append({
                        "id": "ten_lessons",
                        "title": "Эксперт",
                        "description": "Завершено 10 уроков",
                        "icon": "🥇",
                        "earned_at": await self._get_achievement_date(user_id, "ten_lessons")
                    })
                
                # Достижения за точность
                accuracy = overall_progress.get("accuracy_percentage", 0)
                if accuracy >= 80 and overall_progress.get("total_attempts", 0) >= 10:
                    achievements.append({
                        "id": "accuracy_master",
                        "title": "Мастер точности",
                        "description": "80%+ правильных ответов",
                        "icon": "🎯",
                        "earned_at": await self._get_achievement_date(user_id, "accuracy_master")
                    })
                
                # Достижения за время обучения
                study_hours = overall_progress.get("study_time_hours", 0)
                if study_hours >= 1:
                    achievements.append({
                        "id": "one_hour",
                        "title": "Час знаний",
                        "description": "Час обучения пройден",
                        "icon": "⏰",
                        "earned_at": await self._get_achievement_date(user_id, "one_hour")
                    })
                
                # Достижения за уровень сложности
                current_level = overall_progress.get("current_level", 1)
                if current_level >= 3:
                    achievements.append({
                        "id": "advanced_level",
                        "title": "Продвинутый уровень",
                        "description": "Достигнут продвинутый уровень",
                        "icon": "🚀",
                        "earned_at": await self._get_achievement_date(user_id, "advanced_level")
                    })
                
                if current_level >= 5:
                    achievements.append({
                        "id": "master_level",
                        "title": "Мастер рисков",
                        "description": "Достигнут мастер-уровень",
                        "icon": "👑",
                        "earned_at": await self._get_achievement_date(user_id, "master_level")
                    })
                
                return achievements
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения достижений: {e}")
            return []
    
    async def _get_achievement_date(self, user_id: int, achievement_id: str) -> Optional[datetime]:
        """Получение даты получения достижения (упрощенная версия)."""
        try:
            async with db_manager.get_session() as session:
                # В реальной системе здесь была бы таблица достижений
                # Пока возвращаем дату последней активности
                user_result = await session.execute(
                    select(User.last_activity).where(User.id == user_id)
                )
                last_activity = user_result.scalar()
                return last_activity
                
        except Exception as e:
            logging.error(f"❌ Ошибка получения даты достижения: {e}")
            return None
    
    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение таблицы лидеров."""
        try:
            async with db_manager.get_session() as session:
                # Топ пользователей по завершенным урокам
                leaderboard_result = await session.execute(
                    select(
                        User.id,
                        User.first_name,
                        User.username,
                        User.current_difficulty_level,
                        func.count(UserProgress.id).label('completed_lessons'),
                        func.avg(UserProgress.average_score).label('avg_score')
                    )
                    .join(UserProgress, User.id == UserProgress.user_id)
                    .where(UserProgress.status == "completed")
                    .group_by(User.id, User.first_name, User.username, User.current_difficulty_level)
                    .order_by(desc('completed_lessons'), desc('avg_score'))
                    .limit(limit)
                )
                
                leaderboard = []
                for rank, row in enumerate(leaderboard_result, 1):
                    leaderboard.append({
                        "rank": rank,
                        "user_id": row.id,
                        "name": row.first_name or row.username or "Аноним",
                        "level": DifficultyConfig.LEVEL_NAMES.get(row.current_difficulty_level, "Начинающий"),
                        "completed_lessons": row.completed_lessons,
                        "average_score": round(float(row.avg_score or 0), 1)
                    })
                
                return leaderboard
                
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