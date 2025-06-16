"""
Утилиты для работы со стикерами в боте.
Использует конкретные ID стикеров, предоставленные в ТЗ.
"""

import random
import logging
from config.settings import Stickers


async def send_welcome_sticker(context, chat_id):
    """Отправка приветственного стикера (случайный из двух)."""
    try:
        welcome_stickers = [
            "CAACAgIAAxkBAAEOd6RoIsd8Z1Gz2JyvVPrxpwRugDF89wAC8EAAAgMdyUh6q-4BL3FQLzYE",
            "CAACAgIAAxkBAAEOd6xoIshSMujqTxf8Od_p7PLDGn7sUwACWToAAqePcUmYZialrHxKnTYE"
        ]
        sticker_id = random.choice(welcome_stickers)
        
        await context.bot.send_sticker(
            chat_id=chat_id,
            sticker=sticker_id
        )
        return True
        
    except Exception as e:
        logging.error(f"Ошибка отправки приветственного стикера: {e}")
        return False


async def send_correct_answer_sticker(context, chat_id, is_first_correct=True):
    """Отправка стикера за правильный ответ."""
    try:
        if is_first_correct:
            # При первом правильном ответе
            sticker_id = "CAACAgIAAxkBAAEOd6hoIsgIXelJD9h0RgVTxLtEz_ZgMgACky4AAgFM6UhFC9JlyfY5rzYE"
        else:
            # При последующих правильных ответах
            sticker_id = "CAACAgIAAxkBAAEOd6poIsggr—5-2bwnZt7t_2pJP9HWwACyCoAAkj3cUng5lb0xkBC6DYE"
        
        await context.bot.send_sticker(
            chat_id=chat_id,
            sticker=sticker_id
        )
        return True
        
    except Exception as e:
        logging.error(f"Ошибка отправки стикера правильного ответа: {e}")
        return False


async def send_incorrect_answer_sticker(context, chat_id, is_first_incorrect=True):
    """Отправка стикера за неправильный ответ."""
    try:
        if is_first_incorrect:
            # При первом неправильном ответе
            sticker_id = "CAACAgIAAxkBAAEOd6JoIsc8ZgvKw1T8QqL2CNIpNtLUzAAC_0gAApjKwEh4Jj7i8mL2AjYE"
        else:
            # При повторном неправильном ответе (последовательно)
            sticker_id = "CAACAgIAAxkBAAEOd6ZoIsfmsGJP3o0KdTMiriW8U9sVvwACHEUAAvkKiEjOqMQN3AH2PTYE"
        
        await context.bot.send_sticker(
            chat_id=chat_id,
            sticker=sticker_id
        )
        return True
        
    except Exception as e:
        logging.error(f"Ошибка отправки стикера неправильного ответа: {e}")
        return False


async def send_lesson_completed_sticker(context, chat_id):
    """Отправка стикера при успешном прохождении урока."""
    try:
        sticker_id = "CAACAgIAAxkBAAEOd65oIsiE9oHP2Cxsg9wkj1LXFi0L1AACR18AAuphSUoma5l9yrkFmjYE"
        
        await context.bot.send_sticker(
            chat_id=chat_id,
            sticker=sticker_id
        )
        return True
        
    except Exception as e:
        logging.error(f"Ошибка отправки стикера завершения урока: {e}")
        return False


async def send_topic_completed_sticker(context, chat_id):
    """Отправка стикера при успешном прохождении темы."""
    try:
        sticker_id = "CAACAgIAAxkBAAEOd7JoIspvfu0_4EUpFnUcpq6OUjVMEAACRFkAAnnRSUru1p89ZmyntTYE"
        
        await context.bot.send_sticker(
            chat_id=chat_id,
            sticker=sticker_id
        )
        return True
        
    except Exception as e:
        logging.error(f"Ошибка отправки стикера завершения темы: {e}")
        return False


async def send_insufficient_score_sticker(context, chat_id):
    """Отправка стикера если не набрано 80% для успешного завершения урока."""
    try:
        sticker_id = "CAACAgIAAxkBAAEOd7BoIsok2pkQSuPXBxRVf26hil-35gACEywAArBkcEno5QGUqynBvzYE"
        
        await context.bot.send_sticker(
            chat_id=chat_id,
            sticker=sticker_id
        )
        return True
        
    except Exception as e:
        logging.error(f"Ошибка отправки стикера недостаточного результата: {e}")
        return False


async def send_contextual_sticker(context, chat_id, is_correct, consecutive_count=1):
    """Отправка контекстного стикера в зависимости от результата."""
    try:
        if is_correct:
            await send_correct_answer_sticker(context, chat_id, consecutive_count == 1)
        else:
            await send_incorrect_answer_sticker(context, chat_id, consecutive_count == 1)
        return True
        
    except Exception as e:
        logging.error(f"Ошибка отправки контекстного стикера: {e}")
        return False


# Совместимость со старым API
async def send_random_sticker(context, chat_id, sticker_type):
    """Отправка стикера определенного типа (для совместимости)."""
    try:
        if sticker_type == "welcome":
            return await send_welcome_sticker(context, chat_id)
        elif sticker_type == "first_correct":
            return await send_correct_answer_sticker(context, chat_id, True)
        elif sticker_type == "subsequent_correct":
            return await send_correct_answer_sticker(context, chat_id, False)
        elif sticker_type == "lesson_completed":
            return await send_lesson_completed_sticker(context, chat_id)
        elif sticker_type == "topic_completed":
            return await send_topic_completed_sticker(context, chat_id)
        elif sticker_type == "first_incorrect":
            return await send_incorrect_answer_sticker(context, chat_id, True)
        elif sticker_type == "subsequent_incorrect":
            return await send_incorrect_answer_sticker(context, chat_id, False)
        elif sticker_type == "insufficient_score":
            return await send_insufficient_score_sticker(context, chat_id)
        else:
            logging.warning(f"Неизвестный тип стикера: {sticker_type}")
            return False
        
    except Exception as e:
        logging.error(f"Ошибка отправки стикера: {e}")
        return False