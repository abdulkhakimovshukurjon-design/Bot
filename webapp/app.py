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

from fastapi import FastAPI, Form, Request, status
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

app = FastAPI(title="Free UC Bot - Admin Panel")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

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
async def api_send_broadcast(message: str = Form(...)):
    """
    Webdan broadcast yuborish — aiogram Bot orqali to'g'ridan-to'g'ri yuboradi.
    Eslatma: bot.py jarayoni alohida ishlayotgan bo'lsa ham, bu yerda mustaqil Bot
    instance yaratib xabar yuboramiz.
    """
    import asyncio
    from aiogram import Bot

    bot = Bot(token=config.BOT_TOKEN)
    user_ids = await users_db.get_all_user_ids(only_active=True)

    sent, failed = 0, 0
    try:
        for uid in user_ids:
            try:
                await bot.send_message(uid, message)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)
    finally:
        await bot.session.close()

    conn = await get_connection()
    await conn.execute(
        "INSERT INTO broadcast_logs (admin_id, message_preview, sent_count, failed_count) VALUES (?, ?, ?, ?)",
        (0, message[:100], sent, failed),
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=config.WEBAPP_HOST, port=config.WEBAPP_PORT, reload=False)
