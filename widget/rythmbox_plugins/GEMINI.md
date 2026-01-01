개요
1. GTK3 기반의 음악 플레이어 위젯
2. 데스크탑 화면에 현재 재생중인 음악 표시 및 제어 

필요 기능
1. 엘범 아트워크 표시
2. CAVA와 같은 시각화 기능 추가 
3. 음악 플레이어 제어 (재생, 일시정지, 다음 곡, 이전 곡)
4. 가상 화면을 옮기더라도 항상 화면에 표시
5. 위젯은 드래그 앤 드롭으로 위치 변경 가능
6. 사이즈 조절 옵션 및 투명도 조절 옵션 

기술 스펙   
1. python-dbus 라이브러리 사용
2. 지원하는 음악 플레이어 : Audacious, Spotify, Rhythmbox, VLC, Lollypop, Clementine, MPD 등펙 

sudo apt install python3-gi python3-gi-cairo python3-dbus gir1.2-gtk-3.0
