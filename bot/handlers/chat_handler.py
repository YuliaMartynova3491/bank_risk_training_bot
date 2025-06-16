"""
Обработчики чата с AI-ассистентом.
"""

import logging
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, CommandHandler

try:
    from database.database import get_user_by_telegram_id
    from services.user_service import UserService
    DATABASE_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ База данных недоступна для chat_handler")
    DATABASE_AVAILABLE = False

from bot.keyboards.main_menu import get_question_menu_keyboard, get_main_menu_keyboard

try:
    from ai_agent.rag.knowledge_base import QueryProcessor
    RAG_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ RAG система недоступна")
    RAG_AVAILABLE = False


# Состояния для ConversationHandler
WAITING_FOR_QUESTION = 1


async def handle_ask_question_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик меню вопросов AI."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Не удалось ответить на callback query: {e}")
    
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
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Не удалось ответить на callback query: {e}")
    
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
        # Получение пользователя (если БД доступна)
        user = None
        if DATABASE_AVAILABLE:
            try:
                user = await get_user_by_telegram_id(update.effective_user.id)
                if not user:
                    await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                    return ConversationHandler.END
            except Exception as e:
                logging.warning(f"⚠️ Проблема с получением пользователя: {e}")
        
        question = update.message.text
        logging.info(f"🤖 Пользователь {update.effective_user.id} задал вопрос: {question[:50]}...")
        
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
        if RAG_AVAILABLE:
            query_processor = QueryProcessor(knowledge_base)
            user_context = {"difficulty": user.current_difficulty_level if user else 1}
            
            query_result = await query_processor.process_query(question, user_context)
            
            if "error" in query_result:
                await update.message.reply_text(
                    f"😔 Ошибка обработки вопроса: {query_result['error']}",
                    reply_markup=get_main_menu_keyboard()
                )
                return ConversationHandler.END
        else:
            # Простой поиск без QueryProcessor
            try:
                relevant_docs = await knowledge_base.search(question, limit=3)
                query_result = {
                    "relevant_documents": [
                        {"content": doc.page_content, "metadata": doc.metadata}
                        for doc in relevant_docs
                    ],
                    "confidence": 0.8 if relevant_docs else 0.2,
                    "suggestions": []
                }
            except Exception as e:
                logging.error(f"❌ Ошибка поиска: {e}")
                query_result = {"relevant_documents": [], "confidence": 0, "suggestions": []}
        
        # Генерация ответа через LLM или простой ответ
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
        
        # Сохранение в историю чата (если доступно)
        if DATABASE_AVAILABLE and user:
            try:
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
            except Exception as e:
                logging.warning(f"⚠️ Ошибка сохранения истории: {e}")
        
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
        
        # Получение LLM
        llm = context.application.bot_data.get('llm')
        
        if llm and context_text:
            try:
                # Попытка использовать LLM для генерации ответа
                from ai_agent.llm.prompts.qwen_prompts import QwenPrompts
                
                user_prompt = QwenPrompts.RAG_ASSISTANT.format(
                    context=context_text,
                    question=question
                )
                
                try:
                    from langchain_core.messages import HumanMessage, SystemMessage
                    
                    messages = [
                        SystemMessage(content=QwenPrompts.SYSTEM_EXPERT),
                        HumanMessage(content=user_prompt)
                    ]
                    
                    response = await llm.ainvoke(messages)
                    
                    # Очистка и проверка ответа
                    ai_response = response.content.strip()
                    if len(ai_response) > 50:  # Минимальная длина ответа
                        return ai_response
                    
                except Exception as e:
                    logging.warning(f"⚠️ Ошибка вызова LLM: {e}")
                    
            except ImportError:
                logging.warning("⚠️ Prompts недоступны")
        
        # Фаллбек: простой ответ на основе найденного контекста
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


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена разговора."""
    try:
        if update.message:
            await update.message.reply_text(
                "❌ Отменено",
                reply_markup=get_main_menu_keyboard()
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ Отменено",
                reply_markup=get_main_menu_keyboard()
            )
    except Exception as e:
        logging.error(f"❌ Ошибка отмены разговора: {e}")
    
    return ConversationHandler.END


def register_chat_handlers(application):
    """Регистрация обработчиков чата с AI."""
    
    # ИСПРАВЛЕНО: ConversationHandler без per_message и с правильными fallbacks
    question_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_new_question, pattern="^new_question$")],
        states={
            WAITING_FOR_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_question),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^main_menu$"),
            CallbackQueryHandler(cancel_conversation, pattern="^cancel$"),
            CommandHandler("cancel", cancel_conversation)
        ],
        per_chat=True,
        per_user=True
    )
    
    application.add_handler(question_conversation)
    
    # Обработчики меню вопросов
    application.add_handler(CallbackQueryHandler(handle_ask_question_menu, pattern="^ask_question$"))
    
    # Обработчики обратной связи
    application.add_handler(CallbackQueryHandler(handle_feedback, pattern="^helpful_(yes|no)_.*"))


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик обратной связи по ответу."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Не удалось ответить на callback query: {e}")
    
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