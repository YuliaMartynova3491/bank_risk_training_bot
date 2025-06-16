"""
Обработчики команд запуска AI-агента.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from config.settings import settings, START_COMMANDS, MessageTemplates
from bot.keyboards.main_menu import get_main_menu_keyboard
from bot.utils.stickers import send_welcome_sticker


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        logging.info(f"👤 Пользователь {user.id} ({user.username}) запустил бота")
        
        # Создание или обновление пользователя в базе данных
        try:
            from database.database import create_or_update_user
            db_user = await create_or_update_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
        except Exception as e:
            logging.warning(f"⚠️ Проблема с БД: {e}")
            db_user = None
        
        # Отправка приветственного стикера
        await send_welcome_sticker(context, chat_id)
        
        # Отправка приветственного сообщения
        welcome_text = MessageTemplates.WELCOME
        if user.first_name:
            welcome_text = welcome_text.replace("Коллега", user.first_name)
        
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode='HTML'
        )
        
        # Сохранение состояния пользователя
        context.user_data['user_id'] = db_user.id if db_user else None
        context.user_data['telegram_id'] = user.id
        context.user_data['current_state'] = 'main_menu'
        
        logging.info(f"✅ Пользователь {user.id} успешно зарегистрирован")
        
    except Exception as e:
        logging.error(f"❌ Ошибка в start_command: {e}")
        await update.message.reply_text(
            "😔 Произошла ошибка при запуске. Попробуйте еще раз.",
            reply_markup=get_main_menu_keyboard()
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    try:
        await update.message.reply_text(
            text=MessageTemplates.HELP,
            reply_markup=get_main_menu_keyboard(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка в help_command: {e}")
        await update.message.reply_text(
            "😔 Произошла ошибка при получении справки.",
            reply_markup=get_main_menu_keyboard()
        )


async def start_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых команд запуска."""
    message_text = update.message.text.lower().strip()
    
    # Проверяем, является ли сообщение командой запуска
    if any(cmd.lower() in message_text for cmd in START_COMMANDS):
        await start_command(update, context)
    else:
        # Простой ответ для текстовых сообщений
        await update.message.reply_text(
            "👋 Привет! Используйте /start для начала работы с AI-агентом!",
            reply_markup=get_main_menu_keyboard()
        )


def register_start_handlers(application):
    """Регистрация обработчиков команд запуска."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))