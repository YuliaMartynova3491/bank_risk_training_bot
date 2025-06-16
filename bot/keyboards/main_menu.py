"""
Клавиатуры для главного меню AI-агента.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Получение клавиатуры главного меню."""
    keyboard = [
        [
            InlineKeyboardButton("🎓 Начать обучение", callback_data="start_learning"),
            InlineKeyboardButton("❓ Задать вопрос AI", callback_data="ask_question")
        ],
        [
            InlineKeyboardButton("📊 Мой прогресс", callback_data="show_progress"),
            InlineKeyboardButton("📚 Инструкция", callback_data="show_help")
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton("📈 Статистика", callback_data="analytics")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_learning_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура меню обучения."""
    keyboard = [
        [
            InlineKeyboardButton("▶️ Продолжить урок", callback_data="continue_lesson"),
            InlineKeyboardButton("🔄 Начать заново", callback_data="restart_learning")
        ],
        [
            InlineKeyboardButton("📋 Выбрать тему", callback_data="select_topic"),
            InlineKeyboardButton("🎯 Тестирование", callback_data="take_test")
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_question_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для работы с вопросами."""
    keyboard = [
        [
            InlineKeyboardButton("💬 Задать новый вопрос", callback_data="new_question"),
            InlineKeyboardButton("📜 История вопросов", callback_data="question_history")
        ],
        [
            InlineKeyboardButton("🔍 Поиск в методике", callback_data="search_methodology"),
            InlineKeyboardButton("📋 Частые вопросы", callback_data="faq")
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_progress_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура меню прогресса."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Общий прогресс", callback_data="overall_progress"),
            InlineKeyboardButton("📈 По темам", callback_data="topic_progress")
        ],
        [
            InlineKeyboardButton("🏆 Достижения", callback_data="achievements"),
            InlineKeyboardButton("📅 История обучения", callback_data="learning_history")
        ],
        [
            InlineKeyboardButton("📑 Отчет PDF", callback_data="generate_report"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек."""
    keyboard = [
        [
            InlineKeyboardButton("🔔 Уведомления", callback_data="notification_settings"),
            InlineKeyboardButton("🌍 Язык", callback_data="language_settings")
        ],
        [
            InlineKeyboardButton("🎯 Сложность", callback_data="difficulty_settings"),
            InlineKeyboardButton("⏰ Напоминания", callback_data="reminder_settings")
        ],
        [
            InlineKeyboardButton("🔄 Сбросить прогресс", callback_data="reset_progress"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("❌ Нет", callback_data=f"cancel_{action}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_difficulty_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора уровня сложности."""
    keyboard = [
        [
            InlineKeyboardButton("🟢 Начинающий", callback_data="difficulty_1"),
            InlineKeyboardButton("🟡 Базовый", callback_data="difficulty_2")
        ],
        [
            InlineKeyboardButton("🟠 Продвинутый", callback_data="difficulty_3"),
            InlineKeyboardButton("🔴 Эксперт", callback_data="difficulty_4")
        ],
        [
            InlineKeyboardButton("🟣 Мастер", callback_data="difficulty_5"),
            InlineKeyboardButton("🔙 Назад", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_notification_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    """Клавиатура настройки уведомлений."""
    status_text = "Выключить 🔕" if enabled else "Включить 🔔"
    status_action = "disable_notifications" if enabled else "enable_notifications"
    
    keyboard = [
        [
            InlineKeyboardButton(status_text, callback_data=status_action)
        ],
        [
            InlineKeyboardButton("⏰ Время напоминаний", callback_data="reminder_time"),
            InlineKeyboardButton("📅 Частота", callback_data="reminder_frequency")
        ],
        [
            InlineKeyboardButton("🔙 Назад", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Простая клавиатура возврата в главное меню."""
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_navigation_keyboard(current_step: int, total_steps: int, lesson_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура навигации по урокам."""
    keyboard = []
    
    # Первая строка - навигация
    nav_row = []
    if current_step > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"lesson_prev_{lesson_id}"))
    
    nav_row.append(InlineKeyboardButton(f"{current_step}/{total_steps}", callback_data="lesson_info"))
    
    if current_step < total_steps:
        nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f"lesson_next_{lesson_id}"))
    
    keyboard.append(nav_row)
    
    # Вторая строка - действия
    action_row = [
        InlineKeyboardButton("🔄 Повторить", callback_data=f"lesson_repeat_{lesson_id}"),
        InlineKeyboardButton("📝 Заметки", callback_data=f"lesson_notes_{lesson_id}")
    ]
    keyboard.append(action_row)
    
    # Третья строка - выход
    keyboard.append([
        InlineKeyboardButton("📚 Меню обучения", callback_data="learning_menu"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_answer_keyboard(question_id: int, options: list) -> InlineKeyboardMarkup:
    """Клавиатура для ответа на вопрос."""
    keyboard = []
    
    # Добавляем варианты ответов (максимум 4 в ряд)
    for i, option in enumerate(options):
        callback_data = f"answer_{question_id}_{i}"
        # Ограничиваем длину текста на кнопке
        button_text = option[:50] + "..." if len(option) > 50 else option
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Добавляем кнопки управления
    control_row = [
        InlineKeyboardButton("❓ Подсказка", callback_data=f"hint_{question_id}"),
        InlineKeyboardButton("⏭️ Пропустить", callback_data=f"skip_{question_id}")
    ]
    keyboard.append(control_row)
    
    # Кнопка выхода
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)