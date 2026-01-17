import argparse
import sys
import uuid
from loguru import logger
from src.graph.workflow import create_graph
from src.utils.config import settings

def main():
    parser = argparse.ArgumentParser(description="内容提取智能代理")
    parser.add_argument("--sitemap", type=str, default="https://docs.langchain.com/sitemap.xml", help="Sitemap URL 地址")
    parser.add_argument("--prefix", type=str, default="https://docs.langchain.com/oss/python/langchain", help="需要过滤的 URL 前缀")
    parser.add_argument("--auto-approve", action="store_true", help="自动批准所有筛选出的 URL（慎用）")
    parser.add_argument("--generate", action="store_true", help="仅运行第二阶段：生成结构化文档")
    
    args = parser.parse_args()
    
    # 检查配置
    if not settings.llm.api_key:
        logger.error("LLM API Key not found. Please set LLM_API_KEY env var.")
        sys.exit(1)
        
    if args.generate:
        from src.core.structure_generator import generate_book
        import os
        
        # Define paths
        fragments_dir = os.path.join(os.getcwd(), "outputs/fragments")
        output_file = os.path.join(os.getcwd(), "outputs/structured.md")
        
        generate_book(fragments_dir, output_file)
        return

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    app = create_graph()
    
    initial_state = {
        "sitemap_url": args.sitemap,
        "target_url_prefix": args.prefix,
        "candidate_urls": [],
        "approved_urls": [],
        "results": {},
        "fragment_files": [],
        "current_step": "start",
        "error": None
    }
    
    logger.info(f"Starting Scan Phase (Thread ID: {thread_id})...")
    
    # 运行第一阶段：Scan
    try:
        for event in app.stream(initial_state, config=config):
            if "scan" in event:
                count = len(event['scan']['candidate_urls'])
                logger.info(f"Found {count} candidate URLs.")
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        sys.exit(1)
        
    # 检查中断状态
    state_snapshot = app.get_state(config)
    if not state_snapshot.next:
        logger.info("Workflow finished without interruption (unexpected for this graph).")
        return

    # 获取候选列表
    candidates = state_snapshot.values.get("candidate_urls", [])
    if not candidates:
        logger.warning("No URLs found matching the prefix.")
        return
        
    logger.info(f"Review required for {len(candidates)} URLs.")
    
    # 用户交互环节
    if args.auto_approve:
        approved = candidates
        logger.info(f"Auto-approving all {len(approved)} URLs.")
    else:
        print("\n=== Candidate URLs ===")
        for i, url in enumerate(candidates):
            print(f"{i+1}. {url}")
        print("======================\n")
        
        print("Enter indices to approve (comma-separated, e.g. '1,3,5'), 'all' for all, or 'q' to quit:")
        user_input = input("> ").strip().lower()
        
        if user_input == 'q':
            logger.info("Operation cancelled by user.")
            return
        elif user_input == 'all':
            approved = candidates
        else:
            try:
                indices = [int(x.strip()) - 1 for x in user_input.split(',') if x.strip()]
                approved = [candidates[i] for i in indices if 0 <= i < len(candidates)]
            except (ValueError, IndexError):
                logger.error("Invalid input.")
                return
                
    if not approved:
        logger.warning("No URLs approved.")
        return
        
    logger.info(f"Approved {len(approved)} URLs. Resuming extraction...")
    
    # 更新状态并恢复执行
    app.update_state(config, {"approved_urls": approved})
    
    for event in app.stream(None, config=config):
        if "extract" in event:
            logger.success(f"Extraction complete for {len(event['extract']['results'])} URLs.")
            
    logger.info("Fragment generation complete. Please run 'python main.py --generate' to generate the structured document.")

if __name__ == "__main__":
    main()
