import random
import json
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from config import BOT_TOKEN
import database as db

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== СОСТОЯНИЯ ====================
class CharacterCreation(StatesGroup):
    name = State()
    race = State()
    class_type = State()

class BattleState(StatesGroup):
    player_dice = State()

# ==================== ДАННЫЕ ИГРЫ ====================
RACES = {
    "human": {"name": "🧑 Человек", "bonus": "+3 очка навыка", "magic": "✨ Благословение"},
    "elf": {"name": "🧝 Эльф", "bonus": "+3 Ловкость", "magic": "🌿 Природа: Уклон +15%"},
    "dwarf": {"name": "🧔 Гном", "bonus": "+3 Сила", "magic": "🪨 Каменная кожа"},
    "orc": {"name": "👹 Орк", "bonus": "+3 Живучесть", "magic": "🔥 Ярость при HP<50%"},
    "fallen": {"name": "💀 Падший", "bonus": "+1 Ловк, +2 Инт", "magic": "👻 Тень: скрытный удар"}
}

RACE_MAGIC = {
    "human": {
        "name": "✨ Благословение",
        "description": "+10% к лечению",
        "type": "passive",  # пассивная
        "effect": "heal_bonus_10"  # эффект
    },
    "elf": {
        "name": "🌿 Природа",
        "description": "Уклонение +15%",
        "type": "passive",
        "effect": "evasion_15"
    },
    "dwarf": {
        "name": "🪨 Каменная кожа",
        "description": "+5 Физ.защ",
        "type": "passive",
        "effect": "phys_def_5"
    },
    "orc": {
        "name": "🔥 Ярость",
        "description": "+10% урона при HP<50%",
        "type": "passive",
        "effect": "rage_damage_10"
    },
    "fallen": {
        "name": "👻 Тень",
        "description": "Первый удар скрытный",
        "type": "passive",
        "effect": "first_strike_stealth"
    }
}

CLASSES = {
    "warrior": {"name": "⚔️ Воин", "bonus": "+1 Сила, +1 Жив", "magic": "🗡️ Клич: +5 Физ.АТК"},
    "archer": {"name": "🏹 Лучник", "bonus": "+2 Ловкость", "magic": "🎯 Точный выстрел"},
    "wizard": {"name": "🔮 Волшебник", "bonus": "+2 Интеллект", "magic": "🛡️ Маг.щит"},
    "bard": {"name": "🎭 Бард", "bonus": "+1 Инт, +1 Ловк", "magic": "🎵 Вдохновение"},
    "paladin": {"name": "🛡️ Паладин", "bonus": "+1 Сила, +1 Инт", "magic": "✨ Святой свет"},
    "necromancer": {"name": "💀 Некромант", "bonus": "+1 Инт, +1 Жив", "magic": "☠️ Призыв"}
}

CLASS_MAGIC = {
    "warrior": {
        "name": "🗡️ Воинский клич",
        "description": "+5 Физ.АТК на 1 ход",
        "type": "active",
        "mp_cost": 5,
        "effect": "phys_atk_buff_5",
        "duration": 1  # ходов
    },
    "archer": {
        "name": "🎯 Точный выстрел",
        "description": "Игнорирует 5 защиты",
        "type": "active",
        "mp_cost": 5,
        "effect": "ignore_def_5",
        "duration": 1
    },
    "wizard": {
        "name": "🛡️ Магический щит",
        "description": "+10 Маг.защ на 1 ход",
        "type": "active",
        "mp_cost": 5,
        "effect": "magic_def_buff_10",
        "duration": 1
    },
    "bard": {
        "name": "🎵 Вдохновение",
        "description": "+2 ко всем характеристикам на 1 ход",
        "type": "active",
        "mp_cost": 10,
        "effect": "all_stats_buff_2",
        "duration": 1
    },
    "paladin": {
        "name": "✨ Святой свет",
        "description": "Лечение +20 HP",
        "type": "active",
        "mp_cost": 10,
        "effect": "heal_20",
        "duration": 0  # мгновенное
    },
    "necromancer": {
        "name": "☠️ Поднять скелета",
        "description": "Призыв помощника (урон +10)",
        "type": "active",
        "mp_cost": 15,
        "effect": "summon_skeleton",
        "duration": 3  # 3 хода
    }
}

SHOP_ITEMS = {
    "potions": [
        {"id": "hp_small", "name": "🧪 Малое зелье HP", "effect": "+30 HP", "price": 50},
        {"id": "hp_medium", "name": "🧪 Среднее зелье HP", "effect": "+60 HP", "price": 100},
        {"id": "hp_large", "name": "🧪 Большое зелье HP", "effect": "+100 HP", "price": 150},
        {"id": "mp_small", "name": "🧪 Малое зелье MP", "effect": "+30 MP", "price": 50},
        {"id": "mp_medium", "name": "🧪 Среднее зелье MP", "effect": "+60 MP", "price": 100},
        {"id": "mp_large", "name": "🧪 Большое зелье MP", "effect": "+100 MP", "price": 150},
    ],
    "weapons": [
        {"id": "sword_apprentice", "name": "⚔️ Меч Ученика", "effect": "+1 Сила", "price": 150},
        {"id": "shield_apprentice", "name": "🛡️ Щит Ученика", "effect": "+1 Живучесть", "price": 150},
        {"id": "bow_apprentice", "name": "🏹 Лук Ученика", "effect": "+1 Ловкость", "price": 150},
        {"id": "staff_apprentice", "name": "🔮 Посох Ученика", "effect": "+1 Интеллект", "price": 150},
    ],
    "armor": [
        {"id": "helm_apprentice", "name": "⛑️ Шлем Ученика", "effect": "+1 Живучесть", "price": 200},
        {"id": "armor_apprentice", "name": "🛡️ Броня Ученика", "effect": "+1 Живучесть", "price": 200},
        {"id": "pants_apprentice", "name": "👖 Штаны Ученика", "effect": "+1 Ловкость", "price": 200},
    ],
    "accessories": [
        {"id": "amulet_agility", "name": "📿 Амулет Ловкости", "effect": "+2 Ловкость", "price": 400},
        {"id": "ring_protection", "name": "💍 Кольцо Защиты", "effect": "+2 Живучесть", "price": 400},
    ],
    "other": [
        {"id": "scroll_exp", "name": "📜 Свиток опыта", "effect": "+50 Опыта", "price": 500},
    ]
}

SPELLS = {
    5: [
        {"id": "fire_arrow", "name": "🔥 Стрела Огня", "effect": "+5 Маг.АТК", "cost": 2000},
        {"id": "heal", "name": "🌿 Лечение", "effect": "+20 HP", "cost": 1000},
        {"id": "barrier", "name": "🛡️ Барьер", "effect": "+5 Физ.Защ", "cost": 2000},
    ],
    15: [
        {"id": "fireball", "name": "🔥 Огненный Шар", "effect": "+15 Маг.АТК", "cost": 5000},
        {"id": "mass_heal", "name": "🌿 Массовое Лечение", "effect": "+60 HP", "cost": 2000},
    ],
}

MONSTERS = {
    "weak": [
        {"name": "🐀 Крыса", "hp": 15, "phys_atk": 3, "phys_def": 1, "evasion": 3, "exp": 20, "gold": 10},
        {"name": "🕷️ Паук", "hp": 20, "phys_atk": 5, "phys_def": 2, "evasion": 5, "exp": 30, "gold": 15},
        {"name": "🦇 Летучая мышь", "hp": 12, "phys_atk": 4, "phys_def": 1, "evasion": 8, "exp": 25, "gold": 12},
        {"name": "🧟 Зомби", "hp": 25, "phys_atk": 6, "phys_def": 3, "evasion": 2, "exp": 35, "gold": 18},
        {"name": "👺 Гоблин", "hp": 18, "phys_atk": 5, "phys_def": 2, "evasion": 6, "exp": 40, "gold": 20},
    ],
    "medium": [
        {"name": "🐺 Волк-оборотень", "hp": 40, "phys_atk": 10, "phys_def": 4, "evasion": 7, "exp": 70, "gold": 40},
        {"name": "🧛 Вампир", "hp": 35, "phys_atk": 8, "phys_def": 3, "evasion": 6, "exp": 80, "gold": 50},
        {"name": "👹 Орк-воин", "hp": 50, "phys_atk": 12, "phys_def": 6, "evasion": 4, "exp": 90, "gold": 55},
    ],
    "strong": [
        {"name": "🐉 Молодой дракон", "hp": 80, "phys_atk": 20, "phys_def": 10, "evasion": 10, "exp": 200, "gold": 150},
        {"name": "💀 Рыцарь смерти", "hp": 70, "phys_atk": 18, "phys_def": 12, "evasion": 6, "exp": 220, "gold": 180},
    ],
    "bosses": [
        {"name": "👹 ВОЖДЬ ОРКОВ", "hp": 200, "phys_atk": 45, "phys_def": 30, "evasion": 10, "exp": 1000, "gold": 800},
        {"name": "🧛 КОРОЛЬ ВАМПИРОВ", "hp": 180, "phys_atk": 35, "phys_def": 25, "evasion": 15, "exp": 1100, "gold": 900},
    ],
    "titan": {
        "name": "👑 ТИТАН ЭЛДРОН", "hp": 500, "phys_atk": 60, "phys_def": 40, "evasion": 20, "exp": 5000, "gold": 3000
    }
}

CARDS = {
    "red": ["👹 Появился монстр!", "🐺 На вас напали!", "🧟 Зомби атакует!"],
    "yellow": ["📜 Задание: Принеси 5 шкур. Награда: 100💰", "🗝️ Найди артефакт!"],
    "green": ["✨ Бафф: +10 ко всем статам!", "🌿 Лечение: +30 HP"],
    "black": ["☠️ Дебафф: -10 к защите", "🩸 Кровотечение: -5 HP/ход"],
}

# ==================== КЛАВИАТУРЫ ====================
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой персонаж", callback_data="my_character")],
        [InlineKeyboardButton(text="⭐️ Навыки", callback_data="skills")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton(text="🏪 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="⚔️ Бой", callback_data="battle_menu")],
        [InlineKeyboardButton(text="🃏 Карточки", callback_data="cards_menu")],
        [InlineKeyboardButton(text="📜 Лог", callback_data="logs")],
        [InlineKeyboardButton(text="🔮 Башня Магии", callback_data="magic_tower")],
    ])

def race_kb():
    kb = [[InlineKeyboardButton(text=f"{RACES[r]['name']} {RACES[r]['bonus']}", callback_data=f"race_{r}")] for r in RACES]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def class_kb():
    kb = [[InlineKeyboardButton(text=f"{CLASSES[c]['name']} {CLASSES[c]['bonus']}", callback_data=f"class_{c}")] for c in CLASSES]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_race")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def skills_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="+1 💪 Сила = ⚔️ Физ.АТК +4", callback_data="skill_strength")],
        [InlineKeyboardButton(text="+1 ⚡ Ловкость = ⚡ Скр.АТК +8", callback_data="skill_agility")],
        [InlineKeyboardButton(text="+1 ❤️ Живучесть = ❤️ HP +10", callback_data="skill_vitality")],
        [InlineKeyboardButton(text="+1 🧠 Интеллект = 🔮 Маг.АТК +4", callback_data="skill_intelligence")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def inventory_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Зелья", callback_data="inv_potions")],
        [InlineKeyboardButton(text="⚔️ Оружие", callback_data="inv_weapons")],
        [InlineKeyboardButton(text="🛡️ Экипировка", callback_data="inv_armor")],
        [InlineKeyboardButton(text="📿 Бижутерия", callback_data="inv_accessories")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def shop_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Зелья", callback_data="shop_potions")],
        [InlineKeyboardButton(text="⚔️ Оружие", callback_data="shop_weapons")],
        [InlineKeyboardButton(text="🛡️ Экипировка", callback_data="shop_armor")],
        [InlineKeyboardButton(text="📿 Бижутерия", callback_data="shop_accessories")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def battle_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👹 Герой vs Монстр", callback_data="battle_pve")],
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
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Красная", callback_data="card_red")],
        [InlineKeyboardButton(text="🟡 Жёлтая", callback_data="card_yellow")],
        [InlineKeyboardButton(text="🟢 Зелёная", callback_data="card_green")],
        [InlineKeyboardButton(text="⚫ Чёрная", callback_data="card_black")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def battle_action_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атака", callback_data="battle_attack")],
        [InlineKeyboardButton(text="🧪 Зелье", callback_data="battle_potion")],
        [InlineKeyboardButton(text="🏳️ Сдаться", callback_data="battle_surrender")],
    ])

def magic_levels_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Уровень 5", callback_data="magic_5")],
        [InlineKeyboardButton(text="📊 Уровень 15", callback_data="magic_15")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

# ==================== ХЕНДЛЕРЫ ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    player = db.get_player(message.from_user.id)
    if player:
        await message.answer(f"🎮 Добро пожаловать, {player['name']}!", reply_markup=main_menu_kb(), parse_mode="HTML")
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
    await callback.message.edit_text(f"✅ Раса: {RACES[race]['name']}\n\nВыбери класс:", reply_markup=class_kb(), parse_mode="HTML")
    await state.set_state(CharacterCreation.class_type)

@dp.callback_query(CharacterCreation.class_type, F.data.startswith("class_"))
async def set_class(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    class_type = callback.data.split("_")[1]
    db.create_player(callback.from_user.id, callback.from_user.username or "Hero", data["name"], data["race"], class_type)
    await state.clear()
    await callback.message.edit_text(f"🎉 Герой создан!\n\n👤 {data['name']} | {RACES[data['race']]['name']} | {CLASSES[class_type]['name']}", reply_markup=main_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "my_character")
async def show_character(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    text = f"👤 <b>{player['name']}</b>\n❤️ HP: {player['hp']}/{player['max_hp']}\n💰 Золото: {player['gold']}\n⚔️ Физ.АТК: {player['phys_atk']}\n⭐️ Очки навыков: {player['skill_points']}"
    await callback.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "skills")
async def show_skills(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    await callback.message.edit_text(f"⭐️ Навыки\n\nОчки: {player['skill_points']}", reply_markup=skills_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("skill_"))
async def upgrade_skill(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player or player["skill_points"] < 1:
        await callback.answer("❌ Недостаточно очков!", show_alert=True)
        return
    skill = callback.data.split("_")[1]
    updates = {"skill_points": player["skill_points"] - 1}
    if skill == "strength": updates.update({"strength": player["strength"]+1, "phys_atk": player["phys_atk"]+4})
    elif skill == "agility": updates.update({"agility": player["agility"]+1, "stealth_atk": player["stealth_atk"]+8, "evasion": player["evasion"]+3})
    elif skill == "vitality": updates.update({"vitality": player["vitality"]+1, "max_hp": player["max_hp"]+10, "hp": player["hp"]+10, "phys_def": player["phys_def"]+1, "magic_def": player["magic_def"]+1})
    elif skill == "intelligence": updates.update({"intelligence": player["intelligence"]+1, "max_mp": player["max_mp"]+3, "mp": player["mp"]+3, "magic_atk": player["magic_atk"]+4})
    db.update_player(callback.from_user.id, **updates)
    await callback.answer(f"✅ {skill} прокачан!", show_alert=True)
    await show_skills(callback)

@dp.callback_query(F.data == "inventory")
async def show_inventory(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    inv = player["inventory"]
    text = "🎒 Инвентарь\n\n" + ("\n".join([f"• {item_id} x{count}" for item_id, count in inv.items()]) if inv else "• Пусто")
    await callback.message.edit_text(text, reply_markup=inventory_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    await callback.message.edit_text("🏪 Магазин\n\nВыбери категорию:", reply_markup=shop_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("shop_"))
async def show_shop_category(callback: types.CallbackQuery):
    cat_map = {"shop_potions": "potions", "shop_weapons": "weapons", "shop_armor": "armor", "shop_accessories": "accessories"}
    category = cat_map.get(callback.data, "potions")
    items = SHOP_ITEMS.get(category, [])
    kb = [[InlineKeyboardButton(text=f"{item['name']} 💰{item['price']}", callback_data=f"buy_{item['id']}")] for item in items]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop")])
    await callback.message.edit_text(f"🏪 {category.title()}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_item(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    item_id = callback.data.split("_")[1]
    item = next((i for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), None)
    if not item or player["gold"] < item["price"]:
        await callback.answer("❌ Недостаточно золота!", show_alert=True)
        return
    db.update_player(callback.from_user.id, gold=player["gold"] - item["price"])
    inv = player["inventory"]
    inv[item_id] = inv.get(item_id, 0) + 1
    db.update_player(callback.from_user.id, inventory=inv)
    await callback.answer(f"✅ Куплено: {item['name']}!", show_alert=True)
    await show_shop_category(callback)

@dp.callback_query(F.data == "battle_menu")
async def battle_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("⚔️ Бой", reply_markup=battle_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "battle_pve")
async def select_monster(callback: types.CallbackQuery):
    await callback.message.edit_text("👹 Выбери сложность", reply_markup=pve_monsters_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("monster_"))
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    tier = callback.data.split("_")[1]
    monster = MONSTERS["titan"] if tier == "titan" else random.choice(MONSTERS.get(tier, MONSTERS["weak"]))
    await state.update_data(battle={"player": player, "enemy": monster, "enemy_hp": monster["hp"]})
    await callback.message.edit_text(f"⚔️ БОЙ!\n\n👤 {player['name']} ❤️{player['hp']}\n🆚\n👹 {monster['name']} ❤️{monster['hp']}\n\n<i>Нажми ⚔️ Атака:</i>", reply_markup=battle_action_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("battle_"))
async def battle_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    data = await state.get_data()
    battle = data.get("battle", {})
    if not battle:
        await callback.answer("❌ Начни бой сначала", show_alert=True)
        return
    player, enemy, enemy_hp = battle["player"], battle["enemy"], battle["enemy_hp"]
    
    if action == "surrender":
        db.update_player(callback.from_user.id, gold=0, hp=player["max_hp"])
        await callback.message.edit_text("🏳️ Сдался. 💰 Золото потеряно. ❤️ HP восстановлено.", reply_markup=main_menu_kb(), parse_mode="HTML")
        await state.clear()
        return
    
    if action == "attack":
        player_dmg = max(1, player["phys_atk"] - enemy["phys_def"] + random.randint(1, 20))
        enemy_hp -= player_dmg
        if enemy_hp <= 0:
            db.update_player(callback.from_user.id, exp=player["exp"]+enemy["exp"], gold=player["gold"]+enemy["gold"])
            await callback.message.edit_text(f"🏆 ПОБЕДА!\n✨ +{enemy['exp']} опыта\n💰 +{enemy['gold']} золота", reply_markup=main_menu_kb(), parse_mode="HTML")
            await state.clear()
            return
        enemy_dmg = max(1, enemy["phys_atk"] - player["phys_def"] + random.randint(1, 20))
        new_hp = max(0, player["hp"] - enemy_dmg)
        if new_hp <= 0:
            db.update_player(callback.from_user.id, gold=0, hp=player["max_hp"])
            await callback.message.edit_text("💀 ПОРАЖЕНИЕ!\n💰 Золото потеряно.\n❤️ HP восстановлено.", reply_markup=main_menu_kb(), parse_mode="HTML")
            await state.clear()
            return
        battle["enemy_hp"], battle["player"]["hp"] = enemy_hp, new_hp
        await state.update_data(battle=battle)
        await callback.message.edit_text(f"⚔️ Ты: -{player_dmg} | Враг: -{enemy_dmg}\n👤 {new_hp} | 👹 {enemy_hp}", reply_markup=battle_action_kb(), parse_mode="HTML")
        return
    
    if action == "potion":
        inv = player.get("inventory", {})
        if "hp_small" not in inv or inv["hp_small"] < 1:
            await callback.answer("❌ Нет зелий!", show_alert=True)
            return
        new_hp = min(player["max_hp"], player["hp"] + 30)
        inv["hp_small"] -= 1
        db.update_player(callback.from_user.id, hp=new_hp, inventory=inv)
        await callback.answer(f"🧪 +30 HP! ❤️ {new_hp}", show_alert=True)
        return

@dp.callback_query(F.data == "cards_menu")
async def cards_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("🃏 Карточки\n\nВыбери тип:", reply_markup=cards_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("card_"))
async def draw_card(callback: types.CallbackQuery):
    card_type = callback.data.split("_")[1]
    text = random.choice(CARDS[card_type])
    colors = {"red": "🔴", "yellow": "🟡", "green": "🟢", "black": "⚫"}
    await callback.message.edit_text(f"{colors[card_type]} {text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Ещё", callback_data=f"card_{card_type}")], [InlineKeyboardButton(text="🔙 Назад", callback_data="cards_menu")]]), parse_mode="HTML")

@dp.callback_query(F.data == "logs")
async def show_logs(callback: types.CallbackQuery):
    logs = db.get_logs(callback.from_user.id)
    text = "📜 Лог\n\n" + "\n".join([f"• {l['action']}: {l['details']}" for l in logs[:10]]) if logs else "• Пусто"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]), parse_mode="HTML")

@dp.callback_query(F.data == "magic_tower")
async def magic_tower(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Создай персонажа!", show_alert=True)
        return
    await callback.message.edit_text(f"🔮 Башня Магии\n\nУровень: {player['level']}\n💰 {player['gold']}", reply_markup=magic_levels_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("magic_"))
async def show_spells(callback: types.CallbackQuery):
    level = int(callback.data.split("_")[1])
    player = db.get_player(callback.from_user.id)
    if player["level"] < level:
        await callback.answer(f"❌ Нужен уровень {level}!", show_alert=True)
        return
    spells = SPELLS.get(level, [])
    kb = [[InlineKeyboardButton(text=f"{s['name']} 💰{s['cost']}", callback_data=f"spell_{level}_{s['id']}")] for s in spells]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="magic_tower")])
    await callback.message.edit_text(f"🔮 Уровень {level}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("spell_"))
async def learn_spell(callback: types.CallbackQuery):
    parts = callback.data.split("_")
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
    await callback.message.edit_text("🌑 Введи имя (3-30 символов):", parse_mode="HTML")
    await state.set_state(CharacterCreation.name)

@dp.callback_query(F.data == "back_to_race")
async def back_race(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выбери расу:", reply_markup=race_kb())
    await state.set_state(CharacterCreation.race)

@dp.callback_query(F.data == "main_menu")
async def back_main(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if player:
        await callback.message.edit_text(f"🎮 {player['name']}", reply_markup=main_menu_kb(), parse_mode="HTML")
    else:
        await callback.message.edit_text("🌑 /start для начала", parse_mode="HTML")

# ==================== WEBHOOK ЗАПУСК ====================
async def on_startup(app):
    """Устанавливает webhook при запуске"""
    webhook_url = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RENDER_EXTERNAL_URL")
    if webhook_url:
        webhook_url = webhook_url.replace("http://", "https://").rstrip("/")
        await bot.set_webhook(f"{webhook_url}/webhook", allowed_updates=dp.resolve_used_update_types())
        logging.info(f"✅ Webhook установлен: {webhook_url}/webhook")

async def on_shutdown(app):
    """Удаляет webhook при остановке"""
    await bot.delete_webhook()
    await bot.session.close()
    logging.info("✅ Webhook удалён, сессия закрыта")

async def webhook_handler(request):
    """Обрабатывает входящие обновления от Telegram"""
    try:
        update = types.Update(**await request.json())
        await dp.feed_update(bot, update)
        return web.Response()
    except Exception as e:
        logging.error(f"❌ Ошибка webhook: {e}")
        return web.Response(status=400)

def create_app():
    """Создаёт aiohttp приложение для webhook"""
    app = web.Application()
    app.router.add_post("/webhook", webhook_handler)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

# Точка входа
def main():
    app = create_app()
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()
