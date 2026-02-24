import sqlite3
import json
import time
from typing import Optional, Dict, List
from contextlib import contextmanager

DB_NAME = "eldron.db"

@contextmanager
def get_connection():
    """Контекстный менеджер для безопасного подключения к БД"""
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
    """Создаёт таблицы при первом запуске"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS players (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        name TEXT,
                        race TEXT,
                        class_type TEXT,
                        level INTEGER DEFAULT 1,
                        exp INTEGER DEFAULT 0,
                        gold INTEGER DEFAULT 0,
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
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        action TEXT,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
            break
        except sqlite3.OperationalError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (attempt + 1))

def create_player(user_id: int, username: str, name: str, race: str, class_type: str):
    """Создаёт нового персонажа"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                race_bonuses = {
                    "human": {"skill_points": 3},
                    "elf": {"agility": 3},
                    "dwarf": {"strength": 3},
                    "orc": {"vitality": 3},
                    "fallen": {"agility": 1, "intelligence": 2}
                }
                
                class_bonuses = {
                    "warrior": {"strength": 1, "vitality": 1},
                    "archer": {"agility": 2},
                    "wizard": {"intelligence": 2},
                    "bard": {"intelligence": 1, "agility": 1},
                    "paladin": {"strength": 1, "intelligence": 1},
                    "necromancer": {"intelligence": 1, "vitality": 1}
                }
                
                bonuses = {"strength": 0, "vitality": 0, "agility": 0, "intelligence": 0, "skill_points": 0}
                for key in race_bonuses.get(race, {}):
                    if key in bonuses:
                        bonuses[key] += race_bonuses[race].get(key, 0)
                for key in class_bonuses.get(class_type, {}):
                    if key in bonuses:
                        bonuses[key] += class_bonuses[class_type].get(key, 0)
                
                phys_atk = 5 + bonuses["strength"] * 4
                stealth_atk = 10 + bonuses["agility"] * 8 + bonuses["agility"] * 3
                evasion = 8 + bonuses["agility"] * 3
                phys_def = 3 + bonuses["vitality"]
                magic_def = 3 + bonuses["vitality"]
                magic_atk = 10 + bonuses["intelligence"] * 4
                max_hp = 30 + bonuses["vitality"] * 10
                max_mp = 10 + bonuses["intelligence"] * 3
                
                # Применяем пассивную магию расы
                if race == "dwarf":
                    phys_def += 5  # Каменная кожа +5
                if race == "elf":
                    evasion = int(evasion * 1.15)  # Природа +15%
                
                cursor.execute("""
                    INSERT INTO players (
                        user_id, username, name, race, class_type,
                        strength, vitality, agility, intelligence, skill_points,
                        phys_atk, stealth_atk, evasion, phys_def, magic_def, magic_atk,
                        hp, max_hp, mp, max_mp,
                        equipment, inventory, spells,
                        buffs, race_magic_active, class_magic_used, summon_hp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, username, name, race, class_type,
                    bonuses["strength"], bonuses["vitality"], bonuses["agility"], bonuses["intelligence"], bonuses["skill_points"],
                    phys_atk, stealth_atk, evasion, phys_def, magic_def, magic_atk,
                    max_hp, max_hp, max_mp, max_mp,
                    json.dumps({}), json.dumps({}), json.dumps([]),
                    json.dumps({}), 0, 0, 0
                ))
                
                conn.commit()
                add_log(user_id, "create_character", f"{name} ({race}, {class_type})")
            break
        except sqlite3.OperationalError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (attempt + 1))

def get_player(user_id: int) -> Optional[Dict]:
    """Получает данные игрока"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                
                if row:
                    player = dict(row)
                    player["equipment"] = json.loads(player["equipment"] or "{}")
                    player["inventory"] = json.loads(player["inventory"] or "{}")
                    player["spells"] = json.loads(player["spells"] or "[]")
                    player["buffs"] = json.loads(player["buffs"] or "{}")
                    return player
            return None
        except sqlite3.OperationalError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (attempt + 1))

def update_player(user_id: int, **kwargs):
    """Обновляет данные игрока"""
    if not kwargs:
        return
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                json_fields = ["equipment", "inventory", "spells", "buffs"]
                for field in json_fields:
                    if field in kwargs and isinstance(kwargs[field], (dict, list)):
                        kwargs[field] = json.dumps(kwargs[field])
                
                set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
                values = list(kwargs.values()) + [user_id]
                
                cursor.execute(f"UPDATE players SET {set_clause} WHERE user_id = ?", values)
                conn.commit()
            break
        except sqlite3.OperationalError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (attempt + 1))

def add_log(user_id: int, action: str, details: str):
    """Добавляет запись в лог"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
                    (user_id, action, details)
                )
                conn.commit()
            break
        except sqlite3.OperationalError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (attempt + 1))

def get_logs(user_id: int, limit: int = 10) -> List[Dict]:
    """Получает последние логи игрока"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (user_id, limit)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.OperationalError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (attempt + 1))
    return []

# Инициализация БД при импорте
init_db()
