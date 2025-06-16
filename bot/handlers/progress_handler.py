"""
Обработчик отображения прогресса пользователя.
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

try:
    from database.database import get_user_by_telegram_id, db_manager
    from database.models import User, QuestionAttempt, LearningSession
    from services.progress_service import ProgressService
    from sqlalchemy import select, func, desc
    DATABASE_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ База данных недоступна для progress_handler")
    DATABASE_AVAILABLE = False

from bot.keyboards.main_menu import get_main_menu_keyboard


async def handle_show_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик показа прогресса пользователя."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Callback query error: {e}")
    
    try:
        if not DATABASE_AVAILABLE:
            await query.edit_message_text(
                "😔 Функция прогресса временно недоступна",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        user_telegram_id = update.effective_user.id
        
        # Получаем пользователя
        user = await get_user_by_telegram_id(user_telegram_id)
        if not user:
            await query.edit_message_text(
                "❌ Пользователь не найден. Используйте /start",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Собираем статистику
        progress_data = await get_user_progress_data(user.id)
        
        # Формируем сообщение о прогрессе
        progress_text = format_progress_message(user, progress_data)
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Подробная статистика", callback_data="detailed_stats"),
                InlineKeyboardButton("🎯 Рекомендации", callback_data="get_recommendations")
            ],
            [
                InlineKeyboardButton("📚 Продолжить обучение", callback_data="start_learning"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]
        ]
        
        await query.edit_message_text(
            text=progress_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка показа прогресса: {e}")
        await query.edit_message_text(
            "😔 Произошла ошибка при получении прогресса",
            reply_markup=get_main_menu_keyboard()
        )


async def get_user_progress_data(user_id: int) -> dict:
    """Получение данных о прогрессе пользователя."""
    try:
        async with db_manager.get_session() as session:
            # Общая статистика ответов
            total_stats = await session.execute(
                select(
                    func.count(QuestionAttempt.id).label('total'),
                    func.sum(func.cast(QuestionAttempt.is_correct, func.Integer())).label('correct'),
                    func.avg(QuestionAttempt.time_spent_seconds).label('avg_time')
                )
                .where(QuestionAttempt.user_id == user_id)
            )
            
            total_data = total_stats.first()
            
            # Статистика за последнюю неделю
            week_ago = datetime.utcnow() - timedelta(days=7)
            weekly_stats = await session.execute(
                select(
                    func.count(QuestionAttempt.id).label('total'),
                    func.sum(func.cast(QuestionAttempt.is_correct, func.Integer())).label('correct')
                )
                .where(
                    QuestionAttempt.user_id == user_id,
                    QuestionAttempt.created_at >= week_ago
                )
            )
            
            weekly_data = weekly_stats.first()
            
            # Количество сессий
            sessions_count = await session.execute(
                select(func.count(LearningSession.id))
                .where(LearningSession.user_id == user_id)
            )
            
            sessions = sessions_count.scalar() or 0
            
            # Последняя активность
            last_attempt = await session.execute(
                select(QuestionAttempt.created_at)
                .where(QuestionAttempt.user_id == user_id)
                .order_by(desc(QuestionAttempt.created_at))
                .limit(1)
            )
            
            last_activity = last_attempt.scalar()
            
            return {
                'total_questions': total_data.total or 0,
                'correct_answers': total_data.correct or 0,
                'avg_time': total_data.avg_time or 0,
                'weekly_questions': weekly_data.total or 0,
                'weekly_correct': weekly_data.correct or 0,
                'sessions_count': sessions,
                'last_activity': last_activity
            }
            
    except Exception as e:
        logging.error(f"❌ Ошибка получения данных прогресса: {e}")
        return {
            'total_questions': 0,
            'correct_answers': 0,
            'avg_time': 0,
            'weekly_questions': 0,
            'weekly_correct': 0,
            'sessions_count': 0,
            'last_activity': None
        }


def format_progress_message(user, progress_data: dict) -> str:
    """Форматирование сообщения о прогрессе."""
    
    # Расчет общей точности
    total_accuracy = 0
    if progress_data['total_questions'] > 0:
        total_accuracy = (progress_data['correct_answers'] / progress_data['total_questions']) * 100
    
    # Расчет недельной точности
    weekly_accuracy = 0
    if progress_data['weekly_questions'] > 0:
        weekly_accuracy = (progress_data['weekly_correct'] / progress_data['weekly_questions']) * 100
    
    # Определение уровня
    level_name = get_level_name(user.current_difficulty_level)
    
    # Последняя активность
    last_activity_text = "Никогда"
    if progress_data['last_activity']:
        days_ago = (datetime.utcnow() - progress_data['last_activity']).days
        if days_ago == 0:
            last_activity_text = "Сегодня"
        elif days_ago == 1:
            last_activity_text = "Вчера"
        else:
            last_activity_text = f"{days_ago} дней назад"
    
    # Эмодзи для прогресса
    accuracy_emoji = "🔥" if total_accuracy >= 80 else "👍" if total_accuracy >= 60 else "📚"
    level_emoji = "⭐" if user.current_difficulty_level >= 4 else "🚀" if user.current_difficulty_level >= 3 else "📈"
    
    return f"""
📊 <b>Ваш прогресс обучения</b>

{level_emoji} <b>Текущий уровень:</b> {user.current_difficulty_level}/5 ({level_name})

{accuracy_emoji} <b>Общая статистика:</b>
• Всего вопросов: {progress_data['total_questions']}
• Правильных ответов: {progress_data['correct_answers']}
• Точность: {total_accuracy:.1f}%
• Сессий обучения: {progress_data['sessions_count']}

📅 <b>За последнюю неделю:</b>
• Вопросов: {progress_data['weekly_questions']}
• Правильных: {progress_data['weekly_correct']}
• Точность: {weekly_accuracy:.1f}%

🕐 <b>Последняя активность:</b> {last_activity_text}

{get_progress_recommendation(user.current_difficulty_level, total_accuracy)}
    """


def get_level_name(level: int) -> str:
    """Получение названия уровня."""
    level_names = {
        1: "Новичок",
        2: "Изучающий", 
        3: "Практик",
        4: "Эксперт",
        5: "Мастер"
    }
    return level_names.get(level, "Неизвестно")


def get_progress_recommendation(level: int, accuracy: float) -> str:
    """Получение рекомендации на основе прогресса."""
    if accuracy >= 90:
        return "🎯 <b>Отличные результаты!</b> Вы готовы к более сложным темам."
    elif accuracy >= 70:
        return "💪 <b>Хороший прогресс!</b> Продолжайте изучение новых тем."
    elif accuracy >= 50:
        return "📚 <b>Есть над чем работать.</b> Рекомендуем повторить материал."
    else:
        return "🎓 <b>Начинайте с основ.</b> Изучите теоретические материалы."


async def handle_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик подробной статистики."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Callback query error: {e}")
    
    try:
        user_telegram_id = update.effective_user.id
        user = await get_user_by_telegram_id(user_telegram_id)
        
        if not user:
            await query.edit_message_text(
                "❌ Пользователь не найден",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Получаем детальную статистику
        detailed_stats = await get_detailed_statistics(user.id)
        stats_text = format_detailed_stats(detailed_stats)
        
        keyboard = [
            [InlineKeyboardButton("◀️ Назад к прогрессу", callback_data="show_progress")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка показа детальной статистики: {e}")


async def get_detailed_statistics(user_id: int) -> dict:
    """Получение детальной статистики."""
    try:
        async with db_manager.get_session() as session:
            # Статистика по дням за последние 7 дней
            daily_stats = []
            for i in range(7):
                day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                
                day_result = await session.execute(
                    select(
                        func.count(QuestionAttempt.id).label('total'),
                        func.sum(func.cast(QuestionAttempt.is_correct, func.Integer())).label('correct')
                    )
                    .where(
                        QuestionAttempt.user_id == user_id,
                        QuestionAttempt.created_at >= day_start,
                        QuestionAttempt.created_at < day_end
                    )
                )
                
                day_data = day_result.first()
                daily_stats.append({
                    'date': day_start.strftime('%d.%m'),
                    'total': day_data.total or 0,
                    'correct': day_data.correct or 0
                })
            
            return {'daily_stats': daily_stats}
            
    except Exception as e:
        logging.error(f"❌ Ошибка получения детальной статистики: {e}")
        return {'daily_stats': []}


def format_detailed_stats(stats: dict) -> str:
    """Форматирование детальной статистики."""
    text = "📈 <b>Подробная статистика за неделю</b>\n\n"
    
    for day in reversed(stats['daily_stats']):  # Показываем от старых к новым
        if day['total'] > 0:
            accuracy = (day['correct'] / day['total']) * 100
            text += f"📅 <b>{day['date']}</b>: {day['correct']}/{day['total']} ({accuracy:.0f}%)\n"
        else:
            text += f"📅 <b>{day['date']}</b>: Не было активности\n"
    
    return text


async def handle_get_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик получения рекомендаций."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Callback query error: {e}")
    
    try:
        user_telegram_id = update.effective_user.id
        user = await get_user_by_telegram_id(user_telegram_id)
        
        if not user:
            await query.edit_message_text(
                "❌ Пользователь не найден",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        progress_data = await get_user_progress_data(user.id)
        recommendations = generate_recommendations(user, progress_data)
        
        keyboard = [
            [InlineKeyboardButton("📚 Начать изучение", callback_data="start_learning")],
            [InlineKeyboardButton("◀️ Назад к прогрессу", callback_data="show_progress")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=recommendations,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка генерации рекомендаций: {e}")


def generate_recommendations(user, progress_data: dict) -> str:
    """Генерация персональных рекомендаций."""
    
    total_accuracy = 0
    if progress_data['total_questions'] > 0:
        total_accuracy = (progress_data['correct_answers'] / progress_data['total_questions']) * 100
    
    level = user.current_difficulty_level
    
    recommendations = "🎯 <b>Персональные рекомендации</b>\n\n"
    
    # Рекомендации по уровню
    if level == 1:
        recommendations += "📚 <b>Базовый уровень:</b>\n"
        recommendations += "• Изучите основные термины (RTO, MTPD)\n"
        recommendations += "• Разберите классификацию рисков\n"
        recommendations += "• Пройдите теоретические модули\n\n"
    elif level == 2:
        recommendations += "📈 <b>Развивающийся уровень:</b>\n"
        recommendations += "• Изучите типы угроз подробнее\n"
        recommendations += "• Практикуйтесь в идентификации рисков\n"
        recommendations += "• Решайте больше практических задач\n\n"
    elif level >= 3:
        recommendations += "🚀 <b>Продвинутый уровень:</b>\n"
        recommendations += "• Изучайте сложные сценарии\n"
        recommendations += "• Практикуйте планирование восстановления\n"
        recommendations += "• Углубляйтесь в регулятивные требования\n\n"
    
    # Рекомендации по точности
    if total_accuracy < 60:
        recommendations += "💡 <b>Рекомендации по улучшению:</b>\n"
        recommendations += "• Больше времени уделяйте теории\n"
        recommendations += "• Используйте подсказки при ответах\n"
        recommendations += "• Задавайте вопросы AI-ассистенту\n"
        recommendations += "• Повторяйте пройденный материал\n\n"
    
    # Рекомендации по активности
    last_activity = progress_data.get('last_activity')
    if last_activity:
        days_ago = (datetime.utcnow() - last_activity).days
        if days_ago > 3:
            recommendations += "⏰ <b>Регулярность обучения:</b>\n"
            recommendations += "• Занимайтесь каждый день по 10-15 минут\n"
            recommendations += "• Установите напоминания\n"
            recommendations += "• Регулярная практика улучшает результаты\n\n"
    
    recommendations += "🎓 <b>Следующие шаги:</b>\n"
    recommendations += "• Пройдите новый урок\n"
    recommendations += "• Задайте вопросы по сложным темам\n"
    recommendations += "• Отслеживайте свой прогресс\n"
    
    return recommendations


def register_progress_handlers(application):
    """Регистрация обработчиков прогресса."""
    application.add_handler(CallbackQueryHandler(handle_show_progress, pattern="^show_progress$"))
    application.add_handler(CallbackQueryHandler(handle_detailed_stats, pattern="^detailed_stats$"))
    application.add_handler(CallbackQueryHandler(handle_get_recommendations, pattern="^get_recommendations$"))