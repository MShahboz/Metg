import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
import logging

# Logging sozlash
logging.basicConfig(level=logging.INFO)

# Bot sozlamalari
BOT_TOKEN = "5351503607:AAEWQX_DVlAhTYvm46cCE7Irx00VMq_HIg0"
BOT_USERNAME = "@MeTgBot"
ADMIN_ID = 1905881970
SUPPORT_USERNAME = "@metgsupbot"

# Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Ma'lumotlar bazasi
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        uzs INTEGER DEFAULT 0,
        card_number TEXT,
        full_name TEXT,
        ref_link TEXT,
        ref_by INTEGER,
        ref_earnings INTEGER DEFAULT 0,
        total_stars_sold INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        usd_rate INTEGER DEFAULT 13000
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS special_refs (
        ref_link TEXT PRIMARY KEY,
        percentage INTEGER,
        user_id INTEGER
    )''')
    c.execute("INSERT OR IGNORE INTO settings (id, usd_rate) VALUES (1, 13000)")
    conn.commit()
    conn.close()

init_db()

# Holatlar
class UserStates(StatesGroup):
    WAITING_STARS_SELL = State()
    WAITING_CARD = State()
    WAITING_NAME = State()
    WAITING_WITHDRAW = State()
    WAITING_TRANSFER_ID = State()
    ADMIN_SET_RATE = State()
    ADMIN_BROADCAST = State()
    ADMIN_MANAGE_USER = State()
    ADMIN_SPECIAL_REF = State()
    ADMIN_ASSIGN_SPECIAL_REF = State()

# Bosh menu
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Stars Sotish", callback_data="sell_stars")],
        [InlineKeyboardButton(text="💸 Balans", callback_data="balance")],
        [InlineKeyboardButton(text="🤝 Referral", callback_data="referral")],
        [InlineKeyboardButton(text="📊 Kurs", callback_data="course")],
        [InlineKeyboardButton(text="📈 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="settings")]
    ])
    return keyboard

# Admin menu
def get_admin_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Kursni O‘zgartirish", callback_data="admin_set_rate")],
        [InlineKeyboardButton(text="📢 Xabar Yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👤 Foydalanuvchi Boshqarish", callback_data="admin_manage_user")],
        [InlineKeyboardButton(text="🔗 Maxsus Referral Link Yaratish", callback_data="admin_special_ref")],
        [InlineKeyboardButton(text="🔗 Maxsus Link Biriktirish", callback_data="admin_assign_special_ref")],
        [InlineKeyboardButton(text="📊 Umumiy Statistika", callback_data="admin_stats")]
    ])
    return keyboard

# Start komandasi
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    ref_by = None
    if len(message.text.split()) > 1:
        ref_link = message.text.split()[1]
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE ref_link=?", (ref_link,))
        ref_user = c.fetchone()
        c.execute("SELECT user_id FROM special_refs WHERE ref_link=?", (ref_link,))
        special_ref = c.fetchone()
        if ref_user and not special_ref:
            ref_by = ref_user[0]
        elif special_ref:
            ref_by = special_ref[0]
        conn.close()

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        ref_link = f"ref_{user_id}"
        c.execute("INSERT INTO users (user_id, ref_link, ref_by) VALUES (?, ?, ?)", (user_id, ref_link, ref_by))
        conn.commit()
    conn.close()

    text = ("🎉 Xush kelibsiz!\n"
            f"Bu {BOT_USERNAME} orqali Stars soting, balansingizni boshqaring va referral orqali daromad oling.\n"
            "_Stars faqat UZSga almashtiriladi. Kurs talab va taklifga qarab o‘zgaradi._")
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())
    if user_id == ADMIN_ID:
        await message.answer("🛠 Admin paneliga xush kelibsiz!", reply_markup=get_admin_menu())

# Stars sotish
@dp.callback_query(lambda c: c.data == "sell_stars")
async def sell_stars(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📥 Qancha Stars sotmoqchisiz? (Minimal 5 Stars)", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(UserStates.WAITING_STARS_SELL)

@dp.message(UserStates.WAITING_STARS_SELL)
async def process_stars_sell(message: types.Message, state: FSMContext):
    try:
        stars = int(message.text)
        if stars < 5:
            await message.answer("❌ Minimal 5 Stars sotishingiz mumkin!")
            return
        user_id = message.from_user.id

        async with aiohttp.ClientSession() as session:
            payload = {
                "chat_id": user_id,
                "amount": stars,
                "currency": "XTR",
                "description": f"{stars} Stars sotish",
                "payload": f"sell_{user_id}_{stars}"
            }
            async with session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink", json=payload) as response:
                payment_data = await response.json()

        if not payment_data.get("ok"):
            await message.answer(f"❌ To‘lov so‘rovida xatolik: {payment_data.get('error_code', 'Noma’lum xato')}")
            return

        payment_url = payment_data.get("result")
        await message.answer(f"💳 {stars} Stars to‘lovi uchun quyidagi link orqali to‘lang:\n{payment_url}\n"
                            "To‘lov tasdiqlangach, balansingizga UZS qo‘shiladi.")
        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting!")

# To‘lov tasdiqlash
@dp.message(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def handle_successful_payment(message: types.Message):
    payment = message.successful_payment
    stars = payment.total_amount
    user_id = message.from_user.id
    payload = payment.invoice_payload

    if not payload.startswith(f"sell_{user_id}_"):
        return

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT usd_rate FROM settings WHERE id=1")
    usd_rate = c.fetchone()[0]
    uzs = stars * 0.01 * usd_rate

    # Referral komissiyasi
    c.execute("SELECT ref_by, ref_link FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    ref_by, ref_link = user
    if ref_by:
        c.execute("SELECT percentage FROM special_refs WHERE ref_link=?", (ref_link,))
        special_ref = c.fetchone()
        percentage = special_ref[0] if special_ref else 1
        ref_earnings = uzs * (percentage / 100)
        c.execute("UPDATE users SET ref_earnings = ref_earnings + ?, uzs = uzs + ? WHERE user_id=?", 
                  (ref_earnings, ref_earnings, ref_by))
        await bot.send_message(ref_by, f"🤝 Sizning referral tizimingiz orqali {ref_earnings} UZS qo‘shildi!")

    # Balansni yangilash
    c.execute("UPDATE users SET uzs = uzs + ?, total_stars_sold = total_stars_sold + ? WHERE user_id=?", 
              (uzs, stars, user_id))
    conn.commit()
    conn.close()
    await message.answer(f"✅ {stars} Stars to‘lovi tasdiqlandi! Balansingizga {uzs} UZS qo‘shildi.")

# Balans
@dp.callback_query(lambda c: c.data == "balance")
async def balance(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT uzs FROM users WHERE user_id=?", (user_id,))
    uzs = c.fetchone()[0]
    conn.close()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Pul Yechish (Telegram ID, min 500 UZS)", callback_data="transfer_id")],
        [InlineKeyboardButton(text="💳 Pul Yechish (Support orqali, min 5000 UZS)", callback_data="withdraw_support")]
    ])
    await callback.message.answer(f"💰 Balansingiz: {uzs} UZS", reply_markup=keyboard)

# Pul yechish (Support orqali)
@dp.callback_query(lambda c: c.data == "withdraw_support")
async def withdraw_support(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT uzs, card_number, full_name FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()

    if user[1] is None or user[2] is None:
        await callback.message.answer("❌ Avval karta ma’lumotlarini kiriting (Sozlamalar bo‘limida)!")
        return
    if user[0] < 5000:
        await callback.message.answer("❌ Minimal yechish miqdori (Support orqali): 5,000 UZS!")
        return

    await callback.message.answer("📤 Qancha UZS yechmoqchisiz? (Minimal 5,000 UZS)")
    await state.set_state(UserStates.WAITING_WITHDRAW)

@dp.message(UserStates.WAITING_WITHDRAW)
async def process_withdraw_support(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 5000:
            await message.answer("❌ Minimal yechish miqdori (Support orqali): 5,000 UZS!")
            return
        user_id = message.from_user.id
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("SELECT uzs, card_number, full_name FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
        if user[0] < amount:
            await message.answer("❌ Balansingiz yetarli emas!")
            conn.close()
            return
        c.execute("UPDATE users SET uzs = uzs - ? WHERE user_id=?", (amount, user_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ {amount} UZS yechish so‘rovi qabul qilindi! To‘lov tez orada amalga oshiriladi.")
        await bot.send_message(ADMIN_ID, f"🔔 Foydalanuvchi {user_id} {amount} UZSni {user[1]} kartasiga yechmoqchi. "
                                       f"To‘lovni {SUPPORT_USERNAME} orqali aktivlashtiring.")
        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting!")

# Pul o‘tkazish (Telegram ID)
@dp.callback_query(lambda c: c.data == "transfer_id")
async def transfer_id(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT uzs FROM users WHERE user_id=?", (user_id,))
    uzs = c.fetchone()[0]
    conn.close()

    if uzs < 500:
        await callback.message.answer("❌ Minimal o‘tkazma miqdori (Telegram ID): 500 UZS!")
        return
    await callback.message.answer("📤 Pul o‘tkazmoqchi bo‘lgan Telegram ID va miqdorni kiriting (masalan: `123456789 500`):")
    await state.set_state(UserStates.WAITING_TRANSFER_ID)

@dp.message(UserStates.WAITING_TRANSFER_ID)
async def process_transfer_id(message: types.Message, state: FSMContext):
    try:
        target_id, amount = map(int, message.text.split())
        if amount < 500:
            await message.answer("❌ Minimal o‘tkazma miqdori (Telegram ID): 500 UZS!")
            return
        user_id = message.from_user.id
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("SELECT uzs FROM users WHERE user_id=?", (user_id,))
        sender_uzs = c.fetchone()[0]
        c.execute("SELECT user_id FROM users WHERE user_id=?", (target_id,))
        target_user = c.fetchone()
        if not target_user:
            await message.answer("❌ Bunday Telegram ID mavjud emas!")
            conn.close()
            return
        if sender_uzs < amount:
            await message.answer("❌ Balansingiz yetarli emas!")
            conn.close()
            return
        c.execute("UPDATE users SET uzs = uzs - ? WHERE user_id=?", (amount, user_id))
        c.execute("UPDATE users SET uzs = uzs + ? WHERE user_id=?", (amount, target_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ {amount} UZS {target_id} ID ga o‘tkazildi! To‘lov tez orada amalga oshiriladi.")
        await bot.send_message(target_id, f"💸 Sizning balansingizga {amount} UZS o‘tkazildi!")
        await bot.send_message(ADMIN_ID, f"🔔 Foydalanuvchi {user_id} {amount} UZSni {target_id} ID ga o‘tkazdi. "
                                       f"To‘lovni {SUPPORT_USERNAME} orqali aktivlashtiring.")
        await state.clear()
    except:
        await message.answer("❌ Noto‘g‘ri format! Masalan: `123456789 500`")

# Referral
@dp.callback_query(lambda c: c.data == "referral")
async def referral(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT ref_link, ref_earnings FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    c.execute("SELECT COUNT(*) FROM users WHERE ref_by=?", (user_id,))
    ref_count = c.fetchone()[0]
    conn.close()

    ref_link = f"https://t.me/{BOT_USERNAME}?start={user[0]}"
    text = (f"🤝 Referral tizimi:\n"
            f"Sizning linkingiz: {ref_link}\n"
            f"Taklif qilganlar: {ref_count} kishi\n"
            f"Referral daromadingiz: {user[1]} UZS\n\n"
            f"Katta kanal yoki reklama uchun maxsus referral link olish uchun {SUPPORT_USERNAME} ga yozing.")
    await callback.message.answer(text)

# Statistika
@dp.callback_query(lambda c: c.data == "stats")
async def stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT ref_earnings, total_stars_sold FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    c.execute("SELECT COUNT(*), SUM(total_stars_sold), SUM(uzs) FROM users WHERE ref_by=?", (user_id,))
    ref_count, ref_stars, ref_uzs = c.fetchone()
    conn.close()

    text = (f"📈 Sizning statistikangiz:\n"
            f"Referral daromadingiz: {user[0]} UZS\n"
            f"Siz sotgan Stars: {user[1]}\n"
            f"Taklif qilinganlar: {ref_count} kishi\n"
            f"Ular sotgan Stars: {ref_stars or 0}\n"
            f"Ularning UZS daromadi: {ref_uzs or 0} UZS")
    await callback.message.answer(text)

# Kurs
@dp.callback_query(lambda c: c.data == "course")
async def course(callback: types.CallbackQuery):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT usd_rate FROM settings WHERE id=1")
    usd_rate = c.fetchone()[0]
    conn.close()
    stars_uzs = 100 * 0.01 * usd_rate
    text = (f"📊 Joriy kurs:\n"
            f"1$ = {usd_rate} UZS\n"
            f"100 Stars = {stars_uzs} UZS\n\n"
            f"_Stars faqat UZSga almashtiriladi. Kurs talab va taklifga qarab o‘zgaradi._")
    await callback.message.answer(text, parse_mode="Markdown")

# Sozlamalar
@dp.callback_query(lambda c: c.data == "settings")
async def settings(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Karta Ma’lumotlari", callback_data="set_card")],
        [InlineKeyboardButton(text="📞 Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ])
    await callback.message.answer("⚙️ Sozlamalar bo‘limi:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "set_card")
async def set_card(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("💳 Karta raqamingizni kiriting (Humo/Uzcard):")
    await state.set_state(UserStates.WAITING_CARD)

@dp.message(UserStates.WAITING_CARD)
async def process_card(message: types.Message, state: FSMContext):
    card_number = message.text.replace(" ", "")
    if not card_number.isdigit() or len(card_number) != 16:
        await message.answer("❌ Noto‘g‘ri karta raqami! 16 raqamdan iborat bo‘lishi kerak.")
        return
    await state.update_data(card_number=card_number)
    await message.answer("📋 Ism va familyangizni kiriting:")
    await state.set_state(UserStates.WAITING_NAME)

@dp.message(UserStates.WAITING_NAME)
async def process_name(message: types.Message, state: FSMContext):
    full_name = message.text
    data = await state.get_data()
    card_number = data["card_number"]
    user_id = message.from_user.id
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET card_number=?, full_name=? WHERE user_id=?", (card_number, full_name, user_id))
    conn.commit()
    conn.close()
    await message.answer("✅ Karta ma’lumotlari saqlandi!")
    await state.clear()

# Admin: Kurs o‘zgartirish
@dp.callback_query(lambda c: c.data == "admin_set_rate")
async def admin_set_rate(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("❌ Siz admin emassiz!")
        return
    await callback.message.answer("📈 Yangi USD/UZS kursini kiriting (masalan, 13000):")
    await state.set_state(UserStates.ADMIN_SET_RATE)

@dp.message(UserStates.ADMIN_SET_RATE)
async def process_set_rate(message: types.Message, state: FSMContext):
    try:
        rate = int(message.text)
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("UPDATE settings SET usd_rate=? WHERE id=1", (rate,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Kurs yangilandi: 1$ = {rate} UZS")
        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting!")

# Admin: Xabar yuborish
@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("❌ Siz admin emassiz!")
        return
    await callback.message.answer("📢 Hamma foydalanuvchilarga yuboriladigan xabarni kiriting:")
    await state.set_state(UserStates.ADMIN_BROADCAST)

@dp.message(UserStates.ADMIN_BROADCAST)
async def process_broadcast(message: types.Message, state: FSMContext):
    text = message.text
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    for user in users:
        try:
            await bot.send_message(user[0], text)
        except:
            pass
    await message.answer("✅ Xabar hamma foydalanuvchilarga yuborildi!")
    await state.clear()

# Admin: Foydalanuvchi boshqarish
@dp.callback_query(lambda c: c.data == "admin_manage_user")
async def admin_manage_user(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("❌ Siz admin emassiz!")
        return
    await callback.message.answer("👤 Foydalanuvchi ID va o‘zgartirishni kiriting (masalan: `123456789 +100 uzs`):")
    await state.set_state(UserStates.ADMIN_MANAGE_USER)

@dp.message(UserStates.ADMIN_MANAGE_USER)
async def process_manage_user(message: types.Message, state: FSMContext):
    try:
        user_id, action, amount, currency = message.text.split()
        user_id, amount = int(user_id), int(amount)
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        if action == "+":
            c.execute(f"UPDATE users SET {currency} = {currency} + ? WHERE user_id=?", (amount, user_id))
        elif action == "-":
            c.execute(f"UPDATE users SET {currency} = {currency} - ? WHERE user_id=?", (amount, user_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Foydalanuvchi {user_id} uchun {currency} {action}{amount} qilindi!")
        await state.clear()
    except:
        await message.answer("❌ Noto‘g‘ri format! Masalan: `123456789 +100 uzs`")

# Admin: Maxsus referral link yaratish
@dp.callback_query(lambda c: c.data == "admin_special_ref")
async def admin_special_ref(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("❌ Siz admin emassiz!")
        return
    await callback.message.answer("🔗 Maxsus referral link va foizni kiriting (masalan: `ref_special_123 5`):")
    await state.set_state(UserStates.ADMIN_SPECIAL_REF)

@dp.message(UserStates.ADMIN_SPECIAL_REF)
async def process_special_ref(message: types.Message, state: FSMContext):
    try:
        ref_link, percentage = message.text.split()
        percentage = int(percentage)
        if percentage < 3 or percentage > 5:
            await message.answer("❌ Foiz 3-5 oralig‘ida bo‘lishi kerak!")
            return
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO special_refs (ref_link, percentage, user_id) VALUES (?, ?, NULL)", (ref_link, percentage))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Maxsus referral link ({ref_link}) {percentage}% bilan yaratildi!")
        await state.clear()
    except:
        await message.answer("❌ Noto‘g‘ri format! Masalan: `ref_special_123 5`")

# Admin: Maxsus link biriktirish
@dp.callback_query(lambda c: c.data == "admin_assign_special_ref")
async def admin_assign_special_ref(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("❌ Siz admin emassiz!")
        return
    await callback.message.answer("🔗 Foydalanuvchi ID va maxsus referral linkni kiriting (masalan: `123456789 ref_special_123`):")
    await state.set_state(UserStates.ADMIN_ASSIGN_SPECIAL_REF)

@dp.message(UserStates.ADMIN_ASSIGN_SPECIAL_REF)
async def process_assign_special_ref(message: types.Message, state: FSMContext):
    try:
        user_id, ref_link = message.text.split()
        user_id = int(user_id)
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("SELECT ref_link FROM special_refs WHERE ref_link=?", (ref_link,))
        if not c.fetchone():
            await message.answer("❌ Bunday maxsus referral link mavjud emas!")
            conn.close()
            return
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not c.fetchone():
            await message.answer("❌ Bunday foydalanuvchi ID mavjud emas!")
            conn.close()
            return
        c.execute("UPDATE special_refs SET user_id=? WHERE ref_link=?", (user_id, ref_link))
        c.execute("UPDATE users SET ref_link=? WHERE user_id=?", (ref_link, user_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Foydalanuvchi {user_id} ga {ref_link} maxsus linki biriktirildi!")
        await bot.send_message(user_id, f"🔗 Sizga maxsus referral link biriktirildi: https://t.me/{BOT_USERNAME}?start={ref_link}")
        await state.clear()
    except:
        await message.answer("❌ Noto‘g‘ri format! Masalan: `123456789 ref_special_123`")

# Admin: Umumiy statistika
@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.message.answer("❌ Siz admin emassiz!")
        return
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(total_stars_sold), SUM(uzs) FROM users")
    total_users, total_stars, total_uzs = c.fetchone()
    c.execute("SELECT COUNT(*) FROM users WHERE ref_by IS NOT NULL")
    total_referred = c.fetchone()[0]
    c.execute("SELECT ref_link, percentage, user_id FROM special_refs")
    special_refs = c.fetchall()
    conn.close()

    special_refs_text = "\n".join([f"Link: {ref[0]}, Foiz: {ref[1]}%, Foydalanuvchi: {ref[2] or 'Biriktirilmagan'}" for ref in special_refs])
    text = (f"📊 Umumiy statistika:\n"
            f"Foydalanuvchilar soni: {total_users}\n"
            f"Umumiy almashtirilgan Stars: {total_stars or 0}\n"
            f"Umumiy UZS: {total_uzs or 0}\n"
            f"Taklif qilingan foydalanuvchilar: {total_referred}\n"
            f"Maxsus referral linklar:\n{special_refs_text if special_refs_text else 'Hech qanday maxsus link yo‘q'}")
    await callback.message.answer(text)

# Botni ishga tushirish
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​​