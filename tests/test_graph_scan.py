from src.graph.workflow import create_graph
from loguru import logger
import sys

def test_graph_scan():
    logger.info("Initializing Graph...")
    app = create_graph()
    
    initial_state = {
        "sitemap_url": "https://docs.langchain.com/sitemap.xml",
        "target_url_prefix": "https://docs.langchain.com/oss/python/langchain",
        "candidate_urls": [],
        "approved_urls": [],
        "results": {},
        "current_step": "start",
        "error": None
    }
    
    # 每次使用新 ID 避免干扰
    config = {"configurable": {"thread_id": "test_thread_3"}}
    
    logger.info("Starting Graph execution (Phase 1: Scan)...")
    for event in app.stream(initial_state, config=config):
        if "scan" in event:
            logger.info(f"Scan found {len(event['scan']['candidate_urls'])} URLs")
            
    # Check interrupt
    state_snapshot = app.get_state(config)
    if not state_snapshot.next:
        logger.error("Graph finished unexpectedly!")
        return
        
    logger.info("Graph interrupted. Simulating user review...")
    
    candidates = state_snapshot.values.get("candidate_urls", [])
    if not candidates:
        logger.error("No candidates found!")
        return
        
    # 尝试批准前 3 个 URL
    approved = candidates[:3]
        
    logger.info(f"Approving {len(approved)} URLs: {approved}")
    
    app.update_state(config, {"approved_urls": approved})
    logger.info("State updated.")
    
    logger.info("Resuming Graph execution (Phase 2: Extract)...")
    
    for event in app.stream(None, config=config):
        if "extract" in event:
            logger.success(f"Extraction complete for {len(event['extract']['results'])} pages.")
            
    logger.success("Workflow completed (Fragments generated).")

if __name__ == "__main__":
    test_graph_scan()
