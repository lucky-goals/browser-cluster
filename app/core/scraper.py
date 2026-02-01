"""
网页抓取核心模块

使用 Playwright 进行网页渲染和抓取
"""

import time
import base64
import re
import logging
import asyncio
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

        # 设置缓存标志
        html_cached = False
        agent_cached = False
        
        # 结果初始化
        result = {}

        try:
            # 1. 检查网页抓取缓存 (HTML Cache)
            from app.services.cache_service import cache_service
            if params.get("cache_enabled", settings.cache_enabled):
                cached_html = await cache_service.get_html(url, params)
                if cached_html:
                    logger.info(f"HTML cache hit for URL: {url}")
                    html_cached = True
                    # 使用缓存数据
                    result = {
                        "status": "success",
                        "html": cached_html.get("html"),
                        "screenshot": cached_html.get("screenshot"),
                        "metadata": cached_html.get("metadata"),
                        "intercepted_apis": cached_html.get("intercepted_apis"),
                        "skill_results": cached_html.get("skill_results"),
                        "visual_content": cached_html.get("visual_content"),
                    }
                    # 补充必要的上下文变量以便后续 AI 提取使用
                    screenshot = result["screenshot"]
                    visual_content = result.get("visual_content")
                    skill_results = result.get("skill_results") or {}
                    interaction_steps = params.get("interaction_steps")
                    # 如果缓存里没有 visual_content，可能需要后续补充（向下兼容）
            
            # 2. 如果没命中 HTML 缓存，执行真实抓取
            if not html_cached:
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
                    from app.core.skills import SKILLS_MAP, BrowserSkills
                    logger.info(f"Executing {len(interaction_steps)} interaction steps")
                    for i, step in enumerate(interaction_steps):
                        # 兼容模型对象或字典
                        if hasattr(step, "model_dump"):
                            step = step.model_dump()
                        
                        action = step.get("action")
                        step_params = step.get("params", {})
                        
                        if action in SKILLS_MAP:
                            logger.info(f"Executing built-in skill: {action} with params: {step_params}")
                            skill_func = SKILLS_MAP[action]
                            skill_res = await skill_func(page, **step_params)
                        else:
                            # 尝试从数据库加载动态技能
                            logger.info(f"Skill '{action}' not in built-in map, trying dynamic skill")
                            skill_res = await BrowserSkills.execute_dynamic_skill(page, action, **step_params)
                        
                        # 记录有意义的返回结果 (非布尔值或 None)
                        if skill_res not in [True, False, None]:
                            skill_results[f"{action}_{i}"] = skill_res
                    
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
                
                # 提取视觉块状内容 (用于 AI 识别和缓存)
                # 注意：这里需要根据交互步骤中的 selector 提取
                container_selector = None
                exclude_selectors = None
                if interaction_steps:
                    for step in interaction_steps:
                        if hasattr(step, "model_dump"): step = step.model_dump()
                        if step.get("action") == "block_container":
                            container_selector = step.get("params", {}).get("selector")
                        elif step.get("action") == "exclude_elements":
                            exclude_selectors = step.get("params", {}).get("selectors")

                visual_content = await self._extract_visual_content(
                    page, 
                    container_selector=container_selector, 
                    exclude_selectors=exclude_selectors
                )

                # 构建成功结果 (Scraping 部分)
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
                    "skill_results": skill_results,
                    "visual_content": visual_content,
                }

                if intercepted_data:
                    result["intercepted_apis"] = intercepted_data

                # 保存 HTML 缓存 (仅当抓取成功且 visual_content 不含错误时)
                if params.get("cache_enabled", settings.cache_enabled):
                    # 检查 visual_content 是否包含错误信息
                    should_cache = True
                    if visual_content and isinstance(visual_content, str):
                        if "Failed to extract" in visual_content or "Error" in visual_content:
                            should_cache = False
                            logger.warning(f"Skipping HTML cache due to failed visual content extraction")
                    
                    if should_cache:
                        ttl = params.get("cache", {}).get("ttl")
                        await cache_service.set_html(url, params, result, ttl=ttl)

            # 如果有拦截的接口数据，添加到结果中
            if intercepted_data:
                result["intercepted_apis"] = intercepted_data

            # 如果有技能执行结果，添加到结果中
            if skill_results:
                result["skill_results"] = skill_results

            # 如果启用了 Agent 识别，执行内容提取
            if params.get("agent_enabled") and params.get("agent_model_id"):
                # 提取交互步骤中的特殊技能参数 (用于内容提取配置)
                container_selector = None
                exclude_selectors_list = []
                interaction_steps_dicts = []
                if interaction_steps:
                    for step in interaction_steps:
                        if hasattr(step, "model_dump"):
                            step = step.model_dump()
                        interaction_steps_dicts.append(step)
                        
                        action = step.get("action")
                        s_params = step.get("params", {})
                        if action == "block_container":
                            container_selector = s_params.get("selector")
                        elif action == "exclude_elements":
                            s_list = s_params.get("selectors", "")
                            if s_list:
                                exclude_selectors_list.extend([s.strip() for s in s_list.split(";") if s.strip()])
                
                interaction_steps = interaction_steps_dicts
                exclude_selectors = ";".join(exclude_selectors_list) if exclude_selectors_list else None

                # 优化：提取视觉块状内容 (仅当没有从缓存获取到时)
                if not visual_content:
                    visual_content = await self._extract_visual_content(
                        page, 
                        container_selector=container_selector, 
                        exclude_selectors=exclude_selectors
                    )
                
                # 如果有技能执行结果，将其注入到内容中，方便 LLM 提取
                if skill_results:
                    skill_info = "### Skill Results ###\n"
                    for key, val in skill_results.items():
                        skill_info += f"{key}: {val}\n"
                    skill_info += "#####################\n\n"
                    visual_content = skill_info + visual_content

                agent_result = None
                
                # 如果启用了并行提取
                if params.get("agent_parallel_enabled"):
                    batch_size = params.get("agent_parallel_batch_size") or 10
                    
                    header_content = ""
                    main_content = visual_content
                    if "### Skill Results ###" in visual_content:
                        parts = visual_content.split("#####################\n\n", 1)
                        if len(parts) == 2:
                            header_content = parts[0] + "#####################\n\n"
                            main_content = parts[1]
                    
                    items = main_content.split("\n------\n")
                    # 过滤空块
                    items = [item.strip() for item in items if item.strip()]
                    chunks = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
                    
                    logger.info(f"Parallel extraction enabled. Total items: {len(items)}, Chunks: {len(chunks)}, Batch size: {batch_size}")
                    
                    extract_tasks = []
                    for chunk in chunks:
                        chunk_content = header_content + "\n------\n".join(chunk)
                        extract_tasks.append(self._run_agent_extraction(
                            content=chunk_content,
                            screenshot=screenshot,
                            model_id=params["agent_model_id"],
                            user_prompt=params.get("agent_prompt", ""),
                            system_prompt=params.get("agent_system_prompt"),
                            skills=[step.get("action") for step in interaction_steps] if interaction_steps else None
                        ))
                    
                    chunk_results = await asyncio.gather(*extract_tasks)
                    
                    # 合并结果
                    merged_extracted_items = []
                    merged_raw_response = ""
                    total_prompt_tokens = 0
                    total_completion_tokens = 0
                    max_processing_time = 0
                    used_model_id = params.get("agent_model_id")
                    used_model_name = None
                    success_count = 0
                    status = "success"
                    error_msg = None
                    
                    total_cache_hits = 0
                    
                    for i, res in enumerate(chunk_results):
                        # 获取使用的模型信息 (无论成功失败都尝试获取)
                        if not used_model_name and res.get("model_name"):
                            used_model_name = res.get("model_name")
                        if res.get("model_id"):
                            used_model_id = res.get("model_id")

                        if res.get("status") == "success":
                            success_count += 1
                            if res.get("extracted_items"):
                                merged_extracted_items.extend(res["extracted_items"])
                            merged_raw_response += f"--- Chunk {i+1} (Success) ---\n{res.get('raw_response', '')}\n\n"
                        else:
                            error_detail = res.get("error") or "Unknown error"
                            logger.error(f"Chunk {i+1} extraction failed: {error_detail}")
                            error_msg = error_detail
                            merged_raw_response += f"--- Chunk {i+1} (Failed) ---\nError: {error_detail}\n\n"
                        
                        # 累加 Token
                        usage = res.get("token_usage")
                        if usage:
                            total_prompt_tokens += (usage.get("prompt_tokens") or 0)
                            total_completion_tokens += (usage.get("completion_tokens") or 0)
                        
                        # 累加缓存命中
                        total_cache_hits += res.get("cache_hits", 0)
                        
                        # 耗时取最大值
                        max_processing_time = max(max_processing_time, (res.get("processing_time") or 0))
                    
                    if success_count == 0 and len(chunks) > 0:
                        status = "failed"
                    
                    # 最终兜底：如果还是没有模型名称，尝试从数据库获取
                    if not used_model_name and used_model_id:
                        try:
                            from app.services.llm_agent import get_llm_agent
                            temp_agent = await get_llm_agent(used_model_id)
                            if temp_agent:
                                used_model_name = temp_agent.model_name or used_model_id
                        except:
                            pass
                    
                    agent_result = {
                        "status": status,
                        "error": error_msg if status == "failed" else None,
                        "model_id": used_model_id,
                        "model_name": used_model_name,
                        "user_prompt": params.get("agent_prompt"),
                        "system_prompt": params.get("agent_system_prompt"),
                        "extracted_items": merged_extracted_items,
                        "raw_response": merged_raw_response,
                        "token_usage": {
                            "prompt_tokens": total_prompt_tokens,
                            "completion_tokens": total_completion_tokens,
                            "total_tokens": total_prompt_tokens + total_completion_tokens
                        },
                        "processing_time": max_processing_time,
                        "cache_hits": total_cache_hits,
                        "total_chunks": len(chunks),
                        "parallel_info": {
                            "enabled": True,
                            "chunks": len(chunks),
                            "batch_size": batch_size,
                            "success_count": success_count,
                            "cache_hits": total_cache_hits
                        }
                    }
                else:
                    agent_result = await self._run_agent_extraction(
                        content=visual_content,
                        screenshot=screenshot,
                        model_id=params["agent_model_id"],
                        user_prompt=params.get("agent_prompt", ""),
                        system_prompt=params.get("agent_system_prompt"),
                        skills=[step.get("action") for step in interaction_steps] if interaction_steps else None
                    )

                result["agent_result"] = agent_result
                # 将视觉内容存入结果，方便调试
                result["visual_content"] = visual_content
                
                # 设置 AI 缓存标志
                if agent_result.get("cache_hits", 0) > 0:
                    if agent_result.get("total_chunks", 1) == agent_result.get("cache_hits"):
                        agent_cached = True
                    else:
                        # 部分命中 (在结果中体现)
                        pass

            # 最终整合缓存标志到结果
            result["html_cached"] = html_cached
            result["agent_cached"] = agent_cached

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

    async def _extract_visual_content(self, page, container_selector: str = None, exclude_selectors: str = None) -> str:
        """
        提取页面的视觉块状内容
        通过 JavaScript 分析 DOM 元素的视觉位置，并将其按视觉顺序重组。
        """
        js_script = """
        (args) => {
            const containerSelector = args.containerSelector;
            const excludeSelectorsStr = args.excludeSelectorsStr;
            const excludeSelectorsList = (excludeSelectorsStr || "").split(';').map(s => s.trim()).filter(s => s);
            const excludeSelector = excludeSelectorsList.join(',');
            
            const isExcluded = (node) => {
                if (!excludeSelector) return false;
                try {
                    return node.matches(excludeSelector) || node.closest(excludeSelector) !== null;
                } catch (e) { return false; }
            };

            const extractFromRoot = (rootNode) => {
                const results = [];
                const walk = (node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const style = window.getComputedStyle(node);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0' || isExcluded(node)) {
                            return;
                        }
                        
                        const tagName = node.tagName.toLowerCase();
                        if (['script', 'style', 'noscript', 'iframe', 'svg'].includes(tagName)) {
                            return;
                        }

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
                                if (tagName === 'a' && node.href) {
                                    const href = node.href;
                                    text = text ? `${text} [Link: ${href}]` : `[Link: ${href}]`;
                                }

                                results.push({
                                    tagName,
                                    text: text,
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                    w: Math.round(rect.width),
                                    h: Math.round(rect.height)
                                });
                                return;
                            }
                        }
                    }
                    for (const child of node.childNodes) {
                        walk(child);
                    }
                };

                walk(rootNode);

                // 排序与分块逻辑
                results.sort((a, b) => {
                    const yDiff = a.y - b.y;
                    if (Math.abs(yDiff) < 10) return a.x - b.x;
                    return yDiff;
                });

                const blocks = [];
                let currentBlock = null;
                for (const item of results) {
                    if (!currentBlock || Math.abs(item.y - currentBlock.y) > 15) {
                        if (currentBlock) blocks.push(currentBlock);
                        currentBlock = { y: item.y, texts: [item.text] };
                    } else {
                        currentBlock.texts.push(item.text);
                    }
                }
                if (currentBlock) blocks.push(currentBlock);
                return blocks.map(b => b.texts.join(' | ')).join('\\n');
            };

            if (containerSelector) {
                try {
                    const containers = document.querySelectorAll(containerSelector);
                    if (containers.length > 0) {
                        return Array.from(containers)
                            .map(c => extractFromRoot(c))
                            .filter(txt => txt.trim())
                            .join('\\n------\\n');
                    }
                } catch (e) {
                    console.error("Invalid container selector", e);
                }
            }
            
            return extractFromRoot(document.body);
        }
        """
        try:
            content = await page.evaluate(js_script, {
                "containerSelector": container_selector,
                "excludeSelectorsStr": exclude_selectors
            })
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
        self, content: str, screenshot: str, model_id: str, user_prompt: str, system_prompt: Optional[str] = None, skills: List[str] = None, cache_enabled: bool = True
    ) -> dict:
        """
        运行 Agent 内容提取 (带缓存检查)
        """
        from app.services.llm_agent import get_llm_agent
        from app.models.llm import AgentResult, AgentStatus
        from app.services.cache_service import cache_service

        # 1. 检查 LLM 缓存
        if cache_enabled and settings.cache_enabled:
            cached_result = await cache_service.get_llm(content, model_id, user_prompt, system_prompt)
            if cached_result:
                logger.info(f"LLM cache hit for content hash")
                # 标记为命中
                cached_result["cache_hits"] = 1
                cached_result["total_chunks"] = 1
                return cached_result

        try:
            agent = await get_llm_agent(model_id)
            if not agent:
                return AgentResult(
                    status=AgentStatus.FAILED,
                    error=f"Model {model_id} not found or disabled",
                    total_chunks=1
                ).model_dump(mode='json')

            logger.info(f"Agent extraction started for task using model: {agent.model_name} ({model_id})")
            result = await agent.extract_content(
                content=content,
                screenshot_base64=screenshot,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                skills=skills
            )
            logger.info(f"Agent extraction completed using model: {agent.model_name}")
            
            # 转为字典并补全统计信息 (使用 mode='json' 以解析 datetime)
            res_dict = result.model_dump(mode='json')
            res_dict["cache_hits"] = 0
            res_dict["total_chunks"] = 1
            
            # 2. 保存 LLM 缓存 (仅成功时)
            if cache_enabled and settings.cache_enabled and result.status == AgentStatus.SUCCESS:
                await cache_service.set_llm(content, model_id, user_prompt, res_dict, system_prompt=system_prompt)
                
            return res_dict

        except Exception as e:
            return AgentResult(
                status=AgentStatus.FAILED, 
                error=str(e),
                model_id=model_id,
                total_chunks=1
            ).model_dump(mode='json')


# 全局抓取器实例
scraper = Scraper()
