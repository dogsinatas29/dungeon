# dungeon/localization.py

import os
from . import config

# UI 및 시스템 메시지 번역 맵
TRANSLATIONS = {
    "ko": {
        # UI Elements
        "Level": "레벨", "Exp": "경험치", "Job": "직업", "Gold": "골드", "Floor": "층",
        "HP": "HP", "MP": "MP", "Stamina": "스테미너", "Inventory": "인벤토리",
        "Shop": "상점", "Main Menu": "메인 메뉴", "Name": "이름", "Experience": "경험치",
        "Stat Points": "스탯 포인트", "Select your class:": "당신의 직업을 선택하세요:",
        "Detail Stats": "상세 능력치", "Basic Skill": "기본 스킬", "Log": "로그",
        "Move": "이동", "Wait": "대기", "Quickslot": "퀵슬롯", "Close": "닫기",
        "Enter your name": "당신의 이름은 무엇입니까?", "(Max 10 chars)": "(최대 10자)",
        "Equipment": "장비", "Items": "아이템", "No items": "아이템 없음",
        "No equipped items": "장착된 아이템 없음", "Confirm": "확인", "Yes": "예", "No": "아니오",
        "Back": "뒤로 가기", "Load": "불러오기", "Delete": "삭제",
        "No saved games.": "저장된 게임이 없습니다.",
        "Select skill to recharge": "충전할 스킬 선택",
        "Select equipment to repair": "수리할 장비 선택",
        "Select item to identify": "감정할 아이템 선택",
        "No skills available": "사용 가능한 스킬이 없습니다!",
        "No items to repair": "수리할 아이템이 없습니다!",
        "No items to identify": "감정할 아이템이 없습니다!",
        "New Game": "새 게임", "Continue": "이어하기", "Exit Game": "게임 종료",
        "Select": "선택", "GAME OVER": "게임 종료",
        "Press any key to return to Main Menu.": "아무 키나 눌러 메인 메뉴로 돌아갑니다.",
        "Damage": "데미지", "Defense": "방어력",
        "Attack": "공격력", "AC": "방어력(AC)",
        "Equipment/Req": "공격력/장비착용", "Max MP": "최대 마력(MP)", "AC/Hit": "방어력(AC)/명중", "Max HP": "최대 체력(HP)",
        "Dungeon Map": "던전 맵", "Player Condition": "플레이어 상태",
        "STR (Str)": "STR (힘)", "MAG (Mag)": "MAG (마력)", "DEX (Dex)": "DEX (민첩)", "VIT (Vit)": "VIT (활력)",
        
        # Combat Messages
        "Attack!": "공격!", "Defend!": "방어!", "Miss!": "빗나감!", "Critical!": "크리티컬!",
        "You died...": "사망했습니다...", "Victory!": "승리!",
        
        # System Messages
        "Save complete.": "저장이 완료되었습니다.", "Load complete.": "로드가 완료되었습니다.",

        # New Additions
        "LOGS": "로그", "EQUIP": "장비", "QUICK SLOTS": "퀵슬롯", "SKILLS": "스킬", "ACTIVE EFFECTS": "진행 효과",
        "Head": "머리", "Body": "몸통", "Hand1": "손1", "Hand2": "손2", "Gloves": "장갑", "Boots": "신발", "Neck": "목", "Ring1": "반지1", "Ring2": "반지2",
        "recovered": "회복되었습니다.",
        
        # Game Start Messages
        "WASD나 방향키로 이동하고 몬스터와 부딪혀 전투하세요.": "WASD나 방향키로 이동하고 몬스터와 부딪혀 전투하세요.",
        
        # Inventory UI
        "선택:": "선택:",
        "이름:": "이름:",
        "설명:": "설명:",
        "필요 레벨:": "필요 레벨:",
        "공격:": "공격:",
        "방어:": "방어:",
        "사거리:": "사거리:",
        "효과:": "효과:",
        
        # Character Sheet
        "STR (힘)": "STR (힘)",
        "MAG (마력)": "MAG (마력)",
        "DEX (민첩)": "DEX (민첩)",
        "VIT (활력)": "VIT (활력)",
        "Points:": "포인트:",
        
        # Shop UI
        "사기 (BUY)": "사기 (BUY)",
        "팔기 (SELL)": "팔기 (SELL)",
        "소지 골드:": "소지 골드:",
        "구매": "구매",
        "판매": "판매",
        "[←/→] 탭 전환  [↑/↓] 선택  [ENTER]": "[←/→] 탭 전환  [↑/↓] 선택  [ENTER]",
        "  [B] 뒤로/닫기": "  [B] 뒤로/닫기",
        
        # Shrine UI
        "강화할 장비 선택": "강화할 장비 선택",
        "[ENTER] 강화  [ESC] 취소": "[ENTER] 강화  [ESC] 취소",
    },
    "en": {
        "Level": "Level", "Exp": "Exp", "Job": "Job", "Gold": "Gold", "Floor": "Floor",
        "HP": "HP", "MP": "MP", "Stamina": "Stamina", "Inventory": "Inventory",
        "Shop": "Shop", "Main Menu": "Main Menu", "Name": "Name", "Experience": "Experience",
        "Stat Points": "Stat Points", "Select your class:": "Select your class:",
        "Detail Stats": "Detail Stats", "Basic Skill": "Basic Skill", "Log": "Log",
        "Move": "Move", "Wait": "Wait", "Quickslot": "Quickslot", "Close": "Close",
        "Enter your name": "What is your name?", "(Max 10 chars)": "(Max 10 chars)",
        "Equipment": "Equipment", "Items": "Items", "No items": "No items",
        "No equipped items": "No equipped items", "Confirm": "Confirm", "Yes": "Yes", "No": "No",
        "Back": "Back", "Load": "Load", "Delete": "Delete",
        "No saved games.": "No saved games.",
        "Select skill to recharge": "Select skill to recharge",
        "Select equipment to repair": "Select equipment to repair",
        "Select item to identify": "Select item to identify",
        "No skills available": "No skills available!",
        "No items to repair": "No items to repair!",
        "No items to identify": "No items to identify!",
        "New Game": "New Game", "Continue": "Continue", "Exit Game": "Exit Game",
        "Select": "Select", "GAME OVER": "GAME OVER",
        "Press any key to return to Main Menu.": "Press any key to return to Main Menu.",
        "Damage": "Damage", "Defense": "Defense",
        "Attack": "Attack", "AC": "AC",
        "Equipment/Req": "Equipment/Req", "Max MP": "Max MP", "AC/Hit": "AC/Hit", "Max HP": "Max HP",
        "Dungeon Map": "Dungeon Map", "Player Condition": "Player Condition",
        "STR (Str)": "STR (Str)", "MAG (Mag)": "MAG (Mag)", "DEX (Dex)": "DEX (Dex)", "VIT (Vit)": "VIT (Vit)",
        
        "Attack!": "Attack!", "Defend!": "Defend!", "Miss!": "Miss!", "Critical!": "Critical!",
        "You died...": "You died...", "Victory!": "Victory!",
        
        "Save complete.": "Save complete.", "Load complete.": "Load complete.",

        # New Additions
        "LOGS": "LOGS", "EQUIP": "EQUIP", "QUICK SLOTS": "QUICK SLOTS", "SKILLS": "SKILLS", "ACTIVE EFFECTS": "ACTIVE EFFECTS",
        "Head": "Head", "Body": "Body", "Hand1": "Hand1", "Hand2": "Hand2", "Gloves": "Gloves", "Boots": "Boots", "Neck": "Neck", "Ring1": "Ring1", "Ring2": "Ring2",
        "recovered": "recovered", "HP": "HP", "MP": "MP",
        
        # Game Start Messages
        "WASD나 방향키로 이동하고 몬스터와 부딪혀 전투하세요.": "Use WASD or arrow keys to move and bump into monsters to fight.",
        
        # Inventory UI
        "선택:": "Select:",
        "이름:": "Name:",
        "설명:": "Desc:",
        "필요 레벨:": "Req Lv:",
        "공격:": "ATK:",
        "방어:": "DEF:",
        "사거리:": "Range:",
        "효과:": "Effect:",
        
        # Character Sheet
        "STR (힘)": "STR (Str)",
        "MAG (마력)": "MAG (Mag)",
        "DEX (민첩)": "DEX (Dex)",
        "VIT (활력)": "VIT (Vit)",
        "Points:": "Points:",
        
        # Shop UI
        "사기 (BUY)": "BUY",
        "팔기 (SELL)": "SELL",
        "소지 골드:": "Gold:",
        "구매": "Buy",
        "판매": "Sell",
        "[←/→] 탭 전환  [↑/↓] 선택  [ENTER]": "[←/→] Tab  [↑/↓] Select  [ENTER]",
        "  [B] 뒤로/닫기": "  [B] Back/Close",
        
        # Shrine UI
        "강화할 장비 선택": "Select Equipment to Enhance",
        "[ENTER] 강화  [ESC] 취소": "[ENTER] Enhance  [ESC] Cancel",
        
        # System Messages (Dynamic)
        "전신이 석화되어 움직일 수 없습니다!": "You are petrified and cannot move!",
        "몸이 움직이지 않습니다... (기절 중)": "You cannot move... (Stunned)",
        "깊은 잠에 빠져 움직일 수 없습니다... (수면 중)": "You cannot move... (Deep Sleep)",
        "지팡이에 충전된 '{}'을(를) 방출하여 자신을 치유합니다!": "You release the charged '{}' from your staff to heal yourself!",
        "지팡이에 충전된 '{}'을(를) 방출합니다!": "You release the charged '{}' from your staff!",
        "주변을 살펴봅니다.": "You look around.",
        "{}의 시체를 살펴봅니다...": "You examine the corpse of {}...",
        "지상으로 나가는 출구는 막혀있습니다.": "The exit to the surface is blocked.",
        "제자리에서 대기합니다.": "You wait.",
        "탈진하여 쓰러졌습니다! (Stamina 0)": "You collapsed from exhaustion! (Stamina 0)",
        "다음 층으로 연결되는 계단입니다. [ENTER] 키를 눌러 내려가시겠습니까?": "Stairs down to the next floor. Press [ENTER] to descend?",
        "이전 층으로 연결되는 계단입니다. [ENTER] 키를 눌러 올라가시겠습니까?": "Stairs up to the previous floor. Press [ENTER] to ascend?",
        "숨겨진 무언가를 발견했습니다!": "You found something hidden!",
        "{}의 강력한 기운이 방출됩니다!": "A powerful aura exudes from {}!",
        "!!! {}이(가) 분노하여 더욱 강력해집니다! !!!": "!!! {} becomes enraged and grows stronger! !!!",
        "{}이(가) {}.": "{} is {}.",
        "쿠쿠쿵! 어딘가에서 거대한 문이 열리는 소리가 들립니다!": "Rumble! You hear a massive door opening somewhere!",
        "레버를 당기자 함정이 발동했습니다! 폭발이 일어납니다!": "A trap triggers as you pull the lever! An explosion occurs!",
        "폭발로 인해 {}의 피해를 입었습니다! (HP {}%)": "You took {} damage from the explosion! (HP {}%)",
        "문에서 독침이 튀어나왔습니다!": "Poison needles shot out from the door!",
        "'{}'이(가) 강력한 포효와 함께 지원군을 부릅니다!": "'{}' calls for reinforcements with a mighty roar!",
        "!!! {}이(가) {}의 환영을 불러냅니다! !!!": "!!! {} summons the illusion of {}! !!!",
        "보물상자가 갑자기 몬스터로 변했습니다! 기습 공격을 받았습니다!": "The chest suddenly turned into a monster! You were ambushed!",
        "{}와 {}가 충돌하여 서로 {}의 피해를 입었습니다!": "{} and {} collided, dealing {} damage to each other!",
        "{}가 뒤로 밀려났습니다!": "{} was knocked back!",
        "{}가 벽에 부딪혀 {}의 추가 피해를 입었습니다!": "{} hit the wall and took {} extra damage!",
        "{}가 벽에 부딪혀 피해를 입었습니다!": "{} hit the wall and took damage!",
        "체력이 1 회복되었습니다.": "Recovered 1 HP.",
        "마력이 1 회복되었습니다.": "Recovered 1 MP.",
        "이전 보스 1마리 소환": "Summon previous boss", # Not used directly in message but good to have
        "알 수 없는 엔티티와 충돌했습니다.": "Collided with unknown entity.",
        "충돌 발생: {}": "Collision: {}",
        "상인을 만났습니다. (거래 가능)": "You met a Merchant. (Trade available)",
        "{}와 충돌했습니다. 전투가 시작됩니다.": "Collided with {}. Combat starts.",
        "{}이(가) 깊은 잠에 빠졌습니다.": "{} fell into a deep sleep.",
        "{}이(가) 돌로 변했습니다!": "{} turned into stone!",
        "{}이(가) 독에 중독되었습니다!": "{} is poisoned!",
        "{}가 기절했습니다!": "{} is stunned!",
        "{} 효과가 만료되었습니다.": "{} effect expired.",
        "레벨업! 현재 레벨: {}": "Level Up! Current Level: {}",
        "체력과 마력이 모두 회복되었습니다!": "HP and MP fully recovered!",
        "보너스 스탯 포인트 +{} 획득!": "Bonus Stat Points +{} acquired!",
        "!!! {}이(가) {}의 마법으로 전신이 석화되었습니다! !!!": "!!! {} is petrified by {}'s magic! !!!",
        "!!! {}이(가) 해골 군단을 소환합니다!": "!!! {} summons a Skeleton Army!",
        "!!! {} : {} !!!": "!!! {} : {} !!!", # Generic boss shout
        "!!! {}의 광역 강타! !!!": "!!! {}'s AOE Smite! !!!",
        "!!! {}의 시선에 몸이 더욱 굳어갑니다! (석화 {}스택) !!!": "!!! {}'s gaze stiffens your body! (Petrify Stack {}) !!!",
        "!!! 이미 완전히 석화된 상태입니다! !!!": "!!! You are already fully petrified! !!!",
        "!!! 리치 왕의 시선이 당신을 굳게 만듭니다! (석화 1스택) !!!": "!!! The Lich King's gaze stiffens you! (Petrify Stack 1) !!!",
        "!!! 대지의 저주가 당신의 발을 묶습니다! !!!": "!!! Earth's Curse binds your feet! !!!",
        "{}의 전리품: {}이(가) 떨어졌습니다!": "{}'s Loot: {} dropped!",
        "!!! 던전을 정복했습니다 !!!": "!!! Dungeon Conquered !!!",
        "!!! {}(으)로 가는 계단이 나타났습니다 !!!": "!!! Stairs to {} appeared !!!",
        "도살자의 돌진에 치여 큰 피해를 입었습니다!": "You took massive damage from The Butcher's charge!",
        "도살자가 벽에 들이받고 기절했습니다!": "The Butcher hit a wall and is stunned!",
        "갈고리에 끌려가 기절했습니다!": "Dragged by the hook and stunned!",
        "큰 충격과 함께 뒤로 밀려납니다!": "Knocked back with a massive impact!",
        "!!! 도살자의 강력한 내려치기! !!!": "!!! The Butcher's Mighty Slam! !!!",
        "!!! 도살자가 미친 듯이 돌진합니다! !!!": "!!! The Butcher charges madly! !!!",
        "!!! 도살자가 피 묻은 갈고리를 던집니다! !!!": "!!! The Butcher throws a bloody hook! !!!",
        "{}이(가) 당신을 향해 급격히 돌진합니다!": "{} dashes towards you!",
        "{}의 대회전 공격!": "{}'s Whirlwind Attack!",
        "환영의 일격이라 위력이 약합니다.": "Illusion's strike is weaker.",
        "레버를 당기자 함정이 발동했습니다! 폭발이 일어납니다!": "Pulling the lever triggered a trap! Explosion!",
        "폭발로 인해 {}의 피해를 입었습니다! (HP {}%)": "Took {} damage from explosion! (HP {}%)",
        "공격 방향을 선택하세요... [Space] 취소": "Select attack direction... [Space] to cancel",
        "공격 모드 해제.": "Attack mode disabled.",
    }
}

def _(text):
    """지정된 언어에 맞춰 텍스트를 번역하거나 원본을 반환합니다."""
    lang = getattr(config, 'LANGUAGE', 'ko')
    
    trans = TRANSLATIONS.get(lang, {})
    if text in trans:
        return trans[text]
    
    return text

L = _ # Alias for easier access

def get_data_path(file_name, original_path=None):
    """현재 언어 설정을 고려하여 데이터 파일 경로를 반환합니다."""
    lang = getattr(config, 'LANGUAGE', 'ko')
    
    if original_path is None:
        original_path = os.path.join(os.path.dirname(__file__), "data")
    
    if lang == "en":
        en_path = os.path.join(original_path, "en", file_name)
        if os.path.exists(en_path):
            return en_path
            
    return os.path.join(original_path, file_name)
