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
        html: str,
        screenshot_base64: Optional[str],
        user_prompt: str,
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

        try:
            # 构建系统提示
            system_prompt = self._build_extraction_system_prompt(skills)

            # 构建用户消息
            user_message = self._build_extraction_user_message(
                html, user_prompt, screenshot_base64
            )

            # 调用 LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            response = await self._call_llm(messages)

            # 解析响应
            content = response.get("content", "")
            result.raw_response = content
            result.token_usage = response.get("usage")

            # 尝试解析 JSON 结果
            extracted = self._parse_extraction_result(content)
            result.extracted_items = extracted

            result.status = AgentStatus.SUCCESS
            result.processing_time = time.time() - start_time
            result.completed_at = datetime.now()

        except Exception as e:
            logger.error(f"Agent extraction failed: {e}", exc_info=True)
            result.status = AgentStatus.FAILED
            result.error = str(e)
            result.processing_time = time.time() - start_time
            result.completed_at = datetime.now()

        return result

    def _build_extraction_system_prompt(self, skills: List[str] = None) -> str:
        """构建提取任务的系统提示"""
        prompt = """你是一个专业的网页内容提取助手。你的任务是根据用户的要求，从提供的网页 HTML 内容中提取结构化数据。

请遵循以下规则：
1. 仔细分析 HTML 结构，识别重复的列表项或卡片元素
2. 提取用户要求的所有字段
3. 返回 JSON 格式的结果，格式为一个数组，每个元素是一个提取的记录
4. 如果某个字段无法提取，使用 null 值
5. 确保提取的数据完整且准确

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

        if skills:
            prompt += f"\n\n可用的技能: {', '.join(skills)}"

        return prompt

    def _build_extraction_user_message(
        self, html: str, user_prompt: str, screenshot_base64: Optional[str] = None
    ) -> str:
        """构建用户消息"""
        # 限制 HTML 长度，避免超出 token 限制
        max_html_length = 50000  # 约 12500 tokens
        if len(html) > max_html_length:
            html = html[:max_html_length] + "\n... [HTML 内容已截断]"

        message = f"""用户的提取要求：
{user_prompt}

网页 HTML 内容：
```html
{html}
```

请根据要求提取数据，返回 JSON 格式的结果。"""

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
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return {
            "content": data["choices"][0]["message"]["content"],
            "usage": data.get("usage"),
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
        }
        if system_content:
            payload["system"] = system_content

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return {"content": data["content"][0]["text"], "usage": data.get("usage")}

    async def _call_google(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用 Google Gemini API"""
        url = f"{self.base_url}/models/{self.model_name}:generateContent?key={self.api_key}"

        # 转换消息格式
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        headers = {"Content-Type": "application/json"}

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return {
            "content": data["candidates"][0]["content"]["parts"][0]["text"],
            "usage": data.get("usageMetadata"),
        }

    async def _call_ollama(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用 Ollama API"""
        url = f"{self.base_url}/api/chat"

        headers = {"Content-Type": "application/json"}

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return {
            "content": data["message"]["content"],
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0)
                + data.get("eval_count", 0),
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
