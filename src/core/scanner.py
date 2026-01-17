from typing import List, Set
import requests
from bs4 import BeautifulSoup
from loguru import logger

class Scanner:
    """
    负责扫描网站结构，识别目标 URL 列表。
    使用 requests + BeautifulSoup 手动解析以提供更好的控制。
    """
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        self.timeout = timeout
        self.user_agent = user_agent or 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})

    def _fetch_urls_recursive(self, url: str) -> Set[str]:
        """
        递归获取 sitemap 中的 URL。
        """
        urls = set()
        try:
            logger.debug(f"Fetching sitemap: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 使用 xml 解析器
            soup = BeautifulSoup(response.content, 'xml')
            
            # 1. 检查是否是 sitemap index (包含其他 sitemap)
            sitemaps = soup.find_all('sitemap')
            if sitemaps:
                logger.debug(f"Found sitemap index with {len(sitemaps)} sub-sitemaps at {url}")
                for sm in sitemaps:
                    loc = sm.find('loc')
                    if loc and loc.text:
                        # 递归抓取
                        urls.update(self._fetch_urls_recursive(loc.text.strip()))
            
            # 2. 检查是否是标准 sitemap (包含 url)
            # 注意：有些 sitemap index 也可能混有 url，虽然不规范，但最好都检查
            url_tags = soup.find_all('url') # 标准是 <url><loc>...</loc></url>
            for url_tag in url_tags:
                loc = url_tag.find('loc')
                if loc and loc.text:
                    urls.add(loc.text.strip())
            
            # 兼容性处理：直接查找 loc 标签（如果结构不标准）
            # 但要小心不要重复添加 sitemap index 的 loc
            # 上面的逻辑应该覆盖了大部分标准情况。
            
            return urls
            
        except Exception as e:
            logger.error(f"Error fetching sitemap {url}: {e}")
            return set()

    def scan(self, sitemap_url: str, prefix: str = "") -> List[str]:
        """
        扫描 sitemap 并根据前缀过滤 URL。

        Args:
            sitemap_url: 网站的 sitemap.xml 地址
            prefix: 用于过滤 URL 的前缀（可选）

        Returns:
            List[str]: 过滤后的 URL 列表（已排序）
        """
        logger.info(f"Scanning sitemap: {sitemap_url} with prefix: '{prefix}'")
        
        all_urls = self._fetch_urls_recursive(sitemap_url)
        
        if not all_urls:
            logger.warning(f"No URLs found in sitemap: {sitemap_url}")
            return []
            
        logger.info(f"Total unique URLs found: {len(all_urls)}")
        
        sorted_urls = sorted(list(all_urls))
        
        if prefix:
            filtered_urls = [u for u in sorted_urls if u.startswith(prefix)]
            logger.info(f"URLs after prefix filtering: {len(filtered_urls)}")
            return filtered_urls
        
        return sorted_urls

# 单例实例
scanner = Scanner()
