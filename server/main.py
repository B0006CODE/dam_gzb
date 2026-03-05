import asyncio
import os
import time
from collections import defaultdict, deque

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from server.routers import router
from server.services.tasker import tasker
from server.utils.auth_middleware import is_public_path
from server.utils.common_utils import setup_logging
from src.utils.logging_config import logger

# 设置日志配置
setup_logging()

# 环境配置
ENV = os.getenv("ENV", "development")
IS_PRODUCTION = ENV == "production"

RATE_LIMIT_MAX_ATTEMPTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_ENDPOINTS = {("/api/auth/token", "POST")}

# In-memory login attempt tracker to reduce brute-force exposure per worker
_login_attempts: defaultdict[str, deque[float]] = defaultdict(deque)
_attempt_lock = asyncio.Lock()

app = FastAPI(
    title="HydroBrain API",
    docs_url=None if IS_PRODUCTION else "/docs",  # 生产环境禁用文档
    redoc_url=None if IS_PRODUCTION else "/redoc",
)
app.include_router(router, prefix="/api")

# CORS 设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# 请求日志中间件
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录所有API请求的时间和状态"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = _extract_client_ip(request)
        
        # 记录请求开始
        request_id = f"{int(start_time * 1000)}"
        
        try:
            response = await call_next(request)
            
            # 计算请求时间
            process_time = (time.time() - start_time) * 1000  # ms
            
            # 记录请求日志（仅API请求且非健康检查）
            if request.url.path.startswith("/api") and request.url.path not in ["/api/system/health", "/api"]:
                log_level = "warning" if response.status_code >= 400 else "info"
                log_msg = (
                    f"[{request_id}] {request.method} {request.url.path} "
                    f"- {response.status_code} - {process_time:.2f}ms - {client_ip}"
                )
                if log_level == "warning":
                    logger.warning(log_msg)
                else:
                    logger.info(log_msg)
            
            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            
            return response
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"- ERROR - {process_time:.2f}ms - {client_ip}: {str(e)}"
            )
            raise


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        normalized_path = request.url.path.rstrip("/") or "/"
        request_signature = (normalized_path, request.method.upper())

        if request_signature in RATE_LIMIT_ENDPOINTS:
            client_ip = _extract_client_ip(request)
            now = time.monotonic()

            async with _attempt_lock:
                attempt_history = _login_attempts[client_ip]

                while attempt_history and now - attempt_history[0] > RATE_LIMIT_WINDOW_SECONDS:
                    attempt_history.popleft()

                if len(attempt_history) >= RATE_LIMIT_MAX_ATTEMPTS:
                    retry_after = int(max(1, RATE_LIMIT_WINDOW_SECONDS - (now - attempt_history[0])))
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "登录尝试过于频繁，请稍后再试"},
                        headers={"Retry-After": str(retry_after)},
                    )

                attempt_history.append(now)

            response = await call_next(request)

            if response.status_code < 400:
                async with _attempt_lock:
                    _login_attempts.pop(client_ip, None)

            return response

        return await call_next(request)


# 鉴权中间件
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 获取请求路径
        path = request.url.path

        # 检查是否为公开路径，公开路径无需身份验证
        if is_public_path(path):
            return await call_next(request)

        if not path.startswith("/api"):
            # 非API路径，可能是前端路由或静态资源
            return await call_next(request)

        # 继续处理请求
        return await call_next(request)


# 添加中间件（顺序很重要：最后添加的最先执行）
app.add_middleware(RequestLoggingMiddleware)  # 最外层：记录所有请求
app.add_middleware(LoginRateLimitMiddleware)
app.add_middleware(AuthMiddleware)


@app.on_event("startup")
async def start_tasker() -> None:
    logger.info(f"Starting server in {ENV} mode...")
    await tasker.start()


@app.on_event("shutdown")
async def stop_tasker() -> None:
    logger.info("Shutting down server...")
    await tasker.shutdown()


if __name__ == "__main__":
    # 根据环境配置uvicorn参数
    import multiprocessing
    
    # 生产配置
    if IS_PRODUCTION:
        # 生产环境：使用多个workers，禁用reload
        workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2 + 1))
        uvicorn.run(
            "server.main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 5050)),
            workers=workers,
            reload=False,
            access_log=True,
            log_level="info",
        )
    else:
        # 开发环境：单worker，启用reload方便开发
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(os.getenv("PORT", 5050)),
            reload=True,
            log_level="debug",
        )

