# Serverni sozlash (Ubuntu 22.04/24.04)

## 1. SSH orqali serverga ulanish

```bash
ssh root@<server_ip>
```

## 2. Paketlarni yangilash va kerakli dasturlarni o'rnatish

```bash
apt update && apt upgrade -y

# Git o'rnatish
apt install -y git

# Docker va docker-compose o'rnatish
curl -fsSL https://get.docker.com | sh
```

## 3. Loyihani serverga yuklash

```bash
# 1-usul: git clone (agar GitHubda bo'lsa)
git clone <repo-url> /opt/freeuc
cd /opt/freeuc

# 2-usul: FTP/SFTP orqali yuklagan bo'lsangiz
# Fayllarni /opt/freeuc ga yuklab, terminalda:
cd /opt/freeuc
```

## 4. .env faylini sozlash

```bash
cp .env.example .env
nano .env
```

`.env` ichida quyidagilarni to'ldiring:

```
BOT_TOKEN=8867702176:AAH2MUiKtjMgJKcmPtX4bYAF_6SKTLUuQDo
ADMIN_IDS=5771496552
DB_PATH=database/bot.db
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=8000
WEBAPP_SECRET_KEY=uzun_va_murakkab_secret_key_yozing
WEBAPP_ADMIN_USERNAME=admin
WEBAPP_ADMIN_PASSWORD=kuchli_parol_yozing
```

> ⚠️ `WEBAPP_ADMIN_PASSWORD` va `WEBAPP_SECRET_KEY` ni albatta o'zgartiring!

## 5. Bot va webappni ishga tushirish

```bash
cd /opt/freeuc

# Docker compose bilan ishga tushirish
docker compose up -d

# Holatini tekshirish
docker compose ps

# Loglarni ko'rish
docker compose logs -f
```

## 6. Webappga kirish

Brauzerda: `http://<server_ip>:5000`
Login: `admin`
Parol: (env da yozganingiz)

## 7. Firewall sozlash (xavfsizlik)

```bash
ufw allow OpenSSH
ufw enable
```

Agar webappni faqat o'zingiz ishlatmoqchi bo'lsangiz, portni yopishingiz mumkin:

```bash
# SSH tunnel orqali (tavsiya etiladi):
# Localda: ssh -L 5000:localhost:5000 root@<server_ip>
```

## 8. Bot va webappni qayta ishga tushirish

```bash
# Loglarni ko'rish
docker compose logs -f bot      # faqat bot loglari
docker compose logs -f webapp   # faqat webapp loglari

# Qayta ishga tushirish
docker compose restart

# Yangi versiya yuklaganda
docker compose down
docker compose up -d --build
```

## 9. Serverda fayllarni yangilash

```bash
cd /opt/freeuc
git pull                        # GitHubdan yangi versiya olish
docker compose down
docker compose up -d --build
```
