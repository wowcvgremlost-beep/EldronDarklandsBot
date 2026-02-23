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
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==================== ХЕНДЛЕРЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    player = db.get_player(message.from_user.id)
    if player:
        await message.answer(
            f"🎮 Добро пожаловать в <b>Тёмные Земли Эльдрона</b>, {player['name']}!\n\nВыбери действие:",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🌑 <b>ТЁМНЫЕ ЗЕМЛИ ЭЛДРОНА</b> 🌑\n\nСоздай своего героя!\n\n<i>Введи имя (3-30 символов):</i>",
            parse_mode="HTML"
        )
        await state.set_state(CharacterCreation.name)

@dp.message(CharacterCreation.name)
async def set_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3 or len(name) > 30:
        await message.answer("❌ Имя от 3 до 30 символов. Попробуй ещё раз:")
        return
    await state.update_data(name=name)
    await message.answer(f"✅ Имя: <b>{name}</b>\n\nВыбери расу:", reply_markup=race_kb(), parse_mode="HTML")
    await state.set_state(CharacterCreation.race)

@dp.callback_query(CharacterCreation.race, F.data.startswith("race_"))
async def set_race(callback: types.CallbackQuery, state: FSMContext):
    race = callback.data.split("_")[1]
    await state.update_data(race=race)
    await callback.message.edit_text(
        f"✅ Раса: <b>{RACES[race]['name']}</b>\n{RACES[race]['magic']}\n\nВыбери класс:",
        reply_markup=class_kb(),
        parse_mode="HTML"
    )
    await state.set_state(CharacterCreation.class_type)

@dp.callback_query(CharacterCreation.class_type, F.data.startswith("class_"))
async def set_class(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    class_type = callback.data.split("_")[1]
    db.create_player(
        user_id=callback.from_user.id,
        username=callback.from_user.username or "Hero",
        name=data["name"],
        race=data["race"],
        class_type=class_type
    )
    await state.clear()
    await callback.message.edit_text(
        f"🎉 <b>Герой создан!</b>\n\n👤 {data['name']} | {RACES[data['race']]['name']} | {CLASSES[class_type]['name']}\n\nТвоё приключение начинается!",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "my_character")
async def show_character(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала создай персонажа!", show_alert=True)
        return
    exp_needed = player["level"] * 100
    text = (
        f"👤 <b>{player['name']}</b> | {RACES[player['race']]['name']} | {CLASSES[player['class_type']]['name']}\n"
        f"📊 Уровень: {player['level']}\n❤️ HP: {player['hp']}/{player['max_hp']} | 💙 MP: {player['mp']}/{player['max_mp']}\n"
        f"✨ Опыт: {player['exp']}/{exp_needed}\n💰 Золото: {player['gold']}\n\n"
        f"📊 <b>БОЕВЫЕ ХАРАКТЕРИСТИКИ:</b>\n⚔️ Физ.АТК: {player['phys_atk']}\n⚡️ Скр.АТК: {player['stealth_atk']}\n"
        f"🛡️ Уклонение: {player['evasion']}\n🛡️ Физ.Защ: {player['phys_def']}\n🔮 Маг.Защ: {player['magic_def']}\n"
        f"🔮 Маг.АТК: {player['magic_atk']}\n\n📈 <b>НАВЫКИ:</b>\n💪 Сила: {player['strength']}\n❤️ Живучесть: {player['vitality']}\n"
        f"⚡️ Ловкость: {player['agility']}\n🧠 Интеллект: {player['intelligence']}\n⭐️ Очки: {player['skill_points']}"
    )
    await callback.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "skills")
async def show_skills(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала создай персонажа!", show_alert=True)
        return
    await callback.message.edit_text(
        f"⭐️ <b>Прокачка навыков</b>\n\nДоступно очков: {player['skill_points']}",
        reply_markup=skills_kb(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("skill_"))
async def upgrade_skill(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player or player["skill_points"] < 1:
        await callback.answer("❌ Недостаточно очков!", show_alert=True)
        return
    skill = callback.data.split("_")[1]
    updates = {"skill_points": player["skill_points"] - 1}
    if skill == "strength":
        updates["strength"] = player["strength"] + 1
        updates["phys_atk"] = player["phys_atk"] + 4
    elif skill == "agility":
        updates["agility"] = player["agility"] + 1
        updates["stealth_atk"] = player["stealth_atk"] + 8
        updates["evasion"] = player["evasion"] + 3
    elif skill == "vitality":
        updates["vitality"] = player["vitality"] + 1
        updates["max_hp"] = player["max_hp"] + 10
        updates["hp"] = player["hp"] + 10
        updates["phys_def"] = player["phys_def"] + 1
        updates["magic_def"] = player["magic_def"] + 1
    elif skill == "intelligence":
        updates["intelligence"] = player["intelligence"] + 1
        updates["max_mp"] = player["max_mp"] + 3
        updates["mp"] = player["mp"] + 3
        updates["magic_atk"] = player["magic_atk"] + 4
    db.update_player(callback.from_user.id, **updates)
    await callback.answer(f"✅ {skill} прокачан!", show_alert=True)
    await show_skills(callback)

@dp.callback_query(F.data == "inventory")
async def show_inventory(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала создай персонажа!", show_alert=True)
        return
    inv = player["inventory"]
    text = "🎒 <b>Инвентарь</b>\n\n"
    if not inv:
        text += "• Пусто"
    else:
        for item_id, count in inv.items():
            name = "Предмет"
            for cat in SHOP_ITEMS.values():
                for item in cat:
                    if item["id"] == item_id:
                        name = item["name"]
            text += f"• {name} x{count}\n"
    await callback.message.edit_text(text, reply_markup=inventory_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    await callback.message.edit_text("🏪 <b>Магазин</b>\n\nВыбери категорию:", reply_markup=shop_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("shop_"))
async def show_shop_category(callback: types.CallbackQuery):
    category_map = {"shop_potions": "potions", "shop_weapons": "weapons", "shop_armor": "armor", "shop_accessories": "accessories", "shop_other": "other"}
    category = category_map.get(callback.data, "potions")
    items = SHOP_ITEMS.get(category, [])
    kb = []
    for item in items:
        kb.append([InlineKeyboardButton(text=f"{item['name']} 💰{item['price']}", callback_data=f"buy_{item['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop")])
    await callback.message.edit_text(f"🏪 <b>{category.title()}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_item(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    item_id = callback.data.split("_")[1]
    item = None
    for cat in SHOP_ITEMS.values():
        for i in cat:
            if i["id"] == item_id:
                item = i
                break
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
    await callback.message.edit_text("⚔️ <b>Выбери тип боя</b>", reply_markup=battle_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "battle_pve")
async def select_monster(callback: types.CallbackQuery):
    await callback.message.edit_text("👹 <b>Выбери сложность</b>", reply_markup=pve_monsters_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("monster_"))
async def start_pve_battle(callback: types.CallbackQuery, state: FSMContext):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала создай персонажа!", show_alert=True)
        return
    tier = callback.data.split("_")[1]
    if tier == "titan":
        monster = MONSTERS["titan"].copy()
    elif tier in MONSTERS:
        monster = random.choice(MONSTERS[tier]).copy()
    else:
        await callback.answer("❌ Ошибка выбора", show_alert=True)
        return
    battle_data = {"player": player, "enemy": monster, "enemy_hp": monster["hp"]}
    await state.update_data(battle=battle_data)
    await callback.message.edit_text(
        f"⚔️ <b>БОЙ!</b>\n\n👤 {player['name']} ❤️{player['hp']}/{player['max_hp']}\n🆚\n👹 {monster['name']} ❤️{monster['hp']}\n\n<i>Кинь d20 и напиши число (1-20):</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏳️ Сдаться", callback_data="battle_surrender")]]),
        parse_mode="HTML"
    )
    await state.set_state(BattleState.player_dice)

@dp.message(BattleState.player_dice)
async def player_dice_roll(message: types.Message, state: FSMContext):
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
    enemy_dice = random.randint(1, 20)
    player_init = battle["player"]["stealth_atk"] + dice
    enemy_init = battle["enemy"]["evasion"] + enemy_dice
    first = "player" if player_init >= enemy_init else "enemy"
    text = f"🎲 <b>Бросок:</b>\n👤 Ты: {player_init}\n👹 Враг: {enemy_init}\n\n{'✅ Ты первый!' if first == 'player' else '⚠️ Враг первый!'}"
    await state.update_data(player_dice=dice, enemy_dice=enemy_dice, first_turn=first)
    await state.set_state(None)
    await message.answer(text, reply_markup=battle_action_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("battle_"))
async def battle_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    data = await state.get_data()
    battle = data.get("battle", {})
    if not battle:
        await callback.answer("❌ Бой не найден", show_alert=True)
        return
    player = battle["player"]
    enemy = battle["enemy"]
    enemy_hp = battle["enemy_hp"]
    if action == "surrender":
        db.update_player(callback.from_user.id, gold=0, hp=player["max_hp"])
        await callback.message.edit_text("🏳️ Ты сдался. 💰 Золото потеряно. ❤️ HP восстановлено.", reply_markup=main_menu_kb(), parse_mode="HTML")
        await state.clear()
        return
    if action == "attack_phys":
        player_dmg = max(1, player["phys_atk"] - enemy["phys_def"] + random.randint(1, 20))
        enemy_hp -= player_dmg
        if enemy_hp <= 0:
            db.update_player(callback.from_user.id, exp=player["exp"] + enemy["exp"], gold=player["gold"] + enemy["gold"])
            await callback.message.edit_text(f"🏆 <b>ПОБЕДА!</b>\n✨ +{enemy['exp']} опыта\n💰 +{enemy['gold']} золота", reply_markup=main_menu_kb(), parse_mode="HTML")
            await state.clear()
            return
        enemy_dmg = max(1, enemy["phys_atk"] - player["phys_def"] + random.randint(1, 20))
        new_hp = max(0, player["hp"] - enemy_dmg)
        if new_hp <= 0:
            db.update_player(callback.from_user.id, gold=0, hp=player["max_hp"])
            await callback.message.edit_text("💀 <b>ПОРАЖЕНИЕ!</b>\n💰 Золото потеряно.\n❤️ Ты воскрешён.", reply_markup=main_menu_kb(), parse_mode="HTML")
            await state.clear()
            return
        battle["enemy_hp"] = enemy_hp
        battle["player"]["hp"] = new_hp
        await state.update_data(battle=battle)
        await callback.message.edit_text(f"⚔️ Ты: -{player_dmg} HP | Враг: -{enemy_dmg} HP\n👤 {new_hp}/{player['max_hp']} | 👹 {enemy_hp}/{enemy['hp']}", reply_markup=battle_action_kb(), parse_mode="HTML")
        return
    if action == "attack_magic":
        if player["mp"] < 5:
            await callback.answer("❌ Недостаточно MP!", show_alert=True)
            return
        dmg = max(1, player["magic_atk"] - enemy["magic_def"] + random.randint(1, 20))
        enemy_hp -= dmg
        db.update_player(callback.from_user.id, mp=max(0, player["mp"] - 5))
        await callback.answer(f"🔮 Магия: -{dmg} урона!", show_alert=True)
        return
    if action == "use_potion":
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
    await callback.message.edit_text("🃏 <b>Карточки</b>\n\nВыбери тип:", reply_markup=cards_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("card_"))
async def draw_card(callback: types.CallbackQuery):
    card_type = callback.data.split("_")[1]
    card_text = random.choice(CARDS[card_type])
    colors = {"red": "🔴", "yellow": "🟡", "green": "🟢", "black": "⚫"}
    await callback.message.edit_text(f"{colors[card_type]} <b>Карта:</b>\n\n{card_text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Ещё", callback_data=f"card_{card_type}")], [InlineKeyboardButton(text="🔙 Назад", callback_data="cards_menu")]]), parse_mode="HTML")

@dp.callback_query(F.data == "logs")
async def show_logs(callback: types.CallbackQuery):
    logs = db.get_logs(callback.from_user.id)
    text = "📜 <b>Лог</b>\n\n" + "\n".join([f"• {l['action']}: {l['details']}" for l in logs]) if logs else "• Пусто"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]), parse_mode="HTML")

@dp.callback_query(F.data == "magic_tower")
async def magic_tower(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала создай персонажа!", show_alert=True)
        return
    await callback.message.edit_text(f"🔮 <b>Башня Магии</b>\n\nУровень: {player['level']}\n💰 {player['gold']}", reply_markup=magic_levels_kb(), parse_mode="HTML")

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
    await callback.message.edit_text(f"🔮 <b>Уровень {level}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("spell_"))
async def learn_spell(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    level = int(parts[1])
    spell_id = parts[2]
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
    await show_spells(callback)

@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🌑 <b>ТЁМНЫЕ ЗЕМЛИ ЭЛДРОНА</b>\n\n<i>Введи имя (3-30 символов):</i>", parse_mode="HTML")
    await state.set_state(CharacterCreation.name)

@dp.callback_query(F.data == "back_to_race")
async def back_race(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выбери расу:", reply_markup=race_kb())
    await state.set_state(CharacterCreation.race)

@dp.callback_query(F.data == "main_menu")
async def back_main(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if player:
        await callback.message.edit_text(f"🎮 <b>Тёмные Земли Эльдрона</b>, {player['name']}!", reply_markup=main_menu_kb(), parse_mode="HTML")
    else:
        await callback.message.edit_text("🌑 <b>ТЁМНЫЕ ЗЕМЛИ ЭЛДРОНА</b>\n\n/start для начала", parse_mode="HTML")

# Запуск
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
