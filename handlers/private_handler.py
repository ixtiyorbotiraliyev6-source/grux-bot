"""
PRIVATE CHAT HANDLERLARI
- /start (referal link bilan)
- /invite — taklif havolasi
- /check — obuna va referalni tekshirish
- /stats — shaxsiy statistika
"""
from aiogram import Router, Bot, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject

import database as db
from subscription import check_subscription
from config import MESSAGES, REQUIRED_CHANNELS

router = Router()


async def get_req() -> int:
    try:
        val = await db.get_setting("ref_count")
        return int(val)
    except Exception:
        return 5


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message, bot: Bot, command: CommandObject):
    """
    /start — Botni ishga tushirish
    /start ref_123456 — Referal orqali kirish
    """
    user = message.from_user
    args = command.args  # "ref_123456" yoki None
    req = await get_req()

    # Foydalanuvchini bazaga qo'shish
    referred_by = None
    if args and args.startswith("ref_"):
        try:
            referred_by = int(args.replace("ref_", ""))
            if referred_by == user.id:
                referred_by = None  # O'zini taklif qila olmaydi
        except ValueError:
            pass

    existing = await db.get_user(user.id)
    if not existing:
        await db.add_user(
            user_id=user.id,
            username=user.username or "",
            full_name=user.full_name,
            referred_by=referred_by,
        )
        # Referalni qayd etish
        if referred_by:
            await db.increment_referral(referrer_id=referred_by, referred_id=user.id)
            ref_count = await db.get_referral_count(referred_by)
            try:
                await bot.send_message(
                    referred_by,
                    MESSAGES["referral_success"].format(
                        name=user.full_name,
                        count=ref_count,
                        required=req,
                    ),
                    parse_mode="HTML"
                )
                if ref_count >= req:
                    await bot.send_message(
                        referred_by, MESSAGES["unlocked"], parse_mode="HTML"
                    )
            except Exception:
                pass

    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"

    text = MESSAGES["welcome"].format(
        name=user.full_name,
        required=req,
        invite_link=invite_link,
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Mening holatim",
            callback_data="my_status"
        )],
        [InlineKeyboardButton(
            text="🔗 Taklif havolasi",
            callback_data="get_invite"
        )],
    ])

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.message(Command("invite"), F.chat.type == "private")
async def cmd_invite(message: Message, bot: Bot):
    """Taklif havolasini berish"""
    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    ref_count = await db.get_referral_count(message.from_user.id)
    req = await get_req()

    text = (
        f"🔗 <b>Sizning taklif havolangiz:</b>\n\n"
        f"<code>{invite_link}</code>\n\n"
        f"📊 Taklif qilganlar: <b>{ref_count}/{req}</b>\n\n"
        f"💡 Havolani do'stlaringizga yuboring. Ular botni ishga tushirsa, "
        f"taklif hisoblanadi!"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("check"), F.chat.type == "private")
async def cmd_check(message: Message, bot: Bot):
    """Obuna va referalni tekshirish"""
    user = message.from_user
    is_ok, not_subbed = await check_subscription(bot, user.id)
    ref_count = await db.get_referral_count(user.id)
    req = await get_req()

    sub_status = "✅ Obuna" if is_ok else f"❌ Obuna emas ({len(not_subbed)} kanal)"
    ref_status = (
        f"✅ Yetarli ({ref_count}/{req})"
        if ref_count >= req
        else f"❌ Yetarli emas ({ref_count}/{req})"
    )

    text = (
        f"📋 <b>Sizning holatiz:</b>\n\n"
        f"📢 Majburiy obuna: {sub_status}\n"
        f"👥 Taklif qilganlar: {ref_status}\n\n"
    )

    if is_ok and ref_count >= req:
        text += MESSAGES["check_ok"]
    else:
        text += "⚠️ Shartlarni bajaring va qayta urinib ko'ring."

    await message.answer(text, parse_mode="HTML")


@router.message(Command("stats"), F.chat.type == "private")
async def cmd_stats_private(message: Message, bot: Bot):
    """Shaxsiy statistika"""
    user_id = message.from_user.id
    ref_count = await db.get_referral_count(user_id)
    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    req = await get_req()

    text = (
        f"📊 <b>Sizning statistikangiz:</b>\n\n"
        f"👥 Taklif qilganlar: <b>{ref_count}</b> ta\n"
        f"🎯 Maqsad: <b>{req}</b> ta\n"
        f"📈 Progress: <b>{min(ref_count, req)}/{req}</b>\n\n"
        f"🔗 Havola:\n<code>{invite_link}</code>"
    )
    await message.answer(text, parse_mode="HTML")


# ─────────────── CALLBACK ───────────────

@router.callback_query(F.data == "my_status")
async def cb_my_status(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    is_ok, not_subbed = await check_subscription(bot, user_id)
    ref_count = await db.get_referral_count(user_id)
    req = await get_req()

    sub_status = "✅" if is_ok else f"❌ ({len(not_subbed)} kanal)"
    ref_status = f"✅ {ref_count}/{req}" if ref_count >= req else f"❌ {ref_count}/{req}"

    try:
        await call.message.edit_text(
            f"📊 <b>Holatiz:</b>\n\n"
            f"📢 Obuna: {sub_status}\n"
            f"👥 Taklif: {ref_status}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Yangilash", callback_data="my_status")]
            ])
        )
    except Exception:
        pass  # Xabar o'zgarmagan bo'lsa — xato chiqmaydi
    await call.answer("✅ Yangilandi")


@router.callback_query(F.data == "get_invite")
async def cb_get_invite(call: CallbackQuery, bot: Bot):
    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=ref_{call.from_user.id}"
    await call.message.answer(
        f"🔗 <b>Taklif havolangiz:</b>\n\n<code>{invite_link}</code>",
        parse_mode="HTML"
    )
    await call.answer()
