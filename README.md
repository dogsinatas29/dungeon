# Gemini 프로젝트: 던전 크롤러

이 프로젝트는 Google Gemini를 활용한 **바이브 코딩(Vibe Coding)** 프로젝트입니다.

이 프로젝트는 파이썬 기반의 클래식 터미널 로그라이크 게임입니다. 게임 로직은 `dungeon/` 디렉토리 내의 여러 모듈로 분리되어 있으며, **컴포넌트-엔티티-시스템(ECS) 패턴**을 기반으로 설계되어 확장성, 유지보수성, 재사용성을 극대화합니다.

## 🖥️ 실행 환경

-   **권장 Python 버전**: Python 3.13.7 이상 (Python 3.10+ 호환)
-   **운영체제**: Linux (Ubuntu/Debian 계열 권장)
-   **터미널**: UTF-8 인코딩 및 ANSI 색상 지원 터미널
-   **필수 라이브러리**: `readchar`
    ```bash
    pip install readchar
    ```

## 🎯 최종 목표
터미널 기반의 로그라이크 게임 엔진을 ECS 패턴을 기반으로 완성하여, 규칙과 데이터를 실행 로직과 분리하여 관리합니다.

![Dungeon Crawler UI](dungeon_ui.png)

### 🎥 스킬 테스트 시연 (Skill Test Demo)
<video src="skill_test.mp4" controls width="100%"></video>

## 🎮 Roguelike Game Engine Architecture (ECS)

### 📂 핵심 디렉토리 및 모듈 역할

#### 1. Engine Core (엔진 핵심)
-   **`engine.py`**: 게임의 메인 루프 실행, `EntityManager` 초기화, 모든 `System`의 순서별 `update()` 호출 등 게임 흐름 제어.
-   **`entity.py`**: `Entity`의 고유 ID 생성 및 관리. `EntityManager` 클래스를 포함하여 컴포넌트 추가/검색 기능 제공.
-   **`component.py`**: `Entity`에 부여되는 모든 순수 데이터 클래스(State) 정의. (예: `PositionComponent`, `HealthComponent`).
-   **`system.py`**: 컴포넌트를 가진 `Entity`를 처리하는 순수 로직 정의. (예: `MovementSystem`, `CombatSystem`, `RenderingSystem`).

#### 2. Game Data & Definitions (데이터 정의)
-   **`data_manager.py`**: 외부 데이터 파일(`.txt`, `.json`)을 읽어 템플릿(Definition) 객체로 변환하는 로직.
-   **`data/` (디렉토리)**: 모든 게임 데이터 파일 저장소. (`items.txt`, `skills.txt`, `monster_data.txt` 등)
-   **`data/spawn_data.txt`**: 몬스터와 아이템의 스폰 위치, 확률, 드롭 아이템을 결정하는 메타 데이터.

#### 3. Features & Utilities (기능 및 유틸리티)
-   **`map.py`**: 던전 맵 생성 및 관리 로직. 충돌 감지, 시야 계산 등을 담당.
-   **`ui.py`**: 터미널 렌더링 및 UI 인터페이스 관리.
-   **`sound_system.py`**: `aplay`를 사용한 비동기 실제 효과음 재생 및 사운드 플래그 처리.
-   **`sfx_extractor.py`**: (Utility) 영상 파일에서 효과음을 자동으로 추출하여 조각내는 도구.
-   **`data/UI_layout.json`**: UI 레이아웃과 관련된 설정(좌표, 크기 등)을 저장하는 데이터 파일.

## 개발 가이드라인

-   **코딩 스타일**: 파이썬 PEP 8 표준을 준수합니다.
-   **의존성**: `readchar` 라이브러리를 사용합니다.
-   **UI**: 모든 UI 구성 요소는 `dungeon/ui.py`에서 렌더링됩니다.
-   **게임 데이터**: 플레이어 및 맵 데이터는 `game_data/` 디렉토리에 JSON 파일로 저장됩니다.

## 게임 데이터 정의

### 스탯 (Stats)
-   **HP (체력)**: 캐릭터/몬스터의 생명력.
-   **MP (마력)**: 스킬 사용에 필요한 자원.
-   **ATT (공격력)**: 공격 시 상대에게 입히는 데미지에 영향을 줍니다.
-   **DEF (방어력)**: 상대의 공격으로부터 받는 데미지를 감소시킵니다.

### 레벨 (LV) 및 경험치 (EXP)
-   **LV (레벨)**: 캐릭터의 기본 스탯 성장률을 결정하고, 아이템/스킬 사용 요구 조건으로 작동합니다.
-   **EXP (경험치)**: 몬스터 처치 시 획득하며, 일정량 모으면 레벨업합니다.

### 몬스터 표시 및 상호작용
-   **맵 표시**: 몬스터는 `monster_data.txt`에 정의된 고유한 ASCII 심볼(예: 고블린은 'g')로 맵에 표시됩니다.
-   **접근 메시지**: 플레이어가 몬스터로부터 3칸 이내로 접근하면 메시지 로그에 "[몬스터 이름](LV)을(를) 만났습니다."와 같은 메시지가 표시됩니다.

## 최근 변경 사항 요약

### 2025년 10월 9일 목요일
-   **프로젝트 구조 재편성 (ECS 아키텍처 기반)**: 엔진 핵심 로직을 `dungeon/`으로, 모든 게임 데이터를 `data/`로 분리했습니다. `game.py` -> `dungeon/engine.py`, `dungeon_map.py` -> `dungeon/map_manager.py`, `ui.py` -> `dungeon/renderer.py` 등으로 파일 이름을 변경하고 이동했습니다.
-   **게임 플레이 규칙 변경**: 몬스터 리젠 로직 수정, 맵 크기 점진적 증가 로직 변경.
-   **유지보수**: 파일명 오타 수정 (`componant.py` -> `component.py`, `system.pu` -> `system.py`).

### 2025년 10월 12일 토요일
-   **ECS 아키텍처 관련 버그 수정**: `AttributeError: 'Monster' object has no attribute 'x'`, `AttributeError: 'Monster' object has no attribute 'max_hp'`, `KeyError: None`, `NameError: name 'Player' is not defined`, `AttributeError: 'Player' object has no attribute 'max_hp'`, `AttributeError: 'Player' object has no attribute 'color'`, `UnboundLocalError: cannot access local variable 'current_dungeon_level'`, `AttributeError: 'EntityManager' object has no attribute 'has_component'` 등 ECS 전환 과정에서 발생한 다양한 버그를 수정하고 안정화했습니다. 특히, 몬스터 및 플레이어의 스탯/위치 정보가 컴포넌트를 통해 올바르게 관리되도록 수정했습니다.

### 2025년 11월 24일 월요일
-   **UI 입력 가이드 개선**: `dungeon/ui.py` 파일에서 메인 메뉴의 플레이어 이름 입력 프롬프트에서 불필요한 `(Enter)` 가이드를 제거했습니다.
-   **실시간 입력 반영**: `dungeon/ui.py` 파일의 `render_all` 함수 내 게임 조작 가이드를 실시간 키 입력 방식에 맞춰 WASD, 방향키, HJKL, YUBN 등 다양한 이동 옵션과 인벤토리([I]) 단축키를 명시하도록 업데이트했습니다.
-   **엔진 입력 처리 확인**: `dungeon/engine.py`는 이미 `readchar` 라이브러리를 사용하여 실시간 키 입력을 처리하고 있으므로 별도 수정 사항이 없습니다.
-   **NameError 수정**: `dungeon/system.py` 파일에 `DungeonMap` 클래스를 임포트하여 `MovementSystem` 초기화 시 `NameError`가 발생하지 않도록 수정했습니다.
-   **NameError 수정**: `dungeon/system.py` 파일에 `Item` 클래스를 임포트하여 `InventorySystem` 클래스 내 `add_item` 메서드에서 `NameError`가 발생하지 않도록 수정했습니다.
-   **실시간 입력 처리 구현**: `dungeon/system.py` 파일의 `InputSystem`에서 `input()` 대신 `readchar.readchar()`를 사용하여 Enter 키 없이 바로 입력이 처리되도록 수정하고, `readchar` 모듈을 임포트했습니다.
-   **NameError 수정**: `dungeon/system.py` 파일에 `logging` 모듈을 임포트하여 `InputSystem`에서 `NameError`가 발생하지 않도록 수정했습니다.

### 2025년 12월 25일 목요일 (시스템 심화 및 전투 다각화)
- ECS 아키텍처 도입 (전문화된 시스템 기반 로직 처리)
- 스태미나 시스템 및 UI 고도화 (HP/MP/STM 바 및 직업 표시)
- 속성 상성 시스템 (5대 속성 및 상성 데미지 보정)
- 원거리 방향성 공격 시스템 (Space + 방향키, 사거리 및 거리별 데미지 보정)
- 고급 시스템 확장 (맵 이동 고도화, 시체/루팅, 보물상자, 상점 시스템, 속성별 몬스터 색상)
도입하여 특정 방향으로 사거리 내 모든 적을 일직선 타격(관통)할 수 있는 시스템을 구현했습니다.
- **거리별 데미지 보정**: 원거리 공격 시 타겟과의 거리에 따라 데미지가 감쇄되는 밸런스 로직을 적용했습니다.
    - **기술 문서 업데이트**: `GEMINI.md`를 최신 명세에 맞게 전면 개편했습니다.

### 2025년 12월 26일 금요일 (고급 전투 및 접두어 시스템)
- **접두어 시스템 (Affix System)**: 아이템 및 몬스터 생성 시 랜덤 접두어("불타는", "날카로운" 등)가 부여되며, 이름/스탯/속성이 변화합니다.
- **고급 전투 메커니즘**:
    - **SPLASH**: 공격 시 주변 8칸 범위 피해.
    - **PIERCING**: 투사체가 적을 관통하여 일직선상 다수 타격.
- **버그 수정**: 데이터 로딩 오류(CSV 파싱) 및 `Start.py` 크러쉬 해결.

### 2025년 12월 27일 토요일 (실제 오디오 시스템 및 자동화)
- **상용 수준 리얼 오디오 시스템**: `aplay` 연동을 통해 터미널 환경에서도 비동기 배경음 및 효과음 재생 구현.
- **다이내믹 드라이버**: 스킬 데이터(`SOUND_MAGIC_FIRE` 등) 및 상황(Hit, Miss, Block)에 따른 지능형 사운드 트리거.
- **SFX Extractor Bridge**: GEMINI/Veo 등으로 생성한 영상에서 사운드를 자동 추출 및 배치하는 기술 파이프라인 구축.
- **보스 시스템 고도화**: `maps.csv` 기반의 층별 보스 스폰 및 멀티 보스 웨이브 구현.

## 어빌리티 플래그 설명 (Ability Flags)

### 1. 스킬 플래그 (Skill Flags)

| 플래그 | 설명 | 적용 효과 |
| :--- | :--- | :--- |
| **PROJECTILE** | 발사체 형태 | 지정된 사거리만큼 투사체를 발사합니다. |
| **AREA** | 범위 공격 형태 | 플레이어 주변 또는 지정된 위치의 일정 반경에 공격을 가합니다. |
| **AURA** | 지속형 오라 | 플레이어를 따라다니며 일정 시간 동안 주변 적에게 지속 데미지를 입힙니다. |
| **STUN** | 기절 효과 | 적중 시 대상을 일정 시간(기본 2초) 동안 행동 불능 상태로 만듭니다. |
| **KNOCKBACK** | 밀쳐내기 | 적중 시 대상을 공격자의 반대 방향으로 밀어냅니다. |
| **EXPLOSION** | 폭발 연출 | 투사체가 소멸하거나 적중할 때 주변에 시각적 폭발 효과와 데미지를 줍니다. |
| **SPLIT** | 투사체 분열 | 발사 시 투사체가 여러 갈래로 갈라졌다가 다시 모이는 연출을 합니다. |
| **CONVERGE** | 투사체 수렴 | 반대 방향으로 발사된 투사체들이 다시 중앙으로 모여 강력한 피해를 줍니다. |
| **SCALABLE** | 레벨 스케일링 | 스킬 레벨에 따라 데미지(+50%), 사거리(+1), 지속시간(+1)이 증가합니다. |
| **RECOVERY** | 회복 스킬 | 데미지 대신 HP 또는 MP를 회복시키는 효과를 가집니다. |
| **COST_HP** | HP 소모 | 스킬 사용 시 MP 대신 HP를 소모합니다. |
| **COST_MP** | MP 소모 | 스킬 사용 시 MP를 소모합니다. |
| **COST_STM** | 스테미너 소모 | 스킬 사용 시 스테미너를 소모합니다. |

### 2. 몬스터 플래그 (Monster Flags)

| 플래그 | 설명 | 적용 효과 |
| :--- | :--- | :--- |
| **STUN_ON_HIT** | 피격 시 기절 | 몬스터의 근접 공격에 맞았을 때 플레이어를 기절시킬 확률이 생깁니다. |
| **TELEPORT** | 순간 이동 | 이동 시 무작위 인접 위치로 순간 이동하거나 거리를 벌립니다. |
| **FIRE_IMMUNE** | 화염 면역 | '불(FIRE)' 속성의 공격으로부터 데미지를 입지 않습니다. |
| **BOSS** | 보스 등급 | 행동 패턴이 더 위협적이며, 사망 시 특별한 보상을 줄 확률이 높습니다. |
| **SPLIT_ON_DEATH**| 사망 시 분열 | 죽었을 때 더 작은 하위 몬스터들을 소환합니다. |

### 3. 아이템/무기 플래그 (Item Flags)

| 플래그 | 설명 | 적용 효과 |
| :--- | :--- | :--- |
| **PIERCING** | 관통 공격 | 발사체가 적을 뚫고 지나가며 경로상의 모든 적에게 피해를 줍니다. |
| **RANGED** | 원거리 무기 | 일반 근접 공격 대신 사거리를 가진 공격을 수행할 수 있게 합니다. |
| **SPLASH** | 스플래쉬 | 공격 시 대상 주변 8칸에도 50%의 피해를 입힙니다. |

### 4. 사운드 플래그 (Sound Flags)
| 플래그 | 설명 | 매핑 파일 (권장) |
| :--- | :--- | :--- |
| **SOUND_MAGIC_FIRE** | 화석/화염 마법 | `fire.wav` |
| **SOUND_HEAL** | 회복 스킬 | `heal.wav` |
| **SOUND_SWING**| 무기 휘두르기 | `swing.wav` |
| **SOUND_ID_XXX** | 고유 사운드 ID | `skill_XXX.wav` |


## 일반적인 명령어

-   **게임 실행**:
    ```bash
    python3 /home/dogsinatas/python_project/dungeon/dungeon/Start.py
    ```
-   **저장 데이터 삭제**:
    ```bash
    rm -rf /home/dogsinatas/python_project/dungeon/game_data/*
    ```