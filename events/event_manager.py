from collections import defaultdict
from typing import Type, Callable, Any

class EventManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        # 1. 싱글톤 인스턴스 생성 (최초 1회)
        if cls._instance is None:
            cls._instance = super(EventManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # 2. 초기화 로직은 최초 1회만 실행되도록 보장
        if not EventManager._initialized:
            # GEMINI.md: 이벤트 처리 로직을 포함하지 않고 전달 역할만 수행
            self.listeners: defaultdict[Type, list[Callable]] = defaultdict(list)
            EventManager._initialized = True
            print("EventManager 초기화 완료 (싱글톤)")

    def subscribe(self, event_type: Type, listener: Callable):
        """특정 이벤트 타입에 핸들러 함수를 등록합니다."""
        if listener not in self.listeners[event_type]:
            self.listeners[event_type].append(listener)
            # print(f"이벤트 핸들러 등록 완료: {event_type.__name__}")

    def publish(self, event: Any):
        """이벤트 객체를 발행하여 해당 이벤트를 구독한 모든 핸들러를 순서대로 호출합니다."""
        event_type = type(event)
        # GEMINI.md: FIFO 순서를 보장하여 이벤트 객체를 전달
        for listener in self.listeners[event_type]:
            listener(event)

# 전역 인스턴스 생성 (ECS 시스템들이 접근할 유일한 창구)
event_manager = EventManager()
