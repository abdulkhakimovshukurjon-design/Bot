import logging
import random

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.database import users as users_db
from bot.keyboards.reply import games_menu_kb, main_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="games")

GAMES = {}


def _setup_games():
    global GAMES
    GAMES = {
        "user_bets": {},
        "battles": {},
    }


_setup_games()

# ---------------------------------------------------------------------------
# Games menu
# ---------------------------------------------------------------------------
@router.message(F.text == "🎮 O'yinlar")
async def show_games_menu(message: Message) -> None:
    await message.answer("🎮 O'yinlar bo'limiga xush kelibsiz!\n\nO'z UC balansingizni oshiring!", reply_markup=games_menu_kb())


@router.message(F.text == "⬅️ Orqaga")
async def back_to_main(message: Message) -> None:
    await message.answer("🏠 Asosiy menyu.", reply_markup=main_menu_kb())


# ---------------------------------------------------------------------------
# Helper: bet amount selection
# ---------------------------------------------------------------------------
def bet_kb(game: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 UC", callback_data=f"{game}_bet_10"),
         InlineKeyboardButton(text="25 UC", callback_data=f"{game}_bet_25"),
         InlineKeyboardButton(text="50 UC", callback_data=f"{game}_bet_50")],
        [InlineKeyboardButton(text="100 UC", callback_data=f"{game}_bet_100"),
         InlineKeyboardButton(text="250 UC", callback_data=f"{game}_bet_250"),
         InlineKeyboardButton(text="500 UC", callback_data=f"{game}_bet_500")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"{game}_back")],
    ])


async def _get_balance(user_id: int) -> int:
    user = await users_db.get_user(user_id)
    return user["uc_balance"] if user else 0


async def _deduct(user_id: int, amount: int) -> bool:
    user = await users_db.get_user(user_id)
    if not user or user["uc_balance"] < amount:
        return False
    await users_db.admin_adjust_balance(user_id, -amount, admin_id=None, reason=f"game")
    return True


async def _add_win(user_id: int, amount: int) -> None:
    await users_db.add_balance(user_id, amount)


# ---------------------------------------------------------------------------
# 1. BARABAN (Wheel Spin)
# ---------------------------------------------------------------------------
BARABAN_MULTIPLIERS = [0, 0.5, 1, 1.5, 2, 3, 5, 10, 20]
BARABAN_WEIGHTS = [40, 20, 15, 10, 7, 4, 2, 1, 1]  # %


@router.message(F.text == "🎰 Baraban")
async def baraban_start(message: Message) -> None:
    bal = await _get_balance(message.from_user.id)
    await message.answer(
        f"🎰 BARABAN\n\n"
        f"💰 Balans: {bal} UC\n\n"
        f"Koeffitsiyentlar: 0x, 0.5x, 1x, 1.5x, 2x, 3x, 5x, 10x, 20x\n"
        f"Qancha tikmoqchisiz?",
        reply_markup=bet_kb("baraban"),
    )


@router.callback_query(lambda c: c.data.startswith("baraban_bet_"))
async def baraban_spin(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[-1])
    bal = await _get_balance(user_id)
    if bal < amount:
        await callback.message.edit_text("❌ Balansingizda yetarli UC mavjud emas.")
        return

    await _deduct(user_id, amount)

    mult = random.choices(BARABAN_MULTIPLIERS, weights=BARABAN_WEIGHTS, k=1)[0]
    win = int(amount * mult)

    segments = ["0️⃣", "½️⃣", "1️⃣", "1.5️⃣", "2️⃣", "3️⃣", "5️⃣", "🔟", "2️⃣0️⃣"]
    idx = BARABAN_MULTIPLIERS.index(mult)
    wheel = " ".join(segments[:idx]) + f" ▶️{segments[idx]}◀️ " + " ".join(segments[idx+1:])

    msg = f"🎰 BARABAN NATIJASI\n\n{wheel}\n\n"
    if win > 0:
        await _add_win(user_id, win)
        msg += f"🎉 Yutdingiz! +{win} UC (x{mult})"
    else:
        msg += f"😔 Yutqazdingiz. {amount} UC yo'qotildi."

    new_bal = await _get_balance(user_id)
    msg += f"\n\n💰 Balans: {new_bal} UC"
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Qayta o'ynash", callback_data="baraban_bet_again")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="baraban_back")],
    ]))


@router.callback_query(lambda c: c.data == "baraban_bet_again")
async def baraban_again(callback: CallbackQuery) -> None:
    bal = await _get_balance(callback.from_user.id)
    await callback.message.edit_text(
        f"🎰 BARABAN\n\n💰 Balans: {bal} UC\n\nQancha tikmoqchisiz?",
        reply_markup=bet_kb("baraban"),
    )


@router.callback_query(lambda c: c.data == "baraban_back")
async def baraban_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🎮 O'yinlar bo'limi.", reply_markup=None)
    await callback.message.answer("Boshqa o'yin tanlang.", reply_markup=games_menu_kb())


# ---------------------------------------------------------------------------
# 2. PLINKO
# ---------------------------------------------------------------------------
PLINKO_MULTIPLIERS = [0.2, 0.5, 1, 2, 3, 5, 10, 5, 3, 2, 1, 0.5, 0.2]
PLINKO_RANGE = len(PLINKO_MULTIPLIERS)


@router.message(F.text == "🧩 Plinko")
async def plinko_start(message: Message) -> None:
    bal = await _get_balance(message.from_user.id)
    await message.answer(
        f"🧩 PLINKO\n\n"
        f"💰 Balans: {bal} UC\n\n"
        f"Koeffitsiyentlar: 0.2x ~ 10x gacha\n"
        f"Qancha tikmoqchisiz?",
        reply_markup=bet_kb("plinko"),
    )


@router.callback_query(lambda c: c.data.startswith("plinko_bet_"))
async def plinko_drop(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[-1])
    bal = await _get_balance(user_id)
    if bal < amount:
        await callback.message.edit_text("❌ Balansingizda yetarli UC mavjud emas.")
        return

    await _deduct(user_id, amount)

    positions = list(range(PLINKO_RANGE))
    weights = [1] * PLINKO_RANGE
    idx = random.choices(positions, weights=weights, k=1)[0]
    mult = PLINKO_MULTIPLIERS[idx]
    win = int(amount * mult)

    rows = 8
    board = []
    col = idx
    for r in range(rows):
        line = ["⬜"] * PLINKO_RANGE
        if col >= 0 and col < PLINKO_RANGE:
            line[col] = "🔴"
        board.append("".join(line))
        col += random.choice([-1, 0, 1])
        col = max(0, min(PLINKO_RANGE - 1, col))

    board.append("━" * PLINKO_RANGE)
    multipliers_display = [f"{m}x" if m < 10 else f"{int(m)}x" for m in PLINKO_MULTIPLIERS]
    board.append("".join(f"{m:>3}" for m in multipliers_display))

    msg = f"🧩 PLINKO NATIJASI\n\n```\n" + "\n".join(board) + f"\n```\n"
    if win > 0:
        await _add_win(user_id, win)
        msg += f"\n🎉 Yutdingiz! +{win} UC (x{mult})"
    else:
        msg += f"\n😔 Yutqazdingiz. {amount} UC yo'qotildi."

    new_bal = await _get_balance(user_id)
    msg += f"\n💰 Balans: {new_bal} UC"
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Qayta o'ynash", callback_data="plinko_bet_again")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="plinko_back")],
    ]))


@router.callback_query(lambda c: c.data == "plinko_bet_again")
async def plinko_again(callback: CallbackQuery) -> None:
    bal = await _get_balance(callback.from_user.id)
    await callback.message.edit_text(
        f"🧩 PLINKO\n\n💰 Balans: {bal} UC\n\nQancha tikmoqchisiz?",
        reply_markup=bet_kb("plinko"),
    )


@router.callback_query(lambda c: c.data == "plinko_back")
async def plinko_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🎮 O'yinlar bo'limi.", reply_markup=None)
    await callback.message.answer("Boshqa o'yin tanlang.", reply_markup=games_menu_kb())


# ---------------------------------------------------------------------------
# 3. UPGRADE
# ---------------------------------------------------------------------------
@router.message(F.text == "⬆️ Upgrade")
async def upgrade_start(message: Message) -> None:
    user_id = message.from_user.id
    bal = await _get_balance(user_id)
    level = GAMES.setdefault(user_id, {}).get("upgrade_level", 0)

    cost = _upgrade_cost(level)
    success_chance = _upgrade_chance(level)

    msg = (
        f"⬆️ UPGRADE\n\n"
        f"🔧 Sizning darajangiz: {level}\n"
        f"💰 Balans: {bal} UC\n"
        f"💵 Yangilash narxi: {cost} UC\n"
        f"📈 Muvaffaqiyat foizi: {success_chance}%\n\n"
        f"⚠️ Agar muvaffaqiyatsiz bo'lsa, darajangiz 0 ga tushadi!"
    )
    await message.answer(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️ Yangilash", callback_data="upgrade_do")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="upgrade_back")],
    ]))


def _upgrade_cost(level: int) -> int:
    return 50 + level * 75


def _upgrade_chance(level: int) -> int:
    return max(5, 90 - level * 8)


@router.callback_query(lambda c: c.data == "upgrade_do")
async def upgrade_do(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    bal = await _get_balance(user_id)
    level = GAMES.setdefault(user_id, {}).get("upgrade_level", 0)
    cost = _upgrade_cost(level)
    chance = _upgrade_chance(level)

    if bal < cost:
        await callback.message.edit_text("❌ Balansingizda yetarli UC mavjud emas.")
        return

    await _deduct(user_id, cost)
    success = random.randint(1, 100) <= chance

    if success:
        GAMES[user_id]["upgrade_level"] = level + 1
        new_level = level + 1
        await _add_win(user_id, cost * 2)
        msg = f"✅ Yangilash muvaffaqiyatli! Darajangiz: {new_level}\n💰 +{cost * 2} UC sovrin!"
    else:
        GAMES[user_id]["upgrade_level"] = 0
        msg = f"❌ Yangilash muvaffaqiyatsiz! Darajangiz 0 ga tushdi."

    new_bal = await _get_balance(user_id)
    msg += f"\n💰 Balans: {new_bal} UC"
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Qayta urinish", callback_data="upgrade_retry")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="upgrade_back")],
    ]))


@router.callback_query(lambda c: c.data == "upgrade_retry")
async def upgrade_retry(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    bal = await _get_balance(user_id)
    level = GAMES.setdefault(user_id, {}).get("upgrade_level", 0)
    cost = _upgrade_cost(level)
    chance = _upgrade_chance(level)

    msg = (
        f"⬆️ UPGRADE\n\n"
        f"🔧 Sizning darajangiz: {level}\n"
        f"💰 Balans: {bal} UC\n"
        f"💵 Yangilash narxi: {cost} UC\n"
        f"📈 Muvaffaqiyat foizi: {chance}%\n\n"
        f"⚠️ Agar muvaffaqiyatsiz bo'lsa, darajangiz 0 ga tushadi!"
    )
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️ Yangilash", callback_data="upgrade_do")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="upgrade_back")],
    ]))


@router.callback_query(lambda c: c.data == "upgrade_back")
async def upgrade_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🎮 O'yinlar bo'limi.", reply_markup=None)
    await callback.message.answer("Boshqa o'yin tanlang.", reply_markup=games_menu_kb())


# ---------------------------------------------------------------------------
# 4. UC BATTLE (PvP)
# ---------------------------------------------------------------------------
@router.message(F.text == "⚔️ UC Battle")
async def battle_start(message: Message) -> None:
    bal = await _get_balance(message.from_user.id)
    await message.answer(
        f"⚔️ UC BATTLE\n\n"
        f"💰 Balans: {bal} UC\n\n"
        f"Boshqa foydalanuvchi bilan jang qiling!\n"
        f"Kim ko'p UC tiksa, yutish foizi shuncha yuqori.\n\n"
        f"Qancha UC tikmoqchisiz?",
        reply_markup=bet_kb("battle"),
    )


@router.callback_query(lambda c: c.data.startswith("battle_bet_"))
async def battle_create(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[-1])
    bal = await _get_balance(user_id)
    if bal < amount:
        await callback.message.edit_text("❌ Balansingizda yetarli UC mavjud emas.")
        return

    await _deduct(user_id, amount)
    GAMES["battles"][user_id] = {"amount": amount, "player1": user_id}

    await callback.message.edit_text(
        f"⚔️ UC BATTLE — Jang yaratildi!\n\n"
        f"💵 Sizning tikingiz: {amount} UC\n\n"
        f"🔗 Raqibni kutmoqda...\n"
        f"Raqib /battle_{user_id} komandasini yozib qatnashsin.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="battle_cancel")],
        ]),
    )


@router.message(lambda m: m.text and m.text.startswith("/battle_"))
async def battle_join(message: Message) -> None:
    try:
        creator_id = int(message.text.split("_")[1])
    except (IndexError, ValueError):
        await message.answer("❌ Noto'g'ri format. /battle_<user_id>")
        return

    if creator_id not in GAMES["battles"]:
        await message.answer("❌ Bu battle mavjud emas yoki tugagan.")
        return

    user_id = message.from_user.id
    if user_id == creator_id:
        await message.answer("❌ O'zingiz bilan jang qila olmaysiz!")
        return

    battle = GAMES["battles"][creator_id]
    p1_amount = battle["amount"]
    p2_amount = p1_amount
    bal = await _get_balance(user_id)

    if bal < p2_amount:
        await message.answer(f"❌ Balansingizda {p2_amount} UC mavjud emas. Battle qatnashish uchun {p2_amount} UC kerak.")
        return

    await _deduct(user_id, p2_amount)

    total = p1_amount + p2_amount
    p1_chance = (p1_amount / total) * 100

    winner = random.choices(
        [creator_id, user_id],
        weights=[p1_chance, 100 - p1_chance],
        k=1
    )[0]

    if winner == creator_id:
        await _add_win(creator_id, total)
        result = f"🏆 {creator_id} (yoki siz) yutdi! +{total} UC!"
    else:
        await _add_win(user_id, total)
        result = f"🏆 Siz yutdingiz! +{total} UC!"

    del GAMES["battles"][creator_id]

    result_text = (
        f"⚔️ BATTLE NATIJASI\n\n"
        f"👤 Raqib 1: {creator_id} — {p1_amount} UC ({p1_chance:.0f}%)\n"
        f"👤 Raqib 2: {user_id} — {p2_amount} UC ({100-p1_chance:.0f}%)\n\n"
        f"{result}"
    )
    await message.answer(result_text)
    try:
        await message.bot.send_message(creator_id, result_text)
    except Exception:
        pass


@router.callback_query(lambda c: c.data == "battle_cancel")
async def battle_cancel(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if user_id in GAMES["battles"]:
        amount = GAMES["battles"][user_id]["amount"]
        await _add_win(user_id, amount)
        del GAMES["battles"][user_id]
        await callback.message.edit_text("❌ Battle bekor qilindi. Tikingiz qaytarildi.")
    else:
        await callback.message.edit_text("❌ Battle topilmadi.")


# ---------------------------------------------------------------------------
# 5. DICE
# ---------------------------------------------------------------------------
@router.message(F.text == "🎲 Dice")
async def dice_start(message: Message) -> None:
    bal = await _get_balance(message.from_user.id)
    msg = (
        f"🎲 DICE\n\n"
        f"💰 Balans: {bal} UC\n\n"
        f"🎯 1 dan 6 gacha son tanlang!\n"
        f"Agar soningiz tushsa, tikingiz 6 barobar qaytadi!\n"
        f"Masalan: 10 UC tikib, 5 sonini tanlasangiz va 5 tushsa → +60 UC!\n\n"
        f"Qancha tikmoqchisiz?"
    )
    await message.answer(msg, reply_markup=bet_kb("dice"))


@router.callback_query(lambda c: c.data.startswith("dice_bet_"))
async def dice_choose_number(callback: CallbackQuery) -> None:
    amount = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    GAMES.setdefault(user_id, {})["dice_bet"] = amount

    numbers = []
    row = []
    for n in range(1, 7):
        row.append(InlineKeyboardButton(text=str(n), callback_data=f"dice_num_{n}"))
        if n % 3 == 0:
            numbers.append(row)
            row = []
    if row:
        numbers.append(row)
    numbers.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="dice_back")])

    await callback.message.edit_text(
        f"🎲 1 dan 6 gacha sonni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=numbers),
    )


@router.callback_query(lambda c: c.data.startswith("dice_num_"))
async def dice_roll(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    chosen = int(callback.data.split("_")[-1])
    amount = GAMES.get(user_id, {}).get("dice_bet", 10)
    bal = await _get_balance(user_id)

    if bal < amount:
        await callback.message.edit_text("❌ Balansingizda yetarli UC mavjud emas.")
        return

    await _deduct(user_id, amount)
    result = random.randint(1, 6)

    dice_faces = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    msg = f"🎲 DICE NATIJASI\n\nSizning tanlovingiz: {chosen}\nTushgan son: {result} {dice_faces[result]}\n\n"

    if result == chosen:
        win = amount * 6
        await _add_win(user_id, win)
        msg += f"🎉 Tabriklaymiz! +{win} UC (x6)"
    else:
        msg += f"😔 Yutqazdingiz. {amount} UC yo'qotildi."

    new_bal = await _get_balance(user_id)
    msg += f"\n\n💰 Balans: {new_bal} UC"
    await callback.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Qayta o'ynash", callback_data="dice_bet_again")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="dice_back")],
    ]))


@router.callback_query(lambda c: c.data == "dice_bet_again")
async def dice_again(callback: CallbackQuery) -> None:
    bal = await _get_balance(callback.from_user.id)
    await callback.message.edit_text(
        f"🎲 DICE\n\n💰 Balans: {bal} UC\n\nQancha tikmoqchisiz?",
        reply_markup=bet_kb("dice"),
    )


@router.callback_query(lambda c: c.data == "dice_back")
async def dice_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🎮 O'yinlar bo'limi.", reply_markup=None)
    await callback.message.answer("Boshqa o'yin tanlang.", reply_markup=games_menu_kb())
