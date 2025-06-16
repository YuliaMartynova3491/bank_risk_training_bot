"""
Модели базы данных для AI-агента обучения банковским рискам.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()


class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)  
    last_name = Column(String(255), nullable=True)
    
    # Настройки пользователя
    current_difficulty_level = Column(Integer, default=1)
    preferred_language = Column(String(10), default="ru")
    notifications_enabled = Column(Boolean, default=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Topic(Base):
    """Модель темы обучения."""
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    difficulty_level = Column(Integer, nullable=False)
    order_index = Column(Integer, nullable=False)
    
    # Метаданные - переименовано из metadata
    meta_data = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Topic(title={self.title}, difficulty={self.difficulty_level})>"


class Lesson(Base):
    """Модель урока."""
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    
    difficulty_level = Column(Integer, nullable=False)
    order_index = Column(Integer, nullable=False)
    estimated_duration_minutes = Column(Integer, default=15)
    
    learning_objectives = Column(JSON, default=list)
    key_concepts = Column(JSON, default=list)
    prerequisites = Column(JSON, default=list)
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    topic = relationship("Topic")
    
    def __repr__(self):
        return f"<Lesson(title={self.title}, difficulty={self.difficulty_level})>"


class Question(Base):
    """Модель вопроса."""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)
    difficulty_level = Column(Integer, nullable=False)
    
    options = Column(JSON, default=list)
    correct_answer = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    
    scenario_context = Column(Text, nullable=True)
    scenario_meta_data = Column(JSON, default=dict)
    
    tags = Column(JSON, default=list)
    estimated_time_seconds = Column(Integer, default=60)
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    lesson = relationship("Lesson")
    
    def __repr__(self):
        return f"<Question(type={self.question_type}, difficulty={self.difficulty_level})>"


class LearningSession(Base):
    """Модель сессии обучения."""
    __tablename__ = "learning_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    session_state = Column(String(50), default="active")
    current_topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    current_lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    
    total_questions_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)
    
    agent_state = Column(JSON, default=dict)
    context_history = Column(JSON, default=list)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User")
    
    def __repr__(self):
        return f"<LearningSession(user_id={self.user_id}, state={self.session_state})>"


class QuestionAttempt(Base):
    """Модель попытки ответа на вопрос."""
    __tablename__ = "question_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=True)
    
    user_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    confidence_score = Column(Float, nullable=True)
    
    time_spent_seconds = Column(Integer, nullable=True)
    
    ai_feedback = Column(Text, nullable=True)
    improvement_suggestions = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")
    question = relationship("Question")
    session = relationship("LearningSession", foreign_keys=[session_id])
    
    def __repr__(self):
        return f"<QuestionAttempt(user_id={self.user_id}, is_correct={self.is_correct})>"


class UserProgress(Base):
    """Модель прогресса пользователя."""
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    
    status = Column(String(50), default="not_started")
    completion_percentage = Column(Float, default=0.0)
    mastery_level = Column(Float, default=0.0)
    
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)
    average_score = Column(Float, default=0.0)
    time_spent_minutes = Column(Integer, default=0)
    
    recommended_next_difficulty = Column(Integer, nullable=True)
    weakness_areas = Column(JSON, default=list)
    strength_areas = Column(JSON, default=list)
    
    first_attempt_at = Column(DateTime(timezone=True), nullable=True)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User")
    lesson = relationship("Lesson")
    
    def __repr__(self):
        return f"<UserProgress(user_id={self.user_id}, lesson_id={self.lesson_id}, status={self.status})>"


class ChatMessage(Base):
    """Модель сообщений чата с AI-ассистентом."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    message_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    
    context_used = Column(JSON, default=list)
    confidence_score = Column(Float, nullable=True)
    
    meta_data = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<ChatMessage(user_id={self.user_id}, type={self.message_type})>"


class SystemNotification(Base):
    """Модель системных уведомлений."""
    __tablename__ = "system_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    notification_type = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    
    is_sent = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    meta_data = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<SystemNotification(user_id={self.user_id}, type={self.notification_type})>"
