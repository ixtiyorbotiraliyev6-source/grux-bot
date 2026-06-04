import os

# =============================================
#   BOT KONFIGURATSIYASI - config.py
#   Bu faylda barcha sozlamalar saqlanadi
# =============================================

# 🔑 BotFather dan olingan token
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8562902038:AAGKQ2okAPbLRHnC1Hon9MkNEgQeZQOrGSQ")

# 📢 Majburiy obuna kanallari (@ bilan yozing)
# Foydalanuvchi shu kanallarga obuna bo'lmasa yoza olmaydi
REQUIRED_CHANNELS = [
    # Majburiy kanallarni shu yerga qo'shing
    # Misol: "@sizning_kanal"
]

# 👥 Nechta odam taklif qilishi shart (default: 5)
REQUIRED_REFERRALS = 5

# 👑 Bot adminlari (Telegram user ID lar)
# Bu odamlar /admin buyrug'ini ishlatishi mumkin
ADMIN_IDS = [
    7980044619,  # Asosiy admin
]

# 💬 Xabarlar matni (o'zbek tilida)
MESSAGES = {
    "not_subscribed": (
        "⛔ Guruhda yozish uchun avval quyidagi kanallarga obuna bo'ling:\n\n"
        "{channels}\n\n"
        "✅ Obuna bo'lgach, /check buyrug'ini yuboring yoki qayta urinib ko'ring."
    ),
    "not_enough_referrals": (
        "⛔ Guruhda yozish uchun kamida <b>{required}</b> ta do'st taklif qilishingiz kerak!\n\n"
        "📊 Sizning holatiz: <b>{current}/{required}</b> ta taklif\n\n"
        "🔗 Sizning taklif havolangiz:\n"
        "<code>{invite_link}</code>\n\n"
        "Havolani do'stlaringizga yuboring va ular botni ishga tushirsin!"
    ),
    "welcome": (
        "👋 Salom, <b>{name}</b>!\n\n"
        "Bu bot guruhda yozish uchun:\n"
        "1️⃣ Majburiy kanallarga obuna bo'lishingiz\n"
        "2️⃣ {required} ta do'st taklif qilishingiz kerak\n\n"
        "🔗 Taklif havolangiz:\n"
        "<code>{invite_link}</code>"
    ),
    "referral_success": (
        "🎉 <b>{name}</b> sizning taklifingiz bilan qo'shildi!\n"
        "📊 Jami taklif: <b>{count}/{required}</b>"
    ),
    "unlocked": (
        "✅ Tabriklaymiz! Endi guruhda yozishingiz mumkin! 🎊"
    ),
    "check_ok": "✅ Hammasi joyida! Guruhda yozishingiz mumkin.",
}
