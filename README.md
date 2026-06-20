# 🎮 Free UC Bot

Telegram uchun professional "Free UC Bot" — referal tizimi va kunlik bonuslar orqali UC yig'ish imkonini beradi. Premium foydalanuvchilar ko'proq bonuslarga ega bo'ladi.

**Texnologiyalar:** Python 3.12+, Aiogram 3.x, SQLite, FastAPI (admin panel)

---

## 📁 Loyiha strukturasi

```
free_uc_bot/
├── main.py                  # Botni ishga tushiruvchi fayl
├── config.py                 # Barcha sozlamalar (.env dan o'qiydi)
├── .env                       # Tokenlar va sirlar (HECH KIMGA bermang!)
├── requirements.txt           # Python kutubxonalari
│
├── bot/
│   ├── states.py              # FSM holatlari
│   ├── database/
│   │   ├── connection.py      # SQLite ulanish + jadval yaratish
│   │   ├── users.py           # Foydalanuvchi SQL so'rovlari
│   │   └── channels.py        # Kanal SQL so'rovlari
│   ├── keyboards/
│   │   ├── reply.py           # Pastki klaviaturalar
│   │   └── inline.py          # Inline klaviaturalar
│   ├── middlewares/
│   │   ├── subscription.py    # Majburiy obuna tekshiruvi
│   │   ├── error_handler.py   # Global xato boshqaruvi
│   │   └── logging_throttle.py# Log + spamdan himoya
│   ├── handlers/
│   │   ├── start.py           # /start, registratsiya, obuna
│   │   ├── profile.py         # Mening profilim
│   │   ├── features.py        # Referal, Top10, Bonus, Premium, Axborot
│   │   ├── admin_main.py      # Admin panel asosiy
│   │   ├── admin_broadcast.py # Broadcast
│   │   ├── admin_message_user.py # Userga xabar
│   │   ├── admin_grant_premium.py # Premium berish
│   │   ├── admin_search_user.py  # User qidirish
│   │   └── admin_channels.py     # Kanal boshqarish
│   └── utils/
│       ├── subscription.py    # Obuna tekshirish funksiyasi
│       ├── validators.py      # Kirish ma'lumotlarini tekshirish
│       └── scheduler.py       # Premium muddatini avtomatik tekshirish
│
└── webapp/                    # 🖥️ Admin uchun WEBSITE (HTML/CSS/JS + FastAPI)
    ├── app.py                  # FastAPI server
    ├── templates/               # Jinja2 HTML shablonlari
    │   ├── base.html
    │   ├── login.html
    │   ├── dashboard.html
    │   ├── users.html
    │   ├── channels.html
    │   └── broadcast.html
    └── static/
        ├── css/style.css
        └── js/main.js
```

---

## ⚙️ O'rnatish

### 1. Python kutubxonalarini o'rnatish

```bash
pip install -r requirements.txt
```

### 2. `.env` faylini tahrirlash

`.env` fayli ichida quyidagilar allaqachon to'ldirilgan:

```env
BOT_TOKEN=8867702176:AAH2MUiKtjMgJKcmPtX4bYAF_6SKTLUuQDo
ADMIN_IDS=5771496552
```

⚠️ **MUHIM XAVFSIZLIK ESLATMASI:** Bot tokeningiz oshkor bo'lgan bo'lishi mumkin (suhbatda ko'rinib turgani uchun). Ishga tushirishdan oldin **BotFather**'da `/revoke` orqali eski tokenni bekor qilib, yangi token oling, so'ngra `.env` faylida yangilang. Aks holda botingizni begona odam boshqarib olishi mumkin.

Bir nechta admin qo'shish uchun, vergul bilan ajratib yozing:
```env
ADMIN_IDS=5771496552,123456789
```

Web admin panel uchun login/parolni ham xohlasangiz o'zgartiring:
```env
WEBAPP_ADMIN_USERNAME=admin
WEBAPP_ADMIN_PASSWORD=admin123
```

### 3. Botni ishga tushirish

```bash
python main.py
```

Bot polling rejimida ishga tushadi va barcha xabarlarni qabul qila boshlaydi.

### 4. Admin web panelni ishga tushirish

```bash
cd webapp
python app.py
```

Yoki:
```bash
uvicorn webapp.app:app --host 0.0.0.0 --port 8000 --reload
```

Brauzerda oching: **http://localhost:8000**

Login: `admin` / Parol: `admin123` (yoki `.env`da o'zgartirgan qiymatlar)

> 📌 Bot va webapp **bitta SQLite faylni** ishlatadi (`database/bot.db`), shuning uchun ikkisini istalgan tartibda, hatto bir vaqtning o'zida ishga tushirishingiz mumkin.

---

## 🤖 Bot qanday ishlaydi

### Foydalanuvchi tomoni (Telegram ichida)
- `/start` — ro'yxatdan o'tish, majburiy obuna tekshiruvi
- 👤 Mening profilim — shaxsiy ma'lumotlar, PUBG ID o'zgartirish
- 🔗 Referal linkim — shaxsiy referal havola va statistikasi
- 🏆 Top 10 — eng ko'p UC yig'gan foydalanuvchilar
- 🎁 Bonus — har 24 soatda bonus olish
- 💎 Premium — premium narxlari va afzalliklari
- ℹ️ Axborot olish — bot haqida to'liq ma'lumot

### Admin tomoni — IKKI XIL YO'L bilan boshqariladi:

**1) Telegram ichida** (`/admin` buyrug'i orqali):
- 📢 Broadcast, 💬 Userga xabar, 💎 Premium berish, 📊 Statistika, 👤 User qidirish, ⚙️ Majburiy obuna

**2) Web sayt orqali** (`webapp/app.py`):
- 📊 Boshqaruv paneli — real-time statistika va Top 10
- 👥 Foydalanuvchilar — qidirish, balans o'zgartirish, Premium berish, ban/unban
- 📢 Kanallar — majburiy obuna kanallarini qo'shish/o'chirish
- ✉️ Xabar yuborish — broadcast va tarix

---

## 🗄 Ma'lumotlar bazasi jadvallari

| Jadval | Tavsif |
|---|---|
| `users` | Foydalanuvchilar (profil, balans, premium, referal) |
| `admins` | Qo'shimcha adminlar (kelajakda kengaytirish uchun) |
| `channels` | Majburiy obuna kanallari |
| `referrals` | Referal bog'lanishlari va bonuslar |
| `premium_users` | Premium tarixi (kim, qachon, qancha muddat) |
| `bonus_history` | Kunlik bonus tarixi |
| `broadcast_logs` | Yuborilgan broadcast xabarlar tarixi |

---

## 🔒 Xavfsizlik bo'yicha tavsiyalar

1. `.env` faylini hech qachon GitHub'ga yoki ochiq joyga yuklamang.
2. Web panel parolini ishlatishdan oldin albatta o'zgartiring.
3. Production muhitda webapp'ni HTTPS orqali (masalan, Nginx + Let's Encrypt) joylashtiring.
4. Bot tokenini muntazam ravishda yangilab turing, agar oshkor bo'lib qolgan bo'lsa.

---

## 🚀 Keyingi qadamlar (ixtiyoriy kengaytirishlar)

- Webhook rejimiga o'tish (polling o'rniga) production uchun
- Redis orqali FSM storage (ko'p foydalanuvchili yuklama uchun)
- Docker konteynerlashtirish
- Telegram Web App (Mini App) — agar to'liq mobil-native admin panel kerak bo'lsa
