from typing import List, Dict, Optional
import concurrent.futures
import requests
import trafilatura
from loguru import logger
from pydantic import BaseModel
from bs4 import BeautifulSoup

class PageContent(BaseModel):
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    error: Optional[str] = None

class Extractor:
    """
    负责从 URL 提取正文内容。
    使用 requests 下载 + trafilatura 提取。
    """
    
    def __init__(self, max_workers: int = 5, timeout: int = 10, user_agent: str = None):
        self.max_workers = max_workers
        self.timeout = timeout
        self.user_agent = user_agent or 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'

    def _fetch_single(self, url: str) -> PageContent:
        """
        抓取单个 URL 内容。
        """
        headers = {'User-Agent': self.user_agent}
        try:
            logger.debug(f"Fetching content: {url}")
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # 使用 trafilatura 提取
            html = response.text
            content = trafilatura.extract(html, include_comments=False, include_tables=True)
            
            # 尝试提取更多元数据
            metadata = trafilatura.bare_extraction(html)
            
            meta_dict = {}
            if metadata:
                # trafilatura 2.x 返回 Document 对象，需要转换或属性访问
                if hasattr(metadata, 'as_dict'):
                    meta_dict = metadata.as_dict()
                elif isinstance(metadata, dict):
                    meta_dict = metadata
                else:
                    # Fallback for unknown object type
                    if hasattr(metadata, 'title'):
                        meta_dict['title'] = metadata.title
                    if hasattr(metadata, 'text'):
                        meta_dict['text'] = metadata.text
            
            title = meta_dict.get('title')
            text = meta_dict.get('text') or content
            
            # Fallback for title extraction
            if not title:
                try:
                    soup = BeautifulSoup(html, 'lxml')
                    if soup.title and soup.title.string:
                        title = soup.title.string.strip()
                    if not title:
                        h1 = soup.find('h1')
                        if h1:
                            title = h1.get_text().strip()
                except Exception:
                    pass
            
            if not text:
                return PageContent(url=url, title=title, error="No content extracted")
                
            return PageContent(url=url, title=title, content=text)
            
        except Exception as e:
            logger.error(f"Error extracting {url}: {e}")
            return PageContent(url=url, error=str(e))

    def extract_batch(self, urls: List[str]) -> Dict[str, dict]:
        """
        批量抓取内容。
        Returns: Dict[url, PageContent.dict()]
        """
        logger.info(f"Starting extraction for {len(urls)} URLs with {self.max_workers} workers...")
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self._fetch_single, url): url for url in urls}
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    data = future.result()
                    results[url] = data.model_dump()
                    if data.error:
                        logger.warning(f"Failed to extract {url}: {data.error}")
                    else:
                        logger.success(f"Extracted {len(data.content)} chars from {url}")
                except Exception as e:
                    logger.error(f"Exception for {url}: {e}")
                    results[url] = {"url": url, "error": str(e)}
                    
        return results

# 单例
extractor = Extractor()
