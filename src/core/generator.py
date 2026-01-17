import concurrent.futures
import hashlib
import json
import os
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from loguru import logger
from src.utils.config import settings

# 定义输出结构
class KnowledgePoint(BaseModel):
    concept: str = Field(..., description="核心概念名称。保留原有英文，如有通用中文译名，请在括号中补充，例如：'Agent (智能体)'")
    explanation: str = Field(..., description="一句话解释，使用中文，适合背诵和记忆")
    tags: List[str] = Field(default_factory=list, description="相关标签")
    importance: int = Field(..., description="重要性评分 1-5", ge=1, le=5)

class PageAnalysis(BaseModel):
    summary: str = Field(..., description="页面内容的简要总结，使用中文")
    page_type: Literal["Index", "Concept", "Guide", "Reference", "Other"] = Field(
        ..., 
        description="页面类型：Index(目录/概览), Concept(概念解释), Guide(操作指南), Reference(API/参考), Other(其他)"
    )
    knowledge_points: List[KnowledgePoint] = Field(..., description="页面中包含的知识点列表")

class Generator:
    """
    负责调用 LLM 分析内容并生成大纲。
    """
    
    def __init__(self):
        if not settings:
            raise ValueError("Configuration not loaded")
            
        self.llm = ChatOpenAI(
            model=settings.llm.model,
            openai_api_key=settings.llm.api_key,
            openai_api_base=settings.llm.base_url,
            temperature=0.1
        )
        
        self.parser = PydanticOutputParser(pydantic_object=PageAnalysis)
        
        self.analyze_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专家级的知识整理助手。你的任务是从给定的技术文档内容中，提取核心知识脉络。\n"
                       "请仔细阅读内容，识别出关键的概念、原理或步骤，并判断页面类型。\n"
                       "要求：\n"
                       "1. **输出语言必须为中文**（专有名词除外）。\n"
                       "2. **专有名词保留原有英文**，并在括号中补充中文翻译（如果有通用译名）。\n"
                       "3. 总结和解释要简洁明了，适合学习和记忆。\n"
                       "输出必须严格遵循 JSON 格式。\n"
                       "{format_instructions}"),
            ("user", "标题: {title}\n\n内容:\n{content}")
        ])
        
        self.merge_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的技术文档编辑。你的任务是将多个独立的文档分析片段整合为一个逻辑连贯、结构清晰的完整技术指南。\n"
                       "输入是一组相关的知识点和总结。\n"
                       "要求：\n"
                       "1. **逻辑重组**：根据知识点的关联性进行分组，不要简单堆砌。\n"
                       "2. **去重**：合并重复的知识点。\n"
                       "3. **润色**：使用流畅的中文将碎片化信息串联起来。\n"
                       "4. **主线优先**：优先参考类型为 'Index' 或 'Concept' 的内容作为骨架。\n"
                       "输出格式：标准的 Markdown 文档。"),
            ("user", "以下是待整合的文档片段：\n\n{fragments}")
        ])

    def analyze_page(self, title: str, content: str) -> Optional[PageAnalysis]:
        """
        分析单个页面内容。
        """
        try:
            # 截断过长的内容以避免 token 溢出
            truncated_content = content[:15000]
            
            prompt_value = self.analyze_prompt.invoke({
                "title": title, 
                "content": truncated_content,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            logger.info(f"Analyzing page: {title}")
            response = self.llm.invoke(prompt_value)
            
            # 解析结果
            result = self.parser.parse(response.content)
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing page {title}: {e}")
            return None

    def save_analysis(self, analysis: PageAnalysis, url: str, output_dir: str, url_prefix: str = "") -> str:
        """
        将分析结果保存到文件。返回文件路径。
        """
        # Determine filename based on URL and prefix
        if url_prefix and url.startswith(url_prefix):
            name = url[len(url_prefix):].strip("/").replace("/", "_")
            if not name:
                name = "index"
            filename = f"{name}.json"
        else:
            # Fallback logic: use path-based name if possible, otherwise hash
            from urllib.parse import urlparse
            path = urlparse(url).path.strip("/")
            if path:
                # Remove common prefix if implicit? No, just use full path safe
                filename = f"{path.replace('/', '_')}.json"
            else:
                url_hash = hashlib.md5(url.encode()).hexdigest()
                filename = f"{url_hash}.json"

        filepath = os.path.join(output_dir, filename)
        
        data = analysis.model_dump()
        data["url"] = url  # 补充 URL 信息
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return filepath

    def integrate_fragments(self, fragment_paths: List[str]) -> str:
        """
        整合多个分析片段，生成最终大纲。
        支持分批处理以避免 Context Window 溢出。
        """
        fragments_content = []
        for path in fragment_paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 格式化为易读的文本供 LLM 阅读
                    text = f"--- Page: {data.get('url')} (Type: {data.get('page_type')}) ---\n"
                    text += f"Summary: {data.get('summary')}\n"
                    text += "Points:\n"
                    for kp in data.get('knowledge_points', []):
                        text += f"- {kp['concept']} ({kp['importance']}⭐): {kp['explanation']}\n"
                    fragments_content.append(text)
            except Exception as e:
                logger.warning(f"Failed to load fragment {path}: {e}")

        if not fragments_content:
            return "No content to integrate."

        # 分批逻辑
        BATCH_SIZE = 5
        batches = [fragments_content[i:i + BATCH_SIZE] for i in range(0, len(fragments_content), BATCH_SIZE)]
        
        batch_summaries = []
        
        # 并行处理每一批（或者串行，取决于 LLM 限流）
        # 这里为了稳妥选择串行，因为是 Reduce 过程
        for i, batch in enumerate(batches):
            logger.info(f"Integrating batch {i+1}/{len(batches)}...")
            combined_text = "\n\n".join(batch)
            
            # 如果只有一批，直接生成 Markdown
            if len(batches) == 1:
                response = self.llm.invoke(self.merge_prompt.invoke({"fragments": combined_text}))
                return response.content
            
            # 如果有多批，先生成中间摘要
            response = self.llm.invoke(self.merge_prompt.invoke({"fragments": combined_text}))
            batch_summaries.append(response.content)

        # 全局合并
        logger.info("Performing final merge...")
        final_input = "\n\n".join(batch_summaries)
        
        final_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个主编。你的任务是将多个 Markdown 章节整合成一篇完整的文档。\n"
                       "请统一格式，添加总标题和序言，并确保各章节过渡自然。\n"
                       "不要删除具体内容，只是进行组织和润色。"),
            ("user", "以下是各章节草稿：\n\n{drafts}")
        ])
        
        try:
             # 如果内容非常多，可能再次溢出。这里做一个简单的长度检查
            if len(final_input) > 20000:
                logger.warning("Final content too large for single pass, returning concatenated drafts.")
                return "# 汇总文档 (未完全润色)\n\n" + final_input
                
            response = self.llm.invoke(final_prompt.invoke({"drafts": final_input}))
            return response.content
        except Exception as e:
            logger.error(f"Final merge failed: {e}")
            return "# 汇总文档 (合并失败)\n\n" + final_input

    def polish_section(self, content: str, chapter_num: int) -> str:
        """对单个章节进行润色和层级调整"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个技术书籍编辑。请对提供的 Markdown 内容进行润色和格式调整。\n"
                       "任务要求：\n"
                       "1. 将该部分作为全书的第 {chapter_num} 章。\n"
                       "2. 将原有一级标题 (# Title) 降级为二级标题 (## Title)，以此类推，但请为本章添加一个合适的一级标题（例如：# 第 {chapter_num} 章：[原标题]）。\n"
                       "3. 保持专业术语的双语格式（English + 中文解释）。\n"
                       "4. 优化语言流畅度，但保留所有技术细节、代码块和表格。\n"
                       "5. 确保 Markdown 格式规范。"),
            ("user", "原始内容：\n\n{content}")
        ])
        response = self.llm.invoke(prompt.invoke({"content": content, "chapter_num": chapter_num}))
        return response.content

    def generate_toc_and_intro(self, chapters: List[str]) -> str:
        """根据各章内容生成总目录和前言"""
        combined_summaries = "\n\n".join([c[:1000] for c in chapters]) # 取每章前1000字做摘要
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个技术书籍主编。请根据以下各章摘要，生成全书的：\n"
                       "1. 书名（Main Title）\n"
                       "2. 前言（Preface）：概述全书内容和目标读者。\n"
                       "3. 目录（Table of Contents）：列出各章及主要小节。\n"
                       "请直接输出 Markdown 格式。"),
            ("user", "各章摘要片段：\n\n{summaries}")
        ])
        response = self.llm.invoke(prompt.invoke({"summaries": combined_summaries}))
        return response.content

    def generate_from_structure(self, toc: List[Dict], fragments_dir: str) -> str:
        """
        基于给定的目录结构和本地片段生成完整文档。
        """
        from src.core.indexer import FragmentIndexer
        
        indexer = FragmentIndexer(fragments_dir)
        indexer.build_index()
        
        content = ""
        
        def process_node(node, level=1):
            text = ""
            title = node["title"]
            title_cn = node.get("title_cn")
            
            # Use Bilingual Title if available
            display_title = f"{title} ({title_cn})" if title_cn else title
            
            # Match fragment
            fragment = None
            if "keywords" in node:
                for kw in node["keywords"]:
                    fragment = indexer.find_fragment(kw)
                    if fragment:
                        break
            
            # Generate Header
            text += f"{'#' * level} {display_title}\n\n"
            
            if fragment:
                # Load content
                try:
                    with open(fragment['path'], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        text += f"{data.get('summary', '')}\n\n"
                        if data.get('knowledge_points'):
                            text += "#### Core Concepts\n"
                            for kp in data['knowledge_points']:
                                text += f"- **{kp['concept']}** ({kp.get('importance', 3)}⭐): {kp['explanation']}\n"
                        text += "\n"
                except Exception as e:
                    logger.warning(f"Error reading fragment {fragment['path']}: {e}")
            else:
                 if not node.get("children"):
                    text += "*(Content not found)*\n\n"

            # Children
            if "children" in node:
                for child in node["children"]:
                    text += process_node(child, level + 1)
            
            return text

        for node in toc:
            content += process_node(node, level=2)
            
        return content

# 单例
try:
    generator = Generator()
except Exception as e:
    logger.warning(f"Generator init failed (likely missing config): {e}")
    generator = None
