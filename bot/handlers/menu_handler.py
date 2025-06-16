"""
Обработчики меню AI-агента.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from bot.keyboards.main_menu import (
    get_main_menu_keyboard, get_learning_menu_keyboard, 
    get_question_menu_keyboard, get_progress_menu_keyboard,
    get_settings_keyboard, get_difficulty_keyboard,
    get_notification_keyboard, get_back_to_menu_keyboard
)
from config.settings import MessageTemplates
from database.database import get_user_by_telegram_id
from services.progress_service import ProgressService
from services.user_service import UserService


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик главного меню."""
    query = update.callback_query
    await query.answer()
    
    try:
        welcome_text = """
🏦 <b>AI-Агент обучения банковским рискам</b>

Добро пожаловать в интеллектуальную систему обучения управлению рисками непрерывности деятельности банка.

🎯 <b>Выберите действие:</b>
• <b>Обучение</b> - адаптивный курс с AI-поддержкой
• <b>Вопросы</b> - получите ответы от AI-ассистента
• <b>Прогресс</b> - отслеживайте свои достижения
• <b>Инструкция</b> - узнайте как работать с ботом
        """
        
        await query.edit_message_text(
            text=welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_main_menu: {e}")


async def handle_learning_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик меню обучения."""
    query = update.callback_query
    await query.answer()
    
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await query.edit_message_text("❌ Пользователь не найден. Используйте /start")
            return
        
        progress_service = ProgressService()
        progress_info = await progress_service.get_user_overall_progress(user.id)
        
        learning_text = f"""
📚 <b>Меню обучения</b>

👤 <b>Ваш профиль:</b>
• Уровень: {progress_info.get('level_name', 'Начинающий')}
• Прогресс: {progress_info.get('completion_percentage', 0):.1f}%
• Пройдено уроков: {progress_info.get('completed_lessons', 0)}

🎯 <b>Выберите действие:</b>
        """
        
        await query.edit_message_text(
            text=learning_text,
            reply_markup=get_learning_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_learning_menu: {e}")


async def handle_question_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик меню вопросов AI."""
    query = update.callback_query
    await query.answer()
    
    try:
        question_text = """
🤖 <b>AI-Ассистент по рискам</b>

Задайте любой вопрос по управлению рисками непрерывности деятельности банка. 

💡 <b>Примеры вопросов:</b>
• "Что делать при пожаре в офисе?"
• "Как рассчитать время восстановления?"
• "Какие есть типы угроз?"
• "Что такое RTO и MTPD?"

🔍 <b>Возможности:</b>
• Поиск в методике
• История ваших вопросов
• Частые вопросы и ответы
        """
        
        await query.edit_message_text(
            text=question_text,
            reply_markup=get_question_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_question_menu: {e}")


async def handle_progress_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик меню прогресса."""
    query = update.callback_query
    await query.answer()
    
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await query.edit_message_text("❌ Пользователь не найден. Используйте /start")
            return
        
        progress_service = ProgressService()
        stats = await progress_service.get_detailed_progress(user.id)
        
        progress_text = f"""
📊 <b>Ваш прогресс обучения</b>

📈 <b>Общая статистика:</b>
• Общий прогресс: {stats.get('overall_progress', 0):.1f}%
• Пройдено уроков: {stats.get('completed_lessons', 0)}/{stats.get('total_lessons', 0)}
• Правильных ответов: {stats.get('correct_answers', 0)}/{stats.get('total_answers', 0)}
• Время обучения: {stats.get('study_time_hours', 0):.1f} ч

🎯 <b>Текущий уровень:</b> {stats.get('current_level', 'Начинающий')}

🏆 <b>Достижения:</b> {stats.get('achievements_count', 0)}
        """
        
        await query.edit_message_text(
            text=progress_text,
            reply_markup=get_progress_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_progress_menu: {e}")


async def handle_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик меню настроек."""
    query = update.callback_query
    await query.answer()
    
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await query.edit_message_text("❌ Пользователь не найден. Используйте /start")
            return
        
        settings_text = f"""
⚙️ <b>Настройки</b>

👤 <b>Текущие настройки:</b>
• Уровень сложности: {user.current_difficulty_level}/5
• Уведомления: {'Включены' if user.notifications_enabled else 'Отключены'}
• Язык: {user.preferred_language.upper()}

🔧 <b>Доступные настройки:</b>
        """
        
        await query.edit_message_text(
            text=settings_text,
            reply_markup=get_settings_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_settings_menu: {e}")


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик справки."""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text(
            text=MessageTemplates.HELP,
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_help: {e}")


async def handle_difficulty_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик настройки сложности."""
    query = update.callback_query
    await query.answer()
    
    try:
        difficulty_text = """
🎯 <b>Выберите уровень сложности</b>

🟢 <b>Начинающий</b> - базовые понятия и простые вопросы
🟡 <b>Базовый</b> - основные процедуры и методы
🟠 <b>Продвинутый</b> - сложные сценарии и расчеты
🔴 <b>Эксперт</b> - комплексные кейсы и анализ
🟣 <b>Мастер</b> - экспертные знания и принятие решений

💡 AI-агент будет адаптировать вопросы под ваш уровень.
        """
        
        await query.edit_message_text(
            text=difficulty_text,
            reply_markup=get_difficulty_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_difficulty_settings: {e}")


async def handle_difficulty_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения уровня сложности."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Извлекаем уровень из callback_data
        difficulty_level = int(query.data.split('_')[1])
        
        user_service = UserService()
        await user_service.update_difficulty_level(update.effective_user.id, difficulty_level)
        
        level_names = {1: "Начинающий", 2: "Базовый", 3: "Продвинутый", 4: "Эксперт", 5: "Мастер"}
        
        success_text = f"""
✅ <b>Уровень сложности изменен</b>

Новый уровень: <b>{level_names[difficulty_level]}</b>

AI-агент будет генерировать вопросы соответствующей сложности.
        """
        
        await query.edit_message_text(
            text=success_text,
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_difficulty_change: {e}")


async def handle_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик настройки уведомлений."""
    query = update.callback_query
    await query.answer()
    
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        notification_text = f"""
🔔 <b>Настройки уведомлений</b>

📱 <b>Текущий статус:</b> {'Включены' if user.notifications_enabled else 'Отключены'}

📋 <b>Типы уведомлений:</b>
• Напоминания о продолжении обучения
• Уведомления о новых материалах
• Информация о достижениях

⏰ <b>По умолчанию:</b> напоминание через 8 часов неактивности
        """
        
        await query.edit_message_text(
            text=notification_text,
            reply_markup=get_notification_keyboard(user.notifications_enabled),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_notification_settings: {e}")


async def handle_notification_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик включения/отключения уведомлений."""
    query = update.callback_query
    await query.answer()
    
    try:
        action = query.data.split('_')[0]  # enable или disable
        new_status = action == "enable"
        
        user_service = UserService()
        await user_service.update_notification_settings(update.effective_user.id, new_status)
        
        status_text = "включены" if new_status else "отключены"
        
        success_text = f"""
✅ <b>Настройки обновлены</b>

Уведомления <b>{status_text}</b>
        """
        
        await query.edit_message_text(
            text=success_text,
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_notification_toggle: {e}")


def register_menu_handlers(application):
    """Регистрация обработчиков меню."""
    # Основные меню
    application.add_handler(CallbackQueryHandler(handle_main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(handle_learning_menu, pattern="^learning_menu$"))
    application.add_handler(CallbackQueryHandler(handle_question_menu, pattern="^ask_question$"))
    application.add_handler(CallbackQueryHandler(handle_progress_menu, pattern="^show_progress$"))
    application.add_handler(CallbackQueryHandler(handle_settings_menu, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(handle_help, pattern="^show_help$"))
    
    # Новые обработчики для недостающих кнопок
    application.add_handler(CallbackQueryHandler(handle_analytics, pattern="^analytics$"))
    
    # Настройки
    application.add_handler(CallbackQueryHandler(handle_difficulty_settings, pattern="^difficulty_settings$"))
    application.add_handler(CallbackQueryHandler(handle_difficulty_change, pattern="^difficulty_[1-5]$"))
    application.add_handler(CallbackQueryHandler(handle_notification_settings, pattern="^notification_settings$"))
    application.add_handler(CallbackQueryHandler(handle_notification_toggle, pattern="^(enable|disable)_notifications$"))


async def handle_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик аналитики/статистики."""
    query = update.callback_query
    await query.answer()
    
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        analytics_text = f"""
📊 <b>Статистика обучения</b>

👤 <b>Пользователь:</b> {user.first_name or user.username or 'Аноним'}
🎯 <b>Текущий уровень:</b> {user.current_difficulty_level}/5

📈 <b>Общая статистика:</b>
• Время в системе: доступно после обновления
• Активных сессий: доступно после обновления  
• Вопросов отвечено: доступно после обновления

💡 <b>Рекомендации:</b>
• Продолжайте обучение для получения статистики
• Задавайте вопросы AI-ассистенту
• Изучайте материалы методики

🔄 Статистика обновляется в реальном времени
        """
        
        await query.edit_message_text(
            text=analytics_text,
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в handle_analytics: {e}")