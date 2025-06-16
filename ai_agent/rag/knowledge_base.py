"""
RAG система для работы с базой знаний методики управления рисками.
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from config.settings import settings


class KnowledgeBase:
    """Класс для работы с базой знаний через RAG."""
    
    def __init__(self):
        self.embeddings = None
        self.vectorstore = None
        self.text_splitter = None
        self.documents: List[Document] = []
        
    async def initialize(self):
        """Инициализация базы знаний."""
        try:
            logging.info("🔄 Инициализация базы знаний RAG...")
            
            # Инициализация embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name=settings.embedding_model,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # Инициализация text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", "! ", "? ", " "]
            )
            
            # Загрузка документов из JSONL файла
            await self._load_documents_from_jsonl()
            
            # Инициализация векторного хранилища
            await self._initialize_vectorstore()
            
            logging.info("✅ База знаний инициализирована")
            
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации базы знаний: {e}")
            raise
    
    async def _load_documents_from_jsonl(self):
        """Загрузка документов из JSONL файла."""
        try:
            jsonl_path = Path("ai_agent/rag/data/methodology.jsonl")
            
            if not jsonl_path.exists():
                logging.warning(f"⚠️ Файл {jsonl_path} не найден")
                return
            
            documents = []
            
            with open(jsonl_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    try:
                        data = json.loads(line.strip())
                        
                        # Создание документа из prompt-response пары
                        prompt = data.get('prompt', '')
                        response = data.get('response', '')
                        metadata = data.get('metadata', {})
                        
                        if prompt and response:
                            # Документ из вопроса
                            doc_question = Document(
                                page_content=f"Вопрос: {prompt}",
                                metadata={
                                    **metadata,
                                    "type": "question",
                                    "source": "methodology_jsonl",
                                    "line_number": line_num
                                }
                            )
                            documents.append(doc_question)
                            
                            # Документ из ответа
                            doc_answer = Document(
                                page_content=f"Ответ: {response}",
                                metadata={
                                    **metadata,
                                    "type": "answer", 
                                    "source": "methodology_jsonl",
                                    "line_number": line_num,
                                    "related_question": prompt
                                }
                            )
                            documents.append(doc_answer)
                            
                            # Комбинированный документ для лучшего контекста
                            combined_content = f"{prompt}\n\n{response}"
                            doc_combined = Document(
                                page_content=combined_content,
                                metadata={
                                    **metadata,
                                    "type": "qa_pair",
                                    "source": "methodology_jsonl",
                                    "line_number": line_num
                                }
                            )
                            documents.append(doc_combined)
                    
                    except json.JSONDecodeError as e:
                        logging.warning(f"⚠️ Ошибка парсинга строки {line_num}: {e}")
                        continue
            
            # Разбиение документов на чанки
            all_chunks = []
            for doc in documents:
                chunks = self.text_splitter.split_documents([doc])
                all_chunks.extend(chunks)
            
            self.documents = all_chunks
            logging.info(f"📚 Загружено {len(documents)} документов, создано {len(all_chunks)} чанков")
            
        except Exception as e:
            logging.error(f"❌ Ошибка загрузки документов: {e}")
            raise
    
    async def _initialize_vectorstore(self):
        """Инициализация векторного хранилища."""
        try:
            # Создание директории для хранилища
            vectorstore_path = Path(settings.vector_store_path)
            vectorstore_path.mkdir(parents=True, exist_ok=True)
            
            # Проверка существования хранилища
            if self._vectorstore_exists():
                logging.info("📦 Загрузка существующего векторного хранилища")
                self.vectorstore = Chroma(
                    persist_directory=str(vectorstore_path),
                    embedding_function=self.embeddings,
                    collection_name="bank_risk_methodology"
                )
            else:
                logging.info("🔨 Создание нового векторного хранилища")
                
                if not self.documents:
                    logging.warning("⚠️ Нет документов для создания хранилища")
                    return
                
                # Создание векторного хранилища
                self.vectorstore = Chroma.from_documents(
                    documents=self.documents,
                    embedding=self.embeddings,
                    persist_directory=str(vectorstore_path),
                    collection_name="bank_risk_methodology"
                )
                
                # Сохранение хранилища
                self.vectorstore.persist()
                logging.info(f"💾 Векторное хранилище сохранено: {len(self.documents)} документов")
            
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации векторного хранилища: {e}")
            raise
    
    def _vectorstore_exists(self) -> bool:
        """Проверка существования векторного хранилища."""
        vectorstore_path = Path(settings.vector_store_path)
        return (vectorstore_path / "chroma.sqlite3").exists()
    
    async def search(self, query: str, limit: int = 5, filter_metadata: Dict = None) -> List[Document]:
        """Поиск релевантных документов."""
        try:
            if not self.vectorstore:
                logging.warning("⚠️ Векторное хранилище не инициализировано")
                return []
            
            # Поиск с фильтрацией по метаданным
            search_kwargs = {"k": limit}
            if filter_metadata:
                search_kwargs["filter"] = filter_metadata
            
            # Семантический поиск
            results = self.vectorstore.similarity_search(query, **search_kwargs)
            
            logging.info(f"🔍 Найдено {len(results)} документов для запроса: {query[:50]}...")
            
            return results
            
        except Exception as e:
            logging.error(f"❌ Ошибка поиска: {e}")
            return []
    
    async def search_with_scores(self, query: str, limit: int = 5) -> List[tuple]:
        """Поиск с оценками релевантности."""
        try:
            if not self.vectorstore:
                return []
            
            results = self.vectorstore.similarity_search_with_score(query, k=limit)
            
            # Фильтрация по порогу релевантности
            filtered_results = [(doc, score) for doc, score in results if score < 0.8]  # Меньше = более релевантно
            
            logging.info(f"🎯 Найдено {len(filtered_results)} релевантных документов")
            
            return filtered_results
            
        except Exception as e:
            logging.error(f"❌ Ошибка поиска с оценками: {e}")
            return []
    
    async def get_context_for_question(self, question: str, difficulty: int = None) -> str:
        """Получение контекста для генерации ответа на вопрос."""
        try:
            # Формирование фильтров по сложности
            filter_metadata = {}
            if difficulty:
                filter_metadata["difficulty"] = difficulty
            
            # Поиск релевантных документов
            relevant_docs = await self.search(question, limit=3, filter_metadata=filter_metadata)
            
            if not relevant_docs:
                # Попытка без фильтра по сложности
                relevant_docs = await self.search(question, limit=3)
            
            # Формирование контекста
            context_parts = []
            for doc in relevant_docs:
                content = doc.page_content
                metadata = doc.metadata
                
                # Добавление метаинформации
                source_info = f"Источник: {metadata.get('source', 'Неизвестно')}"
                if metadata.get('topic'):
                    source_info += f", Тема: {metadata['topic']}"
                if metadata.get('difficulty'):
                    source_info += f", Уровень: {metadata['difficulty']}"
                
                context_parts.append(f"{content}\n({source_info})")
            
            context = "\n\n---\n\n".join(context_parts)
            
            logging.info(f"📝 Сформирован контекст для вопроса: {len(context)} символов")
            
            return context
            
        except Exception as e:
            logging.error(f"❌ Ошибка формирования контекста: {e}")
            return ""
    
    async def add_document(self, content: str, metadata: Dict = None):
        """Добавление нового документа в базу знаний."""
        try:
            if not self.vectorstore:
                logging.warning("⚠️ Векторное хранилище не инициализировано")
                return
            
            # Создание документа
            doc = Document(
                page_content=content,
                metadata=metadata or {}
            )
            
            # Разбиение на чанки
            chunks = self.text_splitter.split_documents([doc])
            
            # Добавление в векторное хранилище
            self.vectorstore.add_documents(chunks)
            self.vectorstore.persist()
            
            logging.info(f"➕ Добавлен документ: {len(chunks)} чанков")
            
        except Exception as e:
            logging.error(f"❌ Ошибка добавления документа: {e}")
    
    async def update_knowledge_base(self):
        """Обновление базы знаний из JSONL файла."""
        try:
            logging.info("🔄 Обновление базы знаний...")
            
            # Очистка текущих документов
            self.documents = []
            
            # Перезагрузка документов
            await self._load_documents_from_jsonl()
            
            # Пересоздание векторного хранилища
            if self.documents:
                vectorstore_path = Path(settings.vector_store_path)
                
                # Удаление старого хранилища
                import shutil
                if vectorstore_path.exists():
                    shutil.rmtree(vectorstore_path)
                
                # Создание нового
                await self._initialize_vectorstore()
                
                logging.info("✅ База знаний обновлена")
            
        except Exception as e:
            logging.error(f"❌ Ошибка обновления базы знаний: {e}")
    
    async def search_by_topic(self, topic: str, limit: int = 10) -> List[Document]:
        """Поиск документов по теме."""
        try:
            filter_metadata = {"topic": topic}
            results = await self.search("", limit=limit, filter_metadata=filter_metadata)
            return results
            
        except Exception as e:
            logging.error(f"❌ Ошибка поиска по теме: {e}")
            return []
    
    async def search_by_difficulty(self, difficulty: int, limit: int = 10) -> List[Document]:
        """Поиск документов по уровню сложности."""
        try:
            filter_metadata = {"difficulty": difficulty}
            results = await self.search("", limit=limit, filter_metadata=filter_metadata)
            return results
            
        except Exception as e:
            logging.error(f"❌ Ошибка поиска по сложности: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики базы знаний."""
        try:
            if not self.vectorstore:
                return {"error": "Векторное хранилище не инициализировано"}
            
            # Подсчет документов по типам и темам
            stats = {
                "total_documents": len(self.documents),
                "by_type": {},
                "by_topic": {},
                "by_difficulty": {}
            }
            
            for doc in self.documents:
                metadata = doc.metadata
                
                # По типу
                doc_type = metadata.get("type", "unknown")
                stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1
                
                # По теме
                topic = metadata.get("topic", "unknown")
                stats["by_topic"][topic] = stats["by_topic"].get(topic, 0) + 1
                
                # По сложности
                difficulty = metadata.get("difficulty", "unknown")
                stats["by_difficulty"][difficulty] = stats["by_difficulty"].get(difficulty, 0) + 1
            
            return stats
            
        except Exception as e:
            logging.error(f"❌ Ошибка получения статистики: {e}")
            return {"error": str(e)}
    
    async def get_related_questions(self, question: str, limit: int = 5) -> List[str]:
        """Получение связанных вопросов."""
        try:
            # Поиск похожих вопросов
            filter_metadata = {"type": "question"}
            results = await self.search(question, limit=limit, filter_metadata=filter_metadata)
            
            related_questions = []
            for doc in results:
                content = doc.page_content
                if content.startswith("Вопрос: "):
                    question_text = content[8:]  # Убираем "Вопрос: "
                    if question_text not in related_questions and question_text != question:
                        related_questions.append(question_text)
            
            return related_questions[:limit]
            
        except Exception as e:
            logging.error(f"❌ Ошибка поиска связанных вопросов: {e}")
            return []
    
    async def get_random_questions_by_difficulty(self, difficulty: int, count: int = 3) -> List[Dict]:
        """Получение случайных вопросов определенной сложности."""
        try:
            import random
            
            # Поиск всех вопросов нужной сложности
            filter_metadata = {"type": "qa_pair", "difficulty": difficulty}
            all_questions = await self.search("", limit=50, filter_metadata=filter_metadata)
            
            if not all_questions:
                return []
            
            # Случайный выбор
            selected = random.sample(all_questions, min(count, len(all_questions)))
            
            questions = []
            for doc in selected:
                content = doc.page_content
                if "\n\n" in content:
                    question_part, answer_part = content.split("\n\n", 1)
                    questions.append({
                        "question": question_part,
                        "answer": answer_part,
                        "metadata": doc.metadata
                    })
            
            return questions
            
        except Exception as e:
            logging.error(f"❌ Ошибка получения случайных вопросов: {e}")
            return []


class QueryProcessor:
    """Класс для обработки и анализа запросов пользователей."""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base
        self.query_cache = {}  # Простой кэш для часто задаваемых вопросов
    
    async def process_query(self, query: str, user_context: Dict = None) -> Dict[str, Any]:
        """Обработка запроса пользователя."""
        try:
            # Нормализация запроса
            normalized_query = self._normalize_query(query)
            
            # Проверка кэша
            if normalized_query in self.query_cache:
                logging.info(f"💨 Ответ из кэша для запроса: {query[:30]}...")
                return self.query_cache[normalized_query]
            
            # Определение типа запроса
            query_type = self._classify_query(query)
            
            # Получение контекста
            user_difficulty = user_context.get("difficulty", 1) if user_context else 1
            context = await self.knowledge_base.get_context_for_question(query, user_difficulty)
            
            # Поиск релевантных документов
            relevant_docs = await self.knowledge_base.search(query, limit=5)
            
            # Формирование результата
            result = {
                "query": query,
                "normalized_query": normalized_query,
                "query_type": query_type,
                "context": context,
                "relevant_documents": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    } for doc in relevant_docs
                ],
                "confidence": self._calculate_confidence(relevant_docs),
                "suggestions": await self.knowledge_base.get_related_questions(query, 3)
            }
            
            # Кэширование результата
            self.query_cache[normalized_query] = result
            
            return result
            
        except Exception as e:
            logging.error(f"❌ Ошибка обработки запроса: {e}")
            return {"error": str(e)}
    
    def _normalize_query(self, query: str) -> str:
        """Нормализация запроса."""
        # Приведение к нижнему регистру
        normalized = query.lower().strip()
        
        # Удаление лишних пробелов
        normalized = " ".join(normalized.split())
        
        # Удаление знаков препинания в конце
        normalized = normalized.rstrip(".,!?;:")
        
        return normalized
    
    def _classify_query(self, query: str) -> str:
        """Классификация типа запроса."""
        query_lower = query.lower()
        
        # Определение типа по ключевым словам
        if any(word in query_lower for word in ["что такое", "что означает", "определение"]):
            return "definition"
        elif any(word in query_lower for word in ["как", "каким образом", "способ"]):
            return "instruction"
        elif any(word in query_lower for word in ["почему", "зачем", "причина"]):
            return "explanation"
        elif any(word in query_lower for word in ["рассчитать", "формула", "расчет"]):
            return "calculation"
        elif any(word in query_lower for word in ["пример", "сценарий", "случай"]):
            return "example"
        elif query_lower.endswith("?"):
            return "question"
        else:
            return "general"
    
    def _calculate_confidence(self, documents: List[Document]) -> float:
        """Расчет уверенности в ответе на основе релевантности документов."""
        if not documents:
            return 0.0
        
        # Простая метрика на основе количества найденных документов
        confidence = min(len(documents) / 5.0, 1.0)
        
        # Бонус за метаданные
        for doc in documents:
            if doc.metadata.get("type") == "qa_pair":
                confidence += 0.1
            if doc.metadata.get("source") == "methodology_jsonl":
                confidence += 0.05
        
        return min(confidence, 1.0)
    
    def clear_cache(self):
        """Очистка кэша запросов."""
        self.query_cache.clear()
        logging.info("🗑️ Кэш запросов очищен")


# Утилиты для работы с JSONL
class JSONLProcessor:
    """Класс для обработки JSONL файлов."""
    
    @staticmethod
    def validate_jsonl_file(file_path: str) -> Dict[str, Any]:
        """Валидация JSONL файла."""
        try:
            stats = {
                "total_lines": 0,
                "valid_lines": 0,
                "invalid_lines": 0,
                "errors": []
            }
            
            with open(file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    stats["total_lines"] += 1
                    
                    try:
                        data = json.loads(line.strip())
                        
                        # Проверка обязательных полей
                        if "prompt" in data and "response" in data:
                            stats["valid_lines"] += 1
                        else:
                            stats["invalid_lines"] += 1
                            stats["errors"].append(f"Строка {line_num}: отсутствуют обязательные поля")
                    
                    except json.JSONDecodeError as e:
                        stats["invalid_lines"] += 1
                        stats["errors"].append(f"Строка {line_num}: ошибка JSON - {e}")
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def convert_to_jsonl(input_data: List[Dict], output_path: str):
        """Конвертация данных в JSONL формат."""
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                for item in input_data:
                    json_line = json.dumps(item, ensure_ascii=False)
                    file.write(json_line + '\n')
            
            logging.info(f"💾 Сохранено {len(input_data)} записей в {output_path}")
            
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения JSONL: {e}")
            raise