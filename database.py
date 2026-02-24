import sqlite3
import json
import time
import logging
from typing import Optional, Dict, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)
DB_NAME = "eldron.db"

@contextmanager
def get_connection():
    """Безопасное подключение к SQLite"""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        if conn:
            conn.close()

def init_db():
    """Инициализация таблиц"""
    for attempt in range(5):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS players (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT, name TEXT, race TEXT, class_type TEXT,
                        level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0, gold INTEGER DEFAULT 5000,
                        hp INTEGER DEFAULT 30, max_hp INTEGER DEFAULT 30,
                        mp INTEGER DEFAULT 10, max_mp INTEGER DEFAULT 10,
                        strength INTEGER DEFAULT 0, vitality INTEGER DEFAULT 0,
                        agility INTEGER DEFAULT 0, intelligence INTEGER DEFAULT 0,
                        skill_points INTEGER DEFAULT 0,
                        phys_atk INTEGER DEFAULT 5, stealth_atk INTEGER DEFAULT 10,
                        evasion INTEGER DEFAULT 8, phys_def INTEGER DEFAULT 3,
                        magic_def INTEGER DEFAULT 3, magic_atk INTEGER DEFAULT 10,
                        equipment TEXT DEFAULT '{}', inventory TEXT DEFAULT '{}',
                        spells TEXT DEFAULT '[]', buffs TEXT DEFAULT '{}',
                        race_magic_active INTEGER DEFAULT 0,
                        class_magic_used INTEGER DEFAULT 0,
                        summon_hp INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER, action TEXT, details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            break
        except sqlite3.OperationalError as e:
            if attempt == 4:
                raise
            time.sleep(attempt + 1)

def create_player(user_id: int, username: str, name: str, race: str, class_type: str):
    """Создание персонажа"""
    race_bonuses = {
        "human": {"skill_points": 3}, "elf": {"agility": 3},
        "dwarf": {"strength": 3}, "orc": {"vitality": 3},
        "fallen": {"agility": 1, "intelligence": 2}
    }
    class_bonuses = {
        "warrior": {"strength": 1, "vitality": 1}, "archer": {"agility": 2},
        "wizard": {"intelligence": 2}, "bard": {"intelligence": 1, "agility": 1},
        "paladin": {"strength": 1, "intelligence": 1},
        "necromancer": {"intelligence": 1, "vitality": 1}
    }
    
    bonuses = {"strength": 0, "vitality": 0, "agility": 0, "intelligence": 0, "skill_points": 0}
    for k in race_bonuses.get(race, {}):
        if k in bonuses: bonuses[k] += race_bonuses[race].get(k, 0)
    for k in class_bonuses.get(class_type, {}):
        if k in bonuses: bonuses[k] += class_bonuses[class_type].get(k, 0)
    
    phys_atk = 5 + bonuses["strength"] * 4
    stealth_atk = 10 + bonuses["agility"] * 11
    evasion = 8 + bonuses["agility"] * 3
    phys_def = 3 + bonuses["vitality"] + (5 if race == "dwarf" else 0)
    magic_def = 3 + bonuses["vitality"]
    magic_atk = 10 + bonuses["intelligence"] * 4
    max_hp = 30 + bonuses["vitality"] * 10
    max_mp = 10 + bonuses["intelligence"] * 3
    
    if race == "elf":
        evasion = int(evasion * 1.15)
    
    for attempt in range(5):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO players (user_id, username, name, race, class_type,
                        strength, vitality, agility, intelligence, skill_points,
                        phys_atk, stealth_atk, evasion, phys_def, magic_def, magic_atk,
                        hp, max_hp, mp, max_mp, equipment, inventory, spells,
                        buffs, race_magic_active, class_magic_used, summon_hp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, username, name, race, class_type,
                    bonuses["strength"], bonuses["vitality"], bonuses["agility"],
                    bonuses["intelligence"], bonuses["skill_points"],
                    phys_atk, stealth_atk, evasion, phys_def, magic_def, magic_atk,
                    max_hp, max_hp, max_mp, max_mp,
                    json.dumps({}), json.dumps({}), json.dumps([]),
                    json.dumps({}), 0, 0, 0
                ))
                conn.commit()
                add_log(user_id, "create_character", f"{name} ({race}, {class_type})")
            break
        except sqlite3.OperationalError:
            if attempt == 4: raise
            time.sleep(attempt + 1)

def get_player(user_id: int) -> Optional[Dict]:
    """Получение данных игрока"""
    for attempt in range(5):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    player = dict(row)
                    for field in ["equipment", "inventory", "spells", "buffs"]:
                        try:
                            player[field] = json.loads(player[field] or "{}")
                        except:
                            player[field] = {}
                    return player
            return None
        except sqlite3.OperationalError:
            if attempt == 4: raise
            time.sleep(attempt + 1)

def update_player(user_id: int, **kwargs):
    """Обновление данных игрока — надёжная версия"""
    if not kwargs: 
        return True
    
    for attempt in range(5):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                # Обрабатываем JSON-поля: преобразуем dict/list в JSON-строку
                json_fields = ["equipment", "inventory", "spells", "buffs"]
                for field in json_fields:
                    if field in kwargs:
                        if isinstance(kwargs[field], (dict, list)):
                            kwargs[field] = json.dumps(kwargs[field])
                        elif kwargs[field] is None:
                            kwargs[field] = json.dumps({} if field != "spells" else [])
                
                # Формируем SQL-запрос
                set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
                values = list(kwargs.values()) + [user_id]
                
                cursor.execute(f"UPDATE players SET {set_clause} WHERE user_id = ?", values)
                
                # Проверяем, что строка обновилась
                if cursor.rowcount == 0:
                    logger.warning(f"⚠️ update_player: нет строк для user_id={user_id}")
                
                conn.commit()
                
                # Возвращаем успех
                return True
        except sqlite3.OperationalError as e:
            logger.error(f"❌ DB error (attempt {attempt+1}): {e}")
            if attempt == 4:
                raise
            time.sleep(attempt + 1)
    
    return False

def add_gold(user_id: int, amount: int) -> bool:
    """Надёжное добавление золота (атомарная операция)"""
    for attempt in range(5):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE players SET gold = gold + ? WHERE user_id = ?",
                    (amount, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.OperationalError:
            if attempt == 4: raise
            time.sleep(attempt + 1)
    return False

def spend_gold(user_id: int, amount: int) -> bool:
    """Надёжное списание золота (только если достаточно)"""
    for attempt in range(5):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # Списываем только если золота достаточно
                cursor.execute(
                    "UPDATE players SET gold = gold - ? WHERE user_id = ? AND gold >= ?",
                    (amount, user_id, amount)
                )
                conn.commit()
                return cursor.rowcount > 0  # True если строка обновилась
        except sqlite3.OperationalError:
            if attempt == 4: raise
            time.sleep(attempt + 1)
    return False

def add_log(user_id: int, action: str, details: str):
    """Добавление записи в лог"""
    for attempt in range(5):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
                    (user_id, action, details)
                )
                conn.commit()
            break
        except sqlite3.OperationalError:
            if attempt == 4: raise
            time.sleep(attempt + 1)

def get_logs(user_id: int, limit: int = 10) -> List[Dict]:
    """Получение логов"""
    for attempt in range(5):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (user_id, limit)
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            if attempt == 4: raise
            time.sleep(attempt + 1)
    return []

def calculate_stats_from_equipment(equipment: Dict, shop_items: Dict) -> Dict:
    """Рассчитывает бонусы от экипировки"""
    bonuses = {"strength": 0, "vitality": 0, "agility": 0, "intelligence": 0}
    for slot, item_id in equipment.items():
        for category, items in shop_items.items():
            for item in items:
                if item["id"] == item_id:
                    stat = item.get("stat")
                    value = item.get("value", 0)
                    if stat and stat in bonuses:
                        bonuses[stat] += value
                    break
    return bonuses

def apply_equipment_bonuses(player: Dict, shop_items: Dict) -> Dict:
    """Применяет бонусы экипировки к статам"""
    equip_bonuses = calculate_stats_from_equipment(player.get("equipment", {}), shop_items)
    
    # Сохраняем базовые значения (без экипировки)
    base_str = player.get("base_strength", player["strength"] - equip_bonuses["strength"])
    base_vit = player.get("base_vitality", player["vitality"] - equip_bonuses["vitality"])
    base_agi = player.get("base_agility", player["agility"] - equip_bonuses["agility"])
    base_int = player.get("base_intelligence", player["intelligence"] - equip_bonuses["intelligence"])
    
    # Применяем бонусы
    player["strength"] = base_str + equip_bonuses["strength"]
    player["vitality"] = base_vit + equip_bonuses["vitality"]
    player["agility"] = base_agi + equip_bonuses["agility"]
    player["intelligence"] = base_int + equip_bonuses["intelligence"]
    
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

# Инициализация БД при импорте
init_db()
