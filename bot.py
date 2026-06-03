"""
BOT ASOSIY FAYLI — bot.py
Barcha handlerlarni birlashtiradi va botni ishga tushiradi
"""
import asyncio
import logging
import sys

# Windows terminalda emojilarni chop etishda xatolik chiqmasligi uchun utf-8 sozlaymiz
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeAllGroupChats
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION

import database as db
from config import BOT_TOKEN, ADMIN_IDS
from handlers import group_handler, private_handler, admin_handler

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """Bot buyruqlari menyusini sozlash"""
    # Private chat buyruqlari
    private_commands = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="invite", description="🔗 Taklif havolasini olish"),
        BotCommand(command="check", description="✅ Obuna va referalni tekshirish"),
        BotCommand(command="stats", description="📊 Statistikam"),
        BotCommand(command="admin", description="👑 Admin panel"),
    ]
    await bot.set_my_commands(private_commands, scope=BotCommandScopeDefault())

    # Guruh buyruqlari (minimal)
    group_commands = [
        BotCommand(command="check", description="✅ Holatni tekshirish"),
    ]
    await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())


async def dummy_handler(reader, writer):
    try:
        data = await reader.read(100)
        response = "HTTP/1.1 200 OK\r\nContent-Length: 15\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nBot is running!"
        writer.write(response.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass


async def start_dummy_server():
    import os
    port = int(os.environ.get("PORT", 8080))
    try:
        server = await asyncio.start_server(dummy_handler, '0.0.0.0', port)
        logger.info(f"☕ Dummy HTTP server ishga tushdi: port {port}")
        # Serverni fonda umrbod ishlatish
        asyncio.create_task(server.serve_forever())
    except Exception as e:
        logger.error(f"❌ Dummy serverni ishga tushirib bo'lmadi: {e}")


async def on_startup(bot: Bot):
    """Bot ishga tushganda bajariladigan amallar"""
    await db.init_db()
    await set_bot_commands(bot)

    # Render.com port ulanishi uchun dummy serverni yoqish
    import os
    if os.environ.get("PORT"):
        await start_dummy_server()

    bot_info = await bot.get_me()
    logger.info(f"✅ Bot ishga tushdi: @{bot_info.username}")

    # Adminlarga xabar yuborish
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"✅ <b>Bot ishga tushdi!</b>\n\n"
                f"🤖 Bot: @{bot_info.username}\n"
                f"🕐 Vaqt: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Admin {admin_id} ga xabar yuborib bo'lmadi: {e}")


async def on_shutdown(bot: Bot):
    """Bot to'xtaganda bajariladigan amallar"""
    logger.info("⛔ Bot to'xtatildi.")


async def main():
    """Asosiy funksiya"""
    # Bot va Dispatcher yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Startup/shutdown hooklar
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # ── Routerlarni qo'shish (tartib muhim!) ──
    # 1. Guruh handlerlari (spam filter, obuna, referal)
    dp.include_router(group_handler.router)
    # 2. Private chat handlerlari
    dp.include_router(private_handler.router)
    # 3. Admin panel
    dp.include_router(admin_handler.router)

    # Botni ishga tushirish (polling mode)
    logger.info("🚀 Polling boshlandi...")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "callback_query",
                "chat_member",
                "my_chat_member",
            ]
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
