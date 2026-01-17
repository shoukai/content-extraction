import requests
from bs4 import BeautifulSoup
from loguru import logger

def fetch_sitemap_urls(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'xml')
        urls = []
        
        # Check for sitemapindex
        sitemaps = soup.find_all('sitemap')
        if sitemaps:
            logger.info(f"Found sitemap index with {len(sitemaps)} sitemaps.")
            for sm in sitemaps:
                loc = sm.find('loc')
                if loc:
                    logger.info(f"Following sitemap: {loc.text}")
                    urls.extend(fetch_sitemap_urls(loc.text))
        else:
            # Standard sitemap
            locs = soup.find_all('loc')
            for loc in locs:
                urls.append(loc.text)
                
        return urls
        
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return []

def test():
    url = "https://docs.langchain.com/sitemap.xml"
    logger.info(f"Testing manual fetch from {url}")
    urls = fetch_sitemap_urls(url)
    logger.info(f"Found {len(urls)} URLs")
    
    prefix = "https://docs.langchain.com/oss/python/langchain"
    filtered = [u for u in urls if u.startswith(prefix)]
    logger.info(f"Filtered {len(filtered)} URLs")

if __name__ == "__main__":
    test()
