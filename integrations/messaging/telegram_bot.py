"""
Conecta Plus - Bot Telegram
Permite envio de mensagens e notificações via Telegram

Dependências:
    pip install python-telegram-bot

Uso:
    from telegram_bot import TelegramBot

    bot = TelegramBot("seu_bot_token")

    # Enviar mensagem
    await bot.send_message(chat_id, "Olá!")

    # Enviar com botões
    await bot.send_message_with_buttons(chat_id, "Escolha:", [
        {"text": "Opção 1", "callback_data": "opt1"},
        {"text": "Opção 2", "callback_data": "opt2"}
    ])
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParseMode(Enum):
    """Modos de formatação de texto"""
    MARKDOWN = "Markdown"
    MARKDOWN_V2 = "MarkdownV2"
    HTML = "HTML"


@dataclass
class TelegramUser:
    """Usuário do Telegram"""
    id: int
    first_name: str
    last_name: Optional[str]
    username: Optional[str]
    is_bot: bool


@dataclass
class TelegramMessage:
    """Mensagem do Telegram"""
    message_id: int
    chat_id: int
    from_user: TelegramUser
    text: str
    date: int
    reply_to_message: Optional['TelegramMessage'] = None


class TelegramBot:
    """
    Bot Telegram para notificações e interações

    Funcionalidades:
    - Envio de mensagens de texto
    - Envio de mídia (fotos, documentos, vídeos)
    - Mensagens com botões inline
    - Teclados personalizados
    - Comandos
    - Webhooks ou polling
    """

    def __init__(self, token: str):
        """
        Inicializa o bot

        Args:
            token: Token do bot obtido do @BotFather
        """
        self.token = token
        self._application = None
        self._command_handlers = {}
        self._message_handlers = []
        self._callback_handlers = {}

    async def _get_application(self):
        """Obtém ou cria a aplicação do bot"""
        if self._application is None:
            try:
                from telegram.ext import Application
                self._application = Application.builder().token(self.token).build()
            except ImportError:
                logger.error("Biblioteca python-telegram-bot não instalada")
                raise

        return self._application

    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: ParseMode = None,
        disable_notification: bool = False,
        reply_to_message_id: int = None
    ) -> int:
        """
        Envia mensagem de texto

        Args:
            chat_id: ID do chat ou username (@canal)
            text: Texto da mensagem
            parse_mode: Modo de formatação
            disable_notification: Enviar silenciosamente
            reply_to_message_id: ID da mensagem para responder

        Returns:
            ID da mensagem enviada
        """
        try:
            from telegram import Bot

            bot = Bot(token=self.token)

            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode.value if parse_mode else None,
                disable_notification=disable_notification,
                reply_to_message_id=reply_to_message_id
            )

            logger.info(f"Mensagem enviada para {chat_id}: {message.message_id}")
            return message.message_id

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            raise

    async def send_message_with_buttons(
        self,
        chat_id: Union[int, str],
        text: str,
        buttons: List[List[Dict[str, str]]],
        parse_mode: ParseMode = None
    ) -> int:
        """
        Envia mensagem com botões inline

        Args:
            chat_id: ID do chat
            text: Texto da mensagem
            buttons: Matriz de botões [[{"text": "Btn", "callback_data": "data"}]]
            parse_mode: Modo de formatação

        Returns:
            ID da mensagem enviada
        """
        try:
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

            bot = Bot(token=self.token)

            keyboard = []
            for row in buttons:
                keyboard_row = []
                for btn in row:
                    if "url" in btn:
                        keyboard_row.append(InlineKeyboardButton(
                            text=btn["text"],
                            url=btn["url"]
                        ))
                    elif "callback_data" in btn:
                        keyboard_row.append(InlineKeyboardButton(
                            text=btn["text"],
                            callback_data=btn["callback_data"]
                        ))
                keyboard.append(keyboard_row)

            reply_markup = InlineKeyboardMarkup(keyboard)

            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode.value if parse_mode else None,
                reply_markup=reply_markup
            )

            return message.message_id

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem com botões: {e}")
            raise

    async def send_photo(
        self,
        chat_id: Union[int, str],
        photo: str,
        caption: str = None,
        parse_mode: ParseMode = None
    ) -> int:
        """
        Envia foto

        Args:
            chat_id: ID do chat
            photo: URL ou caminho do arquivo
            caption: Legenda
            parse_mode: Modo de formatação

        Returns:
            ID da mensagem enviada
        """
        try:
            from telegram import Bot

            bot = Bot(token=self.token)

            if photo.startswith(("http://", "https://")):
                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode=parse_mode.value if parse_mode else None
                )
            else:
                with open(photo, "rb") as f:
                    message = await bot.send_photo(
                        chat_id=chat_id,
                        photo=f,
                        caption=caption,
                        parse_mode=parse_mode.value if parse_mode else None
                    )

            return message.message_id

        except Exception as e:
            logger.error(f"Erro ao enviar foto: {e}")
            raise

    async def send_document(
        self,
        chat_id: Union[int, str],
        document: str,
        caption: str = None,
        filename: str = None
    ) -> int:
        """
        Envia documento

        Args:
            chat_id: ID do chat
            document: URL ou caminho do arquivo
            caption: Legenda
            filename: Nome do arquivo

        Returns:
            ID da mensagem enviada
        """
        try:
            from telegram import Bot

            bot = Bot(token=self.token)

            if document.startswith(("http://", "https://")):
                message = await bot.send_document(
                    chat_id=chat_id,
                    document=document,
                    caption=caption,
                    filename=filename
                )
            else:
                with open(document, "rb") as f:
                    message = await bot.send_document(
                        chat_id=chat_id,
                        document=f,
                        caption=caption,
                        filename=filename or document.split("/")[-1]
                    )

            return message.message_id

        except Exception as e:
            logger.error(f"Erro ao enviar documento: {e}")
            raise

    async def send_location(
        self,
        chat_id: Union[int, str],
        latitude: float,
        longitude: float
    ) -> int:
        """
        Envia localização

        Args:
            chat_id: ID do chat
            latitude: Latitude
            longitude: Longitude

        Returns:
            ID da mensagem enviada
        """
        try:
            from telegram import Bot

            bot = Bot(token=self.token)

            message = await bot.send_location(
                chat_id=chat_id,
                latitude=latitude,
                longitude=longitude
            )

            return message.message_id

        except Exception as e:
            logger.error(f"Erro ao enviar localização: {e}")
            raise

    async def edit_message(
        self,
        chat_id: Union[int, str],
        message_id: int,
        text: str,
        parse_mode: ParseMode = None,
        buttons: List[List[Dict[str, str]]] = None
    ) -> bool:
        """
        Edita mensagem existente

        Args:
            chat_id: ID do chat
            message_id: ID da mensagem
            text: Novo texto
            parse_mode: Modo de formatação
            buttons: Novos botões (opcional)

        Returns:
            True se editada com sucesso
        """
        try:
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

            bot = Bot(token=self.token)

            reply_markup = None
            if buttons:
                keyboard = []
                for row in buttons:
                    keyboard_row = []
                    for btn in row:
                        if "url" in btn:
                            keyboard_row.append(InlineKeyboardButton(
                                text=btn["text"],
                                url=btn["url"]
                            ))
                        elif "callback_data" in btn:
                            keyboard_row.append(InlineKeyboardButton(
                                text=btn["text"],
                                callback_data=btn["callback_data"]
                            ))
                    keyboard.append(keyboard_row)
                reply_markup = InlineKeyboardMarkup(keyboard)

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode.value if parse_mode else None,
                reply_markup=reply_markup
            )

            return True

        except Exception as e:
            logger.error(f"Erro ao editar mensagem: {e}")
            return False

    async def delete_message(
        self,
        chat_id: Union[int, str],
        message_id: int
    ) -> bool:
        """
        Deleta mensagem

        Args:
            chat_id: ID do chat
            message_id: ID da mensagem

        Returns:
            True se deletada com sucesso
        """
        try:
            from telegram import Bot

            bot = Bot(token=self.token)
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True

        except Exception as e:
            logger.error(f"Erro ao deletar mensagem: {e}")
            return False

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str = None,
        show_alert: bool = False
    ) -> bool:
        """
        Responde a callback de botão inline

        Args:
            callback_query_id: ID do callback
            text: Texto da notificação
            show_alert: Mostrar como alerta

        Returns:
            True se respondido
        """
        try:
            from telegram import Bot

            bot = Bot(token=self.token)
            await bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text,
                show_alert=show_alert
            )
            return True

        except Exception as e:
            logger.error(f"Erro ao responder callback: {e}")
            return False

    def command(self, command: str):
        """
        Decorator para registrar handler de comando

        Args:
            command: Nome do comando (sem /)

        Usage:
            @bot.command("start")
            async def start_handler(update, context):
                await update.message.reply_text("Olá!")
        """
        def decorator(func: Callable):
            self._command_handlers[command] = func
            return func
        return decorator

    def on_message(self, func: Callable):
        """
        Decorator para registrar handler de mensagens

        Usage:
            @bot.on_message
            async def message_handler(update, context):
                await update.message.reply_text("Recebi!")
        """
        self._message_handlers.append(func)
        return func

    def callback(self, pattern: str):
        """
        Decorator para registrar handler de callback

        Args:
            pattern: Padrão do callback_data

        Usage:
            @bot.callback("option_")
            async def callback_handler(update, context):
                await update.callback_query.answer("OK!")
        """
        def decorator(func: Callable):
            self._callback_handlers[pattern] = func
            return func
        return decorator

    async def start_polling(self):
        """Inicia o bot em modo polling"""
        try:
            from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters

            app = await self._get_application()

            # Registrar command handlers
            for cmd, handler in self._command_handlers.items():
                app.add_handler(CommandHandler(cmd, handler))

            # Registrar message handlers
            for handler in self._message_handlers:
                app.add_handler(MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handler
                ))

            # Registrar callback handlers
            for pattern, handler in self._callback_handlers.items():
                app.add_handler(CallbackQueryHandler(handler, pattern=pattern))

            logger.info("Iniciando bot em modo polling...")
            await app.initialize()
            await app.start()
            await app.updater.start_polling()

        except Exception as e:
            logger.error(f"Erro ao iniciar polling: {e}")
            raise

    async def stop(self):
        """Para o bot"""
        if self._application:
            await self._application.stop()
            await self._application.shutdown()
            logger.info("Bot parado")


class NotificationService:
    """
    Serviço de notificações via Telegram

    Facilita o envio de alertas e notificações do sistema
    """

    def __init__(self, bot: TelegramBot, admin_chat_ids: List[int] = None):
        """
        Inicializa o serviço

        Args:
            bot: Instância do TelegramBot
            admin_chat_ids: IDs dos chats de administradores
        """
        self.bot = bot
        self.admin_chat_ids = admin_chat_ids or []

    async def notify_admins(
        self,
        message: str,
        level: str = "INFO",
        parse_mode: ParseMode = ParseMode.HTML
    ):
        """
        Notifica todos os administradores

        Args:
            message: Mensagem
            level: Nível (INFO, WARNING, ERROR, CRITICAL)
            parse_mode: Modo de formatação
        """
        icons = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🚨"
        }

        icon = icons.get(level, "📢")
        formatted = f"{icon} <b>{level}</b>\n\n{message}"

        for chat_id in self.admin_chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=formatted,
                    parse_mode=parse_mode
                )
            except Exception as e:
                logger.error(f"Erro ao notificar admin {chat_id}: {e}")

    async def send_alert(
        self,
        chat_id: int,
        title: str,
        message: str,
        buttons: List[Dict[str, str]] = None
    ):
        """
        Envia alerta formatado

        Args:
            chat_id: ID do chat
            title: Título do alerta
            message: Corpo da mensagem
            buttons: Botões de ação
        """
        text = f"🔔 <b>{title}</b>\n\n{message}"

        if buttons:
            await self.bot.send_message_with_buttons(
                chat_id=chat_id,
                text=text,
                buttons=[buttons],
                parse_mode=ParseMode.HTML
            )
        else:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML
            )


# Exemplo de uso
if __name__ == "__main__":
    print("Bot Telegram")
    print("Uso:")
    print("  bot = TelegramBot('seu_token')")
    print("  await bot.send_message(chat_id, 'Olá!')")
