# combat.py

def calculate_damage(attacker, defender):
    """공격자와 방어자의 능력치를 기반으로 최종 데미지를 계산합니다."""
    damage = attacker.attack - defender.defense
    # 최소 데미지는 1로 보장
    return max(1, damage)

def use_skill_in_combat(player, skill_name, target_monster=None, ui_instance=None):
    if skill_name not in player.skills:
        if ui_instance:
            ui_instance.add_message(f"[{skill_name}] 스킬을 알지 못합니다.")
        return False
    
    skill_info = player.skills[skill_name]
    if player.mp < skill_info["mp_cost"]:
        if ui_instance:
            ui_instance.add_message(f"MP가 부족합니다! ({player.mp}/{skill_info['mp_cost']})")
        return False

    player.mp -= skill_info["mp_cost"]
    if ui_instance:
        ui_instance.add_message(f"'{skill_name}' 사용! MP {skill_info['mp_cost']} 소모.")

    if skill_name == "Fireball":
        if target_monster and not target_monster.dead:
            # 스킬 데미지는 방어력을 무시하는 고정 데미지로 설정 (예시)
            damage = skill_info["base_damage"] * skill_info["level"]
            target_monster.take_damage(damage)
            if ui_instance:
                ui_instance.add_message(f"{target_monster.name}에게 {damage}의 데미지!")
        else:
            if ui_instance:
                ui_instance.add_message("공격할 대상이 없습니다.")
            player.mp += skill_info["mp_cost"] # 마나 반환
            return False
    elif skill_name == "Heal":
        heal_amount = skill_info["base_heal"] * skill_info["level"]
        player.restore_hp(heal_amount)
        if ui_instance:
            ui_instance.add_message(f"HP {heal_amount} 회복. 현재 HP: {player.hp}")
    
    return True

