from __future__ import annotations

import json
import os
import textwrap
import warnings
from typing import Optional

import requests
import time

from models import Paper

# SiliconFlow API 配置
DEFAULT_SILICONFLOW_URL = "https://api.siliconflow.cn/v1/chat/completions"
DEFAULT_SILICONFLOW_MODEL = "Qwen/QwQ-32B"
# 内置的备用 API Key（由用户提供，用于未设置环境变量或未在命令行传参时回退）
DEFAULT_SILICONFLOW_API_KEY = "sk-iixgagmdiimarcsankdstxmlpjypowmcmzlwdfgrjgmbicrg"
SILICONFLOW_API_KEY="sk-zmwzhnvngvjiibrrdifvdqjcydqelpmqmniyuzxwoxastwsx"

class LLMInterpreter:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        provider: str = "siliconflow",
    ):
        self.provider = provider.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url: str
        self.api_key: str

        if self.provider == "siliconflow":
            # 优先：函数参数 -> 环境变量 -> 内置默认
            self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY") or DEFAULT_SILICONFLOW_API_KEY
            if self.api_key == DEFAULT_SILICONFLOW_API_KEY:
                warnings.warn(
                    "正在使用内置的 SiliconFlow API Key 作为回退。建议通过环境变量 SILICONFLOW_API_KEY 或 --api-key 提供你自己的密钥以保证安全。",
                    UserWarning,
                )
            self.base_url = base_url or DEFAULT_SILICONFLOW_URL
            self.model = model or DEFAULT_SILICONFLOW_MODEL
        else:
            raise RuntimeError(f"不支持的提供方：{provider}。当前仅支持 siliconflow。")

    def summarize(self, paper: Paper, content: str, extra: Optional[str] = None) -> str:
        return self._summarize_siliconflow(paper, content, extra)

    def _build_prompt(self, paper: Paper, content: str, extra: Optional[str]) -> str:
        return textwrap.dedent(
            f"""
            论文信息：
            标题：{paper.title}
            作者：{', '.join(paper.authors) if paper.authors else ''}
            年份：{paper.year or ''}
            链接：{paper.link}
            摘要与前几页内容（截断）： 
            {content[:4000]}

            请输出：
            1) 文章定位（研究问题/场景、核心贡献）
            2) 关键方法（含模型/算法/数据/实验设置）
            3) 核心发现与结果
            4) 局限与未来方向
            5) 可发布到社交平台的小结（50-80 字）
            {f'额外需求：{extra}' if extra else ''}
            """
        ).strip()

    def _summarize_siliconflow(self, paper: Paper, content: str, extra: Optional[str]) -> str:
        """调用 SiliconFlow API 进行论文总结"""
        system_prompt = "你是一名科研论文解读助手，请用中文输出，保持条理、分点、精炼。"
        user_prompt = self._build_prompt(paper, content, extra)
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # debug 支持：设置环境变量 SILICONFLOW_DEBUG=1 可以打印请求/响应片段
        debug = os.getenv("SILICONFLOW_DEBUG", "0") in ("1", "true", "True")

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                if debug:
                    print(f"[SiliconFlow] 请求 (attempt={attempt}): model={self.model} messages_len={len(payload['messages'])}")
                resp = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
            except Exception as exc:
                if attempt == max_attempts:
                    raise RuntimeError(f"请求 SiliconFlow 时出错：{exc}") from exc
                sleep_for = 2 ** attempt
                time.sleep(sleep_for)
                continue

            # 若状态码不是 200，提供更清晰的报错与重试逻辑
            if resp.status_code != 200:
                short_body = resp.text[:2000]
                if resp.status_code in (401, 403):
                    raise RuntimeError(
                        f"SiliconFlow 返回 {resp.status_code}（未经授权/禁止）。可能原因：API Key 无效或账号/模型未授权。响应摘要：{short_body}"
                    )
                if resp.status_code == 429:
                    # rate limit，重试
                    if attempt < max_attempts:
                        # 尝试读取 Retry-After
                        try:
                            ra = int(resp.headers.get("Retry-After", 2 ** attempt))
                        except Exception:
                            ra = 2 ** attempt
                        time.sleep(ra)
                        continue
                    raise RuntimeError(f"SiliconFlow 速率限制：{short_body}")
                if 500 <= resp.status_code < 600 and attempt < max_attempts:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"SiliconFlow 返回 {resp.status_code}：{short_body}")

            # 成功返回
            try:
                data = resp.json()
            except Exception as exc:
                raise RuntimeError(f"无法解析 SiliconFlow 返回的 JSON：{exc}，文本：{resp.text[:2000]}") from exc

            # 解析响应（兼容 OpenAI 风格响应）
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                # 支持多种结构：{message: {content: ...}} 或 {text: ...}
                if isinstance(choice, dict):
                    msg = choice.get("message") or choice.get("delta") or {}
                    if isinstance(msg, dict):
                        content = msg.get("content") or msg.get("text")
                        if isinstance(content, str):
                            return content
                    # 直接支持 text 字段
                    text_field = choice.get("text")
                    if isinstance(text_field, str):
                        return text_field
            # 兼容可能的顶层 content
            if isinstance(data, dict):
                # 尝试常见路径
                if "content" in data and isinstance(data["content"], str):
                    return data["content"]

            raise RuntimeError(f"SiliconFlow API 返回异常格式：{json.dumps(data)[:2000]}")

