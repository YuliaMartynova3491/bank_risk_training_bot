"""
Обработчики уроков и обучения AI-агента.
"""

import logging
import random
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from bot.keyboards.main_menu import get_answer_keyboard, get_navigation_keyboard, get_main_menu_keyboard
from config.settings import Stickers
from database.database import get_user_by_telegram_id
from services.user_service import UserService
from services.progress_service import ProgressService


async def handle_start_learning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик начала обучения."""
    query = update.callback_query
    await query.answer()
    
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await query.edit_message_text("❌ Пользователь не найден. Используйте /start")
            return
        
        # Получение AI-агента
        learning_graph = context.application.bot_data.get('learning_graph')
        if not learning_graph:
            await query.edit_message_text(
                "😔 AI-агент временно недоступен. Попробуйте позже.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Отправка стикера приветствия
        welcome_sticker = random.choice(Stickers.WELCOME)
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id,
            sticker=welcome_sticker
        )
        
        # Запуск сессии обучения
        result = await learning_graph.start_learning_session(user.id)
        
        if "error" in result:
            await query.edit_message_text(
                f"😔 Ошибка запуска обучения: {result['error']}",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Создание сессии в базе данных
        user_service = UserService()
        session = await user_service.create_learning_session(user.id)
        
        # Получение первого вопроса
        if "generated_question" in result:
            await present_question(update, context, result["generated_question"], session.id)
        else:
            await query.edit_message_text(
                "🎓 Добро пожаловать на обучение!\n\nАI-агент анализирует ваш уровень знаний и подготавливает персональные вопросы...",
                reply_markup=get_main_menu_keyboard()
            )
        
    except Exception as e:
        logging.error(f"❌ Ошибка начала обучения: {e}")
        await query.edit_message_text(
            "😔 Произошла ошибка при запуске обучения. Попробуйте еще раз.",
            reply_markup=get_main_menu_keyboard()
        )


async def handle_continue_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик продолжения урока."""
    query = update.callback_query
    await query.answer()
    
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        # Поиск активной сессии
        user_service = UserService()
        active_session = await user_service.get_active_session(user.id)
        
        if not active_session:
            await query.edit_message_text(
                "📚 У вас нет активной сессии обучения.\n\nНачните новое обучение?",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Получение контекста обучения
        learning_graph = context.application.bot_data.get('learning_graph')
        user_context = learning_graph.get_user_context(user.id) if learning_graph else None
        
        if not user_context:
            await query.edit_message_text(
                "🔄 Восстанавливаем вашу сессию обучения...",
                reply_markup=get_main_menu_keyboard()
            )
            # Здесь можно добавить логику восстановления сессии
            return
        
        # Генерация следующего вопроса
        if learning_graph:
            result = await learning_graph.start_learning_session(user.id)
            if "generated_question" in result:
                await present_question(update, context, result["generated_question"], active_session.id)
            else:
                await query.edit_message_text(
                    "📚 Готовим для вас следующий вопрос...",
                    reply_markup=get_main_menu_keyboard()
                )
        
    except Exception as e:
        logging.error(f"❌ Ошибка продолжения урока: {e}")


async def present_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question_data: dict, session_id: int):
    """Представление вопроса пользователю."""
    try:
        question_text = question_data.get("question", "")
        options = question_data.get("options", [])
        difficulty = question_data.get("difficulty", 1)
        topic = question_data.get("topic", "")
        
        # Формирование сообщения с вопросом
        message_text = f"""
🎯 <b>Вопрос ({difficulty} уровень)</b>
📚 <i>{topic}</i>

❓ <b>{question_text}</b>

Выберите правильный ответ:
        """
        
        # Сохранение данных вопроса в контексте
        context.user_data['current_question'] = question_data
        context.user_data['session_id'] = session_id
        
        # Создание клавиатуры с вариантами ответов
        # Используем временный ID вопроса
        temp_question_id = f"temp_{session_id}_{random.randint(1000, 9999)}"
        keyboard = get_answer_keyboard(temp_question_id, options)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=message_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                text=message_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
    except Exception as e:
        logging.error(f"❌ Ошибка представления вопроса: {e}")


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ответа на вопрос."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Извлечение данных из callback_data
        callback_parts = query.data.split('_')
        if len(callback_parts) < 3:
            return
        
        answer_index = int(callback_parts[-1])
        
        # Получение данных вопроса из контекста
        question_data = context.user_data.get('current_question')
        session_id = context.user_data.get('session_id')
        
        if not question_data:
            await query.edit_message_text(
                "❌ Данные вопроса не найдены",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Получение пользователя
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            return
        
        # Обработка ответа через AI-агента
        learning_graph = context.application.bot_data.get('learning_graph')
        if learning_graph:
            result = await learning_graph.process_answer(
                user_id=user.id,
                question_id=0,  # Для сгенерированных вопросов
                answer=str(answer_index)
            )
            
            # Получение результата оценки
            is_correct = result.get('is_correct', False)
            feedback = result.get('feedback', '')
            
            # Отправка соответствующего стикера
            if is_correct:
                user_context = learning_graph.get_user_context(user.id)
                if user_context and user_context.consecutive_correct == 1:
                    sticker = Stickers.FIRST_CORRECT
                else:
                    sticker = Stickers.SUBSEQUENT_CORRECT
            else:
                user_context = learning_graph.get_user_context(user.id)
                if user_context and user_context.consecutive_incorrect == 1:
                    sticker = Stickers.FIRST_INCORRECT
                else:
                    sticker = Stickers.SUBSEQUENT_INCORRECT
            
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=sticker
            )
            
            # Сохранение попытки ответа
            progress_service = ProgressService()
            await progress_service.record_question_attempt(
                user_id=user.id,
                question_id=None,  # Для сгенерированных вопросов
                user_answer=str(answer_index),
                is_correct=is_correct,
                session_id=session_id
            )
            
            # Отправка обратной связи
            await query.edit_message_text(
                text=feedback,
                parse_mode='HTML'
            )
            
            # Проверка завершения урока
            completion_data = result.get('completion_data')
            if completion_data:
                await handle_lesson_completion(update, context, completion_data)
            else:
                # Генерация следующего вопроса
                await generate_next_question(update, context, user.id, session_id)
        
    except Exception as e:
        logging.error(f"❌ Ошибка обработки ответа: {e}")


async def handle_lesson_completion(update: Update, context: ContextTypes.DEFAULT_TYPE, completion_data: dict):
    """Обработка завершения урока."""
    try:
        lesson_passed = completion_data.get('lesson_passed', False)
        success_rate = completion_data.get('success_rate', 0)
        
        if lesson_passed:
            # Отправка стикера успешного завершения
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=Stickers.LESSON_COMPLETED
            )
            
            completion_message = f"""
🎉 <b>Урок успешно завершен!</b>

📊 <b>Ваши результаты:</b>
• Успешность: {success_rate:.1f}%
• Вопросов отвечено: {completion_data.get('questions_answered', 0)}
• Правильных ответов: {completion_data.get('correct_answers', 0)}

🎯 <b>Уровень сложности:</b> {completion_data.get('final_difficulty', 1)}

Продолжить обучение или вернуться в меню?
            """
        else:
            # Отправка стикера недостаточного результата
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=Stickers.INSUFFICIENT_SCORE
            )
            
            completion_message = f"""
📚 <b>Рекомендуется повторение</b>

📊 <b>Ваши результаты:</b>
• Успешность: {success_rate:.1f}%
• Требуется: 80%+

💡 <b>Рекомендации:</b>
• Повторите материал
• Задайте вопросы AI-ассистенту
• Попробуйте еще раз

Хотите повторить урок или изучить материал?
            """
        
        # Обновление прогресса в базе данных
        user = await get_user_by_telegram_id(update.effective_user.id)
        if user:
            progress_service = ProgressService()
            # Здесь нужно получить lesson_id из контекста
            # Для демонстрации используем None
            await progress_service.update_lesson_progress(
                user_id=user.id,
                lesson_id=1,  # Временно, нужно получать из контекста
                completion_percentage=success_rate,
                status="completed" if lesson_passed else "in_progress"
            )
        
        from bot.keyboards.main_menu import get_learning_menu_keyboard
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=completion_message,
            reply_markup=get_learning_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка завершения урока: {e}")


async def generate_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, session_id: int):
    """Генерация следующего вопроса."""
    try:
        learning_graph = context.application.bot_data.get('learning_graph')
        if not learning_graph:
            return
        
        # Запрос следующего вопроса от AI-агента
        result = await learning_graph.start_learning_session(user_id)
        
        if "generated_question" in result:
            # Небольшая задержка для лучшего UX
            import asyncio
            await asyncio.sleep(2)
            
            await present_question(update, context, result["generated_question"], session_id)
        elif result.get('completion_data'):
            await handle_lesson_completion(update, context, result['completion_data'])
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📚 Готовим следующий вопрос...",
                reply_markup=get_main_menu_keyboard()
            )
        
    except Exception as e:
        logging.error(f"❌ Ошибка генерации следующего вопроса: {e}")


async def handle_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик запроса подсказки."""
    query = update.callback_query
    await query.answer()
    
    try:
        question_data = context.user_data.get('current_question')
        if not question_data:
            await query.answer("❌ Данные вопроса не найдены")
            return
        
        hint_text = f"""
💡 <b>Подсказка</b>

{question_data.get('explanation', 'Подсказка недоступна')}

Попробуйте ответить еще раз!
        """
        
        await query.answer(hint_text, show_alert=True)
        
    except Exception as e:
        logging.error(f"❌ Ошибка показа подсказки: {e}")


async def handle_skip_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик пропуска вопроса."""
    query = update.callback_query
    await query.answer()
    
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            return
        
        session_id = context.user_data.get('session_id')
        
        # Записываем пропуск как неправильный ответ
        progress_service = ProgressService()
        await progress_service.record_question_attempt(
            user_id=user.id,
            question_id=None,
            user_answer="skipped",
            is_correct=False,
            session_id=session_id
        )
        
        await query.edit_message_text(
            "⏭️ Вопрос пропущен. Переходим к следующему...",
        )
        
        # Генерация следующего вопроса
        await generate_next_question(update, context, user.id, session_id)
        
    except Exception as e:
        logging.error(f"❌ Ошибка пропуска вопроса: {e}")


async def handle_restart_learning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик перезапуска обучения."""
    query = update.callback_query
    await query.answer()
    
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            return
        
        # Очистка контекста пользователя в AI-агенте
        learning_graph = context.application.bot_data.get('learning_graph')
        if learning_graph:
            learning_graph.clear_user_context(user.id)
        
        # Завершение активных сессий
        user_service = UserService()
        active_session = await user_service.get_active_session(user.id)
        if active_session:
            await user_service.update_session_state(active_session.id, "abandoned")
        
        # Очистка контекста бота
        context.user_data.clear()
        
        # Запуск нового обучения
        await handle_start_learning(update, context)
        
    except Exception as e:
        logging.error(f"❌ Ошибка перезапуска обучения: {e}")


async def handle_select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора темы для изучения."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Получение доступных тем
        from database.database import db_manager
        from database.models import Topic
        from sqlalchemy import select
        
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(Topic)
                .where(Topic.is_active == True)
                .order_by(Topic.order_index)
            )
            topics = result.scalars().all()
        
        if not topics:
            await query.edit_message_text(
                "📚 Темы для изучения пока недоступны",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Формирование списка тем
        topics_text = "📚 <b>Выберите тему для изучения:</b>\n\n"
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = []
        
        for topic in topics:
            difficulty_stars = "⭐" * topic.difficulty_level
            topics_text += f"{difficulty_stars} <b>{topic.title}</b>\n"
            topics_text += f"   <i>{topic.description}</i>\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{difficulty_stars} {topic.title}",
                    callback_data=f"topic_{topic.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
        
        await query.edit_message_text(
            text=topics_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка выбора темы: {e}")


async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора конкретной темы."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Извлечение ID темы
        topic_id = int(query.data.split('_')[1])
        
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            return
        
        # Запуск обучения по выбранной теме
        learning_graph = context.application.bot_data.get('learning_graph')
        if learning_graph:
            result = await learning_graph.start_learning_session(user.id, topic_id)
            
            # Создание сессии
            user_service = UserService()
            session = await user_service.create_learning_session(user.id, topic_id)
            
            if "generated_question" in result:
                await present_question(update, context, result["generated_question"], session.id)
            else:
                await query.edit_message_text(
                    f"🎓 Начинаем изучение темы!\n\nПодготавливаем персональные вопросы...",
                    reply_markup=get_main_menu_keyboard()
                )
        
    except Exception as e:
        logging.error(f"❌ Ошибка выбора темы: {e}")


def register_lesson_handlers(application):
    """Регистрация обработчиков уроков."""
    # Основные действия с обучением
    application.add_handler(CallbackQueryHandler(handle_start_learning, pattern="^start_learning$"))
    application.add_handler(CallbackQueryHandler(handle_continue_lesson, pattern="^continue_lesson$"))
    application.add_handler(CallbackQueryHandler(handle_restart_learning, pattern="^restart_learning$"))
    
    # Выбор темы
    application.add_handler(CallbackQueryHandler(handle_select_topic, pattern="^select_topic$"))
    application.add_handler(CallbackQueryHandler(handle_topic_selection, pattern=r"^topic_\d+$"))
    
    # Ответы на вопросы
    application.add_handler(CallbackQueryHandler(handle_answer, pattern=r"^answer_.*_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_hint, pattern="^hint_.*"))
    application.add_handler(CallbackQueryHandler(handle_skip_question, pattern="^skip_.*"))