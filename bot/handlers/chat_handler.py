"""
Обработчики чата с AI-ассистентом.
"""

import logging
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, CommandHandler

from database.database import get_user_by_telegram_id
from services.user_service import UserService
from bot.keyboards.main_menu import get_question_menu_keyboard, get_main_menu_keyboard
from ai_agent.rag.knowledge_base import QueryProcessor


# Состояния для ConversationHandler
WAITING_FOR_QUESTION = 1


async def handle_ask_question_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик меню вопросов AI."""
    query = update.callback_query
    await query.answer()
    
    try:
        question_text = """
🤖 <b>AI-Ассистент по рискам непрерывности</b>

Я помогу вам разобраться в методике управления рисками непрерывности деятельности банка.

💡 <b>Примеры вопросов:</b>
• "Что делать при пожаре в офисе?"
• "Как рассчитать время восстановления?"
• "Какие существуют типы угроз?"
• "Что такое RTO и MTPD?"
• "Как проводится оценка риска?"

📝 <b>Просто напишите ваш вопрос в чат!</b>
        """
        
        await query.edit_message_text(
            text=question_text,
            reply_markup=get_question_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в меню вопросов: {e}")


async def handle_new_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик запроса нового вопроса."""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text(
            "❓ <b>Задайте ваш вопрос</b>\n\nНапишите вопрос по управлению рисками непрерывности деятельности банка:",
            parse_mode='HTML'
        )
        
        return WAITING_FOR_QUESTION
        
    except Exception as e:
        logging.error(f"❌ Ошибка запроса нового вопроса: {e}")
        return ConversationHandler.END


async def process_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка вопроса пользователя."""
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
            return ConversationHandler.END
        
        question = update.message.text
        logging.info(f"🤖 Пользователь {user.telegram_id} задал вопрос: {question[:50]}...")
        
        # Индикация набора текста
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Получение компонентов AI
        knowledge_base = context.application.bot_data.get('knowledge_base')
        if not knowledge_base:
            await update.message.reply_text(
                "😔 AI-ассистент временно недоступен. Попробуйте позже.",
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # Обработка вопроса через RAG
        query_processor = QueryProcessor(knowledge_base)
        user_context = {"difficulty": user.current_difficulty_level}
        
        query_result = await query_processor.process_query(question, user_context)
        
        if "error" in query_result:
            await update.message.reply_text(
                f"😔 Ошибка обработки вопроса: {query_result['error']}",
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # Генерация ответа через LLM
        response = await generate_ai_response(question, query_result, context)
        
        # Формирование клавиатуры с дополнительными действиями
        keyboard = [
            [
                InlineKeyboardButton("❓ Еще вопрос", callback_data="new_question"),
                InlineKeyboardButton("🔍 Связанные темы", callback_data=f"related_{hash(question)}")
            ],
            [
                InlineKeyboardButton("👍 Полезно", callback_data=f"helpful_yes_{hash(question)}"),
                InlineKeyboardButton("👎 Не помогло", callback_data=f"helpful_no_{hash(question)}")
            ],
            [
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]
        ]
        
        await update.message.reply_text(
            text=response,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        # Сохранение в историю чата
        user_service = UserService()
        await user_service.save_chat_message(
            user_id=user.id,
            message_type="user",
            content=question
        )
        
        await user_service.save_chat_message(
            user_id=user.id,
            message_type="assistant", 
            content=response,
            context_used=query_result.get("relevant_documents", []),
            confidence_score=query_result.get("confidence", 0)
        )
        
        # Показ связанных вопросов
        suggestions = query_result.get("suggestions", [])
        if suggestions:
            await show_related_questions(update, context, suggestions)
        
        return ConversationHandler.END
        
    except Exception as e:
        logging.error(f"❌ Ошибка обработки вопроса: {e}")
        await update.message.reply_text(
            "😔 Произошла ошибка при обработке вопроса. Попробуйте еще раз.",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END


async def generate_ai_response(question: str, query_result: Dict[str, Any], context: ContextTypes.DEFAULT_TYPE) -> str:
    """Генерация ответа AI на основе результатов RAG."""
    try:
        # Формирование контекста из найденных документов
        relevant_docs = query_result.get("relevant_documents", [])
        context_text = "\n\n".join([
            doc["content"] for doc in relevant_docs[:3]
        ])
        
        # Определение типа вопроса
        query_type = query_result.get("query_type", "general")
        
        # Системный промпт в зависимости от типа вопроса
        system_prompts = {
            "definition": "Дайте четкое определение термина и объясните его значение в контексте банковских рисков.",
            "instruction": "Предоставьте пошаговые инструкции по выполнению действий.",
            "explanation": "Объясните причины и механизмы явления.",
            "calculation": "Объясните формулы и приведите примеры расчетов.",
            "example": "Приведите конкретные примеры и сценарии.",
            "general": "Дайте полный и понятный ответ на вопрос."
        }
        
        system_prompt = f"""
Вы - эксперт по управлению рисками непрерывности деятельности банка.
{system_prompts.get(query_type, system_prompts['general'])}

Используйте предоставленную информацию из методики банка.
Отвечайте четко, профессионально и практично.
Если информации недостаточно, честно об этом скажите.
Используйте HTML-разметку для форматирования (жирный текст, курсив, списки).
        """
        
        user_prompt = f"""
Контекст из методики банка:
{context_text}

Вопрос: {question}

Дайте подробный и практичный ответ на основе методики.
        """
        
        # Получение LLM
        # В реальной реализации здесь был бы вызов LLM API
        # Для демонстрации возвращаем базовый ответ
        
        if not context_text:
            return """
😔 <b>Извините, я не нашел релевантной информации в методике для ответа на ваш вопрос.</b>

💡 <b>Попробуйте:</b>
• Переформулировать вопрос
• Задать более конкретный вопрос
• Обратиться к специалисту по рискам

❓ <b>Могу помочь с вопросами по:</b>
• Типам угроз непрерывности
• Процедурам оценки рисков
• Расчету времени восстановления
• Планам реагирования на инциденты
            """
        
        # Простая обработка на основе найденного контекста
        response = f"""
📚 <b>Ответ на основе методики банка:</b>

{context_text[:800]}{"..." if len(context_text) > 800 else ""}

💡 <b>Рекомендации:</b>
Изучите полную методику для получения детальной информации.
        """
        
        return response
        
    except Exception as e:
        logging.error(f"❌ Ошибка генерации ответа AI: {e}")
        return "😔 Не удалось сгенерировать ответ. Попробуйте переформулировать вопрос."


async def show_related_questions(update: Update, context: ContextTypes.DEFAULT_TYPE, suggestions: List[str]):
    """Показ связанных вопросов."""
    try:
        if not suggestions:
            return
        
        related_text = "🔗 <b>Связанные вопросы:</b>\n\n"
        keyboard = []
        
        for i, suggestion in enumerate(suggestions[:3], 1):
            related_text += f"{i}. {suggestion}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"{i}. {suggestion[:50]}{'...' if len(suggestion) > 50 else ''}",
                    callback_data=f"suggest_{i}_{hash(suggestion)}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=related_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        # Сохранение предложений в контексте
        context.user_data['suggestions'] = suggestions
        
    except Exception as e:
        logging.error(f"❌ Ошибка показа связанных вопросов: {e}")


async def handle_question_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик истории вопросов."""
    query = update.callback_query
    await query.answer()
    
    try:
        user = await get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        # Получение истории чата
        user_service = UserService()
        chat_history = await user_service.get_user_chat_history(user.id, 10)
        
        if not chat_history:
            await query.edit_message_text(
                "📜 <b>История вопросов пуста</b>\n\nВы еще не задавали вопросов AI-ассистенту.",
                reply_markup=get_question_menu_keyboard(),
                parse_mode='HTML'
            )
            return
        
        # Формирование истории
        history_text = "📜 <b>Ваши последние вопросы:</b>\n\n"
        
        user_questions = [msg for msg in chat_history if msg.message_type == "user"]
        
        for i, message in enumerate(user_questions[:5], 1):
            question = message.content
            date = message.created_at.strftime("%d.%m %H:%M")
            history_text += f"{i}. <i>{date}</i>\n"
            history_text += f"   {question[:100]}{'...' if len(question) > 100 else ''}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("❓ Задать новый вопрос", callback_data="new_question")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=history_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка получения истории вопросов: {e}")


async def handle_search_methodology(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик поиска в методике."""
    query = update.callback_query
    await query.answer()
    
    try:
        search_text = """
🔍 <b>Поиск в методике</b>

Введите ключевые слова для поиска в методике управления рисками:

💡 <b>Примеры поисковых запросов:</b>
• "время восстановления"
• "техногенные угрозы"
• "матрица рисков"
• "переоценка"
• "аутсорсинг"

📝 <b>Напишите ваш поисковый запрос:</b>
        """
        
        await query.edit_message_text(
            text=search_text,
            parse_mode='HTML'
        )
        
        # Установка состояния ожидания поискового запроса
        context.user_data['waiting_for_search'] = True
        
    except Exception as e:
        logging.error(f"❌ Ошибка поиска в методике: {e}")


async def handle_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик частых вопросов."""
    query = update.callback_query
    await query.answer()
    
    try:
        faq_data = [
            {
                "question": "Что такое RTO и MTPD?",
                "answer": "RTO - время восстановления процесса, MTPD - максимально допустимый период простоя"
            },
            {
                "question": "Какие типы угроз существуют?",
                "answer": "Техногенные, природные, социальные, геополитические, экономические, биолого-социальные"
            },
            {
                "question": "Как часто проводится переоценка рисков?",
                "answer": "При наступлении триггеров: изменения в процессах, угрозах или окружении"
            },
            {
                "question": "Что делать при пожаре в офисе?",
                "answer": "Активировать план ОНиВД, перевести на удаленную работу, использовать резервные площадки"
            },
            {
                "question": "Как рассчитывается воздействие риска?",
                "answer": "По формуле T_R = T_rec_AC + T_rec_Office + T_move × F_strategy + T_rec_process"
            }
        ]
        
        faq_text = "❓ <b>Часто задаваемые вопросы</b>\n\n"
        keyboard = []
        
        for i, faq in enumerate(faq_data, 1):
            faq_text += f"{i}. <b>{faq['question']}</b>\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"{i}. {faq['question']}",
                    callback_data=f"faq_{i}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("❓ Задать свой вопрос", callback_data="new_question"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
        
        await query.edit_message_text(
            text=faq_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        # Сохранение FAQ в контексте
        context.user_data['faq_data'] = faq_data
        
    except Exception as e:
        logging.error(f"❌ Ошибка показа FAQ: {e}")


async def handle_faq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ответа на FAQ."""
    query = update.callback_query
    await query.answer()
    
    try:
        faq_index = int(query.data.split('_')[1]) - 1
        faq_data = context.user_data.get('faq_data', [])
        
        if faq_index < 0 or faq_index >= len(faq_data):
            await query.answer("❌ Вопрос не найден")
            return
        
        faq = faq_data[faq_index]
        
        answer_text = f"""
❓ <b>{faq['question']}</b>

💡 <b>Ответ:</b>
{faq['answer']}

📚 Для получения более подробной информации задайте развернутый вопрос AI-ассистенту.
        """
        
        keyboard = [
            [
                InlineKeyboardButton("❓ Задать развернутый вопрос", callback_data="new_question"),
                InlineKeyboardButton("🔙 К FAQ", callback_data="faq")
            ],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=answer_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка ответа на FAQ: {e}")


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик обратной связи по ответу."""
    query = update.callback_query
    await query.answer()
    
    try:
        callback_parts = query.data.split('_')
        feedback_type = callback_parts[1]  # yes или no
        question_hash = callback_parts[2]
        
        if feedback_type == "yes":
            await query.answer("👍 Спасибо за обратную связь! Рад, что смог помочь.")
        else:
            await query.answer("👎 Спасибо за обратную связь! Попробуйте переформулировать вопрос или обратитесь к специалисту.")
        
        # В реальной системе здесь была бы запись обратной связи в базу данных
        logging.info(f"📊 Обратная связь: {feedback_type} для вопроса {question_hash}")
        
    except Exception as e:
        logging.error(f"❌ Ошибка обработки обратной связи: {e}")


async def handle_related_topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик связанных тем."""
    query = update.callback_query
    await query.answer()
    
    try:
        suggestions = context.user_data.get('suggestions', [])
        
        if not suggestions:
            await query.answer("❌ Связанные темы не найдены")
            return
        
        related_text = "🔗 <b>Связанные темы и вопросы:</b>\n\n"
        keyboard = []
        
        for i, suggestion in enumerate(suggestions[:5], 1):
            related_text += f"{i}. {suggestion}\n\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"❓ {suggestion[:40]}{'...' if len(suggestion) > 40 else ''}",
                    callback_data=f"ask_suggestion_{i}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("❓ Задать новый вопрос", callback_data="new_question"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
        
        await query.edit_message_text(
            text=related_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка показа связанных тем: {e}")


async def handle_suggested_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик предложенного вопроса."""
    query = update.callback_query
    await query.answer()
    
    try:
        suggestion_index = int(query.data.split('_')[2]) - 1
        suggestions = context.user_data.get('suggestions', [])
        
        if suggestion_index < 0 or suggestion_index >= len(suggestions):
            await query.answer("❌ Вопрос не найден")
            return
        
        suggested_question = suggestions[suggestion_index]
        
        # Имитация отправки вопроса пользователем
        class MockUpdate:
            def __init__(self, text):
                self.message = MockMessage(text)
                self.effective_user = update.effective_user
                self.effective_chat = update.effective_chat
        
        class MockMessage:
            def __init__(self, text):
                self.text = text
        
        mock_update = MockUpdate(suggested_question)
        
        # Обработка предложенного вопроса
        await process_user_question(mock_update, context)
        
    except Exception as e:
        logging.error(f"❌ Ошибка обработки предложенного вопроса: {e}")


async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик поискового запроса."""
    try:
        if not context.user_data.get('waiting_for_search'):
            return
        
        search_query = update.message.text
        context.user_data['waiting_for_search'] = False
        
        # Поиск в базе знаний
        knowledge_base = context.application.bot_data.get('knowledge_base')
        if not knowledge_base:
            await update.message.reply_text(
                "😔 Поиск временно недоступен",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Выполнение поиска
        search_results = await knowledge_base.search(search_query, limit=5)
        
        if not search_results:
            await update.message.reply_text(
                f"🔍 <b>Поиск по запросу:</b> {search_query}\n\n❌ Ничего не найдено.\n\nПопробуйте другие ключевые слова.",
                reply_markup=get_question_menu_keyboard(),
                parse_mode='HTML'
            )
            return
        
        # Формирование результатов поиска
        results_text = f"🔍 <b>Результаты поиска:</b> {search_query}\n\n"
        
        for i, doc in enumerate(search_results[:3], 1):
            content = doc.page_content
            metadata = doc.metadata
            
            # Обрезка длинного содержимого
            if len(content) > 200:
                content = content[:200] + "..."
            
            results_text += f"{i}. <b>{metadata.get('topic', 'Методика')}</b>\n"
            results_text += f"   {content}\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Новый поиск", callback_data="search_methodology"),
                InlineKeyboardButton("❓ Задать вопрос", callback_data="new_question")
            ],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            text=results_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка обработки поискового запроса: {e}")


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена разговора."""
    await update.message.reply_text(
        "❌ Отменено",
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END


def register_chat_handlers(application):
    """Регистрация обработчиков чата с AI."""
    
    # Conversation handler для вопросов (ИСПРАВЛЕН)
    question_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_new_question, pattern="^new_question$")],
    states={
        WAITING_FOR_QUESTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_question),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_conversation, pattern="^main_menu$"),
        CommandHandler("cancel", cancel_conversation)
    ],
    per_message=False,
    per_chat=True,
    per_user=True
)
    
    application.add_handler(question_conversation)
    
    # Обработчики меню вопросов
    application.add_handler(CallbackQueryHandler(handle_ask_question_menu, pattern="^ask_question$"))
    application.add_handler(CallbackQueryHandler(handle_question_history, pattern="^question_history$"))
    application.add_handler(CallbackQueryHandler(handle_search_methodology, pattern="^search_methodology$"))
    application.add_handler(CallbackQueryHandler(handle_faq, pattern="^faq$"))
    
    # Обработчики FAQ
    application.add_handler(CallbackQueryHandler(handle_faq_answer, pattern=r"^faq_\d+$"))
    
    # Обработчики обратной связи
    application.add_handler(CallbackQueryHandler(handle_feedback, pattern="^helpful_(yes|no)_.*"))
    
    # Обработчики связанных тем
    application.add_handler(CallbackQueryHandler(handle_related_topics, pattern="^related_.*"))
    application.add_handler(CallbackQueryHandler(handle_suggested_question, pattern=r"^ask_suggestion_\d+$"))
    
    # Обработчик поисковых запросов (должен быть последним среди MessageHandler)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            handle_search_query
        ),
        group=10  # Низкий приоритет
    )