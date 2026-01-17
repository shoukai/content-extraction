from trafilatura.sitemaps import sitemap_search
from loguru import logger
import sys

def test_sitemap():
    url = "https://docs.langchain.com/sitemap.xml"
    logger.info(f"Fetching sitemap from {url}...")
    
    # trafilatura.sitemaps.sitemap_search 自动处理嵌套 sitemap 和 URL 提取
    urls = sitemap_search(url)
    
    if not urls:
        logger.error("No URLs found!")
        return
        
    logger.info(f"Found {len(urls)} URLs.")
    
    # 打印前 10 个看看结构
    for i, u in enumerate(urls[:10]):
        print(f"{i+1}: {u}")
        
    # 测试前缀过滤
    prefix = "https://docs.langchain.com/oss/python/langchain"
    filtered = [u for u in urls if u.startswith(prefix)]
    logger.info(f"Filtered {len(filtered)} URLs starting with '{prefix}'")

if __name__ == "__main__":
    test_sitemap()
