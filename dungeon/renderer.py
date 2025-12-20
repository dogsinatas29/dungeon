import os
import sys

# 터미널 색상 코드
COLOR_MAP = {
    "white": "\033[97m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "green": "\033[92m",
    "blue": "\033[94m",
    "gold": "\033[33m",
    "brown": "\033[38;5;130m",
    "dark_grey": "\033[90m",
    "reset": "\033[0m"
}

class Renderer:
    """
    화면 깜빡임을 방지하기 위한 더블 버퍼링 렌더러.
    프레임 버퍼를 메모리에 생성하고, 변경된 부분(또는 전체)을 한 번에 출력합니다.
    """
    def __init__(self, width=120, height=30):
        self.width = width
        self.height = height
        self.buffer = [[" " for _ in range(width)] for _ in range(height)]
        self.clear_command = 'cls' if os.name == 'nt' else 'clear'
        
        # 최초 실행 시 화면 지우기
        os.system(self.clear_command)
        # 커서 숨기기 (선택적)
        sys.stdout.write("\033[?25l")

    def clear_buffer(self):
        """버퍼를 공백으로 초기화"""
        self.buffer = [[" " for _ in range(self.width)] for _ in range(self.height)]

    def draw_char(self, x, y, char, color="white"):
        """특정 위치에 문자 하나를 버퍼에 기록"""
        if 0 <= x < self.width and 0 <= y < self.height:
            # 색상 코드를 포함한 문자열 저장
            # 주의: 버퍼에 색상 코드가 들어가면 길이 계산이 복잡해질 수 있음.
            # 여기서는 편의상 색상코드를 포함해서 저장하되, 
            # 실제로는 (char, color_code) 튜플이나 별도 버퍼를 쓰는 게 정석입니다.
            # 이 구현은 단순화를 위해 문자열을 통째로 넣습니다.
            
            color_code = COLOR_MAP.get(color, COLOR_MAP["white"])
            self.buffer[y][x] = f"{color_code}{char}{COLOR_MAP['reset']}"

    def draw_text(self, x, y, text, color="white"):
        """특정 위치에 문자열을 버퍼에 기록"""
        if 0 <= y < self.height:
            color_code = COLOR_MAP.get(color, COLOR_MAP["white"])
            current_x = x
            for char in text:
                if 0 <= current_x < self.width:
                    self.buffer[y][current_x] = f"{color_code}{char}{COLOR_MAP['reset']}"
                    current_x += 1

    def render(self):
        """버퍼의 내용을 터미널에 출력"""
        # 커서를 (0,0)으로 이동
        sys.stdout.write("\033[H")
        
        output_lines = []
        for row in self.buffer:
            # 각 행을 하나의 문자열로 결합 (이미 색상 코드가 포함됨)
            output_lines.append("".join(row))
        
        # 전체 화면을 한 번에 출력
        sys.stdout.write("\n".join(output_lines))
        sys.stdout.flush()

    def __del__(self):
        # 종료 시 커서 보이기 및 색상 초기화
        sys.stdout.write("\033[?25h")
        sys.stdout.write("\033[0m")
