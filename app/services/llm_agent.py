"""
LLM Agent 服务模块

使用大语言模型进行网页内容理解和智能提取
"""

import json
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
import google.genai as genai
from google.genai import types

from app.models.llm import AgentResult, AgentStatus, LLMProvider

logger = logging.getLogger(__name__)


class LLMAgent:
    """LLM Agent 服务 - 使用大模型进行网页内容理解和提取"""

    def __init__(self, model_config: Dict[str, Any]):
        """
        初始化 LLM Agent

        Args:
            model_config: 模型配置字典，包含 provider, base_url, api_key, model_name 等
        """
        self.config = model_config
        self.provider = model_config.get("provider", "openai")
        self.base_url = model_config.get("base_url", "").rstrip("/")
        self.api_key = model_config.get("api_key", "")
        self.model_name = model_config.get("model_name", "")
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 4096)
        self.supports_stream = model_config.get("supports_stream", False)
        self.max_retries = model_config.get("max_retries", 3)

    async def test_connection(self, prompt: str = "Hello") -> str:
        """
        测试 LLM 连接

        Args:
            prompt: 测试提示词

        Returns:
            str: 模型响应文本
        """
        response = await self._call_llm([{"role": "user", "content": prompt}])
        return response.get("content", "")

    async def extract_content(
        self,
        content: str,
        screenshot_base64: Optional[str],
        user_prompt: str,
        system_prompt: Optional[str] = None,
        skills: List[str] = None,
    ) -> AgentResult:
        """
        从网页中提取结构化内容

        Args:
            html: 网页 HTML 内容
            screenshot_base64: 可选的截图（用于视觉理解）
            user_prompt: 用户的提取要求
            skills: 可用的 skill 列表

        Returns:
            AgentResult: 提取结果
        """
        start_time = time.time()
        result = AgentResult(
            status=AgentStatus.PROCESSING,
            model_id=str(self.config.get("_id", "")),
            model_name=self.config.get("name", self.model_name),
            user_prompt=user_prompt,
            created_at=datetime.now(),
        )

        max_retries = self.max_retries
        retry_delay = 2  # 初始重试延迟（秒）
        
        for attempt in range(max_retries):
            try:
                # 构建系统提示
                system_prompt = self._build_extraction_system_prompt(system_prompt, skills)
                result.system_prompt = system_prompt

                # 构建用户消息
                user_message = self._build_extraction_user_message(
                    content, user_prompt, screenshot_base64
                )

                # 调用 LLM
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]

                response = await self._call_llm(messages)

                # 解析响应
                llm_content = response.get("content", "")
                result.raw_response = llm_content
                result.token_usage = response.get("usage")

                # 尝试解析 JSON 结果
                extracted = self._parse_extraction_result(llm_content)
                result.extracted_items = extracted

                result.status = AgentStatus.SUCCESS
                result.processing_time = time.time() - start_time
                result.completed_at = datetime.now()
                # 成功则跳出重试循环
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Agent extraction attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"Agent extraction failed after {max_retries} attempts: {e}", exc_info=True)
                    result.status = AgentStatus.FAILED
                    result.error = str(e)
                    result.processing_time = time.time() - start_time
                    result.completed_at = datetime.now()

        return result

    def _build_extraction_system_prompt(
        self, custom_system_prompt: Optional[str] = None, skills: List[str] = None
    ) -> str:
        """构建提取任务的系统提示词"""
        base_prompt = """你是一个专业的网页内容提取助手。你的任务是根据用户的要求，从提供的**视觉块状网页内容**中提取结构化数据。

这些内容已经过预处理，按页面的视觉顺序（从上到下，从左到右）进行了排列。每一行代表页面上的一个视觉块或一组紧邻的元素。

请遵循以下规则：
1. 仔细分析提供的文本结构，识别重复的模式、列表项或卡片信息。
2. 提取用户要求的所有字段。同一行中用 '|' 分隔的内容通常是视觉上相邻或具有逻辑关联的（例如：标题 | 价格 | 评分）。
3. 返回 JSON 格式的结果，格式为一个数组，每个元素是一个提取的记录。
4. 如果某个字段无法提取，使用 null 值。
5. 确保提取的数据完整且准确。

输出格式示例：
```json
{
  "items": [
    {"title": "标题1", "price": "100", "image": "http://..."},
    {"title": "标题2", "price": "200", "image": "http://..."}
  ],
  "total_count": 2,
  "notes": "可选的备注说明"
}
```
"""

        # 如果提供了自定义系统提示，将其与基础提示合并
        if custom_system_prompt:
            # prompt = f"{custom_system_prompt}\n\n---\n\n{base_prompt}"
            prompt = f"{custom_system_prompt}"
        else:
            prompt = base_prompt

        if skills:
            prompt += "\n\n系统当前支持以下增强技能 (Skills)，这些技能已经被集成在抓取流程中：\n"
            skill_docs = {
                "scroll": "- 滚动 (scroll): 支持对 window 或特定容器进行垂直滚动，用于触发懒加载或获取下方内容。",
                "infinite_scroll": "- 流式滚动 (infinite_scroll): 高级滚动技能，能够自动判断是否有新内容加载，并持续滚动直到页面底部或加载完成。",
                "pagination": "- 翻页 (pagination): 能够识别并执行“下一页”或“上一页”操作。",
                "zoom": "- 缩放 (zoom): 专门用于地图组件的放大或缩小，帮助获取不同层级的地理信息。",
                "fill": "- 填充 (fill): 支持自动填写表单字段。",
                "click": "- 点击 (click): 点击页面上的特定元素（如展开更多、切换 Tab）。",
                "wait": "- 等待 (wait): 在操作之间执行固定时长的等待，确保动态内容加载完毕。"
            }
            for skill in skills:
                if skill in skill_docs:
                    prompt += f"{skill_docs[skill]}\n"

        return prompt

    def _build_extraction_user_message(
        self, content: str, user_prompt: str, screenshot_base64: Optional[str] = None
    ) -> str:
        """构建用户消息"""
        message = f"""用户的提取要求：
{user_prompt}

网页视觉块状内容（按视觉顺序排列）：
---
{content}
---
"""

        return message

    def _parse_extraction_result(self, content: str) -> Optional[List[Dict]]:
        """解析 LLM 返回的提取结果"""
        try:
            # 尝试提取 JSON 块
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()

            # 解析 JSON
            data = json.loads(content)

            # 支持多种返回格式
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                if "items" in data:
                    return data["items"]
                elif "data" in data:
                    return data["data"]
                elif "results" in data:
                    return data["results"]
                else:
                    # 单个对象包装成列表
                    return [data]

            return None

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse extraction result as JSON: {e}")
            return None

    async def _call_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        调用 LLM API

        Args:
            messages: 消息列表

        Returns:
            Dict: 包含 content 和 usage 的响应
        """
        if self.provider == LLMProvider.OPENAI or self.provider == "openai":
            return await self._call_openai_compatible(messages)
        elif self.provider == LLMProvider.ANTHROPIC or self.provider == "anthropic":
            return await self._call_anthropic(messages)
        elif self.provider == LLMProvider.GOOGLE or self.provider == "google":
            return await self._call_google(messages)
        elif self.provider == LLMProvider.OLLAMA or self.provider == "ollama":
            return await self._call_ollama(messages)
        else:
            # 默认尝试 OpenAI 兼容格式
            return await self._call_openai_compatible(messages)

    async def _call_openai_compatible(
        self, messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """调用 OpenAI 兼容 API"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": self.supports_stream
        }

        full_content = ""
        usage = None

        async with httpx.AsyncClient(timeout=120.0) as client:
            if self.supports_stream:
                logger.info(f"Using streaming for OpenAI compatible model: {self.model_name}")
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data_str)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content_chunk = delta.get("content")
                                if content_chunk:
                                    full_content += content_chunk
                                    # 实时展示
                                    print(content_chunk, end="", flush=True)
                            
                            if "usage" in chunk and chunk["usage"]:
                                usage = chunk["usage"]
                        except Exception as e:
                            logger.warning(f"Failed to parse OpenAI stream chunk: {e}")
                print() # newline
            else:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                full_content = data["choices"][0]["message"]["content"]
                usage = data.get("usage")

        return {
            "content": full_content,
            "usage": usage,
        }

    async def _call_anthropic(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用 Anthropic API"""
        url = f"{self.base_url}/messages"

        # 转换消息格式（提取 system 消息）
        system_content = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                anthropic_messages.append(msg)

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model_name,
            "messages": anthropic_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": self.supports_stream
        }
        if system_content:
            payload["system"] = system_content

        full_content = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0}

        async with httpx.AsyncClient(timeout=120.0) as client:
            if self.supports_stream:
                logger.info(f"Using streaming for Anthropic model: {self.model_name}")
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        
                        data_str = line[6:]
                        try:
                            chunk = json.loads(data_str)
                            event_type = chunk.get("type")
                            
                            if event_type == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    full_content += text
                                    print(text, end="", flush=True)
                            elif event_type == "message_start":
                                msg = chunk.get("message", {})
                                usage["prompt_tokens"] = msg.get("usage", {}).get("input_tokens", 0)
                            elif event_type == "message_delta":
                                usage["completion_tokens"] = chunk.get("usage", {}).get("output_tokens", 0)
                        except Exception as e:
                            logger.warning(f"Failed to parse Anthropic stream chunk: {e}")
                print()
            else:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                full_content = data["content"][0]["text"]
                usage = {
                    "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
                }

        return {"content": full_content, "usage": usage}

    async def _call_google(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用 Google Gemini API (使用 google-genai SDK)"""
        # 配置客户端
        client_options = {'api_key': self.api_key}
        
        # 处理基础 URL
        base_url = self.base_url.rstrip("/")
        if base_url:
            # SDK 的 http_options 使用 base_url
            client_options['http_options'] = {'base_url': base_url}
        
        client = genai.Client(**client_options)
        
        # 转换 OpenAi 消息格式为 SDK 格式
        contents = []
        system_instruction = None
        
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
        
        # 设置生成的配置
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            system_instruction=system_instruction
        )
        
        # SDK 目前主要是同步的，在大规模并发下建议使用其异步版本（如果版本支持 aio）
        # 这里使用 aio 接口（Client.aio）
        async_client = genai.Client(**client_options, vertexai=False).aio
        
        full_content = ""
        usage = None

        if self.supports_stream:
            logger.info(f"Using streaming for Google Gemini model: {self.model_name}")
            async for chunk in await async_client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config
            ):
                if chunk.text:
                    full_content += chunk.text
                    print(chunk.text, end="", flush=True)
                
                if chunk.usage_metadata:
                    usage = {
                        "prompt_tokens": getattr(chunk.usage_metadata, 'prompt_token_count', 0),
                        "completion_tokens": getattr(chunk.usage_metadata, 'candidates_token_count', 0),
                        "total_tokens": getattr(chunk.usage_metadata, 'total_token_count', 0)
                    }
            print()
        else:
            response = await async_client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            full_content = response.text
            usage = {
                "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0) if response.usage_metadata else 0,
                "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0) if response.usage_metadata else 0,
                "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0) if response.usage_metadata else 0
            }
        
        return {
            "content": full_content,
            "usage": usage
        }

    async def _call_ollama(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用 Ollama API"""
        url = f"{self.base_url}/api/chat"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": self.supports_stream,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        full_content = ""
        prompt_tokens = 0
        completion_tokens = 0
        import httpx
        async with httpx.AsyncClient(timeout=300.0) as client:
            if self.supports_stream:
                import logging
                logger = logging.getLogger("app.services.llm_agent")
                logger.info(f"Using streaming for Ollama model: {self.model_name}")
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk:
                                content_chunk = chunk["message"].get("content", "")
                                full_content += content_chunk
                                print(content_chunk, end="", flush=True)
                            if chunk.get("done"):
                                prompt_tokens = chunk.get("prompt_eval_count", 0)
                                completion_tokens = chunk.get("eval_count", 0)
                        except Exception as e:
                            logger.warning(f"Failed to parse Ollama stream chunk: {e}")
                print()
            else:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                full_content = data["message"]["content"]
                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)
        return {
            "content": full_content,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
async def get_llm_agent(model_id: str) -> Optional[LLMAgent]:
    """
    根据模型 ID 获取 LLM Agent 实例

    Args:
        model_id: 模型配置 ID

    Returns:
        LLMAgent 实例，如果模型不存在返回 None
    """
    from bson import ObjectId
    from app.db.mongo import mongo

    try:
        model_config = mongo.llm_models.find_one({"_id": ObjectId(model_id)})
        if not model_config:
            return None
        if not model_config.get("is_enabled", False):
            return None
        return LLMAgent(model_config)
    except Exception as e:
        logger.error(f"Failed to get LLM agent for model {model_id}: {e}")
        return None
