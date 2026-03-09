"""大坝监测异常数据服务

提供获取、解析和处理大坝监测异常数据的功能。
"""

import json
import re
import httpx
from typing import Any

from src.utils.logging_config import logger


class DamExceptionService:
    """大坝异常数据服务"""

    # 默认异常数据API地址
    DEFAULT_API_URL = "https://iiot.cypc.com.cn/damIMonitorApi/yxy/point/getExceptInfo"
    DEFAULT_API_PARAMS: dict[str, Any] = {}

    # 异常评估关键词
    EXCEPTION_KEYWORDS = ["异常", "轻微异常", "严重异常", "未找到对应的指标数据"]

    # 正常评分阈值
    NORMAL_SCORE_THRESHOLD = 10.0

    @classmethod
    def _to_float(cls, value: Any, default: float = 5.0) -> float:
        """将任意值安全转换为 float。"""
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _normalize_exception_item(cls, item: Any, idx: int = 0) -> dict[str, Any] | None:
        """将单条异常数据标准化为统一结构。"""
        if isinstance(item, str):
            text = item.strip()
            if not text:
                return None
            return {
                "id": f"text-{idx}",
                "time": None,
                "pointName": f"文本异常-{idx + 1}",
                "instrumentName": "未知仪器",
                "area": "未知区域",
                "locationTypeName": "未知位置",
                "v": None,
                "score": 5.0,
                "acomment": text[:200],
                "acommentSource": "text",
                "zcoordinate": None,
            }

        if not isinstance(item, dict):
            return None

        point_name = (
            item.get("pointName")
            or item.get("point_name")
            or item.get("point")
            or item.get("name")
            or item.get("id")
        )
        score = cls._to_float(item.get("score"), default=5.0)
        comment = (
            item.get("acomment")
            or item.get("comment")
            or item.get("assessment")
            or "轻微异常，待核查"
        )
        value = item.get("v", item.get("value"))

        normalized = {
            "id": item.get("id", f"item-{idx}"),
            "time": item.get("time"),
            "pointName": point_name or f"未知测点-{idx + 1}",
            "instrumentName": item.get("instrumentName", item.get("instrument_name", "未知仪器")),
            "area": item.get("area", "未知区域"),
            "locationTypeName": item.get("locationTypeName", item.get("location_type_name", "未知位置")),
            "v": value,
            "score": score,
            "acomment": comment,
            "acommentSource": item.get("acommentSource", item.get("commentSource", "normalized")),
            "zcoordinate": item.get("zcoordinate"),
        }
        return normalized

    @classmethod
    def _parse_exception_text(cls, text: str) -> list[dict[str, Any]]:
        """解析文本化异常数据，尽量提取测点、测值和区域。"""
        normalized: list[dict[str, Any]] = []
        if not text:
            return normalized

        sentence_splits = [seg.strip() for seg in re.split(r"[。\n]+", text) if seg.strip()]
        point_pattern = re.compile(r"([A-Za-z0-9#_-]+)测值为(-?\d+(?:\.\d+)?)mm")
        area_pattern = re.compile(r"位于(.+?)下")
        instrument_pattern = re.compile(r"的([^:：]+?)类型")

        item_index = 0
        for sentence in sentence_splits:
            area_match = area_pattern.search(sentence)
            instrument_match = instrument_pattern.search(sentence)
            area = area_match.group(1) if area_match else "未知区域"
            instrument_name = instrument_match.group(1) if instrument_match else "未知仪器"
            comment = "轻微异常，待核查"
            if "严重异常" in sentence:
                comment = "严重异常，建议立即处置"
            elif "轻微异常" in sentence:
                comment = "轻微异常，建议重点关注趋势变化"
            elif "异常" in sentence:
                comment = "存在异常，建议复核"

            matches = list(point_pattern.finditer(sentence))
            for match in matches:
                item_index += 1
                point_name = match.group(1)
                value_raw = match.group(2)
                score = 4.0 if "严重异常" in comment else 5.5
                normalized.append(
                    {
                        "id": f"text-{item_index}",
                        "time": None,
                        "pointName": point_name,
                        "instrumentName": instrument_name,
                        "area": area,
                        "locationTypeName": "文本解析",
                        "v": f"{value_raw}mm",
                        "score": score,
                        "acomment": comment,
                        "acommentSource": "text-parser",
                        "zcoordinate": None,
                    }
                )

        if normalized:
            return normalized

        # 文本无法提取结构化测点时，至少生成一条，避免上游流程中断
        fallback_text = text[:200]
        return [
            {
                "id": "text-fallback-1",
                "time": None,
                "pointName": "文本异常-1",
                "instrumentName": "未知仪器",
                "area": "未知区域",
                "locationTypeName": "文本解析",
                "v": None,
                "score": 5.0,
                "acomment": fallback_text,
                "acommentSource": "text-parser",
                "zcoordinate": None,
            }
        ]

    @classmethod
    def normalize_exception_data(cls, raw_data: Any) -> list[dict[str, Any]]:
        """将异常数据统一标准化为 list[dict]。"""
        if raw_data is None:
            return []

        if isinstance(raw_data, list):
            normalized: list[dict[str, Any]] = []
            for idx, item in enumerate(raw_data):
                normalized_item = cls._normalize_exception_item(item, idx=idx)
                if normalized_item:
                    normalized.append(normalized_item)
            return normalized

        if isinstance(raw_data, dict):
            if "data" in raw_data and raw_data["data"] is not raw_data:
                return cls.normalize_exception_data(raw_data["data"])

            normalized_item = cls._normalize_exception_item(raw_data, idx=0)
            return [normalized_item] if normalized_item else []

        if isinstance(raw_data, str):
            text = raw_data.strip()
            if not text:
                return []
            try:
                parsed = json.loads(text)
                return cls.normalize_exception_data(parsed)
            except json.JSONDecodeError:
                return cls._parse_exception_text(text)

        return []

    @classmethod
    async def fetch_exception_data(
        cls,
        api_url: str = None,
        api_params: dict = None,
        api_headers: dict | None = None,
        timeout: float = 30.0
    ) -> dict:
        """获取大坝异常监测数据

        Args:
            api_url: API地址，默认使用DEFAULT_API_URL
            api_params: API参数，默认使用DEFAULT_API_PARAMS
            api_headers: 额外请求头
            timeout: 请求超时时间（秒）

        Returns:
            API响应数据
        """
        url = api_url or cls.DEFAULT_API_URL
        params = api_params or cls.DEFAULT_API_PARAMS
        headers = api_headers or {}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.error(f"获取大坝异常数据超时: {url}")
            raise ValueError("获取大坝异常数据超时，请稍后重试")
        except httpx.HTTPStatusError as e:
            logger.error(f"获取大坝异常数据HTTP错误: {e.response.status_code}")
            raise ValueError(f"获取大坝异常数据失败，HTTP状态码: {e.response.status_code}")
        except Exception as e:
            logger.error(f"获取大坝异常数据失败: {e}")
            raise ValueError(f"获取大坝异常数据失败: {str(e)}")

    @classmethod
    def parse_exceptions(cls, data: list[dict]) -> list[dict]:
        """解析异常数据，筛选出真正有问题的测点

        Args:
            data: 原始监测数据列表

        Returns:
            异常测点列表
        """
        exceptions = []

        for item in data:
            acomment = item.get("acomment", "")
            score = item.get("score", 10)

            # 判断是否异常：评论包含异常关键词 或 评分低于阈值
            is_exception = False
            for keyword in cls.EXCEPTION_KEYWORDS:
                if keyword in acomment:
                    is_exception = True
                    break

            if score < cls.NORMAL_SCORE_THRESHOLD:
                is_exception = True

            if is_exception:
                exceptions.append({
                    "id": item.get("id"),
                    "time": item.get("time"),
                    "pointName": item.get("pointName"),
                    "instrumentName": item.get("instrumentName"),
                    "area": item.get("area"),
                    "locationTypeName": item.get("locationTypeName"),
                    "value": item.get("v"),
                    "score": score,
                    "comment": acomment,
                    "commentSource": item.get("acommentSource"),
                    "zcoordinate": item.get("zcoordinate"),
                })

        # 按评分升序排列（异常越严重排越前）
        exceptions.sort(key=lambda x: x.get("score", 10))

        return exceptions

    @classmethod
    def build_context_for_qa(cls, exceptions: list[dict], max_items: int = 20) -> str:
        """构建用于问答的上下文

        Args:
            exceptions: 异常测点列表
            max_items: 最大显示条目数

        Returns:
            格式化的上下文文本
        """
        if not exceptions:
            return "当前监测数据显示：所有测点状态正常，未发现异常情况。"

        # 统计信息
        total_count = len(exceptions)

        # 按仪器类型分组统计
        instrument_stats = {}
        for item in exceptions:
            inst = item.get("instrumentName", "未知")
            instrument_stats[inst] = instrument_stats.get(inst, 0) + 1

        # 按区域分组统计
        area_stats = {}
        for item in exceptions:
            area = item.get("area", "未知")
            area_stats[area] = area_stats.get(area, 0) + 1

        # 构建上下文
        lines = [
            "【大坝监测异常数据摘要】",
            f"共发现 {total_count} 个异常测点。",
            "",
            "【按仪器类型统计】",
        ]

        for inst, count in sorted(instrument_stats.items(), key=lambda x: -x[1]):
            lines.append(f"  - {inst}: {count} 个")

        lines.append("")
        lines.append("【按区域统计】")

        for area, count in sorted(area_stats.items(), key=lambda x: -x[1]):
            lines.append(f"  - {area}: {count} 个")

        lines.append("")
        lines.append("【异常测点详情】（按严重程度排序）")

        for i, item in enumerate(exceptions[:max_items], 1):
            lines.append(
                f"  {i}. 测点【{item.get('pointName')}】"
                f"- {item.get('instrumentName')}"
                f" @ {item.get('area')}/{item.get('locationTypeName')}"
                f" | 测量值: {item.get('value')}"
                f" | 评分: {item.get('score')}"
                f" | 评估: {item.get('comment')}"
            )
            if item.get("commentSource"):
                lines[-1] += f" ({item.get('commentSource')})"

        if total_count > max_items:
            lines.append(f"  ... 还有 {total_count - max_items} 个异常测点未显示")

        return "\n".join(lines)

    @classmethod
    def get_summary_stats(cls, exceptions: list[dict]) -> dict[str, Any]:
        """获取异常数据的统计摘要

        Args:
            exceptions: 异常测点列表

        Returns:
            统计信息字典
        """
        if not exceptions:
            return {
                "total_count": 0,
                "by_instrument": {},
                "by_area": {},
                "most_severe": None,
            }

        # 按仪器类型分组
        by_instrument = {}
        for item in exceptions:
            inst = item.get("instrumentName", "未知")
            by_instrument[inst] = by_instrument.get(inst, 0) + 1

        # 按区域分组
        by_area = {}
        for item in exceptions:
            area = item.get("area", "未知")
            by_area[area] = by_area.get(area, 0) + 1

        return {
            "total_count": len(exceptions),
            "by_instrument": by_instrument,
            "by_area": by_area,
            "most_severe": exceptions[0] if exceptions else None,
        }


# 全局服务实例
dam_exception_service = DamExceptionService()
