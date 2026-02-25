"""
📁 shop.py - Данные магазина предметов
✅ Можно легко добавлять новые товары в соответствующие категории
"""

# 🏪 ПРЕДМЕТЫ МАГАЗИНА
SHOP_ITEMS = {
    "potions": [
        {"id": "hp_small", "name": "🧪 Малое зелье HP", "type_name": "Зелья", "type_num": "", "effect": "+30 HP", "price": 50, "stat": "hp", "value": 30, "slot": None, "usable": True},
        {"id": "hp_medium", "name": "🧪 Среднее зелье HP", "type_name": "Зелья", "type_num": "", "effect": "+60 HP", "price": 100, "stat": "hp", "value": 60, "slot": None, "usable": True},
        {"id": "hp_large", "name": "🧪 Большое зелье HP", "type_name": "Зелья", "type_num": "", "effect": "+100 HP", "price": 150, "stat": "hp", "value": 100, "slot": None, "usable": True},
        {"id": "mp_small", "name": "🧪 Малое зелье MP", "type_name": "Зелья", "type_num": "", "effect": "+30 MP", "price": 50, "stat": "mp", "value": 30, "slot": None, "usable": True},
        {"id": "mp_medium", "name": "🧪 Среднее зелье MP", "type_name": "Зелья", "type_num": "", "effect": "+60 MP", "price": 100, "stat": "mp", "value": 60, "slot": None, "usable": True},
        {"id": "mp_large", "name": "🧪 Большое зелье MP", "type_name": "Зелья", "type_num": "", "effect": "+100 MP", "price": 150, "stat": "mp", "value": 100, "slot": None, "usable": True},
    ],
    "weapons": [
        {"id": "sword_apprentice", "name": "⚔️ Меч Ученика", "type_name": "Оружия", "type_num": "1", "effect": "+1 Сила", "price": 150, "stat": "strength", "value": 1, "slot": "weapon_1", "usable": False},
        {"id": "shield_apprentice", "name": "🛡️ Щит Ученика", "type_name": "Оружия", "type_num": "2", "effect": "+1 Живучесть", "price": 150, "stat": "vitality", "value": 1, "slot": "weapon_2", "usable": False},
        {"id": "bow_apprentice", "name": "🏹 Лук Ученика", "type_name": "Оружия", "type_num": "1", "effect": "+1 Ловкость", "price": 150, "stat": "agility", "value": 1, "slot": "weapon_1", "usable": False},
        {"id": "arrows_apprentice", "name": "🏹 Стрелы Ученика", "type_name": "Оружия", "type_num": "2", "effect": "+1 Ловкость", "price": 150, "stat": "agility", "value": 1, "slot": "weapon_2", "usable": False},
        {"id": "staff_apprentice", "name": "🔮 Посох Ученика", "type_name": "Оружия", "type_num": "1", "effect": "+1 Интеллект", "price": 150, "stat": "intelligence", "value": 1, "slot": "weapon_1", "usable": False},
        {"id": "orb_apprentice", "name": "🔮 Сфера Ученика", "type_name": "Оружия", "type_num": "2", "effect": "+1 Интеллект", "price": 150, "stat": "intelligence", "value": 1, "slot": "weapon_2", "usable": False},
    ],
    "armor": [
        {"id": "helm_apprentice", "name": "⛑️ Шлем Ученика", "type_name": "Экипировка", "type_num": "1", "effect": "+1 Живучесть", "price": 200, "stat": "vitality", "value": 1, "slot": "armor_1", "usable": False},
        {"id": "armor_apprentice", "name": "🛡️ Броня Ученика", "type_name": "Экипировка", "type_num": "2", "effect": "+1 Живучесть", "price": 200, "stat": "vitality", "value": 1, "slot": "armor_2", "usable": False},
        {"id": "pants_apprentice", "name": "👖 Штаны Ученика", "type_name": "Экипировка", "type_num": "3", "effect": "+1 Ловкость", "price": 200, "stat": "agility", "value": 1, "slot": "armor_3", "usable": False},
        {"id": "boots_apprentice", "name": "👢 Ботинки Ученика", "type_name": "Экипировка", "type_num": "4", "effect": "+1 Ловкость", "price": 200, "stat": "agility", "value": 1, "slot": "armor_4", "usable": False},
        {"id": "arms_apprentice", "name": "💪 Руки Ученика", "type_name": "Экипировка", "type_num": "5", "effect": "+1 Сила", "price": 200, "stat": "strength", "value": 1, "slot": "armor_5", "usable": False},
        {"id": "gloves_apprentice", "name": "🧤 Перчатки Ученика", "type_name": "Экипировка", "type_num": "6", "effect": "+1 Сила", "price": 200, "stat": "strength", "value": 1, "slot": "armor_6", "usable": False},
    ],
    "accessories": [
        {"id": "amulet_agility", "name": "📿 Амулет Ловкости", "type_name": "Аксессуары", "type_num": "1", "effect": "+2 Ловкость", "price": 400, "stat": "agility", "value": 2, "slot": "accessory_1", "usable": False},
        {"id": "ring_protection", "name": "💍 Кольцо Защиты", "type_name": "Аксессуары", "type_num": "2", "effect": "+2 Живучесть", "price": 400, "stat": "vitality", "value": 2, "slot": "accessory_2", "usable": False},
        {"id": "chain_strength", "name": "⛓️ Цепь Силы", "type_name": "Аксессуары", "type_num": "3", "effect": "+2 Сила", "price": 400, "stat": "strength", "value": 2, "slot": "accessory_3", "usable": False},
    ],
    "other": [
        {"id": "scroll_exp", "name": "📜 Свиток опыта", "type_name": "Разное", "type_num": "", "effect": "+50 Опыта", "price": 500, "stat": "exp", "value": 50, "slot": None, "usable": True},
    ]
}

# 🔍 Вспомогательные функции
def get_item_name_by_id(item_id: str) -> str:
    """Возвращает название предмета по ID"""
    for category_items in SHOP_ITEMS.values():
        for item in category_items:
            if item["id"] == item_id:
                return item["name"]
    return item_id

def get_item_by_id(item_id: str) -> dict | None:
    """Возвращает полный словарь предмета по ID"""
    for category_items in SHOP_ITEMS.values():
        for item in category_items:
            if item["id"] == item_id:
                return item
    return None

def is_equippable(item_id: str) -> bool:
    """Проверяет, можно ли предмет экипировать"""
    item = get_item_by_id(item_id)
    return item is not None and item.get("slot") is not None

def is_usable(item_id: str) -> bool:
    """Проверяет, можно ли предмет применить"""
    item = get_item_by_id(item_id)
    return item is not None and item.get("usable", False)
