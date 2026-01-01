import os
import random
import time
import sys
import unicodedata # 한글 너비 계산을 위해 추가

# --- 게임 설정 ---
DUNGEON_WIDTH = 40  # 중앙 맵의 가로 크기
DUNGEON_HEIGHT = 15 # 중앙 맵의 세로 크기 (24행 터미널에 맞춰 조정)

PLAYER_CHAR = '@'
WALL_CHAR = '█'
FLOOR_CHAR = '.'
MONSTER_CHAR = 'M'
ITEM_CHAR = 'I'
EXIT_CHAR = 'E'

# --- 플레이어 클래스 ---
class Player:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.hp = 100
        self.max_hp = 100
        self.mp = 50
        self.max_mp = 50
        self.inventory = []
        self.skills = {
            "Fireball": {"level": 1, "mp_cost": 10, "base_damage": 10},
            "Heal": {"level": 1, "mp_cost": 15, "base_heal": 20},
        }
        self.skill_recipes = {
            "Fireball": [
                {"level": 2, "items": ["Red Orb", "Magic Dust"], "effect": {"base_damage": 5}},
                {"level": 3, "items": ["Dragon Scale", "Fire Crystal"], "effect": {"base_damage": 10}}
            ],
            "Heal": [
                {"level": 2, "items": ["Green Herb", "Holy Water"], "effect": {"base_heal": 10}}
            ]
        }
        self.dead = False
        # 스킬 및 아이템 슬롯 초기화
        self.skill_slots = {"1": "Fireball", "2": "Heal", "3": "", "4": "", "5": ""}
        self.item_slots = {"6": "Mana Potion", "7": "Health Potion", "8": "", "9": "", "0": ""}
        self.status_effects = [] # 현재 걸린 상태 이상 목록

    def move(self, dx, dy, dungeon_map):
        new_x, new_y = self.x + dx, self.y + dy
        if 0 <= new_x < DUNGEON_WIDTH and 0 <= new_y < DUNGEON_HEIGHT:
            if dungeon_map[new_y][new_x] != WALL_CHAR:
                self.x = new_x
                self.y = new_y
                return True
        return False

    def use_skill(self, skill_name, target_monster=None):
        if skill_name not in self.skills:
            print(f"[{skill_name}] skill not known.")
            return False
        
        skill_info = self.skills[skill_name]
        if self.mp < skill_info["mp_cost"]:
            print(f"Not enough MP! ({self.mp}/{skill_info['mp_cost']})")
            return False

        self.mp -= skill_info["mp_cost"]
        print(f"Used '{skill_name}'! Consumed {skill_info['mp_cost']} MP.")

        if skill_name == "Fireball":
            if target_monster and not target_monster.dead:
                damage = skill_info["base_damage"] * skill_info["level"]
                target_monster.take_damage(damage)
                print(f"Dealt {damage} damage to {target_monster.char}.")
            else:
                print("No valid target found to attack.")
                self.mp += skill_info["mp_cost"] # 마나 돌려주기
                return False
        elif skill_name == "Heal":
            heal_amount = skill_info["base_heal"] * skill_info["level"]
            self.hp = min(self.max_hp, self.hp + heal_amount) # 최대 체력 반영
            print(f"Recovered {heal_amount} HP. Current HP: {self.hp}")
        
        return True

    def check_skill_level_up(self):
        for skill_name, recipes in self.skill_recipes.items():
            current_level = self.skills[skill_name]["level"]
            
            # 다음 레벨업 조건을 찾습니다.
            next_level_recipe = None
            for recipe in recipes:
                if recipe["level"] == current_level + 1:
                    next_level_recipe = recipe
                    break

            if next_level_recipe:
                # 필요한 아이템이 인벤토리에 있는지 확인
                has_all_items = True
                for item_needed in next_level_recipe["items"]:
                    if item_needed not in self.inventory:
                        has_all_items = False
                        break
                
                if has_all_items:
                    # 아이템 소모 및 스킬 레벨업
                    for item_to_remove in next_level_recipe["items"]:
                        self.inventory.remove(item_to_remove)
                    
                    self.skills[skill_name]["level"] += 1
                    # 효과 적용
                    for effect_type, effect_value in next_level_recipe["effect"].items():
                        self.skills[skill_name][effect_type] += effect_value

                    print(f"*** {skill_name} skill leveled up to {self.skills[skill_name]['level']}! ***")
                    return True # 한 번에 하나의 스킬만 레벨업 처리

        return False


# --- 몬스터 클래스 ---
class Monster:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hp = 30
        self.damage = 5
        self.char = MONSTER_CHAR
        self.dead = False

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            return True
        return False
    
    def attack(self, target_player):
        print(f"{self.char} attacks!")
        target_player.hp -= self.damage
        print(f"Lost {self.damage} HP! Current HP: {target_player.hp}")
        if target_player.hp <= 0:
            target_player.dead = True
            print("You have been defeated...")

# --- 던전 생성 함수 ---
def generate_dungeon(width, height, num_monsters=5, num_items=3):
    dungeon = [[WALL_CHAR for _ in range(width)] for _ in range(height)]

    # 단순한 통로 생성 (가운데를 비워둠)
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            dungeon[y][x] = FLOOR_CHAR

    # 플레이어 시작 위치
    player_start_x = random.randint(1, width - 2)
    player_start_y = random.randint(1, height - 2)

    # 몬스터 배치
    monsters = []
    for _ in range(num_monsters):
        while True:
            mx, my = random.randint(1, width - 2), random.randint(1, height - 2)
            if dungeon[my][mx] == FLOOR_CHAR and (mx, my) != (player_start_x, player_start_y):
                monsters.append(Monster(mx, my))
                break
    
    # 아이템 배치 (예시 아이템)
    items = []
    available_items = ["Red Orb", "Magic Dust", "Green Herb", "Holy Water", "Dragon Scale", "Fire Crystal", "Mana Potion", "Health Potion"]
    for _ in range(num_items):
        while True:
            ix, iy = random.randint(1, width - 2), random.randint(1, height - 2)
            if dungeon[iy][ix] == FLOOR_CHAR and (ix, iy) != (player_start_x, player_start_y):
                items.append((ix, iy, random.choice(available_items)))
                break

    # 출구 배치
    exit_x, exit_y = random.randint(1, width - 2), random.randint(1, height - 2)
    while (exit_x, exit_y) == (player_start_x, player_start_y):
        exit_x, exit_y = random.randint(1, width - 2), random.randint(1, height - 2)
    
    return dungeon, player_start_x, player_start_y, monsters, items, exit_x, exit_y

# --- 화면 지우기 함수 ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# --- 문자열의 실제 터미널 너비 계산 함수 ---
def get_display_width(text):
    """
    주어진 문자열이 터미널에서 차지하는 실제 너비를 계산합니다.
    한글 등 전각 문자는 2칸으로 계산합니다.
    """
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width

def pad_string(text, target_width, align='left'):
    """
    주어진 문자열을 target_width에 맞춰 패딩합니다.
    get_display_width를 사용하여 실제 표시 너비를 고려합니다.
    """
    current_width = get_display_width(text)
    if current_width >= target_width:
        truncated_text = ""
        current_truncated_width = 0
        for char in text:
            char_width = get_display_width(char)
            if current_truncated_width + char_width <= target_width:
                truncated_text += char
                current_truncated_width += char_width
            else:
                break
        return truncated_text
    
    padding_needed = target_width - current_width
    if align == 'left':
        return text + ' ' * padding_needed
    elif align == 'right':
        return ' ' * padding_needed + text
    elif align == 'center':
        left_pad = padding_needed // 2
        right_pad = padding_needed - left_pad
        return ' ' * left_pad + text + ' ' * right_pad
    return text


# --- UI 그리기 함수 ---
def draw_ui(dungeon, player, monsters, items, exit_pos, ui_mode="skills"):
    clear_screen()

    UI_LEFT_WIDTH = 24
    UI_CENTER_WIDTH = DUNGEON_WIDTH
    UI_RIGHT_WIDTH = 20 # 그놈 터미널 환경을 고려하여 20으로 설정
    TOTAL_DISPLAY_WIDTH = UI_LEFT_WIDTH + UI_CENTER_WIDTH + UI_RIGHT_WIDTH + 7 # 24 + 40 + 20 + 7 = 91

    # --- 각 패널의 내용 미리 생성 ---
    left_panel_lines = []
    if ui_mode == "skills":
        left_panel_lines.append(pad_string("--- SKILLS ---", UI_LEFT_WIDTH))
        if not player.skills:
            left_panel_lines.append(pad_string("  No skills learned.", UI_LEFT_WIDTH))
        else:
            for skill_name, skill_info in player.skills.items():
                skill_line = f"- {skill_name}(Lv{skill_info['level']})"
                left_panel_lines.append(pad_string(skill_line, UI_LEFT_WIDTH))
    elif ui_mode == "inventory":
        left_panel_lines.append(pad_string("--- INVENTORY ---", UI_LEFT_WIDTH))
        if not player.inventory:
            left_panel_lines.append(pad_string("  Empty", UI_LEFT_WIDTH))
        else:
            for item in player.inventory:
                left_panel_lines.append(pad_string(f"- {item}", UI_LEFT_WIDTH))
    
    left_panel_lines.append(pad_string("", UI_LEFT_WIDTH))
    left_panel_lines.append(pad_string("(K: Skills / I: Inventory)", UI_LEFT_WIDTH))


    right_panel_lines = []
    right_panel_lines.append(pad_string("--- PLAYER INFO ---", UI_RIGHT_WIDTH))
    right_panel_lines.append(pad_string(f"HP: {player.hp}/{player.max_hp}", UI_RIGHT_WIDTH))
    right_panel_lines.append(pad_string(f"MP: {player.mp}/{player.max_mp}", UI_RIGHT_WIDTH))
    
    status_str = ' / '.join(player.status_effects) if player.status_effects else 'Normal'
    right_panel_lines.append(pad_string(f"Status: {status_str}", UI_RIGHT_WIDTH))
    right_panel_lines.append(pad_string(f"Inventory: {len(player.inventory)} items", UI_RIGHT_WIDTH))
    
    right_panel_lines.append(pad_string("", UI_RIGHT_WIDTH))
    right_panel_lines.append(pad_string("(Q: Quit)", UI_RIGHT_WIDTH))
    right_panel_lines.append(pad_string("(S: Use Skill)", UI_RIGHT_WIDTH))

    # 던전 맵 생성
    display_map_lines = []
    current_map = [row[:] for row in dungeon]

    for ix, iy, item_name in items:
        current_map[iy][ix] = ITEM_CHAR
    for monster in monsters:
        if not monster.dead:
            current_map[monster.y][monster.x] = monster.char
    exit_x, exit_y = exit_pos
    current_map[exit_y][exit_x] = EXIT_CHAR
    current_map[player.y][player.x] = PLAYER_CHAR

    for y_idx, row in enumerate(current_map):
        line = "".join(row)
        display_map_lines.append(pad_string(line, UI_CENTER_WIDTH))

    target_content_height = DUNGEON_HEIGHT
    
    while len(left_panel_lines) < target_content_height:
        left_panel_lines.append(" " * UI_LEFT_WIDTH)
    while len(right_panel_lines) < target_content_height:
        right_panel_lines.append(" " * UI_RIGHT_WIDTH)
    
    left_panel_lines = left_panel_lines[:target_content_height]
    right_panel_lines = right_panel_lines[:target_content_height]

    print("┌" + "─" * (TOTAL_DISPLAY_WIDTH - 2) + "┐")

    for i in range(target_content_height):
        left_part = left_panel_lines[i]
        center_part = display_map_lines[i]
        right_part = right_panel_lines[i]
        print(f"│ {left_part} │ {center_part} │ {right_part} │")

    print("│" + "─" * (TOTAL_DISPLAY_WIDTH - 2) + "│")

    # --- 하단 슬롯 정보 ---
    skill_slot_strs = []
    for i in range(1, 6):
        slot_key = str(i)
        skill_name = player.skill_slots.get(slot_key, "")
        skill_slot_strs.append(f"[{slot_key}:{pad_string(skill_name[:6], 6)}]")

    item_slot_strs = []
    for i in range(6, 11):
        slot_key = str(i) if i < 10 else "0"
        item_name = player.item_slots.get(slot_key, "")
        item_slot_strs.append(f"[{slot_key}:{pad_string(item_name[:6], 6)}]")

    skill_line_content = 'Skills: ' + ' '.join(skill_slot_strs)
    item_line_content = 'Items: ' + ' '.join(item_slot_strs)

    print(f"│ {pad_string(skill_line_content, TOTAL_DISPLAY_WIDTH - 4)}│")
    print(f"│ {pad_string(item_line_content, TOTAL_DISPLAY_WIDTH - 4)}│")
    print("└" + "─" * (TOTAL_DISPLAY_WIDTH - 2) + "┘")


# --- 메인 게임 루프 ---
def game_loop():
    player = Player()
    
    dungeon_map, player.x, player.y, monsters, items_on_map, exit_x, exit_y = generate_dungeon(DUNGEON_WIDTH, DUNGEON_HEIGHT)

    initial_tile = dungeon_map[player.y][player.x]
    if initial_tile == MONSTER_CHAR:
        for m in monsters:
            if m.x == player.x and m.y == player.y:
                m.dead = True
                break
    elif initial_tile == ITEM_CHAR:
        for i_idx, (ix, iy, item_name) in enumerate(items_on_map):
            if ix == player.x and iy == player.y:
                player.inventory.append(item_name)
                del items_on_map[i_idx]
                break

    current_ui_mode = "skills"

    while not player.dead:
        draw_ui(dungeon_map, player, monsters, items_on_map, (exit_x, exit_y), current_ui_mode)
        
        print("\nEnter command (w/a/s/d/Q:Quit/K:Skills/I:Inventory/S:UseSkill): ", end="")
        key = input().strip()
        
        moved = False
        message_to_display = ""

        if key == 'w': moved = player.move(0, -1, dungeon_map)
        elif key == 's': moved = player.move(0, 1, dungeon_map)
        elif key == 'a': moved = player.move(-1, 0, dungeon_map)
        elif key == 'd': moved = player.move(1, 0, dungeon_map)
        elif key == 'q' or key == 'Q':
            print("Exiting game.")
            break
        elif key == 'S':
            target_monster = None
            for m in monsters:
                if not m.dead and abs(m.x - player.x) <= 1 and abs(m.y - player.y) <= 1:
                    target_monster = m
                    break
            
            if target_monster:
                print("Enter skill to use (Fireball, Heal etc.):", end="")
                skill_choice = input().strip()
                if skill_choice in player.skills:
                    if player.use_skill(skill_choice, target_monster):
                        message_to_display = f"Used '{skill_choice}'!"
                    else:
                        message_to_display = f"Failed to use '{skill_choice}'."
                else:
                    message_to_display = "Invalid skill name."
            else:
                message_to_display = "No monsters to attack nearby."
        elif key == 'K':
            current_ui_mode = "skills"
        elif key == 'I':
            current_ui_mode = "inventory"
        else:
            message_to_display = "Unknown command."

        item_picked_up = False
        for i_idx, (ix, iy, item_name) in enumerate(items_on_map):
            if player.x == ix and player.y == iy:
                player.inventory.append(item_name)
                message_to_display += f" Picked up '{item_name}'!"
                del items_on_map[i_idx]
                item_picked_up = True
                break
        
        if item_picked_up or moved:
            if player.check_skill_level_up():
                message_to_display += " Skill leveled up!"

        dead_monsters_in_turn = []
        for monster in monsters:
            if not monster.dead:
                if abs(monster.x - player.x) <= 1 and abs(monster.y - player.y) <= 1:
                    monster.attack(player)
                else:
                    dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0,0)])
                    new_mx, new_my = monster.x + dx, monster.y + dy
                    if 0 <= new_mx < DUNGEON_WIDTH and 0 <= new_my < DUNGEON_HEIGHT and dungeon_map[new_my][new_mx] == FLOOR_CHAR:
                        monster.x, monster.y = new_mx, new_my
            if monster.dead:
                dead_monsters_in_turn.append(monster)
        
        for dead_m in dead_monsters_in_turn:
            print(f"{dead_m.char} was defeated!")
            monsters.remove(dead_m)

        if player.hp <= 0:
            player.dead = True
            print("\nYou were defeated in the dungeon...")
            print("--- GAME OVER ---")
            break
        
        if player.x == exit_x and player.y == exit_y:
            print("\nYou successfully escaped the dungeon!")
            print("--- GAME WON ---")
            break
        
        if message_to_display:
            print(message_to_display)


# --- 게임 시작 ---
if __name__ == "__main__":
    game_loop()
