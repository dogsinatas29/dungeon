# main.py
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from widget import MusicWidget

def main():
    win = MusicWidget()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
