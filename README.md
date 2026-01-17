# LangChain Content Extraction Agent

这是一个基于 LangGraph 的智能内容提取代理，专为从技术文档（如 LangChain 文档）中提取结构化知识而设计。

## 核心特性

- **智能爬虫 (Smart Crawler)**：自动解析 Sitemap，支持递归查找，并按 URL 前缀过滤。
- **人机交互 (Human-in-the-loop)**：采用 LangGraph 的中断/恢复机制，允许用户在提取前审核 URL 列表。
- **碎片化存储 (Fragment Storage)**：采用 Map-Reduce 架构，将单页分析结果保存为本地 JSON 片段，有效防止上下文溢出，支持断点续传。
- **结构化生成 (Structured Generation)**：基于官方目录结构 (TOC) 索引本地片段，生成标准化的技术书籍，确保逻辑严密且覆盖全面。
- **多语言优化**：默认输出中文主导的双语内容（保留英文术语）。

## 工作流程

系统采用 **Scan -> Extract -> Fragment -> Index -> Generate** 的五阶段处理流程：

1.  **Scan (扫描)**: 解析 Sitemap 发现目标 URL。
2.  **Extract (提取)**: 并发抓取网页内容。
3.  **Fragment (分片)**: LLM 分析单页内容，提取核心概念与摘要，保存为 `outputs/fragments/*.json`。
4.  **Index (索引)**: 建立 URL 到本地片段的倒排索引。
5.  **Generate (生成)**: 按照预定义的目录结构 (TOC)，从索引中匹配对应片段，组装成完整书籍 `outputs/structured.md`。

## 安装

1. 安装依赖：
```bash
pip install -r requirements.txt
# 或者使用 uv
uv pip install -r requirements.txt
```

2. 配置环境变量：
复制 `.env.example` 为 `.env` 并填入配置：
```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

## 使用方法

### 第一阶段：抓取与碎片化 (Scan & Extract)

使用 `main.py` 抓取目标网站并生成本地内容片段：

```bash
PYTHONPATH=. python main.py \
  --sitemap "https://docs.langchain.com/sitemap.xml" \
  --prefix "https://docs.langchain.com/oss/python/langchain/agents"
```

**交互步骤**：
1. 程序扫描 Sitemap 并列出 URL。
2. 用户输入序号选择 URL (或输入 `all`)。
3. 系统自动提取并生成 `outputs/fragments/*.json`。

### 第二阶段：结构化生成 (Structured Generation)

当 `outputs/fragments` 目录中有数据后，运行以下命令生成最终文档：

```bash
python main.py --generate
```

该命令会：
1. 扫描 `outputs/fragments` 建立内存索引。
2. 读取预定义的目录结构 (TOC)。
3. 自动匹配片段并生成 `outputs/structured.md`。

## 项目结构

- `src/core/`
  - `scanner.py`: Sitemap 扫描器
  - `extractor.py`: 内容提取器
  - `generator.py`: LLM 分析与生成核心
  - `structure_generator.py`: 结构化文档生成逻辑
  - `indexer.py`: 片段索引器
- `src/graph/workflow.py`: LangGraph 状态机定义
- `src/utils/toc_definitions.py`: 目录结构定义
- `outputs/fragments/`: 中间分析结果存储
