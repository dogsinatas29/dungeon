#include <gtkmm/application.h>
#include "MusicWidget.h"

int main(int argc, char* argv[])
{
    auto app = Gtk::Application::create("org.dogsinatas.musicwidget", Gio::ApplicationFlags::APPLICATION_HANDLES_COMMAND_LINE);

    app->signal_activate().connect([&app]() {
        MusicWidget* widget = new MusicWidget();
        app->add_window(*widget); // Add to application
        widget->signal_hide().connect([widget]() { delete widget; }); // Delete widget when closed
        widget->show_all();
    });

    return app->run(argc, argv);
}
