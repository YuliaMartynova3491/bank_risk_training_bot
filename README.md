# 🏦 AI-Агент для обучения банковским рискам

Интеллектуальная система обучения управлению рисками непрерывности деятельности банка на базе Telegram бота с адаптивным AI-агентом.

## 🎯 Возможности

- **🤖 Адаптивное обучение**: AI автоматически подстраивает сложность вопросов под уровень пользователя
- **📚 RAG система**: База знаний на основе методики банка для точных ответов  
- **🧠 LangGraph агент**: Сложная логика обучения с состояниями и переходами
- **👥 Многопользовательский доступ**: Параллельное обучение нескольких сотрудников
- **📊 Персонализация**: Индивидуальный прогресс и рекомендации
- **💬 AI-чат**: Возможность задавать вопросы AI-ассистенту в любое время

## 🏗️ Архитектура

```
├── AI-Agent (LangGraph)          # Адаптивное обучение
├── RAG System (ChromaDB)         # База знаний  
├── Telegram Bot (PTB 20.7)      # Интерфейс
├── Database (SQLite/PostgreSQL)  # Данные пользователей
├── LLM Integration (Qwen2.5)     # Генерация контента
└── Services                      # Бизнес-логика
```

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.8+
- LM Studio (для локальных моделей)
- Qwen2.5-14B-Instruct (загружена в LM Studio)

### Установка

1. **Клонирование репозитория:**
```bash
git clone https://github.com/YuliaMartynova3491/bank_risk_training_bot.git
cd bank_risk_training_bot
```

2. **Создание виртуального окружения:**
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# или
venv\Scripts\activate     # Windows
```

3. **Установка зависимостей:**
```bash
pip install -r requirements.txt
```

4. **Настройка окружения:**
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

5. **Получение токена бота:**
- Найдите @BotFather в Telegram
- Создайте нового бота: `/newbot`
- Скопируйте токен в `.env` файл

6. **Запуск LM Studio:**
- Откройте LM Studio
- Убедитесь что Qwen2.5-14B-Instruct загружен
- Запустите локальный сервер (Server → Start Server)

7. **Запуск бота:**
```bash
python main.py
```

## ⚙️ Конфигурация

### Основные настройки в .env:

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Database  
DATABASE_URL=sqlite+aiosqlite:///./bank_training.db

# LM Studio (локальная модель)
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=qwen2.5-14b-instruct
LLM_PROVIDER=lm_studio

# Обучение
MIN_LESSON_SCORE=80
QUESTIONS_PER_LESSON=3
MAX_DIFFICULTY_LEVEL=5
```

## 📚 База знаний

База знаний создается из файла `ai_agent/rag/data/methodology.jsonl`:

```json
{
  "prompt": "Что такое риск нарушения непрерывности деятельности?",
  "response": "Подробный ответ...",
  "metadata": {
    "difficulty": 1,
    "topic": "Основы",
    "source": "п.1.2"
  }
}
```

## 🎮 Использование

1. **Запуск обучения**: `/start` → "🎓 Начать обучение"
2. **AI-чат**: Задайте любой вопрос по методике
3. **Прогресс**: Отслеживайте достижения и статистику
4. **Адаптация**: AI автоматически подстраивает сложность

## 🛠️ Разработка

### Структура проекта:

```
bank_risk_training_bot/
├── main.py                     # Точка входа
├── config/                     # Конфигурация
├── bot/handlers/               # Обработчики Telegram
├── ai_agent/                   # AI-агент и RAG
├── database/                   # Модели БД
├── services/                   # Бизнес-логика
└── tests/                      # Тесты
```

### Добавление новых вопросов:

1. Отредактируйте `methodology.jsonl`
2. Перезапустите бота для обновления векторной БД

### Тестирование:

```bash
pytest tests/
```

## 📊 Мониторинг

- Логи выводятся в консоль с цветовой подсветкой
- Статистика доступна через бота
- Прогресс пользователей сохраняется в БД

## 🤝 Участие в разработке

1. Fork репозитория
2. Создайте feature branch: `git checkout -b feature/new-feature`
3. Commit изменения: `git commit -m 'Add new feature'`
4. Push в branch: `git push origin feature/new-feature`  
5. Создайте Pull Request

## 📝 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 🆘 Поддержка

- Создайте [Issue](https://github.com/YuliaMartynova3491/bank_risk_training_bot/issues)
- Опишите проблему с логами
- Укажите версию Python и ОС

## 🔮 Roadmap

- [ ] Веб-интерфейс для администрирования
- [ ] Экспорт отчетов в Excel/PDF
- [ ] Интеграция с корпоративным AD
- [ ] Мобильное приложение
- [ ] Голосовые сообщения
- [ ] Мультиязычность

---

**Создано для эффективного обучения банковских сотрудников управлению рисками непрерывности деятельности** 🏦✨