import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from config import Config
from window import MainWindow
from dialogs import ConfigureSourcesDialog


class Application(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = Config()
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = self.props.active_window
        if not win:
            win = MainWindow(config=self.config, application=app)

        
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.add_action(about_action)
        
        configure_action = Gio.SimpleAction.new("configure_sources", None)
        configure_action.connect("activate", self.on_configure_sources)
        self.add_action(configure_action)

        
        win.present()
        
        
        GLib.idle_add(self._load_data_async, win)
    
    def _load_data_async(self, win):
        if not self.config.has_any_tsv_urls():
            self._show_config_dialog(win)
        else:
            win.load_data()
        return False  
    
    def _show_config_dialog(self, win):
        dialog = ConfigureSourcesDialog(self.config, lambda: self._on_config_complete(win))
        dialog.present(win)
    
    def _on_config_complete(self, win):
        win.show_toast("Configuration saved")
        win.load_data()
    
    def on_configure_sources(self, action, param):
        win = self.props.active_window
        if win:
            self._show_config_dialog(win)

    def on_about_action(self, action, param):
        about = Adw.AboutDialog(
            application_name="PkgHarbor",
            application_icon="com.cherryyeti.PkgHarbor",
            developer_name="CherryYeti",
            version="0.1.0",
            copyright="© 2025 CherryYeti",
            license_type=Gtk.License.GPL_2_0_ONLY,
            website="https://codeberg.org/CherryYeti/PkgHarbor",
            issue_url="https://codeberg.org/CherryYeti/PkgHarbor/issues",
            developers=[
                "CherryYeti",
            ],
            comments="PKGHarbor is a GTK frontend for NoPayStation",
        )
        about.present(self.props.active_window)
