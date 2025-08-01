import os
import sys
import logging

import asyncio
import json
from typing import List, Dict, Any, Type
from pydantic import BaseModel
import serpapi

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import (
    Model,
    ModelProvider,
    OpenAIChatCompletionsModel,
    set_default_openai_client,
    set_tracing_disabled,
    set_default_openai_api,
)
from agents import function_tool

from agents.model_settings import ModelSettings


# =========================
# LOG CONFIG
# =========================

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_CONFIG = {
    "level": LOG_LEVEL,
    "format": LOG_FORMAT,
    "handlers": [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
}
logging.basicConfig(**LOG_CONFIG)

logger = logging.getLogger(__name__)


# =========================
# MODEL CONFIG
# =========================


# 加载环境变量
load_dotenv()

# 模型配置
API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen3-8B")

# 初始化OpenAI客户端（单例模式）
custom_client = AsyncOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

# 自定义模型提供者
class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: str | None) -> Model:
        return OpenAIChatCompletionsModel(model=model_name or MODEL_NAME, openai_client=custom_client)

class ReasoningModelProvider(ModelProvider):
    """
    高级模型提供者，处理推理信息和工具调用
    1. 过滤推理内容
    2. 转换工具调用
    """
    def get_model(self, model_name: str | None) -> Model:
        """获取处理了reasoning和tool_call的模型"""
        model = OpenAIChatCompletionsModel(
            model = model_name or MODEL_NAME,
            openai_client = custom_client
        )
        
        # 保存原始的get_response方法
        original_get_response = model.get_response
        
        # 创建新的get_response方法来过滤输出和处理工具调用
        async def enhanced_get_response(*args, **kwargs):
            response = await original_get_response(*args, **kwargs)
            # 打印调试信息
            # logger.info(f"原始模型响应: {str(response)}")
            
            filtered_output = []
            for item in response.output:
                # 处理推理内容
                if hasattr(item, "type"):
                    if item.type == "reasoning":
                        reasoning_content = item.summary[0].text if hasattr(item, 'summary') and item.summary else '无法获取详细内容'
                        logger.info(f"[发现reasoning内容，已过滤] <reasoning>{reasoning_content}</reasoning>")
                        continue
                    
                # 保留其他类型的输出
                filtered_output.append(item)
            
            # 更新响应的输出
            response.output = filtered_output
            logger.info(f"过滤推理内容后模型响应: {str(response)}")

            return response
        
        # 替换 get_response 方法
        model.get_response = enhanced_get_response
        return model

# 创建模型提供者实例
# CUSTOM_MODEL_PROVIDER = CustomModelProvider()
CUSTOM_MODEL_PROVIDER = ReasoningModelProvider()


# 通用模型设置
DEFAULT_MODEL_SETTINGS = ModelSettings(
    temperature=0.7,
    extra_body={"enable_thinking": False},
)

# 设置全局默认配置（应用启动时调用一次）
def setup_openai_config():
    """配置OpenAI客户端的全局设置"""
    set_default_openai_client(custom_client)
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)

setup_openai_config()


# =========================
# JSON OUTPUT FORMAT
# =========================

def get_model_structure(model: Type[BaseModel]) -> str:
    """
    获取Pydantic模型的字段结构并转换为JSON字符串
    支持任意层级的嵌套结构
    
    Args:
        model: 继承自BaseModel的Pydantic模型类
    
    Returns:
        包含模型字段结构的JSON字符串，格式为:
        {"字段名": "类型信息", ...}
    """
    def process_type(annotation: Any) -> str:
        """递归处理字段类型，生成人类可读的类型描述"""
        # 处理泛型类型（如List、Dict）
        if hasattr(annotation, '__origin__'):
            origin = annotation.__origin__
            args = annotation.__args__
            
            if origin is list:
                if len(args) == 1:
                    return f"List[{process_type(args[0])}]"
                return "List[Any]"
            elif origin is dict:
                if len(args) == 2:
                    return f"Dict[{process_type(args[0])}, {process_type(args[1])}]"
                return "Dict[Any, Any]"
            else:
                # 其他泛型类型（如Set、Tuple等）
                args_str = ", ".join([process_type(arg) for arg in args])
                return f"{origin.__name__}[{args_str}]"
        
        # 处理BaseModel子类（递归）
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return get_nested_structure(annotation)
        
        # 处理基础类型
        if hasattr(annotation, '__name__'):
            return annotation.__name__
        
        # 未知类型
        return str(annotation)
    
    def get_nested_structure(model_cls: Type[BaseModel]) -> Dict[str, str]:
        """获取模型的嵌套结构字典"""
        structure = {}
        for field_name, field in model_cls.model_fields.items():
            structure[field_name] = process_type(field.annotation)
        return structure
    
    # 转换为JSON字符串，保持格式美观
    return json.dumps(get_nested_structure(model), ensure_ascii=False, indent=2)


# =========================
# WEB SEARCH TOOL
# =========================


# 初始化搜索客户端
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
if not SERPER_API_KEY:
    raise ValueError("SERPER_API_KEY environment variable is required")

search_client = serpapi.Client(api_key=SERPER_API_KEY)

@function_tool(
    name_override="web_search",
    description_override="执行网络搜索，返回搜索结果。参数：query（搜索关键词，str），num_results（结果数量，默认10，int）。"
)
async def web_search(query: str, num_results: int = 10) -> str:
    """
    网络搜索工具。返回JSON格式的搜索结果。
    """
    def _sync_impl():
        try:
            payload = {"q": query, "engine": "google", "num": num_results}
            search_results = search_client.search(payload)["organic_results"]
            
            if not search_results:
                return "未找到搜索结果"
            
            # 格式化结果
            formatted_results = []
            for idx, result in enumerate(search_results[:num_results]):
                formatted_results.append({
                    "id": idx + 1,
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", "")
                })
            
            return json.dumps(formatted_results, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return f"搜索失败: {str(e)}"
    
    return await asyncio.to_thread(_sync_impl)

