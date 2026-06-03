"""
ADMIN PANEL — Toggle funksiyalari, referral soni, broadcast
"""
import asyncio
from aiogram import Router, Bot, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_IDS

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── FSM ───

class BroadcastState(StatesGroup):
    waiting_message = State()

class SetRefState(StatesGroup):
    waiting_number = State()


# ─── TOGGLE PANEL YARATISH ───

async def build_admin_keyboard() -> InlineKeyboardMarkup:
    s = await db.get_all_settings()

    def ico(key): return "✅" if s.get(key) == "1" else "❌"

    ref_count = s.get("ref_count", "5")

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{ico('sub_check')} Majburiy obuna", callback_data="toggle:sub_check"),
            InlineKeyboardButton(text=f"{ico('ref_check')} Taklif tizimi", callback_data="toggle:ref_check"),
        ],
        [
            InlineKeyboardButton(text=f"{ico('link_filter')} Link/spam filtri", callback_data="toggle:link_filter"),
            InlineKeyboardButton(text=f"{ico('join_cleaner')} Kirdi/chiqdi tozalash", callback_data="toggle:join_cleaner"),
        ],
        [
            InlineKeyboardButton(text=f"👥 Taklif soni: {ref_count} ta", callback_data="set_ref_count"),
        ],
        [
            InlineKeyboardButton(text="📢 Broadcast (reklama)", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh"),
        ]
    ])


async def build_admin_text() -> str:
    stats = await db.get_stats()
    s = await db.get_all_settings()

    def status(key): return "✅ Yoqilgan" if s.get(key) == "1" else "❌ O'chirilgan"

    return (
        f"👑 <b>Admin Panel</b>\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"  👥 Foydalanuvchilar: <b>{stats['users']}</b>\n"
        f"  🏠 Guruhlar: <b>{stats['groups']}</b>\n"
        f"  🔗 Referal: <b>{stats['referrals']}</b>\n\n"
        f"⚙️ <b>Funksiyalar:</b>\n"
        f"  📢 Majburiy obuna: {status('sub_check')}\n"
        f"  👥 Taklif tizimi: {status('ref_check')} ({s.get('ref_count','5')} ta)\n"
        f"  🔗 Link/spam filtri: {status('link_filter')}\n"
        f"  🧹 Kirdi/chiqdi tozalash: {status('join_cleaner')}\n\n"
        f"👇 Tugmalar orqali yoqing/o'chiring:"
    )


# ─── /admin BUYRUQ ───

@router.message(Command("admin"), F.chat.type == "private")
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Ruxsat yo'q!")
        return
    text = await build_admin_text()
    keyboard = await build_admin_keyboard()
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


# ─── TOGGLE CALLBACK ───

@router.callback_query(F.data.startswith("toggle:"))
async def cb_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    key = call.data.split(":")[1]
    labels = {
        "sub_check":    "Majburiy obuna",
        "ref_check":    "Taklif tizimi",
        "link_filter":  "Link/spam filtri",
        "join_cleaner": "Kirdi/chiqdi tozalash",
    }
    new_state = await db.toggle_setting(key)
    state_text = "✅ Yoqildi" if new_state else "❌ O'chirildi"

    await call.answer(f"{labels.get(key, key)}: {state_text}", show_alert=False)

    try:
        text = await build_admin_text()
        keyboard = await build_admin_keyboard()
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass


# ─── TAKLIF SONINI O'ZGARTIRISH ───

@router.callback_query(F.data == "set_ref_count")
async def cb_set_ref_count(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    current = await db.get_setting("ref_count")
    await call.message.answer(
        f"👥 <b>Taklif sonini o'zgartirish</b>\n\n"
        f"Hozirgi son: <b>{current}</b>\n\n"
        f"Yangi son yuboring (1–100):\n"
        f"❌ Bekor qilish: /cancel",
        parse_mode="HTML"
    )
    await state.set_state(SetRefState.waiting_number)
    await call.answer()


@router.message(SetRefState.waiting_number, F.chat.type == "private")
async def process_set_ref(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        n = int(message.text.strip())
        if n < 1 or n > 100:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("❌ 1 dan 100 gacha son kiriting!")
        return

    await db.set_setting("ref_count", str(n))
    await state.clear()

    text = await build_admin_text()
    keyboard = await build_admin_keyboard()
    await message.answer(
        f"✅ Taklif soni <b>{n}</b> ga o'zgartirildi!",
        parse_mode="HTML"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


# ─── /setreferrals — tez buyruq ───

@router.message(Command("setreferrals"), F.chat.type == "private")
async def cmd_set_referrals(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        current = await db.get_setting("ref_count")
        await message.answer(
            f"📌 Ishlatish: <code>/setreferrals 3</code>\n"
            f"Hozirgi son: <b>{current}</b>",
            parse_mode="HTML"
        )
        return
    try:
        n = int(parts[1])
        if n < 1 or n > 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ 1–100 orasida son kiriting!")
        return

    await db.set_setting("ref_count", str(n))
    await message.answer(f"✅ Taklif soni <b>{n}</b> ga o'zgartirildi!", parse_mode="HTML")


# ─── BROADCAST ───

@router.message(Command("broadcast"), F.chat.type == "private")
async def cmd_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    groups = await db.get_active_groups()
    await message.answer(
        f"📢 <b>Broadcast</b>\n\n"
        f"Xabar <b>{len(groups)}</b> ta aktiv guruhga yuboriladi.\n"
        f"Matn, rasm, video — hammasi qabul qilinadi.\n\n"
        f"❌ Bekor qilish: /cancel",
        parse_mode="HTML"
    )
    await state.set_state(BroadcastState.waiting_message)


@router.message(Command("cancel"), F.chat.type == "private")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Bekor qilindi.")


@router.message(BroadcastState.waiting_message, F.chat.type == "private")
async def process_broadcast(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    groups = await db.get_active_groups()
    if not groups:
        await message.answer("❌ Aktiv guruhlar yo'q.")
        return

    status_msg = await message.answer(f"⏳ Yuborilmoqda... 0/{len(groups)}")
    success, failed = 0, 0

    for i, group in enumerate(groups):
        try:
            await message.copy_to(chat_id=group["group_id"])
            success += 1
        except Exception as e:
            failed += 1
            if any(x in str(e) for x in ["kicked", "chat not found", "deactivated"]):
                await db.remove_group(group["group_id"])
        if (i + 1) % 10 == 0:
            try:
                await status_msg.edit_text(f"⏳ Yuborilmoqda... {i+1}/{len(groups)}")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    try:
        await status_msg.edit_text(
            f"✅ <b>Broadcast tugadi!</b>\n\n"
            f"✅ Muvaffaqiyatli: <b>{success}</b>\n"
            f"❌ Xato: <b>{failed}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ─── STATISTIKA ───

@router.message(Command("astats"), F.chat.type == "private")
async def cmd_astats(message: Message):
    if not is_admin(message.from_user.id):
        return
    stats = await db.get_stats()
    groups = await db.get_active_groups()
    group_list = "\n".join([f"  • {g['group_name']}" for g in groups[:10]])
    if len(groups) > 10:
        group_list += f"\n  ... +{len(groups)-10} ta"
    await message.answer(
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['users']}</b>\n"
        f"🏠 Aktiv guruhlar: <b>{stats['groups']}</b>\n"
        f"🔗 Jami referal: <b>{stats['referrals']}</b>\n\n"
        f"🏠 <b>Guruhlar:</b>\n{group_list or '  (hali yo\'q)'}",
        parse_mode="HTML"
    )


# ─── CALLBACKS ───

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    groups = await db.get_active_groups()
    await call.message.answer(
        f"📢 Xabar <b>{len(groups)}</b> ta guruhga yuboriladi.\n"
        f"Xabarni yuboring:\n\n❌ Bekor: /cancel",
        parse_mode="HTML"
    )
    await state.set_state(BroadcastState.waiting_message)
    await call.answer()


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    stats = await db.get_stats()
    await call.answer(
        f"👥 Foydalanuvchi: {stats['users']}\n"
        f"🏠 Guruh: {stats['groups']}\n"
        f"🔗 Referal: {stats['referrals']}",
        show_alert=True
    )


@router.callback_query(F.data == "admin_refresh")
async def cb_admin_refresh(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    try:
        text = await build_admin_text()
        keyboard = await build_admin_keyboard()
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await call.answer("✅ Yangilandi")
    except Exception:
        await call.answer("Hech narsa o'zgarmadi")
