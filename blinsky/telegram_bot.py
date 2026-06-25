"""
telegram_bot.py — Phase 3 Telegram integration for Blinsky.

Bridges Telegram messages through the same OllamaProcessor → ToolProcessor
pipeline used by api/app.py, giving each chat_id its own conversation history.

Dependencies:
    pip install python-telegram-bot>=20.0
"""
from __future__ import annotations

import os
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from blinsky.processors.ollama_processor import OllamaProcessor, _strip_tool_tags
from blinsky.processors.tool_processor import ToolProcessor

# ---------------------------------------------------------------------------
# Greeting / help text
# ---------------------------------------------------------------------------
_GREETING = (
    "👋 Hi! I'm *Blinsky*, your local AI assistant.\n\n"
    "Send me any message and I'll do my best to help.\n"
    "Type /help to see available commands."
)

_HELP = (
    "*Blinsky commands*\n\n"
    "/start — show welcome message\n"
    "/help  — list available commands\n"
    "/clear — wipe this chat's conversation history\n\n"
    "Just type anything else and I'll answer you!"
)


class TelegramBridge:
    """
    Connects Telegram to the Blinsky Ollama + Tool pipeline.

    Each Telegram ``chat_id`` receives an independent :class:`OllamaProcessor`
    instance so conversation histories never bleed between users or chats.
    """

    def __init__(self) -> None:
        # Lazily populated: chat_id → OllamaProcessor
        self._chats: dict[int, OllamaProcessor] = {}

        # Shared ToolProcessor — stateless, safe to reuse
        self._tool_processor = ToolProcessor()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_ollama(self, chat_id: int) -> OllamaProcessor:
        """Return (or create) the OllamaProcessor for *chat_id*."""
        if chat_id not in self._chats:
            self._chats[chat_id] = OllamaProcessor()
        return self._chats[chat_id]

    async def _process_message(self, chat_id: int, user_text: str) -> str:
        """
        Run user_text through OllamaProcessor then ToolProcessor (if needed).

        Mirrors the logic in api/app.py so both surfaces behave identically.
        Returns a clean, tag-free reply string.
        """
        ollama = self._get_ollama(chat_id)

        reply, tool_call = ollama.process(user_text)

        if tool_call:
            # Execute the requested tool
            result = self._tool_processor.execute(tool_call)

            # Feed the tool result back to Ollama for a natural follow-up
            follow_up = (
                f"Tool '{tool_call.get('name')}' returned:\n{result}\n\n"
                "Using this result, give the user a concise, helpful reply. "
                "Do NOT output any <tool> tags. Just answer naturally."
            )
            reply, _ = ollama.process(follow_up)

        # Final safety net — strip any <tool> garbage that leaked through
        reply = _strip_tool_tags(reply)

        if not reply:
            reply = "I ran into an issue generating a response. Please try again."

        # Persist the turn in this chat's history
        ollama.add_turn(user_text, reply)

        return reply

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    async def _cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send a greeting when the user issues /start."""
        await update.message.reply_text(_GREETING, parse_mode="Markdown")

    async def _cmd_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """List all available commands."""
        await update.message.reply_text(_HELP, parse_mode="Markdown")

    async def _cmd_clear(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Clear the conversation history for this chat."""
        chat_id = update.effective_chat.id
        if chat_id in self._chats:
            self._chats[chat_id].history.clear()
        await update.message.reply_text(
            "🗑️ Conversation history cleared. Let's start fresh!"
        )

    # ------------------------------------------------------------------
    # Text message handler
    # ------------------------------------------------------------------

    async def _handle_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle any regular (non-command) text message.

        Shows a typing indicator while waiting for Ollama, then replies.
        """
        chat_id = update.effective_chat.id
        user_text = (update.message.text or "").strip()

        if not user_text:
            return  # Ignore empty messages

        # Show "typing..." action while we wait for Ollama
        await context.bot.send_chat_action(
            chat_id=chat_id, action=ChatAction.TYPING
        )

        try:
            reply = await self._process_message(chat_id, user_text)
        except Exception as exc:
            print(f"[Telegram] Error processing message for chat {chat_id}: {exc}")
            reply = (
                "Something went wrong while processing your message. "
                "Please try again in a moment."
            )

        # Always send a reply — never let the bot go silent
        try:
            await update.message.reply_text(reply)
        except Exception as exc:
            print(f"[Telegram] Failed to send reply to chat {chat_id}: {exc}")

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """
        Build and start the Telegram bot.

        Reads ``TELEGRAM_BOT_TOKEN`` from the environment.
        Prints an informative message if the token is absent, then returns
        without crashing so callers can handle the absence gracefully.
        """
        token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")

        if not token:
            print(
                "[Telegram] Bot requires TELEGRAM_BOT_TOKEN in .env\n"
                "           Add:  TELEGRAM_BOT_TOKEN=<your_bot_token>"
            )
            return

        # Build the Application using the v20+ builder pattern
        app: Application = Application.builder().token(token).build()

        # Register command handlers
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("help", self._cmd_help))
        app.add_handler(CommandHandler("clear", self._cmd_clear))

        # Register handler for all plain text messages (not commands)
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text)
        )

        # Announce startup with the bot's actual username
        bot_info = await app.bot.get_me()
        print(f"[Telegram] Bot started as @{bot_info.username}")

        # Start long-polling (blocks until interrupted)
        await app.run_polling(drop_pending_updates=True)
