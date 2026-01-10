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
