"""
📁 bot.py - Основной код бота
ИСПРАВЛЕНО: выбор "одеть/продать" в инвентаре, исправлена продажа
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

# ==================== ДАННЫЕ (сокращено для краткости - используйте предыдущие RACES, CLASSES, SHOP_ITEMS и т.д.) ====================
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
    "paladin": {"name": "🛡️ Паладин", "bonus": "+1 Сила, +1 Инт", "magic": "✨ Святой свет: Лечение +20 HP"},
    "necromancer": {"name": "💀 Некромант", "bonus": "+1 Инт, +1 Жив", "magic": "☠️ Поднять скелета: Призыв"}
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
SHOP_ITEMS = {
    "potions": [
        {"id": "hp_small", "name": "🧪 Малое зелье HP", "type_name": "Зелья", "type_num": "", "effect": "+30 HP", "price": 50, "stat": "hp", "value": 30, "slot": None},
        {"id": "hp_medium", "name": "🧪 Среднее зелье HP", "type_name": "Зелья", "type_num": "", "effect": "+60 HP", "price": 100, "stat": "hp", "value": 60, "slot": None},
        {"id": "hp_large", "name": "🧪 Большое зелье HP", "type_name": "Зелья", "type_num": "", "effect": "+100 HP", "price": 150, "stat": "hp", "value": 100, "slot": None},
        {"id": "mp_small", "name": "🧪 Малое зелье MP", "type_name": "Зелья", "type_num": "", "effect": "+30 MP", "price": 50, "stat": "mp", "value": 30, "slot": None},
        {"id": "mp_medium", "name": "🧪 Среднее зелье MP", "type_name": "Зелья", "type_num": "", "effect": "+60 MP", "price": 100, "stat": "mp", "value": 60, "slot": None},
        {"id": "mp_large", "name": "🧪 Большое зелье MP", "type_name": "Зелья", "type_num": "", "effect": "+100 MP", "price": 150, "stat": "mp", "value": 100, "slot": None},
    ],
    "weapons": [
        {"id": "sword_apprentice", "name": "⚔️ Меч Ученика", "type_name": "Оружия", "type_num": "1", "effect": "+1 Сила", "price": 150, "stat": "strength", "value": 1, "slot": "weapon_1"},
        {"id": "shield_apprentice", "name": "🛡️ Щит Ученика", "type_name": "Оружия", "type_num": "2", "effect": "+1 Живучесть", "price": 150, "stat": "vitality", "value": 1, "slot": "weapon_2"},
        {"id": "bow_apprentice", "name": "🏹 Лук Ученика", "type_name": "Оружия", "type_num": "1", "effect": "+1 Ловкость", "price": 150, "stat": "agility", "value": 1, "slot": "weapon_1"},
        {"id": "arrows_apprentice", "name": "🏹 Стрелы Ученика", "type_name": "Оружия", "type_num": "2", "effect": "+1 Ловкость", "price": 150, "stat": "agility", "value": 1, "slot": "weapon_2"},
        {"id": "staff_apprentice", "name": "🔮 Посох Ученика", "type_name": "Оружия", "type_num": "1", "effect": "+1 Интеллект", "price": 150, "stat": "intelligence", "value": 1, "slot": "weapon_1"},
        {"id": "orb_apprentice", "name": "🔮 Сфера Ученика", "type_name": "Оружия", "type_num": "2", "effect": "+1 Интеллект", "price": 150, "stat": "intelligence", "value": 1, "slot": "weapon_2"},
    ],
    "armor": [
        {"id": "helm_apprentice", "name": "⛑️ Шлем Ученика", "type_name": "Экипировка", "type_num": "1", "effect": "+1 Живучесть", "price": 200, "stat": "vitality", "value": 1, "slot": "armor_1"},
        {"id": "armor_apprentice", "name": "🛡️ Броня Ученика", "type_name": "Экипировка", "type_num": "2", "effect": "+1 Живучесть", "price": 200, "stat": "vitality", "value": 1, "slot": "armor_2"},
        {"id": "pants_apprentice", "name": "👖 Штаны Ученика", "type_name": "Экипировка", "type_num": "3", "effect": "+1 Ловкость", "price": 200, "stat": "agility", "value": 1, "slot": "armor_3"},
        {"id": "boots_apprentice", "name": "👢 Ботинки Ученика", "type_name": "Экипировка", "type_num": "4", "effect": "+1 Ловкость", "price": 200, "stat": "agility", "value": 1, "slot": "armor_4"},
        {"id": "arms_apprentice", "name": "💪 Руки Ученика", "type_name": "Экипировка", "type_num": "5", "effect": "+1 Сила", "price": 200, "stat": "strength", "value": 1, "slot": "armor_5"},
        {"id": "gloves_apprentice", "name": "🧤 Перчатки Ученика", "type_name": "Экипировка", "type_num": "6", "effect": "+1 Сила", "price": 200, "stat": "strength", "value": 1, "slot": "armor_6"},
    ],
    "accessories": [
        {"id": "amulet_agility", "name": "📿 Амулет Ловкости", "type_name": "Аксессуары", "type_num": "1", "effect": "+2 Ловкость", "price": 400, "stat": "agility", "value": 2, "slot": "accessory_1"},
        {"id": "ring_protection", "name": "💍 Кольцо Защиты", "type_name": "Аксессуары", "type_num": "2", "effect": "+2 Живучесть", "price": 400, "stat": "vitality", "value": 2, "slot": "accessory_2"},
        {"id": "chain_strength", "name": "⛓️ Цепь Силы", "type_name": "Аксессуары", "type_num": "3", "effect": "+2 Сила", "price": 400, "stat": "strength", "value": 2, "slot": "accessory_3"},
    ],
    "other": [
        {"id": "scroll_exp", "name": "📜 Свиток опыта", "type_name": "Разное", "type_num": "", "effect": "+50 Опыта", "price": 500, "stat": "exp", "value": 50, "slot": None},
    ]
}
SPELLS = {5: [{"id": "fire", "name": "🔥 Огонь", "effect": "+5 Маг.АТК", "cost": 2000}], 15: [{"id": "fireball", "name": "🔥 Шар", "effect": "+15 Маг.АТК", "cost": 5000}]}
MONSTERS = {"weak": [{"name": "🐀 Крыса", "hp": 15, "phys_atk": 3, "phys_def": 1, "evasion": 3, "exp": 20, "gold": 10}], "medium": [{"name": "🐺 Волк", "hp": 40, "phys_atk": 10, "phys_def": 4, "evasion": 7, "exp": 70, "gold": 40}], "strong": [{"name": "🐉 Дракон", "hp": 80, "phys_atk": 20, "phys_def": 10, "evasion": 10, "exp": 200, "gold": 150}], "bosses": [{"name": "👹 Босс", "hp": 200, "phys_atk": 45, "phys_def": 30, "evasion": 10, "exp": 1000, "gold": 800}], "titan": {"name": "👑 ТИТАН", "hp": 500, "phys_atk": 60, "phys_def": 40, "evasion": 20, "exp": 5000, "gold": 3000}}
CARDS = {"red": ["👹 Монстр!", "🐺 Атака!"], "yellow": ["📜 Задание: +100💰"], "green": ["✨ Бафф: +10 ко всем"], "black": ["☠️ Дебафф: -10 защиты"]}

# ==================== КЛАВИАТУРЫ ====================
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Персонаж", callback_data="my_character")],[InlineKeyboardButton(text="⭐️ Навыки", callback_data="skills")],[InlineKeyboardButton(text="✨ Способности", callback_data="abilities")],[InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],[InlineKeyboardButton(text="🏪 Магазин", callback_data="shop")],[InlineKeyboardButton(text="⚔️ Бой", callback_data="battle_menu")],[InlineKeyboardButton(text="🃏 Карточки", callback_data="cards_menu")],[InlineKeyboardButton(text="📜 Лог", callback_data="logs")],[InlineKeyboardButton(text="🔮 Магия", callback_data="magic_tower")]])
def race_kb():
    kb = [[InlineKeyboardButton(text=f"{RACES[r]['name']} {RACES[r]['bonus']}", callback_data=f"race_{r}")] for r in RACES]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")])
    return InlineKeyboardMarkup(inline_keyboard=kb)
def class_kb():
    kb = [[InlineKeyboardButton(text=f"{CLASSES[c]['name']} {CLASSES[c]['bonus']}", callback_data=f"class_{c}")] for c in CLASSES]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_race")])
    return InlineKeyboardMarkup(inline_keyboard=kb)
def skills_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💪 +1 Сила = ⚔️+4", callback_data="skill_strength")],[InlineKeyboardButton(text="⚡ +1 Ловк = ⚡+8 🛡️+3", callback_data="skill_agility")],[InlineKeyboardButton(text="❤️ +1 Жив = ❤️+10 🛡️+1", callback_data="skill_vitality")],[InlineKeyboardButton(text="🧠 +1 Инт = 💙+3 🔮+4", callback_data="skill_intelligence")],[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]])
def inventory_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧪 Зелья", callback_data="inv_potions")],[InlineKeyboardButton(text="⚔️ Оружие", callback_data="inv_weapons")],[InlineKeyboardButton(text="🛡️ Экипировка", callback_data="inv_armor")],[InlineKeyboardButton(text="📿 Бижутерия", callback_data="inv_accessories")],[InlineKeyboardButton(text="📦 Разное", callback_data="inv_other")],[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]])
def shop_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧪 Зелья", callback_data="shop_potions")],[InlineKeyboardButton(text="⚔️ Оружие", callback_data="shop_weapons")],[InlineKeyboardButton(text="🛡️ Экипировка", callback_data="shop_armor")],[InlineKeyboardButton(text="📿 Бижутерия", callback_data="shop_accessories")],[InlineKeyboardButton(text="📦 Разное", callback_data="shop_other")],[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]])
def battle_menu_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👹 vs Монстр", callback_data="battle_pve")],[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]])
def pve_monsters_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟢 Слабые", callback_data="monster_weak")],[InlineKeyboardButton(text="🟡 Средние", callback_data="monster_medium")],[InlineKeyboardButton(text="🔴 Сильные", callback_data="monster_strong")],[InlineKeyboardButton(text="👑 Боссы", callback_data="monster_bosses")],[InlineKeyboardButton(text="💀 ТИТАН", callback_data="monster_titan")],[InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")]])
def cards_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔴 Красная", callback_data="card_red")],[InlineKeyboardButton(text="🟡 Жёлтая", callback_data="card_yellow")],[InlineKeyboardButton(text="🟢 Зелёная", callback_data="card_green")],[InlineKeyboardButton(text="⚫ Чёрная", callback_data="card_black")],[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]])
def magic_levels_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📊 Уровень 5", callback_data="magic_5")],[InlineKeyboardButton(text="📊 Уровень 15", callback_data="magic_15")],[InlineKeyboardButton(text="🔙 Назад", callback_data="magic_tower")]])

async def edit_safe(message, **kwargs):
    try:
        await message.edit_text(**kwargs)
        return True
    except Exception as e:
        if any(x in str(e).lower() for x in ["message is not modified", "can't be edited", "not found"]): return True
        logger.error(f"❌ {e}")
        raise

# ==================== АДМИН-КОМАНДЫ ====================
@dp.message(Command("gold"))
async def cmd_gold(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: await message.answer("🔒 Только для админа!"); return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("💰 /gold me <сумма> | set <id> <сумма> | add <id> <сумма> | all <сумма>")
        return
    action = parts[1]
    try:
        if action == "me" and len(parts) == 3:
            amount = int(parts[2]); db.add_gold(message.from_user.id, amount); await message.answer(f"✅ +💰{amount}")
        elif action == "set" and len(parts) == 4:
            uid, amount = int(parts[2]), int(parts[3]); db.update_player(uid, gold=amount); await message.answer(f"✅ У {uid} установлено 💰{amount}")
        elif action == "add" and len(parts) == 4:
            uid, amount = int(parts[2]), int(parts[3]); db.add_gold(uid, amount); await message.answer(f"✅ {uid} +💰{amount}")
        elif action == "all" and len(parts) == 3:
            amount = int(parts[2]); db.update_all_players_gold(amount); await message.answer(f"✅ Всем 💰{amount}")
        else: await message.answer("❌ Неверный формат")
    except: await message.answer("❌ Ошибка: числа должны быть числами")

@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: await message.answer("🔒 Только для админа!"); return
    parts = message.text.split()
    if len(parts) != 2: await message.answer("Использование: /reset <user_id>"); return
    try:
        uid = int(parts[1])
        with db.get_connection() as conn:
            c = conn.cursor(); c.execute("DELETE FROM players WHERE user_id = ?", (uid,)); c.execute("DELETE FROM logs WHERE user_id = ?", (uid,)); conn.commit()
        await message.answer(f"✅ Прогресс {uid} сброшен")
    except Exception as e: await message.answer(f"❌ {e}")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: await message.answer("🔒 Только для админа!"); return
    with db.get_connection() as conn:
        c = conn.cursor(); c.execute("SELECT COUNT(*) FROM players"); pc = c.fetchone()[0]; c.execute("SELECT SUM(gold) FROM players"); tg = c.fetchone()[0] or 0
    await message.answer(f"📊 Игроков: {pc}\n💰 Золота: {tg}")

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
    if len(name) < 3 or len(name) > 30: await message.answer("❌ Имя от 3 до 30 символов:"); return
    await state.update_data(name=name)
    await message.answer(f"✅ Имя: {name}\n\nВыбери расу:", reply_markup=race_kb(), parse_mode="HTML")
    await state.set_state(CharacterCreation.race)

@dp.callback_query(CharacterCreation.race, F.data.startswith("race_"))
async def set_race(callback: types.CallbackQuery, state: FSMContext):
    race = callback.data.split("_")[1]; await state.update_data(race=race)
    await edit_safe(callback.message, text=f"✅ Раса: {RACES[race]['name']}\n{RACES[race]['magic']}\n\nВыбери класс:", reply_markup=class_kb(), parse_mode="HTML")
    await state.set_state(CharacterCreation.class_type)

@dp.callback_query(CharacterCreation.class_type, F.data.startswith("class_"))
async def set_class(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data(); class_type = callback.data.split("_")[1]
    db.create_player(callback.from_user.id, callback.from_user.username or "Hero", data["name"], data["race"], class_type); await state.clear()
    rm, cm = RACE_MAGIC.get(data["race"], {}), CLASS_MAGIC.get(class_type, {})
    text = f"🎉 <b>Герой создан!</b>\n\n👤 {data['name']}\n🧬 {RACES[data['race']]['name']} | {CLASSES[class_type]['name']}\n✨ {rm.get('name','')}: {rm.get('description','')}\n⚔️ {cm.get('name','')}: {cm.get('description','')}\n💰 Золото: 5000\n\nТвоё приключение начинается!"
    await edit_safe(callback.message, text=text, reply_markup=main_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "my_character")
async def show_character(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player: await callback.answer("❌ Создай персонажа!", show_alert=True); return
    exp_needed = player["level"] * 100; rm, cm = RACE_MAGIC.get(player["race"], {}), CLASS_MAGIC.get(player["class_type"], {})
    equip_text = ""; slot_names = {"weapon_1": "⚔️ Оружие I", "weapon_2": "🛡️ Оружие II", "armor_1": "⛑️ Шлем", "armor_2": "🛡️ Броня", "armor_3": "👖 Штаны", "armor_4": "👢 Ботинки", "armor_5": "💪 Руки", "armor_6": "🧤 Перчатки", "accessory_1": "📿 Амулет", "accessory_2": "💍 Кольцо", "accessory_3": "⛓️ Цепь"}
    if player["equipment"]:
        for slot, item_id in player["equipment"].items():
            item_name = next((i["name"] for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), item_id)
            equip_text += f"{slot_names.get(slot, slot)}: {item_name}\n"
    else: equip_text = "• Пусто\n"
    magic_info = f"📜 <b>СПОСОБНОСТИ:</b>\n✨ Раса: {rm.get('name','Нет')} - {rm.get('description','')}\n⚔️ Класс: {cm.get('name','Нет')} - {cm.get('description','')} (MP: {cm.get('mp_cost',0)})\n\n"
    text = (f"👤 <b>{player['name']}</b>\n🧬 {RACES[player['race']]['name']} | {CLASSES[player['class_type']]['name']}\n📊 Уровень: {player['level']}\n❤️ HP: {player['hp']}/{player['max_hp']} | 💙 MP: {player['mp']}/{player['max_mp']}\n✨ Опыт: {player['exp']}/{exp_needed} | 💰 Золото: {player['gold']}\n\n"
            f"📊 <b>ХАРАКТЕРИСТИКИ:</b>\n⚔️ Физ.АТК: {player['phys_atk']}\n⚡️ Скр.АТК: {player['stealth_atk']}\n🛡️ Уклон: {player['evasion']}\n🛡️ Физ.Защ: {player['phys_def']}\n🔮 Маг.Защ: {player['magic_def']}\n🔮 Маг.АТК: {player['magic_atk']}\n\n"
            f"📈 <b>НАВЫКИ:</b>\n💪 Сила: {player['strength']}\n❤️ Жив: {player['vitality']}\n⚡️ Ловк: {player['agility']}\n🧠 Инт: {player['intelligence']}\n⭐️ Очки: {player['skill_points']}\n\n{magic_info}🎒 <b>ЭКИПИРОВКА:</b>\n{equip_text}")
    await edit_safe(callback.message, text=text, reply_markup=main_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "skills")
async def show_skills(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player: await callback.answer("❌ Создай персонажа!", show_alert=True); return
    text = f"⭐️ <b>Прокачка</b>\n\n👤 {player['name']} | ⭐️ Очки: <b>{player['skill_points']}</b>\n\n💪 +1 Сила → ⚔️+4\n⚡ +1 Ловк → ⚡+8 🛡️+3\n❤️ +1 Жив → ❤️+10 🛡️+1\n🧠 +1 Инт → 💙+3 🔮+4\n\n<i>Нажми кнопку:</i>"
    await edit_safe(callback.message, text=text, reply_markup=skills_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("skill_"))
async def upgrade_skill(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player or player["skill_points"] < 1: await callback.answer("❌ Недостаточно очков!", show_alert=True); return
    skill = callback.data.split("_")[1]; updates = {"skill_points": player["skill_points"] - 1}; msg = ""
    if skill == "strength": updates.update({"strength": player["strength"]+1, "phys_atk": player["phys_atk"]+4}); msg = "💪 Сила +1 → ⚔️+4"
    elif skill == "agility": updates.update({"agility": player["agility"]+1, "stealth_atk": player["stealth_atk"]+8, "evasion": player["evasion"]+3}); msg = "⚡ Ловкость +1 → ⚡+8 🛡️+3"
    elif skill == "vitality": updates.update({"vitality": player["vitality"]+1, "max_hp": player["max_hp"]+10, "hp": player["hp"]+10, "phys_def": player["phys_def"]+1, "magic_def": player["magic_def"]+1}); msg = "❤️ Живучесть +1 → ❤️+10 🛡️+1"
    elif skill == "intelligence": updates.update({"intelligence": player["intelligence"]+1, "max_mp": player["max_mp"]+3, "mp": player["mp"]+3, "magic_atk": player["magic_atk"]+4}); msg = "🧠 Интеллект +1 → 💙+3 🔮+4"
    db.update_player(callback.from_user.id, **updates); db.add_log(callback.from_user.id, "upgrade_skill", f"{skill} +1")
    await callback.answer(f"✅ {msg}!", show_alert=True); await show_skills(callback)

@dp.callback_query(F.data == "abilities")
async def show_abilities(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player: await callback.answer("❌ Создай персонажа!", show_alert=True); return
    rm, cm = RACE_MAGIC.get(player["race"], {}), CLASS_MAGIC.get(player["class_type"], {}); kb = []
    if cm.get("type") == "active": kb.append([InlineKeyboardButton(text=f"⚔️ {cm['name']} (-{cm['mp_cost']} MP)", callback_data="use_class_magic")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    text = f"✨ <b>СПОСОБНОСТИ</b>\n\n👤 {player['name']} | 💙 MP: {player['mp']}/{player['max_mp']}\n\n📜 <b>РАСА</b> (пассивная)\n{rm.get('name','Нет')}: {rm.get('description','Нет')}\n\n⚔️ <b>КЛАСС</b> (активная)\n{cm.get('name','Нет')}: {cm.get('description','Нет')}\n💰 MP: {cm.get('mp_cost',0)} | ⏱️ {cm.get('duration',0)} ход(а)"
    await edit_safe(callback.message, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data == "inventory")
async def show_inventory(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player: await callback.answer("❌ Создай персонажа!", show_alert=True); return
    inv = player["inventory"]; text = "🎒 Инвентарь\n\n"
    if not inv: text += "• Пусто"
    else:
        for item_id, count in inv.items():
            item_name = next((i["name"] for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), item_id)
            text += f"• {item_name} x{count}\n"
    await edit_safe(callback.message, text=text, reply_markup=inventory_kb(), parse_mode="HTML")

# ==================== 🔧 НОВЫЙ ИНВЕНТАРЬ С ВЫБОРОМ ДЕЙСТВИЯ ====================

@dp.callback_query(F.data.startswith("inv_"))
async def show_inventory_category(callback: types.CallbackQuery):
    """Показывает предметы с кнопками выбора действия"""
    player = db.get_player(callback.from_user.id)
    if not player: await callback.answer("❌ Создай персонажа!", show_alert=True); return
    cat_map = {"inv_potions": "potions", "inv_weapons": "weapons", "inv_armor": "armor", "inv_accessories": "accessories", "inv_other": "other"}
    category = cat_map.get(callback.data, "potions"); inv = player["inventory"]
    items_in_inv = [(item, inv[item["id"]]) for item in SHOP_ITEMS.get(category, []) if item["id"] in inv and inv[item["id"]] > 0]
    kb = []
    for item, count in items_in_inv:
        # Кнопка с выбором действия: Одеть / Продать
        kb.append([InlineKeyboardButton(text=f"🎒 {item['name']} x{count}", callback_data=f"item_select_{item['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="inventory")])
    text = f"🎒 {category.title()}\n\n<i>Нажми на предмет для выбора действия:</i>"
    await edit_safe(callback.message, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("item_select_"))
async def item_action_menu(callback: types.CallbackQuery):
    """Показывает меню выбора: Одеть или Продать"""
    player = db.get_player(callback.from_user.id)
    if not player: await callback.answer("❌ Ошибка!", show_alert=True); return
    item_id = callback.data.split("_", 2)[2]
    item = next((i for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), None)
    if not item: await callback.answer("❌ Предмет не найден!", show_alert=True); return
    count = player["inventory"].get(item_id, 0)
    # Кнопки действий
    kb = []
    if item.get("slot"):  # Можно экипировать только если есть слот
        kb.append([InlineKeyboardButton(text="⚔️ Одеть", callback_data=f"equip_{item_id}")])
    kb.append([InlineKeyboardButton(text=f"💰 Продать за {item['price']//2}💰", callback_data=f"sell_{item_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="inventory")])
    text = f"🎒 {item['name']} x{count}\n\n{item['effect']}\n💰 Цена: {item['price']} | Продажа: {item['price']//2}\n\n<i>Выбери действие:</i>"
    await edit_safe(callback.message, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("equip_"))
async def equip_item(callback: types.CallbackQuery):
    """✅ ИСПРАВЛЕНО: пересчёт всех статов с нуля"""
    player = db.get_player(callback.from_user.id)
    if not player: await callback.answer("❌ Создай персонажа!", show_alert=True); return
    item_id = callback.data.split("_", 1)[1]
    if item_id not in player["inventory"] or player["inventory"][item_id] < 1: await callback.answer("❌ Нет в инвентаре!", show_alert=True); return
    item = next((i for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), None)
    item_slot = item.get("slot") if item else None
    if not item_slot: await callback.answer("❌ Предмет не экипируется!", show_alert=True); return
    # Экипируем
    equipment = player["equipment"]; equipment[item_slot] = item_id
    db.update_player(callback.from_user.id, equipment=equipment)
    # ✅ ПЕРЕРАСЧИТЫВАЕМ ВСЕ статы с нуля
    updated_player = db.get_player(callback.from_user.id)
    new_stats = db.recalc_all_stats(updated_player, SHOP_ITEMS)
    # Обновляем статы в БД
    db.update_player(callback.from_user.id, **{k: new_stats[k] for k in ["strength", "vitality", "agility", "intelligence", "skill_points", "phys_atk", "stealth_atk", "evasion", "phys_def", "magic_def", "magic_atk", "max_hp", "max_mp", "hp", "mp"]})
    db.add_log(callback.from_user.id, "equip_item", f"Надел {item['name']}")
    await callback.answer(f"✅ {item['name']} надето!", show_alert=True)
    await item_action_menu(callback)  # Возвращаемся к меню выбора

@dp.callback_query(F.data.startswith("sell_"))
async def sell_item(callback: types.CallbackQuery):
    """✅ ИСПРАВЛЕНО: корректное удаление предмета"""
    player = db.get_player(callback.from_user.id)
    if not player: await callback.answer("❌ Создай персонажа!", show_alert=True); return
    item_id = callback.data.split("_", 1)[1]
    inv = player["inventory"]
    if item_id not in inv or inv[item_id] < 1: await callback.answer("❌ Нет предмета!", show_alert=True); return
    item = next((i for cat in SHOP_ITEMS.values() for i in cat if i["id"] == item_id), None)
    if not item: await callback.answer("❌ Предмет не найден!", show_alert=True); return
    price = item["price"] // 2
    # ✅ Уменьшаем количество или удаляем
    inv[item_id] -= 1
    if inv[item_id] <= 0:
        del inv[item_id]  # ✅ Удаляем ключ из словаря
    # ✅ Обновляем инвентарь и золото ОДНИМ запросом
    db.update_player(callback.from_user.id, inventory=inv, gold=player["gold"] + price)
    db.add_log(callback.from_user.id, "sell_item", f"Продал {item['name']} за 💰{price}")
    await callback.answer(f"✅ Продано: {item['name']} за 💰{price}!", show_alert=True)
    await show_inventory_category(callback)  # Возвращаемся к списку

@dp.callback_query(F.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    await edit_safe(callback.message, text="🏪 Магазин\n\nВыбери категорию:", reply_markup=shop_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("shop_"))
async def show_shop_category(callback: types.CallbackQuery):
    cat_map = {"shop_potions": "potions", "shop_weapons": "weapons", "shop_armor": "armor", "shop_accessories": "accessories", "shop_other": "other"}
    category = cat_map.get(callback.data, "potions"); items = SHOP_ITEMS.get(category, [])
    kb = [[InlineKeyboardButton(text=f"{item['name']} {item['effect']} 💰{item['price']}", callback_data=f"buy_{category}_{item['id']}")] for item in items]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop")])
    await edit_safe(callback.message, text=f"🏪 {category.title()}\n\n<i>Нажми для покупки:</i>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_item(callback: types.CallbackQuery):
    uid = callback.from_user.id; parts = callback.data.split("_", 2)
    if len(parts) != 3: await callback.answer("❌ Ошибка формата!", show_alert=True); return
    cat, iid = parts[1], parts[2]
    player = db.get_player(uid)
    if not player: await callback.answer("❌ Персонаж не найден!", show_alert=True); return
    item = next((i for i in SHOP_ITEMS.get(cat, []) if i["id"] == iid), None)
    if not item: await callback.answer(f"❌ Предмет не найден: {iid}", show_alert=True); return
    if player["gold"] < item["price"]: await callback.answer(f"❌ Нужно 💰{item['price']}, у вас 💰{player['gold']}", show_alert=True); return
    if not db.spend_gold(uid, item["price"]): await callback.answer("❌ Ошибка списания!", show_alert=True); return
    inv = player.get("inventory", {}); inv[iid] = inv.get(iid, 0) + 1
    db.update_player(uid, inventory=inv); db.add_log(uid, "buy_item", f"Купил {item['name']}")
    await callback.answer(f"✅ Куплено: {item['name']}!", show_alert=True)
    await show_shop_category(callback)

@dp.callback_query(F.data == "battle_menu")
async def battle_menu(callback: types.CallbackQuery):
    await edit_safe(callback.message, text="⚔️ Бой", reply_markup=battle_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "battle_pve")
async def select_monster(callback: types.CallbackQuery):
    await edit_safe(callback.message, text="👹 Сложность", reply_markup=pve_monsters_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "cards_menu")
async def cards_menu(callback: types.CallbackQuery):
    await edit_safe(callback.message, text="🃏 Карточки\n\nВыбери тип:", reply_markup=cards_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("card_"))
async def draw_card(callback: types.CallbackQuery):
    ctype = callback.data.split("_", 1)[1]; text = random.choice(CARDS[ctype]); colors = {"red": "🔴", "yellow": "🟡", "green": "🟢", "black": "⚫"}
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Ещё", callback_data=f"card_{ctype}")], [InlineKeyboardButton(text="🔙 Назад", callback_data="cards_menu")]])
    await edit_safe(callback.message, text=f"{colors[ctype]} {text}", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "logs")
async def show_logs(callback: types.CallbackQuery):
    logs = db.get_logs(callback.from_user.id); text = "📜 Лог\n\n" + ("\n".join([f"• {l['action']}: {l['details']}" for l in logs[:10]]) if logs else "• Пусто")
    await edit_safe(callback.message, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]), parse_mode="HTML")

@dp.callback_query(F.data == "magic_tower")
async def magic_tower(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player: await callback.answer("❌ Создай персонажа!", show_alert=True); return
    await edit_safe(callback.message, text=f"🔮 Башня Магии\n\nУровень: {player['level']}\n💰 {player['gold']}", reply_markup=magic_levels_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("magic_"))
async def show_spells(callback: types.CallbackQuery):
    level = int(callback.data.split("_", 1)[1]); player = db.get_player(callback.from_user.id)
    if player["level"] < level: await callback.answer(f"❌ Нужен уровень {level}!", show_alert=True); return
    spells = SPELLS.get(level, []); kb = [[InlineKeyboardButton(text=f"{s['name']} 💰{s['cost']}", callback_data=f"spell_{level}_{s['id']}")] for s in spells]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="magic_tower")])
    await edit_safe(callback.message, text=f"🔮 Уровень {level}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("spell_"))
async def learn_spell(callback: types.CallbackQuery):
    parts = callback.data.split("_", 2); level, spell_id = int(parts[1]), parts[2]
    player = db.get_player(callback.from_user.id); spell = next((s for s in SPELLS.get(level, []) if s["id"] == spell_id), None)
    if not spell or player["level"] < level or player["gold"] < spell["cost"]: await callback.answer("❌ Недостаточно условий!", show_alert=True); return
    db.update_player(callback.from_user.id, gold=player["gold"] - spell["cost"]); spells = player["spells"]
    if spell_id not in spells: spells.append(spell_id); db.update_player(callback.from_user.id, spells=spells)
    await callback.answer(f"✅ Изучено: {spell['name']}!", show_alert=True)

@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: types.CallbackQuery, state: FSMContext):
    await edit_safe(callback.message, text="🌑 Введи имя (3-30 символов):", parse_mode="HTML"); await state.set_state(CharacterCreation.name)

@dp.callback_query(F.data == "back_to_race")
async def back_race(callback: types.CallbackQuery, state: FSMContext):
    await edit_safe(callback.message, text="Выбери расу:", reply_markup=race_kb()); await state.set_state(CharacterCreation.race)

@dp.callback_query(F.data == "main_menu")
async def back_main(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if player: await edit_safe(callback.message, text=f"🎮 {player['name']}", reply_markup=main_menu_kb(), parse_mode="HTML")
    else: await edit_safe(callback.message, text="🌑 /start для начала", parse_mode="HTML")

# ==================== WEBHOOK ====================
async def on_startup(app):
    url = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RENDER_EXTERNAL_URL")
    if url:
        url = url.replace("http://", "https://").rstrip("/")
        await bot.set_webhook(f"{url}/webhook", allowed_updates=dp.resolve_used_update_types())
        logger.info(f"✅ Webhook: {url}/webhook")

async def on_shutdown(app):
    await bot.delete_webhook(); await bot.session.close()

async def webhook_handler(request):
    try:
        update = types.Update(**await request.json()); await dp.feed_update(bot, update); return web.Response()
    except Exception as e: logger.error(f"❌ Webhook: {e}"); return web.Response(status=400)

def create_app():
    app = web.Application(); app.router.add_post("/webhook", webhook_handler); app.on_startup.append(on_startup); app.on_shutdown.append(on_shutdown); return app

def main():
    app = create_app(); setup_application(app, dp, bot=bot); web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()
