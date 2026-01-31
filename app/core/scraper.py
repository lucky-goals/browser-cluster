"""
网页抓取核心模块

使用 Playwright 进行网页渲染和抓取
"""

import time
import base64
import re
import logging
from typing import Optional, Dict, Any, List
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth
from app.core.browser import browser_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


class Scraper:
    """网页抓取器"""

    async def scrape(
        self, url: str, params: Dict[str, Any], node_id: str
    ) -> Dict[str, Any]:
        """
        抓取网页内容

        Args:
            url: 目标 URL
            params: 抓取参数
            node_id: 处理节点 ID

        Returns:
            Dict: 包含状态、HTML、元数据等信息的字典
        """
        start_time = time.time()
        page = None
        context = None
        intercepted_data = {}  # 存储拦截到的接口数据

        print(f"Scraping URL: {url} with params: {params}")

        try:
            # 获取 User-Agent
            user_agent = params.get("user_agent") or settings.user_agent

            # 处理代理配置
            proxy_config = params.get("proxy")
            browser = await browser_manager.get_browser()

            # 创建浏览器上下文参数
            context_options = {"java_script_enabled": True, "user_agent": user_agent}

            if proxy_config:
                context_options["proxy"] = {
                    "server": proxy_config.get("server"),
                }
                # 添加代理认证
                if proxy_config.get("username"):
                    context_options["proxy"]["username"] = proxy_config["username"]
                if proxy_config.get("password"):
                    context_options["proxy"]["password"] = proxy_config["password"]

            # 创建新的上下文（确保 User-Agent 和 代理设置生效）
            context = await browser.new_context(**context_options)
            page = await context.new_page()

            # 设置视口大小
            if params.get("viewport"):
                await page.set_viewport_size(params["viewport"])

            # 注入反检测脚本
            if params.get("stealth", settings.stealth_mode):
                await Stealth().apply_stealth_async(page)

            # 设置接口拦截
            intercept_apis = params.get("intercept_apis", [])
            if intercept_apis:
                intercept_continue = params.get("intercept_continue", False)
                await self._setup_api_interception(
                    page, intercept_apis, intercepted_data, intercept_continue
                )

            # 拦截资源（图片、媒体等）
            if params.get("block_images", settings.block_images) or params.get(
                "block_media", settings.block_media
            ):
                await self._block_resources(page, params)

            # 获取等待策略和超时设置
            wait_for = params.get("wait_for", settings.default_wait_for)
            wait_time = params.get("wait_time", 3000)
            timeout = params.get("timeout", settings.default_timeout)

            # 导航到目标 URL
            response = None
            try:
                response = await page.goto(url, wait_until=wait_for, timeout=timeout)
            except PlaywrightTimeoutError:
                # 超时容错：如果已经有响应或页面有内容，则继续
                if not page.is_closed():
                    html_preview = await page.content()
                    if len(html_preview) > 200:  # 认为页面已经加载了部分内容
                        pass
                    else:
                        raise  # 页面内容太少，还是抛出超时异常

            # 等待特定选择器
            if params.get("selector"):
                try:
                    await page.wait_for_selector(params["selector"], timeout=timeout)
                except PlaywrightTimeoutError:
                    # 如果已经有内容，选择器超时也可以容忍
                    pass

            # 额外等待时间
            if wait_time > 0:
                await page.wait_for_timeout(wait_time)

            # 执行交互步骤 (Interaction Steps / Skills)
            interaction_steps = params.get("interaction_steps")
            skill_results = {}
            if interaction_steps:
                from app.core.skills import SKILLS_MAP
                logger.info(f"Executing {len(interaction_steps)} interaction steps")
                for i, step in enumerate(interaction_steps):
                    # 兼容模型对象或字典
                    if hasattr(step, "model_dump"):
                        step = step.model_dump()
                    
                    action = step.get("action")
                    step_params = step.get("params", {})
                    
                    if action in SKILLS_MAP:
                        logger.info(f"Executing skill: {action} with params: {step_params}")
                        skill_func = SKILLS_MAP[action]
                        skill_res = await skill_func(page, **step_params)
                        # 记录有意义的返回结果 (非布尔值或 None)
                        if skill_res not in [True, False, None]:
                            skill_results[f"{action}_{i}"] = skill_res
                    else:
                        logger.warning(f"Unknown skill action: {action}")
                
                # 交互完成后再次等待网络空闲，确保内容加载完毕
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass

            # 获取页面 HTML
            html = await page.content()
            actual_url = page.url  # 获取重定向后的实际 URL

            # 计算加载时间
            load_time = time.time() - start_time

            # 获取页面标题和状态码
            title = ""
            status_code = 0
            try:
                title = await page.title()
                if response:
                    status_code = response.status
                else:
                    # 如果 response 为空（超时），尝试从 main_frame 获取
                    status_code = 200  # 默认为 200，因为我们能拿到内容
            except:
                pass

            # 可选：截图
            screenshot = None
            if params.get("screenshot"):
                try:
                    # 使用 is_fullscreen 参数控制是否全页截图，默认 False
                    is_fullscreen = params.get("is_fullscreen", False)
                    screenshot_bytes = await page.screenshot(full_page=is_fullscreen)
                    screenshot = base64.b64encode(screenshot_bytes).decode()
                except:
                    pass

            # 返回成功结果
            result = {
                "status": "success",
                "html": html,
                "screenshot": screenshot,
                "metadata": {
                    "title": title,
                    "url": url,
                    "actual_url": actual_url,
                    "status_code": status_code,
                    "load_time": load_time,
                    "timestamp": time.time(),
                },
            }

            # 如果有拦截的接口数据，添加到结果中
            if intercepted_data:
                result["intercepted_apis"] = intercepted_data

            # 如果有技能执行结果，添加到结果中
            if skill_results:
                result["skill_results"] = skill_results

            # 如果启用了 Agent 识别，执行内容提取
            if params.get("agent_enabled") and params.get("agent_model_id"):
                # 优化：提取视觉块状内容而不是原始 HTML
                visual_content = await self._extract_visual_content(page)
                
                # 如果有技能执行结果，将其注入到内容中，方便 LLM 提取
                if skill_results:
                    skill_info = "### Skill Results ###\n"
                    for key, val in skill_results.items():
                        skill_info += f"{key}: {val}\n"
                    skill_info += "#####################\n\n"
                    visual_content = skill_info + visual_content

                agent_result = await self._run_agent_extraction(
                    content=visual_content,  # 传递处理后的内容
                    screenshot=screenshot,
                    model_id=params["agent_model_id"],
                    user_prompt=params.get("agent_prompt", ""),
                    system_prompt=params.get("agent_system_prompt"),
                )
                result["agent_result"] = agent_result
                # 将视觉内容存入结果，方便调试
                result["visual_content"] = visual_content

            return result

        except Exception as e:
            # 返回失败结果
            load_time = time.time() - start_time
            error_result = {
                "status": "failed",
                "error": {"message": str(e), "type": type(e).__name__},
                "metadata": {
                    "url": url,
                    "load_time": load_time,
                    "timestamp": time.time(),
                },
            }

            # 如果有拦截的接口数据，也添加到错误结果中
            if intercepted_data:
                error_result["intercepted_apis"] = intercepted_data

            return error_result

        finally:
            # 确保关闭页面和上下文
            if page and context:
                # 关闭上下文（会自动关闭页面）
                await context.close()
            elif page:
                # 只关闭页面
                await page.close()

    async def _setup_api_interception(
        self,
        page,
        api_patterns: List[str],
        intercepted_data: Dict[str, Any],
        continue_after_intercept: bool = False,
    ):
        """
        设置接口拦截

        Args:
            page: Playwright 页面对象
            api_patterns: 要拦截的接口 URL 模式列表（支持通配符 *）
            intercepted_data: 用于存储拦截数据的字典
            continue_after_intercept: 拦截并获取数据后，是否继续执行后续请求（默认 False）
        """

        def url_matches_pattern(url: str, pattern: str) -> bool:
            """
            检查 URL 是否匹配模式

            Args:
                url: 实际 URL
                pattern: URL 模式（支持通配符 *）

            Returns:
                bool: 是否匹配
            """
            # 将通配符 * 转换为正则表达式
            regex_pattern = pattern.replace("*", ".*")
            return re.match(regex_pattern, url) is not None

        async def route_handler(route, request):
            """路由处理函数"""
            try:
                # 检查请求 URL 是否匹配任何拦截模式
                request_url = request.url
                matched_pattern = None

                for pattern in api_patterns:
                    if url_matches_pattern(request_url, pattern):
                        matched_pattern = pattern
                        break

                if matched_pattern:
                    # 拦截请求，获取响应
                    response = await route.fetch()

                    # 获取响应数据
                    content_type = response.headers.get("content-type", "")
                    response_data = {
                        "url": request_url,
                        "method": request.method,
                        "status": response.status,
                        "headers": dict(response.headers),
                    }

                    # 尝试解析 JSON 响应
                    if "application/json" in content_type:
                        try:
                            json_data = await response.json()
                            response_data["body"] = json_data
                        except:
                            response_data["body"] = await response.text()
                    else:
                        # 非 JSON 响应，存储文本内容
                        response_data["body"] = await response.text()

                    # 存储拦截数据
                    if matched_pattern not in intercepted_data:
                        intercepted_data[matched_pattern] = []
                    intercepted_data[matched_pattern].append(response_data)

                    # 判断是否继续请求
                    if continue_after_intercept:
                        await route.continue_()
                    else:
                        # 不执行后续请求，直接中止（或可以使用 route.fulfill 返回已获取的数据，但 abort 更符合“不执行后续”的描述）
                        await route.abort()
                else:
                    # 不匹配，正常请求
                    await route.continue_()
            except Exception as e:
                # 拦截失败时继续请求
                await route.continue_()

        # 注册路由处理器
        await page.route("**/*", route_handler)

    async def _extract_visual_content(self, page) -> str:
        """
        提取页面的视觉块状内容
        通过 JavaScript 分析 DOM 元素的视觉位置，并将其按视觉顺序重组。
        """
        js_script = """
        () => {
            const results = [];
            const walk = (node) => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    const style = window.getComputedStyle(node);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                        return;
                    }
                    
                    const tagName = node.tagName.toLowerCase();
                    if (['script', 'style', 'noscript', 'iframe', 'svg'].includes(tagName)) {
                        return;
                    }

                    // 检查是否有直接的文本内容
                    let hasText = false;
                    for (const child of node.childNodes) {
                        if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
                            hasText = true;
                            break;
                        }
                    }

                    if (hasText || ['button', 'input', 'select', 'textarea', 'a'].includes(tagName)) {
                        const rect = node.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            let text = node.innerText.trim().replace(/\\n+/g, ' ');
                            
                            // 针对 <a> 标签提取 href
                            if (tagName === 'a' && node.href) {
                                const href = node.href;
                                if (text) {
                                    text = `${text} [Link: ${href}]`;
                                } else {
                                    text = `[Link: ${href}]`;
                                }
                            }

                            results.push({
                                tagName,
                                text: text,
                                x: Math.round(rect.x),
                                y: Math.round(rect.y),
                                w: Math.round(rect.width),
                                h: Math.round(rect.height)
                            });
                            return; // 已经处理了该节点的文本，不再递归其子节点（避免重复）
                        }
                    }
                }
                
                for (const child of node.childNodes) {
                    walk(child);
                }
            };

            walk(document.body);

            // 按 Y 坐标排序，然后按 X 坐标排序
            results.sort((a, b) => {
                const yDiff = a.y - b.y;
                if (Math.abs(yDiff) < 10) { // 认为在同一行
                    return a.x - b.x;
                }
                return yDiff;
            });

            // 分块聚合
            const blocks = [];
            let currentBlock = null;

            for (const item of results) {
                if (!currentBlock || Math.abs(item.y - currentBlock.y) > 15) {
                    if (currentBlock) blocks.push(currentBlock);
                    currentBlock = {
                        y: item.y,
                        texts: [item.text]
                    };
                } else {
                    currentBlock.texts.push(item.text);
                }
            }
            if (currentBlock) blocks.push(currentBlock);

            return blocks.map(b => b.texts.join(' | ')).join('\\n');
        }
        """
        try:
            content = await page.evaluate(js_script)
            return content
        except Exception as e:
            logger.error(f"Failed to extract visual content: {e}")
            return "Failed to extract visual content"

    async def _block_resources(self, page, params: Dict[str, Any]):
        """
        拦截指定类型的资源

        Args:
            page: Playwright 页面对象
            params: 抓取参数
        """

        async def route_handler(route, request):
            """路由处理函数"""
            resource_type = request.resource_type

            # 拦截图片
            if params.get("block_images") and resource_type == "image":
                await route.abort()
            # 拦截媒体资源和字体、css
            elif params.get("block_media") and resource_type in [
                "media",
                "font",
                "stylesheet",
            ]:
                await route.abort()
            # 继续加载其他资源
            else:
                await route.continue_()

        # 注册路由处理器
        await page.route("**/*", route_handler)

    async def _run_agent_extraction(
        self, content: str, screenshot: str, model_id: str, user_prompt: str, system_prompt: Optional[str] = None
    ) -> dict:
        """
        运行 Agent 内容提取

        Args:
            html: 网页 HTML 内容
            screenshot: 截图 base64 编码
            model_id: LLM 模型 ID
            user_prompt: 用户的提取要求

        Returns:
            dict: Agent 提取结果
        """
        from app.services.llm_agent import get_llm_agent
        from app.models.llm import AgentResult, AgentStatus

        try:
            agent = await get_llm_agent(model_id)
            if not agent:
                return AgentResult(
                    status=AgentStatus.FAILED,
                    error=f"Model {model_id} not found or disabled",
                ).model_dump()

            result = await agent.extract_content(
                content=content,
                screenshot_base64=screenshot,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
            )
            return result.model_dump()

        except Exception as e:
            return AgentResult(status=AgentStatus.FAILED, error=str(e)).model_dump()


# 全局抓取器实例
scraper = Scraper()
