"""
📁 database.py - Работа с базой данных SQLite
ИСПРАВЛЕНО: пересчёт статов с нуля при экипировке
"""

import sqlite3, json, time, logging
from typing import Optional, Dict, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)
DB_NAME = "eldron.db"

@contextmanager
def get_connection():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        if conn: conn.close()

def init_db():
    for attempt in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("""CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY, username TEXT, name TEXT, race TEXT, class_type TEXT,
                    level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0, gold INTEGER DEFAULT 5000,
                    hp INTEGER DEFAULT 30, max_hp INTEGER DEFAULT 30, mp INTEGER DEFAULT 10, max_mp INTEGER DEFAULT 10,
                    strength INTEGER DEFAULT 0, vitality INTEGER DEFAULT 0, agility INTEGER DEFAULT 0, intelligence INTEGER DEFAULT 0,
                    skill_points INTEGER DEFAULT 0,
                    phys_atk INTEGER DEFAULT 5, stealth_atk INTEGER DEFAULT 10, evasion INTEGER DEFAULT 8,
                    phys_def INTEGER DEFAULT 3, magic_def INTEGER DEFAULT 3, magic_atk INTEGER DEFAULT 10,
                    equipment TEXT DEFAULT '{}', inventory TEXT DEFAULT '{}', spells TEXT DEFAULT '[]', buffs TEXT DEFAULT '{}',
                    race_magic_active INTEGER DEFAULT 0, class_magic_used INTEGER DEFAULT 0, summon_hp INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
                c.execute("""CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, details TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
                conn.commit()
            break
        except: 
            if attempt==4: raise
            time.sleep(attempt+1)

def create_player(uid, uname, name, race, cls):
    rb = {"human":{"skill_points":3},"elf":{"agility":3},"dwarf":{"strength":3},"orc":{"vitality":3},"fallen":{"agility":1,"intelligence":2}}
    cb = {"warrior":{"strength":1,"vitality":1},"archer":{"agility":2},"wizard":{"intelligence":2},"bard":{"intelligence":1,"agility":1},"paladin":{"strength":1,"intelligence":1},"necromancer":{"intelligence":1,"vitality":1}}
    b = {"strength":0,"vitality":0,"agility":0,"intelligence":0,"skill_points":0}
    for k in rb.get(race,{}): 
        if k in b: b[k] += rb[race].get(k,0)
    for k in cb.get(cls,{}): 
        if k in b: b[k] += cb[cls].get(k,0)
    patk = 5 + b["strength"] * 4
    satk = 10 + b["agility"] * 11
    eva = 8 + b["agility"] * 3
    pdef = 3 + b["vitality"] + (5 if race=="dwarf" else 0)
    mdef = 3 + b["vitality"]
    matk = 10 + b["intelligence"] * 4
    mhp = 30 + b["vitality"] * 10
    mmp = 10 + b["intelligence"] * 3
    if race == "elf": eva = int(eva * 1.15)
    values = [uid, uname, name, race, cls, 1, 0, 5000, mhp, mhp, mmp, mmp, b["strength"], b["vitality"], b["agility"], b["intelligence"], b["skill_points"], patk, satk, eva, pdef, mdef, matk, "{}", "{}", "[]", "{}", 0, 0, 0, time.time()]
    for attempt in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                placeholders = ",".join(["?"] * len(values))
                c.execute(f"INSERT INTO players VALUES ({placeholders})", values)
                conn.commit()
                add_log(uid, "create_character", f"{name} ({race}, {cls})")
            break
        except Exception as e:
            logger.error(f"❌ create_player error: {e}")
            if attempt == 4: raise
            time.sleep(attempt + 1)

def get_player(uid):
    for attempt in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM players WHERE user_id = ?", (uid,))
                r = c.fetchone()
                if r:
                    p = dict(r)
                    for f in ["equipment", "inventory", "spells", "buffs"]:
                        try: p[f] = json.loads(p[f] or "{}")
                        except: p[f] = {}
                    p["gold"] = int(p.get("gold", 0))
                    return p
            return None
        except:
            if attempt == 4: raise
            time.sleep(attempt + 1)

def update_player(uid, **kw):
    if not kw: return True
    for attempt in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                for f in ["equipment", "inventory", "spells", "buffs"]:
                    if f in kw and isinstance(kw[f], (dict, list)): kw[f] = json.dumps(kw[f])
                    elif f in kw and kw[f] is None: kw[f] = json.dumps({} if f != "spells" else [])
                sc = ", ".join([f"{k}=?" for k in kw])
                c.execute(f"UPDATE players SET {sc} WHERE user_id = ?", list(kw.values()) + [uid])
                conn.commit()
                return True
        except:
            if attempt == 4: raise
            time.sleep(attempt + 1)
    return False

def add_gold(uid, amount):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (amount, uid))
            conn.commit()
            return c.rowcount > 0
    except: return False

def spend_gold(uid, amount):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET gold = gold - ? WHERE user_id = ? AND gold >= ?", (amount, uid, amount))
            conn.commit()
            return c.rowcount > 0
    except: return False

def set_gold(uid, amount):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET gold = ? WHERE user_id = ?", (amount, uid))
            conn.commit()
            return c.rowcount > 0
    except: return False

def update_all_players_gold(amount=5000):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET gold = ?", (amount,))
            conn.commit()
            return True
    except: return False

def add_log(uid, action, details):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO logs(user_id, action, details) VALUES (?, ?, ?)", (uid, action, details))
            conn.commit()
    except: pass

def get_logs(uid, limit=10):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (uid, limit))
            return [dict(r) for r in c.fetchall()]
    except: return []

# ==================== НОВЫЕ ФУНКЦИИ ДЛЯ ПЕРЕРАСЧЁТА СТАТОВ ====================

def get_base_stats(race, class_type):
    """✅ Рассчитывает БАЗОВЫЕ статы (без экипировки) по расе и классу"""
    rb = {"human":{"skill_points":3},"elf":{"agility":3},"dwarf":{"strength":3},"orc":{"vitality":3},"fallen":{"agility":1,"intelligence":2}}
    cb = {"warrior":{"strength":1,"vitality":1},"archer":{"agility":2},"wizard":{"intelligence":2},"bard":{"intelligence":1,"agility":1},"paladin":{"strength":1,"intelligence":1},"necromancer":{"intelligence":1,"vitality":1}}
    
    b = {"strength":0,"vitality":0,"agility":0,"intelligence":0,"skill_points":0}
    for k in rb.get(race,{}): 
        if k in b: b[k] += rb[race].get(k,0)
    for k in cb.get(class_type,{}): 
        if k in b: b[k] += cb[class_type].get(k,0)
    
    return {
        "strength": b["strength"],
        "vitality": b["vitality"],
        "agility": b["agility"],
        "intelligence": b["intelligence"],
        "skill_points": b["skill_points"],
        "phys_atk": 5 + b["strength"] * 4,
        "stealth_atk": 10 + b["agility"] * 11,
        "evasion": 8 + b["agility"] * 3 + (int((8 + b["agility"] * 3) * 0.15) if race == "elf" else 0),
        "phys_def": 3 + b["vitality"] + (5 if race == "dwarf" else 0),
        "magic_def": 3 + b["vitality"],
        "magic_atk": 10 + b["intelligence"] * 4,
        "max_hp": 30 + b["vitality"] * 10,
        "max_mp": 10 + b["intelligence"] * 3,
    }

def calc_equip_bonuses(equip, shop):
    """Рассчитывает бонусы от текущей экипировки"""
    bonuses = {"strength": 0, "vitality": 0, "agility": 0, "intelligence": 0}
    for slot, item_id in equip.items():
        for category, items in shop.items():
            for item in items:
                if item["id"] == item_id and item.get("stat") in bonuses:
                    bonuses[item["stat"]] += item.get("value", 0)
                    break
    return bonuses

def recalc_all_stats(player, shop):
    """✅ ПЕРЕРАСЧИТЫВАЕТ ВСЕ статы с нуля: база + экипировка"""
    # 1. Получаем базовые статы (раса + класс)
    base = get_base_stats(player["race"], player["class_type"])
    
    # 2. Считаем бонусы от экипировки
    equip_bonus = calc_equip_bonuses(player.get("equipment", {}), shop)
    
    # 3. Складываем базу + бонусы экипировки
    for stat in ["strength", "vitality", "agility", "intelligence"]:
        base[stat] += equip_bonus.get(stat, 0)
    
    # 4. Пересчитываем производные характеристики
    base["phys_atk"] = 5 + base["strength"] * 4
    base["stealth_atk"] = 10 + base["agility"] * 11
    base["evasion"] = 8 + base["agility"] * 3 + (int((8 + base["agility"] * 3) * 0.15) if player["race"] == "elf" else 0)
    base["phys_def"] = 3 + base["vitality"] + (5 if player["race"] == "dwarf" else 0)
    base["magic_def"] = 3 + base["vitality"]
    base["magic_atk"] = 10 + base["intelligence"] * 4
    base["max_hp"] = 30 + base["vitality"] * 10
    base["max_mp"] = 10 + base["intelligence"] * 3
    
    # 5. Сохраняем текущие HP/MP (не сбрасываем!)
    base["hp"] = player.get("hp", base["max_hp"])
    base["mp"] = player.get("mp", base["max_mp"])
    
    return base

def add_log(uid, action, details):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO logs(user_id, action, details) VALUES (?, ?, ?)", (uid, action, details))
            conn.commit()
    except: pass

def get_logs(uid, limit=10):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (uid, limit))
            return [dict(r) for r in c.fetchall()]
    except: return []

init_db()
# update_all_players_gold(5000)
