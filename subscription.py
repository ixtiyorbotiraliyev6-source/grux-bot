"""
Obuna tekshiruvchi funksiya
"""
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from config import REQUIRED_CHANNELS


async def check_subscription(bot: Bot, user_id: int) -> tuple[bool, list[str]]:
    """
    Foydalanuvchi barcha majburiy kanallarga obuna bo'lganmi?
    
    Returns:
        (True, []) - hammasi joyida
        (False, ["@kanal1", ...]) - obuna bo'lmagan kanallar
    """
    not_subscribed = []

    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ("left", "kicked", "banned"):
                not_subscribed.append(channel)
        except (TelegramForbiddenError, TelegramBadRequest):
            # Bot kanalga admin emas yoki kanal topilmadi
            pass

    return len(not_subscribed) == 0, not_subscribed
