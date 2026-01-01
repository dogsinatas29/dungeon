import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

import cairo
import random # 스펙트럼 테스트용, 실제로는 오디오 데이터 사용

from config import DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_OPACITY

class MusicWidget(Gtk.Window):
    def __init__(self):
        super().__init__(title="Music Widget")
        self.set_default_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.set_decorated(False) # 창 장식 제거
        self.set_skip_taskbar_hint(True) # 작업 표시줄에 표시 안 함
        self.set_keep_above(True) # 항상 맨 위에 표시 (가상 화면 이동해도 유지)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY) # 유틸리티 창으로 설정
        
        self.set_app_paintable(True) # 커스텀 그리기 허용
        self.set_visual(self.get_screen().get_rgba_visual()) # 투명도 적용을 위한 RGBA 비주얼 설정
        
        self.current_opacity = DEFAULT_OPACITY
        self.load_css()
        
        self.init_ui()
        self.init_dbus()
        
        # 드래그 앤 드롭을 위한 변수
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # 스펙트럼 시뮬레이션을 위한 타이머 (실제 오디오 데이터로 대체)
        GLib.timeout_add(100, self.update_spectrum)
        self.spectrum_data = [0] * 50 # 예시 데이터

    def load_css(self):
        css_provider = Gtk.CssProvider()
        try:
            css_provider.load_from_path('style.css')
            screen = Gdk.Screen.get_default()
            style_context = self.get_style_context()
            style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            style_context.add_class("music-widget") # CSS 셀렉터 추가
        except Exception as e:
            print(f"Error loading CSS: {e}")

    def init_ui(self):
        # 최상위 컨테이너 (그리드 또는 박스)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.add(main_box)
        main_box.set_name("music-widget") # CSS 셀렉터 연결

        # 앨범 아트 및 컨트롤 버튼 영역
        top_hbox = Gtk.HBox(spacing=10)
        main_box.pack_start(top_hbox, True, True, 0)

        # 앨범 아트
        self.album_art = Gtk.Image.new_from_icon_name("media-optical", Gtk.IconSize.DIALOG)
        top_hbox.pack_start(self.album_art, False, False, 10)

        # 플레이어 정보 및 컨트롤 버튼
        player_info_controls_vbox = Gtk.VBox(spacing=5)
        top_hbox.pack_start(player_info_controls_vbox, True, True, 0)
        
        self.track_label = Gtk.Label(label="No Track Playing")
        self.track_label.set_halign(Gtk.Align.START)
        player_info_controls_vbox.pack_start(self.track_label, False, False, 0)

        self.artist_label = Gtk.Label(label="")
        self.artist_label.set_halign(Gtk.Align.START)
        player_info_controls_vbox.pack_start(self.artist_label, False, False, 0)

        # 컨트롤 버튼
        control_hbox = Gtk.HBox(spacing=5)
        player_info_controls_vbox.pack_start(control_hbox, False, False, 0)

        self.prev_button = Gtk.Button.new_from_icon_name("media-skip-backward", Gtk.IconSize.LARGE_TOOLBAR)
        self.play_pause_button = Gtk.Button.new_from_icon_name("media-playback-start", Gtk.IconSize.LARGE_TOOLBAR)
        self.next_button = Gtk.Button.new_from_icon_name("media-skip-forward", Gtk.IconSize.LARGE_TOOLBAR)

        self.prev_button.connect("clicked", self.on_prev_clicked)
        self.play_pause_button.connect("clicked", self.on_play_pause_clicked)
        self.next_button.connect("clicked", self.on_next_clicked)
        
        control_hbox.pack_start(self.prev_button, False, False, 0)
        control_hbox.pack_start(self.play_pause_button, False, False, 0)
        control_hbox.pack_start(self.next_button, False, False, 0)

        # 스펙트럼 시각화 영역
        self.spectrum_drawing_area = Gtk.DrawingArea()
        self.spectrum_drawing_area.set_size_request(-1, 80) # 높이 80px
        self.spectrum_drawing_area.connect("draw", self.on_draw_spectrum)
        self.spectrum_drawing_area.set_name("spectrum-area") # CSS 셀렉터 연결
        main_box.pack_start(self.spectrum_drawing_area, False, False, 0)
        
        # 투명도 및 크기 조절 (슬라이더 또는 메뉴)
        # 예시: 슬라이더를 추가
        self.opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.1, 1.0, 0.05)
        self.opacity_scale.set_value(self.current_opacity)
        self.opacity_scale.connect("value-changed", self.on_opacity_changed)
        main_box.pack_end(self.opacity_scale, False, False, 5) # 하단에 배치

        # 위젯 이동을 위한 이벤트 연결
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_mouse_motion)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                        Gdk.EventMask.BUTTON_RELEASE_MASK | 
                        Gdk.EventMask.POINTER_MOTION_MASK)
        
        # 크기 조절 핸들 (우측 하단 코너에 Invisible Resize Grip 추가)
        # Gtk.Window에는 기본적으로 resize_grip이 있지만, set_decorated(False)를 사용하면 사라짐.
        # 따라서 수동으로 구현하거나, 마우스 커서 변화 + 이벤트 처리로 구현해야 함.
        # 여기서는 간단하게 윈도우 가장자리를 잡고 크기 조절하는 방식 고려 (더 복잡한 구현 필요)

    def init_dbus(self):
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        
        self.mpris_players = {} # {'player_name': dbus_proxy_object}
        self.current_player = None
        
        self.bus.add_signal_receiver(self.on_name_owner_changed,
                                     bus_name="org.freedesktop.DBus",
                                     signal_name="NameOwnerChanged",
                                     arg0="org.mpris.MediaPlayer2.")
        
        # 현재 활성화된 플레이어 찾기
        self.scan_for_players()
        
        # 초기 플레이어 상태 업데이트
        self.update_player_status()

    def scan_for_players(self):
        # 모든 MPRIS 플레이어를 찾아서 등록
        pass # 구현 필요: DBus를 통해 org.mpris.MediaPlayer2.* 서비스 스캔

    def on_name_owner_changed(self, name, old_owner, new_owner):
        # 플레이어가 시작되거나 종료될 때 처리
        if name.startswith("org.mpris.MediaPlayer2."):
            if new_owner: # 새 플레이어 시작
                print(f"Player started: {name}")
                # self.mpris_players[name] = self.bus.get_object(name, "/org/mpris/MediaPlayer2")
                self.current_player = name # 첫 발견된 플레이어를 현재 플레이어로 설정 (개선 필요)
                self.update_player_status()
            elif old_owner: # 플레이어 종료
                print(f"Player stopped: {name}")
                if name == self.current_player:
                    self.current_player = None
                    self.track_label.set_label("No Track Playing")
                    self.artist_label.set_label("")
                    self.album_art.set_from_icon_name("media-optical", Gtk.IconSize.DIALOG)
                    self.play_pause_button.set_image(Gtk.Image.new_from_icon_name("media-playback-start", Gtk.IconSize.LARGE_TOOLBAR))

    def update_player_status(self):
        if not self.current_player:
            return

        try:
            # MediaPlayer2 인터페이스와 Player 인터페이스 사용
            proxy = self.bus.get_object(self.current_player, "/org/mpris/MediaPlayer2")
            properties_iface = dbus.Interface(proxy, 'org.freedesktop.DBus.Properties')
            player_iface = dbus.Interface(proxy, 'org.mpris.MediaPlayer2.Player')
            
            props = properties_iface.GetAll('org.mpris.MediaPlayer2.Player')
            
            # 메타데이터 추출
            metadata = props.get('Metadata', {})
            track_title = metadata.get('xesam:title', 'Unknown Title')
            track_artist = ", ".join(metadata.get('xesam:artist', ['Unknown Artist']))
            album_art_uri = metadata.get('mpris:artUrl', None)
            playback_status = props.get('PlaybackStatus', 'Stopped')

            self.track_label.set_label(track_title)
            self.artist_label.set_label(track_artist)

            # 앨범 아트 업데이트
            if album_art_uri:
                # TODO: URI를 GdkPixbuf.Pixbuf로 로드하여 이미지 설정 (WebP, File 등 URI 스킴 처리)
                # GdkPixbuf.Pixbuf.new_from_file_at_size() 또는 GdkPixbuf.Pixbuf.new_from_stream() 사용
                print(f"Album Art URI: {album_art_uri}")
                # 임시: 아이콘으로 대체
                self.album_art.set_from_icon_name("media-optical", Gtk.IconSize.DIALOG) 
            else:
                self.album_art.set_from_icon_name("media-optical", Gtk.IconSize.DIALOG)

            # 재생/일시정지 버튼 아이콘 업데이트
            if playback_status == 'Playing':
                self.play_pause_button.set_image(Gtk.Image.new_from_icon_name("media-playback-pause", Gtk.IconSize.LARGE_TOOLBAR))
            else:
                self.play_pause_button.set_image(Gtk.Image.new_from_icon_name("media-playback-start", Gtk.IconSize.LARGE_TOOLBAR))

        except dbus.exceptions.DBusException as e:
            print(f"Error getting player status: {e}")
            self.track_label.set_label("No Track Playing")
            self.artist_label.set_label("")
            self.album_art.set_from_icon_name("media-optical", Gtk.IconSize.DIALOG)
            self.play_pause_button.set_image(Gtk.Image.new_from_icon_name("media-playback-start", Gtk.IconSize.LARGE_TOOLBAR))

        # TODO: PropertiesChanged 시그널을 받아서 상태 업데이트하는 로직 추가

    # --- 플레이어 제어 ---
    def call_player_method(self, method_name):
        if not self.current_player:
            return
        try:
            proxy = self.bus.get_object(self.current_player, "/org/mpris/MediaPlayer2")
            player_iface = dbus.Interface(proxy, 'org.mpris.MediaPlayer2.Player')
            getattr(player_iface, method_name)()
            # 명령 후 상태가 바로 반영되지 않을 수 있으므로 잠시 후 업데이트
            GLib.timeout_add(100, self.update_player_status)
        except dbus.exceptions.DBusException as e:
            print(f"Error calling {method_name}: {e}")

    def on_prev_clicked(self, button):
        self.call_player_method("Previous")

    def on_play_pause_clicked(self, button):
        self.call_player_method("PlayPause")

    def on_next_clicked(self, button):
        self.call_player_method("Next")

    # --- 드래그 앤 드롭으로 위치 변경 ---
    def on_button_press(self, widget, event):
        if event.button == 1: # 좌클릭
            self.is_dragging = True
            self.drag_start_x = event.x_root - self.get_allocation().x
            self.drag_start_y = event.y_root - self.get_allocation().y
            return True
        return False

    def on_button_release(self, widget, event):
        if event.button == 1:
            self.is_dragging = False
            return True
        return False

    def on_mouse_motion(self, widget, event):
        if self.is_dragging:
            new_x = int(event.x_root - self.drag_start_x)
            new_y = int(event.y_root - self.drag_start_y)
            self.move(new_x, new_y)
            return True
        return False

    # --- 투명도 조절 ---
    def on_opacity_changed(self, scale):
        self.current_opacity = scale.get_value()
        # CSS를 통해 투명도 변경
        # Gtk.Window의 opacity는 deprecated 될 수 있으므로, CSS를 이용하는 것이 권장됨
        # 아니면 Gdk.Window.set_opacity() 사용 (deprecated 되지 않은 경우)
        # self.get_window().set_opacity(self.current_opacity)
        
        # CSS 업데이트 방식 (조금 더 복잡)
        css_provider = Gtk.CssProvider()
        css_data = f"#music-widget {{ background-color: rgba(30, 30, 30, {self.current_opacity}); }}"
        css_provider.load_from_data(bytes(css_data.encode()))
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


    # --- 스펙트럼 시각화 ---
    def on_draw_spectrum(self, widget, cr):
        # Cairo를 사용하여 스펙트럼 그리기
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        cr.set_line_width(2)
        bar_width = width / len(self.spectrum_data)
        
        for i, value in enumerate(self.spectrum_data):
            # 스펙트럼 바 색상 그라데이션 (예시)
            r = i / len(self.spectrum_data)
            g = 1 - r
            b = 0.5
            cr.set_source_rgba(r, g, b, 0.8) # 색상 및 투명도
            
            bar_height = height * value
            cr.rectangle(i * bar_width, height - bar_height, bar_width * 0.8, bar_height)
            cr.fill()

    def update_spectrum(self):
        # 실제 오디오 데이터를 가져와서 spectrum_data를 업데이트하는 부분
        # 여기서는 임시로 랜덤 값을 사용합니다.
        self.spectrum_data = [random.uniform(0.1, 1.0) for _ in range(50)]
        self.spectrum_drawing_area.queue_draw() # DrawingArea를 다시 그리도록 요청
        return True # GLib.timeout_add가 계속 호출되도록 True 반환

    # --- 크기 조절 (추가 구현 필요) ---
    # Gtk.Window는 set_decorated(False) 시 기본 크기 조절 기능이 없어짐.
    # 수동으로 Gdk.Window 이벤트 (motion-notify-event + cursor 변경)를 처리하여 구현해야 함.
    # set_size_request() 등을 이용하여 최소/최대 크기 제한 가능.
    # 예를 들어, 마우스가 위젯 가장자리에 있을 때 커서를 변경하고, 드래그 시 윈도우 크기를 조절.
