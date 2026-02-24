import random,json,os,logging
from aiogram import Bot,Dispatcher,types,F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State,StatesGroup
from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler,setup_application
from aiohttp import web
from config import BOT_TOKEN
import database as db

logging.basicConfig(level=logging.INFO); logger=logging.getLogger(__name__)
bot=Bot(token=BOT_TOKEN); dp=Dispatcher()

class CharacterCreation(StatesGroup):
    name=State(); race=State(); class_type=State()

RACES={
    "human":{"name":"🧑 Человек","bonus":"+3 очка навыка","magic":"✨ Благословение: +10% к лечению"},
    "elf":{"name":"🧝 Эльф","bonus":"+3 Ловкость","magic":"🌿 Природа: Уклонение +15%"},
    "dwarf":{"name":"🧔 Гном","bonus":"+3 Сила","magic":"🪨 Каменная кожа: +5 Физ.защ"},
    "orc":{"name":"👹 Орк","bonus":"+3 Живучесть","magic":"🔥 Ярость: +10% урона при HP<50%"},
    "fallen":{"name":"💀 Падший","bonus":"+1 Ловк, +2 Инт","magic":"👻 Тень: Первый удар скрытный"}
}
CLASSES={
    "warrior":{"name":"⚔️ Воин","bonus":"+1 Сила, +1 Жив","magic":"🗡️ Воинский клич: +5 Физ.АТК"},
    "archer":{"name":"🏹 Лучник","bonus":"+2 Ловкость","magic":"🎯 Точный выстрел: Игнор 5 защиты"},
    "wizard":{"name":"🔮 Волшебник","bonus":"+2 Интеллект","magic":"🛡️ Маг.щит: +10 Маг.защ"},
    "bard":{"name":"🎭 Бард","bonus":"+1 Инт, +1 Ловк","magic":"🎵 Вдохновение: +2 ко всем статам"},
    "paladin":{"name":"🛡️ Паладин","bonus":"+1 Сила, +1 Инт","magic":"✨ Святой свет: Лечение +20 HP"},
    "necromancer":{"name":"💀 Некромант","bonus":"+1 Инт, +1 Жив","magic":"☠️ Поднять скелета: Призыв"}
}
RACE_MAGIC={r:{"name":RACES[r]["magic"].split(":")[0].strip(),"description":RACES[r]["magic"].split(":")[1].strip() if ":" in RACES[r]["magic"] else "","type":"passive"} for r in RACES}
CLASS_MAGIC={
    "warrior":{"name":"🗡️ Воинский клич","description":"+5 Физ.АТК на 1 ход","type":"active","mp_cost":5,"duration":1},
    "archer":{"name":"🎯 Точный выстрел","description":"Игнорирует 5 защиты","type":"active","mp_cost":5,"duration":1},
    "wizard":{"name":"🛡️ Магический щит","description":"+10 Маг.защ на 1 ход","type":"active","mp_cost":5,"duration":1},
    "bard":{"name":"🎵 Вдохновение","description":"+2 ко всем статам на 1 ход","type":"active","mp_cost":10,"duration":1},
    "paladin":{"name":"✨ Святой свет","description":"Лечение +20 HP","type":"active","mp_cost":10,"duration":0},
    "necromancer":{"name":"☠️ Поднять скелета","description":"Призыв помощника","type":"active","mp_cost":15,"duration":3}
}

# ✅ МАГАЗИН ПО ТЗ С ПРАВИЛЬНЫМИ СЛОТАМИ
SHOP_ITEMS={
    "potions":[
        {"id":"hp_small","name":"🧪 Малое зелье HP","type_name":"Зелья","type_num":"","effect":"+30 HP","price":50,"stat":"hp","value":30,"slot":None},
        {"id":"hp_medium","name":"🧪 Среднее зелье HP","type_name":"Зелья","type_num":"","effect":"+60 HP","price":100,"stat":"hp","value":60,"slot":None},
        {"id":"hp_large","name":"🧪 Большое зелье HP","type_name":"Зелья","type_num":"","effect":"+100 HP","price":150,"stat":"hp","value":100,"slot":None},
        {"id":"mp_small","name":"🧪 Малое зелье MP","type_name":"Зелья","type_num":"","effect":"+30 MP","price":50,"stat":"mp","value":30,"slot":None},
        {"id":"mp_medium","name":"🧪 Среднее зелье MP","type_name":"Зелья","type_num":"","effect":"+60 MP","price":100,"stat":"mp","value":60,"slot":None},
        {"id":"mp_large","name":"🧪 Большое зелье MP","type_name":"Зелья","type_num":"","effect":"+100 MP","price":150,"stat":"mp","value":100,"slot":None},
    ],
    "weapons":[
        {"id":"sword_apprentice","name":"⚔️ Меч Ученика","type_name":"Оружия","type_num":"1","effect":"+1 Сила","price":150,"stat":"strength","value":1,"slot":"weapon_1"},
        {"id":"shield_apprentice","name":"🛡️ Щит Ученика","type_name":"Оружия","type_num":"2","effect":"+1 Живучесть","price":150,"stat":"vitality","value":1,"slot":"weapon_2"},
        {"id":"bow_apprentice","name":"🏹 Лук Ученика","type_name":"Оружия","type_num":"1","effect":"+1 Ловкость","price":150,"stat":"agility","value":1,"slot":"weapon_1"},
        {"id":"arrows_apprentice","name":"🏹 Стрелы Ученика","type_name":"Оружия","type_num":"2","effect":"+1 Ловкость","price":150,"stat":"agility","value":1,"slot":"weapon_2"},
        {"id":"staff_apprentice","name":"🔮 Посох Ученика","type_name":"Оружия","type_num":"1","effect":"+1 Интеллект","price":150,"stat":"intelligence","value":1,"slot":"weapon_1"},
        {"id":"orb_apprentice","name":"🔮 Сфера Ученика","type_name":"Оружия","type_num":"2","effect":"+1 Интеллект","price":150,"stat":"intelligence","value":1,"slot":"weapon_2"},
    ],
    "armor":[
        {"id":"helm_apprentice","name":"⛑️ Шлем Ученика","type_name":"Экипировка","type_num":"1","effect":"+1 Живучесть","price":200,"stat":"vitality","value":1,"slot":"armor_1"},
        {"id":"armor_apprentice","name":"🛡️ Броня Ученика","type_name":"Экипировка","type_num":"2","effect":"+1 Живучесть","price":200,"stat":"vitality","value":1,"slot":"armor_2"},
        {"id":"pants_apprentice","name":"👖 Штаны Ученика","type_name":"Экипировка","type_num":"3","effect":"+1 Ловкость","price":200,"stat":"agility","value":1,"slot":"armor_3"},
        {"id":"boots_apprentice","name":"👢 Ботинки Ученика","type_name":"Экипировка","type_num":"4","effect":"+1 Ловкость","price":200,"stat":"agility","value":1,"slot":"armor_4"},
        {"id":"arms_apprentice","name":"💪 Руки Ученика","type_name":"Экипировка","type_num":"5","effect":"+1 Сила","price":200,"stat":"strength","value":1,"slot":"armor_5"},
        {"id":"gloves_apprentice","name":"🧤 Перчатки Ученика","type_name":"Экипировка","type_num":"6","effect":"+1 Сила","price":200,"stat":"strength","value":1,"slot":"armor_6"},
    ],
    "accessories":[
        {"id":"amulet_agility","name":"📿 Амулет Ловкости","type_name":"Аксессуары","type_num":"1","effect":"+2 Ловкость","price":400,"stat":"agility","value":2,"slot":"accessory_1"},
        {"id":"ring_protection","name":"💍 Кольцо Защиты","type_name":"Аксессуары","type_num":"2","effect":"+2 Живучесть","price":400,"stat":"vitality","value":2,"slot":"accessory_2"},
        {"id":"chain_strength","name":"⛓️ Цепь Силы","type_name":"Аксессуары","type_num":"3","effect":"+2 Сила","price":400,"stat":"strength","value":2,"slot":"accessory_3"},
    ],
    "other":[
        {"id":"scroll_exp","name":"📜 Свиток опыта","type_name":"Разное","type_num":"","effect":"+50 Опыта","price":500,"stat":"exp","value":50,"slot":None},
    ]
}

SPELLS={5:[{"id":"fire","name":"🔥 Огонь","effect":"+5 Маг.АТК","cost":2000}],15:[{"id":"fireball","name":"🔥 Шар","effect":"+15 Маг.АТК","cost":5000}]}
MONSTERS={"weak":[{"name":"🐀 Крыса","hp":15,"phys_atk":3,"phys_def":1,"evasion":3,"exp":20,"gold":10}],"medium":[{"name":"🐺 Волк","hp":40,"phys_atk":10,"phys_def":4,"evasion":7,"exp":70,"gold":40}],"strong":[{"name":"🐉 Дракон","hp":80,"phys_atk":20,"phys_def":10,"evasion":10,"exp":200,"gold":150}],"bosses":[{"name":"👹 Босс","hp":200,"phys_atk":45,"phys_def":30,"evasion":10,"exp":1000,"gold":800}],"titan":{"name":"👑 ТИТАН","hp":500,"phys_atk":60,"phys_def":40,"evasion":20,"exp":5000,"gold":3000}}
CARDS={"red":["👹 Монстр!","🐺 Атака!"],"yellow":["📜 Задание: +100💰"],"green":["✨ Бафф: +10 ко всем"],"black":["☠️ Дебафф: -10 защиты"]}

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Персонаж",callback_data="my_character")],[InlineKeyboardButton(text="⭐️ Навыки",callback_data="skills")],[InlineKeyboardButton(text="✨ Способности",callback_data="abilities")],[InlineKeyboardButton(text="🎒 Инвентарь",callback_data="inventory")],[InlineKeyboardButton(text="🏪 Магазин",callback_data="shop")],[InlineKeyboardButton(text="⚔️ Бой",callback_data="battle_menu")],[InlineKeyboardButton(text="🃏 Карточки",callback_data="cards_menu")],[InlineKeyboardButton(text="📜 Лог",callback_data="logs")],[InlineKeyboardButton(text="🔮 Магия",callback_data="magic_tower")]])
def race_kb():
    kb=[[InlineKeyboardButton(text=f"{RACES[r]['name']} {RACES[r]['bonus']}",callback_data=f"race_{r}")] for r in RACES]; kb.append([InlineKeyboardButton(text="🔙 Назад",callback_data="back_to_start")]); return InlineKeyboardMarkup(inline_keyboard=kb)
def class_kb():
    kb=[[InlineKeyboardButton(text=f"{CLASSES[c]['name']} {CLASSES[c]['bonus']}",callback_data=f"class_{c}")] for c in CLASSES]; kb.append([InlineKeyboardButton(text="🔙 Назад",callback_data="back_to_race")]); return InlineKeyboardMarkup(inline_keyboard=kb)
def skills_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💪 +1 Сила = ⚔️+4",callback_data="skill_strength")],[InlineKeyboardButton(text="⚡ +1 Ловк = ⚡+8 🛡️+3",callback_data="skill_agility")],[InlineKeyboardButton(text="❤️ +1 Жив = ❤️+10 🛡️+1",callback_data="skill_vitality")],[InlineKeyboardButton(text="🧠 +1 Инт = 💙+3 🔮+4",callback_data="skill_intelligence")],[InlineKeyboardButton(text="🔙 Назад",callback_data="main_menu")]])
def inventory_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧪 Зелья",callback_data="inv_potions")],[InlineKeyboardButton(text="⚔️ Оружие",callback_data="inv_weapons")],[InlineKeyboardButton(text="🛡️ Экипировка",callback_data="inv_armor")],[InlineKeyboardButton(text="📿 Бижутерия",callback_data="inv_accessories")],[InlineKeyboardButton(text="📦 Разное",callback_data="inv_other")],[InlineKeyboardButton(text="🔙 Назад",callback_data="main_menu")]])
def shop_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧪 Зелья",callback_data="shop_potions")],[InlineKeyboardButton(text="⚔️ Оружие",callback_data="shop_weapons")],[InlineKeyboardButton(text="🛡️ Экипировка",callback_data="shop_armor")],[InlineKeyboardButton(text="📿 Бижутерия",callback_data="shop_accessories")],[InlineKeyboardButton(text="📦 Разное",callback_data="shop_other")],[InlineKeyboardButton(text="🔙 Назад",callback_data="main_menu")]])
def battle_menu_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👹 vs Монстр",callback_data="battle_pve")],[InlineKeyboardButton(text="🔙 Назад",callback_data="main_menu")]])
def pve_monsters_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟢 Слабые",callback_data="monster_weak")],[InlineKeyboardButton(text="🟡 Средние",callback_data="monster_medium")],[InlineKeyboardButton(text="🔴 Сильные",callback_data="monster_strong")],[InlineKeyboardButton(text="👑 Боссы",callback_data="monster_bosses")],[InlineKeyboardButton(text="💀 ТИТАН",callback_data="monster_titan")],[InlineKeyboardButton(text="🔙 Назад",callback_data="battle_menu")]])
def cards_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔴 Красная",callback_data="card_red")],[InlineKeyboardButton(text="🟡 Жёлтая",callback_data="card_yellow")],[InlineKeyboardButton(text="🟢 Зелёная",callback_data="card_green")],[InlineKeyboardButton(text="⚫ Чёрная",callback_data="card_black")],[InlineKeyboardButton(text="🔙 Назад",callback_data="main_menu")]])
def magic_levels_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📊 Уровень 5",callback_data="magic_5")],[InlineKeyboardButton(text="📊 Уровень 15",callback_data="magic_15")],[InlineKeyboardButton(text="🔙 Назад",callback_data="magic_tower")]])

async def edit_safe(msg,**kw):
    try: await msg.edit_text(**kw); return True
    except Exception as e:
        if any(x in str(e).lower() for x in ["message is not modified","can't be edited","not found"]): logger.debug(f"⚠️ {e}"); return True
        logger.error(f"❌ {e}"); raise

@dp.errors()
async def err_h(u,e):
    if any(x in str(e).lower() for x in ["message is not modified","can't be edited","not found"]): return True
    logger.error(f"❌ {u.update_id}: {e}"); return True

@dp.message(Command("start"))
async def start(m:types.Message,s:FSMContext):
    p=db.get_player(m.from_user.id)
    if p: await m.answer(f"🎮 Добро пожаловать, {p['name']}!",reply_markup=main_menu_kb(),parse_mode="HTML")
    else: await m.answer("🌑 <b>ТЁМНЫЕ ЗЕМЛИ ЭЛДРОНА</b>\n\n<i>Введи имя (3-30 символов):</i>",parse_mode="HTML"); await s.set_state(CharacterCreation.name)

@dp.message(CharacterCreation.name)
async def set_name(m:types.Message,s:FSMContext):
    n=m.text.strip()
    if len(n)<3 or len(n)>30: await m.answer("❌ Имя от 3 до 30 символов:"); return
    await s.update_data(name=n); await m.answer(f"✅ Имя: {n}\n\nВыбери расу:",reply_markup=race_kb(),parse_mode="HTML"); await s.set_state(CharacterCreation.race)

@dp.callback_query(CharacterCreation.race,F.data.startswith("race_"))
async def set_race(cb:types.CallbackQuery,s:FSMContext):
    r=cb.data.split("_")[1]; await s.update_data(race=r)
    await edit_safe(cb.message,text=f"✅ Раса: {RACES[r]['name']}\n{RACES[r]['magic']}\n\nВыбери класс:",reply_markup=class_kb(),parse_mode="HTML"); await s.set_state(CharacterCreation.class_type)

@dp.callback_query(CharacterCreation.class_type,F.data.startswith("class_"))
async def set_class(cb:types.CallbackQuery,s:FSMContext):
    d=await s.get_data(); c=cb.data.split("_")[1]
    db.create_player(cb.from_user.id,cb.from_user.username or "Hero",d["name"],d["race"],c); await s.clear()
    rm,cm=RACE_MAGIC.get(d["race"],{}),CLASS_MAGIC.get(c,{})
    txt=f"🎉 <b>Герой создан!</b>\n\n👤 {d['name']}\n🧬 {RACES[d['race']]['name']} | {CLASSES[c]['name']}\n✨ {rm.get('name','')}: {rm.get('description','')}\n⚔️ {cm.get('name','')}: {cm.get('description','')}\n\nТвоё приключение начинается!"
    await edit_safe(cb.message,text=txt,reply_markup=main_menu_kb(),parse_mode="HTML")

@dp.callback_query(F.data=="my_character")
async def show_char(cb:types.CallbackQuery):
    p=db.get_player(cb.from_user.id)
    if not p: await cb.answer("❌ Создай персонажа!",show_alert=True); return
    en=p["level"]*100; rm,cm=RACE_MAGIC.get(p["race"],{}),CLASS_MAGIC.get(p["class_type"],{})
    eq=""
    sn={"weapon_1":"⚔️ Оружие I","weapon_2":"🛡️ Оружие II","armor_1":"⛑️ Шлем","armor_2":"🛡️ Броня","armor_3":"👖 Штаны","armor_4":"👢 Ботинки","armor_5":"💪 Руки","armor_6":"🧤 Перчатки","accessory_1":"📿 Амулет","accessory_2":"💍 Кольцо","accessory_3":"⛓️ Цепь"}
    if p["equipment"]:
        for sl,iid in p["equipment"].items():
            nm=iid
            for ct,its in SHOP_ITEMS.items():
                for it in its:
                    if it["id"]==iid: nm=it["name"]; break
            eq+=f"{sn.get(sl,sl)}: {nm}\n"
    else: eq="• Пусто\n"
    mi=f"📜 <b>СПОСОБНОСТИ:</b>\n✨ Раса: {rm.get('name','Нет')} - {rm.get('description','')}\n⚔️ Класс: {cm.get('name','Нет')} - {cm.get('description','')} (MP: {cm.get('mp_cost',0)})\n\n"
    txt=(f"👤 <b>{p['name']}</b>\n🧬 {RACES[p['race']]['name']} | {CLASSES[p['class_type']]['name']}\n📊 Уровень: {p['level']}\n❤️ HP: {p['hp']}/{p['max_hp']} | 💙 MP: {p['mp']}/{p['max_mp']}\n✨ Опыт: {p['exp']}/{en} | 💰 Золото: {p['gold']}\n\n"
         f"📊 <b>ХАРАКТЕРИСТИКИ:</b>\n⚔️ Физ.АТК: {p['phys_atk']}\n⚡️ Скр.АТК: {p['stealth_atk']}\n🛡️ Уклон: {p['evasion']}\n🛡️ Физ.Защ: {p['phys_def']}\n🔮 Маг.Защ: {p['magic_def']}\n🔮 Маг.АТК: {p['magic_atk']}\n\n"
         f"📈 <b>НАВЫКИ:</b>\n💪 Сила: {p['strength']}\n❤️ Жив: {p['vitality']}\n⚡️ Ловк: {p['agility']}\n🧠 Инт: {p['intelligence']}\n⭐️ Очки: {p['skill_points']}\n\n{mi}🎒 <b>ЭКИПИРОВКА:</b>\n{eq}")
    await edit_safe(cb.message,text=txt,reply_markup=main_menu_kb(),parse_mode="HTML")

@dp.callback_query(F.data=="skills")
async def show_skills(cb:types.CallbackQuery):
    p=db.get_player(cb.from_user.id)
    if not p: await cb.answer("❌ Создай персонажа!",show_alert=True); return
    txt=f"⭐️ <b>Прокачка</b>\n\n👤 {p['name']} | ⭐️ Очки: <b>{p['skill_points']}</b>\n\n💪 +1 Сила → ⚔️+4\n⚡ +1 Ловк → ⚡+8 🛡️+3\n❤️ +1 Жив → ❤️+10 🛡️+1\n🧠 +1 Инт → 💙+3 🔮+4\n\n<i>Нажми кнопку:</i>"
    await edit_safe(cb.message,text=txt,reply_markup=skills_kb(),parse_mode="HTML")

@dp.callback_query(F.data.startswith("skill_"))
async def up_skill(cb:types.CallbackQuery):
    p=db.get_player(cb.from_user.id)
    if not p or p["skill_points"]<1: await cb.answer("❌ Недостаточно очков!",show_alert=True); return
    sk=cb.data.split("_")[1]; up={"skill_points":p["skill_points"]-1}; ms=""
    if sk=="strength": up.update({"strength":p["strength"]+1,"phys_atk":p["phys_atk"]+4}); ms="💪 Сила +1 → ⚔️+4"
    elif sk=="agility": up.update({"agility":p["agility"]+1,"stealth_atk":p["stealth_atk"]+8,"evasion":p["evasion"]+3}); ms="⚡ Ловкость +1 → ⚡+8 🛡️+3"
    elif sk=="vitality": up.update({"vitality":p["vitality"]+1,"max_hp":p["max_hp"]+10,"hp":p["hp"]+10,"phys_def":p["phys_def"]+1,"magic_def":p["magic_def"]+1}); ms="❤️ Живучесть +1 → ❤️+10 🛡️+1"
    elif sk=="intelligence": up.update({"intelligence":p["intelligence"]+1,"max_mp":p["max_mp"]+3,"mp":p["mp"]+3,"magic_atk":p["magic_atk"]+4}); ms="🧠 Интеллект +1 → 💙+3 🔮+4"
    db.update_player(cb.from_user.id,**up); db.add_log(cb.from_user.id,"upgrade_skill",f"{sk} +1")
    await cb.answer(f"✅ {ms}!",show_alert=True); await show_skills(cb)

@dp.callback_query(F.data=="abilities")
async def show_abilities(cb:types.CallbackQuery):
    p=db.get_player(cb.from_user.id)
    if not p: await cb.answer("❌ Создай персонажа!",show_alert=True); return
    rm,cm=RACE_MAGIC.get(p["race"],{}),CLASS_MAGIC.get(p["class_type"],{}); kb=[]
    if cm.get("type")=="active": kb.append([InlineKeyboardButton(text=f"⚔️ {cm['name']} (-{cm['mp_cost']} MP)",callback_data="use_class_magic")])
    kb.append([InlineKeyboardButton(text="🔙 Назад",callback_data="main_menu")])
    txt=f"✨ <b>СПОСОБНОСТИ</b>\n\n👤 {p['name']} | 💙 MP: {p['mp']}/{p['max_mp']}\n\n📜 <b>РАСА</b> (пассивная)\n{rm.get('name','Нет')}: {rm.get('description','Нет')}\n\n⚔️ <b>КЛАСС</b> (активная)\n{cm.get('name','Нет')}: {cm.get('description','Нет')}\n💰 MP: {cm.get('mp_cost',0)} | ⏱️ {cm.get('duration',0)} ход(а)"
    await edit_safe(cb.message,text=txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@dp.callback_query(F.data=="inventory")
async def show_inv(cb:types.CallbackQuery):
    p=db.get_player(cb.from_user.id)
    if not p: await cb.answer("❌ Создай персонажа!",show_alert=True); return
    inv=p["inventory"]; txt="🎒 Инвентарь\n\n"
    if not inv: txt+="• Пусто"
    else:
        for iid,cnt in inv.items():
            nm=iid
            for ct,its in SHOP_ITEMS.items():
                for it in its:
                    if it["id"]==iid: nm=it["name"]; break
            txt+=f"• {nm} x{cnt}\n"
    await edit_safe(cb.message,text=txt,reply_markup=inventory_kb(),parse_mode="HTML")

@dp.callback_query(F.data.startswith("inv_"))
async def show_inv_cat(cb:types.CallbackQuery):
    p=db.get_player(cb.from_user.id)
    if not p: await cb.answer("❌ Создай персонажа!",show_alert=True); return
    cm={"inv_potions":"potions","inv_weapons":"weapons","inv_armor":"armor","inv_accessories":"accessories","inv_other":"other"}
    cat=cm.get(cb.data,"potions"); inv=p["inventory"]
    iti=[(it,inv[it["id"]]) for it in SHOP_ITEMS.get(cat,[]) if it["id"] in inv and inv[it["id"]]>0]
    kb=[]
    for it,cnt in iti:
        eq=any(iid==it["id"] for iid in p["equipment"].values())
        kb.append([InlineKeyboardButton(text=f"{'✅' if eq else '🎒'} {it['name']} x{cnt}",callback_data=f"equip_{it['id']}")])
    if cat in ["weapons","armor","accessories"] and cat!="potions" and cat!="other":
        kb.append([InlineKeyboardButton(text="💰 Продать всё за 50%",callback_data=f"sell_all_{cat}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад",callback_data="inventory")])
    txt=f"🎒 {cat.title()}\n\n"+("Нажми для экипировки/продажи:" if iti else "• Пусто")
    await edit_safe(cb.message,text=txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@dp.callback_query(F.data.startswith("equip_"))
async def equip_item(cb:types.CallbackQuery):
    p=db.get_player(cb.from_user.id)
    if not p: await cb.answer("❌ Создай персонажа!",show_alert=True); return
    iid=cb.data.split("_",1)[1]
    if iid not in p["inventory"] or p["inventory"][iid]<1: await cb.answer("❌ Нет в инвентаре!",show_alert=True); return
    it=None; sl=None
    for ct,its in SHOP_ITEMS.items():
        for i in its:
            if i["id"]==iid: it=i; sl=i.get("slot"); break
        if it: break
    if not sl: await cb.answer("❌ Предмет не экипируется!",show_alert=True); return
    eq=p["equipment"]; eq[sl]=iid; db.update_player(cb.from_user.id,equipment=eq)
    up=db.get_player(cb.from_user.id); up=db.apply_equip_bonuses(up,SHOP_ITEMS)
    db.update_player(cb.from_user.id,**{k:up[k] for k in ["strength","vitality","agility","intelligence","phys_atk","stealth_atk","evasion","phys_def","magic_def","magic_atk","max_hp","max_mp"]})
    db.add_log(cb.from_user.id,"equip_item",f"Надел {it['name']}")
    await cb.answer(f"✅ {it['name']} надето!",show_alert=True); await show_inv_cat(cb)

@dp.callback_query(F.data.startswith("unequip_"))
async def unequip_item(cb:types.CallbackQuery):
    p=db.get_player(cb.from_user.id)
    if not p: await cb.answer("❌ Создай персонажа!",show_alert=True); return
    sl=cb.data.split("_",1)[1]
    if sl not in p["equipment"]: await cb.answer("⚠️ Ничего не надето!",show_alert=True); return
    iid=p["equipment"][sl]; nm=next((i["name"] for ct in SHOP_ITEMS.values() for i in ct if i["id"]==iid),iid)
    eq=p["equipment"]; del eq[sl]; db.update_player(cb.from_user.id,equipment=eq)
    up=db.get_player(cb.from_user.id); up=db.apply_equip_bonuses(up,SHOP_ITEMS)
    db.update_player(cb.from_user.id,**{k:up[k] for k in ["strength","vitality","agility","intelligence","phys_atk","stealth_atk","evasion","phys_def","magic_def","magic_atk","max_hp","max_mp"]})
    db.add_log(cb.from_user.id,"unequip_item",f"Снял {nm}")
    await cb.answer(f"🔻 {nm} снято!",show_alert=True); await show_inv_cat(cb)

@dp.callback_query(F.data=="shop")
async def show_shop(cb:types.CallbackQuery): await edit_safe(cb.message,text="🏪 Магазин\n\nВыбери категорию:",reply_markup=shop_kb(),parse_mode="HTML")

@dp.callback_query(F.data.startswith("shop_"))
async def show_shop_cat(cb:types.CallbackQuery):
    cm={"shop_potions":"potions","shop_weapons":"weapons","shop_armor":"armor","shop_accessories":"accessories","shop_other":"other"}
    cat=cm.get(cb.data,"potions"); its=SHOP_ITEMS.get(cat,[])
    kb=[[InlineKeyboardButton(text=f"{i['name']} {i['effect']} 💰{i['price']}",callback_data=f"buy_{cat}_{i['id']}")] for i in its]
    kb.append([InlineKeyboardButton(text="🔙 Назад",callback_data="shop")])
    await edit_safe(cb.message,text=f"🏪 {cat.title()}\n\n<i>Нажми для покупки:</i>",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_item(cb:types.CallbackQuery):
    uid=cb.from_user.id
    parts=cb.data.split("_",2)
    if len(parts)!=3: await cb.answer("❌ Ошибка формата!",show_alert=True); return
    cat,iid=parts[1],parts[2]; logger.info(f"🛒 Покупка: user={uid}, cat={cat}, item={iid}")
    p=db.get_player(uid)
    if not p: await cb.answer("❌ Персонаж не найден!",show_alert=True); return
    it=None
    for i in SHOP_ITEMS.get(cat,[]):
        if i["id"]==iid: it=i; break
    if not it: logger.error(f"❌ Item '{iid}' not found in category '{cat}'"); await cb.answer(f"❌ Предмет не найден: {iid}",show_alert=True); return
    cg,ip=int(p.get("gold",0)),int(it.get("price",0))
    logger.info(f"💰 Проверка: gold={cg}, price={ip}, item={it['name']}")
    if cg<ip: await cb.answer(f"❌ Недостаточно золота! Нужно: 💰{ip}, у вас: 💰{cg}",show_alert=True); return
    if not db.spend_gold(uid,ip): await cb.answer("❌ Ошибка списания золота!",show_alert=True); return
    inv=p.get("inventory",{}); inv[iid]=inv.get(iid,0)+1
    if not db.update_player(uid,inventory=inv): db.add_gold(uid,ip); await cb.answer("❌ Ошибка добавления предмета!",show_alert=True); return
    db.add_log(uid,"buy_item",f"Купил {it['name']} за {ip}💰")
    await cb.answer(f"✅ Куплено: {it['name']} за 💰{ip}!",show_alert=True)
    # ✅ Возвращаемся в ту же категорию магазина
    await show_shop_cat_with_cat(cb, cat)

async def show_shop_cat_with_cat(cb:types.CallbackQuery, cat:str):
    """Показывает категорию магазина по имени"""
    its=SHOP_ITEMS.get(cat,[])
    kb=[[InlineKeyboardButton(text=f"{i['name']} {i['effect']} 💰{i['price']}",callback_data=f"buy_{cat}_{i['id']}")] for i in its]
    kb.append([InlineKeyboardButton(text="🔙 Назад",callback_data="shop")])
    await edit_safe(cb.message,text=f"🏪 {cat.title()}\n\n<i>Нажми для покупки:</i>",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@dp.callback_query(F.data.startswith("sell_"))
async def sell_item(cb:types.CallbackQuery):
    uid=cb.from_user.id
    parts=cb.data.split("_",2)
    if len(parts)<3: await cb.answer("❌ Ошибка!",show_alert=True); return
    if parts[1]=="all":  # Продажа всех предметов категории
        cat=parts[2]
        p=db.get_player(uid)
        if not p: await cb.answer("❌ Ошибка!",show_alert=True); return
        inv=p.get("inventory",{}); total=0; sold=[]
        for iid,cnt in list(inv.items()):
            for ct,its in SHOP_ITEMS.items():
                for it in its:
                    if it["id"]==iid and it.get("slot"):  # Только экипируемые предметы
                        price=it["price"]//2 * cnt
                        total+=price; sold.append(f"{it['name']} x{cnt} → 💰{price}"); break
        if total==0: await cb.answer("⚠️ Нечего продавать!",show_alert=True); return
        db.add_gold(uid,total); inv={k:v for k,v in inv.items() if k not in [s.split()[0] for s in sold]}
        db.update_player(uid,gold=p["gold"]+total,inventory=inv)
        db.add_log(uid,"sell_items",f"Продал: {'; '.join(sold)}")
        await cb.answer(f"✅ Продано на 💰{total}!",show_alert=True); await show_inv_cat(cb)
    else:  # Продажа одного предмета
        iid=parts[1] if len(parts)==2 else parts[2]
        p=db.get_player(uid)
        if not p or iid not in p["inventory"] or p["inventory"][iid]<1: await cb.answer("❌ Нет предмета!",show_alert=True); return
        it=None
        for ct,its in SHOP_ITEMS.items():
            for i in its:
                if i["id"]==iid: it=i; break
            if it: break
        if not it or not it.get("slot"): await cb.answer("❌ Нельзя продать!",show_alert=True); return
        price=it["price"]//2
        inv=p["inventory"]; inv[iid]-=1
        if inv[iid]<=0: del inv[iid]
        db.add_gold(uid,price); db.update_player(uid,gold=p["gold"]+price,inventory=inv)
        db.add_log(uid,"sell_item",f"Продал {it['name']} за 💰{price}")
        await cb.answer(f"✅ Продано: {it['name']} за 💰{price}!",show_alert=True); await show_inv_cat(cb)

@dp.callback_query(F.data=="battle_menu")
async def battle_menu(cb:types.CallbackQuery): await edit_safe(cb.message,text="⚔️ Бой",reply_markup=battle_menu_kb(),parse_mode="HTML")

@dp.callback_query(F.data=="battle_pve")
async def select_monster(cb:types.CallbackQuery): await edit_safe(cb.message,text="👹 Сложность",reply_markup=pve_monsters_kb(),parse_mode="HTML")

@dp.callback_query(F.data=="cards_menu")
async def cards_menu(cb:types.CallbackQuery): await edit_safe(cb.message,text="🃏 Карточки\n\nВыбери тип:",reply_markup=cards_kb(),parse_mode="HTML")

@dp.callback_query(F.data.startswith("card_"))
async def draw_card(cb:types.CallbackQuery):
    ct=cb.data.split("_",1)[1]; txt=random.choice(CARDS[ct]); cl={"red":"🔴","yellow":"🟡","green":"🟢","black":"⚫"}
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Ещё",callback_data=f"card_{ct}")],[InlineKeyboardButton(text="🔙 Назад",callback_data="cards_menu")]])
    await edit_safe(cb.message,text=f"{cl[ct]} {txt}",reply_markup=kb,parse_mode="HTML")

@dp.callback_query(F.data=="logs")
async def show_logs(cb:types.CallbackQuery):
    logs=db.get_logs(cb.from_user.id)
    txt="📜 Лог\n\n"+("\n".join([f"• {l['action']}: {l['details']}" for l in logs[:10]]) if logs else "• Пусто")
    await edit_safe(cb.message,text=txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад",callback_data="main_menu")]]),parse_mode="HTML")

@dp.callback_query(F.data=="magic_tower")
async def magic_tower(cb:types.CallbackQuery):
    p=db.get_player(cb.from_user.id)
    if not p: await cb.answer("❌ Создай персонажа!",show_alert=True); return
    await edit_safe(cb.message,text=f"🔮 Башня Магии\n\nУровень: {p['level']}\n💰 {p['gold']}",reply_markup=magic_levels_kb(),parse_mode="HTML")

@dp.callback_query(F.data.startswith("magic_"))
async def show_spells(cb:types.CallbackQuery):
    lv=int(cb.data.split("_",1)[1]); p=db.get_player(cb.from_user.id)
    if p["level"]<lv: await cb.answer(f"❌ Нужен уровень {lv}!",show_alert=True); return
    sp=SPELLS.get(lv,[]); kb=[[InlineKeyboardButton(text=f"{s['name']} 💰{s['cost']}",callback_data=f"spell_{lv}_{s['id']}")] for s in sp]
    kb.append([InlineKeyboardButton(text="🔙 Назад",callback_data="magic_tower")])
    await edit_safe(cb.message,text=f"🔮 Уровень {lv}",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),parse_mode="HTML")

@dp.callback_query(F.data.startswith("spell_"))
async def learn_spell(cb:types.CallbackQuery):
    pts=cb.data.split("_",2); lv,sid=int(pts[1]),pts[2]
    p=db.get_player(cb.from_user.id); sp=next((s for s in SPELLS.get(lv,[]) if s["id"]==sid),None)
    if not sp or p["level"]<lv or p["gold"]<sp["cost"]: await cb.answer("❌ Недостаточно условий!",show_alert=True); return
    db.update_player(cb.from_user.id,gold=p["gold"]-sp["cost"]); spl=p["spells"]
    if sid not in spl: spl.append(sid); db.update_player(cb.from_user.id,spells=spl)
    await cb.answer(f"✅ Изучено: {sp['name']}!",show_alert=True)

@dp.callback_query(F.data=="back_to_start")
async def back_start(cb:types.CallbackQuery,s:FSMContext):
    await edit_safe(cb.message,text="🌑 Введи имя (3-30 символов):",parse_mode="HTML"); await s.set_state(CharacterCreation.name)

@dp.callback_query(F.data=="back_to_race")
async def back_race(cb:types.CallbackQuery,s:FSMContext):
    await edit_safe(cb.message,text="Выбери расу:",reply_markup=race_kb()); await s.set_state(CharacterCreation.race)

@dp.callback_query(F.data=="main_menu")
async def back_main(cb:types.CallbackQuery):
    p=db.get_player(cb.from_user.id)
    if p: await edit_safe(cb.message,text=f"🎮 {p['name']}",reply_markup=main_menu_kb(),parse_mode="HTML")
    else: await edit_safe(cb.message,text="🌑 /start для начала",parse_mode="HTML")

async def on_startup(app):
    url=os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RENDER_EXTERNAL_URL")
    if url:
        url=url.replace("http://","https://").rstrip("/")
        await bot.set_webhook(f"{url}/webhook",allowed_updates=dp.resolve_used_update_types())
        logger.info(f"✅ Webhook: {url}/webhook")

async def on_shutdown(app): await bot.delete_webhook(); await bot.session.close()

async def webhook_handler(req):
    try:
        upd=types.Update(**await req.json()); await dp.feed_update(bot,upd); return web.Response()
    except Exception as e: logger.error(f"❌ Webhook: {e}"); return web.Response(status=400)

def create_app():
    app=web.Application(); app.router.add_post("/webhook",webhook_handler); app.on_startup.append(on_startup); app.on_shutdown.append(on_shutdown); return app

def main():
    app=create_app(); setup_application(app,dp,bot=bot); web.run_app(app,host="0.0.0.0",port=int(os.getenv("PORT",8080)))

if __name__=="__main__": main()
