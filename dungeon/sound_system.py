
from .ecs import System
from .events import Event, MessageEvent, SkillUseEvent

class SoundEvent(Event):
    def __init__(self, sound_type: str, message: str):
        self.type = "SOUND"
        self.sound_type = sound_type # e.g., 'ATTACK', 'HIT', 'LEVEL_UP'
        self.message = message

class SoundSystem(System):
    """
    게임 내 이벤트에 반응하여 '소리'를 시각적으로(로그/이펙트) 출력하는 시스템.
    추후 실제 오디오 라이브러리(pygame 등)와 연동 가능.
    """
    def __init__(self, world, ui=None):
        super().__init__(world)
        self.ui = ui # UI에 직접 접근하여 특수 효과를 줄 수도 있음

    def process_event(self, event):
        if hasattr(event, 'sound_type'): # 직접 발생시킨 SoundEvent
            self._play_sound(event.sound_type, event.message)
        
        elif event.type == "SKILL_USE":
            # 스킬 사용 시 효과음
            skill_name = event.skill.name
            if "파이어볼" in skill_name:
                self._play_sound("MAGIC", "휘이잉~ 쾅!")
            elif "휠 윈드" in skill_name:
                self._play_sound("SWING", "슈우우웅!")
            elif "매직 미사일" in skill_name:
                self._play_sound("MAGIC", "피이잉!")
            elif "방패 밀치기" in skill_name:
                self._play_sound("BASH", "텅!")
            else:
                self._play_sound("ATTACK", "쉭!")

    def _play_sound(self, sound_type, message):
        """
        소리를 재생(여기서는 시각적 로그 출력)합니다.
        """
        # 로그에 [소리] 태그를 붙여서 출력하거나, 색상을 다르게 할 수 있음
        sound_msg = f"[🔊] {message}"
        
        # World의 EventManager를 통해 메시지 이벤트로 변환하여 출력
        # (순환 참조 주의: MessageEvent를 다시 처리하지 않도록 SoundSystem은 MessageEvent를 무시해야 함)
        if self.world:
             self.world.event_manager.push(MessageEvent(sound_msg))
