# monster.py
class Monster:
    def __init__(self, x, y, ui_instance=None):
        self.x = x
        self.y = y
        self.hp = 30
        self.damage = 5
        self.char = 'M' # MONSTER_CHAR는 dungeon_map.py에서 정의됨
        self.dead = False
        self.ui_instance = ui_instance

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            return True
        return False
    
    def attack(self, target_player):
        if self.ui_instance:
            self.ui_instance.add_message(f"{self.char} attacks!")
            target_player.hp -= self.damage
            self.ui_instance.add_message(f"Lost {self.damage} HP! Current HP: {target_player.hp}")
            if target_player.hp <= 0:
                target_player.dead = True
                self.ui_instance.add_message("You have been defeated...")
        else:
            print(f"{self.char} attacks!")
            target_player.hp -= self.damage
            print(f"Lost {self.damage} HP! Current HP: {target_player.hp}")
            if target_player.hp <= 0:
                target_player.dead = True
                print("You have been defeated...")
