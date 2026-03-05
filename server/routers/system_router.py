import asyncio
import json
import os
import uuid
from collections import deque
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from server.services.dam_service import dam_exception_service
from src.storage.db.models import User
from server.utils.auth_middleware import get_admin_user, get_required_user, get_superadmin_user
from src import config, graph_base
from src.models import select_model
from src.models.chat import test_chat_model_status, test_all_chat_models_status
from src.utils.datetime_utils import utc_now
from src.utils.logging_config import logger

system = APIRouter(prefix="/system", tags=["system"])

# =============================================================================
# === 健康检查分组 ===
# =============================================================================


@system.get("/health")
async def health_check():
    """系统健康检查接口（公开接口）"""
    return {"status": "ok", "message": "服务正常运行"}


# =============================================================================
# === 配置管理分组 ===
# =============================================================================


@system.get("/config")
def get_config(current_user: User = Depends(get_admin_user)):
    """获取系统配置"""
    return config.dump_config()


@system.post("/config")
async def update_config_single(key=Body(...), value=Body(...), current_user: User = Depends(get_admin_user)) -> dict:
    """更新单个配置项"""
    config[key] = value
    config.save()
    return config.dump_config()


@system.post("/config/update")
async def update_config_batch(items: dict = Body(...), current_user: User = Depends(get_admin_user)) -> dict:
    """批量更新配置项"""
    config.update(items)
    config.save()
    return config.dump_config()


@system.post("/restart")
async def restart_system(current_user: User = Depends(get_superadmin_user)):
    """重启系统（仅超级管理员）"""
    # 重新加载模型配置与环境变量状态，确保设置页可见项是最新的
    config._update_models_from_file()
    config.load()
    config.handle_self()
    config._config_items["embed_model"]["choices"] = list(config.embed_model_names.keys())
    config._config_items["reranker"]["choices"] = list(config.reranker_names.keys())
    graph_base.start()
    return {"message": "系统已重启"}


@system.get("/logs")
def get_system_logs(current_user: User = Depends(get_admin_user)):
    """获取系统日志"""
    try:
        from src.utils.logging_config import LOG_FILE

        with open(LOG_FILE) as f:
            last_lines = deque(f, maxlen=1000)

        log = "".join(last_lines)
        return {"log": log, "message": "success", "log_file": LOG_FILE}
    except Exception as e:
        logger.error(f"获取系统日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统日志失败: {str(e)}")


# =============================================================================
# === 信息管理分组 ===
# =============================================================================


def load_info_config():
    """加载信息配置文件"""
    try:
        # 配置文件路径
        brand_file_path = (
            os.environ.get("SMART_WATER_BRAND_FILE_PATH")
            or os.environ.get("YUXI_BRAND_FILE_PATH")
            or "src/config/static/info.local.yaml"
        )
        config_path = Path(brand_file_path)

        # 检查文件是否存在
        if not config_path.exists():
            logger.debug(f"The config file {config_path} does not exist, using default config")
            config_path = Path("src/config/static/info.template.yaml")

        # 读取配置文件
        with open(config_path, encoding="utf-8") as file:
            config = yaml.safe_load(file)

        return config

    except Exception as e:
        logger.error(f"Failed to load info config: {e}")
        return get_default_info_config()


def get_default_info_config():
    """获取默认信息配置"""
    return {
        "organization": {"name": "Smart Water", "logo": "/favicon.svg", "avatar": "/avatar.jpg"},
        "branding": {
            "name": "AI 驱动的智能水利问答平台",
            "title": "AI 驱动的智能水利问答平台",
            "subtitle": "基于大模型的智能水利知识问答系统",
            "description": "基于大模型的智能水利知识问答系统",
        },
        "features": ["📚 灵活知识库", "🕸️ 知识图谱集成", "🤖 多模型支持"],
        "footer": {"copyright": "© Smart Water 2025 v1.0.0"},
    }


@system.get("/info")
async def get_info_config():
    """获取系统信息配置（公开接口，无需认证）"""
    try:
        config = load_info_config()
        return {"success": True, "data": config}
    except Exception as e:
        logger.error(f"获取信息配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取信息配置失败")


@system.post("/info/reload")
async def reload_info_config(current_user: User = Depends(get_admin_user)):
    """重新加载信息配置"""
    try:
        config = load_info_config()
        return {"success": True, "message": "配置重新加载成功", "data": config}
    except Exception as e:
        logger.error(f"重新加载信息配置失败: {e}")
        raise HTTPException(status_code=500, detail="重新加载信息配置失败")


# =============================================================================
# === OCR服务分组 ===
# =============================================================================


@system.get("/ocr/stats")
async def get_ocr_stats(current_user: User = Depends(get_admin_user)):
    """
    获取OCR服务使用统计信息
    返回各个OCR服务的处理统计和性能指标
    """
    try:
        from src.plugins._ocr import get_ocr_stats

        stats = get_ocr_stats()

        return {"status": "success", "stats": stats, "message": "OCR统计信息获取成功"}
    except Exception as e:
        logger.error(f"获取OCR统计信息失败: {str(e)}")
        return {"status": "error", "stats": {}, "message": f"获取OCR统计信息失败: {str(e)}"}


@system.get("/ocr/health")
async def check_ocr_services_health(current_user: User = Depends(get_admin_user)):
    """
    检查所有OCR服务的健康状态
    返回各个OCR服务的可用性信息
    """
    health_status = {
        "mineru_ocr": {"status": "unknown", "message": ""},
        "paddlex_ocr": {"status": "unknown", "message": ""},
    }

    # 检查 MinerU OCR 服务
    try:
        mineru_uri = os.getenv("MINERU_OCR_URI", "http://localhost:30000")
        health_url = f"{mineru_uri}/health"

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_url)
        if response.status_code == 200:
            health_status["mineru_ocr"]["status"] = "healthy"
            health_status["mineru_ocr"]["message"] = f"MinerU服务运行正常 ({mineru_uri})"
        else:
            health_status["mineru_ocr"]["status"] = "unhealthy"
            health_status["mineru_ocr"]["message"] = f"MinerU服务响应异常({mineru_uri}): {response.status_code}"
    except httpx.ConnectError:
        health_status["mineru_ocr"]["status"] = "unavailable"
        health_status["mineru_ocr"]["message"] = "MinerU服务无法连接，请检查服务是否启动"
    except httpx.TimeoutException:
        health_status["mineru_ocr"]["status"] = "timeout"
        health_status["mineru_ocr"]["message"] = "MinerU服务连接超时"
    except Exception as e:
        health_status["mineru_ocr"]["status"] = "error"
        health_status["mineru_ocr"]["message"] = f"MinerU服务检查失败: {str(e)}"

    # 检查 PaddleX OCR 服务
    try:
        paddlex_uri = os.getenv("PADDLEX_URI", "http://localhost:8080")
        health_url = f"{paddlex_uri}/health"

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_url)
        if response.status_code == 200:
            health_status["paddlex_ocr"]["status"] = "healthy"
            health_status["paddlex_ocr"]["message"] = f"PaddleX服务运行正常({paddlex_uri})"
        else:
            health_status["paddlex_ocr"]["status"] = "unhealthy"
            health_status["paddlex_ocr"]["message"] = f"PaddleX服务响应异常({paddlex_uri}): {response.status_code}"
    except httpx.ConnectError:
        health_status["paddlex_ocr"]["status"] = "unavailable"
        health_status["paddlex_ocr"]["message"] = "PaddleX服务无法连接，请检查服务是否启动({paddlex_uri})"
    except httpx.TimeoutException:
        health_status["paddlex_ocr"]["status"] = "timeout"
        health_status["paddlex_ocr"]["message"] = "PaddleX服务连接超时({paddlex_uri})"
    except Exception as e:
        health_status["paddlex_ocr"]["status"] = "error"
        health_status["paddlex_ocr"]["message"] = f"PaddleX服务检查失败: {str(e)}"

    # 计算整体健康状态
    overall_status = "healthy" if any(svc["status"] == "healthy" for svc in health_status.values()) else "unhealthy"

    return {"overall_status": overall_status, "services": health_status, "message": "OCR服务健康检查完成"}


# =============================================================================
# === 聊天模型状态检查分组 ===
# =============================================================================


@system.get("/chat-models/status")
async def get_chat_model_status(provider: str, model_name: str, current_user: User = Depends(get_admin_user)):
    """获取指定聊天模型的状态"""
    logger.debug(f"Checking chat model status: {provider}/{model_name}")
    try:
        status = await test_chat_model_status(provider, model_name)
        return {"status": status, "message": "success"}
    except Exception as e:
        logger.error(f"获取聊天模型状态失败 {provider}/{model_name}: {e}")
        return {
            "message": f"获取聊天模型状态失败: {e}",
            "status": {"provider": provider, "model_name": model_name, "status": "error", "message": str(e)},
        }


@system.get("/chat-models/all/status")
async def get_all_chat_models_status(current_user: User = Depends(get_admin_user)):
    """获取所有聊天模型的状态"""
    logger.debug("Checking all chat models status")
    try:
        status = await test_all_chat_models_status()
        return {"status": status, "message": "success"}
    except Exception as e:
        logger.error(f"获取所有聊天模型状态失败: {e}")
        return {"message": f"获取所有聊天模型状态失败: {e}", "status": {"models": {}, "total": 0, "available": 0}}


# =============================================================================
# === 大坝异常配置分组 ===
# =============================================================================

# 默认大坝异常配置
DEFAULT_DAM_EXCEPTION_CONFIG = {
    "kb_whitelist": [],  # 知识库白名单
    "graph_name": "neo4j",  # 知识图谱名称
    "exception_api_url": "https://mock.apipost.net/mock/349eac/point/getExceptInfo",  # 默认异常数据API
    "exception_api_params": {"apipost_id": "5735bd5d1c8a000", "pwd": "iwhr"},  # API参数
    "include_repair_suggestions": True,  # 是否默认包含修复建议
}

# 存储大坝异常配置的文件路径
DAM_CONFIG_FILE = Path("saves/config/dam_exception.yaml")
# 存储异常问答调用记录
DAM_QA_RECORD_FILE = Path("saves/logs/dam_exception_qa_records.jsonl")


def load_dam_exception_config() -> dict:
    """加载大坝异常配置"""
    try:
        if DAM_CONFIG_FILE.exists():
            with open(DAM_CONFIG_FILE, encoding="utf-8") as f:
                return yaml.safe_load(f) or DEFAULT_DAM_EXCEPTION_CONFIG.copy()
    except Exception as e:
        logger.error(f"加载大坝异常配置失败: {e}")
    return DEFAULT_DAM_EXCEPTION_CONFIG.copy()


def save_dam_exception_config(config_data: dict) -> bool:
    """保存大坝异常配置"""
    try:
        DAM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DAM_CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        logger.error(f"保存大坝异常配置失败: {e}")
        return False


def append_dam_exception_qa_record(record: dict[str, Any]) -> None:
    """追加写入异常问答调用记录"""
    try:
        DAM_QA_RECORD_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DAM_QA_RECORD_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"写入异常问答记录失败: {e}")


def load_dam_exception_qa_records(limit: int = 20) -> list[dict[str, Any]]:
    """读取异常问答调用记录，按时间倒序返回"""
    safe_limit = max(1, min(limit, 200))
    if not DAM_QA_RECORD_FILE.exists():
        return []

    lines = deque(maxlen=safe_limit)
    with open(DAM_QA_RECORD_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)

    records: list[dict[str, Any]] = []
    for line in reversed(lines):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def build_dam_exception_qa_prompt(question: str, context: str, include_repair_suggestions: bool) -> str:
    """构建异常问答提示词"""
    action_requirements = ""
    if include_repair_suggestions:
        action_requirements = """
请输出明确、可执行的处置方案，至少包含：
1. 立即措施（0-2小时）
2. 短期处置（24小时内）
3. 持续整改（1-7天）
每条措施写清楚执行动作、责任角色和预期效果。"""

    return f"""你将收到大坝监测异常数据摘要，请结合用户问题给出专业建议。

{context}

用户问题：{question}
{action_requirements}

请确保回答具体、可落地，优先输出操作步骤，不要泛泛而谈。"""


def build_fallback_solution(stats: dict[str, Any], exceptions: list[dict[str, Any]]) -> str:
    """模型不可用时的兜底建议"""
    total_count = stats.get("total_count", 0)
    most_severe = stats.get("most_severe") or {}
    severe_point = most_severe.get("pointName") or "未知测点"
    severe_comment = most_severe.get("comment") or "暂无评语"

    top_points = []
    for item in exceptions[:3]:
        top_points.append(
            f"- {item.get('pointName', '未知测点')}（评分: {item.get('score', '未知')}，评估: {item.get('comment', '无')}）"
        )
    points_text = "\n".join(top_points) if top_points else "- 暂无异常测点详情"

    return (
        f"当前共识别到 {total_count} 个异常测点，最严重测点为 {severe_point}（{severe_comment}）。\n"
        "建议按以下步骤处置：\n"
        "1. 立即措施（0-2小时）：复核最严重测点与同区域测点，排除传感器故障，完成现场巡检。\n"
        "2. 短期处置（24小时内）：对异常区域加密监测频次，补充人工校核数据，形成风险分级。\n"
        "3. 持续整改（1-7天）：针对重复异常测点实施专项治理并跟踪趋势，更新预警阈值。\n"
        f"重点关注测点：\n{points_text}"
    )


class DamExceptionQARequest(BaseModel):
    """异常问答请求体（供外部系统调用）"""

    question: str = Field(..., min_length=1, max_length=2000, description="异常问题")
    source_system: str = Field(default="external-system", max_length=100, description="调用来源系统标识")
    exception_api_url: str | None = Field(default=None, description="可选覆盖异常数据接口地址")
    exception_api_params: dict[str, Any] | None = Field(default=None, description="可选覆盖异常数据接口参数")
    include_repair_suggestions: bool | None = Field(default=None, description="是否要求返回修复建议")
    model_provider: str | None = Field(default=None, description="可选指定模型提供商")
    model_name: str | None = Field(default=None, description="可选指定模型名称")


@system.get("/dam-exception/config")
async def get_dam_exception_config(current_user: User = Depends(get_admin_user)):
    """获取大坝异常配置（管理员）"""
    try:
        config_data = load_dam_exception_config()
        return {"success": True, "data": config_data}
    except Exception as e:
        logger.error(f"获取大坝异常配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@system.post("/dam-exception/config")
async def update_dam_exception_config(
    kb_whitelist: list[str] = Body(None),
    graph_name: str = Body(None),
    exception_api_url: str = Body(None),
    exception_api_params: dict = Body(None),
    include_repair_suggestions: bool = Body(None),
    current_user: User = Depends(get_admin_user),
):
    """更新大坝异常配置（管理员）"""
    try:
        # 加载当前配置
        config_data = load_dam_exception_config()
        
        # 更新非空字段
        if kb_whitelist is not None:
            config_data["kb_whitelist"] = kb_whitelist
        if graph_name is not None:
            config_data["graph_name"] = graph_name
        if exception_api_url is not None:
            config_data["exception_api_url"] = exception_api_url
        if exception_api_params is not None:
            config_data["exception_api_params"] = exception_api_params
        if include_repair_suggestions is not None:
            config_data["include_repair_suggestions"] = include_repair_suggestions
        
        # 保存配置
        if save_dam_exception_config(config_data):
            return {"success": True, "message": "配置更新成功", "data": config_data}
        else:
            raise HTTPException(status_code=500, detail="保存配置失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新大坝异常配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@system.post("/dam-exception/qa")
async def ask_dam_exception_qa(request_data: DamExceptionQARequest):
    """异常问答接口（供其他系统调用）"""
    question = request_data.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="问题不能为空")

    try:
        dam_config = load_dam_exception_config()
        include_repair_suggestions = (
            request_data.include_repair_suggestions
            if request_data.include_repair_suggestions is not None
            else dam_config.get("include_repair_suggestions", True)
        )

        api_response = await dam_exception_service.fetch_exception_data(
            api_url=request_data.exception_api_url or dam_config.get("exception_api_url"),
            api_params=request_data.exception_api_params or dam_config.get("exception_api_params"),
        )
        raw_data = api_response.get("data", [])
        exceptions = dam_exception_service.parse_exceptions(raw_data)
        stats = dam_exception_service.get_summary_stats(exceptions)
        context = dam_exception_service.build_context_for_qa(exceptions)

        prompt = build_dam_exception_qa_prompt(question, context, include_repair_suggestions)
        system_prompt = (
            "你是一位资深大坝安全专家。请根据监测异常数据提供结构化、可执行的技术处置建议，"
            "回答务必具体，避免泛化描述。"
        )

        answer = ""
        generation_error = None
        try:
            model = select_model(model_provider=request_data.model_provider, model_name=request_data.model_name)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]

            loop = asyncio.get_event_loop()
            model_response = await loop.run_in_executor(None, lambda: model.call(messages, stream=False))
            answer = getattr(model_response, "content", "") or str(model_response)
        except Exception as model_error:
            generation_error = str(model_error)
            logger.warning(f"异常问答模型调用失败，使用兜底建议: {generation_error}")
            answer = build_fallback_solution(stats, exceptions)

        record_id = str(uuid.uuid4())
        record = {
            "record_id": record_id,
            "asked_at": utc_now().isoformat(),
            "source_system": request_data.source_system,
            "question": question,
            "answer": answer,
            "stats": stats,
            "exception_points_total": len(raw_data),
            "is_fallback": generation_error is not None,
            "generation_error": generation_error,
        }
        append_dam_exception_qa_record(record)

        return {
            "success": True,
            "record_id": record_id,
            "question": question,
            "answer": answer,
            "source_system": request_data.source_system,
            "asked_at": record["asked_at"],
            "stats": stats,
            "exception_points_total": len(raw_data),
            "is_fallback": generation_error is not None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"异常问答处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"异常问答处理失败: {str(e)}")


@system.get("/dam-exception/qa/records")
async def get_dam_exception_qa_records(
    limit: int = 20,
    current_user: User = Depends(get_required_user),
):
    """获取异常问答调用记录（登录后可见）"""
    try:
        records = load_dam_exception_qa_records(limit)
        return {"success": True, "records": records, "count": len(records)}
    except Exception as e:
        logger.error(f"获取异常问答记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取异常问答记录失败: {str(e)}")


@system.get("/dam-exception/knowledge-bases")
async def get_available_knowledge_bases(current_user: User = Depends(get_admin_user)):
    """获取可用的知识库列表（供管理员选择）"""
    try:
        from src import knowledge_base
        
        retrievers = knowledge_base.get_retrievers()
        kb_list = [
            {"id": db_id, "name": info.get("name", db_id)}
            for db_id, info in retrievers.items()
        ]
        return {"success": True, "knowledge_bases": kb_list}
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}")
        return {"success": False, "knowledge_bases": [], "message": str(e)}


@system.get("/dam-exception/graphs")
async def get_available_graphs(current_user: User = Depends(get_admin_user)):
    """获取可用的知识图谱列表（供管理员选择）"""
    try:
        # 默认支持的图谱
        graphs = [
            {"id": "neo4j", "name": "Neo4j知识图谱"},
        ]
        
        # 尝试获取其他配置的图谱
        try:
            from src import knowledge_base
            if hasattr(knowledge_base, 'get_graph_names'):
                extra_graphs = knowledge_base.get_graph_names()
                for g in extra_graphs:
                    if g not in [x["id"] for x in graphs]:
                        graphs.append({"id": g, "name": g})
        except Exception:
            pass
            
        return {"success": True, "graphs": graphs}
    except Exception as e:
        logger.error(f"获取图谱列表失败: {e}")
        return {"success": False, "graphs": [], "message": str(e)}


# =============================================================================
# === 模型配置管理分组 ===
# =============================================================================


@system.get("/model-config")
async def get_model_config(current_user: User = Depends(get_superadmin_user)):
    """获取所有模型配置（超级管理员）"""
    try:
        return {
            "success": True,
            "data": {
                "providers": config.model_names,
                "embed_models": config.embed_model_names,
                "rerankers": config.reranker_names,
            }
        }
    except Exception as e:
        logger.error(f"获取模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型配置失败: {str(e)}")


@system.post("/model-config/provider")
async def update_model_provider(
    provider_id: str = Body(..., description="提供商ID，如 'openai', 'deepseek'"),
    name: str = Body(..., description="显示名称"),
    base_url: str = Body(..., description="API基础URL"),
    default: str = Body(None, description="默认模型名称"),
    env: str = Body("NO_API_KEY", description="API Key环境变量名"),
    models: list[str] = Body([], description="支持的模型列表"),
    url: str = Body("", description="文档链接"),
    current_user: User = Depends(get_superadmin_user),
):
    """添加或更新聊天模型提供商（超级管理员）"""
    try:
        provider_data = {
            "name": name,
            "base_url": base_url,
            "default": default or (models[0] if models else ""),
            "env": env,
            "models": models,
        }
        if url:
            provider_data["url"] = url
            
        config.model_names[provider_id] = provider_data
        config._save_models_to_file()
        config.handle_self()  # 重新处理配置以更新状态
        
        return {"success": True, "message": f"提供商 '{provider_id}' 更新成功", "data": provider_data}
    except Exception as e:
        logger.error(f"更新模型提供商失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@system.delete("/model-config/provider/{provider_id}")
async def delete_model_provider(
    provider_id: str,
    current_user: User = Depends(get_superadmin_user),
):
    """删除聊天模型提供商（超级管理员）"""
    try:
        if provider_id not in config.model_names:
            raise HTTPException(status_code=404, detail=f"提供商 '{provider_id}' 不存在")
        
        del config.model_names[provider_id]
        config._save_models_to_file()
        config.handle_self()
        
        return {"success": True, "message": f"提供商 '{provider_id}' 删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模型提供商失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@system.post("/model-config/embed-model")
async def update_embed_model(
    model_id: str = Body(..., description="模型ID，如 'siliconflow/BAAI/bge-m3'"),
    name: str = Body(..., description="模型名称"),
    dimension: int = Body(1024, description="向量维度"),
    base_url: str = Body(..., description="API URL"),
    api_key: str = Body("NO_API_KEY", description="API Key环境变量名"),
    current_user: User = Depends(get_superadmin_user),
):
    """添加或更新Embedding模型（超级管理员）"""
    try:
        model_data = {
            "name": name,
            "dimension": dimension,
            "base_url": base_url,
            "api_key": api_key,
        }
        
        config.embed_model_names[model_id] = model_data
        config._save_models_to_file()
        
        # 更新配置项 choices
        config._config_items["embed_model"]["choices"] = list(config.embed_model_names.keys())
        
        return {"success": True, "message": f"Embedding模型 '{model_id}' 更新成功", "data": model_data}
    except Exception as e:
        logger.error(f"更新Embedding模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@system.delete("/model-config/embed-model/{model_id:path}")
async def delete_embed_model(
    model_id: str,
    current_user: User = Depends(get_superadmin_user),
):
    """删除Embedding模型（超级管理员）"""
    try:
        if model_id not in config.embed_model_names:
            raise HTTPException(status_code=404, detail=f"Embedding模型 '{model_id}' 不存在")
        
        del config.embed_model_names[model_id]
        config._save_models_to_file()
        config._config_items["embed_model"]["choices"] = list(config.embed_model_names.keys())
        
        return {"success": True, "message": f"Embedding模型 '{model_id}' 删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除Embedding模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@system.post("/model-config/reranker")
async def update_reranker(
    model_id: str = Body(..., description="模型ID，如 'siliconflow/BAAI/bge-reranker-v2-m3'"),
    name: str = Body(..., description="模型名称"),
    base_url: str = Body(..., description="API URL"),
    api_key: str = Body("NO_API_KEY", description="API Key环境变量名"),
    current_user: User = Depends(get_superadmin_user),
):
    """添加或更新Reranker模型（超级管理员）"""
    try:
        model_data = {
            "name": name,
            "base_url": base_url,
            "api_key": api_key,
        }
        
        config.reranker_names[model_id] = model_data
        config._save_models_to_file()
        
        # 更新配置项 choices
        config._config_items["reranker"]["choices"] = list(config.reranker_names.keys())
        
        return {"success": True, "message": f"Reranker模型 '{model_id}' 更新成功", "data": model_data}
    except Exception as e:
        logger.error(f"更新Reranker模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@system.delete("/model-config/reranker/{model_id:path}")
async def delete_reranker(
    model_id: str,
    current_user: User = Depends(get_superadmin_user),
):
    """删除Reranker模型（超级管理员）"""
    try:
        if model_id not in config.reranker_names:
            raise HTTPException(status_code=404, detail=f"Reranker模型 '{model_id}' 不存在")
        
        del config.reranker_names[model_id]
        config._save_models_to_file()
        config._config_items["reranker"]["choices"] = list(config.reranker_names.keys())
        
        return {"success": True, "message": f"Reranker模型 '{model_id}' 删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除Reranker模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

