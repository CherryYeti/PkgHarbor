import os
import csv


class TsvEntry:
    
    def __init__(self, data, category, platform):
        self.title_id = data.get("Title ID", "")
        self.region = data.get("Region", "")
        self.name = data.get("Name", "")
        self.pkg_url = data.get("PKG direct link", "")
        self.rap = data.get("RAP", "")
        self.content_id = data.get("Content ID", "")
        self.last_modified = data.get("Last Modification Date", "")
        self.file_size = data.get("File Size", "")
        self.sha256 = data.get("SHA256", "")
        self.category = category  
        self.platform = platform  
    
    def has_download(self):
        return self.pkg_url and self.pkg_url.lower() not in ("missing", "")
    
    def get_file_size_formatted(self):
        try:
            size = int(self.file_size)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        except (ValueError, TypeError):
            return self.file_size or "Unknown"


class TsvParser:
    
    def __init__(self, config):
        self.config = config
        self.entries = []
    
    def load_all(self):
        self.entries = []
        
        for category_key, category_info in self.config.TSV_STRUCTURE.items():
            for platform in category_info["options"]:
                cache_path = self.config.get_tsv_cache_path(category_key, platform)
                if os.path.exists(cache_path):
                    self._load_file(cache_path, category_key, platform)
        
        return self.entries
    
    def _load_file(self, path, category, platform):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    entry = TsvEntry(row, category, platform)
                    self.entries.append(entry)
        except Exception as e:
            print(f"Error loading {path}: {e}")
    
    def get_entries(self, category_filter=None, platform_filter=None, search_text=None, region_filter=None):
        results = self.entries
        
        if category_filter and category_filter != "all":
            results = [e for e in results if e.category == category_filter]
        
        if platform_filter and platform_filter != "all":
            results = [e for e in results if e.platform == platform_filter]
        
        if region_filter and region_filter != "all":
            results = [e for e in results if e.region == region_filter]
        
        if search_text:
            search_lower = search_text.lower()
            results = [e for e in results if 
                      search_lower in e.name.lower() or 
                      search_lower in e.title_id.lower() or
                      search_lower in e.content_id.lower()]
        
        return results
    
    def get_available_platforms(self, category_filter=None):
        platforms = set()
        for entry in self.entries:
            if category_filter and category_filter != "all":
                if entry.category == category_filter:
                    platforms.add(entry.platform)
            else:
                platforms.add(entry.platform)
        return sorted(platforms)
    
    def get_available_categories(self):
        categories = set()
        for entry in self.entries:
            categories.add(entry.category)
        return sorted(categories)
    
    def get_available_regions(self):
        regions = set()
        for entry in self.entries:
            if entry.region:
                regions.add(entry.region)
        return sorted(regions)
