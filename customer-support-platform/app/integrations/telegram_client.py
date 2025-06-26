"""Telegram bot client using aiogram."""
from typing import Optional, List, Dict, Any
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold
import asyncio

from app.config import settings
from app.core.logging import logger

# Initialize bot and dispatcher
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


class TelegramClient:
    """Telegram client for configuration only."""
    def __init__(self):
        self.bot = bot
        self.dp = dp


# Initialize global telegram client
telegram_client = TelegramClient()


async def start_polling():
    """Start the bot polling."""
    try:
        logger.info("Starting Telegram bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {str(e)}")
        raise
