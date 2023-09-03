# Importing necessary libraries
import logging
import sqlite3
from decouple import config
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime


# Fetching necessary configurations from environment variables
TOKEN = config('TELEGRAM_TOKEN')
ASTAH_CHAT_ID = config('ASTAH_CHAT_ID')

# Setting up logging configurations
logging.basicConfig(level=logging.INFO)

# Initializing aiogram Bot and Dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Setting up AsyncIO scheduler for scheduled tasks
scheduler = AsyncIOScheduler()

# Initialize the SQLite database
conn = sqlite3.connect('astah_bot.db')
cursor = conn.cursor()

# Create user_goals table if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS user_goals (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0
)''')

# Check if the column current_pullups exists
cursor.execute("PRAGMA table_info(user_goals)")
columns = [column[1] for column in cursor.fetchall()]
if "current_pullups" not in columns:
    cursor.execute('''ALTER TABLE user_goals ADD COLUMN current_pullups INTEGER DEFAULT 5''')


conn.commit()

# Functions to interact with the database

def get_current_pullups(user_id):
    cursor.execute("SELECT current_pullups FROM user_goals WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 5

def increase_pullups_goal(user_id, increment=1): # Допустим, увеличиваем на 1
    current_pullups = get_current_pullups(user_id)
    new_goal = current_pullups + increment
    cursor.execute("UPDATE user_goals SET current_pullups = ? WHERE user_id = ?", (new_goal, user_id))
    conn.commit()

def add_points(user_id, points):
    cursor.execute("INSERT OR IGNORE INTO user_goals (user_id, points) VALUES (?, ?)", (user_id, points))
    cursor.execute("UPDATE user_goals SET points = points + ? WHERE user_id = ?", (points, user_id))
    conn.commit()

def get_points(user_id):
    cursor.execute("SELECT points FROM user_goals WHERE user_id = ?", (user_id,))
    points = cursor.fetchone()
    return points[0] if points else 0

# Async functions for bot notifications
async def wake_up():
    await bot.send_message(ASTAH_CHAT_ID, "Астах, пора просыпаться! ☀️")

async def training_reminder():
    await bot.send_message(ASTAH_CHAT_ID, "Астах, не забудь про тренировку по футболу сегодня в 16:20! ⚽️")

async def morning_stretch():
    await bot.send_message(ASTAH_CHAT_ID, "Не забудь сделать утреннюю разминку, это поможет начать день правильно! 💪")

# Setting up scheduler jobs
def setup_scheduler_jobs():
    scheduler.add_job(wake_up, CronTrigger(hour=9, minute=0))
    scheduler.add_job(training_reminder, CronTrigger(day_of_week='tue,thu,sat', hour=16, minute=20))
    scheduler.add_job(morning_stretch, CronTrigger(hour=9, minute=20))

# Setting up keyboards for bot interactions
menu_kb = ReplyKeyboardMarkup(resize_keyboard=True)
menu_btn = KeyboardButton("Личный Кабинет")
goals_btn = KeyboardButton("Мои цели")
menu_kb.row(menu_btn, goals_btn)

# Bot message handlers

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет, Астах! Я твой личный бот-помощник.", reply_markup=menu_kb)

@dp.message_handler(lambda message: message.text == 'Личный Кабинет')
async def personal_account(message: types.Message):
    user_id = message.from_user.id
    points = get_points(user_id)

    # Получите текущую дату и время
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Измените ответное сообщение
    await message.answer(f"У тебя {points} баллов!\nдата и время: {current_datetime}", reply_markup=menu_kb)


@dp.message_handler(lambda message: message.text == 'Мои цели')
async def show_goals(message: types.Message):
    goals_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    pushups_btn = KeyboardButton("Отжимания 10")
    pullups_btn = KeyboardButton("Подтягивания 5")  # Новая кнопка
    back_btn = KeyboardButton("Назад")
    goals_kb.row(pushups_btn, pullups_btn, back_btn)  # Добавьте новую кнопку в ряд
    await message.answer("Выбери цель:", reply_markup=goals_kb)


@dp.message_handler(lambda message: message.text.startswith('Подтягивания'))
async def pullups_goal(message: types.Message):
    user_id = message.from_user.id
    current_pullups = get_current_pullups(user_id)

    pullups_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    done_btn = KeyboardButton("ГОТОВО")
    next_time_btn = KeyboardButton("В СЛЕДУЮЩИЙ РАЗ")
    back_btn = KeyboardButton("Назад")
    pullups_kb.row(done_btn, next_time_btn)
    pullups_kb.row(back_btn)

    await message.answer(
        f'{current_pullups} Чистых подтягиваний - {current_pullups} баллов (Папа должен проверить и подтвердить!)',
        reply_markup=pullups_kb)

@dp.message_handler(lambda message: message.text == 'ГОТОВО' and 'Подтягивания' in message.reply_to_message.text)
async def pullups_done(message: types.Message):
    user_id = message.from_user.id
    current_pullups = get_current_pullups(user_id)

    add_points(user_id, current_pullups)
    increase_pullups_goal(user_id)

    await message.answer(f'Поздравляю, ты сделал это и заработал {current_pullups} баллов! 🌟', reply_markup=menu_kb)


@dp.message_handler(lambda message: message.text == 'ГОТОВО')
async def done(message: types.Message):
    user_id = message.from_user.id
    current_pushups = get_current_pushups(user_id)

    add_points(user_id, current_pushups)
    increase_pushups_goal(user_id)

    await message.answer(f'Поздравляю, ты сделал это и заработал {current_pushups} баллов! 🌟', reply_markup=menu_kb)

@dp.message_handler(lambda message: message.text == 'В СЛЕДУЮЩИЙ РАЗ')
async def next_time(message: types.Message):
    await message.answer('Ничего, в следующий раз получится! 👍', reply_markup=menu_kb)

@dp.message_handler(lambda message: message.text == 'Назад')
async def back(message: types.Message):
    await message.answer('Чем могу помочь?', reply_markup=menu_kb)

# Main execution: setting up scheduled jobs and starting bot polling
if __name__ == '__main__':
    setup_scheduler_jobs()
    scheduler.start()
    try:
        executor.start_polling(dp)
    finally:
        conn.close()  # Close SQLite connection when bot stops
