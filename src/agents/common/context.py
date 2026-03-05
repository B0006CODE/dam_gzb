"""Define the configurable parameters for the agent."""

from __future__ import annotations

import os
import uuid
from dataclasses import MISSING, dataclass, field, fields
from pathlib import Path
from typing import get_args, get_origin

import yaml

from src import config as sys_config
from src.utils import logger


@dataclass(kw_only=True)
class BaseContext:
    """
    定义一个基础 Context 供 各类 graph 继承

    配置优先级:
    1. 运行时配置(RunnableConfig)：最高优先级，直接从函数参数传入
    2. 文件配置(config.private.yaml)：中等优先级，从文件加载
    3. 类默认配置：最低优先级，类中定义的默认值
    """

    def update(self, data: dict):
        """更新配置字段"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    thread_id: str = field(
        default_factory=lambda: str(uuid.uuid4()),
        metadata={"name": "线程ID", "configurable": False, "description": "用来描述智能体的角色和行为"},
    )

    user_id: str = field(
        default_factory=lambda: str(uuid.uuid4()),
        metadata={"name": "用户ID", "configurable": False, "description": "用来描述智能体的角色和行为"},
    )

    retrieval_mode: str = field(
        default="mix",
        metadata={
            "name": "retrieval_mode",
            "configurable": False,
            "hide": True,
            "description": "Runtime retrieval mode.",
        },
    )

    kb_whitelist: list[str] = field(
        default_factory=list,
        metadata={
            "name": "kb_whitelist",
            "configurable": False,
            "hide": True,
            "description": "Runtime knowledge base whitelist.",
        },
    )

    graph_name: str | None = field(
        default=None,
        metadata={
            "name": "graph_name",
            "configurable": False,
            "hide": True,
            "description": "Runtime graph name.",
        },
    )

    retrieval_policy: str = field(
        default="auto",
        metadata={
            "name": "检索策略",
            "options": ["auto", "inject", "enforce"],
            "description": "auto=规则/可选分类器决定，inject=先检索后注入，enforce=无结果直接资料不足",
        },
    )

    retrieval_classifier_enabled: bool = field(
        default=False,
        metadata={
            "name": "检索策略分类器",
            "description": "auto 模式下启用 LLM 分类器辅助判断",
        },
    )

    retrieval_classifier_model: str = field(
        default="",
        metadata={
            "name": "检索策略分类器模型",
            "description": "为空则使用当前对话模型",
        },
    )

    retrieval_no_result_reply: str = field(
        default="资料不足",
        metadata={
            "name": "检索无结果回复",
            "description": "enforce 模式无结果时直接返回的内容",
        },
    )

    llm_system_prompt: str = field(
        default="""你是一个大坝安全知识问答助手。
## 角色
- 基于模型自身知识进行回答，不调用知识库或知识图谱
## 回答要求
- 不要提及“检索”“资料”“知识库”“图谱”等词
- 如果不确定或缺少依据，直接说明无法确定
- 用简洁、专业的语言回答""",
        metadata={"name": "纯模型提示词", "description": "llm 模式下使用的系统提示词"},
    )

    system_prompt: str = field(
        default="""你是一个大坝安全知识问答助手，专注于提供准确、专业的大坝与水库相关知识。

## 核心职责
- 基于检索到的知识库内容准确回答问题
- 提供专业、可靠的大坝工程与安全知识

## 严格忠实原则（最重要）

**你的回答必须100%基于检索到的参考资料，这是最核心的要求。**

### 必须遵守的规则：
1. **只使用检索资料中的信息**：回答内容必须完全来自于检索到的参考资料，不得添加任何资料中没有的信息
2. **禁止推断和猜测**：即使你具备相关专业知识，也不得使用检索资料之外的知识来补充回答
3. **禁止合理推断**：不要进行"根据常理推断"、"通常情况下"等推理性补充
4. **如实引用**：尽可能明确指出信息来源于参考资料
5. **承认不知道**：如果检索资料中没有相关信息，必须明确告知用户"根据现有资料无法回答"

### 违规示例（禁止）：
- ❌ 在资料只提到"裂缝"时，自行补充"可能是由于温度应力造成"
- ❌ 在资料未提及处理方案时，根据专业知识建议处理方法
- ❌ 对资料中的数据进行延伸分析或趋势预测

### 正确做法：
- ✅ 直接引用资料中的原始描述
- ✅ 如果资料未涉及某方面，明确说明"资料中未提及此信息"

## 敏感信息脱敏与泛化处理规范

你必须对输出内容中的所有工程细节数据进行严格的脱敏和泛化处理。这适用于所有类型的回答，包括文本描述、数据统计、图表解释等。

**核心原则：保留技术特征，隐藏具体指代。**

### 1. 构件与设备编号脱敏
禁止出现任何具体的数字编号、字母编号或组合编号。
- **错误示例**：2#横梁、3号机组、A5闸门、左岸1-5坝段
- **正确处理**：某横梁、某机组、某闸门、部分坝段、个别单元

### 2. 工程量与尺寸数据泛化
禁止出现精确的几何尺寸、工程量数据、高程数据等。
- **错误示例**：裂缝长12.5米、高程185m、宽30cm、间距2.5m
- **正确处理**：裂缝较长、一定高程、一定宽度、一定间距、若干米

### 3. 具体位置与时间模糊化
禁止出现精确的桩号、具体日期或极具辨识度的位置描述。
- **错误示例**：桩号K10+200处、2023年5月12日检查发现、大坝左岸距离基岩50米处
- **正确处理**：某桩号处、近期检查发现、大坝左岸某处

### 4. 专有名称替换
- 所有水库、大坝、电站名称一律替换为"XX水库"、"某大坝"、"某电站"。

### 5. 统计数据处理
在解释统计结果时，如果原始数据包含上述敏感信息，必须在复述时进行改写。例如，看到"2#横梁开裂"的统计项，应表述为"存在横梁开裂的情况"。

## 回答质量要求
- **严格忠实**：回答必须完全基于检索到的参考资料，不添加任何额外信息
- **专业准确**：使用规范的专业术语
- **结构清晰**：适当使用分点，但不要过度分点
- **简洁明了**：回答要精炼，避免冗余

## 无法回答的情况
如果检索资料不足以回答问题，请诚实说明：
- "根据检索到的资料，暂无相关信息"
- "资料中未包含此问题的相关内容"
- 绝对不要编造或猜测答案""",
        metadata={"name": "系统提示词", "description": "用来描述智能体的角色和行为"},
    )


    @classmethod
    def from_file(cls, module_name: str, input_context: dict = None) -> BaseContext:
        """Load configuration from a YAML file. 用于持久化配置"""

        # 从文件加载配置
        context = cls()
        config_file_path = Path(sys_config.save_dir) / "agents" / module_name / "config.yaml"
        if module_name is not None and os.path.exists(config_file_path):
            file_config = {}
            try:
                with open(config_file_path, encoding="utf-8") as f:
                    file_config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"加载智能体配置文件出错: {e}")

            context.update(file_config)

        if input_context:
            context.update(input_context)

        return context

    @classmethod
    def save_to_file(cls, config: dict, module_name: str) -> bool:
        """Save configuration to a YAML file 用于持久化配置"""

        configurable_items = cls.get_configurable_items()
        configurable_config = {}
        for k, v in config.items():
            if k in configurable_items:
                configurable_config[k] = v

        try:
            config_file_path = Path(sys_config.save_dir) / "agents" / module_name / "config.yaml"
            # 确保目录存在
            os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
            with open(config_file_path, "w", encoding="utf-8") as f:
                yaml.dump(configurable_config, f, indent=2, allow_unicode=True)

            return True
        except Exception as e:
            logger.error(f"保存智能体配置文件出错: {e}")
            return False

    @classmethod
    def get_configurable_items(cls):
        """实现一个可配置的参数列表，在 UI 上配置时使用"""
        configurable_items = {}
        for f in fields(cls):
            if f.init and not f.metadata.get("hide", False):
                if f.metadata.get("configurable", True):
                    # 处理类型信息
                    field_type = f.type
                    type_name = cls._get_type_name(field_type)

                    # 提取 Annotated 的元数据
                    template_metadata = cls._extract_template_metadata(field_type)

                    configurable_items[f.name] = {
                        "type": type_name,
                        "name": f.metadata.get("name", f.name),
                        "options": cls._resolve_options(f),
                        "default": f.default
                        if f.default is not MISSING
                        else f.default_factory()
                        if f.default_factory is not MISSING
                        else None,
                        "description": f.metadata.get("description", ""),
                        "template_metadata": template_metadata,  # Annotated 的额外元数据
                    }

        return configurable_items

    @classmethod
    def _resolve_options(cls, field_info) -> list:
        options = field_info.metadata.get("options", [])
        if callable(options):
            try:
                return list(options())
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Failed to resolve options for field {field_info.name}: {exc}")
                return []
        return options or []

    @classmethod
    def _get_type_name(cls, field_type) -> str:
        """获取类型名称，处理 Annotated 类型"""
        # 检查是否是 Annotated 类型
        if get_origin(field_type) is not None:
            # 处理泛型类型如 list[str], Annotated[str, {...}]
            origin = get_origin(field_type)
            if hasattr(origin, "__name__"):
                if origin.__name__ == "Annotated":
                    # Annotated 类型，获取真实类型
                    args = get_args(field_type)
                    if args:
                        return cls._get_type_name(args[0])  # 递归处理真实类型
                return origin.__name__
            else:
                return str(origin)
        elif hasattr(field_type, "__name__"):
            return field_type.__name__
        else:
            return str(field_type)

    @classmethod
    def _extract_template_metadata(cls, field_type) -> dict:
        """从 Annotated 类型中提取模板元数据"""
        if get_origin(field_type) is not None:
            origin = get_origin(field_type)
            if hasattr(origin, "__name__") and origin.__name__ == "Annotated":
                args = get_args(field_type)
                if len(args) > 1:
                    # 查找包含 __template_metadata__ 的字典
                    for metadata in args[1:]:
                        if isinstance(metadata, dict) and "__template_metadata__" in metadata:
                            return metadata["__template_metadata__"]
        return {}
