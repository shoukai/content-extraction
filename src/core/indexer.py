import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class FragmentIndexer:
    def __init__(self, fragments_dir: str):
        self.fragments_dir = fragments_dir
        self.index: Dict[str, Dict[str, Any]] = {} # url -> {path, title, summary, ...}

    def build_index(self):
        logger.info(f"Building index from {self.fragments_dir}...")
        for filename in os.listdir(self.fragments_dir):
            if not filename.endswith(".json"):
                continue
            
            filepath = os.path.join(self.fragments_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    url = data.get("url")
                    if url:
                        # Normalize URL: remove trailing slash
                        url = url.rstrip("/")
                        self.index[url] = {
                            "path": filepath,
                            "title": data.get("title", "Unknown Title"),
                            "summary": data.get("summary", ""),
                            "page_type": data.get("page_type", "Other")
                        }
            except Exception as e:
                logger.warning(f"Failed to read fragment {filename}: {e}")
        logger.info(f"Indexed {len(self.index)} fragments.")
        return self.index

    def find_fragment(self, keyword_or_suffix: str) -> Dict[str, Any]:
        """Find a fragment by URL suffix or title keyword."""
        keyword_or_suffix = keyword_or_suffix.lower()
        
        # 1. Exact suffix match on URL
        for url, data in self.index.items():
            if url.endswith(keyword_or_suffix):
                return data
            
        # 2. Partial match on URL
        for url, data in self.index.items():
            if keyword_or_suffix in url:
                return data
                
        # 3. Partial match on Title
        for url, data in self.index.items():
            if keyword_or_suffix in data.get("title", "").lower():
                return data
                
        return None
