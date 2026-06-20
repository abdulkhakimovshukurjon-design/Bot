"""
Bot uchun barcha FSM (Finite State Machine) holatlari.
"""
from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_captcha = State()
    waiting_full_name = State()
    waiting_age = State()
    waiting_pubg_id = State()
    waiting_pubg_nickname = State()


class EditProfile(StatesGroup):
    waiting_new_pubg_id = State()


class AdminBroadcast(StatesGroup):
    waiting_message = State()
    waiting_confirm = State()


class AdminMessageUser(StatesGroup):
    waiting_user_id = State()
    waiting_message_text = State()


class AdminGrantPremium(StatesGroup):
    waiting_user_id = State()
    waiting_duration = State()


class AdminGrantUC(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()


class AdminDeductUC(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()


class AdminSearchUser(StatesGroup):
    waiting_query = State()


class AdminAddChannel(StatesGroup):
    waiting_channel = State()


class AdminRemoveChannel(StatesGroup):
    waiting_channel_choice = State()
