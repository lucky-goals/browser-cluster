"""
浏览器自动化技能 (Skills) 模块

定义常用的浏览器操作技能，如翻页、滚动、缩放等。
这些技能可以在抓取过程中被调用。
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from playwright.async_api import Page, ElementHandle

logger = logging.getLogger(__name__)

class BrowserSkills:
    """浏览器操作技能类"""

    @staticmethod
    async def scroll_container(page: Page, selector: str, distance: int = 500, delay: int = 1000):
        """
        滚动指定容器
        
        Args:
            page: Playwright 页面对象
            selector: 容器选择器
            distance: 滚动距离（像素）
            delay: 滚动后的平复等待时间（毫秒）
        """
        try:
            if selector == "window":
                await page.evaluate(f"window.scrollBy(0, {distance})")
            else:
                await page.evaluate(f"""
                    (selector, dist) => {{
                        const el = document.querySelector(selector);
                        if (el) {{
                            el.scrollTop += dist;
                        }}
                    }}
                """, selector, distance)
            
            await asyncio.sleep(delay / 1000)
            return True
        except Exception as e:
            logger.error(f"Skill scroll_container failed: {e}")
            return False

    @staticmethod
    async def pagination(page: Page, action: str = "next", selector: str = None):
        """
        执行翻页操作
        
        Args:
            page: 页面对象
            action: 操作类型 (next, prev)
            selector: 翻页按钮选择器，如果为 None 则尝试自动识别
        """
        try:
            if not selector:
                # 尝试通用的关键词识别翻页按钮
                keywords = ["下一页", "Next", ">", "next page", "»"] if action == "next" else ["上一页", "Prev", "<", "prev page", "«"]
                
                found_btn = False
                for kw in keywords:
                    # 优先查找按钮和链接
                    btn = page.get_by_role("button", name=kw, exact=False)
                    if await btn.count() > 0:
                        await btn.first.click()
                        found_btn = True
                        break
                    
                    lnk = page.get_by_role("link", name=kw, exact=False)
                    if await lnk.count() > 0:
                        await lnk.first.click()
                        found_btn = True
                        break
                
                if not found_btn:
                    # 兜底：使用 text 选择器
                    for kw in keywords:
                        try:
                            await page.click(f"text='{kw}'", timeout=2000)
                            found_btn = True
                            break
                        except:
                            continue
            else:
                await page.click(selector)
            
            # 等待网络空闲
            await page.wait_for_load_state("networkidle", timeout=5000)
            return True
        except Exception as e:
            logger.error(f"Skill pagination failed: {e}")
            return False

    @staticmethod
    async def map_zoom(page: Page, selector: str, direction: str = "in", times: int = 1):
        """
        地图缩放
        
        Args:
            page: 页面对象
            selector: 地图容器或缩放按钮选择器
            direction: 缩放方向 (in, out)
            times: 缩放次数
        """
        try:
            # 常见地图的快捷键：+ 和 - 
            key = "+" if direction == "in" else "-"
            
            # 先对准地图容器
            if selector:
                await page.hover(selector)
            
            for _ in range(times):
                await page.keyboard.press(key)
                await asyncio.sleep(0.5)
            
            return True
        except Exception as e:
            logger.error(f"Skill map_zoom failed: {e}")
            return False

    @staticmethod
    async def fill_form(page: Page, data: Dict[str, str]):
        """
        填充表单
        
        Args:
            page: 页面对象
            data: 键值对 {选择器: 填充内容}
        """
        try:
            for selector, value in data.items():
                await page.fill(selector, value)
            return True
        except Exception as e:
            logger.error(f"Skill fill_form failed: {e}")
            return False

    @staticmethod
    async def click_element(page: Page, selector: str):
        """点击元素"""
        try:
            await page.click(selector)
            return True
        except Exception as e:
            logger.error(f"Skill click_element failed: {e}")
            return False

    @staticmethod
    async def wait_time(page: Page, duration: int):
        """等待时间 (ms)"""
        await asyncio.sleep(duration / 1000)
        return True

    @staticmethod
    async def infinite_scroll(page: Page, selector: str = "window", max_scrolls: int = 10, delay: int = 1500):
        """
        流式滚动（无限滚动）直到不再加载新内容
        
        Args:
            page: 页面对象
            selector: 容器选择器
            max_scrolls: 最大滚动次数，防止陷入死循环
            delay: 每次滚动后的等待加载时间 (ms)
        """
        try:
            current_scrolls = 0
            while current_scrolls < max_scrolls:
                # 获取滚动前的状态（容器总高度）
                if selector == "window":
                    prev_state = await page.evaluate("document.body.scrollHeight")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                else:
                    prev_state = await page.evaluate(f"""
                        (sel) => {{
                            const el = document.querySelector(sel);
                            return el ? el.scrollHeight : 0;
                        }}
                    """, selector)
                    await page.evaluate(f"""
                        (sel) => {{
                            const el = document.querySelector(sel);
                            if (el) el.scrollTop = el.scrollHeight;
                        }}
                    """, selector)
                
                # 等待加载
                await asyncio.sleep(delay / 1000)
                
                # 获取滚动后的状态
                if selector == "window":
                    curr_state = await page.evaluate("document.body.scrollHeight")
                else:
                    curr_state = await page.evaluate(f"""
                        (sel) => {{
                            const el = document.querySelector(sel);
                            return el ? el.scrollHeight : 0;
                        }}
                    """, selector)
                
                # 如果高度没变，说明到底了（或者加载失败/太慢）
                if curr_state == prev_state:
                    logger.info(f"Infinite scroll reached end at {current_scrolls} scrolls")
                    break
                
                current_scrolls += 1
                logger.info(f"Infinite scroll progressed: {current_scrolls}/{max_scrolls}")
            
            return True
        except Exception as e:
            logger.error(f"Skill infinite_scroll failed: {e}")
            return False

    @staticmethod
    async def extract_coordinates(page: Page):
        """
        提取页面中的 Google Maps 坐标 (纬度, 经度)
        支持递归搜索 Shadow DOM 和 iframe
        """
        try:
            # JS 脚本：广度优先搜索所有 Shadow Root 和 iframe 中的 Google Maps 链接
            js_script = """
            () => {
                const results = [];
                const coordRegex = /(ll|query|@)=([-+]?\\d+\\.\\d+),([-+]?\\d+\\.\\d+)/;
                const altRegex = /@([-+]?\\d+\\.\\d+),([-+]?\\d+\\.\\d+)/;

                const findInNode = (root) => {
                    // 1. 查找所有链接，使用正则匹配各种 Google TLD (如 .com, .co.uk, .com.hk 等)
                    const googleMapsRegex = /google\\.[a-z.]+\\/maps/;
                    const links = Array.from(root.querySelectorAll('a')).filter(a => googleMapsRegex.test(a.href));
                    
                    for (const link of links) {
                        const href = link.href;
                        let match = href.match(coordRegex);
                        if (match) {
                            results.push({ lat: match[2], lng: match[3], url: href });
                            continue;
                        }
                        match = href.match(altRegex);
                        if (match) {
                            results.push({ lat: match[1], lng: match[2], url: href });
                        }
                    }

                    // 2. 查找 meta 和 ld+json (仅在 document root)
                    if (root === document) {
                        const metaGeo = document.querySelector('meta[name="geo.position"]');
                        if (metaGeo) {
                            const parts = metaGeo.content.split(';');
                            if (parts.length === 2) results.push({ lat: parts[0], lng: parts[1], source: 'meta' });
                        }
                        
                        const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                        for (const s of scripts) {
                            try {
                                const data = JSON.parse(s.innerText);
                                if (data.geo && data.geo.latitude && data.geo.longitude) {
                                    results.push({ lat: data.geo.latitude, lng: data.geo.longitude, source: 'ld+json' });
                                }
                            } catch (e) {}
                        }
                    }

                    // 3. 递归 Shadow DOM
                    const allElements = root.querySelectorAll('*');
                    for (const el of allElements) {
                        if (el.shadowRoot) {
                            findInNode(el.shadowRoot);
                        }
                    }
                };

                findInNode(document);
                
                // 返回第一个找到的结果，或者按优先级排序
                return results.length > 0 ? results[0] : null;
            }
            """
            coords = await page.evaluate(js_script)
            
            # 如果主文档没找到，尝试在所有 iframe 中搜寻
            if not coords:
                frames = page.frames
                for frame in frames:
                    try:
                        # 检查 frame 是否可以访问 (跨域限制可能导致失败，但在自动化环境下通常可以绕过)
                        coords = await frame.evaluate(js_script)
                        if coords:
                            break
                    except:
                        continue

            if coords:
                logger.info(f"Extracted coordinates: {coords}")
                return coords
            return None
        except Exception as e:
            logger.error(f"Skill extract_coordinates failed: {e}")
            return None

# 技能映射表
SKILLS_MAP = {
    "scroll": BrowserSkills.scroll_container,
    "infinite_scroll": BrowserSkills.infinite_scroll,
    "pagination": BrowserSkills.pagination,
    "zoom": BrowserSkills.map_zoom,
    "fill": BrowserSkills.fill_form,
    "click": BrowserSkills.click_element,
    "wait": BrowserSkills.wait_time,
    "extract_coordinates": BrowserSkills.extract_coordinates
}
