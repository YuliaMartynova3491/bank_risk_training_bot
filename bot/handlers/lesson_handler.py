"""
Обработчики уроков и обучения AI-агента.
"""

import logging
import random
import asyncio
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from bot.keyboards.main_menu import get_main_menu_keyboard
from config.settings import Stickers

try:
    from database.database import get_user_by_telegram_id, db_manager
    from services.user_service import UserService
    from services.progress_service import ProgressService
    DATABASE_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ База данных недоступна для lesson_handler")
    DATABASE_AVAILABLE = False


async def handle_start_learning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик начала обучения."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Callback query error: {e}")
    
    try:
        # Сброс счетчиков при начале нового урока
        context.user_data['questions_answered'] = 0
        context.user_data['correct_answers'] = 0
        
        await show_theory(update, context)
    except Exception as e:
        logging.error(f"❌ Ошибка начала обучения: {e}")
        await query.edit_message_text(
            "😔 Произошла ошибка при запуске обучения.",
            reply_markup=get_main_menu_keyboard()
        )


async def show_theory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ теоретической части на основе уровня пользователя."""
    
    # Получаем уровень пользователя
    user_level = 1
    if DATABASE_AVAILABLE:
        try:
            user = await get_user_by_telegram_id(update.effective_user.id)
            if user:
                user_level = user.current_difficulty_level
        except Exception as e:
            logging.warning(f"⚠️ Ошибка получения уровня пользователя: {e}")
    
    # Генерируем теорию в зависимости от уровня
    theory_text = generate_theory_for_level(user_level)
    
    keyboard = [
        [InlineKeyboardButton("✅ Понятно, к вопросам!", callback_data="start_questions")],
        [InlineKeyboardButton("📖 Перечитать", callback_data="start_learning")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(
        text=theory_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def show_theory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ теоретической части, сгенерированной AI на основе уровня пользователя."""
    
    # Получаем уровень пользователя и анализируем его прогресс
    user_level = 1
    user_progress = None
    
    if DATABASE_AVAILABLE:
        try:
            user = await get_user_by_telegram_id(update.effective_user.id)
            if user:
                user_level = user.current_difficulty_level
                
                # Получаем прогресс пользователя для анализа
                progress_service = ProgressService()
                user_progress = await get_user_progress_for_theory(user.id)
                
        except Exception as e:
            logging.warning(f"⚠️ Ошибка получения уровня пользователя: {e}")
    
    # Показываем сообщение о генерации теории
    await update.callback_query.edit_message_text(
        "🤖 <b>Анализируем ваш уровень знаний...</b>\n\n⏳ AI генерирует персональную теорию на основе вашего прогресса...",
        parse_mode='HTML'
    )
    
    # Генерируем теорию через AI
    theory_text = await generate_theory_with_ai(update, context, user_level, user_progress)
    
    if not theory_text:
        # Fallback на статичную теорию если AI недоступен
        theory_text = generate_fallback_theory_for_level(user_level)
    
    keyboard = [
        [InlineKeyboardButton("✅ Понятно, к вопросам!", callback_data="start_questions")],
        [InlineKeyboardButton("📖 Перечитать", callback_data="start_learning")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(
        text=theory_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def get_user_progress_for_theory(user_id: int) -> dict:
    """Получение прогресса пользователя для генерации теории."""
    try:
        if not DATABASE_AVAILABLE:
            return {}
        
        async with db_manager.get_session() as session:
            from database.models import QuestionAttempt
            from sqlalchemy import select, func, desc
            
            # Последние попытки ответов
            recent_attempts = await session.execute(
                select(QuestionAttempt)
                .where(QuestionAttempt.user_id == user_id)
                .order_by(desc(QuestionAttempt.created_at))
                .limit(10)
            )
            
            attempts = recent_attempts.scalars().all()
            
            # Анализируем слабые места
            weak_topics = []
            strong_topics = []
            
            # Здесь можно добавить более сложную логику анализа
            # пока возвращаем базовую информацию
            
            total_questions = len(attempts)
            correct_answers = sum(1 for attempt in attempts if attempt.is_correct)
            accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            return {
                'total_questions': total_questions,
                'accuracy': accuracy,
                'weak_topics': weak_topics,
                'strong_topics': strong_topics,
                'recent_performance': 'good' if accuracy > 70 else 'needs_improvement'
            }
            
    except Exception as e:
        logging.error(f"❌ Ошибка получения прогресса для теории: {e}")
        return {}


async def generate_theory_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE, user_level: int, user_progress: dict) -> str:
    """Генерация теории через AI на основе уровня и прогресса пользователя."""
    try:
        # Получаем AI-компоненты
        learning_graph = context.application.bot_data.get('learning_graph')
        knowledge_base = context.application.bot_data.get('knowledge_base')
        
        if not learning_graph or not learning_graph.llm:
            logging.warning("⚠️ AI компоненты недоступны для генерации теории")
            return None
        
        # Получаем контекст из базы знаний
        context_query = get_context_query_for_level(user_level)
        context_docs = []
        
        if knowledge_base:
            try:
                docs = await knowledge_base.search(context_query, limit=3)
                context_docs = [doc.page_content for doc in docs] if docs else []
            except Exception as e:
                logging.warning(f"⚠️ Ошибка поиска в базе знаний: {e}")
        
        # Формируем промпт для генерации теории
        theory_prompt = create_theory_prompt(user_level, user_progress, context_docs)
        
        # Генерируем теорию через LLM
        from langchain_core.messages import HumanMessage
        response = await learning_graph.llm.ainvoke([HumanMessage(content=theory_prompt)])
        
        if response and response.content:
            theory_text = response.content.strip()
            
            # Добавляем форматирование если его нет
            if not theory_text.startswith('📚'):
                theory_text = f"📚 <b>Персональный урок (уровень {user_level})</b>\n\n{theory_text}"
            
            logging.info(f"✅ Сгенерирована персональная теория для пользователя уровня {user_level}")
            return theory_text
        
    except Exception as e:
        logging.error(f"❌ Ошибка генерации теории через AI: {e}")
    
    return None


def get_context_query_for_level(level: int) -> str:
    """Получение поискового запроса для контекста теории."""
    level_queries = {
        1: "основы управления рисками непрерывности RTO MTPD определения",
        2: "типы угроз банковские риски техногенные природные социальные",
        3: "оценка рисков анализ воздействия BIA методы процедуры",
        4: "стратегии управления рисками планирование непрерывности",
        5: "регулирование банк россии требования стандарты комплаенс"
    }
    return level_queries.get(level, "управление рисками непрерывности банк")


def create_theory_prompt(user_level: int, user_progress: dict, context_docs: list) -> str:
    """Создание промпта для генерации персональной теории."""
    
    # Анализ прогресса пользователя
    progress_analysis = ""
    if user_progress:
        accuracy = user_progress.get('accuracy', 0)
        total_questions = user_progress.get('total_questions', 0)
        
        if total_questions > 0:
            if accuracy > 80:
                progress_analysis = f"Пользователь демонстрирует высокие результаты (точность {accuracy:.1f}%). Можно давать более сложный материал."
            elif accuracy > 60:
                progress_analysis = f"Пользователь показывает средние результаты (точность {accuracy:.1f}%). Нужен баланс теории и практики."
            else:
                progress_analysis = f"Пользователь испытывает трудности (точность {accuracy:.1f}%). Требуется более детальное объяснение основ."
        else:
            progress_analysis = "Новый пользователь. Начинаем с основ."
    else:
        progress_analysis = "Данные о прогрессе недоступны. Используем стандартный подход для уровня."
    
    # Контекст из базы знаний
    context_text = "\n\n".join(context_docs[:2]) if context_docs else "Базовая информация о управлении рисками непрерывности."
    
    level_descriptions = {
        1: "базовые понятия и определения (RTO, MTPD, критически важные процессы)",
        2: "классификацию угроз и их характеристики", 
        3: "методы оценки рисков и анализа воздействия на бизнес",
        4: "стратегии управления рисками и планирование непрерывности",
        5: "регулятивные требования и комплексные сценарии"
    }
    
    return f"""
Создай персональный урок по управлению рисками непрерывности деятельности банка для пользователя уровня {user_level}.

АНАЛИЗ ПОЛЬЗОВАТЕЛЯ:
{progress_analysis}

УРОВЕНЬ СЛОЖНОСТИ: {user_level}/5
ТЕМА УРОКА: {level_descriptions.get(user_level, "общие вопросы")}

КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:
{context_text[:1500]}

ТРЕБОВАНИЯ К УРОКУ:
1. Адаптируй сложность под уровень пользователя
2. Учитывай его прогресс и результаты
3. Структурируй материал логично и понятно
4. Используй конкретные примеры из банковской практики
5. Добавь эмодзи для лучшего восприятия
6. Объем: 300-500 слов

СТРУКТУРА УРОКА:
- Заголовок с номером урока и темой
- Цель урока
- Основные понятия или процедуры (2-4 пункта)
- Практические примеры
- Заключение с мотивацией к изучению

ВАЖНО: 
- Если пользователь показывает высокие результаты - добавь более сложные концепции
- Если низкие результаты - сосредоточься на основах и простых объяснениях
- Используй HTML теги: <b>жирный</b>, <i>курсив</i>

Создай именно персональный урок, а не общую теорию!
    """


def generate_fallback_theory_for_level(level: int) -> str:
    """Fallback генерация статичной теории если AI недоступен."""
    
    fallback_theories = {
        1: """
📚 <b>Урок 1: Основы управления рисками непрерывности</b>

🎯 <b>Цель урока:</b>
Изучить базовые понятия в области управления рисками непрерывности деятельности банка.

💡 <b>Основные понятия:</b>

<b>🔹 Риск нарушения непрерывности</b> - вероятность событий, нарушающих операционную устойчивость банка.

<b>🔹 RTO</b> - целевое время восстановления процесса.

<b>🔹 MTPD</b> - максимально допустимый период простоя.

✅ Готовы проверить понимание основ?
        """,
        
        2: """
📚 <b>Урок 2: Типы угроз</b>

🎯 <b>Цель урока:</b>
Изучить классификацию угроз, влияющих на непрерывность банка.

🚨 <b>Основные типы угроз:</b>

<b>🔥 Техногенные:</b> пожары, аварии оборудования
<b>🌪️ Природные:</b> стихийные бедствия
<b>👥 Социальные:</b> забастовки, беспорядки

✅ Готовы изучить типы угроз подробнее?
        """,
        
        3: """
📚 <b>Урок 3: Оценка рисков</b>

🎯 <b>Цель урока:</b>
Изучить методы оценки рисков и анализа воздействия.

📊 <b>Этапы оценки:</b>

<b>🔍 Идентификация:</b> выявление угроз
<b>📈 Анализ:</b> оценка вероятности и воздействия
<b>⚖️ Оценка:</b> принятие решений по управлению

✅ Готовы изучить методы оценки?
        """,
        
        4: """
📚 <b>Урок 4: Стратегии управления</b>

🎯 <b>Цель урока:</b>
Изучить стратегии управления рисками и планирование.

🛡️ <b>Стратегии:</b>

<b>✅ Принятие:</b> осознанное принятие риска
<b>🔄 Снижение:</b> внедрение контрольных мер
<b>📤 Передача:</b> страхование, аутсорсинг

✅ Готовы изучить стратегии управления?
        """,
        
        5: """
📚 <b>Урок 5: Регулирование</b>

🎯 <b>Цель урока:</b>
Изучить регулятивные требования и сложные сценарии.

📜 <b>Ключевые аспекты:</b>

<b>🏛️ Требования ЦБ:</b> нормативы и стандарты
<b>🌍 Международные стандарты:</b> ISO, Basel
<b>⚡ Комплексные сценарии:</b> каскадные события

✅ Готовы к экспертному уровню?
        """
    }
    
    return fallback_theories.get(level, fallback_theories[1])


async def handle_start_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик начала вопросов после теории."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Callback query error: {e}")
    
    try:
        # Показываем загрузку
        await query.edit_message_text(
            "🤖 <b>Подготовка персонального вопроса...</b>\n\n⏳ Анализируем ваш уровень и генерируем вопрос...",
            parse_mode='HTML'
        )
        
        # Получаем пользователя
        user = None
        if DATABASE_AVAILABLE:
            try:
                user = await get_user_by_telegram_id(update.effective_user.id)
            except Exception as e:
                logging.warning(f"⚠️ Ошибка получения пользователя: {e}")
        
        # Создаем сессию
        session_id = await create_learning_session(user)
        context.user_data['session_id'] = session_id
        
        # Генерируем первый вопрос
        await generate_and_show_question(update, context, user)
        
    except Exception as e:
        logging.error(f"❌ Ошибка запуска вопросов: {e}")
        await query.edit_message_text(
            "😔 Ошибка при запуске вопросов.",
            reply_markup=get_main_menu_keyboard()
        )


async def create_learning_session(user) -> int:
    """Создание сессии обучения."""
    if DATABASE_AVAILABLE and user:
        try:
            user_service = UserService()
            session = await user_service.create_learning_session(user.id)
            return session.id if session else None
        except Exception as e:
            logging.warning(f"⚠️ Не удалось создать сессию: {e}")
    return None


async def generate_and_show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user, is_edit: bool = True):
    """Генерация и показ вопроса."""
    try:
        # Получаем AI-агент
        learning_graph = context.application.bot_data.get('learning_graph')
        if not learning_graph:
            await update.callback_query.edit_message_text(
                "😔 AI-агент временно недоступен.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Получаем актуальный уровень пользователя
        user_telegram_id = update.effective_user.id
        current_difficulty = context.user_data.get('current_difficulty')
        
        # Если нет в контексте, получаем из БД
        if not current_difficulty and DATABASE_AVAILABLE:
            try:
                progress_service = ProgressService()
                question_params = await progress_service.get_personalized_question_params(user_telegram_id)
                current_difficulty = question_params.get('difficulty', 1)
                focus_topics = question_params.get('focus_topics', [])
                
                # Сохраняем в контексте
                context.user_data['current_difficulty'] = current_difficulty
            except Exception as e:
                logging.warning(f"⚠️ Ошибка получения параметров: {e}")
                current_difficulty = 1
                focus_topics = ["basic_concepts"]
        else:
            current_difficulty = current_difficulty or 1
            focus_topics = ["basic_concepts"] if current_difficulty <= 2 else ["risk_assessment"]
        
        # Генерируем вопрос с учетом актуального уровня
        result = await learning_graph.start_learning_session(
            user_telegram_id, 
            difficulty_override=current_difficulty,
            focus_topics=focus_topics
        )
        
        if "error" in result:
            await update.callback_query.edit_message_text(
                f"😔 Ошибка: {result['error']}",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        if "generated_question" not in result:
            await update.callback_query.edit_message_text(
                "😔 Не удалось сгенерировать вопрос.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Показываем вопрос
        await show_question(update, context, result["generated_question"], is_edit)
        
    except Exception as e:
        logging.error(f"❌ Ошибка генерации вопроса: {e}")
        await update.callback_query.edit_message_text(
            "😔 Ошибка генерации вопроса.",
            reply_markup=get_main_menu_keyboard()
        )


async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question_data: Dict[str, Any], is_edit: bool = True):
    """Показ вопроса пользователю."""
    try:
        question_text = question_data.get("question", "")
        options = question_data.get("options", [])
        difficulty = question_data.get("difficulty", 1)
        topic = question_data.get("topic", "Общие вопросы")
        
        # Сохраняем данные вопроса
        context.user_data['current_question'] = question_data
        
        # Формируем текст
        message_text = f"""
🎯 <b>Вопрос (уровень {difficulty}/5)</b>
📚 <i>{topic}</i>

❓ <b>{question_text}</b>

Выберите правильный ответ:
        """
        
        # Создаем клавиатуру
        keyboard = []
        for i, option in enumerate(options):
            keyboard.append([
                InlineKeyboardButton(
                    f"{chr(65 + i)}. {option}", 
                    callback_data=f"answer_{i}"
                )
            ])
        
        # Добавляем кнопки действий
        keyboard.append([
            InlineKeyboardButton("💡 Подсказка", callback_data="hint"),
            InlineKeyboardButton("⏭️ Пропустить", callback_data="skip")
        ])
        keyboard.append([
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if is_edit and update.callback_query:
            await update.callback_query.edit_message_text(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
    except Exception as e:
        logging.error(f"❌ Ошибка показа вопроса: {e}")


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ответа на вопрос."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Callback query error: {e}")
    
    try:
        # Получаем индекс ответа
        answer_index = int(query.data.split('_')[1])
        
        # Получаем данные вопроса
        question_data = context.user_data.get('current_question')
        if not question_data:
            await query.edit_message_text(
                "❌ Данные вопроса не найдены",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Проверяем правильность ответа
        correct_answer_index = question_data.get("correct_answer", 0)
        is_correct = answer_index == correct_answer_index
        current_difficulty = question_data.get("difficulty", 1)
        
        # Получение пользователя
        user = None
        if DATABASE_AVAILABLE:
            try:
                user = await get_user_by_telegram_id(update.effective_user.id)
            except Exception as e:
                logging.warning(f"⚠️ Ошибка получения пользователя: {e}")
        
        # Отправка соответствующего стикера
        sticker = Stickers.FIRST_CORRECT if is_correct else Stickers.FIRST_INCORRECT
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id,
            sticker=sticker
        )
        
        # Обрабатываем ответ и получаем обратную связь
        feedback = await process_answer_and_get_feedback(
            update, context, is_correct, answer_index, question_data, current_difficulty, user
        )
        
        # Проверяем завершение урока
        if await check_lesson_completion(update, context, is_correct, feedback):
            return  # Урок завершен, выходим
        
        # Отправляем обратную связь с кнопками
        keyboard = [
            [
                InlineKeyboardButton("➡️ Следующий вопрос", callback_data="next_question"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]
        ]
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=feedback,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка обработки ответа: {e}")


async def process_answer_and_get_feedback(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    is_correct: bool, 
    answer_index: int, 
    question_data: Dict[str, Any], 
    current_difficulty: int,
    user
) -> str:
    """Обработка ответа и генерация обратной связи."""
    
    user_telegram_id = update.effective_user.id
    session_id = context.user_data.get('session_id')
    
    # Адаптивная логика
    if DATABASE_AVAILABLE:
        try:
            progress_service = ProgressService()
            
            # Рассчитываем новый уровень (используем telegram_id)
            new_difficulty, reason = await progress_service.calculate_next_difficulty(
                user_id=user_telegram_id,
                current_answer_correct=is_correct,
                current_difficulty=current_difficulty,
                session_id=session_id
            )
            
            # Обновляем уровень пользователя (используем telegram_id)
            await progress_service.update_user_difficulty_level(user_telegram_id, new_difficulty, reason)
            
            # Получаем правильный ответ
            correct_option = ""
            if not is_correct:
                options = question_data.get('options', [])
                correct_answer_index = question_data.get("correct_answer", 0)
                if correct_answer_index < len(options):
                    correct_option = options[correct_answer_index]
            
            explanation = question_data.get('explanation', '')
            
            # Генерируем адаптивную обратную связь
            feedback = await progress_service.get_adaptive_feedback(
                is_correct=is_correct,
                old_level=current_difficulty,
                new_level=new_difficulty,
                explanation=explanation,
                correct_answer=correct_option
            )
            
            # Сохраняем новый уровень в контексте для следующего вопроса
            context.user_data['current_difficulty'] = new_difficulty
            
            # Записываем попытку (используем внутренний ID для записи в таблицу попыток)
            if user:
                await progress_service.record_question_attempt(
                    user_id=user.id,
                    question_id=None,
                    user_answer=str(answer_index),
                    is_correct=is_correct,
                    session_id=session_id
                )
            
            return feedback
            
        except Exception as e:
            logging.error(f"❌ Ошибка адаптивной логики: {e}")
    
    # Простая обратная связь без адаптивности
    if is_correct:
        return f"✅ <b>Правильно!</b>\n\n💡 {question_data.get('explanation', '')}"
    else:
        options = question_data.get('options', [])
        correct_answer_index = question_data.get("correct_answer", 0)
        correct_option = options[correct_answer_index] if correct_answer_index < len(options) else "Неизвестно"
        return f"❌ <b>Неправильно.</b>\n\n🎯 <b>Правильный ответ:</b> {correct_option}\n\n💡 {question_data.get('explanation', '')}"


async def check_lesson_completion(update: Update, context: ContextTypes.DEFAULT_TYPE, is_correct: bool, feedback: str) -> bool:
    """Проверка завершения урока."""
    
    # Счетчик вопросов для завершения урока
    questions_answered = context.user_data.get('questions_answered', 0) + 1
    correct_answers = context.user_data.get('correct_answers', 0)
    if is_correct:
        correct_answers += 1
    
    context.user_data['questions_answered'] = questions_answered
    context.user_data['correct_answers'] = correct_answers
    
    # Проверяем завершение урока (4 вопроса или высокая точность)
    if questions_answered >= 4:
        accuracy = correct_answers / questions_answered
        if accuracy >= 0.75:  # 75% правильных ответов
            # Завершаем урок и переходим к следующему
            completion_data = {
                'lesson_passed': True,
                'success_rate': accuracy * 100,
                'questions_answered': questions_answered,
                'correct_answers': correct_answers
            }
            
            # Добавляем кнопку завершения урока вместо следующего вопроса
            keyboard = [
                [InlineKeyboardButton("✅ Завершить урок", callback_data="complete_lesson")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            
            feedback += f"\n\n🎉 <b>Урок завершен!</b>\n📊 Точность: {accuracy:.1%}\n✅ Ответов: {questions_answered}/{correct_answers}"
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=feedback,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            return True
    
    return False


async def handle_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик следующего вопроса с адаптивной сложностью."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Callback query error: {e}")
    
    try:
        # Используем telegram_id везде
        user_telegram_id = update.effective_user.id
        session_id = context.user_data.get('session_id')
        
        # Получаем текущий уровень из контекста ИЛИ из БД
        current_difficulty = context.user_data.get('current_difficulty')
        
        if DATABASE_AVAILABLE and not current_difficulty:
            # Если нет в контексте, получаем из БД
            progress_service = ProgressService()
            question_params = await progress_service.get_personalized_question_params(user_telegram_id)
            current_difficulty = question_params.get('difficulty', 1)
            focus_topics = question_params.get('focus_topics', [])
        else:
            current_difficulty = current_difficulty or 1
            focus_topics = ["basic_concepts"] if current_difficulty == 1 else ["risk_assessment"]
        
        # Показываем загрузку с информацией о уровне
        loading_text = f"""
🤖 <b>Генерируем следующий вопрос...</b>

📊 <b>Уровень сложности:</b> {current_difficulty}/5
🎯 <b>Фокус:</b> {', '.join(focus_topics[:2]) if focus_topics else 'общие вопросы'}

⏳ AI адаптирует вопрос под ваши знания...
        """
        
        await query.edit_message_text(
            text=loading_text,
            parse_mode='HTML'
        )
        
        # Получаем пользователя для внутренних операций
        user = None
        if DATABASE_AVAILABLE:
            try:
                user = await get_user_by_telegram_id(user_telegram_id)
            except Exception as e:
                logging.warning(f"⚠️ Ошибка получения пользователя: {e}")
        
        # Небольшая задержка для UX
        await asyncio.sleep(1)
        
        # Генерируем и показываем следующий вопрос с учетом текущего уровня
        await generate_and_show_question(update, context, user, is_edit=True)
        
    except Exception as e:
        logging.error(f"❌ Ошибка следующего вопроса: {e}")
        await query.edit_message_text(
            "😔 Ошибка генерации следующего вопроса.",
            reply_markup=get_main_menu_keyboard()
        )


async def handle_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик подсказки."""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"⚠️ Callback query error: {e}")
    
    try:
        question_data = context.user_data.get('current_question')
        if not question_data:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Данные вопроса не найдены"
            )
            return
        
        # Подсказка, а не правильный ответ
        explanation = question_data.get('explanation', 'Подсказка недоступна')
        question_text = question_data.get('question', '')
        
        # Создаем подсказку на основе объяснения, но не раскрываем ответ
        hint_text = ""
        if "RTO" in question_text:
            hint_text = "💡 Подумайте о времени и восстановлении процессов"
        elif "MTPD" in question_text:
            hint_text = "💡 Речь идет о максимально допустимом периоде"
        elif "техногенн" in question_text.lower():
            hint_text = "💡 Подумайте о деятельности человека и технических процессах"
        elif "BIA" in question_text or "воздействие на бизнес" in question_text.lower():
            hint_text = "💡 Анализ начинается с определения самого важного"
        elif "непрерывност" in question_text.lower():
            hint_text = "💡 Подумайте о том, что помогает быстро восстановить работу"
        else:
            # Общая подсказка на основе первых слов объяснения
            hint_words = explanation.split()[:10]
            hint_text = f"💡 Ключевые понятия: {' '.join(hint_words)}..."
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"💡 <b>Подсказка:</b>\n\n{hint_text}",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка показа подсказки: {e}")


async def handle_skip_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик пропуска вопроса."""
    query = update.callback_query
    
    try:
        await query.answer("⏭️ Вопрос пропущен")
    except Exception as e:
        logging.warning(f"⚠️ Callback query error: {e}")
    
    try:
        # Записываем пропуск как неправильный ответ
        if DATABASE_AVAILABLE:
            user = await get_user_by_telegram_id(update.effective_user.id)
            if user:
                session_id = context.user_data.get('session_id')
                progress_service = ProgressService()
                await progress_service.record_question_attempt(
                    user_id=user.id,
                    question_id=None,
                    user_answer="skipped",
                    is_correct=False,
                    session_id=session_id
                )
        
        # Переходим к следующему вопросу
        await handle_next_question(update, context)
        
    except Exception as e:
        logging.error(f"❌ Ошибка пропуска вопроса: {e}")


async def handle_complete_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик завершения урока."""
    query = update.callback_query
    
    try:
        await query.answer("🎉 Урок завершен!")
    except Exception as e:
        logging.warning(f"⚠️ Callback query error: {e}")
    
    try:
        # Сбрасываем счетчики
        context.user_data['questions_answered'] = 0
        context.user_data['correct_answers'] = 0
        
        completion_text = """
🎉 <b>Поздравляем! Урок успешно завершен!</b>

📚 <b>Что дальше?</b>
• Изучить следующую тему
• Повторить пройденный материал  
• Задать вопросы AI-ассистенту
• Посмотреть свой прогресс

💡 <b>Рекомендация:</b> Переходите к следующему уроку для изучения новых тем!
        """
        
        keyboard = [
            [InlineKeyboardButton("📖 Следующий урок", callback_data="start_learning")],
            [InlineKeyboardButton("📊 Мой прогресс", callback_data="show_progress")],
            [InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_question")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=completion_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка завершения урока: {e}")


def register_lesson_handlers(application):
    """Регистрация обработчиков уроков."""
    application.add_handler(CallbackQueryHandler(handle_start_learning, pattern="^start_learning$"))
    application.add_handler(CallbackQueryHandler(handle_start_questions, pattern="^start_questions$"))
    application.add_handler(CallbackQueryHandler(handle_next_question, pattern="^next_question$"))
    application.add_handler(CallbackQueryHandler(handle_complete_lesson, pattern="^complete_lesson$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern=r"^answer_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_hint, pattern="^hint$"))
    application.add_handler(CallbackQueryHandler(handle_skip_question, pattern="^skip$"))