import os
import traceback

from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from src import config
from src.utils import get_docker_safe_url


def _resolve_api_key(env_config: str | list[str] | None) -> str:
    if env_config is None:
        return ""
    if isinstance(env_config, list):
        for env_var in env_config:
            if env_var == "NO_API_KEY":
                return "EMPTY"
            value = os.getenv(env_var)
            if value:
                return value
        return ""
    if env_config == "NO_API_KEY":
        return "EMPTY"
    return os.getenv(env_config, env_config)


def load_chat_model(fully_specified_name: str, **kwargs) -> BaseChatModel:
    """
    Load a chat model from a fully specified name.
    """
    if not fully_specified_name or "/" not in fully_specified_name:
        raise ValueError(f"Invalid model spec `{fully_specified_name}`. Expected `provider/model` format.")

    provider, model = fully_specified_name.split("/", maxsplit=1)

    assert provider != "custom", "[弃用] 自定义模型已移除，请在 src/config/static/models.yaml 中配置"

    model_info = config.model_names.get(provider)
    if not model_info:
        available = ", ".join(sorted(config.model_names.keys()))
        raise ValueError(f"Model provider `{provider}` is not configured. Available providers: {available}")

    base_url = model_info.get("base_url")
    if not base_url:
        raise ValueError(f"Model provider `{provider}` is missing `base_url` in models config.")

    api_key = _resolve_api_key(model_info.get("env", "NO_API_KEY"))
    base_url = get_docker_safe_url(base_url)

    if provider in ["deepseek", "dashscope"]:
        from langchain_deepseek import ChatDeepSeek

        return ChatDeepSeek(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url,
            api_base=base_url,
            stream_usage=True,
        )

    elif provider == "together":
        from langchain_together import ChatTogether

        return ChatTogether(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url,
            stream_usage=True,
        )

    else:
        try:  # 其他模型，默认使用OpenAIBase, like openai, zhipuai
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model,
                api_key=SecretStr(api_key),
                base_url=base_url,
                stream_usage=True,
            )
        except Exception as e:
            raise ValueError(f"Model provider {provider} load failed, {e} \n {traceback.format_exc()}")
