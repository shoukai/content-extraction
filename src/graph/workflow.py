import os
from src.core.extractor import extractor
from src.core.generator import generator
from loguru import logger
from langgraph.graph import StateGraph, END
from src.graph.state import AgentState
from src.core.scanner import scanner
from langgraph.checkpoint.memory import MemorySaver

def scan_node(state: AgentState):
    """
    执行扫描任务
    """
    logger.info("Executing scan_node...")
    sitemap = state.get("sitemap_url")
    prefix = state.get("target_url_prefix", "")
    
    if not sitemap:
        return {"error": "Missing sitemap_url"}
        
    urls = scanner.scan(sitemap, prefix)
    return {"candidate_urls": urls, "current_step": "review_pending"}

def extract_node(state: AgentState):
    """
    执行内容提取与初步分析
    """
    logger.info("Executing extract_node...")
    approved_urls = state.get("approved_urls", [])
    prefix = state.get("target_url_prefix", "")
    
    if not approved_urls:
        logger.warning("No approved_urls found, skipping extraction.")
        return {"error": "No approved URLs provided"}
        
    results = extractor.extract_batch(approved_urls)
    
    output_dir = "outputs/fragments"
    os.makedirs(output_dir, exist_ok=True)
    
    fragment_files = []
    
    if not generator:
        logger.error("Generator instance is None!")
        return {"error": "Generator not initialized"}

    # 遍历结果，进行分析并保存
    for url, data in results.items():
        # 只有当 error 存在且不为 None 时才跳过
        if data.get("error"):
            logger.warning(f"Skipping {url} due to extraction error: {data['error']}")
            continue
            
        title = data.get("title") or "Unknown Title"
        content = data.get("content") or ""
        
        if not content:
            logger.warning(f"Skipping {url} due to empty content")
            continue
            
        logger.info(f"Analyzing content for {url}...")
        analysis = generator.analyze_page(title, content)
        if analysis:
            filepath = generator.save_analysis(analysis, url, output_dir, url_prefix=prefix)
            fragment_files.append(filepath)
            logger.success(f"Analysis saved to {filepath}")
        else:
            logger.warning(f"Analysis failed for {url}")
            
    return {"results": results, "fragment_files": fragment_files, "current_step": "extraction_complete"}

def outline_node(state: AgentState):
    """
    执行整合生成（Reduce）
    """
    logger.info("Executing outline_node...")
    fragment_files = state.get("fragment_files", [])
    
    if not generator:
        logger.error("Generator instance is None!")
        return {"error": "Generator not initialized"}
        
    if not fragment_files:
        logger.warning("No fragment files found for outline generation.")
        return {"error": "No content to generate outline"}
        
    logger.info(f"Integrating {len(fragment_files)} fragments...")
    
    # 调用整合逻辑
    outline_text = generator.integrate_fragments(fragment_files)
    logger.info(f"Generated outline length: {len(outline_text)}")
    
    return {"outline": outline_text, "current_step": "complete"}

def create_graph(checkpointer=None):
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("scan", scan_node)
    workflow.add_node("extract", extract_node)
    # workflow.add_node("outline", outline_node)
    
    # 设置入口
    workflow.set_entry_point("scan")
    
    # 连接
    workflow.add_edge("scan", "extract")
    # workflow.add_edge("extract", "outline")
    workflow.add_edge("extract", END)
    # workflow.add_edge("outline", END)
    
    # 编译图
    if checkpointer is None:
        checkpointer = MemorySaver()
    app = workflow.compile(interrupt_after=["scan"], checkpointer=checkpointer)
    return app
