import os
import re
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from src.utils.config import settings

class Visualizer:
    """
    负责为文档补充图表（支持 AntV Infographic 和 Mermaid）。
    仅处理中间章节的插图，不生成开头和结尾的汇总图。
    """
    
    def __init__(self):
        if not settings.llm.api_key:
            raise ValueError("LLM API Key not found")
            
        self.llm = ChatOpenAI(
            model=settings.llm.model,
            openai_api_key=settings.llm.api_key,
            openai_api_base=settings.llm.base_url,
            temperature=0.1
        )

    def generate_chapter_diagrams(self, content: str) -> str:
        """
        处理文档中间部分，为章节插入图表。
        """
        logger.info("Analyzing chapters for diagram opportunities...")
        
        # Split by H2 headers
        sections = re.split(r'(^## .+)', content, flags=re.MULTILINE)
        
        new_content = [sections[0]] # Preamble
        
        # Process pairs (Header, Content)
        for i in range(1, len(sections), 2):
            header = sections[i]
            body = sections[i+1] if i+1 < len(sections) else ""
            full_section = header + body
            
            # 放宽限制：只要内容长度足够，都尝试生成图表，让 LLM 决定是否必要
            # 但为了避免无意义图表，仍然要求一定长度
            if len(body.strip()) > 300:
                logger.info(f"Generating diagram for section: {header.strip()}")
                diagram = self._create_diagram_for_text(header, body)
                if diagram:
                    full_section = header + "\n\n" + diagram + "\n" + body
            
            new_content.append(full_section)
            
        return "".join(new_content)

    def _create_diagram_for_text(self, title: str, text: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个可视化专家，精通 AntV Infographic 和 Mermaid。\n"
                       "请根据章节内容，选择最合适的图表引擎生成一个图表代码块。\n"
                       "\n"
                       "### 1. 引擎与模版选择（根据内容逻辑选择）\n"
                       "- **AntV Infographic**：适用于结构化、展示型内容。\n"
                       "  - **对比 (Compare)** -> 适用于方案对比、优劣势分析、SWOT。\n"
                       "    - 数据键：`data.compares`\n"
                       "    - 模版：`compare-quadrant-quarter-circular` (象限), `compare-binary-horizontal-badge-card-arrow` (两方PK)\n"
                       "  - **列表 (List)** -> 适用于核心概念列举、功能清单、检查项。\n"
                       "    - 数据键：`data.lists`\n"
                       "    - 模版：`list-column-done-list` (清单), `list-grid-horizontal-icon-arrow` (网格), `list-pyramid-badge-card` (金字塔)\n"
                       "  - **序列 (Sequence)** -> 适用于步骤指南、时间线、发展历程。\n"
                       "    - 数据键：`data.sequences`\n"
                       "    - 模版：`sequence-circular-simple` (循环), `sequence-timeline-done-list` (时间轴), `sequence-mountain-underline-text` (里程碑)\n"
                       "\n"
                       "- **Mermaid**：适用于逻辑流、系统架构、状态流转。\n"
                       "  - 模版：`graph TD` (流程图), `sequenceDiagram` (时序交互), `classDiagram` (类结构)。\n"
                       "\n"
                       "### 2. 排版与内容要求\n"
                       "- **多样性优先**：不要总是使用同一种图表。如果是对比内容，必须用 Compare 类；如果是步骤内容，必须用 Sequence 类。\n"
                       "- **AntV 限制**：`desc` 字段限 30 字。**必须根据模版类型使用正确的 `data` 键**。\n"
                       "\n"
                       "### 3. 输出格式\n"
                       "直接输出代码块。如果内容不适合生成图表，输出 `NO_CHART`。\n"
                       "\n"
                       "#### 示例 1：AntV 列表 (List)\n"
                       "```infographic\n"
                       "infographic list-column-done-list\n"
                       "data\n"
                       "  lists\n"
                       "    - label 核心特性\n"
                       "      desc 特性描述(限30字)\n"
                       "```\n"
                       "\n"
                       "#### 示例 2：AntV 对比 (Compare)\n"
                       "```infographic\n"
                       "infographic compare-binary-horizontal-badge-card-arrow\n"
                       "data\n"
                       "  compares\n"
                       "    - label 方案 A\n"
                       "      desc 优势描述\n"
                       "    - label 方案 B\n"
                       "      desc 优势描述\n"
                       "```\n"
                       "\n"
                       "#### 示例 3：AntV 序列 (Sequence)\n"
                       "```infographic\n"
                       "infographic sequence-timeline-done-list\n"
                       "data\n"
                       "  sequences\n"
                       "    - label 第一阶段\n"
                       "      desc 初始化项目结构\n"
                       "    - label 第二阶段\n"
                       "      desc 开发核心功能\n"
                       "```\n"
                       "\n"
                       "#### 示例 4：Mermaid 流程\n"
                       "```mermaid\n"
                       "graph TD\n"
                       "  A[开始] --> B{{判断}}\n"
                       "  B -->|是| C[执行]\n"
                       "  B -->|否| D[结束]\n"
                       "```"),
            ("user", "章节标题: {title}\n内容片段: {text}")
        ])
        try:
            response = self.llm.invoke(prompt.invoke({"title": title, "text": text[:3000]}))
            content = response.content.strip()
            if "NO_CHART" in content:
                return ""
            return content
        except Exception as e:
            logger.error(f"Failed to generate diagram for {title}: {e}")
            return ""

    def process_document(self, input_path: str, output_path: str = None):
        """主入口：处理整个文档。如果提供 output_path，则写入新文件；否则覆盖原文件。"""
        if not os.path.exists(input_path):
            logger.error(f"File not found: {input_path}")
            return

        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        logger.info(f"Visualizing document: {input_path}")

        # 仅处理中间章节图表，移除首尾图表
        content_with_chapters = self.generate_chapter_diagrams(content)

        final_content = content_with_chapters

        target_path = output_path if output_path else input_path
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        logger.success(f"Visualization complete! Saved to {target_path}")
