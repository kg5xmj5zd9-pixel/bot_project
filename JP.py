import os
import json
import uuid
import asyncio
import logging
import ssl
import certifi
import aiohttp

from pathlib import Path
from datetime import datetime

from aiogram.types import FSInputFile
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# CONFIG

BOT_TOKEN = "8620429120:AAFL_eqH8QNoTXXeW4whPS_tHTPJJM9eyCg"
CRYPTO_PAY_TOKEN = "580016:AAtAOHw8wzibm6MHeMVWtWMQOPzVYqwbf2c"

SHOP_NAME = "jp_regs"
SUPPORT = "@ivy_kauf"

PRODUCT_PRICE = 6

# GOODS DIR (ONLY CHANGE HERE)

def get_desktop():
    home = Path.home()
    desktop = home / "Desktop"

    if not desktop.exists():
        desktop = home / "Рабочий стол"

    return desktop


GOODS_DIR = get_desktop() / "goods"

USERS_DB = Path("users.json")

# SSL FIX

ssl_context = ssl.create_default_context(
    cafile=certifi.where()
)

# LOGGING

logging.basicConfig(level=logging.INFO)

# BOT

bot = Bot(BOT_TOKEN)

dp = Dispatcher(
    storage=MemoryStorage()
)

users = {}

# STATES

class TopUpState(StatesGroup):
    waiting_amount = State()

# RULES

RULES_TEXT = f"""
⚖ ПРАВИЛА 

✦ Проверяйте товар сразу, возврат/замена возможны в течение 30 минут с момента покупки аккаунта.
✦ Замена предоставляется только при заливе с хорошего прокси и антика.
✦ ЖП регс лучший шоп
✦ По всем вопросам писать сапу

✦ Support: {SUPPORT}
"""

# DATABASE

def load_users():

    global users

    if USERS_DB.exists():

        with open(
            USERS_DB,
            "r",
            encoding="utf-8"
        ) as f:

            raw_users = json.load(f)

        for user_id, value in raw_users.items():

            if isinstance(value, dict):

                users[user_id] = value

            else:

                users[user_id] = {
                    "balance": float(value)
                }

    else:
        users = {}

def save_users():

    with open(
        USERS_DB,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            users,
            f,
            indent=2,
            ensure_ascii=False
        )

# USER

def ensure_user(user_id):

    user_id = str(user_id)

    if user_id not in users:

        users[user_id] = {
            "balance": 0
        }

        save_users()

# GOODS

def ensure_goods():

    GOODS_DIR.mkdir(exist_ok=True)

def get_goods():

    ensure_goods()

    return [
        f for f in GOODS_DIR.iterdir()
        if f.suffix == ".txt"
    ]

# MENU

def menu():

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Купить")],
            [
                KeyboardButton(text="◆ Наличие"),
                KeyboardButton(text="⚖ Правила")
            ],
            [
                KeyboardButton(text="⌬ Баланс"),
                KeyboardButton(text="✚ Пополнить")
            ],
            [KeyboardButton(text="✦ Support")]
        ],
        resize_keyboard=True
    )

# START

@dp.message(Command("start"))
async def start(message: types.Message):

    ensure_user(message.from_user.id)

    await message.answer(
        f"✦ Добро пожаловать в {SHOP_NAME}",
        reply_markup=menu()
    )

# ======================================================
# RULES
# ======================================================

@dp.message(F.text == "⚖ Правила")
async def rules(message: types.Message):

    await message.answer(RULES_TEXT)

# ======================================================
# BALANCE
# ======================================================

@dp.message(F.text == "⌬ Баланс")
async def balance(message: types.Message):

    ensure_user(message.from_user.id)

    user_id = str(message.from_user.id)

    balance_value = users[user_id]["balance"]

    await message.answer(
        f"✦ Ваш баланс: {balance_value}$"
    )

# ======================================================
# STOCK
# ======================================================

@dp.message(F.text == "◆ Наличие")
async def stock(message: types.Message):

    await message.answer(
        f"✦ В наличии: {len(get_goods())} шт.\n"
        f"✦ Цена: {PRODUCT_PRICE}$"
    )

# ======================================================
# SUPPORT
# ======================================================

@dp.message(F.text == "✦ Support")
async def support(message: types.Message):

    await message.answer(
        f"✦ Support: {SUPPORT}"
    )

# ======================================================
# TOPUP START
# ======================================================

@dp.message(F.text == "✚ Пополнить")
async def topup(message: types.Message, state: FSMContext):

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✖ Отмена")]
        ],
        resize_keyboard=True
    )

    await state.set_state(
        TopUpState.waiting_amount
    )

    await message.answer(
        "💸 Введите сумму пополнения в USD\n\n"
        "Пример: 10",
        reply_markup=kb
    )

# ======================================================
# CANCEL
# ======================================================

@dp.message(F.text == "✖ Отмена")
async def cancel(message: types.Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "✖ Пополнение отменено",
        reply_markup=menu()
    )

# ======================================================
# CREATE INVOICE
# ======================================================

async def create_invoice(amount):

    url = "https://pay.crypt.bot/api/createInvoice"

    headers = {
        "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN
    }

    payload = {
        "asset": "USDT",
        "amount": amount,
        "description": f"{SHOP_NAME} balance"
    }

    connector = aiohttp.TCPConnector(
        ssl=ssl_context
    )

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        async with session.post(
            url,
            json=payload,
            headers=headers
        ) as response:

            data = await response.json()

            return data["result"]

# ======================================================
# CHECK INVOICE
# ======================================================

async def check_invoice(invoice_id):

    url = (
        f"https://pay.crypt.bot/api/getInvoices"
        f"?invoice_ids={invoice_id}"
    )

    headers = {
        "Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN
    }

    connector = aiohttp.TCPConnector(
        ssl=ssl_context
    )

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        async with session.get(
            url,
            headers=headers
        ) as response:

            data = await response.json()

            items = data["result"]["items"]

            if not items:
                return False

            invoice = items[0]

            return invoice["status"] == "paid"

# PROCESS AMOUNT

@dp.message(TopUpState.waiting_amount)
async def process_amount(
    message: types.Message,
    state: FSMContext
):

    try:

        amount = float(message.text)

        if amount <= 0:

            return await message.answer(
                "✖ Сумма должна быть больше 0"
            )

    except:

        return await message.answer(
            "✖ Введите число\n\n"
            "Пример: 10"
        )

    invoice = await create_invoice(amount)

    invoice_id = invoice["invoice_id"]
    pay_url = invoice["pay_url"]

    await state.clear()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💸 Оплатить",
                    url=pay_url
                )
            ],
            [
                InlineKeyboardButton(
                    text="✔ Проверить оплату",
                    callback_data=f"check_{invoice_id}_{amount}"
                )
            ]
        ]
    )

    await message.answer(
        f"✚ Счет создан\n\n"
        f"⌬ Сумма: {amount}$\n"
        f"⌬ Invoice ID: {invoice_id}",
        reply_markup=kb
    )

    await message.answer(
        "🔙 Главное меню",
        reply_markup=menu()
    )

# ======================================================
# CHECK PAYMENT
# ======================================================

@dp.callback_query(F.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):

    data = callback.data.split("_")

    invoice_id = data[1]
    amount = float(data[2])

    paid = await check_invoice(invoice_id)

    if not paid:

        return await callback.answer(
            "✖ Оплата еще не поступила",
            show_alert=True
        )

    ensure_user(callback.from_user.id)

    user_id = str(callback.from_user.id)

    users[user_id]["balance"] += amount

    save_users()

    await callback.message.edit_text(
        f"✔ Оплата подтверждена\n\n"
        f"⌬ +{amount}$\n"
        f"⌬ Баланс: {users[user_id]['balance']}$"
    )

# ======================================================
# BUY MENU
# ======================================================

@dp.message(F.text == "🛒 Купить")
async def buy_menu(message: types.Message):

    ensure_user(message.from_user.id)

    user_id = str(message.from_user.id)

    balance = users[user_id]["balance"]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Купить аккаунт",
                    callback_data="buy_account"
                )
            ]
        ]
    )

    await message.answer(
        f"◆ SELFREG\n\n"
        f"✦ Цена: {PRODUCT_PRICE}$\n"
        f"✦ В наличии: {len(get_goods())}\n"
        f"✦ Баланс: {balance}$",
        reply_markup=kb
    )

# ======================================================
# BUY ACCOUNT (ТОЛЬКО КНОПКА)
# ======================================================

@dp.callback_query(F.data == "buy_account")
async def buy_account(callback: types.CallbackQuery):

    ensure_user(callback.from_user.id)

    user_id = str(callback.from_user.id)

    balance = users[user_id]["balance"]

    if balance < PRODUCT_PRICE:
        return await callback.answer(
            "✖ Недостаточно средств",
            show_alert=True
        )

    goods = get_goods()

    if not goods:
        return await callback.answer(
            "✖ Товар закончился",
            show_alert=True
        )

    file_path = goods[0]

    order_id = str(uuid.uuid4())[:8].upper()

    try:

        users[user_id]["balance"] -= PRODUCT_PRICE
        save_users()

        file = FSInputFile(file_path)

        await bot.send_document(
            chat_id=callback.message.chat.id,
            document=file,
            caption=(
                f"✔ Заказ выдан\n\n"
                f"◆ ORDER: #{order_id}\n"
                f"⌬ Остаток: {users[user_id]['balance']}$\n"
                f"◷ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
        )

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logging.error(f"File delete error: {e}")

        await callback.message.answer(
            f"✔ Покупка завершена\n"
            f"◆ Осталось товаров: {len(get_goods())}"
        )

        await callback.answer("✔ Успешно")

    except Exception as e:

        users[user_id]["balance"] += PRODUCT_PRICE
        save_users()

        await callback.message.answer(
            f"✖ Ошибка выдачи:\n{e}"
        )

# ======================================================
# MAIN
# ======================================================

async def main():

    ensure_goods()

    load_users()

    print("=" * 50)
    print(f"🤖 {SHOP_NAME}")
    print(f"◆ Товаров: {len(get_goods())}")
    print("=" * 50)

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dp.start_polling(bot)

# ======================================================

if __name__ == "__main__":

    asyncio.run(main())