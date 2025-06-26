from typing import Any, Optional
from uuid import UUID

from aiogram import Bot, Dispatcher, types
from fastapi import HTTPException, status

from app.config import settings
from app.core.redis import Cache
from app.services.ticket_service import TicketService


class TelegramService:
    def __init__(self, db: Any):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher(self.bot)
        self.cache_prefix = "telegram:"
        self.db = db
        # Register message handlers
        self.setup_handlers()

    def setup_handlers(self):
        """Setup message handlers for the bot."""
        @self.dp.message_handler(commands=['start'])
        async def start_handler(message: types.Message):
            await self._handle_start(message)

        @self.dp.message_handler(commands=['help'])
        async def help_handler(message: types.Message):
            await self._handle_help(message)

        @self.dp.message_handler()
        async def message_handler(message: types.Message):
            await self._handle_message(message)

    async def _handle_start(self, message: types.Message):
        """Handle /start command."""
        welcome_text = (
            "Welcome to our Customer Support Bot! 👋\n\n"
            "You can create a support ticket by simply sending "
            "me your question or issue.\n\n"
            "Use /help to see all available commands."
        )
        await message.reply(welcome_text)

    async def _handle_help(self, message: types.Message):
        """Handle /help command."""
        help_text = (
            "Available commands:\n\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/status <ticket_id> - Check ticket status\n\n"
            "Simply send me a message to create a new support ticket!"
        )
        await message.reply(help_text)

    async def _handle_message(self, message: types.Message):
        """Handle regular messages and create tickets."""
        try:
            # Create ticket from message

            ticket_data = {
                "subject": "Telegram Support Request",
                "description": message.text,
                "channel": "telegram",
                "organization_id": settings.DEFAULT_ORGANIZATION_ID,  # Ensure this is set in config
                "customer_id": None  # Optionally resolve customer by Telegram ID
            }


            ticket_service = TicketService(self.db)
            ticket = await ticket_service.create_ticket(ticket_data)

            # Cache the telegram chat ID with ticket ID
            await Cache.set(
                f"{self.cache_prefix}ticket:{ticket.id}",
                message.chat.id
            )

            await message.reply(
                f"Thanks for reaching out! I've created ticket "
                f"#{ticket.id} for you. We'll get back to you soon!"
            )
        except Exception as e:
            await message.reply(
                "Sorry, I couldn't create your ticket. "
                "Please try again later."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to handle telegram message: {str(e)}"
            )

    async def send_response(
        self,
        ticket_id: UUID,
        response: str
    ) -> bool:
        """Send ticket response back to customer."""
        try:
            # Get chat ID from cache
            chat_id = await Cache.get(
                f"{self.cache_prefix}ticket:{ticket_id}"
            )
            if not chat_id:
                raise ValueError("Chat ID not found for ticket")

            # Send response
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"Update for ticket #{ticket_id}:\n\n{response}"
            )
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send telegram response: {str(e)}"
            )

    async def start_polling(self):
        """Start polling for telegram updates."""
        try:
            await self.dp.start_polling()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start telegram polling: {str(e)}"
            )

    async def stop_polling(self):
        """Stop polling for telegram updates."""
        try:
            await self.dp.stop_polling()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stop telegram polling: {str(e)}"
            )