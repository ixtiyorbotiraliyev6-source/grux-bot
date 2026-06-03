import asyncio
import re
from aiogram import Router, Bot, F
from aiogram.types import (
    Message, ChatMemberUpdated,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION
import database as db
from subscription import check_subscription
from config import REQUIRED_CHANNELS, ADMIN_IDS

router = Router()

async def get_req():
    try:
        return int(await db.get_setting("ref_count"))
    except Exception:
        return 5

async def temp_msg(bot, chat_id, text, delay=15):
    try:
        m = await bot.send_message(chat_id, text, parse_mode="HTML")
        await asyncio.sleep(delay)
        await m.delete()
    except Exception:
        pass

async def notify(bot, user_id, chat_id, text, kb=None):
    try:
        await bot.send_message(user_id, text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        try:
            bot_info = await bot.get_me()
            asyncio.create_task(temp_msg(
                bot, chat_id,
                "Xabaringiz o'chirildi! Botga boring: @" + bot_info.username,
                20
            ))
        except Exception:
            pass

URL_RE = re.compile(
    r"(https?://|t\.me/|@[a-zA-Z]\w{4,}|tg://|bit\.ly)",
    re.IGNORECASE
)
SPAM_WORDS = ["reklama","sotiladi","kanalimiz","subscribe","join now","click here"]

def is_spam(msg):
    if msg.forward_origin:
        return True, "forward xabar"
    if msg.from_user and msg.from_user.is_bot:
        return True, "bot xabari"
    text = msg.text or msg.caption or ""
    if URL_RE.search(text):
        return True, "havola/link"
    tl = text.lower()
    for w in SPAM_WORDS:
        if w in tl:
            return True, "spam soz"
    if msg.reply_markup and hasattr(msg.reply_markup, "inline_keyboard"):
        return True, "tugmali xabar"
    return False, ""

SERVICE = {
    "new_chat_members","left_chat_member","new_chat_title",
    "new_chat_photo","delete_chat_photo","group_chat_created",
    "supergroup_chat_created","pinned_message"
}

@router.message(F.content_type.in_(SERVICE))
async def del_service(message: Message):
    if await db.get_setting("join_cleaner") != "1":
        return
    try:
        await message.delete()
    except Exception:
        pass

@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_join(event: ChatMemberUpdated, bot: Bot):
    new_user = event.new_chat_member.user
    adder = event.from_user
    chat_id = event.chat.id
    if new_user.is_bot:
        return
    if not await db.get_user(new_user.id):
        await db.add_user(new_user.id, new_user.username or "", new_user.full_name)
    user = await db.get_user(new_user.id)
    req = await get_req()
    bot_info = await bot.get_me()
    invite_link = "https://t.me/" + bot_info.username + "?start=ref_" + str(new_user.id)

    # REFERAL: 2 usul - togiridan qoshish YOKI havola
    referrer_id = None
    if adder and adder.id != new_user.id and not adder.is_bot:
        referrer_id = adder.id   # Usul 1: togiridan qoshdi
    elif user and user.get("referred_by"):
        referrer_id = user["referred_by"]  # Usul 2: havola orqali

    if referrer_id:
        added = await db.increment_referral(referrer_id, new_user.id)
        if added:
            count = await db.get_referral_count(referrer_id)
            try:
                if count >= req:
                    msg = (new_user.full_name + " siz orqali keldi!\n"
                           "Taklif: " + str(count) + "/" + str(req) + "\n\n"
                           "Barakalla! Endi guruhda yozishingiz mumkin!")
                else:
                    msg = (new_user.full_name + " siz orqali keldi!\n"
                           "Taklif: " + str(count) + "/" + str(req) + "\n\n"
                           "Yana " + str(req - count) + " ta qo'shing!")
                await bot.send_message(referrer_id, msg)
            except Exception:
                pass

    sub_on = await db.get_setting("sub_check") == "1"
    ref_on = await db.get_setting("ref_check") == "1"
    steps = []
    if sub_on and REQUIRED_CHANNELS:
        ch_links = " | ".join(
            ['<a href="https://t.me/' + c.lstrip("@") + '">' + c + "</a>"
             for c in REQUIRED_CHANNELS]
        )
        steps.append("1) Kanallarga obuna bo'ling:\n   " + ch_links)
    if ref_on:
        steps.append(
            "2) <b>" + str(req) + "</b> ta do'st qo'shing:\n"
            "   - Guruhga to'g'ridan qo'shing\n"
            "   - Yoki havola orqali taklif qiling:\n"
            "   <code>" + invite_link + "</code>"
        )
    if steps:
        body = "\n\n".join(steps)
        text = (
            "<a href=\"tg://user?id=" + str(new_user.id) + "\">" + new_user.full_name + "</a>"
            " guruhga xush kelibsiz!\n\n"
            "<b>Guruhda yozish uchun:</b>\n\n" + body + "\n\n"
            "Shartlar bajarilib bo'lgach yozishingiz mumkin!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Botni ishga tushirish",
                url="https://t.me/" + bot_info.username + "?start=ref_" + str(new_user.id)
            )
        ]])
    else:
        text = (
            "<a href=\"tg://user?id=" + str(new_user.id) + "\">" + new_user.full_name + "</a>"
            " guruhga xush kelibsiz!"
        )
        kb = None
    try:
        await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def msg_filter(message: Message, bot: Bot):
    user = message.from_user
    if not user or user.is_bot:
        return
    if user.id in ADMIN_IDS:
        return
    try:
        cm = await bot.get_chat_member(message.chat.id, user.id)
        if cm.status in ("administrator", "creator"):
            return
    except Exception:
        pass

    if await db.get_setting("link_filter") == "1":
        spam, reason = is_spam(message)
        if spam:
            try:
                await message.delete()
            except Exception:
                pass
            asyncio.create_task(notify(
                bot, user.id, message.chat.id,
                "Xabaringiz o'chirildi!\n\nSabab: <b>" + reason + "</b>\n\n"
                "Bu guruhda reklama va havolalar taqiqlangan."
            ))
            return

    if await db.get_setting("sub_check") == "1" and REQUIRED_CHANNELS:
        is_ok, not_subbed = await check_subscription(bot, user.id)
        if not is_ok:
            try:
                await message.delete()
            except Exception:
                pass
            buttons = [
                [InlineKeyboardButton(
                    text=ch + " ga obuna bo'lish",
                    url="https://t.me/" + ch.lstrip("@")
                )] for ch in not_subbed
            ]
            buttons.append([InlineKeyboardButton(
                text="Obuna bo'ldim, tekshir",
                callback_data="check_sub:" + str(message.chat.id)
            )])
            ch_text = "\n".join(["  - " + c for c in not_subbed])
            asyncio.create_task(notify(
                bot, user.id, message.chat.id,
                "Xabaringiz o'chirildi!\n\n"
                "Guruhda yozish uchun obuna bo'ling:\n" + ch_text + "\n\n"
                "Obuna bo'lgach 'Tekshir' tugmasini bosing.",
                InlineKeyboardMarkup(inline_keyboard=buttons)
            ))
            asyncio.create_task(temp_msg(
                bot, message.chat.id,
                "<a href=\"tg://user?id=" + str(user.id) + "\">" + user.full_name + "</a>"
                " - avval majburiy kanallarga obuna bo'ling! (Bot sizga yozdi)",
                15
            ))
            return

    if await db.get_setting("ref_check") == "1":
        req = await get_req()
        db_user = await db.get_user(user.id)
        if not db_user:
            await db.add_user(user.id, user.username or "", user.full_name)
            db_user = await db.get_user(user.id)
        ref_count = db_user.get("referral_count", 0)
        if ref_count < req:
            try:
                await message.delete()
            except Exception:
                pass
            bot_info = await bot.get_me()
            invite_link = "https://t.me/" + bot_info.username + "?start=ref_" + str(user.id)
            filled = int((ref_count / req) * 10)
            bar = "#" * filled + "." * (10 - filled)
            asyncio.create_task(notify(
                bot, user.id, message.chat.id,
                "Xabaringiz o'chirildi!\n\n"
                "Guruhda yozish uchun <b>" + str(req) + "</b> ta odam qo'shing!\n\n"
                "[" + bar + "] " + str(ref_count) + "/" + str(req) + "\n\n"
                "Yana <b>" + str(req - ref_count) + "</b> ta kerak.\n\n"
                "<b>2 usul:</b>\n"
                "1) Guruhga to'g'ridan qo'shing\n"
                "2) Havola orqali taklif qiling:\n"
                "<code>" + invite_link + "</code>",
                InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="Havolani ulashish",
                        url="https://t.me/share/url?url=" + invite_link
                    )],
                    [InlineKeyboardButton(
                        text="Tekshirish",
                        callback_data="check_ref:" + str(message.chat.id)
                    )]
                ])
            ))
            asyncio.create_task(temp_msg(
                bot, message.chat.id,
                "<a href=\"tg://user?id=" + str(user.id) + "\">" + user.full_name + "</a>"
                " - guruhda yozish uchun <b>" + str(req) + "</b> ta odam qo'shing! "
                "(" + str(ref_count) + "/" + str(req) + ") Bot sizga yozdi.",
                15
            ))
            return

@router.callback_query(F.data.startswith("check_sub:"))
async def cb_check_sub(call: CallbackQuery, bot: Bot):
    is_ok, not_subbed = await check_subscription(bot, call.from_user.id)
    if is_ok:
        try:
            await call.message.edit_text("Obuna tasdiqlandi! Endi guruhda yozishingiz mumkin.")
        except Exception:
            pass
        await call.answer("Tasdiqlandi!", show_alert=False)
    else:
        await call.answer(
            "Hali " + str(len(not_subbed)) + " ta kanalga obuna bo'lmadingiz!",
            show_alert=True
        )

@router.callback_query(F.data.startswith("check_ref:"))
async def cb_check_ref(call: CallbackQuery, bot: Bot):
    req = await get_req()
    ref_count = await db.get_referral_count(call.from_user.id)
    if ref_count >= req:
        try:
            await call.message.edit_text(
                "Barakalla! " + str(ref_count) + " ta odam qo'shdingiz.\n"
                "Endi guruhda yozishingiz mumkin!"
            )
        except Exception:
            pass
        await call.answer("Ochildi!", show_alert=False)
    else:
        await call.answer(
            "Hali yetarli emas: " + str(ref_count) + "/" + str(req) + "\n"
            "Yana " + str(req - ref_count) + " ta qo'shing!",
            show_alert=True
        )
