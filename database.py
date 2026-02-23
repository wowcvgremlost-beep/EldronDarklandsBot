import sqlite3
import json
from typing import Optional, Dict, List

# Используем локальный SQLite файл
DB_NAME = "eldron.db"

def get_connection():
    """Создаёт подключение к базе данных"""
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    """Создаёт таблицы при первом запуске"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблица игроков
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица логов
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
    conn.close()

def create_player(user_id: int, username: str, name: str, race: str, class_type: str):
    """Создаёт нового персонажа"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Базовые бонусы расы
    race_bonuses = {
        "human": {"skill_points": 3, "magic": "Благословение: +10% к лечению"},
        "elf": {"agility": 3, "magic": "Природа: Шанс уклонения +15%"},
        "dwarf": {"strength": 3, "magic": "Каменная кожа: +5 Физ.защ в бою"},
        "orc": {"vitality": 3, "magic": "Ярость: +10% урона при HP < 50%"},
        "fallen": {"agility": 1, "intelligence": 2, "magic": "Тень: Первый удар скрытный"}
    }
    
    # Базовые бонусы класса
    class_bonuses = {
        "warrior": {"strength": 1, "vitality": 1, "magic": "Воинский клич: +5 Физ.АТК на 1 ход"},
        "archer": {"agility": 2, "magic": "Точный выстрел: Игнорирует 5 ед. защиты"},
        "wizard": {"intelligence": 2, "magic": "Магический щит: +10 Маг.защ на 1 ход"},
        "bard": {"intelligence": 1, "agility": 1, "magic": "Вдохновение: +2 ко всем характеристикам союзника"},
        "paladin": {"strength": 1, "intelligence": 1, "magic": "Святой свет: Лечение +20 HP"},
        "necromancer": {"intelligence": 1, "vitality": 1, "magic": "Поднять скелета: Призыв помощника"}
    }
    
    # Применяем бонусы
    bonuses = {"strength": 0, "vitality": 0, "agility": 0, "intelligence": 0, "skill_points": 0}
    for key in race_bonuses.get(race, {}):
        if key in bonuses:
            bonuses[key] += race_bonuses[race].get(key, 0)
    for key in class_bonuses.get(class_type, {}):
        if key in bonuses:
            bonuses[key] += class_bonuses[class_type].get(key, 0)
    
    # Рассчитываем боевые характеристики
    phys_atk = 5 + bonuses["strength"] * 4
    stealth_atk = 10 + bonuses["agility"] * 8 + bonuses["agility"] * 3
    evasion = 8 + bonuses["agility"] * 3
    phys_def = 3 + bonuses["vitality"]
    magic_def = 3 + bonuses["vitality"]
    magic_atk = 10 + bonuses["intelligence"] * 4
    max_hp = 30 + bonuses["vitality"] * 10
    max_mp = 10 + bonuses["intelligence"] * 3
    
    cursor.execute("""
        INSERT INTO players (
            user_id, username, name, race, class_type,
            strength, vitality, agility, intelligence, skill_points,
            phys_atk, stealth_atk, evasion, phys_def, magic_def, magic_atk,
            hp, max_hp, mp, max_mp,
            equipment, inventory, spells
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, username, name, race, class_type,
        bonuses["strength"], bonuses["vitality"], bonuses["agility"], bonuses["intelligence"], bonuses["skill_points"],
        phys_atk, stealth_atk, evasion, phys_def, magic_def, magic_atk,
        max_hp, max_hp, max_mp, max_mp,
        json.dumps({}), json.dumps({}), json.dumps([])
    ))
    
    add_log(user_id, "create_character", f"{name} ({race}, {class_type})")
    conn.commit()
    conn.close()

def get_player(user_id: int) -> Optional[Dict]:
    """Получает данные игрока"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        player = dict(row)
        player["equipment"] = json.loads(player["equipment"] or "{}")
        player["inventory"] = json.loads(player["inventory"] or "{}")
        player["spells"] = json.loads(player["spells"] or "[]")
        return player
    return None

def update_player(user_id: int, **kwargs):
    """Обновляет данные игрока"""
    if not kwargs:
        return
    conn = get_connection()
    cursor = conn.cursor()
    
    # Обрабатываем JSON-поля
    json_fields = ["equipment", "inventory", "spells"]
    for field in json_fields:
        if field in kwargs and isinstance(kwargs[field], (dict, list)):
            kwargs[field] = json.dumps(kwargs[field])
    
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]
    
    cursor.execute(f"UPDATE players SET {set_clause} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

def add_log(user_id: int, action: str, details: str):
    """Добавляет запись в лог"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, action, details)
    )
    conn.commit()
    conn.close()

def get_logs(user_id: int, limit: int = 10) -> List[Dict]:
    """Получает последние логи игрока"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Инициализация БД при импорте
init_db()
