import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from config import Config
from tsv_downloader import TsvDownloader


class ConfigureSourcesDialog(Adw.Dialog):
    
    def __init__(self, config, on_complete):
        super().__init__()
        self.config = config
        self.on_complete = on_complete
        self.entries = {}  
        self.downloader = TsvDownloader(config)
        self.is_downloading = False
        
        self.set_title("Configure Sources")
        self.set_content_width(550)
        self.set_content_height(650)
        
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        
        self.save_button = Gtk.Button(label="Save")
        self.save_button.add_css_class("suggested-action")
        self.save_button.connect("clicked", self._on_save_clicked)
        header.pack_end(self.save_button)
        
        main_box.append(header)
        
        
        overlay = Gtk.Overlay()
        overlay.set_vexpand(True)
        
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        
        for category_key, category_info in Config.TSV_STRUCTURE.items():
            group = self._create_tsv_group(category_key, category_info)
            content.append(group)
        
        
        download_group = self._create_download_group()
        content.append(download_group)
        
        
        refetch_group = self._create_refetch_group()
        content.append(refetch_group)
        
        scrolled.set_child(content)
        overlay.set_child(scrolled)
        
        
        self.progress_box = self._create_progress_overlay()
        self.progress_box.set_visible(False)
        overlay.add_overlay(self.progress_box)
        
        main_box.append(overlay)
        self.set_child(main_box)
    
    def _create_progress_overlay(self):
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_size_request(300, -1)
        box.add_css_class("card")
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        
        inner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        inner_box.set_margin_start(24)
        inner_box.set_margin_end(24)
        inner_box.set_margin_top(24)
        inner_box.set_margin_bottom(24)
        
        
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32)
        self.spinner.set_halign(Gtk.Align.CENTER)
        inner_box.append(self.spinner)
        
        
        self.progress_label = Gtk.Label(label="Downloading...")
        self.progress_label.set_halign(Gtk.Align.CENTER)
        inner_box.append(self.progress_label)
        
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_hexpand(True)
        inner_box.append(self.progress_bar)
        
        box.append(inner_box)
        return box
    
    def _create_tsv_group(self, category_key, category_info):
        group = Adw.PreferencesGroup()
        group.set_title(category_info["label"])
        group.set_description(f"TSV URLs for {category_info['label']}")
        
        existing_urls = self.config.get_all_tsv_urls().get(category_key, {})
        
        for platform in category_info["options"]:
            row = Adw.EntryRow()
            row.set_title(f"{platform} TSV")
            
            
            existing_url = existing_urls.get(platform, "")
            if existing_url:
                row.set_text(existing_url)
            
            
            self.entries[(category_key, platform)] = row
            group.add(row)
        
        return group
    
    def _create_download_group(self):
        group = Adw.PreferencesGroup()
        group.set_title("Downloads")
        group.set_description("Where to save downloaded files")
        
        row = Adw.ActionRow()
        row.set_title("Download Directory")
        
        current_dir = self.config.get_download_directory() or ""
        self.download_dir_label = Gtk.Label(label=current_dir)
        self.download_dir_label.set_ellipsize(3)  
        self.download_dir_label.add_css_class("dim-label")
        self.download_dir_label.set_max_width_chars(30)
        row.add_suffix(self.download_dir_label)
        
        browse_button = Gtk.Button(icon_name="folder-open-symbolic")
        browse_button.set_valign(Gtk.Align.CENTER)
        browse_button.add_css_class("flat")
        browse_button.connect("clicked", self._on_browse_clicked)
        row.add_suffix(browse_button)
        row.set_activatable_widget(browse_button)
        
        group.add(row)
        return group
    
    def _create_refetch_group(self):
        group = Adw.PreferencesGroup()
        group.set_title("TSV Cache")
        group.set_description("Download and cache TSV files locally")
        
        
        refetch_row = Adw.ActionRow()
        refetch_row.set_title("Re-fetch TSV Files")
        refetch_row.set_subtitle("Download fresh copies of all TSV files")
        
        self.refetch_button = Gtk.Button(label="Fetch Now")
        self.refetch_button.set_valign(Gtk.Align.CENTER)
        self.refetch_button.add_css_class("suggested-action")
        self.refetch_button.connect("clicked", self._on_refetch_clicked)
        refetch_row.add_suffix(self.refetch_button)
        refetch_row.set_activatable_widget(self.refetch_button)
        
        group.add(refetch_row)
        return group
    
    def _on_browse_clicked(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Download Directory")
        
        
        current_dir = self.config.get_download_directory()
        if current_dir:
            initial_folder = Gio.File.new_for_path(current_dir)
            dialog.set_initial_folder(initial_folder)
        
        dialog.select_folder(self.get_root(), None, self._on_folder_selected)
    
    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self.download_dir_label.set_label(path)
        except Exception:
            pass  
    
    def _save_config(self):
        
        tsv_urls = {}
        for (category_key, platform), entry in self.entries.items():
            url = entry.get_text().strip()
            if url:
                if category_key not in tsv_urls:
                    tsv_urls[category_key] = {}
                tsv_urls[category_key][platform] = url
        
        
        self.config.set_all_tsv_urls(tsv_urls)
        
        
        download_dir = self.download_dir_label.get_label()
        if download_dir:
            self.config.set_download_directory(download_dir)
    
    def _on_save_clicked(self, button):
        self._save_config()
        self._start_download()
    
    def _on_refetch_clicked(self, button):
        self._save_config()
        self._start_download()
    
    def _start_download(self):
        if self.is_downloading:
            return
        
        self.is_downloading = True
        self._set_ui_downloading(True)
        
        self.downloader.download_all(
            on_progress=self._on_download_progress,
            on_file_complete=self._on_file_complete,
            on_all_complete=self._on_all_downloads_complete,
            on_error=self._on_download_error
        )
    
    def _set_ui_downloading(self, downloading):
        self.save_button.set_sensitive(not downloading)
        self.refetch_button.set_sensitive(not downloading)
        self.progress_box.set_visible(downloading)
        self.spinner.set_spinning(downloading)
        
        
        for entry in self.entries.values():
            entry.set_sensitive(not downloading)
        
        if downloading:
            self.refetch_button.set_label("Downloading...")
            self.progress_bar.set_fraction(0.0)
        else:
            self.refetch_button.set_label("Fetch Now")
    
    def _on_download_progress(self, current_file, file_index, total_files, bytes_downloaded, total_bytes):
        self.progress_label.set_label(f"Downloading {current_file}\n({file_index}/{total_files})")
        
        
        if total_files > 0:
            file_progress = (file_index - 1) / total_files
            if total_bytes > 0:
                file_progress += (bytes_downloaded / total_bytes) / total_files
            self.progress_bar.set_fraction(min(file_progress, 1.0))
    
    def _on_file_complete(self, category, platform, local_path):
        pass  
    
    def _on_all_downloads_complete(self):
        self.is_downloading = False
        self._set_ui_downloading(False)
        self.progress_bar.set_fraction(1.0)
        
        self.close()
        self.on_complete()
    
    def _on_download_error(self, category, platform, error_message):
        self.progress_label.set_label(f"Error: {category}/{platform}\n{error_message}")
