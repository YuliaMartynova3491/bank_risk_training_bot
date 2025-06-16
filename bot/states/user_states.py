"""
Состояния пользователей для ConversationHandler.
"""

from enum import Enum

class UserStates(Enum):
    """Состояния пользователя в процессе обучения."""
    
    MAIN_MENU = "main_menu"
    LEARNING = "learning"
    ANSWERING_QUESTION = "answering_question" 
    ASKING_AI = "asking_ai"
    WAITING_FOR_QUESTION = "waiting_for_question"
    SETTINGS = "settings"