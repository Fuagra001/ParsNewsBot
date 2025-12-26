import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import traceback
import requests
from bs4 import BeautifulSoup

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN
from summarizer import make_summary

bot = Bot(token="7922022266:AAF_HcGye4W4taFZ2AMuekAd6jdTWNFhbmU")
dp = Dispatcher()

CHANNELS_FILE = Path("channels.json")

# ---------------- Работа с файлами каналов ----------------
def load_channels():
    if CHANNELS_FILE.exists():
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_channels(channels):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)

# ---------------- Кнопки для каналов (Inline) ----------------
def build_channels_keyboard(channels):
    keyboard_buttons = []
    for ch in channels:
        row = [
            types.InlineKeyboardButton(text=f"📄 {ch}", callback_data=f"use_{ch}"),
            types.InlineKeyboardButton(text="❌", callback_data=f"del_{ch}")
        ]
        keyboard_buttons.append(row)
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

# ---------------- ReplyKeyboard с кнопкой "Отчет" ----------------
report_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[[types.KeyboardButton(text="📊 Отчет")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

# ---------------- Parser для последних 1 дня ----------------
def parse_channel(url: str, days: int = 1):
    if "/s/" not in url:
        url = url.replace("t.me/", "t.me/s/")

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    posts = soup.find_all("div", class_="tgme_widget_message")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    messages = []
    first_date = None
    last_date = None

    for post in posts:
        time_tag = post.find("time")
        if not time_tag or "datetime" not in time_tag.attrs:
            continue

        post_date = datetime.fromisoformat(time_tag["datetime"])
        if post_date.tzinfo is None:
            post_date = post_date.replace(tzinfo=timezone.utc)

        if post_date < since:
            continue

        text_tag = post.find("div", class_="tgme_widget_message_text")
        if text_tag:
            messages.append(text_tag.get_text(" ", strip=True))
            if not first_date or post_date < first_date:
                first_date = post_date
            if not last_date or post_date > last_date:
                last_date = post_date

    first_str = first_date.strftime("%Y-%m-%d") if first_date else "N/A"
    last_str = last_date.strftime("%Y-%m-%d") if last_date else "N/A"

    return messages, first_str, last_str

# ---------------- /start ----------------
@dp.message(Command(commands=["start"]))
async def start(message: types.Message):
    channels = load_channels()
    text = ("👋 Привет! Пришли ссылку на Telegram-канал для отчёта за последний день.\n"
            "Или выбери канал из списка ниже.")

    if channels:
        inline_kb = build_channels_keyboard(channels)
        await message.answer(text, reply_markup=inline_kb)
    else:
        await message.answer(text)

    # Кнопка "Отчет" всегда видна под полем ввода
    await message.answer("Нажми 📊 Отчет для формирования отчета", reply_markup=report_keyboard)

# ---------------- Обработка сообщений ----------------
@dp.message()
async def handle_message(message: types.Message):
    text = message.text.strip()

    # Нажата кнопка "Отчет"
    if text == "📊 Отчет":
        channels = load_channels()
        if not channels:
            await message.answer("❗ Список каналов пуст. Добавьте хотя бы один канал.")
            return
        await message.answer("Выберите канал для формирования отчета:",
                             reply_markup=build_channels_keyboard(channels))
        return

    # Пришла ссылка на канал
    if "t.me/" in text:
        channels = load_channels()
        if text not in channels:
            channels.append(text)
            save_channels(channels)
            await message.answer(f"✅ Канал добавлен в список.")
        await generate_report(message, text)
        return

    # Любое другое сообщение
    await message.answer("❗ Пришли ссылку на Telegram-канал или нажми 📊 Отчет.")

# ---------------- Генерация отчёта ----------------
async def generate_report(message, channel_url: str):
    await message.answer("⏳ Собираю посты за последний день и готовлю отчёт...")

    try:
        msgs, first_date, last_date = parse_channel(channel_url)
        if not msgs:
            await message.answer("❗ Не найдено постов за последний день")
            return

        summary = make_summary(channel_url, msgs, (first_date, last_date))
        await message.answer(summary)

    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке канала:\n{type(e).__name__}: {str(e)}")
        traceback.print_exc()

# ---------------- Кнопки выбора / удаления ----------------
@dp.callback_query(lambda c: c.data.startswith("use_"))
async def use_channel(callback: types.CallbackQuery):
    channel_url = callback.data.replace("use_", "")
    await callback.message.answer(f"Выбран канал: {channel_url}")
    await generate_report(callback.message, channel_url)

@dp.callback_query(lambda c: c.data.startswith("del_"))
async def delete_channel(callback: types.CallbackQuery):
    channel_url = callback.data.replace("del_", "")
    channels = load_channels()
    if channel_url in channels:
        channels.remove(channel_url)
        save_channels(channels)
        await callback.message.answer(f"❌ Канал удалён: {channel_url}")

    channels = load_channels()
    if channels:
        await callback.message.answer("Обновлённый список каналов:", reply_markup=build_channels_keyboard(channels))
    else:
        await callback.message.answer("Список каналов пуст.")

# ---------------- Запуск бота ----------------
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
