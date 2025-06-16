"""
LangGraph граф для обучения с адаптивной сложностью.
"""

import logging
from typing import Dict, Any, List, Optional
import json

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    from typing_extensions import Annotated, TypedDict
    LANGGRAPH_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ LangGraph недоступен")
    LANGGRAPH_AVAILABLE = False

try:
    from database.database import get_user_by_telegram_id, db_manager
    from database.models import User
    from sqlalchemy import select
    DATABASE_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ База данных недоступна для learning_graph")
    DATABASE_AVAILABLE = False


class LearningState(TypedDict):
    """Состояние обучения для LangGraph."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: int
    current_difficulty: int
    focus_topics: List[str]
    question_count: int
    correct_answers: int
    current_question: Optional[Dict[str, Any]]
    session_active: bool


class LearningGraph:
    """Граф обучения на основе LangGraph с адаптивной сложностью."""
    
    def __init__(self, knowledge_base=None, llm=None):
        self.knowledge_base = knowledge_base
        self.llm = llm
        self.graph = None
        self.is_initialized = False
        
        # Настройки адаптивности
        self.min_difficulty = 1
        self.max_difficulty = 5
        self.questions_per_session = 10
        
        # Темы по уровням сложности
        self.difficulty_topics = {
            1: ["basic_concepts", "definitions", "simple_terms"],
            2: ["risk_identification", "threat_types", "basic_procedures"],
            3: ["risk_assessment", "impact_analysis", "intermediate_concepts"],
            4: ["mitigation_strategies", "business_continuity", "advanced_procedures"],
            5: ["regulatory_compliance", "complex_scenarios", "expert_level"]
        }
    
    async def initialize(self) -> bool:
        """Инициализация графа обучения."""
        try:
            if not LANGGRAPH_AVAILABLE:
                logging.warning("⚠️ LangGraph недоступен - используется упрощенный режим")
                self.is_initialized = True
                return True
            
            # Создаем граф состояний
            workflow = StateGraph(LearningState)
            
            # Добавляем узлы (ИСПРАВЛЕНО: убираем недостижимые узлы)
            workflow.add_node("assess_user", self.assess_user_level)
            workflow.add_node("generate_question", self.generate_question)
            workflow.add_node("check_completion", self.check_session_completion)
            
            # Добавляем простые рёбра (ИСПРАВЛЕНО: простая структура)
            workflow.set_entry_point("assess_user")
            workflow.add_edge("assess_user", "generate_question")
            workflow.add_edge("generate_question", "check_completion")
            workflow.add_edge("check_completion", END)
            
            # Компилируем граф
            self.graph = workflow.compile()
            self.is_initialized = True
            
            logging.info("✅ LangGraph агент инициализирован")
            return True
            
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации LangGraph: {e}")
            # Включаем упрощенный режим
            self.is_initialized = True
            return True
    
    async def start_learning_session(
        self, 
        user_id: int, 
        difficulty_override: Optional[int] = None,
        focus_topics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Запуск новой сессии обучения."""
        try:
            if not self.is_initialized:
                await self.initialize()
            
            # Получаем уровень пользователя
            user_difficulty = await self.get_user_difficulty(user_id)
            current_difficulty = difficulty_override or user_difficulty
            
            # Определяем темы для фокуса
            if not focus_topics:
                focus_topics = self.difficulty_topics.get(current_difficulty, ["basic_concepts"])
            
            logging.info(f"👤 Оценка пользователя {user_id}: уровень {current_difficulty}")
            
            if LANGGRAPH_AVAILABLE and self.graph:
                # Используем LangGraph
                initial_state = LearningState(
                    messages=[],
                    user_id=user_id,
                    current_difficulty=current_difficulty,
                    focus_topics=focus_topics,
                    question_count=0,
                    correct_answers=0,
                    current_question=None,
                    session_active=True
                )
                
                result = await self.graph.ainvoke(initial_state)
                
                if result.get("current_question"):
                    return {
                        "success": True,
                        "generated_question": result["current_question"],
                        "difficulty": result["current_difficulty"],
                        "focus_topics": result["focus_topics"]
                    }
                else:
                    return {"error": "Не удалось сгенерировать вопрос через LangGraph"}
            else:
                # Упрощенный режим без LangGraph
                return await self.generate_simple_question(user_id, current_difficulty, focus_topics)
                
        except Exception as e:
            logging.error(f"❌ Ошибка запуска сессии обучения: {e}")
            return {"error": str(e)}
    
    async def get_user_difficulty(self, user_id: int) -> int:
        """Получение текущего уровня сложности пользователя."""
        if DATABASE_AVAILABLE:
            try:
                # ИСПРАВЛЕНО: получаем пользователя по Telegram ID, а не по внутреннему ID
                from database.database import db_manager
                from database.models import User
                
                async with db_manager.get_session() as session:
                    user_result = await session.execute(
                        select(User).where(User.telegram_id == user_id)
                    )
                    user = user_result.scalar_one_or_none()
                    
                    if user:
                        level = user.current_difficulty_level
                        logging.info(f"📊 Получен уровень пользователя {user_id}: {level}")
                        return level
                    else:
                        logging.warning(f"⚠️ Пользователь {user_id} не найден в БД")
                        
            except Exception as e:
                logging.warning(f"⚠️ Ошибка получения уровня пользователя: {e}")
        
        logging.info(f"📊 Используем начальный уровень для пользователя {user_id}: 1")
        return 1  # Начальный уровень по умолчанию
    
    async def assess_user_level(self, state: LearningState) -> LearningState:
        """Оценка уровня пользователя."""
        try:
            # Логика оценки уже выполнена в start_learning_session
            return state
        except Exception as e:
            logging.error(f"❌ Ошибка оценки пользователя: {e}")
            return state
    
    async def generate_question(self, state: LearningState) -> LearningState:
        """Генерация вопроса через LLM."""
        try:
            difficulty = state["current_difficulty"]
            focus_topics = state["focus_topics"]
            
            # Получаем контекст из базы знаний
            context = await self.get_context_for_difficulty(difficulty, focus_topics)
            
            # Генерируем вопрос через LLM
            question_data = await self.generate_question_with_llm(difficulty, context, focus_topics)
            
            if question_data:
                state["current_question"] = question_data
                logging.info(f"❓ Сгенерирован вопрос для пользователя {state['user_id']}")
            
            return state
            
        except Exception as e:
            logging.error(f"❌ Ошибка генерации вопроса: {e}")
            return state
    
    async def get_context_for_difficulty(self, difficulty: int, focus_topics: List[str]) -> str:
        """Получение контекста из базы знаний для определенного уровня сложности."""
        try:
            if not self.knowledge_base:
                return "Базовая информация о рисках непрерывности деятельности банка."
            
            # ИСПРАВЛЕНО: формируем разные запросы для разных уровней
            if difficulty == 1:
                query = "банковские риски определения основные понятия"
            elif difficulty == 2:
                query = "типы угроз риски идентификация процедуры"
            elif difficulty == 3:
                query = "оценка рисков воздействие анализ методы"
            elif difficulty == 4:
                query = "управление рисками стратегии непрерывность бизнес"
            else:  # 5
                query = "регулирование комплаенс сложные сценарии планирование"
            
            # Добавляем темы фокуса
            if focus_topics:
                topics_str = " ".join(focus_topics)
                query += f" {topics_str}"
            
            # Ищем релевантные документы
            docs = await self.knowledge_base.search(query, limit=3)
            
            if docs:
                context = "\n\n".join([doc.page_content for doc in docs])
                logging.info(f"🔍 Найдено {len(docs)} документов для запроса: {query[:50]}...")
                return context
            else:
                return "Базовая информация о рисках непрерывности деятельности банка."
                
        except Exception as e:
            logging.warning(f"⚠️ Ошибка получения контекста: {e}")
            return "Базовая информация о рисках непрерывности деятельности банка."
    
    async def generate_question_with_llm(
        self, 
        difficulty: int, 
        context: str, 
        focus_topics: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Генерация вопроса через LLM."""
        try:
            if not self.llm:
                return await self.generate_fallback_question(difficulty)
            
            # Формируем промпт для генерации вопроса
            prompt = self.create_question_prompt(difficulty, context, focus_topics)
            
            # Вызываем LLM
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            response_text = response.content.strip()
            
            # Парсим ответ
            question_data = self.parse_llm_response(response_text, difficulty)
            
            if question_data and self.validate_question(question_data):
                return question_data
            else:
                logging.warning("⚠️ LLM сгенерировал некорректный вопрос, используем fallback")
                return await self.generate_fallback_question(difficulty)
                
        except Exception as e:
            logging.error(f"❌ Ошибка генерации вопроса через LLM: {e}")
            return await self.generate_fallback_question(difficulty)
    
    def create_question_prompt(self, difficulty: int, context: str, focus_topics: List[str]) -> str:
        """Создание промпта для генерации вопроса."""
        topics_str = ", ".join(focus_topics)
        
        # ИСПРАВЛЕНО: добавляем вариативность и требования к подсказкам
        import random
        variation_seed = random.randint(1000, 9999)
        
        return f"""
Создай НОВЫЙ и УНИКАЛЬНЫЙ вопрос для тестирования знаний по управлению рисками непрерывности деятельности банка.

ВАЖНО: Генерируй каждый раз РАЗНЫЕ вопросы! Вариант #{variation_seed}

ПАРАМЕТРЫ:
- Уровень сложности: {difficulty}/5
- Темы для фокуса: {topics_str}
- Тип вопроса: множественный выбор (4 варианта)

ТРЕБОВАНИЯ К СЛОЖНОСТИ:
Уровень 1: Определения, основные термины (RTO, MTPD)
Уровень 2: Типы угроз, классификация рисков
Уровень 3: Процедуры оценки, анализ воздействия
Уровень 4: Стратегии управления, планирование
Уровень 5: Комплексные сценарии, регулирование

КОНТЕКСТ:
{context[:1000]}

ТРЕБОВАНИЯ:
1. Вопрос должен соответствовать уровню сложности {difficulty}
2. Включи практические аспекты из банковской деятельности
3. 4 варианта ответа (только один правильный)
4. Объяснение должно быть обучающим, НЕ подсказкой к ответу
5. Вопрос должен проверять понимание, а не память

ФОРМАТ ОТВЕТА (строго JSON):
{{
    "question": "Текст вопроса",
    "options": ["Вариант A", "Вариант B", "Вариант C", "Вариант D"],
    "correct_answer": 0,
    "explanation": "Подробное объяснение правильного ответа с дополнительной информацией",
    "difficulty": {difficulty},
    "topic": "Название темы"
}}

Ответь только JSON без дополнительного текста.
        """
    
    def parse_llm_response(self, response_text: str, difficulty: int) -> Optional[Dict[str, Any]]:
        """Парсинг ответа LLM."""
        try:
            # Пытаемся извлечь JSON из ответа
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                question_data = json.loads(json_str)
                
                # Проверяем обязательные поля
                required_fields = ["question", "options", "correct_answer", "explanation"]
                if all(field in question_data for field in required_fields):
                    question_data["difficulty"] = difficulty
                    return question_data
            
            return None
            
        except json.JSONDecodeError as e:
            logging.warning(f"⚠️ Ошибка парсинга JSON ответа LLM: {e}")
            return None
        except Exception as e:
            logging.error(f"❌ Ошибка обработки ответа LLM: {e}")
            return None
    
    def validate_question(self, question_data: Dict[str, Any]) -> bool:
        """Валидация сгенерированного вопроса."""
        try:
            # Проверяем обязательные поля
            if not question_data.get("question") or len(question_data["question"]) < 10:
                return False
            
            options = question_data.get("options", [])
            if len(options) != 4:
                return False
            
            correct_answer = question_data.get("correct_answer")
            if not isinstance(correct_answer, int) or correct_answer < 0 or correct_answer >= 4:
                return False
            
            if not question_data.get("explanation") or len(question_data["explanation"]) < 10:
                return False
            
            return True
            
        except Exception as e:
            logging.warning(f"⚠️ Ошибка валидации вопроса: {e}")
            return False
    
    async def generate_fallback_question(self, difficulty: int) -> Dict[str, Any]:
        """Генерация резервного вопроса при ошибке LLM."""
        fallback_questions = {
            1: [
                {
                    "question": "Что означает аббревиатура RTO в контексте управления рисками непрерывности?",
                    "options": [
                        "Время восстановления операций",
                        "Риск технических операций", 
                        "Регулярная техническая оценка",
                        "Расчет текущих обязательств"
                    ],
                    "correct_answer": 0,
                    "explanation": "RTO (Recovery Time Objective) - это целевое время восстановления процесса после инцидента.",
                    "topic": "Основные термины"
                },
                {
                    "question": "Что такое MTPD в управлении рисками непрерывности?",
                    "options": [
                        "Максимально допустимый период простоя",
                        "Минимальное время подготовки данных",
                        "Максимальный темп производственных данных",
                        "Методы технического планирования данных"
                    ],
                    "correct_answer": 0,
                    "explanation": "MTPD (Maximum Tolerable Period of Disruption) - максимально допустимый период нарушения процесса.",
                    "topic": "Основные термины"
                }
            ],
            2: [
                {
                    "question": "Какие из перечисленных угроз относятся к техногенным рискам?",
                    "options": [
                        "Землетрясения и наводнения",
                        "Пожары и аварии оборудования",
                        "Экономические кризисы",
                        "Социальные беспорядки"
                    ],
                    "correct_answer": 1,
                    "explanation": "Техногенные угрозы - это риски, связанные с технической деятельностью человека, включая пожары, аварии оборудования, техногенные катастрофы.",
                    "topic": "Типы угроз"
                },
                {
                    "question": "К какому типу угроз относятся забастовки и беспорядки?",
                    "options": [
                        "Природные",
                        "Техногенные",
                        "Социальные",
                        "Экономические"
                    ],
                    "correct_answer": 2,
                    "explanation": "Забастовки и социальные беспорядки относятся к социальным угрозам, которые могут нарушить деятельность банка.",
                    "topic": "Типы угроз"
                }
            ],
            3: [
                {
                    "question": "При оценке воздействия на бизнес (BIA) в первую очередь определяют:",
                    "options": [
                        "Стоимость восстановительных работ",
                        "Критически важные бизнес-процессы",
                        "Количество сотрудников в подразделении",
                        "Размер страховых выплат"
                    ],
                    "correct_answer": 1,
                    "explanation": "Анализ воздействия на бизнес начинается с выявления критически важных процессов, без которых банк не может функционировать.",
                    "topic": "Анализ воздействия"
                },
                {
                    "question": "Что включает в себя процедура оценки риска?",
                    "options": [
                        "Только расчет финансовых потерь",
                        "Идентификацию, анализ и оценку рисков",
                        "Только выбор методов защиты",
                        "Только составление отчетности"
                    ],
                    "correct_answer": 1,
                    "explanation": "Процедура оценки риска включает три этапа: идентификацию угроз, анализ их воздействия и оценку уровня риска.",
                    "topic": "Оценка рисков"
                }
            ],
            4: [
                {
                    "question": "Основная цель планов обеспечения непрерывности бизнеса:",
                    "options": [
                        "Полное предотвращение всех рисков",
                        "Минимизация времени восстановления критических процессов",
                        "Максимизация прибыли",
                        "Сокращение штата сотрудников"
                    ],
                    "correct_answer": 1,
                    "explanation": "Планы обеспечения непрерывности бизнеса направлены на быстрое восстановление критически важных процессов после инцидента.",
                    "topic": "Планирование непрерывности"
                }
            ],
            5: [
                {
                    "question": "Какие требования предъявляет Банк России к управлению операционными рисками?",
                    "options": [
                        "Только ведение статистики инцидентов",
                        "Комплексную систему управления рисками с регулярной отчетностью",
                        "Только страхование от всех рисков",
                        "Только назначение ответственного сотрудника"
                    ],
                    "correct_answer": 1,
                    "explanation": "Банк России требует создания комплексной системы управления операционными рисками с процедурами выявления, оценки, контроля и отчетности.",
                    "topic": "Регулирование"
                }
            ]
        }
        
        # ИСПРАВЛЕНО: выбираем случайный вопрос из доступных для уровня
        questions_for_level = fallback_questions.get(difficulty, fallback_questions[1])
        import random
        question = random.choice(questions_for_level).copy()
        question["difficulty"] = difficulty
        
        logging.info(f"🔄 Использован резервный вопрос уровня {difficulty}")
        return question
    
    async def generate_simple_question(
        self, 
        user_id: int, 
        difficulty: int, 
        focus_topics: List[str]
    ) -> Dict[str, Any]:
        """Простая генерация вопроса без LangGraph."""
        try:
            # Получаем контекст
            context = await self.get_context_for_difficulty(difficulty, focus_topics)
            
            # Генерируем вопрос
            if self.llm:
                question_data = await self.generate_question_with_llm(difficulty, context, focus_topics)
            else:
                question_data = await self.generate_fallback_question(difficulty)
            
            if question_data:
                return {
                    "success": True,
                    "generated_question": question_data,
                    "difficulty": difficulty,
                    "focus_topics": focus_topics
                }
            else:
                return {"error": "Не удалось сгенерировать вопрос"}
                
        except Exception as e:
            logging.error(f"❌ Ошибка простой генерации вопроса: {e}")
            return {"error": str(e)}
    
    async def process_answer(self, state: LearningState) -> LearningState:
        """Обработка ответа пользователя."""
        # Эта функция будет вызываться из lesson_handler
        return state
    
    async def adapt_difficulty(self, state: LearningState) -> LearningState:
        """Адаптация сложности на основе ответа."""
        # Логика адаптации теперь в ProgressService
        return state
    
    async def check_session_completion(self, state: LearningState) -> LearningState:
        """Проверка завершения сессии."""
        if state["question_count"] >= self.questions_per_session:
            state["session_active"] = False
        return state
    
    def should_continue(self, state: LearningState) -> str:
        """Определение продолжения сессии."""
        return "continue" if state["session_active"] else "end"