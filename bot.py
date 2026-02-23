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
    enemy_dice = State()

# ==================== ДАННЫЕ ИГРЫ ====================
# (вставьте все данные из предыдущего кода: RACES, CLASSES, SHOP_ITEMS, SPELLS, MONSTERS, CARDS)
# ... (сокращено для краткости - оставьте все данные как были)

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

# ... (остальные данные SHOP_ITEMS, SPELLS, MONSTERS, CARDS оставьте как были)

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
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==================== ХЕНДЛЕРЫ (ОБРАБОТЧИКИ) ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    player = db.get_player(message.from_user.id)
    if player:
        await message.answer(
            f"🎮 Добро пожаловать в <b>Тёмные Земли Эльдрона</b>, {player['name']}!\n\n"
            f"Выбери действие:",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🌑 <b>ТЁМНЫЕ ЗЕМЛИ ЭЛДРОНА</b> 🌑\n\n"
            "Создай своего героя и начни приключение!\n\n"
            "<i>Введи имя персонажа (3-30 символов):</i>",
            parse_mode="HTML"
        )
        await state.set_state(CharacterCreation.name)

@dp.message(CharacterCreation.name)
async def set_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3 or len(name) > 30:
        await message.answer("❌ Имя должно быть от 3 до 30 символов. Попробуй ещё раз:")
        return
    
    await state.update_data(name=name)
    await message.answer(
        f"✅ Имя: <b>{name}</b>\n\nВыбери расу:",
        reply_markup=race_kb(),
        parse_mode="HTML"
    )
    await state.set_state(CharacterCreation.race)

@dp.callback_query(CharacterCreation.race, F.data.startswith("race_"))
async def set_race(callback: types.CallbackQuery, state: FSMContext):
    race = callback.data.split("_")[1]
    await state.update_data(race=race)
    await callback.message.edit_text(
        f"✅ Расa: <b>{RACES[race]['name']}</b>\n{RACES[race]['magic']}\n\nВыбери класс:",
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
        f"🎉 <b>Герой создан!</b>\n\n"
        f"👤 {data['name']} | {RACES[data['race']]['name']} | {CLASSES[class_type]['name']}\n"
        f"✨ {CLASSES[class_type]['magic']}\n\n"
        f"Твоё приключение начинается!",
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
    exp_left = exp_needed - player["exp"]
    
    equip_text = ""
    for slot, item in player["equipment"].items():
        equip_text += f"• {slot}: {item}\n"
    if not equip_text:
        equip_text = "• Пусто\n"
    
    text = (
        f"👤 <b>{player['name']}</b> | {RACES[player['race']]['name']} | {CLASSES[player['class_type']]['name']}\n"
        f"📊 Уровень: {player['level']}\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']} | 💙 MP: {player['mp']}/{player['max_mp']}\n"
        f"✨ Опыт: {player['exp']}/{exp_needed} (осталось {exp_left})\n"
        f"💰 Золото: {player['gold']}\n\n"
        f"📊 <b>БОЕВЫЕ ХАРАКТЕРИСТИКИ:</b>\n"
        f"⚔️ Физ.АТК: {player['phys_atk']}\n"
        f"⚡️ Скр.АТК: {player['stealth_atk']}\n"
        f"🛡️ Уклонение: {player['evasion']}\n"
        f"🛡️ Физ.Защ: {player['phys_def']}\n"
        f"🔮 Маг.Защ: {player['magic_def']}\n"
        f"🔮 Маг.АТК: {player['magic_atk']}\n\n"
        f"📈 <b>БАЗОВЫЕ НАВЫКИ:</b>\n"
        f"💪 Сила: {player['strength']}\n"
        f"❤️ Живучесть: {player['vitality']}\n"
        f"⚡️ Ловкость: {player['agility']}\n"
        f"🧠 Интеллект: {player['intelligence']}\n"
        f"⭐️ Очки навыков: {player['skill_points']}\n\n"
        f"🎒 <b>ЭКИПИРОВКА:</b>\n{equip_text}"
    )
    
    await callback.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "skills")
async def show_skills(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала создай персонажа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"⭐️ <b>Прокачка навыков</b>\n\n"
        f"Доступно очков: {player['skill_points']}\n\n"
        f"<i>Нажми на кнопку, чтобы прокачать навык:</i>",
        reply_markup=skills_kb(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("skill_"))
async def upgrade_skill(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player or player["skill_points"] < 1:
        await callback.answer("❌ Недостаточно очков навыков!", show_alert=True)
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
    db.add_log(callback.from_user.id, "upgrade_skill", f"+1 {skill}")
    
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
        text += "• Пусто\n"
    else:
        for item_id, count in inv.items():
            name = "Неизвестный предмет"
            for category in [SHOP_ITEMS.get("potions", []), SHOP_ITEMS.get("weapons", []), 
                           SHOP_ITEMS.get("armor", []), SHOP_ITEMS.get("accessories", []),
                           SHOP_ITEMS.get("other", [])]:
                for item in category:
                    if item["id"] == item_id:
                        name = item["name"]
                        break
            text += f"• {name} x{count}\n"
    
    await callback.message.edit_text(text, reply_markup=inventory_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    await callback.message.edit_text("🏪 <b>Магазин</b>\n\nВыбери категорию:", 
                                     reply_markup=shop_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("shop_"))
async def show_shop_category(callback: types.CallbackQuery):
    category_map = {
        "shop_potions": "potions",
        "shop_weapons": "weapons",
        "shop_armor": "armor",
        "shop_accessories": "accessories",
        "shop_other": "other"
    }
    category = category_map.get(callback.data, "potions")
    items = SHOP_ITEMS.get(category, [])
    
    if not items:
        await callback.answer("📭 Категория пуста", show_alert=True)
        return
    
    kb = []
    for item in items:
        kb.append([InlineKeyboardButton(
            text=f"{item['name']} {item['effect']} 💰{item['price']}",
            callback_data=f"buy_{item['id']}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop")])
    
    await callback.message.edit_text(
        f"🏪 <b>{category.title()}</b>\n\n<i>Нажми на товар для покупки:</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("buy_"))
async def buy_item(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    item_id = callback.data.split("_")[1]
    
    item = None
    for category in SHOP_ITEMS.values():
        for i in category:
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
    
    db.add_log(callback.from_user.id, "buy_item", f"{item['name']} за {item['price']}💰")
    
    await callback.answer(f"✅ Куплено: {item['name']}!", show_alert=True)
    await show_shop_category(callback)

@dp.callback_query(F.data == "battle_menu")
async def battle_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("⚔️ <b>Выбери тип боя</b>", 
                                     reply_markup=battle_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "battle_pve")
async def select_monster(callback: types.CallbackQuery):
    await callback.message.edit_text("👹 <b>Выбери сложность монстра</b>", 
                                     reply_markup=pve_monsters_kb(), parse_mode="HTML")

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
    
    battle_data = {
        "player": {k: v for k, v in player.items()},
        "enemy": monster,
        "enemy_hp": monster["hp"],
        "turn": 0
    }
    await state.update_data(battle=battle_data)
    
    await callback.message.edit_text(
        f"⚔️ <b>НАЧАЛО БОЯ!</b>\n\n"
        f"👤 {player['name']} ❤️{player['hp']}/{player['max_hp']}\n"
        f"🆚\n"
        f"👹 {monster['name']} ❤️{monster['hp']}/{monster['hp']}\n\n"
        f"<i>Кинь кубик d20 и напиши число (1-20):</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏳️ Сдаться", callback_data="battle_surrender")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(BattleState.player_dice)

@dp.message(BattleState.player_dice)
async def player_dice_roll(message: types.Message, state: FSMContext):
    try:
        dice = int(message.text)
        if dice < 1 or dice > 20:
            await message.answer("❌ Число должно быть от 1 до 20!")
            return
    except ValueError:
        await message.answer("❌ Введи число от 1 до 20!")
        return
    
    data = await state.get_data()
    battle = data.get("battle", {})
    
    if not battle:
        await message.answer("❌ Бой не найден. Начни заново.")
        await state.clear()
        return
    
    enemy_dice = random.randint(1, 20)
    
    player_init = battle["player"]["stealth_atk"] + dice
    enemy_init = battle["enemy"]["evasion"] + enemy_dice
    
    first = "player" if player_init >= enemy_init else "enemy"
    
    text = (
        f"🎲 <b>Результаты броска:</b>\n"
        f"👤 Ты: {battle['player']['stealth_atk']} + {dice} = {player_init}\n"
        f"👹 Враг: {battle['enemy']['evasion']} + {enemy_dice} = {enemy_init}\n\n"
        f"{'✅ Ты ходишь первым!' if first == 'player' else '⚠️ Враг ходит первым!'}\n\n"
        f"<i>Выбери действие:</i>"
    )
    
    await state.update_data(player_dice=dice, enemy_dice=enemy_dice, first_turn=first)
    await state.set_state(None)  # Сбрасываем состояние
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
        db.add_log(callback.from_user.id, "battle_surrender", f"Сдался в бою с {enemy['name']}")
        await callback.message.edit_text(
            f"🏳️ Ты сдался.\n"
            f"💰 Всё золото потеряно.\n"
            f"❤️ Ты воскрешён с полным HP.\n\n"
            f"<i>Возвращайся, когда станешь сильнее!</i>",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    if action == "attack_phys":
        player_dmg = max(1, player["phys_atk"] - enemy["phys_def"] + random.randint(1, 20))
        enemy_hp -= player_dmg
        
        result_text = f"⚔️ Ты атакуешь и наносишь <b>{player_dmg}</b> урона!\n"
        
        if enemy_hp <= 0:
            db.update_player(
                callback.from_user.id,
                exp=player["exp"] + enemy["exp"],
                gold=player["gold"] + enemy["gold"]
            )
            db.add_log(callback.from_user.id, "battle_win", f"Победа над {enemy['name']}")
            
            await callback.message.edit_text(
                f"🏆 <b>ПОБЕДА!</b>\n\n"
                f"{result_text}\n"
                f"👹 {enemy['name']} повержен!\n"
                f"✨ +{enemy['exp']} опыта\n"
                f"💰 +{enemy['gold']} золота",
                reply_markup=main_menu_kb(),
                parse_mode="HTML"
            )
            await state.clear()
            return
        else:
            enemy_dmg = max(1, enemy["phys_atk"] - player["phys_def"] + random.randint(1, 20))
            new_hp = max(0, player["hp"] - enemy_dmg)
            
            result_text += f"👹 Враг контратакует и наносит <b>{enemy_dmg}</b> урона!\n"
            
            if new_hp <= 0:
                db.update_player(callback.from_user.id, gold=0, hp=player["max_hp"])
                db.add_log(callback.from_user.id, "battle_lose", f"Поражение от {enemy['name']}")
                
                await callback.message.edit_text(
                    f"💀 <b>ПОРАЖЕНИЕ!</b>\n\n"
                    f"{result_text}\n"
                    f"Ты пал в бою...\n"
                    f"💰 Всё золото потеряно.\n"
                    f"❤️ Ты воскрешён с полным HP.",
                    reply_markup=main_menu_kb(),
                    parse_mode="HTML"
                )
                await state.clear()
                return
            else:
                battle["enemy_hp"] = enemy_hp
                battle["player"]["hp"] = new_hp
                await state.update_data(battle=battle)
                
                await callback.message.edit_text(
                    f"⚔️ <b>Ход завершён</b>\n\n"
                    f"{result_text}\n"
                    f"👤 Твой HP: {new_hp}/{player['max_hp']}\n"
                    f"👹 Враг HP: {enemy_hp}/{enemy['hp']}\n\n"
                    f"<i>Твой ход:</i>",
                    reply_markup=battle_action_kb(),
                    parse_mode="HTML"
                )
                return
    
    if action == "attack_magic":
        if player["mp"] < 5:
            await callback.answer("❌ Недостаточно MP!", show_alert=True)
            return
        dmg = max(1, player["magic_atk"] - enemy["magic_def"] + random.randint(1, 20))
        enemy_hp -= dmg
        db.update_player(callback.from_user.id, mp=max(0, player["mp"] - 5))
        await callback.answer(f"🔮 Магия нанесла {dmg} урона!", show_alert=True)
        return
    
    if action == "use_potion":
        inv = player.get("inventory", {})
        if "hp_small" not in inv or inv["hp_small"] < 1:
            await callback.answer("❌ Нет зелий HP!", show_alert=True)
            return
        new_hp = min(player["max_hp"], player["hp"] + 30)
        inv["hp_small"] -= 1
        db.update_player(callback.from_user.id, hp=new_hp, inventory=inv)
        await callback.answer(f"🧪 Восстановлено 30 HP! ❤️ {new_hp}/{player['max_hp']}", show_alert=True)
        return

@dp.callback_query(F.data == "cards_menu")
async def cards_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("🃏 <b>Карточки событий</b>\n\nВыбери тип карты:", 
                                     reply_markup=cards_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("card_"))
async def draw_card(callback: types.CallbackQuery):
    card_type = callback.data.split("_")[1]
    card_text = random.choice(CARDS[card_type])
    
    colors = {"red": "🔴", "yellow": "🟡", "green": "🟢", "black": "⚫"}
    
    await callback.message.edit_text(
        f"{colors[card_type]} <b>Выпала карта:</b>\n\n"
        f"{card_text}\n\n"
        f"<i>Нажми 'Ещё' для новой карты или 'Назад' в меню.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Ещё", callback_data=f"card_{card_type}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="cards_menu")]
        ]),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "logs")
async def show_logs(callback: types.CallbackQuery):
    logs = db.get_logs(callback.from_user.id)
    
    if not logs:
        text = "📜 <b>Лог событий</b>\n\n• Пусто"
    else:
        text = "📜 <b>Последние события:</b>\n\n"
        for log in logs:
            text += f"• {log['action']}: {log['details']}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "magic_tower")
async def magic_tower(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала создай персонажа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"🔮 <b>Башня Магии</b>\n\n"
        f"Твой уровень: {player['level']}\n"
        f"💰 Золото: {player['gold']}\n\n"
        f"<i>Выбери уровень заклинаний для изучения:</i>",
        reply_markup=magic_levels_kb(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("magic_"))
async def show_spells(callback: types.CallbackQuery):
    level = int(callback.data.split("_")[1])
    player = db.get_player(callback.from_user.id)
    
    if player["level"] < level:
        await callback.answer(f"❌ Нужен уровень {level}!", show_alert=True)
        return
    
    spells = SPELLS.get(level, [])
    kb = []
    for spell in spells:
        kb.append([InlineKeyboardButton(
            text=f"{spell['name']} {spell['effect']} {level}ур 💰{spell['cost']}",
            callback_data=f"spell_{level}_{spell['id']}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="magic_tower")])
    
    await callback.message.edit_text(
        f"🔮 <b>Заклинания уровня {level}</b>\n\n"
        f"<i>Нажми на заклинание для изучения:</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("spell_"))
async def learn_spell(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    level = int(parts[1])
    spell_id = parts[2]
    
    player = db.get_player(callback.from_user.id)
    spell = None
    
    for s in SPELLS.get(level, []):
        if s["id"] == spell_id:
            spell = s
            break
    
    if not spell or player["level"] < level or player["gold"] < spell["cost"]:
        await callback.answer("❌ Недостаточно условий!", show_alert=True)
        return
    
    db.update_player(callback.from_user.id, gold=player["gold"] - spell["cost"])
    spells = player["spells"]
    if spell_id not in spells:
        spells.append(spell_id)
        db.update_player(callback.from_user.id, spells=spells)
    
    db.add_log(callback.from_user.id, "learn_spell", f"Изучено: {spell['name']}")
    
    await callback.answer(f"✅ Изучено: {spell['name']}!", show_alert=True)
    await show_spells(callback)

# Навигация
@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🌑 <b>ТЁМНЫЕ ЗЕМЛИ ЭЛДРОНА</b>\n\n"
        "<i>Введи имя персонажа (3-30 символов):</i>",
        parse_mode="HTML"
    )
    await state.set_state(CharacterCreation.name)

@dp.callback_query(F.data == "back_to_race")
async def back_race(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выбери расу:", reply_markup=race_kb())
    await state.set_state(CharacterCreation.race)

@dp.callback_query(F.data == "main_menu")
async def back_main(callback: types.CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if player:
        await callback.message.edit_text(
            f"🎮 <b>Тёмные Земли Эльдрона</b>, {player['name']}!",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "🌑 <b>ТЁМНЫЕ ЗЕМЛИ ЭЛДРОНА</b>\n\n/start для начала",
            parse_mode="HTML"
        )

# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
