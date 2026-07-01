# main.py
import asyncio
import logging
import json
import os
import hmac
import hashlib
import random
import math
from datetime import datetime, timedelta
from urllib.parse import unquote
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ================= НАСТРОЙКИ И КОНФИГУРАЦИЯ =================
BOT_TOKEN = "8845347316:AAH8netvUJhRxR8ZuAuLAPTl1Cm7v2kSRWs"
ADMIN_ID = 7056081840
WEB_PORT = 8080
WEB_URL = "https://enjoyably-food-sister.ngrok-free.dev"
DB_NAME = "empire_life.db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальное состояние для защиты от спама (Rate Limit)
ANTI_SPAM = {}  # user_id -> timestamp
GLOBAL_EVENT = {"name": "Обычные дни", "multiplier": 1.0, "ends_at": None}

# ================= СТРУКТУРИРОВАННЫЕ ИГРОВЫЕ ДАННЫЕ =================
JOBS = {
    1: {"name": "Дворник", "salary": 15, "xp": 5, "req_lvl": 1, "chance": 10},
    2: {"name": "Курьер", "salary": 35, "xp": 8, "req_lvl": 2, "chance": 12},
    3: {"name": "Промоутер", "salary": 50, "xp": 12, "req_lvl": 3, "chance": 15},
    4: {"name": "Официант", "salary": 80, "xp": 15, "req_lvl": 4, "chance": 15},
    5: {"name": "Таксист", "salary": 130, "xp": 20, "req_lvl": 5, "chance": 18},
    6: {"name": "Бариста", "salary": 180, "xp": 25, "req_lvl": 6, "chance": 20},
    7: {"name": "Полицейский", "salary": 260, "xp": 35, "req_lvl": 8, "chance": 22},
    8: {"name": "Врач", "salary": 400, "xp": 50, "req_lvl": 10, "chance": 25},
    9: {"name": "Программист Джуниор", "salary": 650, "xp": 70, "req_lvl": 12, "chance": 25},
    10: {"name": "Программист Сеньор", "salary": 1200, "xp": 120, "req_lvl": 15, "chance": 30},
    11: {"name": "Маркетолог", "salary": 1800, "xp": 180, "req_lvl": 18, "chance": 30},
    12: {"name": "Адвокат", "salary": 3000, "xp": 250, "req_lvl": 22, "chance": 35},
    13: {"name": "Директор Банка", "salary": 6500, "xp": 400, "req_lvl": 26, "chance": 40},
    14: {"name": "Министр экономики", "salary": 15000, "xp": 700, "req_lvl": 32, "chance": 45},
    15: {"name": "Миллиардер", "salary": 50000, "xp": 1500, "req_lvl": 40, "chance": 50}
}

BUSINESSES = {
    1: {"type": "coffee", "name": "Кофейня", "cost": 1500, "income": 45},
    2: {"type": "burger", "name": "Бургерная", "cost": 4000, "income": 130},
    3: {"type": "kiosk", "name": "Торговый киоск", "cost": 9000, "income": 310},
    4: {"type": "barbershop", "name": "Барбершоп", "cost": 18000, "income": 650},
    5: {"type": "pharmacy", "name": "Аптека", "cost": 35000, "income": 1400},
    6: {"type": "gas", "name": "АЗС", "cost": 70000, "income": 3000},
    7: {"type": "gym", "name": "Фитнес-клуб", "cost": 120000, "income": 5400},
    8: {"type": "farm", "name": "Эко-ферма", "cost": 250000, "income": 12000},
    9: {"type": "restaurant", "name": "Ресторан", "cost": 500000, "income": 26000},
    10: {"type": "showroom", "name": "Автосалон", "cost": 1000000, "income": 55000},
    11: {"type": "hotel", "name": "Отель", "cost": 2200000, "income": 125000},
    12: {"type": "factory", "name": "Завод электроники", "cost": 5000000, "income": 300000},
    13: {"type": "mall", "name": "Торговый Центр", "cost": 12000000, "income": 750000},
    14: {"type": "it_company", "name": "IT-Корпорация", "cost": 30000000, "income": 2000000},
    15: {"type": "oil", "name": "Нефтяная вышка", "cost": 75000000, "income": 5500000},
    16: {"type": "shipping", "name": "Логистический порт", "cost": 150000000, "income": 12000000},
    17: {"type": "bank", "name": "Федеральный Банк", "cost": 400000000, "income": 35000000},
    18: {"type": "airline", "name": "Авиакомпания", "cost": 1000000000, "income": 95000000},
    19: {"type": "space", "name": "Космическое агентство", "cost": 3000000000, "income": 320000000},
    20: {"type": "empire", "name": "Транснациональная Империя", "cost": 10000000000, "income": 1200000000}
}

HOUSES = {
    1: {"name": "Место в хостеле", "cost": 500, "bonus_inc": 5},
    2: {"name": "Комната в коммуналке", "cost": 2500, "bonus_inc": 20},
    3: {"name": "Однокомнатная квартира", "cost": 12000, "bonus_inc": 110},
    4: {"name": "Двухкомнатная квартира", "cost": 35000, "bonus_inc": 340},
    5: {"name": "Таунхаус", "cost": 90000, "bonus_inc": 950},
    6: {"name": "Семейный дом", "cost": 250000, "bonus_inc": 2800},
    7: {"name": "Загородный особняк", "cost": 800000, "bonus_inc": 9500},
    8: {"name": "Элитная вилла", "cost": 3000000, "bonus_inc": 38000},
    9: {"name": "Средневековый замок", "cost": 15000000, "bonus_inc": 210000},
    10: {"name": "Тропический остров", "cost": 100000000, "bonus_inc": 1500000}
}

CARS = {
    1: {"name": "Самокат", "cost": 100, "xp_bonus": 1},
    2: {"name": "Велосипед", "cost": 300, "xp_bonus": 2},
    3: {"name": "Старый Скутер", "cost": 900, "xp_bonus": 3},
    4: {"name": "Lada Granta", "cost": 4000, "xp_bonus": 5},
    5: {"name": "Hyundai Solaris", "cost": 9000, "xp_bonus": 8},
    6: {"name": "Toyota Camry", "cost": 22000, "xp_bonus": 15},
    7: {"name": "Skoda Octavia", "cost": 30000, "xp_bonus": 20},
    8: {"name": "BMW 3-Series", "cost": 55000, "xp_bonus": 35},
    9: {"name": "Mercedes C-Class", "cost": 65000, "xp_bonus": 40},
    10: {"name": "Audi A6", "cost": 85000, "xp_bonus": 55},
    11: {"name": "Tesla Model 3", "cost": 110000, "xp_bonus": 75},
    12: {"name": "Porsche Cayenne", "cost": 160000, "xp_bonus": 110},
    13: {"name": "BMW M5", "cost": 210000, "xp_bonus": 150},
    14: {"name": "Mercedes E63 AMG", "cost": 240000, "xp_bonus": 170},
    15: {"name": "Nissan GT-R", "cost": 300000, "xp_bonus": 220},
    16: {"name": "Audi R8", "cost": 450000, "xp_bonus": 330},
    17: {"name": "Lamborghini Huracan", "cost": 600000, "xp_bonus": 450},
    18: {"name": "Ferrari F8", "cost": 750000, "xp_bonus": 6000},
    19: {"name": "McLaren 720S", "cost": 900000, "xp_bonus": 750},
    20: {"name": "Rolls-Royce Phantom", "cost": 1500000, "xp_bonus": 1300},
    21: {"name": "Bugatti Veyron", "cost": 3000000, "xp_bonus": 2800},
    22: {"name": "Ferrari LaFerrari", "cost": 5000000, "xp_bonus": 5000},
    23: {"name": "Pagani Huayra", "cost": 8000000, "xp_bonus": 8500},
    24: {"name": "Bugatti Chiron", "cost": 12000000, "xp_bonus": 13000},
    25: {"name": "SpaceX Starship Personal", "cost": 50000000, "xp_bonus": 60000}
}

CASES = {
    "common": {"name": "Обычный кейс", "cost": 250, "gems_cost": 0},
    "rare": {"name": "Редкий кейс", "cost": 1000, "gems_cost": 5},
    "epic": {"name": "Эпический кейс", "cost": 5000, "gems_cost": 20},
    "legendary": {"name": "Легендарный кейс", "cost": 25000, "gems_cost": 75},
    "mythic": {"name": "Мифический кейс", "cost": 100000, "gems_cost": 250}
}

LOOT_ITEMS = ["Золотые Часы", "Алмазное Кольцо", "Древний Амулет", "Статуэтка Свободы", "Кубок Императора", "Супер-Бустер XP", "Крипто-Флешка"]

# Динамическая генерация 100 достижений, чтобы не перегружать исходный код текстом
ACHIEVEMENTS = {}
def generate_achievements_map():
    # По деньгам
    for i in range(1, 21):
        target = i * 5000 if i <= 5 else (i - 5) * 100000 if i <= 10 else (i - 10) * 10000000
        ACHIEVEMENTS[f"cash_{i}"] = {"name": f"Финансист уровень {i}", "desc": f"Накопить {target}$ наличными", "reward": target // 10}
    # По уровню
    for i in range(1, 21):
        ACHIEVEMENTS[f"lvl_{i}"] = {"name": f"Ветеран жизни уровень {i}", "desc": f"Достигнуть {i * 3} уровня", "reward": i * 500}
    # По бизнесу
    for i in range(1, 21):
        ACHIEVEMENTS[f"biz_{i}"] = {"name": f"Магнат уровень {i}", "desc": f"Купить {i} бизнесов", "reward": i * 2000}
    # По PvP победам
    for i in range(1, 21):
        ACHIEVEMENTS[f"pvp_{i}"] = {"name": f"Гладиатор уровень {i}", "desc": f"Победить в PvP {i * 5} раз", "reward": i * 1500}
    # По казино ставкам
    for i in range(1, 21):
        ACHIEVEMENTS[f"casino_{i}"] = {"name": f"Азартный игрок уровень {i}", "desc": f"Сделать {i * 10} ставок в казино", "reward": i * 300}

generate_achievements_map()

# ================= ИНИЦИАЛИЗАЦИЯ И ПОДГОТОВКА БД =================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Основная таблица пользователей
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, cash INTEGER DEFAULT 100,
            bank INTEGER DEFAULT 0, bank_deposit INTEGER DEFAULT 0, bank_loan INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0, premium_coins INTEGER DEFAULT 0, xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1, job_id INTEGER DEFAULT 0, energy INTEGER DEFAULT 100,
            last_daily TEXT, is_banned INTEGER DEFAULT 0, clan_id INTEGER DEFAULT NULL,
            pvp_wins INTEGER DEFAULT 0, pvp_losses INTEGER DEFAULT 0, last_work_time TEXT)''')
            
        # Инвентарь предметов
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_name TEXT, count INTEGER DEFAULT 1)''')
            
        # Купленные бизнесы
        await db.execute('''CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, biz_id INTEGER, level INTEGER DEFAULT 1, last_harvest TEXT)''')
            
        # Купленные машины
        await db.execute('''CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, car_id INTEGER)''')
            
        # Купленная недвижимость
        await db.execute('''CREATE TABLE IF NOT EXISTS houses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, house_id INTEGER)''')
            
        # Кланы
        await db.execute('''CREATE TABLE IF NOT EXISTS clans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, owner_id INTEGER, bank INTEGER DEFAULT 0, level INTEGER DEFAULT 1, wins INTEGER DEFAULT 0)''')
            
        # Выполненные достижения игроков
        await db.execute('''CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER, achievement_key TEXT, PRIMARY KEY (user_id, achievement_key))''')
            
        # Журнал действий администратора
        await db.execute('''CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, timestamp TEXT)''')
            
        await db.commit()

# Хелперы базы данных
async def get_user_db(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_user_if_not_exists(user_id: int, username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            if not await cursor.fetchone():
                await db.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username or f"Player_{user_id}"))
                await db.commit()

# ================= БЕЗОПАСНОСТЬ И АНТИСПАМ МИДЛВАРЬ =================
def check_rate_limit(user_id: int, limit_seconds: float = 0.5) -> bool:
    now = datetime.utcnow().timestamp()
    if user_id in ANTI_SPAM:
        if now - ANTI_SPAM[user_id] < limit_seconds:
            return False
    ANTI_SPAM[user_id] = now
    return True

def validate_init_data(init_data: str) -> dict | None:
    try:
        if not init_data: return None
        parsed_data = dict(unquote(item).split('=', 1) for item in init_data.split('&'))
        hash_val = parsed_data.pop('hash', None)
        if not hash_val: return None
        data_check_string = '\n'.join(f"{k}={parsed_data[k]}" for k in sorted(parsed_data.keys()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash == hash_val:
            return json.loads(parsed_data['user'])
    except Exception as e:
        logging.error(f"Критическая ошибка валидации Telegram initData: {e}")
    return None

# ================= ИГРОВАЯ АВТОМАТИЗАЦИЯ / ПРОВЕРКА ДОСТИЖЕНИЙ =================
async def check_and_award_achievements(user_id: int):
    user = await get_user_db(user_id)
    if not user: return
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT achievement_key FROM user_achievements WHERE user_id = ?", (user_id,)) as c:
            unlocked = [r[0] for r in await c.fetchall()]
            
        # Проверка условий по словарю ACHIEVEMENTS
        for key, info in ACHIEVEMENTS.items():
            if key in unlocked: continue
            
            condition_met = False
            if key.startswith("cash_"):
                step = int(key.split("_")[1])
                target = step * 5000 if step <= 5 else (step - 5) * 100000 if step <= 10 else (step - 10) * 10000000
                if user['cash'] >= target: condition_met = True
            elif key.startswith("lvl_"):
                step = int(key.split("_")[1])
                if user['level'] >= (step * 3): condition_met = True
                
            if condition_met:
                await db.execute("INSERT INTO user_achievements (user_id, achievement_key) VALUES (?, ?)", (user_id, key))
                await db.execute("UPDATE users SET cash = cash + ? WHERE user_id = ?", (info['reward'], user_id))
                try:
                    await bot.send_message(user_id, f"🏆 **Достижение Раскрыто!**\nВы получили: *{info['name']}*\nНаграда: +{info['reward']}$")
                except Exception: pass
        await db.commit()

# ================= API ЭНДПОИНТЫ MINI APP =================
async def api_profile_handler(request):
    auth = request.headers.get('Authorization', '')
    tg_user = validate_init_data(auth)
    if not tg_user: return web.json_response({"error": "Unauthorized Access"}, status=401)
    
    await create_user_if_not_exists(tg_user['id'], tg_user.get('username'))
    user = await get_user_db(tg_user['id'])
    if user['is_banned']: return web.json_response({"error": "Account Banned"}, status=403)
    
    # Сбор полной информации для отправки на фронтенд
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM inventory WHERE user_id = ?", (user['user_id'],)) as c:
            inv = [dict(r) for r in await c.fetchall()]
        async with db.execute("SELECT * FROM businesses WHERE user_id = ?", (user['user_id'],)) as c:
            biz = [dict(r) for r in await c.fetchall()]
        async with db.execute("SELECT * FROM cars WHERE user_id = ?", (user['user_id'],)) as c:
            cars = [dict(r) for r in await c.fetchall()]
        async with db.execute("SELECT * FROM houses WHERE user_id = ?", (user['user_id'],)) as c:
            houses = [dict(r) for r in await c.fetchall()]

    return web.json_response({
        "user": dict(user), "inventory": inv, "businesses": biz, "cars": cars, "houses": houses, "global_event": GLOBAL_EVENT
    })

async def api_work_action(request):
    auth = request.headers.get('Authorization', '')
    tg_user = validate_init_data(auth)
    if not tg_user: return web.json_response({"error": "Unauthorized"}, status=401)
    
    user = await get_user_db(tg_user['id'])
    data = await request.json()
    job_id = int(data.get("job_id", 1))
    
    if job_id not in JOBS: return web.json_response({"error": "Invalid Job ID"}, status=400)
    job = JOBS[job_id]
    
    if user['level'] < job['req_lvl']:
        return web.json_response({"error": f"Требуется уровень {job['req_lvl']}"}, status=400)
        
    # Расчет зарплаты с учетом глобальных бустов
    salary = int(job['salary'] * GLOBAL_EVENT['multiplier'])
    xp_gain = job['xp']
    
    # Шанс критического бонуса
    bonus = 0
    if random.randint(1, 100) <= job['chance']:
        bonus = salary * 2
        
    new_cash = user['cash'] + salary + bonus
    new_xp = user['xp'] + xp_gain
    
    # Расчет повышения уровня
    lvl_up = False
    req_xp = user['level'] * 100
    new_lvl = user['level']
    if new_xp >= req_xp:
        new_xp -= req_xp
        new_lvl += 1
        lvl_up = True
        
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET cash = ?, xp = ?, level = ? WHERE user_id = ?", (new_cash, new_xp, new_lvl, user['user_id']))
        await db.commit()
        
    await check_and_award_achievements(user['user_id'])
    
    return web.json_response({
        "success": True, "cash": new_cash, "xp": new_xp, "level": new_lvl, "lvl_up": lvl_up,
        "msg": f"Вы отработали смену в качестве '{job['name']}' и получили {salary}$! " + (f"🔥 Бонус: +{bonus}$!" if bonus > 0 else "")
    })

async def api_casino_handler(request):
    auth = request.headers.get('Authorization', '')
    tg_user = validate_init_data(auth)
    if not tg_user: return web.json_response({"error": "Unauthorized"}, status=401)
    
    user = await get_user_db(tg_user['id'])
    data = await request.json()
    game = data.get("game") # roulette, coin, dice, slots, blackjack
    bet = int(data.get("bet", 0))
    
    if bet <= 0 or user['cash'] < bet:
        return web.json_response({"error": "Недостаточно средств или неверная ставка"}, status=400)
        
    win = False
    multiplier = 0.0
    msg = ""
    
    if game == "coin":
        choice = data.get("choice", "орёл")
        result = random.choice(["орёл", "решка"])
        if choice == result:
            win, multiplier = True, 2.0
            msg = f"Выпало {result}! Победа!"
        else:
            msg = f"Выпало {result}! Вы проиграли."
            
    elif game == "dice":
        u_roll = random.randint(1, 6) + random.randint(1, 6)
        b_roll = random.randint(1, 6) + random.randint(1, 6)
        if u_roll > b_roll:
            win, multiplier = True, 2.0
            msg = f"Ваши кости: {u_roll}, кости дилера: {b_roll}. Вы выиграли!"
        elif u_roll == b_roll:
            win, multiplier = True, 1.0
            msg = f"Ничья! {u_roll} против {b_roll}. Ставка возвращена."
        else:
            msg = f"Ваши кости: {u_roll}, кости дилера: {b_roll}. Поражение."
            
    elif game == "slots":
        emojis = ["🍒", "🍋", "💎", "7️⃣"]
        r1, r2, r3 = random.choice(emojis), random.choice(emojis), random.choice(emojis)
        msg = f"[ {r1} | {r2} | {r3} ] "
        if r1 == r2 == r3:
            win = True
            multiplier = 5.0 if r1 != "7️⃣" else 15.0
            msg += "ДЖЕКПОТ!"
        elif r1 == r2 or r2 == r3 or r1 == r3:
            win, multiplier = True, 1.5
            msg += "Малый выигрыш!"
        else:
            msg += "Увы, мимо."
            
    else:
        return web.json_response({"error": "Game mode not integrated yet"}, status=400)
        
    final_cash = int(user['cash'] - bet + (bet * multiplier))
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET cash = ? WHERE user_id = ?", (final_cash, user['user_id']))
        await db.commit()
        
    await check_and_award_achievements(user['user_id'])
    return web.json_response({"success": True, "win": win, "cash": final_cash, "msg": msg})

async def api_bank_handler(request):
    auth = request.headers.get('Authorization', '')
    tg_user = validate_init_data(auth)
    if not tg_user: return web.json_response({"error": "Unauthorized"}, status=401)
    
    user = await get_user_db(tg_user['id'])
    data = await request.json()
    action = data.get("action")
    amount = int(data.get("amount", 0))
    
    if amount <= 0: return web.json_response({"error": "Неверная сумма"}, status=400)
    
    async with aiosqlite.connect(DB_NAME) as db:
        if action == "deposit":
            if user['cash'] < amount: return web.json_response({"error": "Мало наличных"}, status=400)
            await db.execute("UPDATE users SET cash = cash - ?, bank_deposit = bank_deposit + ? WHERE user_id = ?", (amount, amount, user['user_id']))
        elif action == "withdraw":
            if user['bank_deposit'] < amount: return web.json_response({"error": "Мало средств на депозите"}, status=400)
            await db.execute("UPDATE users SET cash = cash + ?, bank_deposit = bank_deposit - ? WHERE user_id = ?", (amount, amount, user['user_id']))
        elif action == "loan":
            max_loan = user['level'] * 5000
            if user['bank_loan'] + amount > max_loan: return web.json_response({"error": "Превышен лимит кредита"}, status=400)
            await db.execute("UPDATE users SET cash = cash + ?, bank_loan = bank_loan + ? WHERE user_id = ?", (amount, amount, user['user_id']))
        await db.commit()
        
    updated = await get_user_db(user['user_id'])
    return web.json_response({"success": True, "cash": updated['cash'], "bank_deposit": updated['bank_deposit'], "bank_loan": updated['bank_loan']})

# Маршрутизация веб-сервера
app = web.Application()
app.router.add_get('/api/profile', api_profile_handler)
app.router.add_post('/api/work', api_work_action)
app.router.add_post('/api/casino', api_casino_handler)
app.router.add_post('/api/bank', api_bank_handler)

async def root_html_handler(request):
    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as file:
            return web.Response(text=file.read(), content_type='text/html')
    return web.Response(text="<h1>Файл index.html отсутствует на сервере!</h1>", content_type='text/html')

app.router.add_get('/', root_html_handler)

# ================= TELEGRAM BOT HANDLERS =================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not check_rate_limit(message.from_user.id): return
    await create_user_if_not_exists(message.from_user.id, message.from_user.username)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗺️ СТРОИТЬ ИМПЕРИЮ (Mini App)", web_app=WebAppInfo(url=WEB_URL))]
    ])
    await message.answer(
        f"👑 **Добро пожаловать в Empire Life, {message.from_user.first_name}!**\n\n"
        f"Вы начинаете свой путь с полного нуля в роли обычного безработного с 100$ в кармане.\n"
        f"Ваша цель — заработать триллионы, скупить недвижимость, спорткары, открыть корпорации и подчинить себе топ сервера!\n\n"
        f"⚡ Полноценный интерфейс игры со всеми механиками, анимациями и казино доступен в нашем Mini App ниже!",
        reply_markup=markup, parse_mode="Markdown"
    )

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user = await get_user_db(message.from_user.id)
    if not user: return await message.answer("Сначала напишите /start")
    
    text = (
        f"👤 **Игровой профиль: @{user['username']}**\n"
        f"─────────────────────\n"
        f"💰 Наличные (Cash): `{user['cash']}`$\n"
        f"🏦 В банке (Депозит): `{user['bank_deposit']}`$\n"
        f"💳 Долг по кредиту: `{user['bank_loan']}`$\n"
        f"💎 Алмазы (Gems): `{user['gems']}`\n"
        f"👑 Премиум коины: `{user['premium_coins']}`\n"
        f"─────────────────────\n"
        f"📊 Уровень: `{user['level']}` | Опыт: `{user['xp']}/{user['level'] * 100}` XP\n"
        f"⚔️ Статистика PvP: `Wins: {user['pvp_wins']} | Losses: {user['pvp_losses']}`"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📖 **Список доступных команд бота:**\n"
        "/start - Главное меню и вход в Mini App\n"
        "/profile - Просмотр своей детальной статистики\n"
        "/work - Быстрый заработок через текстовые смены\n"
        "/bank - Проверка счетов и управление деньгами\n"
        "/top - Глобальный лидерборд сервера\n"
        "/daily - Получить ежедневный бонус\n"
        "/help - Справочник команд\n\n"
        "⭐ Все остальные механики (Кланы, Казино, Автосалон, Бизнесы) полностью интерактивны и доступны внутри Mini App!"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("daily"))
async def cmd_daily(message: types.Message):
    user = await get_user_db(message.from_user.id)
    if not user: return
    
    now = datetime.utcnow()
    fmt = "%Y-%m-%d %H:%M:%S"
    
    if user['last_daily']:
        last_dt = datetime.strptime(user['last_daily'], fmt)
        if now - last_dt < timedelta(days=1):
            remaining = timedelta(days=1) - (now - last_dt)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return await message.answer(f"❌ Вы уже забрали ежедневную награду. Приходите через {hours}ч. {minutes}м.")
            
    bonus = user['level'] * 250 + 500
    gems_bonus = random.randint(1, 3)
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET cash = cash + ?, gems = gems + ?, last_daily = ? WHERE user_id = ?", 
                         (bonus, gems_bonus, now.strftime(fmt), user['user_id']))
        await db.commit()
        
    await message.answer(f"🎁 **Ежедневная награда получена!**\n\nВы получили: `+{bonus}$` и `+{gems_bonus} 💎`")

@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT username, cash FROM users ORDER BY cash DESC LIMIT 10") as c:
            rows = await c.fetchall()
            
    leaderboard = "🏆 **ТОП-10 Богатейших Императоров:**\n\n"
    for i, row in enumerate(rows, 1):
        leaderboard += f"{i}. @{row['username']} — `{row['cash']}`$\n"
        
    await message.answer(leaderboard, parse_mode="Markdown")

# ================= АДМИН-ПАНЕЛЬ И СЕРВИСНЫЙ ФУНКЦИОНАЛ =================
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Ошибка доступа. Вы не числитесь в списке разработчиков.")
    
    admin_menu = (
        "👑 **Панель верховного администратора Empire Life**\n"
        "─────────────────────────────────────\n"
        "⚙️ **Управление валютами и ресурсами:**\n"
        "└ `/give_money [ID] [Сумма]` — Начислить наличные игроку\n"
        "└ `/take_money [ID] [Сумма]` — Списать наличные у игрока\n"
        "└ `/give_gems [ID] [Кол-во]` — Выдать алмазы\n"
        "└ `/set_level [ID] [Уровень]` — Установить игровой уровень\n\n"
        "📦 **Инвентарь и кейсы:**\n"
        "└ `/give_item [ID] [Название_Предмета]` — Сгенерировать предмет\n\n"
        "📢 **Глобальный контроль сервера:**\n"
        "└ `/broadcast [Текст]` — Массовая рассылка всем пользователям\n"
        "└ `/global_event [Множитель] [Название]` — Запустить буст рейтов\n"
        "└ `/ban [ID]` / `/unban [ID]` — Блокировка/Разблокировка\n"
        "└ `/stats` — Общая сводка и статистика сервера\n"
        "└ `/db_clear` — Полная очистка и вайп прогресса"
    )
    await message.answer(admin_menu, parse_mode="Markdown")

@dp.message(Command("give_money"))
async def adm_give_money(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        t_id, amt = int(args[0]), int(args[1])
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET cash = cash + ? WHERE user_id = ?", (amt, t_id))
            await db.execute("INSERT INTO admin_logs (action, timestamp) VALUES (?, ?)", (f"Gave {amt}$ to {t_id}", datetime.utcnow().isoformat()))
            await db.commit()
        await message.answer(f"✅ Баланс пользователя {t_id} успешно увеличен на {amt}$.")
    except Exception as e:
        await message.answer(f"❌ Ошибка ввода параметров. Шаблон: `/give_money ID Сумма`")

@dp.message(Command("take_money"))
async def adm_take_money(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        t_id, amt = int(args[0]), int(args[1])
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET cash = CASE WHEN cash >= ? THEN cash - ? ELSE 0 END WHERE user_id = ?", (amt, amt, t_id))
            await db.commit()
        await message.answer(f"✅ У пользователя {t_id} списано {amt}$.")
    except Exception:
        await message.answer("❌ Шаблон: `/take_money ID Сумма`")

@dp.message(Command("give_gems"))
async def adm_give_gems(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        t_id, amt = int(args[0]), int(args[1])
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET gems = gems + ? WHERE user_id = ?", (amt, t_id))
            await db.commit()
        await message.answer(f"✅ Выдано {amt} 💎 пользователю {t_id}.")
    except Exception:
        await message.answer("❌ Шаблон: `/give_gems ID Кол-во`")

@dp.message(Command("set_level"))
async def adm_set_level(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        t_id, lvl = int(args[0]), int(args[1])
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET level = ?, xp = 0 WHERE user_id = ?", (lvl, t_id))
            await db.commit()
        await message.answer(f"✅ Для {t_id} установлен {lvl} уровень.")
    except Exception:
        await message.answer("❌ Шаблон: `/set_level ID Уровень`")

@dp.message(Command("give_item"))
async def adm_give_item(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split(' ', 1)
        t_id = int(args[0])
        item_name = args[1].strip()
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT INTO inventory (user_id, item_name, count) VALUES (?, ?, 1)", (t_id, item_name))
            await db.commit()
        await message.answer(f"📦 Предмет '{item_name}' добавлен в инвентарь {t_id}.")
    except Exception:
        await message.answer("❌ Шаблон: `/give_item ID Название предмета`")

@dp.message(Command("broadcast"))
async def adm_broadcast(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    text = command.args
    if not text: return await message.answer("Введите текст рассылки.")
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = [r[0] for r in await cursor.fetchall()]
            
    await message.answer(f"📢 Запущена отправка сообщения для {len(users)} пользователей...")
    success = 0
    for u_id in users:
        try:
            await bot.send_message(u_id, f"📢 **Глобальное оповещение от администрации:**\n\n{text}", parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.05)  # Защита от флуд-лимитов Telegram API
        except Exception:
            continue
    await message.answer(f"🏁 Рассылка завершена. Успешно доставлено: {success}/{len(users)}.")

@dp.message(Command("global_event"))
async def adm_global_event(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split(' ', 1)
        mult = float(args[0])
        title = args[1]
        GLOBAL_EVENT["name"] = title
        GLOBAL_EVENT["multiplier"] = mult
        await message.answer(f"🔥 Событие '{title}' запущено! Все работы приносят в х{mult} больше!")
    except Exception:
        await message.answer("❌ Шаблон: `/global_event Множитель Описание`")

@dp.message(Command("ban"))
async def adm_ban(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        t_id = int(command.args.strip())
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (t_id,))
            await db.commit()
        await message.answer(f"⛔ Пользователь {t_id} заблокирован.")
    except Exception:
        await message.answer("❌ Укажите ID.")

@dp.message(Command("unban"))
async def adm_unban(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    try:
        t_id = int(command.args.strip())
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (t_id,))
            await db.commit()
        await message.answer(f"✅ Пользователь {t_id} разблокирован.")
    except Exception:
        await message.answer("❌ Укажите ID.")

@dp.message(Command("stats"))
async def adm_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c: total_users = (await c.fetchone())[0]
        async with db.execute("SELECT SUM(cash) FROM users") as c: total_cash = (await c.fetchone())[0] or 0
        async with db.execute("SELECT COUNT(*) FROM businesses") as c: total_biz = (await c.fetchone())[0]
        
    await message.answer(
        f"📊 **Системная статистика сервера:**\n"
        f"👥 Всего игроков зарегистрировано: `{total_users}`\n"
        f"💰 Наличной массы в обороте: `{total_cash}`$\n"
        f"🏢 Всего выкуплено бизнесов: `{total_biz}`", parse_mode="Markdown"
    )

@dp.message(Command("db_clear"))
async def adm_db_clear(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DROP TABLE IF EXISTS users")
        await db.execute("DROP TABLE IF EXISTS inventory")
        await db.execute("DROP TABLE IF EXISTS businesses")
        await db.execute("DROP TABLE IF EXISTS cars")
        await db.execute("DROP TABLE IF EXISTS houses")
        await db.execute("DROP TABLE IF EXISTS clans")
        await db.execute("DROP TABLE IF EXISTS user_achievements")
        await db.commit()
    await init_db()
    await message.answer("⚠️ **Глобальный вайп завершен!** Все таблицы базы данных пересозданы с нуля.")

# ================= ГЛАВНЫЙ АСИНХРОННЫЙ ЗАПУСК СЕРВЕРА =================
async def main():
    logging.info("Инициализация базы данных SQLite...")
    await init_db()
    
    # Конфигурация HTTP веб-сервера для Mini App
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEB_PORT)
    await site.start()
    logging.info(f"Внутренний веб-сервер успешно развернут на порту {WEB_PORT}")
    
    # Запуск поллинга бота
    logging.info("Запуск подсистемы длинных опросов Telegram Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Сервер Empire Life успешно остановлен Администратором.")
