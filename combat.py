# combat.py
# Player 및 Monster 클래스를 import 해야 합니다.
# from player import Player # 이 파일에서 Player를 직접 인스턴스화하지 않으므로 필요 없음
# from monster import Monster # 이 파일에서 Monster를 직접 인스턴스화하지 않으므로 필요 없음

def use_skill_in_combat(player, skill_name, target_monster=None, ui_instance=None):
    if skill_name not in player.skills:
        if ui_instance:
            ui_instance.add_message(f"[{skill_name}] skill not known.")
        else:
            print(f"[{skill_name}] skill not known.")
        return False
    
    skill_info = player.skills[skill_name]
    if player.mp < skill_info["mp_cost"]:
        if ui_instance:
            ui_instance.add_message(f"Not enough MP! ({player.mp}/{skill_info['mp_cost']})")
        else:
            print(f"Not enough MP! ({player.mp}/{skill_info['mp_cost']})")
        return False

    player.mp -= skill_info["mp_cost"]
    if ui_instance:
        ui_instance.add_message(f"Used '{skill_name}'! Consumed {skill_info['mp_cost']} MP.")
    else:
        print(f"Used '{skill_name}'! Consumed {skill_info['mp_cost']} MP.")

    if skill_name == "Fireball":
        if target_monster and not target_monster.dead:
            damage = skill_info["base_damage"] * skill_info["level"]
            target_monster.take_damage(damage)
            if ui_instance:
                ui_instance.add_message(f"Dealt {damage} damage to {target_monster.char}.")
            else:
                print(f"Dealt {damage} damage to {target_monster.char}.")
        else:
            if ui_instance:
                ui_instance.add_message("No valid target found to attack.")
            else:
                print("No valid target found to attack.")
            player.mp += skill_info["mp_cost"] # 마나 돌려주기
            return False
    elif skill_name == "Heal":
        heal_amount = skill_info["base_heal"] * skill_info["level"]
        player.hp = min(player.max_hp, player.hp + heal_amount)
        if ui_instance:
            ui_instance.add_message(f"Recovered {heal_amount} HP. Current HP: {player.hp}")
        else:
            print(f"Recovered {heal_amount} HP. Current HP: {player.hp}")
    
    return True

# 몬스터의 공격 로직은 Monster 클래스 내부에 있으므로 여기서는 별도 함수 불필요.
# 필요하다면 여기에 공통 전투 유틸리티 함수를 추가할 수 있습니다.
