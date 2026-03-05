from dataclasses import dataclass, field
from typing import Annotated

from src import config as sys_config
from src.agents.common.context import BaseContext
from src.agents.common.mcp import MCP_SERVERS
from src.agents.common.tools import gen_tool_info

from .tools import get_tools


@dataclass(kw_only=True)
class Context(BaseContext):
    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default_factory=lambda: getattr(sys_config, "default_model", "") or "deepseek/deepseek-chat",
        metadata={"name": "智能体模型", "options": [], "description": "智能体的驱动模型"},
    )

    tools: Annotated[list[dict], {"__template_metadata__": {"kind": "tools"}}] = field(
        default_factory=list,
        metadata={
            "name": "工具",
            "options": lambda: gen_tool_info(get_tools()),  # 动态生成，避免导入时初始化外部依赖
            "description": "工具列表",
        },
    )

    mcps: list[str] = field(
        default_factory=list,
        metadata={"name": "MCP服务器", "options": list(MCP_SERVERS.keys()), "description": "MCP服务器列表"},
    )
