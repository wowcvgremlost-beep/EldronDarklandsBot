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
    """✅ ИСПРАВЛЕНО: ровно 31 значение для 31 колонки"""
    # Бонусы расы
    rb = {"human":{"skill_points":3},"elf":{"agility":3},"dwarf":{"strength":3},"orc":{"vitality":3},"fallen":{"agility":1,"intelligence":2}}
    # Бонусы класса
    cb = {"warrior":{"strength":1,"vitality":1},"archer":{"agility":2},"wizard":{"intelligence":2},"bard":{"intelligence":1,"agility":1},"paladin":{"strength":1,"intelligence":1},"necromancer":{"intelligence":1,"vitality":1}}
    
    # Считаем бонусы
    b = {"strength":0,"vitality":0,"agility":0,"intelligence":0,"skill_points":0}
    for k in rb.get(race,{}): 
        if k in b: b[k] += rb[race].get(k,0)
    for k in cb.get(cls,{}): 
        if k in b: b[k] += cb[cls].get(k,0)
    
    # Рассчитываем характеристики
    patk = 5 + b["strength"] * 4
    satk = 10 + b["agility"] * 11
    eva = 8 + b["agility"] * 3
    pdef = 3 + b["vitality"] + (5 if race=="dwarf" else 0)
    mdef = 3 + b["vitality"]
    matk = 10 + b["intelligence"] * 4
    mhp = 30 + b["vitality"] * 10
    mmp = 10 + b["intelligence"] * 3
    if race == "elf": eva = int(eva * 1.15)
    
    for att in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                # ✅ РОВНО 31 значение (посчитайте запятые: 30 запятых = 31 значение)
                c.execute("""INSERT INTO players VALUES(
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        uid,           # 1 user_id
                        uname,         # 2 username
                        name,          # 3 name
                        race,          # 4 race
                        cls,           # 5 class_type
                        1,             # 6 level
                        0,             # 7 exp
                        0,             # 8 gold
                        mhp,           # 9 hp
                        mhp,           # 10 max_hp
                        mmp,           # 11 mp
                        mmp,           # 12 max_mp
                        b["strength"], # 13 strength
                        b["vitality"], # 14 vitality
                        b["agility"],  # 15 agility
                        b["intelligence"], # 16 intelligence
                        b["skill_points"], # 17 skill_points
                        patk,          # 18 phys_atk
                        satk,          # 19 stealth_atk
                        eva,           # 20 evasion
                        pdef,          # 21 phys_def
                        mdef,          # 22 magic_def
                        matk,          # 23 magic_atk
                        "{}",          # 24 equipment
                        "{}",          # 25 inventory
                        "[]",          # 26 spells
                        "{}",          # 27 buffs
                        0,             # 28 race_magic_active
                        0,             # 29 class_magic_used
                        0,             # 30 summon_hp
                        time.time()    # 31 created_at
                    ))
                conn.commit()
                add_log(uid, "create_character", f"{name} ({race}, {cls})")
            break
        except Exception as e:
            logger.error(f"❌ create_player error: {e}")
            if att == 4: raise
            time.sleep(att + 1)

def get_player(uid):
    for att in range(5):
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
            if att == 4: raise
            time.sleep(att + 1)

def update_player(uid, **kw):
    if not kw: return True
    for att in range(5):
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
            if att == 4: raise
            time.sleep(att + 1)
    return False

def add_gold(uid, amt):
    for att in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (amt, uid))
                conn.commit()
                return c.rowcount > 0
        except:
            if att == 4: raise
            time.sleep(att + 1)
    return False

def spend_gold(uid, amt):
    for att in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE players SET gold = gold - ? WHERE user_id = ? AND gold >= ?", (amt, uid, amt))
                conn.commit()
                return c.rowcount > 0
        except:
            if att == 4: raise
            time.sleep(att + 1)
    return False

def add_log(uid, act, det):
    for att in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO logs(user_id, action, details) VALUES (?, ?, ?)", (uid, act, det))
                conn.commit()
            break
        except:
            if att == 4: raise
            time.sleep(att + 1)

def get_logs(uid, lim=10):
    for att in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (uid, lim))
                return [dict(r) for r in c.fetchall()]
        except:
            if att == 4: raise
            time.sleep(att + 1)
    return []

def calc_equip_bonuses(equip, shop):
    bn = {"strength":0, "vitality":0, "agility":0, "intelligence":0}
    for slot, iid in equip.items():
        for cat, items in shop.items():
            for it in items:
                if it["id"] == iid and it.get("stat") in bn:
                    bn[it["stat"]] += it.get("value", 0)
                    break
    return bn

def apply_equip_bonuses(p, shop):
    eb = calc_equip_bonuses(p.get("equipment", {}), shop)
    bs = {
        "strength": p["strength"] - eb["strength"],
        "vitality": p["vitality"] - eb["vitality"],
        "agility": p["agility"] - eb["agility"],
        "intelligence": p["intelligence"] - eb["intelligence"]
    }
    for k in eb: p[k] = bs[k] + eb[k]
    p["phys_atk"] = 5 + p["strength"] * 4
    p["stealth_atk"] = 10 + p["agility"] * 11
    p["evasion"] = 8 + p["agility"] * 3
    p["phys_def"] = 3 + p["vitality"]
    p["magic_def"] = 3 + p["vitality"]
    p["magic_atk"] = 10 + p["intelligence"] * 4
    p["max_hp"] = 30 + p["vitality"] * 10
    p["max_mp"] = 10 + p["intelligence"] * 3
    return p

init_db()
