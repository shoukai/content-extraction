import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any
from loguru import logger
import json
import os
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Discovery:
    def __init__(self):
        pass

    def extract_toc(self, url: str, output_dir: str) -> List[Dict[str, Any]]:
        """
        Extract Table of Contents from the homepage.
        Returns a list of sections, each containing a title and children links.
        """
        logger.info(f"Discovering TOC from {url}...")
        try:
            # Verify=False to handle potential SSL issues in some envs
            response = requests.get(url, verify=False, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Strategy: Find ULs that look like navigation menus
            candidate_uls = []
            for ul in soup.find_all('ul'):
                links = ul.find_all('a')
                if len(links) >= 3: # Min 3 links to be considered a menu section
                    candidate_uls.append(ul)
            
            base_domain = urlparse(url).netloc
            valid_uls = []
            
            # Filter for internal links
            for ul in candidate_uls:
                internal_links = 0
                links = ul.find_all('a')
                for a in links:
                    href = a.get('href', '')
                    if href.startswith('/') or base_domain in href:
                        internal_links += 1
                
                # If mostly internal, keep it
                if links and (internal_links / len(links)) > 0.5:
                    valid_uls.append(ul)
            
            logger.info(f"Found {len(valid_uls)} navigation lists.")
            
            full_structure = []
            
            # Process each UL
            for i, ul in enumerate(valid_uls):
                # Try to find a section title
                # 1. Previous sibling header
                section_title = f"Section {i+1}"
                
                # Walk back siblings to find a header-like element
                curr = ul
                for _ in range(5): # Look back 5 siblings max
                    prev = curr.find_previous_sibling()
                    if not prev:
                        break
                    
                    # If it's a header
                    if prev.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                        section_title = prev.get_text(strip=True)
                        break
                    # If it's a paragraph or div with text, might be a label
                    if prev.name in ['p', 'div', 'span'] and len(prev.get_text(strip=True)) < 50:
                         # Heuristic: Short text likely a label
                         section_title = prev.get_text(strip=True)
                         break
                    curr = prev
                
                # Extract items (links)
                items = []
                for li in ul.find_all('li'): # Use recursive=True to get nested items too? 
                    # For now, just flat list of links in this UL
                    # Or preserve hierarchy if needed.
                    # Simple approach: find all 'a' in this UL
                    for a in li.find_all('a', recursive=False): # Only direct children?
                        title = a.get_text(strip=True)
                        href = urljoin(url, a.get('href'))
                        if title and href:
                            items.append({"title": title, "url": href})
                            
                    # If LI has no direct A but has nested UL, we might handle recursion later.
                    # But find_all('a') on UL gives all links.
                    # Let's iterate LI to be safer about structure.
                
                # If recursive=False failed (no direct A), try all A in UL
                if not items:
                     for a in ul.find_all('a'):
                        title = a.get_text(strip=True)
                        href = urljoin(url, a.get('href'))
                        if title and href:
                            items.append({"title": title, "url": href})

                if items:
                    # Deduplicate items
                    unique_items = []
                    seen = set()
                    for item in items:
                        if item['url'] not in seen:
                            unique_items.append(item)
                            seen.add(item['url'])
                    
                    full_structure.append({
                        "title": section_title,
                        "children": unique_items
                    })
            
            # Save raw TOC
            raw_path = os.path.join(output_dir, "toc_raw.json")
            os.makedirs(output_dir, exist_ok=True)
            with open(raw_path, 'w', encoding='utf-8') as f:
                json.dump(full_structure, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved raw TOC to {raw_path}")
            return full_structure
            
        except Exception as e:
            logger.error(f"Failed to extract TOC: {e}")
            return []

discovery = Discovery()
