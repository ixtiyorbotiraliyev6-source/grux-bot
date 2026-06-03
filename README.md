# 🤖 Telegram Guruh Boshqaruv Boti

## 📋 Funksiyalar

| Funksiya | Tavsif |
|----------|--------|
| ✅ Majburiy obuna | Kanalga obuna bo'lmasdan yozib bo'lmaydi |
| 👥 +5 taklif tizimi | 5 ta do'st taklif qilmasdan yozib bo'lmaydi |
| 🧹 Kirdi/chiqdi tozalash | Sistem xabarlar avtomatik o'chiriladi |
| 🚫 Spam/reklama bloklash | Forward, link, kalit so'zlar o'chiriladi |
| 📢 Broadcast | Barcha guruhlarga reklama yuborish |
| 📊 Admin panel | Statistika, guruhlar boshqaruvi |

---

## ⚙️ O'rnatish

### 1. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 2. `config.py` ni sozlash
```python
BOT_TOKEN = "1234567890:ABCdef..."       # BotFather dan oling
REQUIRED_CHANNELS = ["@kanal1", "@kanal2"]  # Majburiy kanallar
REQUIRED_REFERRALS = 5                     # Nechta taklif kerak
ADMIN_IDS = [123456789]                    # Sizning Telegram ID
```

### 3. Botni ishga tushirish
```bash
python bot.py
```

---

## 🔧 Bot sozlamalari

### Majburiy obuna kanallarini qo'shish
`config.py` da `REQUIRED_CHANNELS` ro'yxatiga qo'shing:
```python
REQUIRED_CHANNELS = [
    "@my_channel",
    "@another_channel",
]
```
> ⚠️ Bot shu kanallarga **admin** bo'lishi kerak!

### Taklif sonini o'zgartirish
```python
REQUIRED_REFERRALS = 3  # 3 ta taklif yetarli
```

---

## 👑 Admin buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/admin` | Admin panel (statistika + tugmalar) |
| `/broadcast` | Barcha guruhlarga xabar yuborish |
| `/astats` | Batafsil statistika |
| `/groups` | Guruhlar ro'yxati |

## 👤 Foydalanuvchi buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Botni ishga tushirish |
| `/invite` | Taklif havolasini olish |
| `/check` | Obuna va referal holatini tekshirish |
| `/stats` | Shaxsiy statistika |

---

## 🏠 Guruhga bot qo'shish

1. Botni guruhga qo'shing
2. Botni **admin** qiling (xabar o'chirish huquqi bilan)
3. Majburiy kanallarga ham botni **admin** qiling
4. Tayyor! ✅

---

## 💰 Monetizatsiya usullari

### 1. Broadcast (Reklama yuborish)
Bot 100+ guruhga admin bo'lsa — `/broadcast` orqali barchaga reklama yuboring.
- Narx: $5–$50 per broadcast (auditoriyaga qarab)

### 2. Guruh boshqaruv xizmati
Guruh egalariga botni ijaraga bering:
- $10–$50/oy per guruh

### 3. Kanal o'stirish
Majburiy obuna orqali kanallaringizni o'stiring, so'ng:
- Kanalga reklama qabul qiling
- Yoki kanallarni soting

### 4. VIP panel
Katta guruhlar uchun qo'shimcha funksiyalar (yashirin so'zlar filtri, captcha, va h.k.) evaziga to'lov.

---

## 📁 Fayl tuzilmasi

```
telegram-bot/
├── bot.py              # Asosiy fayl
├── config.py           # Sozlamalar
├── database.py         # Ma'lumotlar bazasi
├── subscription.py     # Obuna tekshiruvchi
├── requirements.txt    # Kutubxonalar
└── handlers/
    ├── group_handler.py    # Guruh xabarlari
    ├── private_handler.py  # Private chat
    └── admin_handler.py    # Admin panel
```

---

## ⚠️ Muhim eslatmalar

- Bot guruhda **"Delete messages"** huquqiga ega bo'lishi **shart**
- Majburiy kanallarga bot **admin** bo'lishi kerak (obuna tekshirish uchun)
- `bot.db` fayli avtomatik yaratiladi (SQLite ma'lumotlar bazasi)
- `bot.log` faylida barcha loglar saqlanadi
