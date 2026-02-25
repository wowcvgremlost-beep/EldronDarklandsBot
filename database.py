def recalc_all_stats(player: dict, shop_items: dict) -> dict:
    """
    ✅ ИСПРАВЛЕНО: skill_points НЕ пересчитывается — он сохраняется как есть!
    
    Пересчитывает ВСЕ характеристики персонажа с нуля на основе:
    - Базовых статов расы/класса
    - Прокачанных навыков (strength, agility, vitality, intelligence)
    - Экипированных предметов
    
    Args:
        player: Словарь с данными игрока из БД
        shop_items: Словарь SHOP_ITEMS из shop.py
        
    Returns:
        dict: Словарь с пересчитанными характеристиками (БЕЗ skill_points!)
    """
    # Базовые значения
    base = get_base_stats(player["race"], player["class_type"])
    
    # Бонусы от прокачанных навыков
    skill_bonuses = {
        "phys_atk": player["strength"] * 4,
        "stealth_atk": player["agility"] * 8,
        "evasion": player["agility"] * 3,
        "max_hp": player["vitality"] * 10,
        "hp": player["vitality"] * 10,  # HP тоже увеличивается
        "phys_def": player["vitality"] * 1 + player["vitality"] * 1,  # +1 от vitality
        "magic_def": player["vitality"] * 1,
        "max_mp": player["intelligence"] * 3,
        "mp": player["intelligence"] * 3,  # MP тоже увеличивается
        "magic_atk": player["intelligence"] * 4,
    }
    
    # Бонусы от экипировки
    equip_bonuses = {"strength": 0, "vitality": 0, "agility": 0, "intelligence": 0}
    equipment = player.get("equipment", {})
    
    for slot, item_id in equipment.items():
        item = next((i for cat in shop_items.values() for i in cat if i["id"] == item_id), None)
        if item and item.get("stat"):
            stat = item["stat"]
            if stat in equip_bonuses:
                equip_bonuses[stat] += item["value"]
    
    # ✅ ДОБАВЛЯЕМ бонусы экипировки к основным характеристикам
    # Это нужно для правильного пересчёта производных статов
    final_strength = player["strength"] + equip_bonuses["strength"]
    final_vitality = player["vitality"] + equip_bonuses["vitality"]
    final_agility = player["agility"] + equip_bonuses["agility"]
    final_intelligence = player["intelligence"] + equip_bonuses["intelligence"]
    
    # Пересчитываем производные статы с учётом экипировки
    final_bonuses = {
        "phys_atk": final_strength * 4,
        "stealth_atk": final_agility * 8,
        "evasion": final_agility * 3,
        "max_hp": final_vitality * 10,
        "phys_def": final_vitality * 2,  # +1 от vitality * 2
        "magic_def": final_vitality * 1,
        "max_mp": final_intelligence * 3,
        "magic_atk": final_intelligence * 4,
    }
    
    # Собираем итоговый словарь
    # ✅ skill_points НЕ включаем — он сохраняется отдельно!
    return {
        "phys_atk": base["phys_atk"] + final_bonuses["phys_atk"],
        "stealth_atk": base["stealth_atk"] + final_bonuses["stealth_atk"],
        "evasion": base["evasion"] + final_bonuses["evasion"],
        "phys_def": base["phys_def"] + final_bonuses["phys_def"],
        "magic_def": base["magic_def"] + final_bonuses["magic_def"],
        "magic_atk": base["magic_atk"] + final_bonuses["magic_atk"],
        "max_hp": base["max_hp"] + final_bonuses["max_hp"],
        "max_mp": base["max_mp"] + final_bonuses["max_mp"],
        # ✅ hp и mp обновляем только если они меньше новых max
        "hp": min(player["hp"], base["max_hp"] + final_bonuses["max_hp"]),
        "mp": min(player["mp"], base["max_mp"] + final_bonuses["max_mp"]),
        # ✅ skill_points НЕ возвращаем — он не должен перезаписываться!
    }
