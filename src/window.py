import gi
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Soup", "3.0")
from gi.repository import Gtk, Adw, Gio, GObject, Pango, GLib, Soup

from config import Config
from tsv_parser import TsvParser, TsvEntry


class EntryObject(GObject.Object):
    
    def __init__(self, entry):
        super().__init__()
        self.entry = entry


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.tsv_parser = TsvParser(config)
        self.current_entries = []
        self.active_downloads = {}  

        self.set_title("PkgHarbor")
        self.set_default_size(1000, 700)

        
        
        
        header_bar = Adw.HeaderBar()
        window_title = Adw.WindowTitle(title="PkgHarbor")
        header_bar.set_title_widget(window_title)

        
        self.search_button = Gtk.ToggleButton(icon_name="system-search-symbolic")
        self.search_button.connect("toggled", self._on_search_toggled)
        header_bar.pack_start(self.search_button)

        
        menu = Gio.Menu()
        menu.append("Configure TSV Sources", "app.configure_sources")
        menu.append("About PkgHarbor", "app.about")

        
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        
        
        
        self.toast_overlay = Adw.ToastOverlay()
        
        
        self.main_stack = Gtk.Stack()
        self.main_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        
        
        loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        loading_box.set_valign(Gtk.Align.CENTER)
        loading_box.set_halign(Gtk.Align.CENTER)
        
        spinner = Gtk.Spinner()
        spinner.set_size_request(32, 32)
        spinner.set_spinning(True)
        loading_box.append(spinner)
        
        loading_label = Gtk.Label(label="Loading...")
        loading_label.add_css_class("dim-label")
        loading_box.append(loading_label)
        
        self.main_stack.add_named(loading_box, "loading")
        
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        
        self.search_bar = Gtk.SearchBar()
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_bar.set_child(self.search_entry)
        self.search_bar.connect_entry(self.search_entry)
        content_box.append(self.search_bar)

        
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        filter_box.set_margin_top(12)
        filter_box.set_margin_bottom(12)
        filter_box.set_margin_start(12)
        filter_box.set_margin_end(12)

        
        category_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        category_label = Gtk.Label(label="Type:")
        category_label.add_css_class("dim-label")
        category_box.append(category_label)
        
        self.category_dropdown = Gtk.DropDown()
        self.category_model = Gtk.StringList()
        self.category_dropdown.set_model(self.category_model)
        self.category_dropdown.connect("notify::selected", self._on_filter_changed)
        category_box.append(self.category_dropdown)
        filter_box.append(category_box)

        
        platform_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        platform_label = Gtk.Label(label="Console:")
        platform_label.add_css_class("dim-label")
        platform_box.append(platform_label)
        
        self.platform_dropdown = Gtk.DropDown()
        self.platform_model = Gtk.StringList()
        self.platform_dropdown.set_model(self.platform_model)
        self.platform_dropdown.connect("notify::selected", self._on_filter_changed)
        platform_box.append(self.platform_dropdown)
        filter_box.append(platform_box)

        
        region_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        region_label = Gtk.Label(label="Region:")
        region_label.add_css_class("dim-label")
        region_box.append(region_label)
        
        self.region_dropdown = Gtk.DropDown()
        self.region_model = Gtk.StringList()
        self.region_dropdown.set_model(self.region_model)
        self.region_dropdown.connect("notify::selected", self._on_filter_changed)
        region_box.append(self.region_dropdown)
        filter_box.append(region_box)

        
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        filter_box.append(spacer)

        
        self.results_label = Gtk.Label(label="0 items")
        self.results_label.add_css_class("dim-label")
        filter_box.append(self.results_label)

        content_box.append(filter_box)

        
        table_container = Gtk.Frame()
        table_container.set_margin_start(12)
        table_container.set_margin_end(12)
        table_container.set_margin_bottom(12)
        table_container.set_vexpand(True)

        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        
        self.list_store = Gio.ListStore(item_type=EntryObject)
        self.selection_model = Gtk.SingleSelection(model=self.list_store)

        
        self.column_view = Gtk.ColumnView(model=self.selection_model)
        self.column_view.set_hexpand(True)
        self.column_view.set_vexpand(True)
        self.column_view.add_css_class("data-table")
        
        
        self._add_column("Name", self._create_name_cell, expand=True)
        self._add_column("Title ID", self._create_title_id_cell, width=110)
        self._add_column("Region", self._create_region_cell, width=70)
        self._add_column("Platform", self._create_platform_cell, width=80)
        self._add_column("Type", self._create_category_cell, width=80)
        self._add_column("Size", self._create_size_cell, width=90)
        self._add_button_column("", self._setup_download_button, self._bind_download_button, width=50)

        scrolled.set_child(self.column_view)
        table_container.set_child(scrolled)
        content_box.append(table_container)

        
        self.status_bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.status_bar.set_margin_top(6)
        self.status_bar.set_margin_bottom(6)
        self.status_bar.set_margin_start(12)
        self.status_bar.set_margin_end(12)
        
        
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.status_label = Gtk.Label(label="Welcome to PkgHarbor!")
        self.status_label.set_xalign(0)
        self.status_label.set_hexpand(True)
        self.status_label.add_css_class("dim-label")
        status_row.append(self.status_label)
        
        
        self.download_info_label = Gtk.Label()
        self.download_info_label.add_css_class("dim-label")
        self.download_info_label.set_visible(False)
        status_row.append(self.download_info_label)
        
        self.status_bar.append(status_row)
        
        
        self.download_progress = Gtk.ProgressBar()
        self.download_progress.set_visible(False)
        self.download_progress.set_show_text(False)
        self.status_bar.append(self.download_progress)
        
        content_box.append(self.status_bar)

        self.main_stack.add_named(content_box, "content")
        
        
        self.main_stack.set_visible_child_name("loading")
        
        self.toast_overlay.set_child(self.main_stack)

        
        
        
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        toolbar_view.set_content(self.toast_overlay)

        self.set_content(toolbar_view)
        
        
        self._populate_filters()
    
    def _add_column(self, title, factory_func, width=None, expand=False):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", factory_func)
        
        column = Gtk.ColumnViewColumn(title=title, factory=factory)
        column.set_resizable(True)
        
        if expand:
            column.set_expand(True)
        elif width:
            column.set_fixed_width(width)
        
        self.column_view.append_column(column)
    
    def _add_button_column(self, title, setup_func, bind_func, width=None):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", setup_func)
        factory.connect("bind", bind_func)
        
        column = Gtk.ColumnViewColumn(title=title, factory=factory)
        column.set_resizable(False)
        
        if width:
            column.set_fixed_width(width)
        
        self.column_view.append_column(column)
    
    def _on_factory_setup(self, factory, list_item):
        label = Gtk.Label()
        label.set_xalign(0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_margin_start(6)
        label.set_margin_end(6)
        label.set_margin_top(6)
        label.set_margin_bottom(6)
        list_item.set_child(label)
    
    def _setup_download_button(self, factory, list_item):
        button = Gtk.Button()
        button.set_icon_name("folder-download-symbolic")
        button.add_css_class("flat")
        button.set_valign(Gtk.Align.CENTER)
        button.set_halign(Gtk.Align.CENTER)
        button.set_tooltip_text("Download PKG")
        list_item.set_child(button)
    
    def _bind_download_button(self, factory, list_item):
        button = list_item.get_child()
        item = list_item.get_item()
        
        if item:
            entry = item.entry
            
            
            if hasattr(button, '_handler_id') and button._handler_id:
                button.disconnect(button._handler_id)
            
            if entry.has_download():
                button.set_sensitive(True)
                button.set_tooltip_text(f"Download {entry.name}")
                button._handler_id = button.connect("clicked", self._on_download_clicked, entry)
            else:
                button.set_sensitive(False)
                button.set_tooltip_text("Download not available")
                button._handler_id = None
    
    def _get_rap_status(self, entry):
        rap = entry.rap.strip() if entry.rap else ""
        rap_upper = rap.upper()
        
        if not rap or rap_upper == "":
            return ('none', None)
        elif rap_upper == "NOT REQUIRED":
            return ('not_required', None)
        elif rap_upper in ("UNLOCK/LICENSE BY DLC", "UNLOCK BY DLC", "LICENSE BY DLC"):
            return ('dlc_unlock', None)
        elif rap_upper == "MISSING":
            return ('missing', None)
        else:
            
            return ('available', rap)
    
    def _get_rap_download_url(self, entry):
        rap_status, rap_value = self._get_rap_status(entry)
        
        if rap_status != 'available' or not rap_value:
            return None
        
        content_id = entry.content_id
        if not content_id:
            return None
        
        
        base_url = "https://nopaystation.com/tools/rap2file"
        return f"{base_url}/{content_id}/{rap_value}"
    
    def _on_download_clicked(self, button, entry):
        
        if self.active_downloads:
            self.show_toast("A download is already in progress")
            return
        
        
        download_dir = self.config.get_download_directory()
        if not download_dir:
            self.show_toast("Please configure a download directory first")
            return
        
        
        filename = f"{entry.content_id or entry.title_id}.pkg"
        
        
        dialog = Gtk.FileDialog()
        dialog.set_title(f"Save {entry.name}")
        dialog.set_initial_name(filename)
        
        initial_folder = Gio.File.new_for_path(download_dir)
        dialog.set_initial_folder(initial_folder)
        
        dialog.save(self, None, self._on_save_dialog_response, entry)
    
    def _on_save_dialog_response(self, dialog, result, entry):
        try:
            file = dialog.save_finish(result)
            if file:
                dest_path = file.get_path()
                self._start_download(entry, dest_path)
        except Exception as e:
            if "Dismissed" not in str(e):
                self.show_toast(f"Error: {e}")
    
    def _start_download(self, entry, dest_path):
        self.update_status(f"Downloading: {entry.name}")
        
        
        self.download_progress.set_visible(True)
        self.download_progress.set_fraction(0.0)
        self.download_info_label.set_visible(True)
        self.download_info_label.set_label("Starting...")
        
        
        try:
            total_size = int(entry.file_size) if entry.file_size else 0
        except ValueError:
            total_size = 0
        
        
        session = Soup.Session()
        message = Soup.Message.new("GET", entry.pkg_url)
        
        if message is None:
            self.show_toast(f"Invalid URL for {entry.name}")
            self._hide_progress()
            return
        
        
        download_id = entry.content_id or entry.title_id
        self.active_downloads[download_id] = {
            "entry": entry,
            "dest_path": dest_path,
            "session": session,
            "total_size": total_size,
            "downloaded": 0,
            "file": None,
            "cancellable": Gio.Cancellable(),
            "type": "pkg"
        }
        
        
        session.send_async(
            message,
            GLib.PRIORITY_DEFAULT,
            self.active_downloads[download_id]["cancellable"],
            self._on_send_complete,
            download_id,
            message
        )
    
    def _on_send_complete(self, session, result, download_id, message):
        if download_id not in self.active_downloads:
            return
        
        download_info = self.active_downloads[download_id]
        
        try:
            input_stream = session.send_finish(result)
            
            if message.get_status() != Soup.Status.OK:
                self.show_toast(f"Download failed: HTTP {message.get_status()}")
                self._download_cleanup(download_id)
                return
            
            
            if download_info["total_size"] == 0:
                content_length = message.get_response_headers().get_content_length()
                if content_length > 0:
                    download_info["total_size"] = content_length
            
            
            download_info["file"] = open(download_info["dest_path"], "wb")
            download_info["input_stream"] = input_stream
            
            
            self._read_chunk(download_id)
            
        except Exception as e:
            self.show_toast(f"Download error: {e}")
            self._download_cleanup(download_id)
    
    def _read_chunk(self, download_id):
        if download_id not in self.active_downloads:
            return
        
        download_info = self.active_downloads[download_id]
        input_stream = download_info["input_stream"]
        
        
        input_stream.read_bytes_async(
            65536,
            GLib.PRIORITY_DEFAULT,
            download_info["cancellable"],
            self._on_chunk_read,
            download_id
        )
    
    def _on_chunk_read(self, input_stream, result, download_id):
        if download_id not in self.active_downloads:
            return
        
        download_info = self.active_downloads[download_id]
        
        try:
            gbytes = input_stream.read_bytes_finish(result)
            data = gbytes.get_data()
            
            if data and len(data) > 0:
                
                download_info["file"].write(data)
                download_info["downloaded"] += len(data)
                
                
                self._update_download_progress(download_id)
                
                
                self._read_chunk(download_id)
            else:
                
                self._download_complete(download_id)
                
        except Exception as e:
            self.show_toast(f"Download error: {e}")
            self._download_cleanup(download_id)
    
    def _update_download_progress(self, download_id):
        if download_id not in self.active_downloads:
            return
        
        download_info = self.active_downloads[download_id]
        downloaded = download_info["downloaded"]
        total_size = download_info["total_size"]
        file_type = download_info.get("type", "pkg").upper()
        
        if total_size > 0:
            fraction = min(downloaded / total_size, 1.0)
            self.download_progress.set_fraction(fraction)
            
            
            downloaded_str = self._format_size(downloaded)
            total_str = self._format_size(total_size)
            percent = int(fraction * 100)
            
            self.download_info_label.set_label(f"[{file_type}] {downloaded_str} / {total_str} ({percent}%)")
        else:
            
            self.download_progress.pulse()
            downloaded_str = self._format_size(downloaded)
            self.download_info_label.set_label(f"[{file_type}] {downloaded_str} downloaded")
    
    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def _download_complete(self, download_id):
        if download_id not in self.active_downloads:
            return
        
        download_info = self.active_downloads[download_id]
        entry = download_info["entry"]
        download_type = download_info.get("type", "pkg")
        
        
        if download_info["file"]:
            download_info["file"].close()
        
        
        if "input_stream" in download_info:
            download_info["input_stream"].close(None)
        
        if download_type == "pkg":
            
            self.download_progress.set_fraction(1.0)
            self.show_toast(f"Downloaded: {entry.name}")
            
            
            pkg_dest_path = download_info["dest_path"]
            del self.active_downloads[download_id]
            
            
            self._handle_rap_download(entry, pkg_dest_path)
        else:
            
            self.download_progress.set_fraction(1.0)
            self.download_info_label.set_label("Complete!")
            self.update_status(f"Downloaded {entry.name} with RAP")
            
            
            del self.active_downloads[download_id]
            
            
            GLib.timeout_add(2000, self._hide_progress)
    
    def _handle_rap_download(self, entry, pkg_dest_path):
        rap_status, rap_value = self._get_rap_status(entry)
        
        if rap_status == 'not_required':
            
            self._show_rap_info_dialog(
                entry,
                "RAP Not Required",
                f"The title \"{entry.name}\" does not require a RAP file for activation.",
                pkg_dest_path
            )
        elif rap_status == 'dlc_unlock':
            
            self._show_rap_info_dialog(
                entry,
                "License Required",
                f"The title \"{entry.name}\" requires a license from its DLC.\n\n"
                "You need to download and install the corresponding DLC to unlock this content.",
                pkg_dest_path
            )
        elif rap_status == 'missing':
            
            self._show_rap_info_dialog(
                entry,
                "RAP Missing",
                f"The RAP file for \"{entry.name}\" is not available in the database.\n\n"
                "You may need to obtain the RAP file from another source.",
                pkg_dest_path
            )
        elif rap_status == 'available':
            
            rap_url = self._get_rap_download_url(entry)
            if rap_url:
                self._start_rap_download(entry, pkg_dest_path, rap_url)
            else:
                self._show_rap_info_dialog(
                    entry,
                    "RAP Error",
                    f"Could not construct RAP download URL for \"{entry.name}\".\n\n"
                    f"Content ID: {entry.content_id}\n"
                    f"RAP: {rap_value}",
                    pkg_dest_path
                )
        else:
            
            self.update_status(f"Downloaded {entry.name}")
            GLib.timeout_add(2000, self._hide_progress)
    
    def _show_rap_info_dialog(self, entry, title, message, pkg_dest_path):
        dialog = Adw.AlertDialog()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.choose(self, None, self._on_rap_dialog_closed, entry)
        
        self.update_status(f"Downloaded {entry.name}")
        GLib.timeout_add(2000, self._hide_progress)
    
    def _on_rap_dialog_closed(self, dialog, result, entry):
        try:
            dialog.choose_finish(result)
        except:
            pass
    
    def _start_rap_download(self, entry, pkg_dest_path, rap_url):
        
        pkg_dir = os.path.dirname(pkg_dest_path)
        rap_filename = f"{entry.content_id}.rap"
        rap_dest_path = os.path.join(pkg_dir, rap_filename)
        
        self.update_status(f"Downloading RAP: {entry.name}")
        self.download_progress.set_fraction(0.0)
        self.download_info_label.set_label("Downloading RAP...")
        
        
        session = Soup.Session()
        message = Soup.Message.new("GET", rap_url)
        
        if message is None:
            self._show_rap_info_dialog(
                entry,
                "RAP Download Error",
                f"Invalid RAP URL for \"{entry.name}\".",
                pkg_dest_path
            )
            return
        
        
        download_id = f"{entry.content_id or entry.title_id}_rap"
        self.active_downloads[download_id] = {
            "entry": entry,
            "dest_path": rap_dest_path,
            "session": session,
            "total_size": 0,  
            "downloaded": 0,
            "file": None,
            "cancellable": Gio.Cancellable(),
            "type": "rap",
            "pkg_dest_path": pkg_dest_path
        }
        
        
        session.send_async(
            message,
            GLib.PRIORITY_DEFAULT,
            self.active_downloads[download_id]["cancellable"],
            self._on_send_complete,
            download_id,
            message
        )
    
    def _download_cleanup(self, download_id):
        if download_id not in self.active_downloads:
            return
        
        download_info = self.active_downloads[download_id]
        entry = download_info["entry"]
        
        
        if download_info.get("file"):
            download_info["file"].close()
        
        
        if download_info.get("input_stream"):
            try:
                download_info["input_stream"].close(None)
            except:
                pass
        
        self.update_status(f"Download failed: {entry.name}")
        
        
        del self.active_downloads[download_id]
        
        self._hide_progress()
    
    def _hide_progress(self):
        self.download_progress.set_visible(False)
        self.download_info_label.set_visible(False)
        return False  
    
    def _create_name_cell(self, factory, list_item):
        label = list_item.get_child()
        item = list_item.get_item()
        if item:
            label.set_label(item.entry.name)
            label.set_tooltip_text(item.entry.name)
    
    def _create_title_id_cell(self, factory, list_item):
        label = list_item.get_child()
        item = list_item.get_item()
        if item:
            label.set_label(item.entry.title_id)
    
    def _create_region_cell(self, factory, list_item):
        label = list_item.get_child()
        item = list_item.get_item()
        if item:
            label.set_label(item.entry.region)
    
    def _create_platform_cell(self, factory, list_item):
        label = list_item.get_child()
        item = list_item.get_item()
        if item:
            label.set_label(item.entry.platform)
    
    def _create_category_cell(self, factory, list_item):
        label = list_item.get_child()
        item = list_item.get_item()
        if item:
            label.set_label(item.entry.category.capitalize())
    
    def _create_size_cell(self, factory, list_item):
        label = list_item.get_child()
        item = list_item.get_item()
        if item:
            label.set_label(item.entry.get_file_size_formatted())
    
    def _populate_filters(self):
        
        self.category_model.splice(0, self.category_model.get_n_items(), [])
        self.category_model.append("All Types")
        for category_key, category_info in Config.TSV_STRUCTURE.items():
            self.category_model.append(category_info["label"])
        
        
        self._update_platform_filter()
        
        
        self._update_region_filter()
    
    def _update_platform_filter(self):
        self.platform_model.splice(0, self.platform_model.get_n_items(), [])
        self.platform_model.append("All Consoles")
        
        
        platforms = ["PS3", "PSV", "PSP", "PSM", "PSX"]
        for platform in platforms:
            self.platform_model.append(platform)
    
    def _update_region_filter(self):
        self.region_model.splice(0, self.region_model.get_n_items(), [])
        self.region_model.append("All Regions")
        
        
        regions = ["US", "EU", "JP", "ASIA", "HK"]
        for region in regions:
            self.region_model.append(region)
    
    def _on_filter_changed(self, dropdown, param):
        self._apply_filters()
    
    def _on_search_toggled(self, button):
        self.search_bar.set_search_mode(button.get_active())
        if button.get_active():
            self.search_entry.grab_focus()
    
    def _on_search_changed(self, entry):
        self._apply_filters()
    
    def _get_selected_category(self):
        selected = self.category_dropdown.get_selected()
        if selected == 0 or selected == Gtk.INVALID_LIST_POSITION:
            return "all"
        
        
        keys = list(Config.TSV_STRUCTURE.keys())
        if selected - 1 < len(keys):
            return keys[selected - 1]
        return "all"
    
    def _get_selected_platform(self):
        selected = self.platform_dropdown.get_selected()
        if selected == 0 or selected == Gtk.INVALID_LIST_POSITION:
            return "all"
        
        platforms = ["PS3", "PSV", "PSP", "PSM", "PSX"]
        if selected - 1 < len(platforms):
            return platforms[selected - 1]
        return "all"
    
    def _get_selected_region(self):
        selected = self.region_dropdown.get_selected()
        if selected == 0 or selected == Gtk.INVALID_LIST_POSITION:
            return "all"
        
        regions = ["US", "EU", "JP", "ASIA", "HK"]
        if selected - 1 < len(regions):
            return regions[selected - 1]
        return "all"
    
    def _apply_filters(self):
        category = self._get_selected_category()
        platform = self._get_selected_platform()
        region = self._get_selected_region()
        search_text = self.search_entry.get_text()
        
        entries = self.tsv_parser.get_entries(category, platform, search_text, region)
        
        
        self.list_store.remove_all()
        for entry in entries:
            self.list_store.append(EntryObject(entry))
        
        
        self.results_label.set_label(f"{len(entries)} items")
    
    def load_data(self):
        self.update_status("Loading data...")
        
        
        GLib.idle_add(self._load_data_async)
    
    def _load_data_async(self):
        self.tsv_parser.load_all()
        self._apply_filters()
        
        total = len(self.tsv_parser.entries)
        if total > 0:
            self.update_status(f"Loaded {total} entries from cache")
        else:
            self.update_status("No data loaded. Configure TSV sources in the menu.")
        
        
        self.main_stack.set_visible_child_name("content")
        
        return False  
    
    def show_toast(self, message):
        toast = Adw.Toast(title=message)
        self.toast_overlay.add_toast(toast)
    
    def update_status(self, message):
        self.status_label.set_label(message)
