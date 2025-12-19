import os
import json
from gi.repository import GLib


class Config:
    
    
    TSV_STRUCTURE = {
        "games": {
            "label": "Games",
            "options": ["PSV", "PSP", "PSM", "PS3", "PSX"]
        },
        "dlcs": {
            "label": "DLCs",
            "options": ["PSV", "PSP", "PS3"]
        },
        "themes": {
            "label": "Themes",
            "options": ["PSV"]
        }
    }
    
    def __init__(self):
        
        config_dir = GLib.get_user_config_dir()
        self.app_config_dir = os.path.join(config_dir, "pkgharbor")
        self.tsv_cache_dir = os.path.join(self.app_config_dir, "tsv_cache")
        self.config_path = os.path.join(self.app_config_dir, "config.json")
        self.config = self._load()
    
    def _load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def get_tsv_url(self, category, platform):
        tsv_urls = self.config.get("tsv_urls", {})
        category_urls = tsv_urls.get(category, {})
        return category_urls.get(platform)
    
    def set_tsv_url(self, category, platform, url):
        if "tsv_urls" not in self.config:
            self.config["tsv_urls"] = {}
        if category not in self.config["tsv_urls"]:
            self.config["tsv_urls"][category] = {}
        self.config["tsv_urls"][category][platform] = url
        self.save()
    
    def get_all_tsv_urls(self):
        return self.config.get("tsv_urls", {})
    
    def set_all_tsv_urls(self, tsv_urls):
        self.config["tsv_urls"] = tsv_urls
        self.save()
    
    def has_any_tsv_urls(self):
        tsv_urls = self.config.get("tsv_urls", {})
        for category in tsv_urls.values():
            for url in category.values():
                if url and url.strip():
                    return True
        return False
    
    def get_download_directory(self):
        return self.config.get("download_directory", GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD))
    
    def set_download_directory(self, path):
        self.config["download_directory"] = path
        self.save()
    
    def get_tsv_cache_path(self, category, platform):
        return os.path.join(self.tsv_cache_dir, f"{category}_{platform}.tsv")
    
    def get_cached_tsv_files(self):
        cached = []
        for category_key, category_info in self.TSV_STRUCTURE.items():
            for platform in category_info["options"]:
                cache_path = self.get_tsv_cache_path(category_key, platform)
                if os.path.exists(cache_path):
                    cached.append((category_key, platform, cache_path))
        return cached
    
    def ensure_tsv_cache_dir(self):
        os.makedirs(self.tsv_cache_dir, exist_ok=True)
