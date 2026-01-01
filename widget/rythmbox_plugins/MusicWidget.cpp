#include "MusicWidget.h"
#include <iostream>
#include <random> // for simulated spectrum

// Constants (can be moved to a config.h)
const int DEFAULT_WIDTH = 400;
const int DEFAULT_HEIGHT = 200;
const double DEFAULT_OPACITY = 0.8;

MusicWidget::MusicWidget()
    : m_MainBox(Gtk::Orientation::ORIENTATION_VERTICAL, 5),
      m_TopHBox(Gtk::Orientation::ORIENTATION_HORIZONTAL, 10),
      m_PlayerInfoControlsVBox(Gtk::Orientation::ORIENTATION_VERTICAL, 5),
      m_ControlHBox(Gtk::Orientation::ORIENTATION_HORIZONTAL, 5),
      m_AlbumArt(Gtk::Stock::MEDIA_OPTICAL, Gtk::ICON_SIZE_DIALOG), // Gtk::Stock::MEDIA_OPTICAL instead of icon name
      m_TrackLabel("No Track Playing"),
      m_ArtistLabel(""),
      m_PrevButton(Gtk::Stock::MEDIA_SKIP_BACKWARD),
      m_PlayPauseButton(Gtk::Stock::MEDIA_PLAY),
      m_NextButton(Gtk::Stock::MEDIA_SKIP_FORWARD),
      m_OpacityScale(Gtk::Orientation::ORIENTATION_HORIZONTAL),
      m_is_dragging(false)
{
    set_default_size(DEFAULT_WIDTH, DEFAULT_HEIGHT);
    set_decorated(false);
    set_skip_taskbar_hint(true);
    set_keep_above(true);
    set_type_hint(Gdk::WindowTypeHint::TYPE_HINT_UTILITY);

    // For transparency
    set_app_paintable(true);
    auto screen = Gdk::Screen::get_default();
    if (screen) {
        set_visual(screen->get_rgba_visual());
    }
    set_opacity(DEFAULT_OPACITY); // Gtk::Window::set_opacity directly for Gtk3

    add(m_MainBox);
    m_MainBox.set_name("music-widget"); // For CSS

    // Layout
    m_MainBox.pack_start(m_TopHBox, Gtk::PACK_EXPAND_WIDGET, 0);
    m_TopHBox.pack_start(m_AlbumArt, Gtk::PACK_SHRINK, 10);
    m_TopHBox.pack_start(m_PlayerInfoControlsVBox, Gtk::PACK_EXPAND_WIDGET, 0);

    m_PlayerInfoControlsVBox.pack_start(m_TrackLabel, Gtk::PACK_SHRINK, 0);
    m_TrackLabel.set_halign(Gtk::ALIGN_START);
    m_PlayerInfoControlsVBox.pack_start(m_ArtistLabel, Gtk::PACK_SHRINK, 0);
    m_ArtistLabel.set_halign(Gtk::ALIGN_START);
    m_PlayerInfoControlsVBox.pack_start(m_ControlHBox, Gtk::PACK_SHRINK, 0);

    m_ControlHBox.pack_start(m_PrevButton, Gtk::PACK_SHRINK, 0);
    m_ControlHBox.pack_start(m_PlayPauseButton, Gtk::PACK_SHRINK, 0);
    m_ControlHBox.pack_start(m_NextButton, Gtk::PACK_SHRINK, 0);

    // Spectrum Area
    m_SpectrumDrawingArea.set_size_request(-1, 80);
    m_SpectrumDrawingArea.signal_draw().connect(sigc::mem_fun(*this, &MusicWidget::on_draw));
    m_SpectrumDrawingArea.set_name("spectrum-area"); // For CSS
    m_MainBox.pack_start(m_SpectrumDrawingArea, Gtk::PACK_SHRINK, 0);

    // Opacity Scale
    m_OpacityScale.set_range(0.1, 1.0);
    m_OpacityScale.set_increments(0.05, 0.1);
    m_OpacityScale.set_value(DEFAULT_OPACITY);
    m_OpacityScale.signal_value_changed().connect(sigc::mem_fun(*this, &MusicWidget::on_opacity_scale_changed));
    m_MainBox.pack_end(m_OpacityScale, Gtk::PACK_SHRINK, 5);

    // Connect signals for buttons
    m_PrevButton.signal_clicked().connect(sigc::mem_fun(*this, &MusicWidget::on_prev_clicked));
    m_PlayPauseButton.signal_clicked().connect(sigc::mem_fun(*this, &MusicWidget::on_play_pause_clicked));
    m_NextButton.signal_clicked().connect(sigc::mem_fun(*this, &MusicWidget::on_next_clicked));

    // Connect signals for window dragging
    add_events(Gdk::BUTTON_PRESS_MASK | Gdk::BUTTON_RELEASE_MASK | Gdk::POINTER_MOTION_MASK);
    signal_button_press_event().connect(sigc::mem_fun(*this, &MusicWidget::on_button_press_event));
    signal_button_release_event().connect(sigc::mem_fun(*this, &MusicWidget::on_button_release_event));
    signal_motion_notify_event().connect(sigc::mem_fun(*this, &MusicWidget::on_motion_notify_event));

    // Initialize DBus and spectrum
    init_dbus();
    Glib::signal_timeout().connect(sigc::mem_fun(*this, &MusicWidget::update_spectrum_data), 100);

    // Load CSS
    auto css_provider = Gtk::CssProvider::create();
    try {
        css_provider->load_from_path("style.css");
        Gtk::StyleContext::add_provider_for_screen(screen, css_provider, GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    } catch (const Glib::Error& ex) {
        std::cerr << "Error loading CSS: " << ex.what() << std::endl;
    }

    show_all_children();
}

MusicWidget::~MusicWidget() {}

bool MusicWidget::on_draw(const Cairo::RefPtr<Cairo::Context>& cr) {
    const auto allocation = m_SpectrumDrawingArea.get_allocation();
    const double width = allocation.get_width();
    const double height = allocation.get_height();

    cr->set_line_width(2);
    double bar_width = width / m_spectrum_data.size();

    for (size_t i = 0; i < m_spectrum_data.size(); ++i) {
        double value = m_spectrum_data[i];
        double r = static_cast<double>(i) / m_spectrum_data.size();
        double g = 1.0 - r;
        double b = 0.5;
        cr->set_source_rgba(r, g, b, 0.8);

        double bar_height = height * value;
        cr->rectangle(i * bar_width, height - bar_height, bar_width * 0.8, bar_height);
        cr->fill();
    }
    return true;
}

bool MusicWidget::on_button_press_event(GdkEventButton* event) {
    if (event->type == Gdk::BUTTON_PRESS && event->button == 1) {
        m_is_dragging = true;
        m_drag_start_x = static_cast<int>(event->x_root - get_allocation().get_x());
        m_drag_start_y = static_cast<int>(event->y_root - get_allocation().get_y());
        return true;
    }
    return false;
}

bool MusicWidget::on_button_release_event(GdkEventButton* event) {
    if (event->type == Gdk::BUTTON_RELEASE && event->button == 1) {
        m_is_dragging = false;
        return true;
    }
    return false;
}

bool MusicWidget::on_motion_notify_event(GdkEventMotion* event) {
    if (m_is_dragging) {
        int new_x = static_cast<int>(event->x_root - m_drag_start_x);
        int new_y = static_cast<int>(event->y_root - m_drag_start_y);
        move(new_x, new_y);
        return true;
    }
    return false;
}

void MusicWidget::on_opacity_scale_changed() {
    set_opacity(m_OpacityScale.get_value());
    // For CSS based opacity, you would need to regenerate/update CSS
    // Similar to Python example, but Gtkmm provides set_opacity directly
}

bool MusicWidget::update_spectrum_data() {
    // Simulate spectrum data
    static std::default_random_engine generator;
    static std::uniform_real_distribution<double> distribution(0.1, 1.0);
    m_spectrum_data.clear();
    for (int i = 0; i < 50; ++i) {
        m_spectrum_data.push_back(distribution(generator));
    }
    m_SpectrumDrawingArea.queue_draw(); // Request redraw
    return true; // Keep the timeout running
}

// Placeholder for DBus initialization and control
void MusicWidget::init_dbus() {
    // Using Gio::DBus (GLibmm's DBus wrapper)
    // Glib::RefPtr<Gio::DBus::Connection> Gio::DBus::Connection::get_for_bus(Gio::DBus::BusType::SESSION);
    // Connection to MPRIS interfaces etc.
    // This part requires more advanced DBus C++ coding.
    // Example: https://docs.gtkmm.org/giomm/stable/classGio_1_1DBus_1_1Connection.html
    // You would use Gio::DBus::Proxy to interact with MPRIS players.
    // And Gio::DBus::Connection::signal_name_owner_changed() to detect player changes.
}

void MusicWidget::update_player_status() {
    // Fetch current player status via DBus and update UI
    // This is where you'd use Gio::DBus::Proxy for 'org.mpris.MediaPlayer2.Player' interface
    // to get Metadata, PlaybackStatus etc.
}

void MusicWidget::call_player_method(const Glib::ustring& method_name) {
    // Call DBus method on the current player (e.g., PlayPause, Next, Previous)
}

void MusicWidget::on_prev_clicked() {
    std::cout << "Previous clicked!" << std::endl;
    call_player_method("Previous");
}

void MusicWidget::on_play_pause_clicked() {
    std::cout << "Play/Pause clicked!" << std::endl;
    call_player_method("PlayPause");
    // Update button icon based on actual playback status
}

void MusicWidget::on_next_clicked() {
    std::cout << "Next clicked!" << std::endl;
    call_player_method("Next");
}

void MusicWidget::on_name_owner_changed(const Glib::RefPtr<Gio::DBus::Connection>& connection,
                                       const Glib::ustring& sender_name,
                                       const Glib::ustring& node_name,
                                       const Glib::ustring& old_owner,
                                       const Glib::ustring& new_owner)
{
    // Handle player start/stop events
    if (node_name.find("org.mpris.MediaPlayer2.") == 0) {
        if (!new_owner.empty()) {
            std::cout << "Player started: " << node_name << std::endl;
            m_current_player_bus_name = node_name;
            update_player_status();
        } else if (!old_owner.empty() && node_name == m_current_player_bus_name) {
            std::cout << "Player stopped: " << node_name << std::endl;
            m_current_player_bus_name = "";
            m_TrackLabel.set_text("No Track Playing");
            m_ArtistLabel.set_text("");
            m_AlbumArt.set(Gtk::Stock::MEDIA_OPTICAL, Gtk::ICON_SIZE_DIALOG);
            m_PlayPauseButton.set_image_from_icon_name(Gtk::Stock::MEDIA_PLAY, Gtk::ICON_SIZE_LARGE_TOOLBAR);
        }
    }
}
