# combat.py
import random

def calculate_damage(attacker, defender, skill=None):
    """
    공격자와 방어자의 능력치를 기반으로 최종 데미지를 계산합니다.
    스킬이 제공되면 스킬 데미지를 우선으로 사용합니다.
    치명타 발생 시 데미지를 증폭시키고, 치명타 여부를 함께 반환합니다.
    """
    is_critical = False
    base_damage = 0

    if skill:
        # 스킬 데미지 사용 (SkillDefinition 객체를 받는다고 가정)
        base_damage = skill.damage
    else:
        # 기본 공격 데미지
        base_damage = attacker.attack

    # 치명타 발동 여부 확인 (attacker에 critical_chance 속성이 있다고 가정)
    if hasattr(attacker, 'critical_chance') and random.random() < attacker.critical_chance:
        is_critical = True

    # 데미지 계산
    damage = base_damage - defender.defense

    # 치명타 발생 시 데미지 증폭
    if is_critical:
        # attacker에 critical_damage_multiplier 속성이 있다고 가정
        multiplier = getattr(attacker, 'critical_damage_multiplier', 1.5)
        damage = int(damage * multiplier)

    # 최소 데미지는 1로 보장
    final_damage = max(1, damage)

    return final_damage, is_critical

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

