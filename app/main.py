"""FastAPI 应用入口、路由注册和进程生命周期。"""

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager

# Windows 下 Playwright 需要 ProactorEventLoop。
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    admin,
    auth,
    backup,
    cookies,
    llm,
    nodes,
    prompt_template,
    proxy,
    proxies,
    rules,
    schedules,
    scrape,
    scrapers,
    skill_bundles,
    skills,
    stats,
    tasks,
    users,
    workflows,
)
from app.core.browser import browser_manager
from app.core.config import settings
from app.core.drission_browser import drission_manager
from app.core.logger import setup_logging
from app.core.scheduler import scraper_scheduler
from app.db.mongo import mongo
from app.db.redis import redis_client
from app.services.cookie_service import cookie_service
from app.services.node_manager import node_manager
from app.services.proxy_service import proxy_service
from app.services.scheduler_service import scheduler_service

setup_logging()
logger = logging.getLogger(__name__)


async def browser_idle_check() -> None:
    """定期回收长时间空闲的 Playwright/DrissionPage 实例。"""
    logger.info("Starting background browser idle check loop...")
    while True:
        try:
            await asyncio.to_thread(
                drission_manager.check_idle, timeout=settings.browser_idle_timeout
            )
            await browser_manager.check_idle_browser()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Error in browser_idle_check: %s", exc)
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """初始化数据库、调度器和遗留运行节点，并在关闭时释放资源。"""
    loop = asyncio.get_running_loop()
    logger.info("Lifespan startup. Current event loop: %s", type(loop).__name__)

    settings.load_from_db()
    mongo.connect()
    redis_client.connect_cache()

    # 管理后台所需的默认数据必须在路由可用前准备好。
    try:
        from scripts.init_admin import init_admin

        init_admin()
    except Exception as exc:
        logger.error("Failed to initialize admin user: %s", exc)
    try:
        from scripts.init_skills import init_skills

        await init_skills()
    except Exception as exc:
        logger.error("Failed to initialize skills: %s", exc)

    await node_manager.auto_start_nodes()
    proxy_service.register_config_callback(scheduler_service.refresh_system_jobs)
    cookie_service.register_config_callback(scheduler_service.refresh_system_jobs)
    scheduler_service.start()
    scraper_scheduler.start()
    idle_task = asyncio.create_task(browser_idle_check())

    try:
        yield
    finally:
        logger.info("Lifespan shutdown. Cleaning up...")
        idle_task.cancel()
        await asyncio.gather(idle_task, return_exceptions=True)
        await node_manager.stop_all_nodes()
        scheduler_service.stop()
        try:
            if scraper_scheduler.scheduler.running:
                scraper_scheduler.scheduler.shutdown(wait=False)
        except Exception as exc:
            logger.warning("Failed to stop scraper scheduler: %s", exc)
        mongo.close()
        redis_client.close_all()
        logger.info("Cleanup complete.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Playwright-based distributed browser cluster",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestLogMiddleware:
    """记录每个 HTTP 请求的状态码和处理耗时。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        start_time = time.time()
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        method = scope.get("method")
        path = scope.get("path")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                process_time = time.time() - start_time
                logger.info(
                    "API访问日志 | %s | %s %s | %s | %.3fs",
                    client_ip,
                    method,
                    path,
                    message["status"],
                    process_time,
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(RequestLogMiddleware)

# Core APIs
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(scrape.router)
app.include_router(tasks.router)
app.include_router(stats.router)
app.include_router(admin.router)
app.include_router(nodes.router)

# Fork-specific LLM, prompt, skill, backup and Mongo proxy APIs.
app.include_router(llm.router)
app.include_router(prompt_template.router)
app.include_router(proxies.router)
app.include_router(skills.router)
app.include_router(skill_bundles.router)
app.include_router(backup.router)

# Upstream parser, scheduler, pool and workflow APIs.
app.include_router(rules.router)
app.include_router(schedules.router)
app.include_router(proxy.router)
app.include_router(scrapers.router)
app.include_router(cookies.router)
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflows"])

os.makedirs("screenshots", exist_ok=True)
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")


@app.get("/api")
async def root():
    return {"name": settings.app_name, "version": settings.app_version, "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


static_dir = "static"
if not os.path.exists(static_dir) and os.path.exists("admin/dist"):
    static_dir = "admin/dist"

if os.path.exists(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return {"error": "Not Found", "status": 404}
        file_path = os.path.join(static_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn

    # 项目约定关闭热重载，避免重复启动浏览器、调度器和 Worker 线程。
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        loop="asyncio",
        workers=1,
    )
