"""
📁 database.py - Работа с базой данных SQLite
Здесь все функции для сохранения и получения данных игроков
"""

import sqlite3
import json
import time
import logging
from typing import Optional, Dict, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)
DB_NAME = "eldron.db"

# ==================== ПОДКЛЮЧЕНИЕ К БД ====================
@contextmanager
def get_connection():
    """Безопасное подключение к SQLite с таймаутом"""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")  # Улучшает производительность
        conn.row_factory = sqlite3.Row  # Возвращает строки как словари
        yield conn
    finally:
        if conn:
            conn.close()

# ==================== ИНИЦИАЛИЗАЦИЯ БД ====================
def init_db():
    """Создаёт таблицы при первом запуске"""
    for attempt in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                
                # Таблица игроков (31 колонка)
                c.execute("""CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    name TEXT,
                    race TEXT,
                    class_type TEXT,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    gold INTEGER DEFAULT 5000,
                    hp INTEGER DEFAULT 30,
                    max_hp INTEGER DEFAULT 30,
                    mp INTEGER DEFAULT 10,
                    max_mp INTEGER DEFAULT 10,
                    strength INTEGER DEFAULT 0,
                    vitality INTEGER DEFAULT 0,
                    agility INTEGER DEFAULT 0,
                    intelligence INTEGER DEFAULT 0,
                    skill_points INTEGER DEFAULT 0,
                    phys_atk INTEGER DEFAULT 5,
                    stealth_atk INTEGER DEFAULT 10,
                    evasion INTEGER DEFAULT 8,
                    phys_def INTEGER DEFAULT 3,
                    magic_def INTEGER DEFAULT 3,
                    magic_atk INTEGER DEFAULT 10,
                    equipment TEXT DEFAULT '{}',
                    inventory TEXT DEFAULT '{}',
                    spells TEXT DEFAULT '[]',
                    buffs TEXT DEFAULT '{}',
                    race_magic_active INTEGER DEFAULT 0,
                    class_magic_used INTEGER DEFAULT 0,
                    summon_hp INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
                
                # Таблица логов
                c.execute("""CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
                
                conn.commit()
                logger.info("✅ База данных инициализирована")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка init_db (попытка {attempt+1}): {e}")
            if attempt == 4:
                raise
            time.sleep(attempt + 1)

# ==================== СОЗДАНИЕ ИГРОКА ====================
def create_player(uid, uname, name, race, cls):
    """Создаёт нового персонажа с расчётом характеристик"""
    
    # 📊 Бонусы рас (можно добавлять новые расы здесь)
    race_bonuses = {
        "human": {"skill_points": 3},
        "elf": {"agility": 3},
        "dwarf": {"strength": 3},
        "orc": {"vitality": 3},
        "fallen": {"agility": 1, "intelligence": 2}
    }
    
    # 📊 Бонусы классов (можно добавлять новые классы здесь)
    class_bonuses = {
        "warrior": {"strength": 1, "vitality": 1},
        "archer": {"agility": 2},
        "wizard": {"intelligence": 2},
        "bard": {"intelligence": 1, "agility": 1},
        "paladin": {"strength": 1, "intelligence": 1},
        "necromancer": {"intelligence": 1, "vitality": 1}
    }
    
    # Считаем общие бонусы
    bonuses = {"strength": 0, "vitality": 0, "agility": 0, "intelligence": 0, "skill_points": 0}
    for k in race_bonuses.get(race, {}):
        if k in bonuses:
            bonuses[k] += race_bonuses[race].get(k, 0)
    for k in class_bonuses.get(cls, {}):
        if k in bonuses:
            bonuses[k] += class_bonuses[cls].get(k, 0)
    
    # Рассчитываем боевые характеристики по формулам
    patk = 5 + bonuses["strength"] * 4
    satk = 10 + bonuses["agility"] * 11
    eva = 8 + bonuses["agility"] * 3
    pdef = 3 + bonuses["vitality"] + (5 if race == "dwarf" else 0)
    mdef = 3 + bonuses["vitality"]
    matk = 10 + bonuses["intelligence"] * 4
    mhp = 30 + bonuses["vitality"] * 10
    mmp = 10 + bonuses["intelligence"] * 3
    if race == "elf":
        eva = int(eva * 1.15)  # Эльфы +15% уклонения
    
    # Формируем список значений (автоматически 31 значение)
    values = [
        uid, uname, name, race, cls,           # 1-5: идентификаторы
        1, 0, 5000,                            # 6-8: level, exp, gold (5000 для новых!)
        mhp, mhp, mmp, mmp,                    # 9-12: hp, max_hp, mp, max_mp
        bonuses["strength"], bonuses["vitality"], bonuses["agility"], 
        bonuses["intelligence"], bonuses["skill_points"],  # 13-17: навыки
        patk, satk, eva, pdef, mdef, matk,     # 18-23: боевые статы
        "{}", "{}", "[]", "{}",                # 24-27: equipment, inventory, spells, buffs
        0, 0, 0,                               # 28-30: флаги магии
        time.time()                            # 31: created_at
    ]
    
    logger.info(f"🔍 create_player: {len(values)} значений для INSERT")
    
    for attempt in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                placeholders = ",".join(["?"] * len(values))
                c.execute(f"INSERT INTO players VALUES ({placeholders})", values)
                conn.commit()
                add_log(uid, "create_character", f"{name} ({race}, {cls})")
                logger.info(f"✅ Персонаж создан: {name} | Золото: 5000")
            break
        except Exception as e:
            logger.error(f"❌ create_player error: {e}")
            if attempt == 4:
                raise
            time.sleep(attempt + 1)

# ==================== ПОЛУЧЕНИЕ ИГРОКА ====================
def get_player(uid):
    """Получает данные игрока из БД"""
    for attempt in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM players WHERE user_id = ?", (uid,))
                r = c.fetchone()
                if r:
                    p = dict(r)
                    # Преобразуем JSON строки обратно в словари/списки
                    for f in ["equipment", "inventory", "spells", "buffs"]:
                        try:
                            p[f] = json.loads(p[f] or "{}")
                        except:
                            p[f] = {}
                    p["gold"] = int(p.get("gold", 0))
                    return p
            return None
        except Exception as e:
            logger.error(f"❌ get_player error: {e}")
            if attempt == 4:
                raise
            time.sleep(attempt + 1)

# ==================== ОБНОВЛЕНИЕ ИГРОКА ====================
def update_player(uid, **kw):
    """Обновляет поля игрока в БД"""
    if not kw:
        return True
    for attempt in range(5):
        try:
            with get_connection() as conn:
                c = conn.cursor()
                # Преобразуем словари/списки в JSON строки
                for f in ["equipment", "inventory", "spells", "buffs"]:
                    if f in kw and isinstance(kw[f], (dict, list)):
                        kw[f] = json.dumps(kw[f])
                    elif f in kw and kw[f] is None:
                        kw[f] = json.dumps({} if f != "spells" else [])
                sc = ", ".join([f"{k}=?" for k in kw])
                c.execute(f"UPDATE players SET {sc} WHERE user_id = ?", list(kw.values()) + [uid])
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ update_player error: {e}")
            if attempt == 4:
                raise
            time.sleep(attempt + 1)
    return False

# ==================== ЗОЛОТО ====================
def add_gold(uid, amount):
    """Добавляет золото игроку"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (amount, uid))
            conn.commit()
            logger.info(f"💰 Добавлено {amount} золота игроку {uid}")
            return c.rowcount > 0
    except Exception as e:
        logger.error(f"❌ add_gold error: {e}")
        return False

def spend_gold(uid, amount):
    """Списывает золото (только если достаточно)"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET gold = gold - ? WHERE user_id = ? AND gold >= ?", (amount, uid, amount))
            conn.commit()
            return c.rowcount > 0
    except Exception as e:
        logger.error(f"❌ spend_gold error: {e}")
        return False

def set_gold(uid, amount):
    """Устанавливает точное количество золота (для админа)"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET gold = ? WHERE user_id = ?", (amount, uid))
            conn.commit()
            logger.info(f"💰 Установлено {amount} золота игроку {uid}")
            return c.rowcount > 0
    except Exception as e:
        logger.error(f"❌ set_gold error: {e}")
        return False

def update_all_players_gold(amount=5000):
    """⚠️ ОБНОВЛЯЕТ ЗОЛОТО ВСЕМ ИГРОКАМ (для тестов)"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET gold = ?", (amount,))
            conn.commit()
            logger.info(f"💰 Золото обновлено для {c.rowcount} игроков на {amount}")
            return True
    except Exception as e:
        logger.error(f"❌ update_all_players_gold error: {e}")
        return False

# ==================== ЛОГИ ====================
def add_log(uid, action, details):
    """Добавляет запись в лог действий"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO logs(user_id, action, details) VALUES (?, ?, ?)", (uid, action, details))
            conn.commit()
    except Exception as e:
        logger.error(f"❌ add_log error: {e}")

def get_logs(uid, limit=10):
    """Получает последние логи игрока"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (uid, limit))
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        logger.error(f"❌ get_logs error: {e}")
        return []

# ==================== ЭКИПИРОВКА ====================
def calc_equip_bonuses(equip, shop):
    """Рассчитывает бонусы от экипировки"""
    bonuses = {"strength": 0, "vitality": 0, "agility": 0, "intelligence": 0}
    for slot, item_id in equip.items():
        for category, items in shop.items():
            for item in items:
                if item["id"] == item_id and item.get("stat") in bonuses:
                    bonuses[item["stat"]] += item.get("value", 0)
                    break
    return bonuses

def apply_equip_bonuses(player, shop):
    """Применяет бонусы экипировки к статам игрока"""
    equip_bonuses = calc_equip_bonuses(player.get("equipment", {}), shop)
    
    # Вычисляем базовые статы (без экипировки)
    base_stats = {
        "strength": player["strength"] - equip_bonuses["strength"],
        "vitality": player["vitality"] - equip_bonuses["vitality"],
        "agility": player["agility"] - equip_bonuses["agility"],
        "intelligence": player["intelligence"] - equip_bonuses["intelligence"]
    }
    
    # Применяем бонусы
    for stat, bonus in equip_bonuses.items():
        player[stat] = base_stats[stat] + bonus
    
    # Пересчитываем боевые характеристики
    player["phys_atk"] = 5 + player["strength"] * 4
    player["stealth_atk"] = 10 + player["agility"] * 11
    player["evasion"] = 8 + player["agility"] * 3
    player["phys_def"] = 3 + player["vitality"]
    player["magic_def"] = 3 + player["vitality"]
    player["magic_atk"] = 10 + player["intelligence"] * 4
    player["max_hp"] = 30 + player["vitality"] * 10
    player["max_mp"] = 10 + player["intelligence"] * 3
    
    return player

# ==================== ИНИЦИАЛИЗАЦИЯ ПРИ ИМПОРТЕ ====================
init_db()

# 🎁 РАЗОВАЯ НАСТРОЙКА: раскомментируйте для обновления золота всем игрокам
# update_all_players_gold(5000)
