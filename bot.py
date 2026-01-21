import asyncio
import sqlite3
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

BOT_TOKEN = "8141299447:AAExxanoFA80m65tyyqBKN4YDAY7lJmuffg"
SUPER_ADMIN_ID = 8394063467

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# ================= DATABASE =================
db = sqlite3.connect("database.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT,
    phone TEXT,
    complaint TEXT,
    created_at TEXT
)
""")
db.commit()

def get_admin_ids():
    cursor.execute("SELECT telegram_id FROM admins")
    return [row[0] for row in cursor.fetchall()]

def add_admin(tg_id: int):
    try:
        cursor.execute("INSERT INTO admins (telegram_id) VALUES (?)", (tg_id,))
        db.commit()
    except sqlite3.IntegrityError:
        pass

def save_complaint(full_name, phone, complaint):
    cursor.execute(
        "INSERT INTO complaints VALUES (NULL,?,?,?,?)",
        (full_name, phone, complaint, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    db.commit()

# ================= FSM =================
class ComplaintStates(StatesGroup):
    full_name = State()
    phone = State()
    complaint = State()

PHONE_REGEX = r"^\+998\d{9}$"

# ================= COMMANDS =================
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📝 <b>Murojaat yuborish</b>\n\n"
        "Iltimos, F.I.Sh (Ism Familiya) kiriting:\n\n"
        "❌ Bekor qilish: /cancel"
    )
    await state.set_state(ComplaintStates.full_name)

@dp.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi.")

# ================= FSM HANDLERS =================
@dp.message(ComplaintStates.full_name)
async def get_full_name(message: types.Message, state: FSMContext):
    if message.text.startswith("/"):
        return
    await state.update_data(full_name=message.text.strip())
    await message.answer("📞 Telefon raqamingizni kiriting:\n(+998xxxxxxxxx)")
    await state.set_state(ComplaintStates.phone)

@dp.message(ComplaintStates.phone)
async def get_phone(message: types.Message, state: FSMContext):
    if message.text.startswith("/"):
        return

    if not re.match(PHONE_REGEX, message.text):
        await message.answer(
            "❌ Telefon raqam noto‘g‘ri formatda!\n"
            "To‘g‘ri format: <b>+998901234567</b>"
        )
        return

    await state.update_data(phone=message.text)
    await message.answer("📝 Shikoyatingiz matnini kiriting:")
    await state.set_state(ComplaintStates.complaint)

@dp.message(ComplaintStates.complaint)
async def get_complaint(message: types.Message, state: FSMContext):
    if message.text.startswith("/"):
        return

    data = await state.get_data()
    full_name = data["full_name"]
    phone = data["phone"]
    complaint = message.text

    save_complaint(full_name, phone, complaint)

    receivers = set(get_admin_ids())
    receivers.add(SUPER_ADMIN_ID)

    notify_text = (
        "📨 <b>Yangi murojaat</b>\n\n"
        f"👤 <b>F.I.Sh:</b> {full_name}\n"
        f"☎️ <b>Telefon:</b> {phone}\n"
        f"📝 <b>Shikoyat:</b>\n{complaint}"
    )

    for admin_id in receivers:
        try:
            await bot.send_message(admin_id, notify_text)
        except:
            pass

    await message.answer("✅ Murojaatingiz qabul qilindi. Rahmat!")
    await state.clear()

# ================= ADMIN =================
@dp.message(Command("admin"))
async def admin_handler(message: types.Message, state: FSMContext):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    await state.clear()
    await message.answer("Admin Telegram ID yuboring:")

@dp.message(lambda m: m.from_user.id == SUPER_ADMIN_ID and m.text.isdigit())
async def add_admin_handler(message: types.Message):
    add_admin(int(message.text))
    await message.answer("✅ Admin qo‘shildi")

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
