"""
📁 database.py - Работа с базой данных SQLite
✅ Содержит все необходимые функции для бота
"""

import sqlite3
import os
from typing import Optional, Dict, List, Any

# Путь к базе данных
DB_PATH = os.getenv("DB_PATH", "game.db")

def get_connection():
    """Возвращает соединение с базой данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Чтобы получать строки как словари
    return conn

def init_db():
    """Инициализирует таблицы базы данных"""
    with get_connection() as conn:
        c = conn.cursor()
        
        # Таблица игроков
        c.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                race TEXT,
                class_type TEXT,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 5000,
                hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                mp INTEGER DEFAULT 30,
                max_mp INTEGER DEFAULT 30,
                strength INTEGER DEFAULT 5,
                vitality INTEGER DEFAULT 5,
                agility INTEGER DEFAULT 5,
                intelligence INTEGER DEFAULT 5,
                skill_points INTEGER DEFAULT 3,
                phys_atk INTEGER DEFAULT 20,
                stealth_atk INTEGER DEFAULT 40,
                evasion INTEGER DEFAULT 15,
                phys_def INTEGER DEFAULT 5,
                magic_def INTEGER DEFAULT 5,
                magic_atk INTEGER DEFAULT 20,
                inventory TEXT DEFAULT '{}',
                equipment TEXT DEFAULT '{}',
                spells TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица логов
        c.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players (user_id)
            )
        ''')
        
        conn.commit()

# ==================== ФУНКЦИИ ДЛЯ ИГРОКОВ ====================

def create_player(user_id: int, username: str, name: str, race: str, class_type: str) -> bool:
    """Создаёт нового игрока в базе данных"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO players 
                (user_id, username, name, race, class_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, name, race, class_type))
            conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error creating player: {e}")
        return False

def get_player(user_id: int) -> Optional[Dict[str, Any]]:
    """✅ Получает данные игрока по user_id"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row:
                # Преобразуем Row в dict и парсим JSON-поля
                player = dict(row)
                player["inventory"] = json.loads(player["inventory"] or "{}")
                player["equipment"] = json.loads(player["equipment"] or "{}")
                player["spells"] = json.loads(player["spells"] or "[]")
                return player
            return None
    except Exception as e:
        print(f"❌ Error getting player: {e}")
        return None

def update_player(user_id: int, **kwargs) -> bool:
    """Обновляет данные игрока"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            # Парсим JSON-поля если они передаются
            for key in ["inventory", "equipment", "spells"]:
                if key in kwargs and isinstance(kwargs[key], (dict, list)):
                    kwargs[key] = json.dumps(kwargs[key])
            
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            
            c.execute(f"UPDATE players SET {set_clause} WHERE user_id = ?", values)
            conn.commit()
            return c.rowcount > 0
    except Exception as e:
        print(f"❌ Error updating player: {e}")
        return False

def add_gold(user_id: int, amount: int) -> bool:
    """Добавляет золото игроку"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (amount, user_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error adding gold: {e}")
        return False

def spend_gold(user_id: int, amount: int) -> bool:
    """Списывает золото у игрока (если достаточно)"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT gold FROM players WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row and row["gold"] >= amount:
                c.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (amount, user_id))
                conn.commit()
                return True
            return False
    except Exception as e:
        print(f"❌ Error spending gold: {e}")
        return False

def update_all_players_gold(amount: int) -> bool:
    """Устанавливает золото всем игрокам (админ-функция)"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE players SET gold = ?", (amount,))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error updating all players gold: {e}")
        return False

# ==================== ФУНКЦИИ ДЛЯ ЛОГОВ ====================

def add_log(user_id: int, action: str, details: str) -> bool:
    """Добавляет запись в лог действий игрока"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO logs (user_id, action, details)
                VALUES (?, ?, ?)
            ''', (user_id, action, details))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error adding log: {e}")
        return False

def get_logs(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Получает последние логи игрока"""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT action, details, timestamp 
                FROM logs 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            rows = c.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error getting logs: {e}")
        return []

# ==================== ФУНКЦИЯ ПЕРЕРАСЧЁТА СТАТОВ ====================

def recalc_all_stats(player: Dict[str, Any], shop_items: Dict[str, List]) -> Dict[str, Any]:
    """
    Пересчитывает ВСЕ характеристики игрока с нуля.
    
    ✅ ВАЖНО: skill_points НЕ пересчитывается — он сохраняется отдельно!
    
    Returns:
        dict: Словарь с пересчитанными характеристиками (БЕЗ skill_points)
    """
    # Базовые значения от расы/класса (можно расширить)
    base = {
        "phys_atk": 20, "stealth_atk": 40, "evasion": 15,
        "phys_def": 5, "magic_def": 5, "magic_atk": 20,
        "max_hp": 100, "max_mp": 30
    }
    
    # Бонусы от прокачанных навыков
    skill_bonuses = {
        "phys_atk": player["strength"] * 4,
        "stealth_atk": player["agility"] * 8,
        "evasion": player["agility"] * 3,
        "max_hp": player["vitality"] * 10,
        "phys_def": player["vitality"] * 2,
        "magic_def": player["vitality"] * 1,
        "max_mp": player["intelligence"] * 3,
        "magic_atk": player["intelligence"] * 4,
    }
    
    # Бонусы от экипировки
    equip_bonuses = {"strength": 0, "vitality": 0, "agility": 0, "intelligence": 0}
    equipment = player.get("equipment", {})
    
    for slot, item_id in equipment.items():
        # Ищем предмет в shop_items
        for category_items in shop_items.values():
            for item in category_items:
                if item["id"] == item_id and item.get("stat"):
                    stat = item["stat"]
                    if stat in equip_bonuses:
                        equip_bonuses[stat] += item["value"]
                    break
    
    # Итоговые характеристики с учётом экипировки
    final_strength = player["strength"] + equip_bonuses["strength"]
    final_vitality = player["vitality"] + equip_bonuses["vitality"]
    final_agility = player["agility"] + equip_bonuses["agility"]
    final_intelligence = player["intelligence"] + equip_bonuses["intelligence"]
    
    # Пересчитываем производные статы
    final_bonuses = {
        "phys_atk": final_strength * 4,
        "stealth_atk": final_agility * 8,
        "evasion": final_agility * 3,
        "max_hp": final_vitality * 10,
        "phys_def": final_vitality * 2,
        "magic_def": final_vitality * 1,
        "max_mp": final_intelligence * 3,
        "magic_atk": final_intelligence * 4,
    }
    
    # Собираем итоговый словарь
    # ✅ skill_points НЕ включаем — он сохраняется отдельно!
    return {
        "phys_atk": base["phys_atk"] + skill_bonuses["phys_atk"] + final_bonuses["phys_atk"],
        "stealth_atk": base["stealth_atk"] + skill_bonuses["stealth_atk"] + final_bonuses["stealth_atk"],
        "evasion": base["evasion"] + skill_bonuses["evasion"] + final_bonuses["evasion"],
        "phys_def": base["phys_def"] + skill_bonuses["phys_def"] + final_bonuses["phys_def"],
        "magic_def": base["magic_def"] + skill_bonuses["magic_def"] + final_bonuses["magic_def"],
        "magic_atk": base["magic_atk"] + skill_bonuses["magic_atk"] + final_bonuses["magic_atk"],
        "max_hp": base["max_hp"] + skill_bonuses["max_hp"] + final_bonuses["max_hp"],
        "max_mp": base["max_mp"] + skill_bonuses["max_mp"] + final_bonuses["max_mp"],
        # ✅ hp и mp обновляем только если они меньше новых max
        "hp": min(player["hp"], base["max_hp"] + skill_bonuses["max_hp"] + final_bonuses["max_hp"]),
        "mp": min(player["mp"], base["max_mp"] + skill_bonuses["max_mp"] + final_bonuses["max_mp"]),
        # ✅ skill_points НЕ возвращаем — он не должен перезаписываться!
    }

# ==================== ИНИЦИАЛИЗАЦИЯ ====================

# Инициализируем БД при импорте модуля
init_db()
