"""
Free UC Bot — Admin Panel (FastAPI + HTML/CSS/JS)

Bu webapp bot bilan bitta SQLite bazasini ishlatadi.
Ishga tushirish: python webapp/app.py  (yoki uvicorn webapp.app:app)
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, URLSafeSerializer

import config
from bot.database.connection import close_db, init_db, get_connection
from bot.database import users as users_db
from bot.database import channels as channels_db

BASE_DIR = Path(__file__).resolve().parent

import jinja2
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=jinja2.select_autoescape(),
    cache_size=0,
)

def render_template(name: str, status_code: int = 200, **context) -> HTMLResponse:
    template = _jinja_env.get_template(name)
    html = template.render(**context)
    return HTMLResponse(content=html, status_code=status_code)

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("webapp")

app = FastAPI(title="Free UC Bot - Admin Panel")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.exception_handler(Exception)
async def catch_all_exceptions(request: Request, exc: Exception):
    import traceback
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("Unhandled error on %s %s\n%s", request.method, request.url.path, tb)
    return JSONResponse({"detail": "Internal error"}, status_code=500)

serializer = URLSafeSerializer(config.WEBAPP_SECRET_KEY, salt="admin-session")
SESSION_COOKIE = "admin_session"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    await init_db(config.DB_PATH)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_db()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def create_session_token(username: str) -> str:
    return serializer.dumps({"username": username})


def verify_session(request: Request) -> Optional[str]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        data = serializer.loads(token)
        return data.get("username")
    except BadSignature:
        return None


def require_login(request: Request) -> Optional[RedirectResponse]:
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return None


async def _notify_user(user_id: int, text: str) -> None:
    """Foydalanuvchiga Telegram orqali qisqa muddatli Bot instance bilan xabar yuborish."""
    from aiogram import Bot

    bot = Bot(token=config.BOT_TOKEN)
    try:
        await bot.send_message(user_id, text)
    except Exception:
        pass
    finally:
        await bot.session.close()


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if verify_session(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return render_template("login.html", request=request, error=None)


@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == config.WEBAPP_ADMIN_USERNAME and password == config.WEBAPP_ADMIN_PASSWORD:
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        token = create_session_token(username)
        response.set_cookie(SESSION_COOKIE, token, httponly=True, max_age=60 * 60 * 24 * 7)
        return response

    return render_template(
        "login.html", request=request, error="❌ Login yoki parol noto'g'ri.",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    stats = await users_db.get_stats()
    return render_template("dashboard.html", request=request, stats=stats, active_page="dashboard")


# ---------------------------------------------------------------------------
# Users page
# ---------------------------------------------------------------------------
@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, page: int = 1):
    redirect = require_login(request)
    if redirect:
        return redirect

    limit = 25
    offset = (page - 1) * limit
    users = await users_db.get_all_users_paginated(offset=offset, limit=limit)

    for u in users:
        u["is_premium_now"] = await users_db.is_premium(u["user_id"])
        u["referral_count"] = await users_db.get_referral_count(u["user_id"])

    return render_template("users.html", request=request, users=users, page=page, active_page="users")


@app.get("/api/users/search")
async def api_search_user(q: str):
    user = await users_db.search_user(q)
    if not user:
        return JSONResponse({"found": False})

    is_premium = await users_db.is_premium(user["user_id"])
    referral_count = await users_db.get_referral_count(user["user_id"])
    user["is_premium_now"] = is_premium
    user["referral_count"] = referral_count
    return JSONResponse({"found": True, "user": user})


@app.post("/api/users/{user_id}/ban")
async def api_ban_user(user_id: int):
    await users_db.ban_user(user_id)
    return JSONResponse({"success": True})


@app.post("/api/users/{user_id}/unban")
async def api_unban_user(user_id: int):
    await users_db.unban_user(user_id)
    return JSONResponse({"success": True})


@app.post("/api/users/{user_id}/balance")
async def api_update_balance(user_id: int, amount: int = Form(...)):
    new_balance = await users_db.admin_adjust_balance(user_id, amount, admin_id=None, reason="webapp_admin")

    if amount > 0:
        text = f"🎉 Sizga admin tomonidan +{amount} UC qo'shildi!\n💰 Joriy balansingiz: {new_balance} UC"
    else:
        text = f"⚠️ Balansingizdan {abs(amount)} UC ayirildi.\n💰 Joriy balansingiz: {new_balance} UC"
    await _notify_user(user_id, text)

    return JSONResponse({"success": True, "new_balance": new_balance})


@app.post("/api/users/{user_id}/message")
async def api_send_user_message(user_id: int, text: str = Form(...)):
    await _notify_user(user_id, text)
    return JSONResponse({"success": True})


@app.post("/api/users/{user_id}/premium")
async def api_grant_premium(user_id: int, months: int = Form(...)):
    expires_iso = await users_db.grant_premium(user_id, months, granted_by=None)

    await _notify_user(
        user_id,
        f"💎 Sizga admin tomonidan {months} oylik Premium berildi!\n"
        f"📅 Premium muddati: {expires_iso[:10] if expires_iso else '—'} gacha",
    )

    return JSONResponse({"success": True, "expires_at": expires_iso})


# ---------------------------------------------------------------------------
# Channels page
# ---------------------------------------------------------------------------
@app.get("/channels", response_class=HTMLResponse)
async def channels_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    channels = await channels_db.get_all_channels()
    return render_template("channels.html", request=request, channels=channels, active_page="channels")


@app.post("/api/channels/add")
async def api_add_channel(username: str = Form(...), title: str = Form("")):
    from aiogram import Bot

    username = username.strip()
    if not username.startswith("@"):
        return JSONResponse({"success": False, "error": "Username @ bilan boshlanishi kerak"})

    bot = Bot(token=config.BOT_TOKEN)
    try:
        try:
            chat = await bot.get_chat(username)
        except Exception:
            return JSONResponse(
                {"success": False, "error": "Kanal topilmadi. Username to'g'riligini tekshiring."}
            )

        try:
            me = await bot.get_me()
            bot_member = await bot.get_chat_member(chat.id, me.id)
            if bot_member.status not in ("administrator", "creator"):
                return JSONResponse(
                    {"success": False, "error": "Bot bu kanalda administrator emas. Avval botni admin qiling."}
                )
        except Exception:
            return JSONResponse({"success": False, "error": "Botning kanaldagi statusini tekshirib bo'lmadi."})

        success = await channels_db.add_channel(str(chat.id), username, title or chat.title)
        if not success:
            return JSONResponse({"success": False, "error": "Bu kanal allaqachon ro'yxatda mavjud."})

        return JSONResponse({"success": True, "chat_id": str(chat.id), "title": chat.title})
    finally:
        await bot.session.close()


@app.post("/api/channels/{channel_id}/delete")
async def api_delete_channel(channel_id: int):
    success = await channels_db.remove_channel_by_id(channel_id)
    return JSONResponse({"success": success})


# ---------------------------------------------------------------------------
# Broadcast page
# ---------------------------------------------------------------------------
@app.get("/broadcast", response_class=HTMLResponse)
async def broadcast_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    conn = await get_connection()
    cursor = await conn.execute("SELECT * FROM broadcast_logs ORDER BY created_at DESC LIMIT 20")
    logs = [dict(r) for r in await cursor.fetchall()]

    return render_template("broadcast.html", request=request, logs=logs, active_page="broadcast")


@app.post("/api/broadcast/send")
async def api_send_broadcast(message: str = Form(""), photo: UploadFile | None = File(None), send_to_channels: str = Form("0")):
    """
    Webdan broadcast yuborish — aiogram Bot orqali to'g'ridan-to'g'ri yuboradi.
    Rasm fayl sifatida yuklansa, rasm + caption yuboradi, aks holda faqat matn.
    send_to_channels=1 bo'lsa, kanallarga ham yuboradi.
    """
    import asyncio
    from aiogram import Bot
    from aiogram.types import BufferedInputFile

    from bot.database import channels as channels_db

    bot = Bot(token=config.BOT_TOKEN)
    user_ids = await users_db.get_all_user_ids(only_active=True)
    channels = await channels_db.get_all_channels() if send_to_channels == "1" else []

    photo_bytes = await photo.read() if photo else None
    photo_name = photo.filename if photo else None

    sent, failed = 0, 0
    preview = message[:100] if message else f"[rasm: {photo_name or 'noma\'lum'}]"
    try:
        for uid in user_ids:
            try:
                if photo_bytes:
                    input_file = BufferedInputFile(file=photo_bytes, filename=photo_name or "photo.jpg")
                    await bot.send_photo(chat_id=uid, photo=input_file, caption=message or None)
                else:
                    await bot.send_message(uid, message)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)

        for ch in channels:
            try:
                chat_id = int(ch["chat_id"])
                if photo_bytes:
                    input_file = BufferedInputFile(file=photo_bytes, filename=photo_name or "photo.jpg")
                    await bot.send_photo(chat_id=chat_id, photo=input_file, caption=message or None)
                else:
                    await bot.send_message(chat_id, message)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)
    finally:
        await bot.session.close()

    conn = await get_connection()
    await conn.execute(
        "INSERT INTO broadcast_logs (admin_id, message_preview, sent_count, failed_count) VALUES (?, ?, ?, ?)",
        (0, preview, sent, failed),
    )
    await conn.commit()

    return JSONResponse({"success": True, "sent": sent, "failed": failed})


# ---------------------------------------------------------------------------
# Withdrawals page
# ---------------------------------------------------------------------------
@app.get("/withdrawals", response_class=HTMLResponse)
async def withdrawals_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    conn = await get_connection()
    cursor = await conn.execute(
        """
        SELECT w.*, u.full_name, u.username, u.pubg_id
        FROM withdrawals w
        LEFT JOIN users u ON u.user_id = w.user_id
        ORDER BY (w.status = 'pending') DESC, w.created_at DESC
        LIMIT 100
        """
    )
    withdrawals = [dict(r) for r in await cursor.fetchall()]

    return render_template("withdrawals.html", request=request, withdrawals=withdrawals, active_page="withdrawals")


@app.post("/api/withdrawals/{withdrawal_id}/complete")
async def api_complete_withdrawal(withdrawal_id: int):
    result = await users_db.complete_withdrawal(withdrawal_id)
    if not result:
        return JSONResponse({"success": False}, status_code=400)

    try:
        from aiogram import Bot

        bot = Bot(token=config.BOT_TOKEN)
        try:
            await bot.send_message(
                result["user_id"],
                f"✅ Sizning {result['amount']} UC miqdoridagi yechib olish so'rovingiz "
                "admin tomonidan bajarildi. UC tez orada hisobingizga tushadi!",
            )
        finally:
            await bot.session.close()
    except Exception:
        pass

    return JSONResponse({"success": True})


# ---------------------------------------------------------------------------
# CSV eksport
# ---------------------------------------------------------------------------
@app.get("/export/users.csv")
async def export_users_csv():
    import csv
    import io

    from fastapi.responses import StreamingResponse

    users = await users_db.get_all_users_paginated(offset=0, limit=100000)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["user_id", "full_name", "username", "pubg_id", "pubg_nickname", "uc_balance", "is_banned", "created_at"])
    for u in users:
        writer.writerow([
            u.get("user_id"), u.get("full_name"), u.get("username"), u.get("pubg_id"),
            u.get("pubg_nickname"), u.get("uc_balance"), u.get("is_banned"), u.get("created_at"),
        ])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )


@app.get("/export/withdrawals.csv")
async def export_withdrawals_csv():
    import csv
    import io

    from fastapi.responses import StreamingResponse

    conn = await get_connection()
    cursor = await conn.execute(
        """
        SELECT w.id, w.user_id, u.full_name, u.username, u.pubg_id, w.amount, w.status, w.created_at, w.completed_at
        FROM withdrawals w
        LEFT JOIN users u ON u.user_id = w.user_id
        ORDER BY w.created_at DESC
        """
    )
    rows = await cursor.fetchall()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "user_id", "full_name", "username", "pubg_id", "amount", "status", "created_at", "completed_at"])
    for r in rows:
        writer.writerow(list(r))
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=withdrawals.csv"},
    )


# ---------------------------------------------------------------------------
# Stats API (for dashboard auto-refresh / charts)
# ---------------------------------------------------------------------------
@app.get("/api/stats")
async def api_stats():
    stats = await users_db.get_stats()
    return JSONResponse(stats)


@app.get("/api/stats/top10")
async def api_top10():
    top = await users_db.get_top_users(10)
    return JSONResponse({"top": top})


@app.get("/api/stats/chart")
async def api_chart():
    daily = await users_db.get_daily_registrations(14)
    now = datetime.now()
    labels = []
    data = []
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).strftime("%d.%m")
        labels.append(day)
        val = 0
        for d in daily:
            d_day = d["day"]
            if isinstance(d_day, str):
                d_day = d_day[:10]
            if d_day == (now - timedelta(days=i)).strftime("%Y-%m-%d"):
                val = d["cnt"]
                break
        data.append(val)
    return JSONResponse({"labels": labels, "data": data})


# ---------------------------------------------------------------------------
# Games (Telegram WebApp)
# ---------------------------------------------------------------------------
import hashlib
import hmac
import random
from urllib.parse import parse_qs

_GAMES_DATA: dict = {"upgrade_levels": {}, "battles": {}}

BARABAN_MULTIPLIERS = [0, 0.5, 1, 1.5, 2, 3, 5, 10, 20]
BARABAN_WEIGHTS = [40, 20, 15, 10, 7, 4, 2, 1, 1]

PLINKO_MULTIPLIERS = [0.2, 0.5, 1, 2, 3, 5, 10, 5, 3, 2, 1, 0.5, 0.2]


def _parse_webapp_init(init_data: str) -> dict | None:
    """Validate Telegram WebApp init data and return parsed params."""
    try:
        parsed = parse_qs(init_data)
        params = {k: v[0] for k, v in parsed.items()}
        received_hash = params.pop("hash", None)
        if not received_hash:
            return None

        secret_key = hmac.new(
            b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256
        ).digest()

        check_items = sorted(
            [f"{k}={v}" for k, v in params.items()],
            key=lambda x: x.lower(),
        )
        data_check_string = "\n".join(check_items)

        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if computed_hash != received_hash:
            return None
        return params
    except Exception:
        return None


@app.post("/api/games/init")
async def api_games_init(data: dict):
    import json

    init_data = data.get("initData", "")
    if not init_data:
        return JSONResponse({"ok": False, "error": "initData yo'q"})

    params = _parse_webapp_init(init_data)
    if not params:
        return JSONResponse({"ok": False, "error": "Noto'g'ri initData"})

    try:
        user_info = json.loads(params.get("user", "{}"))
        user_id = user_info.get("id")
        if not user_id:
            return JSONResponse({"ok": False, "error": "user_id topilmadi"})
    except Exception:
        return JSONResponse({"ok": False, "error": "user ma'lumotlarini o'qib bo'lmadi"})

    user = await users_db.get_user(user_id)
    if not user:
        return JSONResponse({"ok": False, "error": "Foydalanuvchi topilmadi"})

    return JSONResponse({
        "ok": True,
        "user": {"id": user_id, "full_name": user.get("full_name")},
        "balance": user.get("uc_balance", 0),
    })


@app.get("/games", response_class=HTMLResponse)
async def games_page(request: Request):
    return render_template("games.html", request=request)


@app.post("/api/games/baraban/play")
async def api_baraban_play(data: dict):
    import json

    init_data = data.get("initData", "")
    params = _parse_webapp_init(init_data)
    if not params:
        return JSONResponse({"ok": False, "error": "Noto'g'ri initData"})
    try:
        user_id = json.loads(params["user"])["id"]
    except Exception:
        return JSONResponse({"ok": False, "error": "user_id topilmadi"})

    amount = data.get("amount", 0)
    if amount <= 0:
        return JSONResponse({"ok": False, "error": "Noto'g'ri miqdor"})

    user = await users_db.get_user(user_id)
    if not user or user["uc_balance"] < amount:
        return JSONResponse({"ok": False, "error": "Balans yetarli emas"})

    await users_db.admin_adjust_balance(user_id, -amount, reason="game_baraban")
    mult = random.choices(BARABAN_MULTIPLIERS, weights=BARABAN_WEIGHTS, k=1)[0]
    win = int(amount * mult)

    segments = ["0️⃣", "½️⃣", "1️⃣", "1.5️⃣", "2️⃣", "3️⃣", "5️⃣", "🔟", "2️⃣0️⃣"]
    idx = BARABAN_MULTIPLIERS.index(mult)
    wheel = " ".join(segments[:idx]) + f" ▶️{segments[idx]}◀️ " + " ".join(segments[idx+1:])

    msg = ""
    if win > 0:
        await users_db.add_balance(user_id, win)
        msg = f"🎉 Yutdingiz! +{win} UC (x{mult})"
    else:
        msg = f"😔 {amount} UC yo'qotildi"

    new_bal = await users_db.get_user(user_id)
    bal = new_bal["uc_balance"] if new_bal else 0

    return JSONResponse({
        "ok": True, "game": "baraban",
        "win": win, "amount": amount, "multiplier": mult,
        "wheel": wheel, "balance": bal,
    })


@app.post("/api/games/plinko/play")
async def api_plinko_play(data: dict):
    import json

    init_data = data.get("initData", "")
    params = _parse_webapp_init(init_data)
    if not params:
        return JSONResponse({"ok": False, "error": "Noto'g'ri initData"})
    try:
        user_id = json.loads(params["user"])["id"]
    except Exception:
        return JSONResponse({"ok": False, "error": "user_id topilmadi"})

    amount = data.get("amount", 0)
    if amount <= 0:
        return JSONResponse({"ok": False, "error": "Noto'g'ri miqdor"})

    user = await users_db.get_user(user_id)
    if not user or user["uc_balance"] < amount:
        return JSONResponse({"ok": False, "error": "Balans yetarli emas"})

    await users_db.admin_adjust_balance(user_id, -amount, reason="game_plinko")
    plinko_range = len(PLINKO_MULTIPLIERS)
    idx = random.randrange(plinko_range)
    mult = PLINKO_MULTIPLIERS[idx]
    win = int(amount * mult)

    rows = 8
    lines = []
    col = idx
    for _ in range(rows):
        line = ["⬜"] * plinko_range
        if 0 <= col < plinko_range:
            line[col] = "🔴"
        lines.append("".join(line))
        col += random.choice([-1, 0, 1])
        col = max(0, min(plinko_range - 1, col))

    lines.append("━" * plinko_range)
    m = [f"{x}x" if x < 10 else f"{int(x)}x" for x in PLINKO_MULTIPLIERS]
    lines.append("".join(f"{v:>3}" for v in m))
    board = "\n".join(lines)

    if win > 0:
        await users_db.add_balance(user_id, win)

    new_bal = await users_db.get_user(user_id)
    bal = new_bal["uc_balance"] if new_bal else 0

    return JSONResponse({
        "ok": True, "game": "plinko",
        "win": win, "amount": amount, "multiplier": mult,
        "board": board, "balance": bal,
    })


@app.post("/api/games/upgrade/status")
async def api_upgrade_status(data: dict | None = None):
    import json

    init_data = (data or {}).get("initData", "")
    params = _parse_webapp_init(init_data) if init_data else None
    if not params:
        return JSONResponse({"ok": False, "error": "initData yo'q"})
    try:
        user_id = json.loads(params["user"])["id"]
    except Exception:
        return JSONResponse({"ok": False, "error": "user_id topilmadi"})

    level = _GAMES_DATA.setdefault(user_id, {}).get("upgrade_level", 0)
    cost = 50 + level * 75
    chance = max(5, 90 - level * 8)
    return JSONResponse({"ok": True, "level": level, "cost": cost, "chance": chance})


@app.post("/api/games/upgrade/play")
async def api_upgrade_play(data: dict):
    import json

    init_data = data.get("initData", "")
    params = _parse_webapp_init(init_data)
    if not params:
        return JSONResponse({"ok": False, "error": "Noto'g'ri initData"})
    try:
        user_id = json.loads(params["user"])["id"]
    except Exception:
        return JSONResponse({"ok": False, "error": "user_id topilmadi"})

    _GAMES_DATA.setdefault(user_id, {})
    level = _GAMES_DATA[user_id].get("upgrade_level", 0)
    cost = 50 + level * 75

    user = await users_db.get_user(user_id)
    if not user or user["uc_balance"] < cost:
        return JSONResponse({"ok": False, "error": "Balans yetarli emas"})

    await users_db.admin_adjust_balance(user_id, -cost, reason="game_upgrade")
    chance = max(5, 90 - level * 8)
    success = random.randint(1, 100) <= chance

    if success:
        new_level = level + 1
        _GAMES_DATA[user_id]["upgrade_level"] = new_level
        await users_db.add_balance(user_id, cost * 2)
        new_bal = await users_db.get_user(user_id)
        bal = new_bal["uc_balance"] if new_bal else 0
        return JSONResponse({
            "ok": True, "game": "upgrade",
            "win": cost * 2, "amount": cost, "multiplier": 2,
            "level": new_level, "balance": bal,
        })
    else:
        _GAMES_DATA[user_id]["upgrade_level"] = 0
        new_bal = await users_db.get_user(user_id)
        bal = new_bal["uc_balance"] if new_bal else 0
        return JSONResponse({
            "ok": True, "game": "upgrade",
            "win": 0, "amount": cost, "multiplier": 0,
            "level": 0, "balance": bal,
        })


@app.post("/api/games/dice/play")
async def api_dice_play(data: dict):
    import json

    init_data = data.get("initData", "")
    params = _parse_webapp_init(init_data)
    if not params:
        return JSONResponse({"ok": False, "error": "Noto'g'ri initData"})
    try:
        user_id = json.loads(params["user"])["id"]
    except Exception:
        return JSONResponse({"ok": False, "error": "user_id topilmadi"})

    amount = data.get("amount", 0)
    chosen = data.get("number", 0)

    if amount <= 0 or chosen < 1 or chosen > 6:
        return JSONResponse({"ok": False, "error": "Noto'g'ri ma'lumot"})

    user = await users_db.get_user(user_id)
    if not user or user["uc_balance"] < amount:
        return JSONResponse({"ok": False, "error": "Balans yetarli emas"})

    await users_db.admin_adjust_balance(user_id, -amount, reason="game_dice")
    result = random.randint(1, 6)
    dice_faces = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

    if result == chosen:
        win = amount * 6
        await users_db.add_balance(user_id, win)
    else:
        win = 0

    new_bal = await users_db.get_user(user_id)
    bal = new_bal["uc_balance"] if new_bal else 0

    return JSONResponse({
        "ok": True, "game": "dice",
        "win": win, "amount": amount, "multiplier": 6 if win > 0 else 0,
        "result": result, "chosen": chosen,
        "dice_face": dice_faces[result], "balance": bal,
    })


@app.post("/api/games/battle_create/play")
async def api_battle_create(data: dict):
    import json

    init_data = data.get("initData", "")
    params = _parse_webapp_init(init_data)
    if not params:
        return JSONResponse({"ok": False, "error": "Noto'g'ri initData"})
    try:
        user_id = json.loads(params["user"])["id"]
    except Exception:
        return JSONResponse({"ok": False, "error": "user_id topilmadi"})

    amount = data.get("amount", 0)
    if amount <= 0:
        return JSONResponse({"ok": False, "error": "Noto'g'ri miqdor"})

    user = await users_db.get_user(user_id)
    if not user or user["uc_balance"] < amount:
        return JSONResponse({"ok": False, "error": "Balans yetarli emas"})

    await users_db.admin_adjust_balance(user_id, -amount, reason="game_battle")
    import time
    battle_id = int(time.time() * 1000) % 1000000
    _GAMES_DATA["battles"][battle_id] = {
        "creator_id": user_id,
        "amount": amount,
    }

    return JSONResponse({
        "ok": True, "battle_id": battle_id, "amount": amount,
    })


@app.post("/api/games/battle_list/play")
async def api_battle_list(data: dict):
    active = []
    for bid, b in list(_GAMES_DATA["battles"].items()):
        creator = await users_db.get_user(b["creator_id"])
        active.append({
            "id": bid,
            "creator_id": b["creator_id"],
            "creator_name": creator.get("full_name") if creator else str(b["creator_id"]),
            "amount": b["amount"],
        })
    return JSONResponse({"ok": True, "battles": active})


@app.post("/api/games/battle_join/play")
async def api_battle_join(data: dict):
    import json

    init_data = data.get("initData", "")
    params = _parse_webapp_init(init_data)
    if not params:
        return JSONResponse({"ok": False, "error": "Noto'g'ri initData"})
    try:
        user_id = json.loads(params["user"])["id"]
    except Exception:
        return JSONResponse({"ok": False, "error": "user_id topilmadi"})

    battle_id = data.get("battle_id")
    if battle_id not in _GAMES_DATA["battles"]:
        return JSONResponse({"ok": False, "error": "Battle topilmadi"})

    battle = _GAMES_DATA["battles"][battle_id]
    creator_id = battle["creator_id"]
    if user_id == creator_id:
        return JSONResponse({"ok": False, "error": "O'zingiz bilan jang qila olmaysiz"})

    amount = battle["amount"]
    user = await users_db.get_user(user_id)
    if not user or user["uc_balance"] < amount:
        return JSONResponse({"ok": False, "error": "Balans yetarli emas"})

    await users_db.admin_adjust_balance(user_id, -amount, reason="game_battle")

    total = amount * 2
    p1_chance = (amount / total) * 100
    winner = random.choices(
        [creator_id, user_id],
        weights=[p1_chance, 100 - p1_chance],
        k=1
    )[0]

    if winner == creator_id:
        await users_db.add_balance(creator_id, total)
    else:
        await users_db.add_balance(user_id, total)

    del _GAMES_DATA["battles"][battle_id]

    new_bal = await users_db.get_user(user_id)
    bal = new_bal["uc_balance"] if new_bal else 0

    return JSONResponse({
        "ok": True, "game": "battle",
        "win": total if winner == user_id else 0,
        "amount": amount, "multiplier": 2,
        "winner_id": winner, "total": total,
        "balance": bal,
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=config.WEBAPP_HOST, port=config.WEBAPP_PORT, reload=False)
