import argparse
import sys
import uuid
import os
import json
from loguru import logger
from src.graph.workflow import create_graph
from src.utils.config import settings
from src.core.discovery import discovery

def main():
    parser = argparse.ArgumentParser(description="内容提取智能代理")
    parser.add_argument("--project", type=str, required=True, help="项目名称 (如 langgraph)")
    parser.add_argument("--home", type=str, help="项目文档首页 URL (用于提取目录结构)")
    parser.add_argument("--prefix", type=str, help="URL 前缀过滤 (可选)")
    parser.add_argument("--filter", type=str, help="页面过滤关键词或 URL (用于测试)")
    parser.add_argument("--generate", action="store_true", help="仅运行生成阶段")
    parser.add_argument("--visualize", action="store_true", help="为现有文档生成图表 (Mermaid/AntV)")
    
    args = parser.parse_args()
    project_name = args.project
    
    # Paths
    output_dir = os.path.join(os.getcwd(), "outputs", project_name)
    fragments_dir = os.path.join(output_dir, "fragments")
    toc_path = os.path.join(output_dir, "toc_raw.json")
    
    # 检查配置
    if not settings.llm.api_key:
        logger.error("LLM API Key not found. Please set LLM_API_KEY env var.")
        sys.exit(1)

    if args.visualize:
        from src.core.visualizer import Visualizer
        visualizer = Visualizer()
        input_file = os.path.join(output_dir, "structured.md")
        output_file = os.path.join(output_dir, "structured_with_diagrams.md")
        visualizer.process_document(input_file, output_file)
        return
        
    if args.generate:
        from src.core.structure_generator import generate_book
        
        output_file = os.path.join(output_dir, "structured.md")
        
        logger.info(f"Generating book for project: {project_name}")
        logger.info(f"Reading fragments from: {fragments_dir}")
        
        generate_book(project_name, fragments_dir, output_file)
        return

    # Phase 1: Discovery (Agent Flow)
    toc_structure = []
    
    # If home URL is provided, discover fresh TOC
    if args.home:
        logger.info(f"Starting Discovery Phase for {project_name} from {args.home}...")
        toc_structure = discovery.extract_toc(args.home, output_dir)
        if not toc_structure:
            logger.error("Discovery failed. Exiting.")
            sys.exit(1)
    
    # If no home URL, try to load existing TOC
    elif os.path.exists(toc_path):
        logger.info(f"Loading existing TOC from {toc_path}...")
        with open(toc_path, 'r', encoding='utf-8') as f:
            toc_structure = json.load(f)
    else:
        logger.error("No --home provided and no existing TOC found at {toc_path}.")
        logger.error("Please provide --home to initialize the project structure.")
        sys.exit(1)
        
    # Flatten candidates from TOC
    candidates = []
    seen_urls = set()
    
    def extract_urls(nodes):
        for node in nodes:
            if "url" in node and node["url"]:
                u = node["url"]
                if u not in seen_urls:
                    # Filter by prefix if provided
                    if args.prefix and not u.startswith(args.prefix):
                        pass
                    else:
                        candidates.append(u)
                        seen_urls.add(u)
            
            if "children" in node:
                extract_urls(node["children"])
                
    extract_urls(toc_structure)
    
    if not candidates:
        logger.warning("No candidate URLs found in TOC.")
        sys.exit(0)
    
    # Filter for testing
    if args.filter:
        logger.info(f"Applying filter: {args.filter}")
        original_count = len(candidates)
        candidates = [u for u in candidates if args.filter in u]
        logger.info(f"Filtered {original_count} -> {len(candidates)} URLs")
        if not candidates:
            logger.error("No URLs matched the filter.")
            sys.exit(0)
    
    # User Selection / Confirmation
    print(f"\n=== Project: {project_name} ===")
    print(f"Total Candidates: {len(candidates)}")
    print("Candidate List:")
    # Print all candidates if reasonable, or paginate? 
    # For selection, printing all (or at least providing a way to see them) is better.
    # Let's print first 20, then ask if they want to see more? 
    # Or just print all if < 50.
    limit_preview = 50
    for i, url in enumerate(candidates):
        if i >= limit_preview:
            print(f"... and {len(candidates)-limit_preview} more.")
            break
        print(f"{i+1}. {url}")
    print("======================================\n")
    
    selected_indices = []
    while True:
        choice = input("Enter selection (e.g. 'all', '1-5', '1,3', 'q' to quit): ").strip().lower()
        
        if choice == 'q':
            logger.info("Aborted by user.")
            sys.exit(0)
            
        elif choice in ['all', '']:
             selected_indices = range(len(candidates))
             break
             
        else:
             try:
                 parts = choice.split(',')
                 indices = set()
                 for part in parts:
                     part = part.strip()
                     if not part: continue
                     
                     if '-' in part:
                         s_str, e_str = part.split('-')
                         start = int(s_str)
                         end = int(e_str)
                         # Support 1-based index input
                         indices.update(range(start-1, end))
                     else:
                         indices.add(int(part) - 1)
                 
                 valid_indices = [i for i in indices if 0 <= i < len(candidates)]
                 if not valid_indices:
                     print("No valid items selected.")
                     continue
                     
                 selected_indices = sorted(list(valid_indices))
                 print(f"You selected {len(selected_indices)} URLs.")
                 confirm = input("Confirm selection? (y/n): ").strip().lower()
                 if confirm in ['y', 'yes']:
                     break
             except ValueError:
                 print("Invalid format. Please use numbers (e.g. 1,3) or ranges (e.g. 1-5).")

    # Filter candidates
    candidates = [candidates[i] for i in selected_indices]
    logger.info(f"Proceeding with {len(candidates)} URLs...")

    # Phase 2: Extraction (Graph)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    app = create_graph()
    
    initial_state = {
        "project_name": project_name,
        "home_url": args.home or "",
        "target_url_prefix": args.prefix or "",
        "sitemap_url": "", # Deprecated
        "toc_structure": toc_structure,
        "candidate_urls": candidates,
        "approved_urls": [], # Will be handled by graph logic if needed, but we essentially pre-approved here
        "results": {},
        "fragment_files": [],
        "current_step": "start",
        "error": None
    }
    
    logger.info(f"Starting Extraction Graph (Thread: {thread_id})...")
    
    try:
        # 1. Start Graph (Runs 'scan' node)
        # Since we provided candidate_urls, scan_node will just pass them through
        for event in app.stream(initial_state, config=config):
            if "scan" in event:
                logger.info("Scan node completed.")
                
        # 2. Check state (Paused after scan)
        snapshot = app.get_state(config)
        if not snapshot.next:
            logger.warning("Graph finished unexpectedly.")
            sys.exit(0)
            
        # 3. Approve URLs (We already confirmed them in main.py)
        candidates = snapshot.values.get("candidate_urls", [])
        if not candidates:
            logger.warning("No candidates found in graph state.")
            sys.exit(0)
            
        logger.info(f"Auto-approving {len(candidates)} URLs (already confirmed).")
        app.update_state(config, {"approved_urls": candidates})
        
        # 4. Resume Graph (Runs 'extract' node)
        logger.info("Resuming graph for extraction...")
        for event in app.stream(None, config=config):
            if "extract" in event:
                logger.info("Extraction completed.")
                res = event["extract"]
                if "results" in res:
                     logger.success(f"Extracted {len(res['results'])} pages.")
            
    except Exception as e:
        logger.error(f"Extraction Phase encountered an error: {e}")
        logger.warning("Proceeding to Generation Phase with available fragments...")

    # Phase 3: Generation (Always run after extraction)
    logger.info("\n=== Starting Phase 3: Generation ===")
    from src.core.structure_generator import generate_book
    
    output_file = os.path.join(output_dir, "structured.md")
    logger.info(f"Generating structured document for {project_name}...")
    
    try:
        generate_book(project_name, fragments_dir, output_file)
        logger.success(f"Full process complete! Document available at: {output_file}")
    except Exception as e:
        logger.error(f"Generation failed: {e}")

if __name__ == "__main__":
    main()
