"""大坝监测异常数据服务

提供获取、解析和处理大坝监测异常数据的功能。
"""

import httpx
from typing import Any

from src.utils.logging_config import logger


class DamExceptionService:
    """大坝异常数据服务"""
    
    # 默认异常数据API地址
    DEFAULT_API_URL = "https://mock.apipost.net/mock/349eac/point/getExceptInfo"
    DEFAULT_API_PARAMS = {"apipost_id": "5735bd5d1c8a000", "pwd": "iwhr"}
    
    # 异常评估关键词
    EXCEPTION_KEYWORDS = ["异常", "轻微异常", "严重异常", "未找到对应的指标数据"]
    
    # 正常评分阈值
    NORMAL_SCORE_THRESHOLD = 10.0
    
    @classmethod
    async def fetch_exception_data(
        cls,
        api_url: str = None,
        api_params: dict = None,
        timeout: float = 30.0
    ) -> dict:
        """获取大坝异常监测数据
        
        Args:
            api_url: API地址，默认使用DEFAULT_API_URL
            api_params: API参数，默认使用DEFAULT_API_PARAMS
            timeout: 请求超时时间（秒）
            
        Returns:
            API响应数据
        """
        url = api_url or cls.DEFAULT_API_URL
        params = api_params or cls.DEFAULT_API_PARAMS
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params)
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
            f"【大坝监测异常数据摘要】",
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
