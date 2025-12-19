import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Soup", "3.0")
from gi.repository import GLib, Gio, Soup


class TsvDownloader:
    
    def __init__(self, config):
        self.config = config
        self.session = Soup.Session()
        self.cancel = None
    
    def download_all(self, on_progress, on_file_complete, on_all_complete, on_error):
        self.config.ensure_tsv_cache_dir()
        self.cancel = Gio.Cancellable()
        
        
        downloads = []
        tsv_urls = self.config.get_all_tsv_urls()
        for category_key, platforms in tsv_urls.items():
            for platform, url in platforms.items():
                if url and url.strip():
                    local_path = self.config.get_tsv_cache_path(category_key, platform)
                    downloads.append({
                        "category": category_key,
                        "platform": platform,
                        "url": url.strip(),
                        "local_path": local_path
                    })
        
        if not downloads:
            on_all_complete()
            return
        
        
        self._download_next(downloads, 0, on_progress, on_file_complete, on_all_complete, on_error)
    
    def _download_next(self, downloads, index, on_progress, on_file_complete, on_all_complete, on_error):
        if self.cancel.is_cancelled():
            return
        
        if index >= len(downloads):
            on_all_complete()
            return
        
        download = downloads[index]
        total_files = len(downloads)
        
        
        message = Soup.Message.new("GET", download["url"])
        if message is None:
            on_error(download["category"], download["platform"], f"Invalid URL: {download['url']}")
            self._download_next(downloads, index + 1, on_progress, on_file_complete, on_all_complete, on_error)
            return
        
        
        on_progress(f"{download['category']}/{download['platform']}", index + 1, total_files, 0, 0)
        
        
        self.session.send_and_read_async(
            message,
            GLib.PRIORITY_DEFAULT,
            self.cancel,
            lambda session, result: self._on_download_complete(
                session, result, message, download, downloads, index,
                on_progress, on_file_complete, on_all_complete, on_error
            )
        )
    
    def _on_download_complete(self, session, result, message, download, downloads, index,
                               on_progress, on_file_complete, on_all_complete, on_error):
        try:
            bytes_data = session.send_and_read_finish(result)
            
            if message.get_status() != Soup.Status.OK:
                on_error(download["category"], download["platform"], 
                        f"HTTP {message.get_status()}: {message.get_reason_phrase()}")
            else:
                
                data = bytes_data.get_data()
                with open(download["local_path"], "wb") as f:
                    f.write(data)
                
                on_progress(f"{download['category']}/{download['platform']}", 
                           index + 1, len(downloads), len(data), len(data))
                on_file_complete(download["category"], download["platform"], download["local_path"])
        
        except Exception as e:
            on_error(download["category"], download["platform"], str(e))
        
        
        self._download_next(downloads, index + 1, on_progress, on_file_complete, on_all_complete, on_error)
    
    def cancel_downloads(self):
        if self.cancel:
            self.cancel.cancel()
