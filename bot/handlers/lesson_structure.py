"""
Структура уроков с теоретической частью.
"""

import logging
from typing import Dict, List, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class LessonStructure:
    """Класс для управления структурой уроков."""
    
    # Теоретические модули
    THEORY_MODULES = {
        1: {  # Уровень 1 - Основы
            "title": "Основы управления рисками непрерывности",
            "theory": """
📚 <b>Урок 1: Основы управления рисками непрерывности</b>

🎯 <b>Что вы изучите:</b>
• Понятие риска нарушения непрерывности деятельности
• Основные термины: RTO, MTPD, критически важные процессы
• Типы угроз для банка
• Роль регулятора (ЦБ РФ)

💡 <b>Риск нарушения непрерывности деятельности</b> - это вероятность возникновения угроз, которые могут привести к нарушению способности банка поддерживать операционную устойчивость.

📋 <b>Ключевые термины:</b>
• <b>RTO</b> (Recovery Time Objective) - целевое время восстановления процесса
• <b>MTPD</b> (Maximum Tolerable Period of Disruption) - максимально допустимый период простоя
• <b>Критически важный процесс</b> - процесс, прерывание которого критически влияет на деятельность банка

🚨 <b>6 типов угроз:</b>
1. Техногенные (пожары, аварии)
2. Природные (землетрясения, наводнения)
3. Социальные (забастовки, беспорядки)
4. Геополитические (санкции, конфликты)
5. Экономические (кризисы, дефолты)
6. Биолого-социальные (пандемии, эпидемии)

✅ Теперь проверим ваши знания!
            """,
            "learning_objectives": [
                "Понимание основных терминов",
                "Знание типов угроз", 
                "Осознание важности непрерывности"
            ]
        },
        2: {  # Уровень 2 - Процедуры
            "title": "Процедуры оценки и реагирования",
            "theory": """
📚 <b>Урок 2: Процедуры оценки и реагирования</b>

🎯 <b>Что вы изучите:</b>
• Методика оценки рисков
• Качественная и количественная оценка
• Процедуры реагирования на инциденты
• Планы обеспечения непрерывности (ОНиВД)

📊 <b>Оценка рисков включает:</b>
• Анализ окружения критически важных процессов
• Оценку влияния недоступности АС, офисов, аутсорсеров
• Расчет времени воздействия риска (T_R)
• Определение рейтинга риска

📈 <b>Формула воздействия риска:</b>
T_R = T_rec_AC + T_rec_Office + T_move × F_strategy + T_rec_process

🚨 <b>План ОНиВД содержит:</b>
• Процедуры перевода на удаленную работу
• Переезд на резервные площадки
• Активация резервных систем
• Уведомление заинтересованных сторон

✅ Переходим к практическим вопросам!
            """,
            "learning_objectives": [
                "Понимание методики оценки",
                "Знание формул расчета",
                "Умение применять процедуры"
            ]
        },
        3: {  # Уровень 3 - Сценарии
            "title": "Анализ сценариев и принятие решений",
            "theory": """
📚 <b>Урок 3: Анализ сценариев и принятие решений</b>

🎯 <b>Что вы изучите:</b>
• Анализ сложных сценариев угроз
• Принятие решений в условиях неопределенности
• Комплексная оценка рисков
• Стратегии митигации

🎭 <b>Сценарный анализ:</b>
• Моделирование различных угроз
• Оценка каскадных эффектов
• Анализ взаимодействия факторов риска
• Планирование комплексного реагирования

🧠 <b>Принятие решений:</b>
• Быстрая оценка ситуации
• Приоритизация действий
• Координация с подразделениями
• Коммуникация с руководством

⚡ <b>Примеры сложных сценариев:</b>
• Пандемия + кибератака
• Природная катастрофа + экономический кризис
• Геополитические санкции + техногенная авария

✅ Проверим навыки принятия решений!
            """,
            "learning_objectives": [
                "Анализ сложных сценариев",
                "Принятие обоснованных решений",
                "Комплексное мышление"
            ]
        }
    }

    @staticmethod
    async def show_theory_module(update: Update, context: ContextTypes.DEFAULT_TYPE, level: int):
        """Показать теоретический модуль."""
        try:
            if level not in LessonStructure.THEORY_MODULES:
                level = 1  # Фаллбек на базовый уровень
            
            module = LessonStructure.THEORY_MODULES[level]
            
            keyboard = [
                [InlineKeyboardButton("✅ Понятно, к вопросам!", callback_data=f"start_questions_{level}")],
                [InlineKeyboardButton("📖 Перечитать", callback_data=f"reread_theory_{level}")],
                [
                    InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_question"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]
            ]
            
            # Проверяем, нужно ли обновлять сообщение
            try:
                if update.callback_query:
                    # Проверяем, не то же ли самое сообщение
                    current_text = update.callback_query.message.text
                    if current_text and module["theory"] in current_text:
                        # Сообщение уже показано, просто отвечаем на callback
                        logging.info(f"📚 Теория уровня {level} уже показана")
                        return
                    
                    await update.callback_query.edit_message_text(
                        text=module["theory"],
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(
                        text=module["theory"],
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
            except Exception as telegram_error:
                # Если не удалось отредактировать, отправляем новое сообщение
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=module["theory"],
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            
            logging.info(f"📚 Показан теоретический модуль уровня {level}")
            
        except Exception as e:
            logging.error(f"❌ Ошибка показа теории: {e}")
            # Отправляем сообщение об ошибке
            try:
                if update.callback_query:
                    await update.callback_query.edit_message_text(
                        "😔 Произошла ошибка при загрузке теоретического материала.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
                        ])
                    )
                else:
                    await update.message.reply_text(
                        "😔 Произошла ошибка при загрузке теоретического материала."
                    )
            except:
                pass

    @staticmethod
    def get_lesson_flow(level: int) -> Dict[str, Any]:
        """Получить структуру урока для уровня."""
        return {
            "theory_module": LessonStructure.THEORY_MODULES.get(level, LessonStructure.THEORY_MODULES[1]),
            "question_count": 3 + level,  # Больше вопросов на высоких уровнях
            "passing_score": 70 + (level * 5),  # Выше требования на высоких уровнях
            "scenarios_enabled": level >= 3  # Сценарии только с 3 уровня
        }

    @staticmethod
    def get_progress_text(completed_theory: bool, questions_answered: int, correct_answers: int) -> str:
        """Получить текст прогресса урока."""
        if not completed_theory:
            return "📚 Изучите теоретическую часть"
        
        if questions_answered == 0:
            return "✅ Теория изучена • 🎯 Готов к вопросам"
        
        accuracy = (correct_answers / questions_answered * 100) if questions_answered > 0 else 0
        return f"✅ Теория изучена • 🎯 Вопросов: {questions_answered} • 📊 Точность: {accuracy:.0f}%"