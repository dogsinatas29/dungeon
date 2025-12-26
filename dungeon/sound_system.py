import subprocess
import os
from .ecs import System
from .events import Event, MessageEvent, SkillUseEvent, SoundEvent

class SoundSystem(System):
    """
    게임 내 이벤트에 반응하여 '소리'를 시각적으로(로그) 표시하고, 
    리눅스 표준인 aplay를 통해 실제 효과음을 비동기로 재생하는 시스템.
    """
    def process(self):
        pass # 사운드 재생은 이벤트 기반으로 작동함
    def __init__(self, world, ui=None):
        super().__init__(world)
        self.ui = ui
        # 사운드 파일 경로 매핑 (sounds/ 디렉토리 기준)
        self.sound_map = {
            "ATTACK": "attack.wav",
            "HIT": "hit.wav",
            "MAGIC": "magic.wav",
            "CRITICAL": "critical.wav",
            "BASH": "bash.wav",
            "SWING": "swing.wav",
            "LEVEL_UP": "levelup.wav",
            "STEP": "step.wav",
            "MISS": "miss.wav",
            "BLOCK": "block.wav",
            "MAGIC_FIRE": "fire.wav",
            "MAGIC_ICE": "ice.wav",
            "MAGIC_BOLT": "bolt.wav",
            "HEAL": "heal.wav",
            "EXPLOSION": "explosion.wav"
        }
        self.sound_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sounds")

    def process_event(self, event):
        if event.type == "SOUND":
            self._play_sound(event.sound_type, event.message)
        
        elif event.type == "SKILL_USE":
            # 1. 스킬의 플래그에서 소리 정보 탐색
            skill = getattr(event, 'skill', None) or event.skill_name
            
            # 만약 skill이 이름(문자열)이라면 엔진에서 정의를 찾아옴
            if isinstance(skill, str):
                skill_defs = getattr(self.world.engine, 'skill_defs', {})
                skill = skill_defs.get(skill)

            sound_found = False
            
            if hasattr(skill, 'flags'):
                for flag in skill.flags:
                    if flag.startswith("SOUND_"):
                        self._play_sound(flag)
                        sound_found = True
                        break
            
            if sound_found:
                return

            # 2. 플래그가 없으면 기존 하드코딩 방식 유지 (하위 호환)
            skill_name = skill.name if hasattr(skill, 'name') else str(skill)
            if "파이어볼" in skill_name:
                self._play_sound("MAGIC")
            elif "휠 윈드" in skill_name:
                self._play_sound("SWING")
            elif "방패 밀치기" in skill_name:
                self._play_sound("BASH")
            else:
                self._play_sound("MAGIC")

    def _play_sound(self, sound_type, message=""):
        """시각적 피드백 출력 및 실제 파일 재생 시도"""
        # 1. 시각적 피드백 (로그)
        if message:
            sound_msg = f"[🔊] {message}"
            self.world.event_manager.push(MessageEvent(sound_msg))

        # 2. 실제 오디오 재생 (aplay 사용, 비동기)
        # 기본 맵에서 찾기
        file_name = self.sound_map.get(sound_type)
        
        # 맵에 없으면 다이내믹 플래그 확인 (SOUND_ID_X -> skill_X.wav, SOUND_NAME -> name.wav)
        if not file_name:
            if sound_type.startswith("SOUND_ID_"):
                id_val = sound_type.replace("SOUND_ID_", "")
                file_name = f"skill_{id_val}.wav"
            elif sound_type.startswith("SOUND_"):
                # SOUND_MAGIC_FIRE -> magic_fire.wav
                file_name = f"{sound_type.replace('SOUND_', '').lower()}.wav"

        if file_name:
            file_path = os.path.join(self.sound_dir, file_name)
            if os.path.exists(file_path):
                try:
                    # subprocess.DEVNULL을 사용하여 터미널 출력을 방해하지 않음
                    subprocess.Popen(["aplay", "-q", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass # aplay가 없거나 오류 시 무시
