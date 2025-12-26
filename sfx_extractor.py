import subprocess
import os
import sys

def extract_sfx(input_video, start_time, duration, output_name):
    """영상에서 특정 구간의 소리만 추출하여 .wav로 저장"""
    # sounds 디렉토리 확인 및 생성
    sounds_dir = os.path.join(os.path.dirname(__file__), "sounds")
    if not os.path.exists(sounds_dir):
        os.makedirs(sounds_dir)
        print(f"📁 디렉토리 생성: {sounds_dir}")

    output_path = os.path.join(sounds_dir, f"{output_name}.wav")
    
    # ffmpeg 존재 확인
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("❌ 오류: 'ffmpeg'가 시스템에 설치되어 있지 않습니다.")
        print("설치 방법: sudo apt install ffmpeg")
        return False

    command = [
        'ffmpeg', '-i', input_video,
        '-ss', str(start_time), '-t', str(duration),
        '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
        output_path, '-y'
    ]
    
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if result.returncode == 0:
        print(f"✅ 추출 완료: {output_name}.wav ({start_time}s ~ {start_time+duration}s)")
        return True
    else:
        print(f"❌ 추출 실패: {output_name}.wav (ffmpeg 에러)")
        return False

def run_pack_extraction(video_file, pack_type="default"):
    """미리 정의된 팩 구성에 따라 일괄 추출"""
    
    # 예시 팩 구성 (필요에 따라 수정 가능)
    packs = {
        "battle": [
            (0, 1, 'swing'),
            (2, 1, 'hit'),
            (4, 1.5, 'crit'),
            (6, 1, 'miss'),
            (8, 1, 'block'),
            (10, 2, 'levelup'),
            (13, 1, 'coin'),
            (15, 0.5, 'step')
        ],
        "magic": [
            (0, 2, 'fire'),
            (3, 2, 'ice'),
            (6, 2, 'bolt'),
            (9, 2, 'heal'),
            (12, 2, 'bash'),
            (15, 3, 'explosion')
        ]
    }
    
    target_pack = packs.get(pack_type, [])
    if not target_pack:
        print(f"❓ 알 수 없는 팩 타입: {pack_type}")
        return

    print(f"🎬 '{video_file}'에서 '{pack_type}' 사운드 추출 시작...")
    success_count = 0
    for start, dur, name in target_pack:
        if extract_sfx(video_file, start, dur, name):
            success_count += 1
            
    print(f"\n✨ 작업 완료: {success_count}/{len(target_pack)}개 성공")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python3 sfx_extractor.py <영상파일명> [팩이름(battle/magic)]")
        print("예시: python3 sfx_extractor.py battle_pack.mp4 battle")
    else:
        video = sys.argv[1]
        pack = sys.argv[2] if len(sys.argv) > 2 else "battle"
        
        if not os.path.exists(video):
            print(f"❌ 파일을 찾을 수 없습니다: {video}")
        else:
            run_pack_extraction(video, pack)
