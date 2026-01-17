from src.core.scanner import scanner
from loguru import logger
import sys

def test_scanner_module():
    url = "https://docs.langchain.com/sitemap.xml"
    prefix = "https://docs.langchain.com/oss/python/langchain"
    
    logger.info("Testing Scanner module...")
    urls = scanner.scan(url, prefix)
    
    if not urls:
        logger.error("Scanner failed to find URLs.")
        sys.exit(1)
        
    logger.success(f"Scanner successfully found {len(urls)} URLs matching prefix.")
    for u in urls[:5]:
        print(f"Sample: {u}")

if __name__ == "__main__":
    test_scanner_module()
