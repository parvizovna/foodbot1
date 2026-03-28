import asyncio
import sqlite3
from datetime import datetime, time, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8099040023:AAEgYrl3_d8SLdfOUI02uHeJnDSo3ahrSjw"
OWNER_ID = 1818964  # <-- твой Telegram user_id

NIGHT_START = time(23, 0)
NIGHT_END = time(8, 0)
# =============================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ---------- БАЗА ДАННЫХ ----------

conn = sqlite3.connect("food_log.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS food_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")
conn.commit()

def save_food_log(text: str):
    cursor.execute(
        "INSERT INTO food_log (text, created_at) VALUES (?, ?)",
        (text, datetime.now().isoformat())
    )
    conn.commit()

# ---------- КНОПКИ ----------

def remind_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏰ Напомнить через 3 часа", callback_data="remind_3"),
            InlineKeyboardButton(text="⏰ Напомнить через 4 часа", callback_data="remind_4"),
        ],
        [
            InlineKeyboardButton(text="❌ Не напоминать", callback_data="no_remind")
        ]
    ])

def after_remind_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏰ Напомнить через час", callback_data="remind_1")
        ],
        [
            InlineKeyboardButton(text="❌ Не напоминать", callback_data="no_remind")
        ]
    ])

# ---------- НОЧНОЙ РЕЖИМ ----------

def apply_night_mode(target_time: datetime) -> datetime:
    now_time = target_time.time()

    # если попали в ночной диапазон — перенос на 08:00
    if NIGHT_START <= now_time or now_time < NIGHT_END:
        next_morning = target_time
        if now_time >= NIGHT_START:
            next_morning += timedelta(days=1)

        return next_morning.replace(
            hour=NIGHT_END.hour,
            minute=0,
            second=0,
            microsecond=0
        )

    return target_time

async def send_reminder(chat_id: int, delay_seconds: int):
    target_time = datetime.now() + timedelta(seconds=delay_seconds)
    target_time = apply_night_mode(target_time)

    sleep_seconds = (target_time - datetime.now()).total_seconds()
    if sleep_seconds > 0:
        await asyncio.sleep(sleep_seconds)

    await bot.send_message(
        chat_id,
        "🍽 Напоминание поесть",
        reply_markup=after_remind_keyboard()
    )

# ---------- ХЭНДЛЕРЫ ----------

@dp.message(CommandStart())
async def start(message: Message):
    if message.from_user.id != OWNER_ID:
        return

    await message.answer(
        "📔 *Дневник питания*\n\n"
        "Пиши, что ел(а) — я сохраню и напомню поесть.\n"
        "🌙 Ночной режим: 23:00–08:00",
        parse_mode="Markdown"
    )

@dp.message()
async def handle_message(message: Message):
    if message.from_user.id != OWNER_ID:
        return

    save_food_log(message.text)

    await message.answer(
        "Когда напомнить поесть?",
        reply_markup=remind_keyboard()
    )

@dp.callback_query(F.data.startswith("remind_"))
async def handle_remind(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    hours = int(callback.data.split("_")[1])
    seconds = hours * 3600

    asyncio.create_task(
        send_reminder(callback.message.chat.id, seconds)
    )

    await callback.answer()
    await callback.message.edit_text(
        f"✅ Хорошо, напомню через {hours} ч.\n"
        f"🌙 Если попадёт в ночь — перенесу на утро"
    )

@dp.callback_query(F.data == "no_remind")
async def handle_no_remind(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return

    await callback.answer("Ок 👍")
    await callback.message.edit_text("🚫 Напоминание отменено")

# ---------- ЗАПУСК ----------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())