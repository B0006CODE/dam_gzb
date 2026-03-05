import os
import time
from collections import defaultdict

from src.utils import logger

GOLBAL_STATE = {}

# OCR服务监控统计
OCR_STATS = {"requests": defaultdict(int), "failures": defaultdict(int), "service_status": defaultdict(str)}


def log_ocr_request(service_name: str, file_path: str, success: bool, processing_time: float, error_msg: str = None):
    """记录OCR请求统计信息"""
    # 更新统计
    OCR_STATS["requests"][service_name] += 1

    if not success:
        OCR_STATS["failures"][service_name] += 1
        OCR_STATS["service_status"][service_name] = "error"
        logger.error(f"OCR失败 - {service_name}: {os.path.basename(file_path)} - {error_msg}")
    else:
        OCR_STATS["service_status"][service_name] = "healthy"
        logger.info(f"OCR成功 - {service_name}: {os.path.basename(file_path)}")


def get_ocr_stats():
    """获取OCR服务统计信息"""
    stats = {}
    for service in OCR_STATS["requests"]:
        success_count = OCR_STATS["requests"][service] - OCR_STATS["failures"][service]
        success_rate = (success_count / OCR_STATS["requests"][service]) if OCR_STATS["requests"][service] > 0 else 0

        stats[service] = {
            "total_requests": OCR_STATS["requests"][service],
            "success_count": success_count,
            "failure_count": OCR_STATS["failures"][service],
            "success_rate": f"{success_rate:.2%}",
            "status": OCR_STATS["service_status"][service],
        }

    return stats


class OCRServiceException(Exception):
    """OCR服务异常"""

    def __init__(self, message, service_name=None, status_code=None):
        super().__init__(message)
        self.service_name = service_name
        self.status_code = status_code


class OCRPlugin:
    """OCR 插件"""

    def __init__(self, **kwargs):
        _ = kwargs

    def process_file_mineru(self, file_path, params=None):
        """
        使用Mineru OCR处理文件
        :param file_path: 文件路径
        :param params: 参数
        :return: 提取的文本
        """
        import requests

        from .mineru import parse_doc

        mineru_ocr_uri = os.getenv("MINERU_OCR_URI", "http://localhost:30000")
        mineru_ocr_uri_health = f"{mineru_ocr_uri}/health"

        try:
            # 健康检查
            health_check_response = requests.get(mineru_ocr_uri_health, timeout=5)
            if health_check_response.status_code != 200:
                error_detail = "Unknown error"
                try:
                    error_detail = health_check_response.json()
                except Exception:
                    error_detail = health_check_response.text

                raise OCRServiceException(
                    f"MinerU OCR服务健康检查失败: {error_detail}", "mineru_ocr", "health_check_failed"
                )

        except Exception as e:
            if isinstance(e, OCRServiceException):
                raise
            raise OCRServiceException(f"MinerU OCR服务检查失败: {str(e)}", "mineru_ocr", "service_error")

        try:
            start_time = time.time()
            file_path_list = [file_path]
            output_dir = os.path.join(os.getcwd(), "tmp", "mineru_ocr")

            backend = os.getenv("MINERU_BACKEND", "pipeline")
            text = parse_doc(file_path_list, output_dir, backend=backend, server_url=mineru_ocr_uri)[0]

            processing_time = time.time() - start_time
            log_ocr_request("mineru_ocr", file_path, True, processing_time)

            logger.debug(f"Mineru OCR result: {text[:50]}(...) total {len(text)} characters.")
            return text

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"MinerU OCR处理失败: {str(e)}"
            log_ocr_request("mineru_ocr", file_path, False, processing_time, error_msg)

            raise OCRServiceException(error_msg, "mineru_ocr", "processing_failed")

    def process_file_paddlex(self, file_path, params=None):
        """
        使用Paddlex OCR处理文件
        :param file_path: 文件路径
        :param params: 参数
        :return: 提取的文本
        """
        from .paddlex import analyze_document, check_paddlex_health

        paddlex_uri = os.getenv("PADDLEX_URI", "http://localhost:8080")

        try:
            # 健康检查
            health_check_response = check_paddlex_health(paddlex_uri)
            if not health_check_response.ok:
                error_detail = "Unknown error"
                try:
                    error_detail = health_check_response.json()
                except Exception:
                    error_detail = health_check_response.text

                raise OCRServiceException(
                    f"PaddleX OCR服务健康检查失败: {error_detail}", "paddlex_ocr", "health_check_failed"
                )
        except Exception as e:
            if isinstance(e, OCRServiceException):
                raise
            raise OCRServiceException(f"PaddleX OCR服务检查失败: {str(e)}", "paddlex_ocr", "service_error")

        try:
            start_time = time.time()
            result = analyze_document(file_path, base_url=paddlex_uri)
            processing_time = time.time() - start_time

            if not result["success"]:
                error_msg = f"PaddleX OCR处理失败: {result['error']}"
                log_ocr_request("paddlex_ocr", file_path, False, processing_time, error_msg)

                raise OCRServiceException(error_msg, "paddlex_ocr", "processing_failed")

            log_ocr_request("paddlex_ocr", file_path, True, processing_time)
            return result["full_text"]

        except Exception as e:
            if isinstance(e, OCRServiceException):
                raise
            processing_time = time.time() - start_time if "start_time" in locals() else 0
            error_msg = f"PaddleX OCR处理失败: {str(e)}"
            log_ocr_request("paddlex_ocr", file_path, False, processing_time, error_msg)

            raise OCRServiceException(error_msg, "paddlex_ocr", "processing_failed")


def get_state(task_id):
    return GOLBAL_STATE.get(task_id, {})


def plainreader(file_path):
    """读取普通文本文件并返回text文本"""
    assert os.path.exists(file_path), "File not found"

    with open(file_path) as f:
        text = f.read()
    return text
