# LangChain 官方文档目录结构定义
# 用于指导生成器的结构化输出

LANGCHAIN_TOC = [
    {"title": "Overview", "title_cn": "概览", "keywords": ["langchain/overview"]},
    {"title": "Get Started", "title_cn": "快速入门", "children": [
        {"title": "Install", "title_cn": "安装", "keywords": ["install"]},
        {"title": "Quickstart", "title_cn": "快速上手", "keywords": ["quickstart"]},
        {"title": "Changelog", "title_cn": "更新日志", "keywords": ["changelog"]},
        {"title": "Philosophy", "title_cn": "设计理念", "keywords": ["philosophy"]},
    ]},
    {"title": "Core Components", "title_cn": "核心组件", "children": [
        {"title": "Agents", "title_cn": "智能体", "keywords": ["agents"]},
        {"title": "Models", "title_cn": "模型", "keywords": ["models"]},
        {"title": "Messages", "title_cn": "消息", "keywords": ["messages"]},
        {"title": "Tools", "title_cn": "工具", "keywords": ["tools"]},
        {"title": "Short-term Memory", "title_cn": "短期记忆", "keywords": ["short-term-memory"]},
        {"title": "Streaming", "title_cn": "流式处理", "keywords": ["streaming/overview"]},
        {"title": "Structured Output", "title_cn": "结构化输出", "keywords": ["structured-output"]},
    ]},
    {"title": "Middleware", "title_cn": "中间件", "children": [
        {"title": "Overview", "title_cn": "概览", "keywords": ["middleware/overview"]},
        {"title": "Built-in Middleware", "title_cn": "内置中间件", "keywords": ["middleware/built-in"]},
        {"title": "Custom Middleware", "title_cn": "自定义中间件", "keywords": ["middleware/custom"]},
        {"title": "Advanced Usage", "title_cn": "高级用法", "children": [
             {"title": "Guardrails", "title_cn": "安全护栏", "keywords": ["guardrails"]},
             {"title": "Runtime", "title_cn": "运行时", "keywords": ["runtime"]},
             {"title": "Context Engineering", "title_cn": "上下文工程", "keywords": ["context-engineering"]},
             {"title": "Model Context Protocol (MCP)", "title_cn": "模型上下文协议", "keywords": ["mcp", "model-context-protocol"]},
             {"title": "Human-in-the-loop", "title_cn": "人机协同", "keywords": ["human-in-the-loop", "hitl"]},
        ]},
    ]},
    {"title": "Multi-agent Systems", "title_cn": "多智能体系统", "children": [
        {"title": "Overview", "title_cn": "概览", "keywords": ["multi-agent"]},
        {"title": "Subagents", "title_cn": "子智能体", "keywords": ["subagents"]},
        {"title": "Handoffs", "title_cn": "任务交接", "keywords": ["handoffs"]},
        {"title": "Skills", "title_cn": "技能", "keywords": ["skills"]},
        {"title": "Router", "title_cn": "路由", "keywords": ["router"]},
        {"title": "Custom Workflow", "title_cn": "自定义工作流", "keywords": ["custom-workflow"]},
    ]},
    {"title": "Retrieval", "title_cn": "检索", "keywords": ["retrieval"]},
    {"title": "Long-term Memory", "title_cn": "长期记忆", "keywords": ["long-term-memory"]},
    {"title": "Agent Development", "title_cn": "智能体开发", "children": [
        {"title": "LangSmith Studio", "title_cn": "LangSmith 工作台", "keywords": ["studio"]},
        {"title": "Testing", "title_cn": "测试", "keywords": ["test"]},
        {"title": "Agent Chat UI", "title_cn": "聊天界面", "keywords": ["ui"]},
        {"title": "Deployment", "title_cn": "部署", "keywords": ["deploy"]},
        {"title": "Observability", "title_cn": "可观测性", "keywords": ["observability"]},
    ]}
]
