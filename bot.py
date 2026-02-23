import random
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN
import database as db

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== СОСТОЯНИЯ (FSM) ====================

class CharacterCreation(StatesGroup):
    name = State()
    race = State()
    class_type = State()

class BattleState(StatesGroup):
    player_dice = State()

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
    "paladin": {"name": "🛡️ Паладин", "bonus": "+1 Сила, +1 Инт", "magic": "✨ Святой свет: Лечение +20 HP"},
    "necromancer": {"name": "💀 Некромант", "bonus": "+1 Инт, +1 Жив", "magic": "☠️ Поднять скелета: Призыв"}
}

SHOP_ITEMS = {
    "potions": [
        {"id": "hp_small", "name": "🧪 Малое зелье HP", "effect": "+30 HP", "price": 50, "type": "heal", "value": 30},
        {"id": "hp_medium", "name": "🧪 Среднее зелье HP", "effect": "+60 HP", "price": 100, "type": "heal", "value": 60},
        {"id": "hp_large", "name": "🧪 Большое зелье HP", "effect": "+100 HP", "price": 150, "type": "heal", "value": 100},
        {"id": "mp_small", "name": "🧪 Малое зелье MP", "effect": "+30 MP", "price": 50, "type": "mana", "value": 30},
        {"id": "mp_medium", "name": "🧪 Среднее зелье MP", "effect": "+60 MP", "price": 100, "type": "mana", "value": 60},
        {"id": "mp_large", "name": "🧪 Большое зелье MP", "effect": "+100 MP", "price": 150, "type": "mana", "value": 100},
    ],
    "weapons": [
        {"id": "sword_apprentice", "name": "⚔️ Меч Ученика", "effect": "+1 Сила", "price": 150, "stat": "strength", "value": 1},
        {"id": "shield_apprentice", "name": "🛡️ Щит Ученика", "effect": "+1 Живучесть", "price": 150, "stat": "vitality", "value": 1},
        {"id": "bow_apprentice", "name": "🏹 Лук Ученика", "effect": "+1 Ловкость", "price": 150, "stat": "agility", "value": 1},
        {"id": "arrows_apprentice", "name": "🏹 Стрелы Ученика", "effect": "+1 Ловкость", "price": 150, "stat": "agility", "value": 1},
        {"id": "staff_apprentice", "name": "🔮 Посох Ученика", "effect": "+1 Интеллект", "price": 150, "stat": "intelligence", "value": 1},
        {"id": "orb_apprentice", "name": "🔮 Сфера Ученика", "effect": "+1 Интеллект", "price": 150, "stat": "intelligence", "value": 1},
    ],
    "armor": [
        {"id": "helm_apprentice", "name": "⛑️ Шлем Ученика", "effect": "+1 Живучесть", "price": 200, "stat": "vitality", "value": 1},
        {"id": "armor_apprentice", "name": "🛡️ Броня Ученика", "effect": "+1 Живучесть", "price": 200, "stat": "vitality", "value": 1},
        {"id": "pants_apprentice", "name": "👖 Штаны Ученика", "effect": "+1 Ловкость", "price": 200, "stat": "agility", "value": 1},
        {"id": "boots_apprentice", "name": "👢 Ботинки Ученика", "effect": "+1 Ловкость", "price": 200, "stat": "agility", "value": 1},
        {"id": "arms_apprentice", "name": "💪 Руки Ученика", "effect": "+1 Сила", "price": 200, "stat": "strength", "value": 1},
        {"id": "gloves_apprentice", "name": "🧤 Перчатки Ученика", "effect": "+1 Сила", "price": 200, "stat": "strength", "value": 1},
    ],
    "accessories": [
        {"id": "amulet_agility", "name": "📿 Амулет Ловкости", "effect": "+2 Ловкость", "price": 400, "stat": "agility", "value": 2},
        {"id": "ring_protection", "name": "💍 Кольцо Защиты", "effect": "+2 Живучесть", "price": 400, "stat": "vitality", "value": 2},
        {"id": "chain_strength", "name": "⛓️ Цепь Силы", "effect": "+2 Сила", "price": 400, "stat": "strength", "value": 2},
    ],
    "other": [
        {"id": "scroll_exp", "name": "📜 Свиток опыта", "effect": "+50 Опыта", "price": 500, "type": "exp", "value": 50},
    ]
}

SPELLS = {
    5: [
        {"id": "fire_arrow", "name": "🔥 Стрела Огня", "effect": "+5 Маг.АТК", "cost": 2000, "stat": "magic_atk", "value": 5},
        {"id": "ice_shield", "name": "❄️ Ледяной Щит", "effect": "+5 Маг.Защ", "cost": 2000, "stat": "magic_def", "value": 5},
        {"id": "heal", "name": "🌿 Лечение", "effect": "+20 HP", "cost": 1000, "type": "heal", "value": 20},
        {"id": "sharpen", "name": "🗡️ Заточка", "effect": "+5 Физ.АТК", "cost": 2000, "stat": "phys_atk", "value": 5},
        {"id": "barrier", "name": "🛡️ Барьер", "effect": "+5 Физ.Защ", "cost": 2000, "stat": "phys_def", "value": 5},
    ],
    15: [
        {"id": "fireball", "name": "🔥 Огненный Шар", "effect": "+15 Маг.АТК", "cost": 5000, "stat": "magic_atk", "value": 15},
        {"id": "ice_wall", "name": "❄️ Ледяная Стена", "effect": "+15 Маг.Защ", "cost": 5000, "stat": "magic_def", "value": 15},
        {"id": "mass_heal", "name": "🌿 Массовое Лечение", "effect": "+60 HP", "cost": 2000, "type": "heal", "value": 60},
        {"id": "sharp_blade", "name": "🗡️ Острое Лезвие", "effect": "+10 Физ.АТК", "cost": 5000, "stat": "phys_atk", "value": 10},
        {"id": "iron_skin", "name": "🛡️ Железная Кожа", "effect": "+10 Физ.Защ", "cost": 5000, "stat": "phys_def", "value": 10},
    ],
    30: [
        {"id": "hellfire", "name": "🔥 Адское Пламя", "effect": "+30 Маг.АТК", "cost": 9000, "stat": "magic_atk", "value": 30},
        {"id": "permafrost", "name": "❄️ Вечная Мерзлота", "effect": "+30 Маг.Защ", "cost": 9000, "stat": "magic_def", "value": 30},
        {"id": "resurrect", "name": "🌿 Воскрешение", "effect": "+120 HP", "cost": 4000, "type": "heal", "value": 120},
        {"id": "dragonslayer", "name": "🗡️ Убийца Драконов", "effect": "+25 Физ.АТК", "cost": 9000, "stat": "phys_atk", "value": 25},
        {"id": "impervious", "name": "🛡️ Непробиваемость", "effect": "+25 Физ.Защ", "cost": 9000, "stat": "phys_def", "value": 25},
    ],
    50: [
        {"id": "volcano", "name": "🔥 Извержение Вулкана", "effect": "+50 Маг.АТК", "cost": 17000, "stat": "magic_atk", "value": 50},
        {"id": "ice_age", "name": "❄️ Ледниковый Период", "effect": "+50 Маг.Защ", "cost": 17000, "stat": "magic_def", "value": 50},
        {"id": "phoenix", "name": "🌿 Феникс", "effect": "+250 HP", "cost": 8000, "type": "heal", "value": 250},
        {"id": "destroyer", "name": "🗡️ Разрушитель", "effect": "+45 Физ.АТК", "cost": 17000, "stat": "phys_atk", "value": 45},
        {"id": "absolute_defense", "name": "🛡️ Абсолютная Защита", "effect": "+45 Физ.Защ", "cost": 17000, "stat": "phys_def", "value": 45},
    ],
    100: [
        {"id": "armageddon", "name": "🔥 Конец Света", "effect": "+100 Маг.АТК", "cost": 33000, "stat": "magic_atk", "value": 100},
        {"id": "eternal_winter", "name": "❄️ Вечная Зима", "effect": "+100 Маг.Защ", "cost": 33000, "stat": "magic_def", "value": 100},
        {"id": "immortality", "name": "🌿 Бессмертие", "effect": "+500 HP", "cost": 15000, "type": "heal", "value": 500},
        {"id": "worldslayer", "name": "🗡️ Убийца Миров", "effect": "+100 Физ.АТК", "cost": 33000, "stat": "phys_atk", "value": 100},
        {"id": "gods_shield", "name": "🛡️ Щит Богов", "effect": "+100 Физ.Защ", "cost": 33000, "stat": "phys_def", "value": 100},
    ]
}

MONSTERS = {
    "weak": [
        {"name": "🐀 Крыса-мутант", "hp": 15, "phys_atk": 3, "magic_atk": 0, "phys_def": 1, "magic_def": 1, "evasion": 3, "exp": 20, "gold": 10},
        {"name": "🕷️ Гигантский паук", "hp": 20, "phys_atk": 5, "magic_atk": 0, "phys_def": 2, "magic_def": 1, "evasion": 5, "exp": 30, "gold": 15},
        {"name": "🦇 Летучая мышь", "hp": 12, "phys_atk": 4, "magic_atk": 2, "phys_def": 1, "magic_def": 2, "evasion": 8, "exp": 25, "gold": 12},
        {"name": "🧟 Слабый зомби", "hp": 25, "phys_atk": 6, "magic_atk": 0, "phys_def": 3, "magic_def": 1, "evasion": 2, "exp": 35, "gold": 18},
        {"name": "👺 Гоблин-разбойник", "hp": 18, "phys_atk": 5, "magic_atk": 3, "phys_def": 2, "magic_def": 2, "evasion": 6, "exp": 40, "gold": 20},
    ],
    "medium": [
        {"name": "🐺 Волк-оборотень", "hp": 40, "phys_atk": 10, "magic_atk": 0, "phys_def": 4, "magic_def": 3, "evasion": 7, "exp": 70, "gold": 40},
        {"name": "🧛 Вампир-новичок", "hp": 35, "phys_atk": 8, "magic_atk": 8, "phys_def": 3, "magic_def": 5, "evasion": 6, "exp": 80, "gold": 50},
        {"name": "👹 Орк-воин", "hp": 50, "phys_atk": 12, "magic_atk": 0, "phys_def": 6, "magic_def": 2, "evasion": 4, "exp": 90, "gold": 55},
        {"name": "🧙 Тёмный ученик", "hp": 30, "phys_atk": 5, "magic_atk": 15, "phys_def": 2, "magic_def": 8, "evasion": 5, "exp": 85, "gold": 45},
        {"name": "🦂 Скорпион-убийца", "hp": 45, "phys_atk": 11, "magic_atk": 5, "phys_def": 5, "magic_def": 4, "evasion": 8, "exp": 95, "gold": 60},
    ],
    "strong": [
        {"name": "🐉 Молодой дракон", "hp": 80, "phys_atk": 20, "magic_atk": 15, "phys_def": 10, "magic_def": 10, "evasion": 10, "exp": 200, "gold": 150},
        {"name": "💀 Рыцарь смерти", "hp": 70, "phys_atk": 18, "magic_atk": 12, "phys_def": 12, "magic_def": 8, "evasion": 6, "exp": 220, "gold": 180},
        {"name": "🔮 Тёмный маг", "hp": 50, "phys_atk": 8, "magic_atk": 25, "phys_def": 5, "magic_def": 15, "evasion": 8, "exp": 210, "gold": 160},
        {"name": "🦁 Мантикора", "hp": 75, "phys_atk": 22, "magic_atk": 10, "phys_def": 8, "magic_def": 6, "evasion": 12, "exp": 230, "gold": 170},
        {"name": "👿 Демон-искуситель", "hp": 60, "phys_atk": 15, "magic_atk": 20, "phys_def": 7, "magic_def": 12, "evasion": 10, "exp": 240, "gold": 190},
    ],
    "very_strong": [
        {"name": "🐉 Древний дракон", "hp": 150, "phys_atk": 35, "magic_atk": 30, "phys_def": 20, "magic_def": 20, "evasion": 15, "exp": 500, "gold": 400},
        {"name": "👑 Лич-повелитель", "hp": 120, "phys_atk": 25, "magic_atk": 40, "phys_def": 15, "magic_def": 25, "evasion": 12, "exp": 550, "gold": 450},
        {"name": "🔥 Повелитель демонов", "hp": 140, "phys_atk": 30, "magic_atk": 35, "phys_def": 18, "magic_def": 22, "evasion": 14, "exp": 520, "gold": 420},
        {"name": "🌑 Тень Эльдрона", "hp": 100, "phys_atk": 20, "magic_atk": 45, "phys_def": 10, "magic_def": 30, "evasion": 20, "exp": 580, "gold": 480},
        {"name": "⚡ Громовой гигант", "hp": 160, "phys_atk": 40, "magic_atk": 15, "phys_def": 25, "magic_def": 15, "evasion": 8, "exp": 600, "gold": 500},
    ],
    "bosses": [
        {"name": "👹 ВОЖДЬ ОРКОВ ГРОМ", "hp": 200, "phys_atk": 45, "magic_atk": 20, "phys_def": 30, "magic_def": 20, "evasion": 10, "exp": 1000, "gold": 800},
        {"name": "🧛 КОРОЛЬ ВАМПИРОВ", "hp": 180, "phys_atk": 35, "magic_atk": 40, "phys_def": 25, "magic_def": 30, "evasion": 15, "exp": 1100, "gold": 900},
        {"name": "🔮 АРХИМАГ ТЬМЫ", "hp": 150, "phys_atk": 20, "magic_atk": 55, "phys_def": 20, "magic_def": 40, "evasion": 18, "exp": 1200, "gold": 1000},
    ],
    "titan": {
        "name": "👑 ТИТАН ЭЛДРОН - ФИНАЛЬНЫЙ БОСС",
        "hp": 500, "phys_atk": 60, "magic_atk": 60, "phys_def": 40, "magic_def": 40, "evasion": 20,
        "exp": 5000, "gold": 3000
    }
}

CARDS = {
    "red": [
        "👹 Появился монстр: Гоблин-разбойник!",
        "🐺 На вас напал Волк-оборотень!",
        "🧟 Из тени вышел Зомби-воин!",
        "🕷️ Гигантский паук преградил путь!",
        "🦇 Стая летучих мышей атакует!",
    ],
    "yellow": [
        "📜 Задание: Принеси 5 шкур волка. Награда: 100 💰, 50 ✨",
        "🗝️ Найди потерянный артефакт в пещере. Награда: 150 💰, 80 ✨",
        "🧙 Помоги магу собрать ингредиенты. Награда: Зелье MP +100 ✨",
        "🏰 Очисти деревню от монстров. Награда: 200 💰, 120 ✨",
        "💎 Найди скрытый сундук. Награда: Случайный предмет!",
    ],
    "green": [
        "✨ Бафф: +10 ко всем характеристикам на 1 бой!",
        "🌿 Лечение: Восстановлено 30 HP",
        "💫 Удача: Следующий бросок кубика +5",
        "🛡️ Защита: +15 к защите на 1 ход",
        "⚡ Скорость: Ходишь первым в следующем бою",
    ],
    "black": [
        "☠️ Дебафф: -10 к защите на 1 бой",
        "🩸 Кровотечение: -5 HP каждый ход (3 хода)",
        "🌀 Замешательство: 30% шанс промахнуться",
        "🔇 Безмолвие: Нельзя использовать магию (2 хода)",
        "🦠 Яд: -10 HP сразу, -3 HP каждый ход (2 хода)",
    ]
}

# ==================== КЛАВИАТУРЫ ====================

def main_menu_kb():
    kb = [
        [InlineKeyboardButton(text="👤 Мой персонаж", callback_data="my_character")],
        [InlineKeyboardButton(text="⭐️ Навыки", callback_data="skills")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton(text="🏪 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="⚔️ Бой", callback_data="battle_menu")],
        [InlineKeyboardButton(text="🃏 Карточки", callback_data="cards_menu")],
        [InlineKeyboardButton(text="📜 Лог", callback_data="logs")],
        [InlineKeyboardButton(text="🔮 Башня Магии", callback_data="magic_tower")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def race_kb():
    kb = [[InlineKeyboardButton(text=f"{RACES[r]['name']} {RACES[r]['bonus']}", callback_data=f"race_{r}")] 
          for r in RACES]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def class_kb():
    kb = [[InlineKeyboardButton(text=f"{CLASSES[c]['name']} {CLASSES[c]['bonus']}", callback_data=f"class_{c}")] 
          for c in CLASSES]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_race")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def skills_kb():
    kb = [
        [InlineKeyboardButton(text="+1 💪 Сила = ⚔️ Физ.АТК +4", callback_data="skill_strength")],
        [InlineKeyboardButton(text="+1 ⚡ Ловкость = ⚡ Скр.АТК +8, 🛡️ Уклон +3", callback_data="skill_agility")],
        [InlineKeyboardButton(text="+1 ❤️ Живучесть = ❤️ HP +10, 🛡️ Ф/М.Защ +1", callback_data="skill_vitality")],
        [InlineKeyboardButton(text="+1 🧠 Интеллект = 💙 MP +3, 🔮 Маг.АТК +4", callback_data="skill_intelligence")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def inventory_kb():
    kb = [
        [InlineKeyboardButton(text="🧪 Зелья", callback_data="inv_potions")],
        [InlineKeyboardButton(text="⚔️ Оружие", callback_data="inv_weapons")],
        [InlineKeyboardButton(text="🛡️ Экипировка", callback_data="inv_armor")],
        [InlineKeyboardButton(text="📿 Бижутерия", callback_data="inv_accessories")],
        [InlineKeyboardButton(text="📦 Разное", callback_data="inv_other")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def shop_kb():
    kb = [
        [InlineKeyboardButton(text="🧪 Зелья", callback_data="shop_potions")],
        [InlineKeyboardButton(text="⚔️ Оружие", callback_data="shop_weapons")],
        [InlineKeyboardButton(text="🛡️ Экипировка", callback_data="shop_armor")],
        [InlineKeyboardButton(text="📿 Бижутерия", callback_data="shop_accessories")],
        [InlineKeyboardButton(text="📦 Разное", callback_data="shop_other")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def battle_menu_kb():
    kb = [
        [InlineKeyboardButton(text="👥 Герой vs Герой", callback_data="battle_pvp")],
        [InlineKeyboardButton(text="👹 Герой vs Монстр", callback_data="battle_pve")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def pve_monsters_kb():
    kb = [
        [InlineKeyboardButton(text="🟢 Слабые монстры", callback_data="monster_weak")],
        [InlineKeyboardButton(text="🟡 Средние монстры", callback_data="monster_medium")],
        [InlineKeyboardButton(text="🔴 Сильные монстры", callback_data="monster_strong")],
        [InlineKeyboardButton(text="🟣 Очень сильные", callback_data="monster_very_strong")],
        [InlineKeyboardButton(text="👑 Боссы", callback_data="monster_bosses")],
        [InlineKeyboardButton(text="💀 ТИТАН (финал)", callback_data="monster_titan")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="battle_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def cards_kb():
    kb = [
        [InlineKeyboardButton(text="🔴 Красная (монстр)", callback_data="card_red")],
        [InlineKeyboardButton(text="🟡 Жёлтая (задание)", callback_data="card_yellow")],
        [InlineKeyboardButton(text="🟢 Зелёная (бафф)", callback_data="card_green")],
        [InlineKeyboardButton(text="⚫ Чёрная (дебафф)", callback_data="card_black")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def battle_action_kb():
    kb = [
        [InlineKeyboardButton(text="⚔️ Физическая атака", callback_data="battle_attack_phys")],
        [InlineKeyboardButton(text="🔮 Магическая атака", callback_data="battle_attack_magic")],
        [InlineKeyboardButton(text="🧪 Использовать зелье", callback_data="battle_use_potion")],
        [InlineKeyboardButton(text="🏳️ Сдаться", callback_data="battle_surrender")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def magic_levels_kb():
    kb = [
        [InlineKeyboardButton(text="📊 Уровень 5", callback_data="magic_5")],
        [InlineKeyboardButton(text="📊 Уровень 15", callback_data="magic_15")],
        [InlineKeyboardButton(text="📊 Уровень 30", callback_data="magic_30")],
        [InlineKeyboardButton(text="📊 Уровень 50", callback_data="magic_50")],
        [InlineKeyboardButton(text="📊 Уровень 100", callback_data="magic_100")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="magic_tower")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb
