from typing import List, Dict, TypedDict, Annotated, Optional
import operator

class AgentState(TypedDict):
    """
    智能体状态定义
    """
    # 输入信息
    target_url_prefix: str
    sitemap_url: str
    
    # 扫描阶段
    candidate_urls: List[str]
    
    # 用户确认后的 URL
    approved_urls: List[str]
    
    # 爬取与分析阶段
    # 使用 Annotated[..., operator.ior] 允许在不同节点合并字典结果
    results: Annotated[Dict[str, dict], operator.ior]
    
    # 临时文件路径列表
    fragment_files: Annotated[List[str], operator.add]
    
    # 状态标记
    current_step: str
    error: Optional[str]
