"""
LangGraph агент для адаптивного обучения банковским рискам.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain.schema import Document

from config.settings import settings, DifficultyConfig


class LearningState(Enum):
    """Состояния процесса обучения."""
    ASSESSMENT = "assessment"
    QUESTION_GENERATION = "question_generation" 
    QUESTION_PRESENTATION = "question_presentation"
    ANSWER_EVALUATION = "answer_evaluation"
    DIFFICULTY_ADAPTATION = "difficulty_adaptation"
    LESSON_COMPLETION = "lesson_completion"
    TOPIC_TRANSITION = "topic_transition"


@dataclass
class LearningContext:
    """Контекст обучения пользователя."""
    user_id: int
    current_difficulty: int = 1
    current_topic_id: Optional[int] = None
    current_lesson_id: Optional[int] = None
    questions_answered: int = 0
    correct_answers: int = 0
    consecutive_correct: int = 0
    consecutive_incorrect: int = 0
    session_history: List[Dict] = None
    knowledge_gaps: List[str] = None
    strengths: List[str] = None
    
    def __post_init__(self):
        if self.session_history is None:
            self.session_history = []
        if self.knowledge_gaps is None:
            self.knowledge_gaps = []
        if self.strengths is None:
            self.strengths = []


class LearningGraph:
    """Основной класс LangGraph агента для адаптивного обучения."""
    
    def __init__(self, knowledge_base, llm=None):
        self.knowledge_base = knowledge_base
        self.llm = llm
        self.graph = None
        self.contexts: Dict[int, LearningContext] = {}
    
    async def set_llm(self, llm):
        """Установка LLM после инициализации."""
        self.llm = llm
    
    async def initialize(self):
        """Инициализация графа обучения."""
    try:
        from langgraph.graph import StateGraph, END
        
        workflow = StateGraph(dict)
        
        # Только необходимые узлы
        workflow.add_node("assessment", self._assessment_node)
        workflow.add_node("question_generation", self._question_generation_node)
        
        # Простые переходы
        workflow.add_edge("assessment", "question_generation")
        workflow.add_edge("question_generation", END)
        
        workflow.set_entry_point("assessment")
        
        self.graph = workflow.compile()
        
        logging.info("✅ LangGraph агент инициализирован")
        
    except Exception as e:
        logging.error(f"❌ Ошибка инициализации LangGraph: {e}")
        raise
    
    async def start_learning_session(self, user_id: int, topic_id: int = None) -> Dict[str, Any]:
        """Начало новой сессии обучения."""
        try:
            # Создание или обновление контекста
            if user_id not in self.contexts:
                self.contexts[user_id] = LearningContext(user_id=user_id)
            
            context = self.contexts[user_id]
            context.current_topic_id = topic_id
            context.questions_answered = 0
            context.correct_answers = 0
            
            # Запуск графа
            initial_state = {
                "user_id": user_id,
                "context": context,
                "action": "start_session"
            }
            
            result = await self.graph.ainvoke(initial_state)
            return result
            
        except Exception as e:
            logging.error(f"❌ Ошибка запуска сессии обучения: {e}")
            return {"error": str(e)}
    
    async def process_answer(self, user_id: int, question_id: int, answer: str) -> Dict[str, Any]:
        """Обработка ответа пользователя."""
        try:
            if user_id not in self.contexts:
                return {"error": "Сессия не найдена"}
            
            context = self.contexts[user_id]
            
            # Прямая обработка ответа без LangGraph для избежания рекурсии
            return await self._process_answer_direct(context, answer)
            
        except Exception as e:
            logging.error(f"❌ Ошибка обработки ответа: {e}")
            return {"error": str(e)}
    
    async def _process_answer_direct(self, context: LearningContext, answer: str) -> Dict[str, Any]:
        """Прямая обработка ответа без LangGraph."""
        try:
            # Предполагаем что у нас есть текущий вопрос в контексте
            if not hasattr(context, 'current_question'):
                return {"error": "Нет текущего вопроса"}
            
            question_data = context.current_question
            user_answer_index = int(answer) if answer.isdigit() else -1
            correct_answer_index = question_data.get("correct_answer", 0)
            
            is_correct = user_answer_index == correct_answer_index
            
            # Обновление контекста
            context.questions_answered += 1
            if is_correct:
                context.correct_answers += 1
                context.consecutive_correct += 1
                context.consecutive_incorrect = 0
            else:
                context.consecutive_incorrect += 1
                context.consecutive_correct = 0
            
            # Генерация обратной связи
            if is_correct:
                feedback = f"✅ Правильно! {question_data.get('explanation', '')}"
            else:
                correct_option = question_data.get('options', [])[correct_answer_index] if correct_answer_index < len(question_data.get('options', [])) else "Неизвестно"
                feedback = f"❌ Неправильно. Правильный ответ: {correct_option}\n\n💡 {question_data.get('explanation', '')}"
            
            # Адаптация сложности
            adaptation_made = False
            if context.consecutive_correct >= 2 and context.current_difficulty < 5:
                context.current_difficulty = min(context.current_difficulty + 1, 5)
                adaptation_made = True
                feedback += f"\n\n🎯 Уровень повышен до {context.current_difficulty}!"
            elif context.consecutive_incorrect >= 2 and context.current_difficulty > 1:
                context.current_difficulty = max(context.current_difficulty - 1, 1)
                adaptation_made = True
                feedback += f"\n\n📚 Уровень понижен до {context.current_difficulty} для лучшего усвоения"
            
            # Проверка завершения урока
            if context.questions_answered >= settings.questions_per_lesson:
                success_rate = context.correct_answers / context.questions_answered * 100
                lesson_passed = success_rate >= settings.min_lesson_score
                
                completion_data = {
                    "lesson_passed": lesson_passed,
                    "success_rate": success_rate,
                    "questions_answered": context.questions_answered,
                    "correct_answers": context.correct_answers,
                    "final_difficulty": context.current_difficulty
                }
                
                return {
                    "is_correct": is_correct,
                    "feedback": feedback,
                    "completion_data": completion_data
                }
            
            return {
                "is_correct": is_correct,
                "feedback": feedback,
                "adaptation_made": adaptation_made,
                "current_difficulty": context.current_difficulty
            }
            
        except Exception as e:
            logging.error(f"❌ Ошибка прямой обработки ответа: {e}")
            return {"error": str(e)}
    
    # Узлы графа
    async def _assessment_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел оценки текущего уровня знаний пользователя."""
        try:
            context: LearningContext = state["context"]
            
            # Получение истории ответов пользователя
            from database.database import db_manager
            from database.models import QuestionAttempt
            from sqlalchemy import select, desc
            
            async with db_manager.get_session() as session:
                # Получаем последние ответы для анализа
                recent_attempts = await session.execute(
                    select(QuestionAttempt)
                    .where(QuestionAttempt.user_id == context.user_id)
                    .order_by(desc(QuestionAttempt.created_at))
                    .limit(10)
                )
                attempts = recent_attempts.scalars().all()
            
            # Анализ производительности
            if attempts:
                correct_rate = sum(1 for a in attempts if a.is_correct) / len(attempts)
                
                # Адаптация сложности на основе результатов
                if correct_rate >= 0.8 and context.current_difficulty < 5:
                    context.current_difficulty = min(context.current_difficulty + 1, 5)
                elif correct_rate <= 0.4 and context.current_difficulty > 1:
                    context.current_difficulty = max(context.current_difficulty - 1, 1)
            
            state["assessment_complete"] = True
            state["recommended_difficulty"] = context.current_difficulty
            
            logging.info(f"👤 Оценка пользователя {context.user_id}: уровень {context.current_difficulty}")
            
            return state
            
        except Exception as e:
            logging.error(f"❌ Ошибка в узле оценки: {e}")
            state["error"] = str(e)
            return state
    
    async def _question_generation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел генерации адаптивных вопросов."""
        try:
            context: LearningContext = state["context"]
            
            # Поиск подходящего контента в базе знаний
            difficulty_keywords = {
                1: ["основы", "что такое", "определение"],
                2: ["процедуры", "как", "методы"],
                3: ["анализ", "оценка", "сценарии"],
                4: ["расчет", "формула", "сложные"],
                5: ["экспертные", "принятие решений", "комплексные"]
            }
            
            keywords = difficulty_keywords.get(context.current_difficulty, ["основы"])
            search_query = f"банковские риски {' '.join(keywords[:2])}"
            
            # Поиск релевантного контента
            relevant_docs = await self.knowledge_base.search(search_query, limit=3)
            
            if not relevant_docs:
                state["error"] = "Контент для генерации вопроса не найден"
                return state
            
            # ИСПРАВЛЕНИЕ: Определяем context_text ЗДЕСЬ
            context_text = "\n".join([doc.page_content for doc in relevant_docs])
            
            # Попытка генерации через LLM
            if self.llm:
                try:
                    # Формирование промпта для генерации вопроса (оптимизировано для Qwen2.5)
                    from ai_agent.llm.prompts.qwen_prompts import QwenPrompts
                    
                    question_prompt = QwenPrompts.QUESTION_GENERATOR.format(
                        difficulty=context.current_difficulty,
                        topic="банковские риски непрерывности",
                        context=context_text
                    )
                    
                    # Генерация вопроса через LLM
                    from langchain_core.messages import HumanMessage, SystemMessage
                    
                    messages = [
                        SystemMessage(content=QwenPrompts.SYSTEM_EXPERT),
                        HumanMessage(content=question_prompt)
                    ]
                    
                    response = await self.llm.ainvoke(messages)
                    
                    # Парсинг JSON ответа
                    import json
                    try:
                        # Очистка ответа от лишних символов
                        response_content = response.content.strip()
                        if response_content.startswith("```json"):
                            response_content = response_content[7:-3]
                        elif response_content.startswith("```"):
                            response_content = response_content[3:-3]
                        
                        question_data = json.loads(response_content)
                        state["generated_question"] = question_data
                        state["question_context"] = context_text
                        
                        logging.info(f"❓ Сгенерирован вопрос для пользователя {context.user_id}")
                        return state
                        
                    except json.JSONDecodeError:
                        logging.warning("⚠️ Ошибка парсинга JSON от LLM, используем фаллбек")
                        # Фаллбек к простому вопросу
                        pass
                        
                except Exception as e:
                    logging.warning(f"⚠️ Ошибка LLM: {e}, используем фаллбек")
            
            # Фаллбек - используем простой вопрос
            state["generated_question"] = self._create_fallback_question(context.current_difficulty)
            state["question_context"] = context_text
            
            logging.info(f"❓ Использован фаллбек вопрос для пользователя {context.user_id}")
            
            return state
            
        except Exception as e:
            logging.error(f"❌ Ошибка генерации вопроса: {e}")
            state["error"] = str(e)
            return state
    
    async def _answer_evaluation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел оценки ответа пользователя."""
        try:
            context: LearningContext = state["context"]
            user_answer = state.get("user_answer")
            question_data = state.get("generated_question", {})
            
            if not user_answer or not question_data:
                state["error"] = "Недостаточно данных для оценки"
                return state
            
            # Оценка правильности ответа
            correct_answer_index = question_data.get("correct_answer", 0)
            user_answer_index = int(user_answer) if user_answer.isdigit() else -1
            
            is_correct = user_answer_index == correct_answer_index
            
            # Обновление контекста
            context.questions_answered += 1
            if is_correct:
                context.correct_answers += 1
                context.consecutive_correct += 1
                context.consecutive_incorrect = 0
            else:
                context.consecutive_incorrect += 1
                context.consecutive_correct = 0
            
            # Сохранение результата в историю
            attempt_record = {
                "question": question_data.get("question"),
                "user_answer": user_answer,
                "correct_answer": correct_answer_index,
                "is_correct": is_correct,
                "difficulty": context.current_difficulty,
                "timestamp": "now"
            }
            context.session_history.append(attempt_record)
            
            # Сохранение в базу данных
            await self._save_question_attempt(
                user_id=context.user_id,
                question_data=question_data,
                user_answer=user_answer,
                is_correct=is_correct
            )
            
            state["is_correct"] = is_correct
            state["evaluation_complete"] = True
            
            # Генерация обратной связи
            if is_correct:
                feedback = f"✅ Правильно! {question_data.get('explanation', '')}"
            else:
                correct_option = question_data.get('options', [])[correct_answer_index]
                feedback = f"❌ Неправильно. Правильный ответ: {correct_option}\n\n💡 {question_data.get('explanation', '')}"
            
            state["feedback"] = feedback
            
            logging.info(f"📊 Ответ пользователя {context.user_id}: {'✅' if is_correct else '❌'}")
            
            return state
            
        except Exception as e:
            logging.error(f"❌ Ошибка оценки ответа: {e}")
            state["error"] = str(e)
            return state
    
    async def _difficulty_adaptation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел адаптации сложности."""
        try:
            context: LearningContext = state["context"]
            
            # Логика адаптации сложности
            adaptation_made = False
            
            # Увеличиваем сложность при серии правильных ответов
            if context.consecutive_correct >= 2 and context.current_difficulty < 5:
                context.current_difficulty = min(context.current_difficulty + 1, 5)
                adaptation_made = True
                state["adaptation_message"] = f"🎯 Уровень повышен до {DifficultyConfig.LEVEL_NAMES[context.current_difficulty]}!"
            
            # Уменьшаем сложность при серии неправильных ответов
            elif context.consecutive_incorrect >= 2 and context.current_difficulty > 1:
                context.current_difficulty = max(context.current_difficulty - 1, 1)
                adaptation_made = True
                state["adaptation_message"] = f"📚 Уровень понижен до {DifficultyConfig.LEVEL_NAMES[context.current_difficulty]} для лучшего усвоения"
            
            state["adaptation_made"] = adaptation_made
            state["current_difficulty"] = context.current_difficulty
            
            logging.info(f"🎯 Адаптация для пользователя {context.user_id}: уровень {context.current_difficulty}")
            
            return state
            
        except Exception as e:
            logging.error(f"❌ Ошибка адаптации сложности: {e}")
            state["error"] = str(e)
            return state
    
    async def _lesson_completion_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел завершения урока."""
        try:
            context: LearningContext = state["context"]
            
            # Расчет результатов урока
            success_rate = context.correct_answers / max(context.questions_answered, 1) * 100
            
            # Определение статуса завершения
            lesson_passed = success_rate >= settings.min_lesson_score
            
            completion_data = {
                "lesson_passed": lesson_passed,
                "success_rate": success_rate,
                "questions_answered": context.questions_answered,
                "correct_answers": context.correct_answers,
                "final_difficulty": context.current_difficulty
            }
            
            # Сообщение о завершении
            if lesson_passed:
                message = f"🎉 Урок завершен успешно!\n📊 Результат: {success_rate:.1f}%"
            else:
                message = f"📚 Необходимо повторение\n📊 Результат: {success_rate:.1f}% (требуется {settings.min_lesson_score}%)"
            
            state["completion_data"] = completion_data
            state["completion_message"] = message
            
            # Сохранение прогресса
            await self._save_lesson_progress(context.user_id, completion_data)
            
            logging.info(f"🏁 Урок завершен для пользователя {context.user_id}: {success_rate:.1f}%")
            
            return state
            
        except Exception as e:
            logging.error(f"❌ Ошибка завершения урока: {e}")
            state["error"] = str(e)
            return state
    
    async def _topic_transition_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел перехода к следующей теме."""
        try:
            context: LearningContext = state["context"]
            
            # Логика выбора следующей темы на основе прогресса
            # Это упрощенная версия - в реальности нужна более сложная логика
            
            next_topic_id = None
            if context.current_topic_id:
                next_topic_id = context.current_topic_id + 1
            
            state["next_topic_id"] = next_topic_id
            state["transition_complete"] = True
            
            logging.info(f"🔄 Переход к теме {next_topic_id} для пользователя {context.user_id}")
            
            return state
            
        except Exception as e:
            logging.error(f"❌ Ошибка перехода к теме: {e}")
            state["error"] = str(e)
            return state
    
    # Функции маршрутизации
    def _route_after_evaluation(self, state: Dict[str, Any]) -> str:
        """Маршрутизация после оценки ответа."""
        context: LearningContext = state["context"]
        
        # Завершаем урок после определенного количества вопросов
        if context.questions_answered >= settings.questions_per_lesson:
            return "complete_lesson"
        
        # Переходим к следующей теме при высоких результатах
        if context.consecutive_correct >= 3 and context.current_difficulty >= 4:
            return "next_topic"
        
        # Продолжаем с адаптацией сложности
        return "continue"
    
    def _route_after_adaptation(self, state: Dict[str, Any]) -> str:
        """Маршрутизация после адаптации сложности."""
        context: LearningContext = state["context"]
        
        # Завершаем урок если достигли лимита вопросов
        if context.questions_answered >= settings.questions_per_lesson:
            return "complete_lesson"
        
        # Продолжаем генерацию вопросов
        return "continue"
    
    # Вспомогательные методы
    def _create_fallback_question(self, difficulty: int) -> Dict[str, Any]:
        """Создание резервного вопроса при ошибке генерации."""
        fallback_questions = {
            1: {
                "question": "Что означает аббревиатура RTO в контексте управления рисками?",
                "options": [
                    "Время восстановления процесса",
                    "Реальное время операций", 
                    "Результат технической оценки",
                    "Режим текущей операции"
                ],
                "correct_answer": 0,
                "explanation": "RTO (Recovery Time Objective) - это целевое время восстановления процесса после реализации угрозы непрерывности.",
                "difficulty": 1,
                "topic": "Основные понятия"
            }
        }
        
        return fallback_questions.get(difficulty, fallback_questions[1])
    
    async def _save_question_attempt(self, user_id: int, question_data: Dict, user_answer: str, is_correct: bool):
        """Сохранение попытки ответа в базе данных."""
        try:
            from database.models import QuestionAttempt
            from database.database import db_manager
            
            async with db_manager.get_session() as session:
                attempt = QuestionAttempt(
                    user_id=user_id,
                    question_id=None,  # Для сгенерированных вопросов
                    user_answer=user_answer,
                    is_correct=is_correct,
                    ai_feedback=question_data.get("explanation"),
                    time_spent_seconds=None
                )
                session.add(attempt)
                await session.commit()
                
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения попытки: {e}")
    
    async def _save_lesson_progress(self, user_id: int, completion_data: Dict):
        """Сохранение прогресса урока."""
        try:
            from database.models import UserProgress
            from database.database import db_manager
            
            async with db_manager.get_session() as session:
                # Здесь должна быть логика сохранения прогресса
                # Упрощенная версия
                pass
                
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения прогресса: {e}")
    
    def get_user_context(self, user_id: int) -> Optional[LearningContext]:
        """Получение контекста пользователя."""
        return self.contexts.get(user_id)
    
    def clear_user_context(self, user_id: int):
        """Очистка контекста пользователя."""
        if user_id in self.contexts:
            del self.contexts[user_id]