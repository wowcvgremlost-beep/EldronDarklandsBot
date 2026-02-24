"""
📁 bot.py - Основной код бота
✅ ДОБАВЛЕНО:
- Полная боевая система PvE
- HP не восстанавливается после боя (только при смерти)
- Монстры в 5 раз сильнее
- У монстров есть навыки и магия
"""

import random, json, os, logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from config import BOT_TOKEN, ADMIN_IDS
import database as db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class CharacterCreation(StatesGroup):
    name = State()
    race = State()
    class_type = State()

class BattleState(StatesGroup):
    player_dice = State()
    enemy_turn = State()

# ==================== ДАННЫЕ ИГРЫ ====================
RACES = {
    "human": {"name": "🧑 Человек", "bonus": "+3 очка навыка", "magic": "✨ Благословение: +10% к лечению"},
    "elf": {"name": "🧝 Эльф", "bonus": "+3 Ловкость", "magic": "🌿 Природа: Уклонение +15%"},
    "dwarf": {"name": "🧔 Гном", "bonus": "+3 Сила", "magic": "🪨 Каменная кожа: +5 Физ.защ"},
    "orc": {"name": "👹 Орк", "bonus": "+3 Живучесть", "magic": "🔥 Ярость: +10% урона при HP<50%"},
    "fallen": {"name": "💀 Падший", "bonus": "+1 Ловк, +2 Инт", "magic": "👻 Тень: Первый удар скрытный"}
}

CLASSES = {
    "warrior": {"name": "⚔️ Воин", "bonus": "+1 Сила, +1 Жив", "magic": "🗡️ Воинский клич: +5 Физ.АТК"},
    "archer": {"name": "🏹 Лучник", "bonus": "+2 Ловкость", "magic": "🎯 Точный выстрел: Игнор 5 защиты"},
    "wizard": {"name": "🔮 Волшебник", "bonus": "+2 Интеллект", "magic": "🛡️ Маг.щит: +10 Маг.защ"},
    "bard": {"name": "🎭 Бард", "bonus": "+1 Инт, +1 Ловк", "magic": "🎵 Вдохновение: +2 ко всем статам"},
    "paladin": {"name": "🛡️ Паладин", "bonus": "+1 Сила, +1 Инт", "magic": "✨ Святой свет: Лечение +20 HP"},    "necromancer": {"name": "💀 Некромант", "bonus": "+1 Инт, +1 Жив", "magic": "☠️ Поднять скелета: Призыв"}
}

RACE_MAGIC = {r: {"name": RACES[r]["magic"].split(":")[0].strip(), "description": RACES[r]["magic"].split(":")[1].strip() if ":" in RACES[r]["magic"] else "", "type": "passive"} for r in RACES}

CLASS_MAGIC = {
    "warrior": {"name": "🗡️ Воинский клич", "description": "+5 Физ.АТК на 1 ход", "type": "active", "mp_cost": 5, "duration": 1},
    "archer": {"name": "🎯 Точный выстрел", "description": "Игнорирует 5 защиты", "type": "active", "mp_cost": 5, "duration": 1},
    "wizard": {"name": "🛡️ Магический щит", "description": "+10 Маг.защ на 1 ход", "type": "active", "mp_cost": 5, "duration": 1},
    "bard": {"name": "🎵 Вдохновение", "description": "+2 ко всем статам на 1 ход", "type": "active", "mp_cost": 10, "duration": 1},
    "paladin": {"name": "✨ Святой свет", "description": "Лечение +20 HP", "type": "active", "mp_cost": 10, "duration": 0},
    "necromancer": {"name": "☠️ Поднять скелета", "description": "Призыв помощника", "type": "active", "mp_cost": 15, "duration": 3}
}

# 🏪 МАГАЗИН
SHOP_ITEMS = {
    "potions": [
        {"id": "hp_small", "name": "🧪 Малое зелье HP", "type_name": "Зелья", "type_num": "", "effect": "+30 HP", "price": 50, "stat": "hp", "value": 30, "slot": None, "usable": True},
        {"id": "hp_medium", "name": "🧪 Среднее зелье HP", "type_name": "Зелья", "type_num": "", "effect": "+60 HP", "price": 100, "stat": "hp", "value": 60, "slot": None, "usable": True},
        {"id": "hp_large", "name": "🧪 Большое зелье HP", "type_name": "Зелья", "type_num": "", "effect": "+100 HP", "price": 150, "stat": "hp", "value": 100, "slot": None, "usable": True},
        {"id": "mp_small", "name": "🧪 Малое зелье MP", "type_name": "Зелья", "type_num": "", "effect": "+30 MP", "price": 50, "stat": "mp", "value": 30, "slot": None, "usable": True},
        {"id": "mp_medium", "name": "🧪 Среднее зелье MP", "type_name": "Зелья", "type_num": "", "effect": "+60 MP", "price": 100, "stat": "mp", "value": 60, "slot": None, "usable": True},
        {"id": "mp_large", "name": "🧪 Большое зелье MP", "type_name": "Зелья", "type_num": "", "effect": "+100 MP", "price": 150, "stat": "mp", "value": 100, "slot": None, "usable": True},
    ],
    "weapons": [
        {"id": "sword_apprentice", "name": "⚔️ Меч Ученика", "type_name": "Оружия", "type_num": "1", "effect": "+1 Сила", "price": 150, "stat": "strength", "value": 1, "slot": "weapon_1", "usable": False},
        {"id": "shield_apprentice", "name": "🛡️ Щит Ученика", "type_name": "Оружия", "type_num": "2", "effect": "+1 Живучесть", "price": 150, "stat": "vitality", "value": 1, "slot": "weapon_2", "usable": False},
        {"id": "bow_apprentice", "name": "🏹 Лук Ученика", "type_name": "Оружия", "type_num": "1", "effect": "+1 Ловкость", "price": 150, "stat": "agility", "value": 1, "slot": "weapon_1", "usable": False},
        {"id": "arrows_apprentice", "name": "🏹 Стрелы Ученика", "type_name": "Оружия", "type_num": "2", "effect": "+1 Ловкость", "price": 150, "stat": "agility", "value": 1, "slot": "weapon_2", "usable": False},
        {"id": "staff_apprentice", "name": "🔮 Посох Ученика", "type_name": "Оружия", "type_num": "1", "effect": "+1 Интеллект", "price": 150, "stat": "intelligence", "value": 1, "slot": "weapon_1", "usable": False},
        {"id": "orb_apprentice", "name": "🔮 Сфера Ученика", "type_name": "Оружия", "type_num": "2", "effect": "+1 Интеллект", "price": 150, "stat": "intelligence", "value": 1, "slot": "weapon_2", "usable": False},
    ],
    "armor": [
        {"id": "helm_apprentice", "name": "⛑️ Шлем Ученика", "type_name": "Экипировка", "type_num": "1", "effect": "+1 Живучесть", "price": 200, "stat": "vitality", "value": 1, "slot": "armor_1", "usable": False},
        {"id": "armor_apprentice", "name": "🛡️ Броня Ученика", "type_name": "Экипировка", "type_num": "2", "effect": "+1 Живучесть", "price": 200, "stat": "vitality", "value": 1, "slot": "armor_2", "usable": False},
        {"id": "pants_apprentice", "name": "👖 Штаны Ученика", "type_name": "Экипировка", "type_num": "3", "effect": "+1 Ловкость", "price": 200, "stat": "agility", "value": 1, "slot": "armor_3", "usable": False},
        {"id": "boots_apprentice", "name": "👢 Ботинки Ученика", "type_name": "Экипировка", "type_num": "4", "effect": "+1 Ловкость", "price": 200, "stat": "agility", "value": 1, "slot": "armor_4", "usable": False},
        {"id": "arms_apprentice", "name": "💪 Руки Ученика", "type_name": "Экипировка", "type_num": "5", "effect": "+1 Сила", "price": 200, "stat": "strength", "value": 1, "slot": "armor_5", "usable": False},
        {"id": "gloves_apprentice", "name": "🧤 Перчатки Ученика", "type_name": "Экипировка", "type_num": "6", "effect": "+1 Сила", "price": 200, "stat": "strength", "value": 1, "slot": "armor_6", "usable": False},
    ],
    "accessories": [
        {"id": "amulet_agility", "name": "📿 Амулет Ловкости", "type_name": "Аксессуары", "type_num": "1", "effect": "+2 Ловкость", "price": 400, "stat": "agility", "value": 2, "slot": "accessory_1", "usable": False},
        {"id": "ring_protection", "name": "💍 Кольцо Защиты", "type_name": "Аксессуары", "type_num": "2", "effect": "+2 Живучесть", "price": 400, "stat": "vitality", "value": 2, "slot": "accessory_2", "usable": False},
        {"id": "chain_strength", "name": "⛓️ Цепь Силы", "type_name": "Аксессуары", "type_num": "3", "effect": "+2 Сила", "price": 400, "stat": "strength", "value": 2, "slot": "accessory_3", "usable": False},
    ],
    "other": [
        {"id": "scroll_exp", "name": "📜 Свиток опыта", "type_name": "Разное", "type_num": "", "effect": "+50 Опыта", "price": 500, "stat": "exp", "value": 50, "slot": None, "usable": True},
    ]
}
# 👹 МОНСТРЫ (×5 СИЛЬНЕЕ + НАВЫКИ)
MONSTERS = {
    "weak": [
        {"name": "🐀 Крыса", "hp": 75, "max_hp": 75, "phys_atk": 15, "phys_def": 5, "evasion": 15, "exp": 100, "gold": 50, "skill": "🦠 Болезнь", "skill_effect": "-5 HP/ход", "skill_chance": 20},
        {"name": "🕷️ Паук", "hp": 100, "max_hp": 100, "phys_atk": 25, "phys_def": 10, "evasion": 25, "exp": 150, "gold": 75, "skill": "🕸️ Паутина", "skill_effect": "-10 Ловкость", "skill_chance": 30},
        {"name": "🦇 Летучая мышь", "hp": 60, "max_hp": 60, "phys_atk": 20, "phys_def": 5, "evasion": 40, "exp": 125, "gold": 60, "skill": "🦇 Вампиризм", "skill_effect": "Ворует 10 HP", "skill_chance": 25},
        {"name": "🧟 Зомби", "hp": 125, "max_hp": 125, "phys_atk": 30, "phys_def": 15, "evasion": 10, "exp": 175, "gold": 90, "skill": "🧟 Заражение", "skill_effect": "-10 Сила", "skill_chance": 35},
        {"name": "👺 Гоблин", "hp": 90, "max_hp": 90, "phys_atk": 25, "phys_def": 10, "evasion": 30, "exp": 200, "gold": 100, "skill": "🗡️ Крит", "skill_effect": "×2 урон", "skill_chance": 15},
    ],
    "medium": [
        {"name": "🐺 Волк", "hp": 200, "max_hp": 200, "phys_atk": 50, "phys_def": 20, "evasion": 35, "exp": 350, "gold": 200, "skill": "🐺 Стая", "skill_effect": "+20 АТК если HP<50%", "skill_chance": 40},
        {"name": "🧛 Вампир", "hp": 175, "max_hp": 175, "phys_atk": 40, "phys_def": 15, "evasion": 30, "exp": 400, "gold": 250, "skill": "🩸 Кровопийца", "skill_effect": "Ворует 20 HP", "skill_chance": 50},
        {"name": "👹 Орк", "hp": 250, "max_hp": 250, "phys_atk": 60, "phys_def": 30, "evasion": 20, "exp": 450, "gold": 275, "skill": "🔥 Ярость", "skill_effect": "+50 АТК если HP<30%", "skill_chance": 60},
    ],
    "strong": [
        {"name": "🐉 Дракон", "hp": 400, "max_hp": 400, "phys_atk": 100, "phys_def": 50, "evasion": 50, "exp": 1000, "gold": 750, "skill": "🔥 Огненное дыхание", "skill_effect": "50 урона игнорируя защиту", "skill_chance": 30},
        {"name": "💀 Рыцарь смерти", "hp": 350, "max_hp": 350, "phys_atk": 90, "phys_def": 60, "evasion": 30, "exp": 1100, "gold": 900, "skill": "💀 Проклятие", "skill_effect": "-20 ко всем статам", "skill_chance": 40},
    ],
    "bosses": [
        {"name": "👹 ВОЖДЬ ОРКОВ", "hp": 1000, "max_hp": 1000, "phys_atk": 225, "phys_def": 150, "evasion": 50, "exp": 5000, "gold": 4000, "skill": "👹 Боевой клич", "skill_effect": "+100 АТК на 1 ход", "skill_chance": 50},
    ],
    "titan": {
        "name": "👑 ТИТАН ЭЛДРОН", "hp": 2500, "max_hp": 2500, "phys_atk": 300, "phys_def": 200, "evasion": 100, "exp": 25000, "gold": 15000, "skill": "👑 Апокалипсис", "skill_effect": "100 урона", "skill_chance": 25
    }
}

SPELLS = {5: [{"id": "fire", "name": "🔥 Огонь", "effect": "+5 Маг.АТК", "cost": 2000}], 15: [{"id": "fireball", "name": "🔥 Шар", "effect": "+15 Маг.АТК", "cost": 5000}]}
CARDS = {"red": ["👹 Монстр!", "🐺 Атака!"], "yellow": ["📜 Задание: +100💰"], "green": ["✨ Бафф: +10 ко всем"], "black": ["☠️ Дебафф: -10 защиты"]}

# ==================== КЛАВИАТУРЫ ====================
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Персонаж", callback_data="my_character")],
        [InlineKeyboardButton(text="⭐️ Навыки", callback_data="skills")],
        [InlineKeyboardButton(text="✨ Способности", callback_data="abilities")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton(text="🏪 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="⚔️ Бой", callback_data="battle_menu")],
        [InlineKeyboardButton(text="🃏 Карточки", callback_data="cards_menu")],
        [InlineKeyboardButton(text="📜 Лог", callback_data="logs")],
        [InlineKeyboardButton(text="🔮 Магия", callback_data="magic_tower")],
    ])

def race_kb():
    kb = [[InlineKeyboardButton(text=f"{RACES[r]['name']} {RACES[r]['bonus']}", callback_data=f"race_{r}")] for r in RACES]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def class_kb():
    kb = [[InlineKeyboardButton(text=f"{CLASSES[c]['name']} {CLASSES[c]['bonus']}", callback_data=f"class_{c}")] for c in CLASSES]    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_race")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def skills_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💪 +1 Сила = ⚔️+4", callback_data="skill_strength")],
        [InlineKeyboardButton(text="⚡ +1 Ловк = ⚡+8 🛡️+3", callback_data="skill_agility")],
        [InlineKeyboardButton(text="❤️ +1 Жив = ❤️+10 🛡️+1", callback_data="skill_vitality")],
        [InlineKeyboardButton(text="🧠 +1 Инт = 💙+3 🔮+4", callback_data="skill_intelligence")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def inventory_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Зелья", callback_data="inv_potions")],
        [InlineKeyboardButton(text="⚔️ Оружие", callback_data="inv_weapons")],
        [InlineKeyboardButton(text="🛡️ Экипировка", callback_data="inv_armor")],
        [InlineKeyboardButton(text="📿 Бижутерия", callback_data="inv_accessories")],
        [InlineKeyboardButton(text="📦 Разное", callback_data="inv_other")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def shop_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Зелья", callback_data="shop_potions")],
        [InlineKeyboardButton(text="⚔️ Оружие", callback_data="shop_weapons")],
        [InlineKeyboardButton(text="🛡️ Экипировка", callback_data="shop_armor")],
        [InlineKeyboardButton(text="📿 Бижутерия", callback_data="shop_accessories")],
        [InlineKeyboardButton(text="📦 Разное", callback_data="shop_other")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def battle_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👹 vs Монстр", callback_data="battle_pve")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def pve_monsters_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Слабые", callback_data="monster_weak")],
        [InlineKeyboardButton(text="🟡 Средние", callback_data="monster_medium")],
        [InlineKeyboardButton(text="🔴 Сильные", callback_data="monster_strong")],
        [InlineKeyboardButton(text="👑 Боссы", callback_data="monster_bosses")],
        [InlineKeyboardButton(text="💀 ТИТАН", callback_data="monster_titan")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")],
    ])

def cards_kb():
    return InlineKeyboardMarkup(inline_keyboard=[        [InlineKeyboardButton(text="🔴 Красная", callback_data="card_red")],
        [InlineKeyboardButton(text="🟡 Жёлтая", callback_data="card_yellow")],
        [InlineKeyboardButton(text="🟢 Зелёная", callback_data="card_green")],
        [InlineKeyboardButton(text="⚫ Чёрная", callback_data="card_black")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def magic_levels_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Уровень 5", callback_data="magic_5")],
        [InlineKeyboardButton(text="📊 Уровень 15", callback_data="magic_15")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="magic_tower")],
    ])

def battle_action_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атака", callback_data="battle_attack")],
        [InlineKeyboardButton(text="🔮 Магия", callback_data="battle_magic")],
        [InlineKeyboardButton(text="🧪 Зелье", callback_data="battle_potion")],
        [InlineKeyboardButton(text="🏳️ Сдаться", callback_data="battle_surrender")],
    ])

async def edit_safe(message, **kwargs):
    try:
        await message.edit_text(**kwargs)
        return True
    except Exception as e:
        if any(x in str(e).lower() for x in ["message is not modified", "can't be edited", "not found"]):
            return True
        logger.error(f"❌ {e}")
        raise

# ==================== АДМИН-КОМАНДЫ ====================
@dp.message(Command("gold"))
async def cmd_gold(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🔒 Только для админа!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("💰 /gold me <сумма>")
        return
    action = parts[1]
    try:
        if action == "me" and len(parts) == 3:
            amount = int(parts[2])
            db.add_gold(message.from_user.id, amount)
            await message.answer(f"✅ +💰{amount}")
    except:
        await message.answer("❌ Ошибка")
@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🔒 Только для админа!")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("/reset <user_id>")
        return
    try:
        uid = int(parts[1])
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM players WHERE user_id = ?", (uid,))
        await message.answer(f"✅ Прогресс {uid} сброшен")
    except Exception as e:
        await message.answer(f"❌ {e}")

# ==================== ОСНОВНЫЕ ХЕНДЛЕРЫ ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    player = db.get_player(message.from_user.id)
    if player:
        await message.answer(f"🎮 Добро пожаловать, {player['name']}!\n💰 Золото: {player['gold']}", reply_markup=main_menu_kb(), parse_mode="HTML")
    else:
        await message.answer("🌑 <b>ТЁМНЫЕ ЗЕМЛИ ЭЛДРОНА</b>\n\n<i>Введи имя (3-30 символов):</i>", parse_mode="HTML")
        await state.set_state(CharacterCreation.name)

@dp.message(CharacterCreation.name)
async def set_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3 or len(name) > 30:
        await message.answer("❌ Имя от 3 до 30 символов:")
        return
    await state.update_data(name=name)
    await message.answer(f"✅ Имя: {name}\n\nВыбери расу:", reply_markup=race_kb(), parse_mode="HTML")
    await state.set_state(CharacterCreation.race)

@dp.callback_query(CharacterCreation.race, F.data.startswith("race_"))
async def set_race(callback: types.CallbackQuery, state: FSMContext):
    race = callback.data.split("_")[1]
    await state.update_data(race=race)
    await edit_safe(callback.message, text=f"✅ Раса: {RACES[race]['name']}\n{RACES[race]['magic']}\n\nВыбери класс:", reply_markup=class_kb(), parse_mode="HTML")
    await state.set_state(CharacterCreation.class_type)

@dp.callback_query(CharacterCreation.class_type, F.data.startswith("class_"))
async def set_class(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    class_type = callback.data.split("_")[1]    db.create_player(callback.from_user.id, callback.from_user.username or "Hero", data["name"], data["race"], class_type)
    await state.clear()
    rm, cm = RACE_MAGIC.get(data["race"], {}), CLASS_MAGIC.get(class_type, {})
    text = f"🎉 <b>Герой создан!</b>\n\n👤 {data['name']}\n🧬 {RACES[data['race']]['name']} | {CLASSES[class_type]['name']}\n✨ {rm.get('name','')}: {rm.get('description','')}\n⚔️ {cm.get('name','')}: {cm.get('description','')}\n💰 Золото: 5000\n\nТвоё приключение начинается!"
    await edit_safe(callback.message, text=text, reply_markup=main_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "my_character")
async def show_character(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    exp_needed = player["level"] * 100
    equip_text = ""
    slot_names = {"weapon_1": "⚔️ Оружие I", "weapon_2": "🛡️ Оружие II", "armor_1": "⛑️ Шлем", "armor_2": "🛡️ Броня", "armor_3": "👖 Штаны", "armor_4": "👢 Ботинки", "armor_5": "💪 Руки", "armor_6": "🧤 Перчатки", "accessory_1": "📿 Амулет", "accessory_2": "💍 Кольцо", "accessory_3": "⛓️ Цепь"}
    if player["equipment"]:
        for slot, item_id in player["equipment"].items():
            item_name = next((i["name"] for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), item_id)
            equip_text += f"{slot_names.get(slot, slot)}: {item_name}\n"
    else:
        equip_text = "• Пусто\n"
    text = (f"👤 <b>{player['name']}</b>\n📊 Уровень: {player['level']}\n❤️ HP: {player['hp']}/{player['max_hp']} | 💙 MP: {player['mp']}/{player['max_mp']}\n"
            f"✨ Опыт: {player['exp']}/{exp_needed} | 💰 Золото: {player['gold']}\n\n"
            f"📊 <b>ХАРАКТЕРИСТИКИ:</b>\n⚔️ Физ.АТК: {player['phys_atk']}\n⚡️ Скр.АТК: {player['stealth_atk']}\n"
            f"🛡️ Уклон: {player['evasion']}\n🛡️ Физ.Защ: {player['phys_def']}\n🔮 Маг.Защ: {player['magic_def']}\n🔮 Маг.АТК: {player['magic_atk']}\n\n"
            f"📈 <b>НАВЫКИ:</b>\n💪 Сила: {player['strength']}\n❤️ Жив: {player['vitality']}\n⚡️ Ловк: {player['agility']}\n🧠 Инт: {player['intelligence']}\n⭐️ Очки: {player['skill_points']}\n\n"
            f"🎒 <b>ЭКИПИРОВКА:</b>\n{equip_text}")
    await edit_safe(callback.message, text=text, reply_markup=main_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "skills")
async def show_skills(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    text = f"⭐️ <b>Прокачка</b>\n\n👤 {player['name']} | ⭐️ Очки: <b>{player['skill_points']}</b>"
    await edit_safe(callback.message, text=text, reply_markup=skills_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("skill_"))
async def upgrade_skill(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player or player["skill_points"] < 1:
        await callback.answer("❌ Недостаточно очков!", show_alert=True)
        return
    skill = callback.data.split("_")[1]
    updates = {"skill_points": player["skill_points"] - 1}
    msg = ""
    if skill == "strength":
        updates.update({"strength": player["strength"]+1, "phys_atk": player["phys_atk"]+4})
        msg = "💪 Сила +1 → ⚔️+4"    elif skill == "agility":
        updates.update({"agility": player["agility"]+1, "stealth_atk": player["stealth_atk"]+8, "evasion": player["evasion"]+3})
        msg = "⚡ Ловкость +1 → ⚡+8 🛡️+3"
    elif skill == "vitality":
        updates.update({"vitality": player["vitality"]+1, "max_hp": player["max_hp"]+10, "hp": player["hp"]+10, "phys_def": player["phys_def"]+1, "magic_def": player["magic_def"]+1})
        msg = "❤️ Живучесть +1 → ❤️+10 🛡️+1"
    elif skill == "intelligence":
        updates.update({"intelligence": player["intelligence"]+1, "max_mp": player["max_mp"]+3, "mp": player["mp"]+3, "magic_atk": player["magic_atk"]+4})
        msg = "🧠 Интеллект +1 → 💙+3 🔮+4"
    db.update_player(callback.from_user.id, **updates)
    await callback.answer(f"✅ {msg}!", show_alert=True)
    await show_skills(callback)

@dp.callback_query(F.data == "inventory")
async def show_inventory(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    inv = player["inventory"]
    text = "🎒 Инвентарь\n\n" + ("\n".join([f"• {k} x{v}" for k,v in inv.items()]) if inv else "• Пусто")
    await edit_safe(callback.message, text=text, reply_markup=inventory_kb(), parse_mode="HTML")

# ==================== ⚔️ БОЕВАЯ СИСТЕМА ====================

@dp.callback_query(F.data == "battle_menu")
async def battle_menu(callback: types.CallbackQuery):
    await edit_safe(callback.message, text="⚔️ Бой", reply_markup=battle_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "battle_pve")
async def select_monster(callback: types.CallbackQuery):
    await edit_safe(callback.message, text="👹 Выбери сложность", reply_markup=pve_monsters_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("monster_"))
async def start_pve_battle(callback: types.CallbackQuery, state: FSMContext):
    """Начало боя с монстром"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    
    tier = callback.data.split("_")[1]
    if tier == "titan":
        monster = MONSTERS["titan"].copy()
    elif tier in MONSTERS:
        monster = random.choice(MONSTERS[tier]).copy()
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)
        return
        # Сохраняем состояние боя
    battle_data = {
        "player_hp": player["hp"],
        "player_max_hp": player["max_hp"],
        "player_mp": player["mp"],
        "enemy": monster,
        "enemy_hp": monster["hp"],
        "turn": 0
    }
    await state.update_data(battle=battle_data)
    
    text = (f"⚔️ <b>НАЧАЛО БОЯ!</b>\n\n"
            f"👤 {player['name']} ❤️{player['hp']}/{player['max_hp']} 💙{player['mp']}/{player['max_mp']}\n"
            f"🆚\n"
            f"👹 {monster['name']} ❤️{monster['hp']}/{monster['max_hp']}\n"
            f"✨ Навык: {monster.get('skill', 'Нет')} ({monster.get('skill_chance', 0)}%)\n\n"
            f"<i>Кинь кубик d20 и напиши число (1-20):</i>")
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏳️ Сдаться", callback_data="battle_surrender")]]), parse_mode="HTML")
    await state.set_state(BattleState.player_dice)

@dp.message(BattleState.player_dice)
async def player_dice_roll(message: types.Message, state: FSMContext):
    """Бросок кубика игроком"""
    try:
        dice = int(message.text)
        if dice < 1 or dice > 20:
            await message.answer("❌ Число от 1 до 20!")
            return
    except ValueError:
        await message.answer("❌ Введи число!")
        return
    
    data = await state.get_data()
    battle = data.get("battle", {})
    if not battle:
        await message.answer("❌ Бой не найден.")
        await state.clear()
        return
    
    # Бросок монстра
    enemy_dice = random.randint(1, 20)
    
    # Инициатива: Скр.АТК + кубик
    player_init = battle.get("player_stats", {}).get("stealth_atk", 50) + dice
    enemy_init = battle["enemy"]["evasion"] + enemy_dice
    first = "player" if player_init >= enemy_init else "enemy"
    
    text = (f"🎲 <b>Результаты броска:</b>\n"
            f"👤 Ты: {battle.get('player_stats', {}).get('stealth_atk', 50)} + {dice} = {player_init}\n"            f"👹 Враг: {battle['enemy']['evasion']} + {enemy_dice} = {enemy_init}\n\n"
            f"{'✅ Ты ходишь первым!' if first == 'player' else '⚠️ Враг ходит первым!'}\n\n"
            f"<i>Выбери действие:</i>")
    
    await state.update_data(player_dice=dice, enemy_dice=enemy_dice, first_turn=first)
    await state.set_state(None)
    await message.answer(text, reply_markup=battle_action_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("battle_"))
async def battle_action(callback: types.CallbackQuery, state: FSMContext):
    """Действия в бою"""
    action = callback.data.split("_")[1]
    data = await state.get_data()
    battle = data.get("battle", {})
    
    if not battle:
        await callback.answer("❌ Бой не найден", show_alert=True)
        return
    
    # Получаем актуальные данные игрока
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Ошибка!", show_alert=True)
        return
    
    enemy = battle["enemy"].copy()
    enemy_hp = battle["enemy_hp"]
    
    # ✅ СДАТЬСЯ
    if action == "surrender":
        db.update_player(callback.from_user.id, gold=0)
        await callback.message.edit_text(
            "🏳️ Ты сдался.\n💰 Золото потеряно.\n❤️ HP не восстановлены.",
            reply_markup=main_menu_kb(), parse_mode="HTML"
        )
        await state.clear()
        return
    
    # ⚔️ АТАКА
    if action == "attack":
        player_dmg = max(1, player["phys_atk"] - enemy["phys_def"] + random.randint(1, 20))
        
        # Критический удар (кубик 20)
        if data.get("player_dice", 0) == 20:
            player_dmg *= 2
            logger.info(f"🎯 КРИТИЧЕСКИЙ УДАР! ×2 урон")
        
        enemy_hp -= player_dmg
        
        # Проверка на навык монстра (крит)        if enemy.get("skill") == "🗡️ Крит" and random.randint(1, 100) <= enemy.get("skill_chance", 0):
            player_dmg *= 2
            enemy_hp -= player_dmg
            logger.info(f"🗡️ Монстр использовал крит! +{player_dmg} урона")
        
        if enemy_hp <= 0:
            # ✅ ПОБЕДА: HP НЕ восстанавливаются
            db.update_player(callback.from_user.id, 
                exp=player["exp"] + enemy["exp"],
                gold=player["gold"] + enemy["gold"]
            )
            db.add_log(callback.from_user.id, "battle_win", f"Победа над {enemy['name']}")
            
            await callback.message.edit_text(
                f"🏆 <b>ПОБЕДА!</b>\n\n"
                f"⚔️ Ты нанёс {player_dmg} урона!\n"
                f"👹 {enemy['name']} повержен!\n"
                f"✨ +{enemy['exp']} опыта\n"
                f"💰 +{enemy['gold']} золота\n\n"
                f"⚠️ HP не восстановлены: ❤️ {player['hp']}/{player['max_hp']}",
                reply_markup=main_menu_kb(), parse_mode="HTML"
            )
            await state.clear()
            return
        
        # Ход монстра
        enemy_dmg = max(1, enemy["phys_atk"] - player["phys_def"] + random.randint(1, 20))
        new_hp = max(0, player["hp"] - enemy_dmg)
        
        # Проверка навыка монстра
        skill_used = ""
        if enemy.get("skill") and random.randint(1, 100) <= enemy.get("skill_chance", 0):
            skill_used = f"\n✨ {enemy['name']} использовал {enemy['skill']}!"
            if enemy["skill"] in ["🦇 Вампиризм", "🩸 Кровопийца"]:
                steal = min(10 if "Вампиризм" in enemy["skill"] else 20, enemy_dmg)
                enemy_hp = min(enemy["max_hp"], enemy_hp + steal)
                new_hp = max(0, new_hp - steal)
                skill_used += f" (украдено {steal} HP)"
        
        if new_hp <= 0:
            # ✅ ПОРАЖЕНИЕ: золото теряется, HP восстанавливаются ТОЛЬКО при смерти
            db.update_player(callback.from_user.id, gold=0, hp=player["max_hp"])
            db.add_log(callback.from_user.id, "battle_lose", f"Поражение от {enemy['name']}")
            
            await callback.message.edit_text(
                f"💀 <b>ПОРАЖЕНИЕ!</b>\n\n"
                f"👹 {enemy['name']} нанёс {enemy_dmg} урона{skill_used}\n"
                f"Ты пал в бою...\n"
                f"💰 Всё золото потеряно.\n"
                f"❤️ Ты воскрешён с полным HP (только после смерти).",                reply_markup=main_menu_kb(), parse_mode="HTML"
            )
            await state.clear()
            return
        
        # ✅ Обновляем HP игрока (НЕ восстанавливаем после боя!)
        db.update_player(callback.from_user.id, hp=new_hp)
        
        # Сохраняем состояние
        battle["enemy_hp"] = enemy_hp
        await state.update_data(battle=battle)
        
        await callback.message.edit_text(
            f"⚔️ <b>Ход завершён</b>\n\n"
            f"👤 Ты нанёс: {player_dmg} урона\n"
            f"👹 Враг нанёс: {enemy_dmg} урона{skill_used}\n\n"
            f"👤 Твой HP: {new_hp}/{player['max_hp']}\n"
            f"👹 Враг HP: {enemy_hp}/{enemy['max_hp']}\n\n"
            f"<i>Кинь кубик d20 и напиши число (1-20):</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏳️ Сдаться", callback_data="battle_surrender")]]),
            parse_mode="HTML"
        )
        await state.set_state(BattleState.player_dice)
        return
    
    # 🔮 МАГИЯ
    if action == "magic":
        if player["mp"] < 5:
            await callback.answer("❌ Недостаточно MP!", show_alert=True)
            return
        dmg = max(1, player["magic_atk"] - enemy.get("magic_def", 5) + random.randint(1, 20))
        enemy_hp -= dmg
        db.update_player(callback.from_user.id, mp=max(0, player["mp"] - 5))
        battle["enemy_hp"] = enemy_hp
        await state.update_data(battle=battle)
        await callback.answer(f"🔮 Магия нанесла {dmg} урона!", show_alert=True)
        return
    
    # 🧪 ЗЕЛЬЕ
    if action == "potion":
        inv = player.get("inventory", {})
        if "hp_small" not in inv or inv["hp_small"] < 1:
            await callback.answer("❌ Нет зелий!", show_alert=True)
            return
        new_hp = min(player["max_hp"], player["hp"] + 30)
        inv["hp_small"] -= 1
        db.update_player(callback.from_user.id, hp=new_hp, inventory=inv)
        battle["player_hp"] = new_hp
        await state.update_data(battle=battle)
        await callback.answer(f"🧪 +30 HP! ❤️ {new_hp}/{player['max_hp']}", show_alert=True)        return

# ==================== ИНВЕНТАРЬ ====================
@dp.callback_query(F.data.startswith("inv_"))
async def show_inventory_category(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    cat_map = {"inv_potions": "potions", "inv_weapons": "weapons", "inv_armor": "armor", "inv_accessories": "accessories", "inv_other": "other"}
    category = cat_map.get(callback.data, "potions")
    inv = player["inventory"]
    items_in_inv = [(item, inv[item["id"]]) for item in SHOP_ITEMS.get(category, []) if item["id"] in inv and inv[item["id"]] > 0]
    kb = []
    for item, count in items_in_inv:
        is_equipped = any(eid == item["id"] for eid in player.get("equipment", {}).values())
        prefix = "✅ " if is_equipped else "🎒 "
        kb.append([InlineKeyboardButton(text=f"{prefix}{item['name']} x{count}", callback_data=f"item_select_{item['id']}")])
    slot_prefix = {"weapons": "weapon", "armor": "armor", "accessories": "accessory"}.get(category)
    if slot_prefix and any(slot.startswith(slot_prefix) for slot in player.get("equipment", {})):
        kb.append([InlineKeyboardButton(text="🔻 Снять всю экипировку", callback_data=f"unequip_all_{category}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="inventory")])
    text = f"🎒 {category.title()}\n\n<i>Нажми на предмет для выбора действия:</i>"
    await edit_safe(callback.message, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("item_select_"))
async def item_action_menu(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Ошибка!", show_alert=True)
        return
    item_id = callback.data.split("_", 2)[2]
    item = next((i for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), None)
    if not item:
        await callback.answer("❌ Предмет не найден!", show_alert=True)
        return
    count = player["inventory"].get(item_id, 0)
    equipped_slot = None
    for slot, eid in player.get("equipment", {}).items():
        if eid == item_id:
            equipped_slot = slot
            break
    kb = []
    if item.get("slot") and not equipped_slot:
        kb.append([InlineKeyboardButton(text="⚔️ Одеть", callback_data=f"equip_{item_id}")])
    elif equipped_slot:
        kb.append([InlineKeyboardButton(text="✅ Экипировано", callback_data="noop")])
        kb.append([InlineKeyboardButton(text="🔻 Снять", callback_data=f"unequip_{item_id}")])
    if item.get("usable"):
        if item["stat"] == "hp":            kb.append([InlineKeyboardButton(text=f"💚 Применить (+{item['value']} HP)", callback_data=f"use_{item_id}")])
        elif item["stat"] == "mp":
            kb.append([InlineKeyboardButton(text=f"💙 Применить (+{item['value']} MP)", callback_data=f"use_{item_id}")])
        elif item["stat"] == "exp":
            kb.append([InlineKeyboardButton(text=f"📜 Использовать (+{item['value']} EXP)", callback_data=f"use_{item_id}")])
    kb.append([InlineKeyboardButton(text=f"💰 Продать за {item['price']//2}💰", callback_data=f"sell_{item_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="inventory")])
    status = "✅ Экипировано" if equipped_slot else "🎒 В инвентаре"
    text = f"🎒 {item['name']} x{count}\n\n{item['effect']}\n💰 Цена: {item['price']} | Продажа: {item['price']//2}\n📊 Статус: {status}\n\n<i>Выбери действие:</i>"
    await edit_safe(callback.message, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("use_"))
async def use_item(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    item_id = callback.data.split("_", 1)[1]
    inv = player["inventory"]
    if item_id not in inv or inv[item_id] < 1:
        await callback.answer("❌ Нет предмета!", show_alert=True)
        return
    item = next((i for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), None)
    if not item or not item.get("usable"):
        await callback.answer("❌ Этот предмет нельзя применить!", show_alert=True)
        return
    updates = {}
    msg = ""
    if item["stat"] == "hp":
        new_hp = min(player["hp"] + item["value"], player["max_hp"])
        if new_hp == player["hp"]:
            await callback.answer("⚠️ HP уже полностью восстановлено!", show_alert=True)
            return
        updates["hp"] = new_hp
        msg = f"💚 +{item['value']} HP"
    elif item["stat"] == "mp":
        new_mp = min(player["mp"] + item["value"], player["max_mp"])
        if new_mp == player["mp"]:
            await callback.answer("⚠️ MP уже полностью восстановлено!", show_alert=True)
            return
        updates["mp"] = new_mp
        msg = f"💙 +{item['value']} MP"
    elif item["stat"] == "exp":
        new_exp = player["exp"] + item["value"]
        exp_needed = player["level"] * 100
        if new_exp >= exp_needed:
            updates["level"] = player["level"] + 1
            updates["exp"] = new_exp - exp_needed
            updates["skill_points"] = player["skill_points"] + 1
            msg = f"📜 +{item['value']} EXP | 🎉 Уровень {updates['level']}! +1⭐️"        else:
            updates["exp"] = new_exp
            msg = f"📜 +{item['value']} EXP"
    inv[item_id] -= 1
    if inv[item_id] <= 0:
        del inv[item_id]
    updates["inventory"] = inv
    db.update_player(callback.from_user.id, **updates)
    db.add_log(callback.from_user.id, "use_item", f"Применил {item['name']}")
    await callback.answer(f"✅ {msg}!", show_alert=True)
    await item_action_menu(callback)

@dp.callback_query(F.data.startswith("equip_"))
async def equip_item(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    item_id = callback.data.split("_", 1)[1]
    if item_id not in player["inventory"] or player["inventory"][item_id] < 1:
        await callback.answer("❌ Нет в инвентаре!", show_alert=True)
        return
    item = next((i for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), None)
    item_slot = item.get("slot") if item else None
    if not item_slot:
        await callback.answer("❌ Предмет не экипируется!", show_alert=True)
        return
    equipment = player["equipment"]
    equipment[item_slot] = item_id
    db.update_player(callback.from_user.id, equipment=equipment)
    updated_player = db.get_player(callback.from_user.id)
    new_stats = db.recalc_all_stats(updated_player, SHOP_ITEMS)
    db.update_player(callback.from_user.id, **{k: new_stats[k] for k in ["strength", "vitality", "agility", "intelligence", "skill_points", "phys_atk", "stealth_atk", "evasion", "phys_def", "magic_def", "magic_atk", "max_hp", "max_mp", "hp", "mp"]})
    db.add_log(callback.from_user.id, "equip_item", f"Надел {item['name']}")
    await callback.answer(f"✅ {item['name']} надето!", show_alert=True)
    await item_action_menu(callback)

@dp.callback_query(F.data.startswith("unequip_"))
async def unequip_item(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    item_id = callback.data.split("_", 1)[1]
    equipment = player.get("equipment", {})
    slot_to_remove = None
    for slot, eid in equipment.items():
        if eid == item_id:
            slot_to_remove = slot
            break    if not slot_to_remove:
        await callback.answer("⚠️ Предмет не экипирован!", show_alert=True)
        return
    del equipment[slot_to_remove]
    db.update_player(callback.from_user.id, equipment=equipment)
    updated_player = db.get_player(callback.from_user.id)
    new_stats = db.recalc_all_stats(updated_player, SHOP_ITEMS)
    db.update_player(callback.from_user.id, **{k: new_stats[k] for k in ["strength", "vitality", "agility", "intelligence", "skill_points", "phys_atk", "stealth_atk", "evasion", "phys_def", "magic_def", "magic_atk", "max_hp", "max_mp", "hp", "mp"]})
    item = next((i for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), None)
    db.add_log(callback.from_user.id, "unequip_item", f"Снял {item['name'] if item else item_id}")
    await callback.answer(f"🔻 {item['name'] if item else item_id} снято!", show_alert=True)
    await item_action_menu(callback)

@dp.callback_query(F.data.startswith("unequip_all_"))
async def unequip_all_category(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("❌ Ошибка!", show_alert=True)
        return
    category = parts[2]
    slot_map = {
        "weapons": ["weapon_1", "weapon_2"],
        "armor": ["armor_1", "armor_2", "armor_3", "armor_4", "armor_5", "armor_6"],
        "accessories": ["accessory_1", "accessory_2", "accessory_3"]
    }
    slots_to_check = slot_map.get(category, [])
    if not slots_to_check:
        await callback.answer("❌ Ошибка категории!", show_alert=True)
        return
    equipment = player.get("equipment", {})
    removed = []
    for slot in slots_to_check:
        if slot in equipment:
            item_id = equipment[slot]
            item_name = next((i["name"] for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), item_id)
            del equipment[slot]
            removed.append(item_name)
    if not removed:
        await callback.answer("⚠️ Нечего снимать!", show_alert=True)
        return
    db.update_player(callback.from_user.id, equipment=equipment)
    updated_player = db.get_player(callback.from_user.id)
    new_stats = db.recalc_all_stats(updated_player, SHOP_ITEMS)
    db.update_player(callback.from_user.id, **{k: new_stats[k] for k in ["strength", "vitality", "agility", "intelligence", "skill_points", "phys_atk", "stealth_atk", "evasion", "phys_def", "magic_def", "magic_atk", "max_hp", "max_mp", "hp", "mp"]})
    db.add_log(callback.from_user.id, "unequip_all", f"Снял: {', '.join(removed)}")
    await callback.answer(f"🔻 Снято: {', '.join(removed)}!", show_alert=True)    await show_inventory_category(callback)

@dp.callback_query(F.data.startswith("sell_"))
async def sell_item(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    item_id = callback.data.split("_", 1)[1]
    inv = player["inventory"]
    if item_id not in inv or inv[item_id] < 1:
        await callback.answer("❌ Нет предмета!", show_alert=True)
        return
    item = next((i for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), None)
    if not item:
        await callback.answer("❌ Предмет не найден!", show_alert=True)
        return
    equipment = player.get("equipment", {})
    equipped_slot = None
    for slot, eid in equipment.items():
        if eid == item_id:
            equipped_slot = slot
            break
    if equipped_slot:
        del equipment[equipped_slot]
        db.update_player(callback.from_user.id, equipment=equipment)
        logger.info(f"🔻 Снят экипированный предмет {item_id} перед продажей")
    price = item["price"] // 2
    inv[item_id] -= 1
    if inv[item_id] <= 0:
        del inv[item_id]
    db.update_player(callback.from_user.id, inventory=inv, gold=player["gold"] + price)
    updated_player = db.get_player(callback.from_user.id)
    new_stats = db.recalc_all_stats(updated_player, SHOP_ITEMS)
    db.update_player(callback.from_user.id, **{k: new_stats[k] for k in ["strength", "vitality", "agility", "intelligence", "skill_points", "phys_atk", "stealth_atk", "evasion", "phys_def", "magic_def", "magic_atk", "max_hp", "max_mp", "hp", "mp"]})
    db.add_log(callback.from_user.id, "sell_item", f"Продал {item['name']} за 💰{price}")
    await callback.answer(f"✅ Продано: {item['name']} за 💰{price}!", show_alert=True)
    await show_inventory_category(callback)

# ==================== МАГАЗИН ====================
@dp.callback_query(F.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    await edit_safe(callback.message, text="🏪 Магазин\n\nВыбери категорию:", reply_markup=shop_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("shop_"))
async def show_shop_category(callback: types.CallbackQuery):
    cat_map = {"shop_potions": "potions", "shop_weapons": "weapons", "shop_armor": "armor", "shop_accessories": "accessories", "shop_other": "other"}
    category = cat_map.get(callback.data, "potions")
    items = SHOP_ITEMS.get(category, [])
    kb = [[InlineKeyboardButton(text=f"{item['name']} {item['effect']} 💰{item['price']}", callback_data=f"buy_{category}_{item['id']}")] for item in items]    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop")])
    await edit_safe(callback.message, text=f"🏪 {category.title()}\n\n<i>Нажми для покупки:</i>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_item(callback: types.CallbackQuery):
    uid = callback.from_user.id
    parts = callback.data.split("_", 2)
    if len(parts) != 3:
        await callback.answer("❌ Ошибка формата!", show_alert=True)
        return
    category, item_id = parts[1], parts[2]
    player = db.get_player(uid)
    if not player:
        await callback.answer("❌ Персонаж не найден!", show_alert=True)
        return
    item = next((i for i in SHOP_ITEMS.get(category, []) if i["id"] == item_id), None)
    if not item:
        await callback.answer(f"❌ Предмет не найден: {item_id}", show_alert=True)
        return
    if player["gold"] < item["price"]:
        await callback.answer(f"❌ Нужно 💰{item['price']}, у вас 💰{player['gold']}", show_alert=True)
        return
    if not db.spend_gold(uid, item["price"]):
        await callback.answer("❌ Ошибка списания!", show_alert=True)
        return
    inv = player.get("inventory", {})
    inv[item_id] = inv.get(item_id, 0) + 1
    db.update_player(uid, inventory=inv)
    db.add_log(uid, "buy_item", f"Купил {item['name']}")
    await callback.answer(f"✅ Куплено: {item['name']}!", show_alert=True)
    
    async def show_shop_category_by_name(callback, category):
        items = SHOP_ITEMS.get(category, [])
        kb = [[InlineKeyboardButton(text=f"{item['name']} {item['effect']} 💰{item['price']}", callback_data=f"buy_{category}_{item['id']}")] for item in items]
        kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop")])
        await edit_safe(callback.message, text=f"🏪 {category.title()}\n\n<i>Нажми для покупки:</i>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
    
    await show_shop_category_by_name(callback, category)

# ==================== ОСТАЛЬНЫЕ ХЕНДЛЕРЫ ====================
@dp.callback_query(F.data == "cards_menu")
async def cards_menu(callback: types.CallbackQuery):
    await edit_safe(callback.message, text="🃏 Карточки\n\nВыбери тип:", reply_markup=cards_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("card_"))
async def draw_card(callback: types.CallbackQuery):
    ctype = callback.data.split("_", 1)[1]
    text = random.choice(CARDS[ctype])
    colors = {"red": "🔴", "yellow": "🟡", "green": "🟢", "black": "⚫"}
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Ещё", callback_data=f"card_{ctype}")], [InlineKeyboardButton(text="🔙 Назад", callback_data="cards_menu")]])    await edit_safe(callback.message, text=f"{colors[ctype]} {text}", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "logs")
async def show_logs(callback: types.CallbackQuery):
    logs = db.get_logs(callback.from_user.id)
    text = "📜 Лог\n\n" + ("\n".join([f"• {l['action']}: {l['details']}" for l in logs[:10]]) if logs else "• Пусто")
    await edit_safe(callback.message, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]), parse_mode="HTML")

@dp.callback_query(F.data == "magic_tower")
async def magic_tower(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    await edit_safe(callback.message, text=f"🔮 Башня Магии\n\nУровень: {player['level']}\n💰 {player['gold']}", reply_markup=magic_levels_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("magic_"))
async def show_spells(callback: types.CallbackQuery):
    level = int(callback.data.split("_", 1)[1])
    player = db.get_player(callback.from_user.id)
    if player["level"] < level:
        await callback.answer(f"❌ Нужен уровень {level}!", show_alert=True)
        return
    spells = SPELLS.get(level, [])
    kb = [[InlineKeyboardButton(text=f"{s['name']} 💰{s['cost']}", callback_data=f"spell_{level}_{s['id']}")] for s in spells]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="magic_tower")])
    await edit_safe(callback.message, text=f"🔮 Уровень {level}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("spell_"))
async def learn_spell(callback: types.CallbackQuery):
    parts = callback.data.split("_", 2)
    level, spell_id = int(parts[1]), parts[2]
    player = db.get_player(callback.from_user.id)
    spell = next((s for s in SPELLS.get(level, []) if s["id"] == spell_id), None)
    if not spell or player["level"] < level or player["gold"] < spell["cost"]:
        await callback.answer("❌ Недостаточно условий!", show_alert=True)
        return
    db.update_player(callback.from_user.id, gold=player["gold"] - spell["cost"])
    spells = player["spells"]
    if spell_id not in spells:
        spells.append(spell_id)
        db.update_player(callback.from_user.id, spells=spells)
    await callback.answer(f"✅ Изучено: {spell['name']}!", show_alert=True)

@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: types.CallbackQuery, state: FSMContext):
    await edit_safe(callback.message, text="🌑 Введи имя (3-30 символов):", parse_mode="HTML")
    await state.set_state(CharacterCreation.name)

@dp.callback_query(F.data == "back_to_race")async def back_race(callback: types.CallbackQuery, state: FSMContext):
    await edit_safe(callback.message, text="Выбери расу:", reply_markup=race_kb())
    await state.set_state(CharacterCreation.race)

@dp.callback_query(F.data == "main_menu")
async def back_main(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if player:
        await edit_safe(callback.message, text=f"🎮 {player['name']}", reply_markup=main_menu_kb(), parse_mode="HTML")
    else:
        await edit_safe(callback.message, text="🌑 /start для начала", parse_mode="HTML")

# ==================== WEBHOOK ====================
async def on_startup(app):
    url = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RENDER_EXTERNAL_URL")
    if url:
        url = url.replace("http://", "https://").rstrip("/")
        await bot.set_webhook(f"{url}/webhook", allowed_updates=dp.resolve_used_update_types())
        logger.info(f"✅ Webhook: {url}/webhook")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()

async def webhook_handler(request):
    try:
        update = types.Update(**await request.json())
        await dp.feed_update(bot, update)
        return web.Response()
    except Exception as e:
        logger.error(f"❌ Webhook: {e}")
        return web.Response(status=400)

def create_app():
    app = web.Application()
    app.router.add_post("/webhook", webhook_handler)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

def main():
    app = create_app()
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()