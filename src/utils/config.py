import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# 加载 .env 文件
# 假设 .env 在项目根目录，即当前文件的上上上级目录 (src/utils/config.py -> src/utils -> src -> root)
# 或者直接依赖 python-dotenv 的自动查找功能
load_dotenv()

class LLMSettings(BaseModel):
    """
    映射 .env 中的 BASIC_MODEL_* 配置到标准字段
    """
    base_url: str = Field(..., alias="BASIC_MODEL_BASE_URL")
    api_key: str = Field(..., alias="BASIC_MODEL_API_KEY")
    model: str = Field(..., alias="BASIC_MODEL_MODEL")

    class Config:
        populate_by_name = True

class AppSettings(BaseModel):
    llm: LLMSettings
    
    # 可以在这里添加其他配置，如输出目录等
    output_dir: Path = Field(default=Path("outputs"))

def load_config() -> AppSettings:
    """
    从环境变量加载配置
    """
    # 构造 LLM 设置
    # 注意：这里我们手动从 os.environ 获取，因为 pydantic 的自动环境变量加载通常需要统一的前缀
    # 或者我们可以直接实例化，让 pydantic 验证
    
    try:
        llm_settings = LLMSettings(
            base_url=os.environ["BASIC_MODEL_BASE_URL"],
            api_key=os.environ["BASIC_MODEL_API_KEY"],
            model=os.environ["BASIC_MODEL_MODEL"]
        )
        
        return AppSettings(llm=llm_settings)
    except KeyError as e:
        raise ValueError(f"Missing required environment variable: {e}")

# 单例实例，方便导入
try:
    settings = load_config()
except Exception as e:
    # 允许在没有 .env 的情况下导入模块（例如在测试时），但使用时会报错
    print(f"Warning: Failed to load configuration: {e}")
    settings = None
